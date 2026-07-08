import { useEffect, useRef } from "react";
import { useGpu } from "../useGpu";

/**
 * Hero editorial: wordmark masivo sobre un waveform animado en canvas.
 * El waveform es el sujeto de la app (audio → texto); la animación vive
 * solo aquí — el resto de la página queda quieto.
 */
export function Hero({ onGpuText }: { onGpuText?: (text: string) => void }) {
  const gpu = useGpu(onGpuText);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    let t = 0;

    function resize() {
      if (!canvas) return;
      canvas.width = canvas.offsetWidth * devicePixelRatio;
      canvas.height = canvas.offsetHeight * devicePixelRatio;
    }
    resize();
    window.addEventListener("resize", resize);

    function draw() {
      if (!canvas || !ctx) return;
      const { width: w, height: h } = canvas;
      ctx.clearRect(0, 0, w, h);

      const barW = 3 * devicePixelRatio;
      const gap = 5 * devicePixelRatio;
      const n = Math.ceil(w / (barW + gap));
      const mid = h * 0.72;

      for (let i = 0; i < n; i++) {
        // pseudo-waveform: suma de senos desfasados, determinista por barra
        const a =
          Math.sin(i * 0.18 + t * 0.017) * 0.5 +
          Math.sin(i * 0.052 - t * 0.011) * 0.3 +
          Math.sin(i * 0.011 + t * 0.005) * 0.2;
        const amp = Math.abs(a) * h * 0.34 + 2 * devicePixelRatio;
        const alpha = 0.05 + Math.abs(a) * 0.2;
        ctx.fillStyle = `rgba(133, 120, 240, ${alpha.toFixed(3)})`;
        ctx.fillRect(i * (barW + gap), mid - amp, barW, amp * 2);
      }

      t += 1;
      if (!reduceMotion) raf = requestAnimationFrame(draw);
    }

    // Con reduce-motion se dibuja un solo frame estático
    t = 240;
    draw();
    if (!reduceMotion) raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <div className="hero">
      <canvas ref={canvasRef} className="hero-canvas" aria-hidden="true" />
      <div className="hero-inner">
        <div className="hero-top">
          <span className="hero-kicker">Transcripción y traducción local</span>
          <div className={`gpu-stats${gpu.available ? "" : " gpu-off"}`}>{gpu.text}</div>
        </div>
        <h1 className="hero-wordmark">
          Flowxy
          <span className="hero-wordmark-outline">Translator</span>
        </h1>
        <p className="hero-tagline">
          video → texto → cualquier idioma · whisper + nllb-200 · en tu GPU
        </p>
      </div>
    </div>
  );
}
