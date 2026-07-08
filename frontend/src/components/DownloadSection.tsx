import { useState } from "react";
import { api } from "../api";
import { tracked } from "../busy";
import { InfoBox } from "./InfoBox";
import type { MediaType } from "../types";

interface Props {
  onMediaReady: (fileName: string, mediaType: MediaType) => void;
}

export function DownloadSection({ onMediaReady }: Props) {
  const [url, setUrl] = useState("");
  const [downloadVideo, setDownloadVideo] = useState(true);
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState<{ kind: "success" | "error" | "warning"; text: string } | null>(null);

  async function handleDownload() {
    if (!url.trim()) {
      setInfo({ kind: "warning", text: "Por favor ingresa una URL" });
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
          `Archivo: ${data.file_name} | Duración: ${Math.round(data.duration)}s | ` +
          `Tamaño: ${(data.size_bytes / 1024 / 1024).toFixed(2)} MB | Tipo: ${data.media_type}`,
      });
    } catch (e) {
      setInfo({ kind: "error", text: `Error: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <h2>📥 1. Descargar Video de YouTube</h2>
      <p className="section-desc">
        Pega el enlace de cualquier video de YouTube para comenzar el proceso de transcripción y
        traducción.
      </p>
      <div className="input-group">
        <input
          type="text"
          placeholder="https://www.youtube.com/watch?v=..."
          className="input-field"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleDownload()}
        />
      </div>
      <div className="checkbox-group" style={{ margin: "1.5rem 0" }}>
        <label>
          <input
            type="checkbox"
            checked={downloadVideo}
            onChange={(e) => setDownloadVideo(e.target.checked)}
          />
          <span style={{ fontSize: "1rem", fontWeight: 600 }}>
            ✅ Descargar VIDEO COMPLETO (recomendado para ver con subtítulos)
          </span>
        </label>
      </div>
      <button
        className={`btn btn-primary${loading ? " loading" : ""}`}
        style={{ width: "100%", fontSize: "1rem", padding: "1.2rem" }}
        disabled={loading}
        onClick={handleDownload}
      >
        ⬇️ DESCARGAR VIDEO
      </button>
      {info && <InfoBox kind={info.kind}>{info.text}</InfoBox>}
    </section>
  );
}
