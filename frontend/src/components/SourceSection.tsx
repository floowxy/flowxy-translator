import { useRef, useState } from "react";
import type { DragEvent } from "react";
import { api } from "../api";
import { tracked } from "../busy";
import { InfoBox } from "./InfoBox";
import { Section } from "./Section";
import type { MediaType } from "../types";

interface Props {
  onMediaReady: (fileName: string, mediaType: MediaType) => void;
}

/** Fuente única: URL de YouTube o archivo local — es la misma decisión. */
export function SourceSection({ onMediaReady }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [url, setUrl] = useState("");
  const [downloadVideo, setDownloadVideo] = useState(true);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [info, setInfo] = useState<{ kind: "success" | "error" | "warning"; text: string } | null>(null);

  async function handleDownload() {
    if (!url.trim()) {
      setInfo({ kind: "warning", text: "Ingresa una URL de YouTube" });
      return;
    }

    setLoading(true);
    setInfo(null);
    try {
      const data = await tracked(api.download(url.trim(), downloadVideo));
      onMediaReady(data.file_name, data.media_type);
      setInfo({
        kind: "success",
        text:
          `${data.file_name} · ${Math.round(data.duration)}s · ` +
          `${(data.size_bytes / 1024 / 1024).toFixed(1)} MB · ${data.media_type}`,
      });
    } catch (e) {
      setInfo({ kind: "error", text: `Error al descargar: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  }

  async function handleFile(file: File) {
    setInfo(null);
    try {
      const data = await tracked(api.upload(file));
      onMediaReady(data.file_name, data.media_type);
      setInfo({
        kind: "success",
        text: `${data.file_name} · ${(file.size / 1024 / 1024).toFixed(1)} MB · ${data.media_type}`,
      });
    } catch (e) {
      setInfo({ kind: "error", text: `Error al subir: ${(e as Error).message}` });
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  return (
    <Section
      step={1}
      title="Fuente"
      desc="Pega un enlace de YouTube o usa un archivo de video/audio de tu equipo."
    >
      <div className="input-group">
        <input
          type="text"
          placeholder="https://www.youtube.com/watch?v=..."
          className="input-field"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleDownload()}
        />
        <button
          className={`btn btn-primary${loading ? " loading" : ""}`}
          style={{ flexShrink: 0 }}
          disabled={loading}
          onClick={handleDownload}
        >
          Descargar
        </button>
      </div>
      <div className="checkbox-group">
        <label>
          <input
            type="checkbox"
            checked={downloadVideo}
            onChange={(e) => setDownloadVideo(e.target.checked)}
          />
          <span>Video completo — necesario para subtítulos quemados y el reproductor</span>
        </label>
      </div>

      <div className="source-divider">o archivo local</div>

      <div
        className={`drop-zone${dragOver ? " drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        Arrastra un MP4 · MKV · WebM · MP3 — o{" "}
        <span className="drop-zone-cta">selecciona un archivo</span>
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*,audio/*,.mkv,.mov,.webm,.avi,.flac"
          style={{ display: "none" }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
      </div>

      {info && <InfoBox kind={info.kind}>{info.text}</InfoBox>}
    </Section>
  );
}
