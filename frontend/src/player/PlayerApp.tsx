import { useCallback, useEffect, useRef, useState } from "react";
import { api, mediaUrl } from "../api";
import type { SubtitleSegment } from "../types";

type SubtitleMode = "none" | "original" | "translated" | "bilingual";

interface Display {
  segIndex: number;
  wordIndex: number;
}

/** Búsqueda binaria del segmento activo (segments ordenados por start). */
function findSegmentIndex(segments: SubtitleSegment[], time: number): number {
  let left = 0;
  let right = segments.length - 1;
  while (left <= right) {
    const mid = (left + right) >> 1;
    const seg = segments[mid];
    if (time >= seg.start && time <= seg.end) return mid;
    if (time < seg.start) right = mid - 1;
    else left = mid + 1;
  }
  return -1;
}

export default function PlayerApp() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videos, setVideos] = useState<string[]>([]);
  const [selected, setSelected] = useState("");
  const [segments, setSegments] = useState<SubtitleSegment[]>([]);
  const [mode, setMode] = useState<SubtitleMode>("translated");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [display, setDisplay] = useState<Display>({ segIndex: -1, wordIndex: -1 });

  // ── Carga inicial: lista de videos procesados ────────────────────────────
  useEffect(() => {
    (async () => {
      let names: string[] = [];
      try {
        const data = await api.history();
        names = (data.entries ?? [])
          .filter((e) => e.media_type === "video")
          .map((e) => e.file_name);
      } catch {
        // Historial no disponible — fallback a localStorage
      }

      const lastFile = localStorage.getItem("lastDownloadedFile");
      if (names.length === 0 && lastFile && localStorage.getItem("lastMediaType") === "video") {
        names = [lastFile];
      }

      if (names.length === 0) {
        setStatus("No hay videos disponibles. Descarga un video primero desde la página principal.");
        return;
      }

      setVideos(names);
      const initial = lastFile && names.includes(lastFile) ? lastFile : names[0];
      setSelected(initial);
    })();
  }, []);

  // ── Cargar subtítulos al cambiar de video ────────────────────────────────
  const loadSubtitles = useCallback(async (fileName: string) => {
    setError(null);
    setStatus("Cargando subtítulos...");
    setDisplay({ segIndex: -1, wordIndex: -1 });
    try {
      const data = await api.subtitles(fileName);
      const segs = [...data.segments].sort((a, b) => a.start - b.start);
      setSegments(segs);
      setStatus(`Subtítulos cargados: ${segs.length} segmentos (${data.language})`);
    } catch {
      setSegments([]);
      setStatus("No se encontraron subtítulos. Transcribe el video primero en la página principal.");
    }
  }, []);

  useEffect(() => {
    if (!selected) return;
    localStorage.setItem("lastDownloadedFile", selected);
    localStorage.setItem("lastMediaType", "video");
    loadSubtitles(selected);
  }, [selected, loadSubtitles]);

  // ── Sincronización de subtítulos: rAF, solo re-renderiza cuando cambia ───
  useEffect(() => {
    if (mode === "none" || segments.length === 0) return;

    let raf: number;
    const tick = () => {
      const video = videoRef.current;
      if (video) {
        const t = video.currentTime;
        const segIndex = findSegmentIndex(segments, t);
        let wordIndex = -1;

        if (mode === "original" && segIndex >= 0) {
          const words = segments[segIndex].words ?? [];
          wordIndex = words.findIndex((w) => t >= w.start && t <= w.end);
        }

        setDisplay((prev) =>
          prev.segIndex === segIndex && prev.wordIndex === wordIndex
            ? prev
            : { segIndex, wordIndex },
        );
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [segments, mode]);

  const seg = display.segIndex >= 0 ? segments[display.segIndex] : null;
  const showSubtitle = mode !== "none" && seg !== null;

  function handleVideoError() {
    const code = videoRef.current?.error?.code;
    const messages: Record<number, string> = {
      1: "Carga del video abortada",
      2: "Error de red",
      3: "Error de decodificación",
      4: "Formato de video no soportado",
    };
    setError(`Error de video: ${messages[code ?? 0] ?? "Error desconocido"}`);
  }

  return (
    <>
      <header>
        <h1>
          <span className="wordmark-accent">flowxy</span> reproductor
        </h1>
      </header>

      <div className="video-container">
        <div className="video-wrapper">
          <video
            ref={videoRef}
            key={selected}
            src={selected ? mediaUrl(selected, "video") : undefined}
            controls
            onError={selected ? handleVideoError : undefined}
          />

          <div className="subtitle-container">
            {showSubtitle && seg && (
              <div className={`subtitle${mode === "bilingual" ? " bilingual" : ""}`}>
                {mode === "bilingual" ? (
                  <>
                    <span className="subtitle-original">{seg.text}</span>
                    <span className="subtitle-translated">{seg.translated ?? seg.text}</span>
                  </>
                ) : mode === "translated" ? (
                  seg.translated ?? seg.text
                ) : (seg.words?.length ?? 0) > 0 ? (
                  seg.words.map((w, i) => (
                    <span key={i} className={i === display.wordIndex ? "word-highlight" : ""}>
                      {w.word}{" "}
                    </span>
                  ))
                ) : (
                  seg.text
                )}
              </div>
            )}
          </div>
        </div>

        <div className="controls-panel">
          <div className="control-group">
            <label htmlFor="videoSelect">Video</label>
            <select
              id="videoSelect"
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              {videos.length === 0 && <option value="">Selecciona un video...</option>}
              {videos.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>

            <label htmlFor="subtitleMode">Subtítulos</label>
            <select
              id="subtitleMode"
              value={mode}
              onChange={(e) => setMode(e.target.value as SubtitleMode)}
            >
              <option value="none">Sin subtítulos</option>
              <option value="original">Original</option>
              <option value="translated">Traducido</option>
              <option value="bilingual">Bilingüe</option>
            </select>

            <button className="btn-back" onClick={() => (location.href = "/")}>
              ← Volver al inicio
            </button>
          </div>

          {status && <div className="status">{status}</div>}
          {error && <div className="error">{error}</div>}
        </div>
      </div>
    </>
  );
}
