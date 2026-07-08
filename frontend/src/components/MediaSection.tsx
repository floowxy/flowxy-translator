import { mediaUrl } from "../api";
import { Section } from "./Section";
import type { MediaType } from "../types";

interface Props {
  fileName: string | null;
  mediaType: MediaType | null;
  showPlayerLink: boolean;
}

export function MediaSection({ fileName, mediaType, showPlayerLink }: Props) {
  const src = fileName && mediaType ? mediaUrl(fileName, mediaType) : null;

  return (
    <Section step={2} title="Reproducir">
      {!src ? (
        <div className="media-placeholder">
          El contenido aparecerá aquí cuando descargues o subas un archivo
        </div>
      ) : mediaType === "video" ? (
        // key=src fuerza recarga del elemento al cambiar de archivo
        <video key={src} src={src} controls className="audio-player" />
      ) : (
        <audio key={src} src={src} controls className="audio-player" />
      )}

      {showPlayerLink && (
        <div className="info-box player-link-box">
          <a href="/player" target="_blank" rel="noopener noreferrer" className="player-link">
            Abrir reproductor con subtítulos en tiempo real
            <span>→</span>
          </a>
        </div>
      )}
    </Section>
  );
}
