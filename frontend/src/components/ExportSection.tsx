import { useState } from "react";
import { api, triggerDownload } from "../api";
import { InfoBox } from "./InfoBox";
import type { ExportFormat } from "../types";

interface Props {
  fileName: string | null;
  hasTranslation: boolean;
  enabled: boolean;
}

const FORMATS: { format: ExportFormat; label: string }[] = [
  { format: "srt", label: "📄 Exportar SRT" },
  { format: "vtt", label: "📄 Exportar VTT" },
  { format: "txt", label: "📄 Exportar TXT" },
  { format: "json", label: "📄 Exportar JSON" },
];

export function ExportSection({ fileName, hasTranslation, enabled }: Props) {
  const [bilingual, setBilingual] = useState(false);
  const [info, setInfo] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  async function handleExport(format: ExportFormat) {
    if (!fileName) return;
    setInfo(null);
    try {
      // JSON siempre incluye todo, sin variante bilingüe
      const useBilingual = format === "json" ? false : bilingual;
      const data = await api.exportFile(fileName, format, hasTranslation, useBilingual);
      triggerDownload(data.file_name);
      setInfo({ kind: "success", text: `✓ Exportado: ${data.file_name}` });
    } catch (e) {
      setInfo({ kind: "error", text: `Error exportando: ${(e as Error).message}` });
    }
  }

  return (
    <section className="card">
      <h2>💾 5. Exportar Subtítulos</h2>
      <p className="section-desc">
        Descarga los subtítulos en diferentes formatos para usar en reproductores de video o
        editores.
      </p>
      <div className="export-buttons">
        {FORMATS.map(({ format, label }) => (
          <button
            key={format}
            className="btn btn-tertiary"
            disabled={!enabled}
            onClick={() => handleExport(format)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="checkbox-group">
        <label>
          <input
            type="checkbox"
            checked={bilingual}
            onChange={(e) => setBilingual(e.target.checked)}
          />
          <span style={{ fontWeight: 600 }}>Bilingüe (original + traducción)</span>
        </label>
      </div>
      {info && <InfoBox kind={info.kind}>{info.text}</InfoBox>}
    </section>
  );
}
