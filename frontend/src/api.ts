// Cliente HTTP tipado — única capa que habla con el backend FastAPI.
// Rutas relativas: en dev las proxea Vite (:5173 → :9000), en producción
// el frontend se sirve desde el mismo origen que la API.

import type {
  ConfigOverrides,
  DownloadResult,
  ExportFormat,
  ExportResult,
  GpuStatsResponse,
  HistoryEntry,
  MediaType,
  PresetName,
  SettingsResponse,
  SubtitlesResponse,
  SystemSpecs,
  TranscriptionResult,
  TranslationResult,
  UploadResult,
  VideoExportResult,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, init);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || `HTTP ${resp.status}`);
  }
  return data as T;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  gpuStats: () => request<GpuStatsResponse>("/api/gpu-stats"),

  progress: (taskId: string) =>
    request<{ task_id: string; progress: number }>(`/api/progress/${taskId}`),

  download: (url: string, downloadVideo: boolean) =>
    post<DownloadResult>("/api/download", { url, download_video: downloadVideo }),

  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<UploadResult>("/api/upload", { method: "POST", body: formData });
  },

  transcribe: (fileName: string, language: string | null, taskId: string) =>
    post<TranscriptionResult>("/api/transcribe", {
      file_name: fileName,
      language,
      task_id: taskId,
    }),

  translateTranscript: (fileName: string, targetLang: string, taskId: string) =>
    post<TranslationResult>("/api/translate-transcript", {
      file_name: fileName,
      target_lang: targetLang,
      task_id: taskId,
    }),

  exportFile: (fileName: string, format: ExportFormat, useTranslation: boolean, bilingual: boolean) =>
    post<ExportResult>("/api/export", {
      file_name: fileName,
      format,
      use_translation: useTranslation,
      bilingual,
    }),

  exportVideo: (fileName: string, includeTts: boolean, taskId: string) =>
    post<VideoExportResult>("/api/export-video", {
      file_name: fileName,
      include_tts: includeTts,
      task_id: taskId,
    }),

  history: () => request<{ entries: HistoryEntry[] }>("/api/history"),

  deleteFile: (fileName: string) =>
    request<{ status: string; deleted: string }>(
      `/api/files/${encodeURIComponent(fileName)}`,
      { method: "DELETE" },
    ),

  clearTranslationCache: (fileName: string) =>
    request<{ status: string; cleared: string }>(
      `/api/cache/translation/${encodeURIComponent(fileName)}`,
      { method: "DELETE" },
    ),

  subtitles: (fileName: string) =>
    request<SubtitlesResponse>(`/api/subtitles/${encodeURIComponent(fileName)}`),

  systemSpecs: () => request<SystemSpecs>("/api/system-specs"),

  getSettings: () => request<SettingsResponse>("/api/settings"),

  saveSettings: (preset: PresetName, overrides: ConfigOverrides) =>
    post<SettingsResponse>("/api/settings", { preset, overrides }),
};

export function mediaUrl(fileName: string, mediaType: MediaType): string {
  const prefix = mediaType === "video" ? "/video" : "/audio";
  return `${prefix}/${encodeURIComponent(fileName)}`;
}

export function exportDownloadUrl(fileName: string): string {
  return `/api/export/${encodeURIComponent(fileName)}`;
}

/** Dispara la descarga de un archivo exportado en el navegador. */
export function triggerDownload(fileName: string): void {
  const a = document.createElement("a");
  a.href = exportDownloadUrl(fileName);
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/**
 * Polling de progreso de una tarea (0.0–1.0). Devuelve la función para
 * detenerlo — llamarla siempre en el finally de la operación.
 */
export function pollProgress(taskId: string, onProgress: (p: number) => void): () => void {
  const timer = setInterval(async () => {
    try {
      const d = await api.progress(taskId);
      if (d.progress >= 0) onProgress(d.progress);
    } catch {
      // silenciar errores de red durante polling
    }
  }, 400);
  return () => clearInterval(timer);
}
