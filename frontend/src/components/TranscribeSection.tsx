import { useState } from "react";
import { api, pollProgress } from "../api";
import { tracked } from "../busy";
import { InfoBox } from "./InfoBox";
import { Section } from "./Section";
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
    setProgressText("Transcribiendo… 0%");

    const stopPolling = pollProgress(taskId, (p) => {
      setProgressText(`Transcribiendo… ${Math.round(p * 100)}%`);
    });

    try {
      const data = await tracked(api.transcribe(fileName, language || null, taskId));
      onTranscribed(data);
      setInfo({
        kind: "success",
        text:
          `Idioma ${data.language} · ${Math.round(data.duration)}s · ` +
          `${data.segments.length} segmentos · ${data.text.length.toLocaleString()} caracteres`,
      });
    } catch (e) {
      setInfo({ kind: "error", text: `Error al transcribir: ${(e as Error).message}` });
    } finally {
      stopPolling();
      setLoading(false);
      setProgressText(null);
    }
  }

  return (
    <Section
      step={3}
      title="Transcripción"
      desc="Whisper convierte el audio en texto con timestamps por palabra, acelerado por GPU."
    >
      <div className="button-group" style={{ marginBottom: "1rem" }}>
        <button
          className={`btn btn-primary${loading ? " loading" : ""}`}
          style={{ flex: 2 }}
          disabled={!fileName || loading}
          onClick={handleTranscribe}
        >
          Transcribir audio
        </button>
        <select
          className="select-field"
          style={{ flex: 1, width: "auto" }}
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        >
          <option value="">Detectar idioma</option>
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      </div>
      <textarea
        rows={10}
        placeholder="La transcripción aparecerá aquí"
        className="text-area"
        readOnly
        value={progressText ?? transcription?.text ?? ""}
      />
      {info && <InfoBox kind={info.kind}>{info.text}</InfoBox>}
    </Section>
  );
}
