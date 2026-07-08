import { useState } from "react";
import { api, pollProgress } from "../api";
import { tracked } from "../busy";
import { InfoBox } from "./InfoBox";
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
    setProgressText("Traduciendo... 0%");

    const stopPolling = pollProgress(taskId, (p) => {
      const pct = Math.round(p * 100);
      const done = Math.round(p * totalSegments);
      setProgressText(
        totalSegments
          ? `Traduciendo... ${pct}% (${done}/${totalSegments} segmentos)`
          : `Traduciendo... ${pct}%`,
      );
    });

    try {
      const data = await tracked(api.translateTranscript(fileName, targetLang, taskId));
      onTranslated(data);
      setInfo({
        kind: "success",
        text: `De ${data.source_lang} a ${data.target_lang} | Segmentos traducidos: ${data.segments.length}`,
      });
    } catch (e) {
      setInfo({ kind: "error", text: `Error: ${(e as Error).message}` });
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
    <section className="card">
      <h2>🌐 4. Traducción (NLLB AI)</h2>
      <p className="section-desc">
        Traduce el texto transcrito a cualquier idioma usando el modelo NLLB-200 de Meta con
        aceleración GPU.
      </p>
      <div className="button-group" style={{ gap: "1rem", marginBottom: "1.5rem" }}>
        <button
          className={`btn btn-secondary${loading ? " loading" : ""}`}
          style={{ flex: 2, fontSize: "1rem", padding: "1rem" }}
          disabled={!canTranslate || loading}
          onClick={runTranslation}
        >
          🌍 TRADUCIR
        </button>
        <button
          className="btn btn-tertiary"
          title="Borra la caché y retraduce con el motor DP mejorado"
          style={{ fontSize: "0.8rem", padding: "0.6rem 1rem", whiteSpace: "nowrap" }}
          disabled={!translation || loading}
          onClick={handleRetranslate}
        >
          ↺ Retranslate
        </button>
        <select
          className="select-field"
          style={{ flex: 1 }}
          value={targetLang}
          onChange={(e) => setTargetLang(e.target.value)}
        >
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              → {l.label}
            </option>
          ))}
        </select>
      </div>
      <textarea
        rows={10}
        placeholder="La traducción aparecerá aquí..."
        className="text-area"
        readOnly
        value={progressText ?? translation?.translated_text ?? ""}
      />
      {info && <InfoBox kind={info.kind}>{info.text}</InfoBox>}
    </section>
  );
}
