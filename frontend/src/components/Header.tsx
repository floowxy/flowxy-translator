import { useEffect, useState, useSyncExternalStore } from "react";
import { api } from "../api";
import { getBusyCount, subscribeBusy } from "../busy";

interface GpuState {
  text: string;
  available: boolean;
}

/** Top bar con wordmark y estado de GPU — polling adaptativo: 4s ocupado, 30s idle. */
export function Header({ onGpuText }: { onGpuText?: (text: string) => void }) {
  const busyCount = useSyncExternalStore(subscribeBusy, getBusyCount);
  const [gpu, setGpu] = useState<GpuState>({ text: "GPU …", available: true });

  useEffect(() => {
    let cancelled = false;

    async function fetchStats() {
      let next: GpuState;
      try {
        const data = await api.gpuStats();
        if (data.cuda?.available) {
          const memPercent = data.gpu.memory?.percent ?? 0;
          const name = (data.gpu.name ?? "GPU").replace("NVIDIA GeForce ", "");
          next = { text: `${name} · ${memPercent}%`, available: true };
        } else {
          next = { text: "CPU (sin CUDA)", available: false };
        }
      } catch {
        next = { text: "GPU sin datos", available: false };
      }
      if (!cancelled) {
        setGpu(next);
        onGpuText?.(next.text);
      }
    }

    fetchStats();
    const timer = setInterval(fetchStats, busyCount > 0 ? 4000 : 30000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [busyCount, onGpuText]);

  return (
    <header>
      <h1>
        <span className="wordmark-accent">flowxy</span> translator
      </h1>
      <div className={`gpu-stats${gpu.available ? "" : " gpu-off"}`}>{gpu.text}</div>
    </header>
  );
}
