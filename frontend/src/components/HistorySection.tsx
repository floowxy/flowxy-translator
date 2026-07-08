import { useEffect, useState } from "react";
import { api } from "../api";
import type { HistoryEntry } from "../types";

interface Props {
  /** Cambia para forzar recarga del historial (p.ej. tras procesar un archivo). */
  refreshKey: number;
  onRestore: (entry: HistoryEntry) => void;
}

export function HistorySection({ refreshKey, onRestore }: Props) {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    let cancelled = false;
    api
      .history()
      .then((data) => {
        if (!cancelled) setEntries(data.entries ?? []);
      })
      .catch(() => {
        // Historial no disponible — no es crítico
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  async function handleDelete(fileName: string) {
    try {
      await api.deleteFile(fileName);
      setEntries((prev) => prev.filter((e) => e.file_name !== fileName));
    } catch {
      // el próximo refresh lo reconciliará
    }
  }

  if (entries.length === 0) return null;

  return (
    <div className="container" style={{ paddingBottom: 0 }}>
      <section className="card" style={{ padding: "1.5rem" }}>
        <h2 style={{ marginBottom: "1.25rem", fontSize: "1.1rem" }}>
          📂 Videos Procesados Anteriormente
        </h2>
        <div className="history-list">
          {entries.map((entry) => (
            <div
              key={entry.file_name}
              className="history-entry"
              onClick={() => onRestore(entry)}
            >
              <div className="history-icon">{entry.media_type === "video" ? "🎬" : "🎵"}</div>
              <div className="history-body">
                <div className="history-title">{entry.file_name}</div>
                <div className="history-meta">
                  {entry.language.toUpperCase()} · {Math.round(entry.duration / 60)} min ·{" "}
                  {entry.segments} seg
                  {entry.translations.length > 0 && ` · ✓ ${entry.translations.join(", ")}`}
                </div>
                {entry.text_preview && (
                  <div className="history-preview">"{entry.text_preview}…"</div>
                )}
              </div>
              <div className="history-actions">
                <span className="history-restore-hint">Restaurar →</span>
                <button
                  className="delete-btn"
                  title="Borrar archivo"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(entry.file_name);
                  }}
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
