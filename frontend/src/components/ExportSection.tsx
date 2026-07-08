import { useState } from "react";
import { api, triggerDownload } from "../api";
import { InfoBox } from "./InfoBox";
import { Section } from "./Section";
import type { ExportFormat } from "../types";

interface Props {
  fileName: string | null;
  hasTranslation: boolean;
  enabled: boolean;
}

const FORMATS: ExportFormat[] = ["srt", "vtt", "txt", "json"];

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
      setInfo({ kind: "success", text: `Exportado: ${data.file_name}` });
    } catch (e) {
      setInfo({ kind: "error", text: `Error al exportar: ${(e as Error).message}` });
    }
  }

  return (
    <Section
      step={5}
      title="Exportar subtítulos"
      desc="Descarga la transcripción o traducción para usar en reproductores y editores."
    >
      <div className="export-buttons">
        {FORMATS.map((format) => (
          <button
            key={format}
            className="btn btn-tertiary"
            disabled={!enabled}
            onClick={() => handleExport(format)}
          >
            {format.toUpperCase()}
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
          <span>Bilingüe — original y traducción juntos</span>
        </label>
      </div>
      {info && <InfoBox kind={info.kind}>{info.text}</InfoBox>}
    </Section>
  );
}
