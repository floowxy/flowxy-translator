import { useEffect, useState, useSyncExternalStore } from "react";
import { api } from "../api";
import { getBusyCount, subscribeBusy } from "../busy";

/** Header con GPU stats — polling adaptativo: 4s con tareas activas, 30s idle. */
export function Header({ onGpuText }: { onGpuText?: (text: string) => void }) {
  const busyCount = useSyncExternalStore(subscribeBusy, getBusyCount);
  const [gpuText, setGpuText] = useState("Cargando GPU...");

  useEffect(() => {
    let cancelled = false;

    async function fetchStats() {
      let text: string;
      try {
        const data = await api.gpuStats();
        if (data.cuda?.available) {
          const memPercent = data.gpu.memory?.percent ?? 0;
          text = `GPU: ${data.gpu.name ?? "Unknown"} | Memory: ${memPercent}%`;
        } else {
          text = "GPU: No disponible (usando CPU)";
        }
      } catch {
        text = "GPU: Error";
      }
      if (!cancelled) {
        setGpuText(text);
        onGpuText?.(text);
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
      <h1>🚀 flowxy-translator</h1>
      <p className="subtitle">Transcripción y Traducción con GPU | Whisper + NLLB-200</p>
      <div className="gpu-stats">{gpuText}</div>
    </header>
  );
}
