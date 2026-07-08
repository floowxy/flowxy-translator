import { useCallback, useState } from "react";
import { api } from "./api";
import { Header } from "./components/Header";
import { HistorySection } from "./components/HistorySection";
import { UploadSection } from "./components/UploadSection";
import { DownloadSection } from "./components/DownloadSection";
import { MediaSection } from "./components/MediaSection";
import { TranscribeSection } from "./components/TranscribeSection";
import { TranslateSection } from "./components/TranslateSection";
import { ExportSection } from "./components/ExportSection";
import { VideoExportSection } from "./components/VideoExportSection";
import type { HistoryEntry, MediaType, TranscriptionResult, TranslationResult } from "./types";

export default function App() {
  const [currentFile, setCurrentFile] = useState<string | null>(null);
  const [mediaType, setMediaType] = useState<MediaType | null>(null);
  const [transcription, setTranscription] = useState<TranscriptionResult | null>(null);
  const [translation, setTranslation] = useState<TranslationResult | null>(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const [footerGpu, setFooterGpu] = useState("Cargando...");

  const handleMediaReady = useCallback((fileName: string, type: MediaType) => {
    setCurrentFile(fileName);
    setMediaType(type);
    setTranscription(null);
    setTranslation(null);

    if (type === "video") {
      // El reproductor (/player) usa esto para preseleccionar el último video
      localStorage.setItem("lastDownloadedFile", fileName);
      localStorage.setItem("lastMediaType", "video");
    }
  }, []);

  const handleTranscribed = useCallback((result: TranscriptionResult) => {
    setTranscription(result);
    setTranslation(null);
    setHistoryRefresh((n) => n + 1);
  }, []);

  const handleTranslated = useCallback((result: TranslationResult) => {
    setTranslation(result);
    setHistoryRefresh((n) => n + 1);
  }, []);

  /** Restaura una sesión del historial — transcripción/traducción llegan de caché en ms. */
  const handleRestore = useCallback(async (entry: HistoryEntry) => {
    handleMediaReady(entry.file_name, entry.media_type);

    try {
      const data = await api.transcribe(entry.file_name, null, crypto.randomUUID());
      setTranscription(data);
    } catch {
      return; // sin transcripción no hay nada más que restaurar
    }

    if (entry.translations.length > 0) {
      const lang = entry.translations.includes("es") ? "es" : entry.translations[0];
      try {
        const data = await api.translateTranscript(entry.file_name, lang, crypto.randomUUID());
        setTranslation(data);
      } catch {
        // traducción no restaurable — el usuario puede retraducir
      }
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [handleMediaReady]);

  return (
    <>
      <Header onGpuText={setFooterGpu} />

      <HistorySection refreshKey={historyRefresh} onRestore={handleRestore} />

      <div className="container">
        <UploadSection onMediaReady={handleMediaReady} />
        <DownloadSection onMediaReady={handleMediaReady} />
        <MediaSection
          fileName={currentFile}
          mediaType={mediaType}
          showPlayerLink={mediaType === "video" && transcription !== null}
        />
        <TranscribeSection
          fileName={currentFile}
          transcription={transcription}
          onTranscribed={handleTranscribed}
        />
        <TranslateSection
          fileName={currentFile}
          totalSegments={transcription?.segments.length ?? 0}
          canTranslate={transcription !== null}
          translation={translation}
          onTranslated={handleTranslated}
        />
        <ExportSection
          fileName={currentFile}
          hasTranslation={translation !== null}
          enabled={translation !== null}
        />
        <VideoExportSection
          fileName={currentFile}
          enabled={translation !== null && mediaType === "video"}
        />
      </div>

      <footer>
        <p style={{ lineHeight: 1.8 }}>
          Powered by <strong>Whisper</strong> + <strong>NLLB-200</strong> +{" "}
          <strong>Edge-TTS</strong>
          <br />
          GPU: <span style={{ fontWeight: 600 }}>{footerGpu}</span>
        </p>
        <p style={{ marginTop: "1rem", fontSize: "0.8rem", opacity: 0.7 }}>
          Made with ❤️ by flowxy
        </p>
      </footer>
    </>
  );
}
