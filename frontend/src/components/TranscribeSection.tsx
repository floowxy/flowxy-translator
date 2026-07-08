import { useState } from "react";
import { api, pollProgress } from "../api";
import { tracked } from "../busy";
import { InfoBox } from "./InfoBox";
import { LANGUAGES } from "../types";
import type { TranscriptionResult } from "../types";

interface Props {
  fileName: string | null;
  transcription: TranscriptionResult | null;
  onTranscribed: (result: TranscriptionResult) => void;
}

export function TranscribeSection({ fileName, transcription, onTranscribed }: Props) {
  const [language, setLanguage] = useState("");
  const [loading, setLoading] = useState(false);
  const [progressText, setProgressText] = useState<string | null>(null);
  const [info, setInfo] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  async function handleTranscribe() {
    if (!fileName) return;

    const taskId = crypto.randomUUID();
    setLoading(true);
    setInfo(null);
    setProgressText("Transcribiendo... 0%");

    const stopPolling = pollProgress(taskId, (p) => {
      setProgressText(`Transcribiendo... ${Math.round(p * 100)}%`);
    });

    try {
      const data = await tracked(api.transcribe(fileName, language || null, taskId));
      onTranscribed(data);
      setInfo({
        kind: "success",
        text:
          `Idioma: ${data.language} | Duración: ${Math.round(data.duration)}s | ` +
          `Segmentos: ${data.segments.length} | Caracteres: ${data.text.length}`,
      });
    } catch (e) {
      setInfo({ kind: "error", text: `Error: ${(e as Error).message}` });
    } finally {
      stopPolling();
      setLoading(false);
      setProgressText(null);
    }
  }

  return (
    <section className="card">
      <h2>📝 3. Transcripción (Whisper AI)</h2>
      <p className="section-desc">
        Convierte el audio a texto usando el modelo Whisper de OpenAI con aceleración GPU.
      </p>
      <div className="button-group" style={{ gap: "1rem", marginBottom: "1.5rem" }}>
        <button
          className={`btn btn-secondary${loading ? " loading" : ""}`}
          style={{ flex: 2, fontSize: "1rem", padding: "1rem" }}
          disabled={!fileName || loading}
          onClick={handleTranscribe}
        >
          🎤 TRANSCRIBIR AUDIO
        </button>
        <select
          className="select-field"
          style={{ flex: 1 }}
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        >
          <option value="">Auto-detectar idioma</option>
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      </div>
      <textarea
        rows={10}
        placeholder="La transcripción aparecerá aquí..."
        className="text-area"
        readOnly
        value={progressText ?? transcription?.text ?? ""}
      />
      {info && <InfoBox kind={info.kind}>{info.text}</InfoBox>}
    </section>
  );
}
