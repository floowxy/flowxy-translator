import { useState } from "react";
import { api, exportDownloadUrl, pollProgress } from "../api";
import { tracked } from "../busy";
import { InfoBox } from "./InfoBox";
import { Section } from "./Section";
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
    if (p < 0.05) return "Generando subtítulos SRT…";
    if (p < 0.75) return `Quemando subtítulos… ${pct}%`;
    if (includeTts && p < 0.93) return `Generando audio TTS… ${pct}%`;
    return `Finalizando… ${pct}%`;
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
    <Section
      step={6}
      title="Video final"
      desc="Genera un MP4 con los subtítulos quemados, compatible con cualquier reproductor."
    >
      <div className="checkbox-group" style={{ marginBottom: "1rem" }}>
        <label>
          <input
            type="checkbox"
            checked={includeTts}
            onChange={(e) => setIncludeTts(e.target.checked)}
          />
          <span>Doblaje TTS en español — reemplaza el audio original</span>
        </label>
        <p className="checkbox-hint">Tarda más: genera la voz y sincroniza el audio completo</p>
      </div>

      <button
        className="btn btn-primary"
        style={{ width: "100%" }}
        disabled={!enabled || loading}
        onClick={handleExport}
      >
        Generar video con subtítulos
      </button>

      {loading && (
        <div className="export-progress">
          <div style={{ marginBottom: "0.6rem" }}>
            <span className="export-progress-text">{progressLabel(progress)}</span>
          </div>
          <div className="export-progress-track">
            <div id="export-progress-bar" style={{ width: `${Math.round(progress * 100)}%` }} />
          </div>
        </div>
      )}

      {result && (
        <InfoBox kind="success">
          {result.file_name} · {(result.size_bytes / 1024 / 1024).toFixed(1)} MB ·{" "}
          {result.includes_tts ? "con TTS" : "sin TTS"}
          <a
            href={exportDownloadUrl(result.file_name)}
            download={result.file_name}
            className="download-final-link"
          >
            Descargar video final
          </a>
        </InfoBox>
      )}
      {error && <InfoBox kind="error">Error: {error}</InfoBox>}
    </Section>
  );
}
