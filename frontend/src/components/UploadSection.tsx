import { useRef, useState } from "react";
import type { DragEvent } from "react";
import { api } from "../api";
import { tracked } from "../busy";
import { InfoBox } from "./InfoBox";
import type { MediaType } from "../types";

interface Props {
  onMediaReady: (fileName: string, mediaType: MediaType) => void;
}

export function UploadSection({ onMediaReady }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [info, setInfo] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  async function handleFile(file: File) {
    setInfo(null);
    const sizeMB = (file.size / 1024 / 1024).toFixed(1);
    try {
      const data = await tracked(api.upload(file));
      onMediaReady(data.file_name, data.media_type);
      setInfo({ kind: "success", text: `✓ ${data.file_name} — ${sizeMB} MB` });
    } catch (e) {
      setInfo({ kind: "error", text: `Error: ${(e as Error).message}` });
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  return (
    <section className="card" style={{ padding: "1.5rem" }}>
      <h2 style={{ fontSize: "1.05rem", marginBottom: "0.6rem" }}>
        📁 Subir Archivo Local{" "}
        <span style={{ fontSize: "0.8rem", opacity: 0.6, fontWeight: 400 }}>
          (alternativa a YouTube)
        </span>
      </h2>
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
        Arrastra un MP4 · MKV · WebM · MP3 aquí — o{" "}
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
    </section>
  );
}
