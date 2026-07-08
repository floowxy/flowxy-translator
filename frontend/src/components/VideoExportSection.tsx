import { useState } from "react";
import { api, exportDownloadUrl, pollProgress } from "../api";
import { tracked } from "../busy";
import { InfoBox } from "./InfoBox";
import type { VideoExportResult } from "../types";

interface Props {
  fileName: string | null;
  enabled: boolean;
}

export function VideoExportSection({ fileName, enabled }: Props) {
  const [includeTts, setIncludeTts] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<VideoExportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function progressLabel(p: number): string {
    const pct = Math.round(p * 100);
    if (p < 0.05) return "Generando subtítulos SRT...";
    if (p < 0.75) return `Quemando subtítulos... ${pct}%`;
    if (includeTts && p < 0.93) return `Generando audio TTS... ${pct}%`;
    return `Finalizando... ${pct}%`;
  }

  async function handleExport() {
    if (!fileName) return;

    const taskId = crypto.randomUUID();
    setLoading(true);
    setResult(null);
    setError(null);
    setProgress(0);

    const stopPolling = pollProgress(taskId, setProgress);

    try {
      const data = await tracked(api.exportVideo(fileName, includeTts, taskId));
      setProgress(1);
      setResult(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      stopPolling();
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <h2>🎬 6. Generar Video Final con Subtítulos</h2>
      <p className="section-desc" style={{ lineHeight: 1.7 }}>
        Crea un nuevo video con subtítulos integrados permanentemente (quemados) y opcionalmente
        con audio TTS. El video resultante será compatible con cualquier reproductor.
      </p>

      <div className="checkbox-group" style={{ marginBottom: "2rem" }}>
        <label>
          <input
            type="checkbox"
            checked={includeTts}
            onChange={(e) => setIncludeTts(e.target.checked)}
          />
          <span style={{ fontSize: "1rem", fontWeight: 600 }}>
            🎙️ Incluir audio TTS en español (doblaje completo)
          </span>
        </label>
        <p className="checkbox-hint">
          Genera voz en español y reemplaza el audio original (tarda más tiempo)
        </p>
      </div>

      <button
        className="btn btn-primary"
        style={{ width: "100%", fontSize: "1rem", padding: "1.2rem" }}
        disabled={!enabled || loading}
        onClick={handleExport}
      >
        🎬 GENERAR VIDEO CON SUBTÍTULOS
      </button>

      {loading && (
        <div className="export-progress">
          <div style={{ marginBottom: "0.75rem" }}>
            <span className="export-progress-text">{progressLabel(progress)}</span>
          </div>
          <div className="export-progress-track">
            <div
              id="export-progress-bar"
              style={{ width: `${Math.round(progress * 100)}%` }}
            />
          </div>
        </div>
      )}

      {result && (
        <InfoBox kind="success">
          Video generado: {result.file_name} ({(result.size_bytes / 1024 / 1024).toFixed(2)} MB) —{" "}
          {result.includes_tts ? "Con TTS" : "Sin TTS"}
          <a
            href={exportDownloadUrl(result.file_name)}
            download={result.file_name}
            className="download-final-link"
          >
            ⬇️ DESCARGAR VIDEO FINAL
          </a>
        </InfoBox>
      )}
      {error && <InfoBox kind="error">Error: {error}</InfoBox>}
    </section>
  );
}
