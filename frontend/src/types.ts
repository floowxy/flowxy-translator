// Tipos compartidos — contrato con la API del backend FastAPI

export type MediaType = "audio" | "video";

export interface Word {
  word: string;
  start: number;
  end: number;
}

export interface Segment {
  id?: number;
  start: number;
  end: number;
  text: string;
  words?: Word[];
  translated_text?: string;
}

export interface TranscriptionResult {
  status: string;
  text: string;
  segments: Segment[];
  language: string;
  duration: number;
}

export interface TranslationResult {
  status: string;
  segments: Segment[];
  translated_text: string;
  source_lang: string;
  target_lang: string;
}

export interface DownloadResult {
  status: string;
  file_name: string;
  title: string;
  duration: number;
  size_bytes: number;
  media_type: MediaType;
}

export interface UploadResult {
  status: string;
  file_name: string;
  size_bytes: number;
  media_type: MediaType;
}

export interface HistoryEntry {
  file_name: string;
  media_type: MediaType;
  language: string;
  duration: number;
  text_preview: string;
  segments: number;
  translations: string[];
}

export interface ExportResult {
  status: string;
  file_name: string;
  format: string;
  path: string;
}

export interface VideoExportResult {
  status: string;
  message: string;
  file_name: string;
  file_path: string;
  size_bytes: number;
  includes_tts: boolean;
}

export interface GpuStatsResponse {
  cuda: { available: boolean };
  gpu: { name?: string; memory?: { percent: number } };
}

export interface SubtitleSegment {
  start: number;
  end: number;
  text: string;
  words: Word[];
  translated?: string;
}

export interface SubtitlesResponse {
  status: string;
  file_name: string;
  language: string;
  segments: SubtitleSegment[];
}

export type ExportFormat = "srt" | "vtt" | "txt" | "json";

// Idiomas soportados en la UI (subset de NLLB_LANG_CODES del backend)
export const LANGUAGES: { code: string; label: string }[] = [
  { code: "en", label: "Inglés" },
  { code: "es", label: "Español" },
  { code: "fr", label: "Francés" },
  { code: "de", label: "Alemán" },
  { code: "it", label: "Italiano" },
  { code: "pt", label: "Portugués" },
  { code: "ja", label: "Japonés" },
  { code: "zh", label: "Chino" },
];
