import { useState } from "react";
import { api, pollProgress } from "../api";
import { tracked } from "../busy";
import { InfoBox } from "./InfoBox";
import { Section } from "./Section";
import { LANGUAGES } from "../types";
import type { TranslationResult } from "../types";

interface Props {
  fileName: string | null;
  totalSegments: number;
  canTranslate: boolean;
  translation: TranslationResult | null;
  onTranslated: (result: TranslationResult) => void;
}

export function TranslateSection({
  fileName,
  totalSegments,
  canTranslate,
  translation,
  onTranslated,
}: Props) {
  const [targetLang, setTargetLang] = useState("es");
  const [loading, setLoading] = useState(false);
  const [progressText, setProgressText] = useState<string | null>(null);
  const [info, setInfo] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  async function runTranslation() {
    if (!fileName) return;

    const taskId = crypto.randomUUID();
    setLoading(true);
    setInfo(null);
    setProgressText("Traduciendo… 0%");

    const stopPolling = pollProgress(taskId, (p) => {
      const pct = Math.round(p * 100);
      const done = Math.round(p * totalSegments);
      setProgressText(
        totalSegments
          ? `Traduciendo… ${pct}% (${done}/${totalSegments} segmentos)`
          : `Traduciendo… ${pct}%`,
      );
    });

    try {
      const data = await tracked(api.translateTranscript(fileName, targetLang, taskId));
      onTranslated(data);
      setInfo({
        kind: "success",
        text: `${data.source_lang} → ${data.target_lang} · ${data.segments.length} segmentos`,
      });
    } catch (e) {
      setInfo({ kind: "error", text: `Error al traducir: ${(e as Error).message}` });
    } finally {
      stopPolling();
      setLoading(false);
      setProgressText(null);
    }
  }

  async function handleRetranslate() {
    if (!fileName) return;
    try {
      await api.clearTranslationCache(fileName);
    } catch (e) {
      setInfo({ kind: "error", text: `Error limpiando caché: ${(e as Error).message}` });
      return;
    }
    await runTranslation();
  }

  return (
    <Section
      step={4}
      title="Traducción"
      desc="NLLB-200 traduce por grupos de oraciones completas, con contexto entre grupos."
    >
      <div className="button-group" style={{ marginBottom: "1rem" }}>
        <button
          className={`btn btn-primary${loading ? " loading" : ""}`}
          style={{ flex: 2 }}
          disabled={!canTranslate || loading}
          onClick={runTranslation}
        >
          Traducir
        </button>
        <select
          className="select-field"
          style={{ flex: 1, width: "auto" }}
          value={targetLang}
          onChange={(e) => setTargetLang(e.target.value)}
        >
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              → {l.label}
            </option>
          ))}
        </select>
        <button
          className="btn btn-tertiary"
          title="Borra la caché y vuelve a traducir desde cero"
          disabled={!translation || loading}
          onClick={handleRetranslate}
        >
          Retraducir
        </button>
      </div>
      <textarea
        rows={10}
        placeholder="La traducción aparecerá aquí"
        className="text-area"
        readOnly
        value={progressText ?? translation?.translated_text ?? ""}
      />
      {info && <InfoBox kind={info.kind}>{info.text}</InfoBox>}
    </Section>
  );
}
