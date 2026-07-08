import { mediaUrl } from "../api";
import type { MediaType } from "../types";

interface Props {
  fileName: string | null;
  mediaType: MediaType | null;
  showPlayerLink: boolean;
}

export function MediaSection({ fileName, mediaType, showPlayerLink }: Props) {
  const src = fileName && mediaType ? mediaUrl(fileName, mediaType) : null;

  return (
    <section className="card">
      <h2>🎵 2. Reproducir Audio/Video</h2>
      <p className="section-desc">
        Una vez descargado, podrás reproducir el contenido aquí o en el reproductor con subtítulos
        en tiempo real.
      </p>

      {/* key=src fuerza recarga del elemento al cambiar de archivo */}
      {src && mediaType === "video" ? (
        <video
          key={src}
          src={src}
          controls
          className="audio-player"
          style={{ maxWidth: "100%", borderRadius: "var(--radius-md)" }}
        />
      ) : (
        <audio key={src ?? "empty"} src={src ?? undefined} controls className="audio-player" />
      )}

      {showPlayerLink && (
        <div className="info-box player-link-box">
          <a href="/player" target="_blank" rel="noopener noreferrer" className="player-link">
            <span style={{ fontSize: "1.5em" }}>🎬</span>
            ABRIR REPRODUCTOR CON SUBTÍTULOS EN TIEMPO REAL
            <span style={{ fontSize: "1.2em" }}>→</span>
          </a>
        </div>
      )}
    </section>
  );
}
