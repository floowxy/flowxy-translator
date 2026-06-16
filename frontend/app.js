// ============================================
// FLOWXY-TRANSLATOR - Frontend App
// Complete workflow: Download → Transcribe → Translate → Export
// ============================================

// El frontend es servido por el propio backend FastAPI, así que las
// rutas relativas siempre apuntan al servidor correcto (host y puerto).
const API_BASE = "";

// DOM Elements
const elements = {
  // Download
  videoUrl: document.getElementById("videoUrl"),
  downloadBtn: document.getElementById("downloadBtn"),
  downloadVideoCheck: document.getElementById("downloadVideoCheck"),
  downloadInfo: document.getElementById("download-info"),

  // Audio/Video
  audioPlayer: document.getElementById("audioPlayer"),
  videoPlayer: document.getElementById("videoPlayer"),
  playerLink: document.getElementById("player-link"),

  // Transcribe
  transcribeBtn: document.getElementById("transcribeBtn"),
  langSelect: document.getElementById("langSelect"),
  transcript: document.getElementById("transcript"),
  transcriptInfo: document.getElementById("transcript-info"),

  // Translate  
  translateBtn: document.getElementById("translateBtn"),
  targetLangSelect: document.getElementById("targetLangSelect"),
  translation: document.getElementById("translation"),
  translationInfo: document.getElementById("translation-info"),

  // Retranslate
  retranslateBtn: document.getElementById("retranslateBtn"),

  // Export
  exportSrtBtn: document.getElementById("exportSrtBtn"),
  exportVttBtn: document.getElementById("exportVttBtn"),
  exportTxtBtn: document.getElementById("exportTxtBtn"),
  exportJsonBtn: document.getElementById("exportJsonBtn"),
  bilingualCheck: document.getElementById("bilingualCheck"),

  // Video Export
  exportVideoBtn: document.getElementById("exportVideoBtn"),
  includeTtsCheck: document.getElementById("includeTtsCheck"),
  exportVideoProgress: document.getElementById("export-video-progress"),
  exportProgressText: document.getElementById("export-progress-text"),
  exportProgressBar: document.getElementById("export-progress-bar"),
  exportVideoInfo: document.getElementById("export-video-info"),

  // Upload local
  dropZone: document.getElementById("dropZone"),
  fileInput: document.getElementById("fileInput"),
  uploadInfo: document.getElementById("upload-info"),

  // GPU & Log (opcional)
  gpuStats: document.getElementById("gpu-stats"),
  footerGpu: document.getElementById("footerGpu"),
  log: document.getElementById("logConsole"),
  clearLogBtn: document.getElementById("clearLogBtn"),
};

// ============================================
// GPU POLLING ADAPTATIVO
// ============================================
let _gpuPollTimer = null;
let _activeTasks = 0;

function _setBusy(delta) {
  _activeTasks = Math.max(0, _activeTasks + delta);
  clearInterval(_gpuPollTimer);
  _gpuPollTimer = setInterval(fetchGPUStats, _activeTasks > 0 ? 4000 : 30000);
}

// State
let state = {
  currentFile: null,
  mediaType: null,  // "audio" or "video"
  transcriptionData: null,
  translationData: null,
  sourceLanguage: null,
  targetLanguage: "es",
};

// ============================================
// UTILITIES
// ============================================

function log(message, type = "info") {
  const timestamp = new Date().toLocaleTimeString();
  const prefix = {
    info: "ℹ️",
    success: "✅",
    error: "❌",
    warning: "⚠️",
  }[type] || "•";

  // Solo log a consola si no hay elemento de log
  if (elements.log) {
    elements.log.textContent += `[${timestamp}] ${prefix} ${message}\n`;
    elements.log.scrollTop = elements.log.scrollHeight;
  }

  // Siempre log a consola del navegador
  console.log(`[${timestamp}] ${prefix} ${message}`);
}

function setButtonLoading(button, loading) {
  if (loading) {
    button.classList.add("loading");
    button.disabled = true;
  } else {
    button.classList.remove("loading");
    button.disabled = false;
  }
}

function showInfo(element, message, type = "info") {
  element.textContent = message;
  element.className = `info-box ${type}`;
  element.classList.remove("hidden");
}

function hideInfo(element) {
  element.classList.add("hidden");
}

// ============================================
// PROGRESS POLLING
// ============================================

function startProgressPolling(taskId, onProgress) {
  return setInterval(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/progress/${taskId}`);
      const d = await r.json();
      if (d.progress >= 0) onProgress(d.progress);
    } catch {
      // silenciar errores de red durante polling
    }
  }, 400);
}

// ============================================
// API CALLS
// ============================================

async function fetchGPUStats() {
  let text;

  try {
    const resp = await fetch(`${API_BASE}/api/gpu-stats`);
    const data = await resp.json();

    if (data.cuda && data.cuda.available) {
      const gpu = data.gpu;
      const memPercent = gpu.memory ? gpu.memory.percent : 0;
      text = `GPU: ${gpu.name || "Unknown"} | Memory: ${memPercent}%`;
    } else {
      text = "GPU: No disponible (usando CPU)";
    }
  } catch (error) {
    text = "GPU: Error";
    log("Error obteniendo stats de GPU", "warning");
  }

  elements.gpuStats.textContent = text;
  if (elements.footerGpu) {
    elements.footerGpu.textContent = text;
  }
}

async function uploadFile(file) {
  log(`Subiendo: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`);
  hideInfo(elements.uploadInfo);

  const formData = new FormData();
  formData.append("file", file);

  _setBusy(1);
  try {
    const resp = await fetch(`${API_BASE}/api/upload`, { method: "POST", body: formData });
    const data = await resp.json();

    if (resp.ok && data.status === "ok") {
      state.currentFile = data.file_name;
      state.mediaType = data.media_type;

      const url = data.media_type === "video"
        ? `${API_BASE}/video/${encodeURIComponent(data.file_name)}`
        : `${API_BASE}/audio/${encodeURIComponent(data.file_name)}`;

      if (data.media_type === "video") {
        elements.videoPlayer.src = url;
        elements.videoPlayer.load();
        elements.videoPlayer.style.display = "block";
        elements.audioPlayer.style.display = "none";
        localStorage.setItem("lastDownloadedFile", data.file_name);
        localStorage.setItem("lastMediaType", "video");
      } else {
        elements.audioPlayer.src = url;
        elements.audioPlayer.load();
        elements.audioPlayer.style.display = "block";
        elements.videoPlayer.style.display = "none";
      }

      elements.transcribeBtn.disabled = false;
      showInfo(elements.uploadInfo, `✓ ${data.file_name} — ${(file.size / 1024 / 1024).toFixed(1)} MB`, "success");
      log(`✓ Archivo listo: ${data.file_name}`, "success");
    } else {
      throw new Error(data.detail || "Error al subir");
    }
  } catch (error) {
    log(`Error: ${error.message}`, "error");
    showInfo(elements.uploadInfo, `Error: ${error.message}`, "error");
  } finally {
    _setBusy(-1);
  }
}

async function downloadAudio(url, downloadVideo = false) {
  log(downloadVideo ? "Descargando video..." : "Descargando audio...");
  setButtonLoading(elements.downloadBtn, true);
  hideInfo(elements.downloadInfo);

  _setBusy(1);
  try {
    const resp = await fetch(`${API_BASE}/api/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, download_video: downloadVideo }),
    });

    const data = await resp.json();

    if (resp.ok && data.status === "ok") {
      state.currentFile = data.file_name;
      state.mediaType = data.media_type;

      log(`✓ Descargado: ${data.title}`, "success");
      showInfo(
        elements.downloadInfo,
        `Archivo: ${data.file_name} | Duración: ${Math.round(data.duration)}s | Tamaño: ${(data.size_bytes / 1024 / 1024).toFixed(2)} MB | Tipo: ${data.media_type}`,
        "success"
      );

      // Cargar en el player apropiado
      const encodedFileName = encodeURIComponent(data.file_name);
      const mediaUrl = data.media_type === "video"
        ? `${API_BASE}/video/${encodedFileName}`
        : `${API_BASE}/audio/${encodedFileName}`;

      if (data.media_type === "video") {
        elements.videoPlayer.src = mediaUrl;
        elements.videoPlayer.load();
        elements.videoPlayer.style.display = "block";
        elements.audioPlayer.style.display = "none";

        // Guardar en localStorage para el player
        localStorage.setItem('lastDownloadedFile', data.file_name);
        localStorage.setItem('lastMediaType', 'video');
      } else {
        elements.audioPlayer.src = mediaUrl;
        elements.audioPlayer.load();
        elements.audioPlayer.style.display = "block";
        elements.videoPlayer.style.display = "none";
      }

      // Habilitar botón de transcripción
      elements.transcribeBtn.disabled = false;

      return data;
    } else {
      throw new Error(data.detail || "Error en descarga");
    }
  } catch (error) {
    log(`Error: ${error.message}`, "error");
    showInfo(elements.downloadInfo, `Error: ${error.message}`, "error");
    throw error;
  } finally {
    setButtonLoading(elements.downloadBtn, false);
    _setBusy(-1);
  }
}

async function transcribeAudio(fileName, language) {
  const taskId = crypto.randomUUID();
  log("Transcribiendo con Whisper...");
  setButtonLoading(elements.transcribeBtn, true);
  hideInfo(elements.transcriptInfo);
  elements.transcript.value = "Transcribiendo... 0%";

  const pollInterval = startProgressPolling(taskId, (p) => {
    const pct = Math.round(p * 100);
    elements.transcript.value = `Transcribiendo... ${pct}%`;
  });

  _setBusy(1);
  try {
    const resp = await fetch(`${API_BASE}/api/transcribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_name: fileName, language: language || null, task_id: taskId }),
    });

    const data = await resp.json();

    if (resp.ok && data.status === "ok") {
      state.transcriptionData = data;
      state.sourceLanguage = data.language;

      log(`✓ Transcripción completada (${data.language})`, "success");
      elements.transcript.value = data.text;

      showInfo(
        elements.transcriptInfo,
        `Idioma: ${data.language} | Duración: ${Math.round(data.duration)}s | Segmentos: ${data.segments.length} | Caracteres: ${data.text.length}`,
        "success"
      );

      elements.translateBtn.disabled = false;

      if (state.mediaType === "video") {
        elements.playerLink.classList.remove("hidden");
      }

      return data;
    } else {
      throw new Error(data.detail || "Error en transcripción");
    }
  } catch (error) {
    log(`Error: ${error.message}`, "error");
    elements.transcript.value = "";
    showInfo(elements.transcriptInfo, `Error: ${error.message}`, "error");
    throw error;
  } finally {
    clearInterval(pollInterval);
    setButtonLoading(elements.transcribeBtn, false);
    _setBusy(-1);
  }
}

async function translateTranscript(fileName, targetLang) {
  const taskId = crypto.randomUUID();
  const totalSegments = state.transcriptionData?.segments?.length || 0;

  log(`Traduciendo a ${targetLang}...`);
  setButtonLoading(elements.translateBtn, true);
  hideInfo(elements.translationInfo);
  elements.translation.value = "Traduciendo... 0%";

  const pollInterval = startProgressPolling(taskId, (p) => {
    const pct = Math.round(p * 100);
    const done = Math.round(p * totalSegments);
    elements.translation.value = totalSegments
      ? `Traduciendo... ${pct}% (${done}/${totalSegments} segmentos)`
      : `Traduciendo... ${pct}%`;
  });

  _setBusy(1);
  try {
    const resp = await fetch(`${API_BASE}/api/translate-transcript`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_name: fileName, target_lang: targetLang, task_id: taskId }),
    });

    const data = await resp.json();

    if (resp.ok && data.status === "ok") {
      state.translationData = data;
      state.targetLanguage = targetLang;

      log(`✓ Traducción completada`, "success");
      elements.translation.value = data.translated_text;

      showInfo(
        elements.translationInfo,
        `De ${data.source_lang} a ${data.target_lang} | Segmentos traducidos: ${data.segments.length}`,
        "success"
      );

      enableExportButtons();
      elements.retranslateBtn.disabled = false;

      if (state.mediaType === "video") {
        elements.playerLink.classList.remove("hidden");
      }

      return data;
    } else {
      throw new Error(data.detail || "Error en traducción");
    }
  } catch (error) {
    log(`Error: ${error.message}`, "error");
    elements.translation.value = "";
    showInfo(elements.translationInfo, `Error: ${error.message}`, "error");
    throw error;
  } finally {
    clearInterval(pollInterval);
    setButtonLoading(elements.translateBtn, false);
    _setBusy(-1);
  }
}

async function retranslate() {
  if (!state.currentFile) return;
  log("Limpiando caché de traducción...");
  try {
    await fetch(`${API_BASE}/api/cache/translation/${encodeURIComponent(state.currentFile)}`, {
      method: "DELETE",
    });
    log("↺ Retranslating con DP mejorado...");
    await translateTranscript(state.currentFile, elements.targetLangSelect.value);
  } catch (e) {
    log(`Error en retranslate: ${e.message}`, "error");
  }
}

async function exportFile(fileName, format, useTranslation, bilingual) {
  log(`Exportando como ${format.toUpperCase()}...`);

  try {
    const resp = await fetch(`${API_BASE}/api/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        file_name: fileName,
        format: format,
        use_translation: useTranslation,
        bilingual: bilingual,
      }),
    });

    const data = await resp.json();

    if (resp.ok && data.status === "ok") {
      log(`✓ Exportado: ${data.file_name}`, "success");

      // Descargar archivo
      const downloadUrl = `${API_BASE}/api/export/${encodeURIComponent(data.file_name)}`;
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = data.file_name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      return data;
    } else {
      throw new Error(data.detail || "Error en exportación");
    }
  } catch (error) {
    log(`Error exportando: ${error.message}`, "error");
    throw error;
  }
}

// ============================================
// HELPERS
// ============================================

function enableExportButtons() {
  elements.exportSrtBtn.disabled = false;
  elements.exportVttBtn.disabled = false;
  elements.exportTxtBtn.disabled = false;
  elements.exportJsonBtn.disabled = false;

  // Habilitar exportación de video
  if (state.mediaType === "video") {
    elements.exportVideoBtn.disabled = false;
  }
}

// ============================================
// EVENT LISTENERS
// ============================================

// Upload — drag & drop + file input
elements.dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  elements.dropZone.style.borderColor = "rgba(102,126,234,0.8)";
  elements.dropZone.style.background = "rgba(102,126,234,0.08)";
});
elements.dropZone.addEventListener("dragleave", () => {
  elements.dropZone.style.borderColor = "rgba(102,126,234,0.35)";
  elements.dropZone.style.background = "";
});
elements.dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  elements.dropZone.style.borderColor = "rgba(102,126,234,0.35)";
  elements.dropZone.style.background = "";
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});
elements.dropZone.addEventListener("click", () => elements.fileInput.click());
elements.fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) uploadFile(file);
});

// Download
elements.downloadBtn.addEventListener("click", async () => {
  const url = elements.videoUrl.value.trim();

  if (!url) {
    log("Por favor ingresa una URL", "warning");
    return;
  }

  const downloadVideo = elements.downloadVideoCheck.checked;

  try {
    await downloadAudio(url, downloadVideo);
  } catch (error) {
    // Error ya logueado
  }
});

// Transcribe
elements.transcribeBtn.addEventListener("click", async () => {
  if (!state.currentFile) {
    log("Primero descarga un audio", "warning");
    return;
  }

  const language = elements.langSelect.value || null;

  try {
    await transcribeAudio(state.currentFile, language);
  } catch (error) {
    // Error ya logueado
  }
});

// Translate
elements.translateBtn.addEventListener("click", async () => {
  if (!state.currentFile || !state.transcriptionData) {
    log("Primero transcribe el audio", "warning");
    return;
  }

  const targetLang = elements.targetLangSelect.value;

  try {
    await translateTranscript(state.currentFile, targetLang);
  } catch (error) {
    // Error ya logueado
  }
});

// Export SRT
elements.exportSrtBtn.addEventListener("click", async () => {
  const useTranslation = !!state.translationData;
  const bilingual = elements.bilingualCheck.checked;

  try {
    await exportFile(state.currentFile, "srt", useTranslation, bilingual);
  } catch (error) {
    // Error ya logueado
  }
});

// Export VTT
elements.exportVttBtn.addEventListener("click", async () => {
  const useTranslation = !!state.translationData;
  const bilingual = elements.bilingualCheck.checked;

  try {
    await exportFile(state.currentFile, "vtt", useTranslation, bilingual);
  } catch (error) {
    // Error ya logueado
  }
});

// Export TXT
elements.exportTxtBtn.addEventListener("click", async () => {
  const useTranslation = !!state.translationData;
  const bilingual = elements.bilingualCheck.checked;

  try {
    await exportFile(state.currentFile, "txt", useTranslation, bilingual);
  } catch (error) {
    // Error ya logueado
  }
});

// Export JSON
elements.exportJsonBtn.addEventListener("click", async () => {
  const useTranslation = !!state.translationData;

  try {
    await exportFile(state.currentFile, "json", useTranslation, false);
  } catch (error) {
    // Error ya logueado
  }
});

// Video Export
elements.exportVideoBtn.addEventListener("click", exportVideoWithSubtitles);

// Retranslate
elements.retranslateBtn.addEventListener("click", retranslate);

// Clear Log (solo si existe)
if (elements.clearLogBtn) {
  elements.clearLogBtn.addEventListener("click", () => {
    if (elements.log) {
      elements.log.textContent = "";
    }
  });
}

// ============================================
// Video Export con Subtítulos
// ============================================

async function exportVideoWithSubtitles() {
  if (!state.currentFile) {
    log("No hay archivo para exportar", "error");
    return;
  }

  const taskId = crypto.randomUUID();
  const includeTts = elements.includeTtsCheck.checked;

  log(`Generando video con subtítulos${includeTts ? " + TTS" : ""}...`);

  elements.exportVideoProgress.classList.remove("hidden");
  elements.exportVideoBtn.disabled = true;
  elements.exportProgressBar.style.width = "0%";
  elements.exportProgressText.textContent = "Iniciando exportación...";

  _setBusy(1);
  // Progreso real via polling — FFmpeg reporta out_time_ms al backend
  const pollInterval = startProgressPolling(taskId, (p) => {
    const pct = Math.round(p * 100);
    elements.exportProgressBar.style.width = `${pct}%`;
    if (p < 0.05) {
      elements.exportProgressText.textContent = "Generando subtítulos SRT...";
    } else if (p < 0.75) {
      elements.exportProgressText.textContent = `Quemando subtítulos... ${pct}%`;
    } else if (includeTts && p < 0.93) {
      elements.exportProgressText.textContent = `Generando audio TTS... ${pct}%`;
    } else {
      elements.exportProgressText.textContent = `Finalizando... ${pct}%`;
    }
  });

  try {
    const resp = await fetch(`${API_BASE}/api/export-video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        file_name: state.currentFile,
        include_tts: includeTts,
        task_id: taskId,
      }),
    });

    clearInterval(pollInterval);
    elements.exportProgressBar.style.width = "100%";

    const data = await resp.json();

    if (resp.ok && data.status === "ok") {
      elements.exportProgressText.textContent = "✓ Completado!";
      log(`✓ Video exportado: ${data.file_name}`, "success");

      const sizeMB = (data.size_bytes / (1024 * 1024)).toFixed(2);
      showInfo(
        elements.exportVideoInfo,
        `Video generado: ${data.file_name} (${sizeMB} MB) — ${includeTts ? "Con TTS" : "Sin TTS"}`,
        "success"
      );

      const downloadLink = document.createElement("a");
      downloadLink.href = `${API_BASE}${data.file_path}`;
      downloadLink.download = data.file_name;
      downloadLink.textContent = "⬇️ DESCARGAR VIDEO FINAL";
      downloadLink.style.cssText = "display:block; margin-top:1rem; padding:1rem; background:var(--accent-success); color:white; text-align:center; text-decoration:none; border-radius:var(--radius-md); font-weight:bold;";
      elements.exportVideoInfo.appendChild(downloadLink);

      setTimeout(() => {
        elements.exportVideoProgress.classList.add("hidden");
        elements.exportVideoBtn.disabled = false;
      }, 2000);
    } else {
      throw new Error(data.detail || "Error exportando video");
    }
  } catch (error) {
    clearInterval(pollInterval);
    log(`Error: ${error.message}`, "error");
    showInfo(elements.exportVideoInfo, `Error: ${error.message}`, "error");
    elements.exportVideoProgress.classList.add("hidden");
    elements.exportVideoBtn.disabled = false;
  } finally {
    _setBusy(-1);
  }
}

// ============================================
// HISTORIAL DE ARCHIVOS PROCESADOS
// ============================================

async function loadHistory() {
  try {
    const resp = await fetch(`${API_BASE}/api/history`);
    const data = await resp.json();
    const entries = data.entries || [];
    if (entries.length === 0) return;

    const section = document.getElementById("history-section");
    const list = document.getElementById("history-list");

    list.innerHTML = entries.map((entry) => {
      const mins = Math.round(entry.duration / 60);
      const transLabel = entry.translations.length ? `· ✓ ${entry.translations.join(", ")}` : "";
      const icon = entry.media_type === "video" ? "🎬" : "🎵";
      const preview = entry.text_preview ? `"${entry.text_preview}…"` : "";

      return `
        <div class="history-entry"
             data-filename="${entry.file_name.replace(/"/g, "&quot;")}"
             data-mediatype="${entry.media_type}"
             data-translations="${JSON.stringify(entry.translations).replace(/"/g, "&quot;")}"
             style="display:flex; align-items:center; gap:1rem; padding:0.9rem 1rem;
                    background:rgba(255,255,255,0.04); border-radius:var(--radius-md);
                    border:1px solid rgba(255,255,255,0.08); cursor:pointer;
                    transition:border-color 0.2s,background 0.2s;"
             onmouseenter="this.style.background='rgba(102,126,234,0.12)';this.style.borderColor='rgba(102,126,234,0.4)'"
             onmouseleave="this.style.background='rgba(255,255,255,0.04)';this.style.borderColor='rgba(255,255,255,0.08)'">
          <div style="font-size:1.8rem;flex-shrink:0;">${icon}</div>
          <div style="flex:1;min-width:0;overflow:hidden;">
            <div style="font-weight:600;font-size:0.875rem;color:var(--text-primary);
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${entry.file_name}</div>
            <div style="font-size:0.78rem;color:var(--text-secondary);margin-top:0.2rem;">
              ${entry.language.toUpperCase()} · ${mins} min · ${entry.segments} seg ${transLabel}
            </div>
            ${preview ? `<div style="font-size:0.78rem;color:var(--text-muted);margin-top:0.15rem;
                              font-style:italic;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                           ${preview}</div>` : ""}
          </div>
          <div style="display:flex;align-items:center;gap:0.5rem;flex-shrink:0;">
            <span style="color:var(--accent-cyan);font-size:0.85rem;opacity:0.7;">Restaurar →</span>
            <button class="delete-btn"
                    data-filename="${entry.file_name.replace(/"/g, "&quot;")}"
                    title="Borrar archivo"
                    style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);
                           color:var(--accent-error);border-radius:var(--radius-sm);
                           padding:0.25rem 0.5rem;cursor:pointer;font-size:0.8rem;
                           transition:all 0.2s;line-height:1;">🗑️</button>
          </div>
        </div>`;
    }).join("");

    list.querySelectorAll(".history-entry").forEach((el) => {
      el.addEventListener("click", (e) => {
        if (e.target.closest(".delete-btn")) return;
        const fileName = el.dataset.filename;
        const mediaType = el.dataset.mediatype;
        const translations = JSON.parse(el.dataset.translations);
        restoreSession(fileName, mediaType, translations);
      });
    });

    list.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteHistoryEntry(btn.dataset.filename);
      });
    });

    section.style.display = "block";
  } catch {
    // Historial no disponible — no es crítico
  }
}

async function deleteHistoryEntry(fileName) {
  try {
    const resp = await fetch(`${API_BASE}/api/files/${encodeURIComponent(fileName)}`, { method: "DELETE" });
    if (resp.ok) {
      log(`✓ Borrado: ${fileName}`, "success");
      await loadHistory();
    }
  } catch (e) {
    log(`Error borrando: ${e.message}`, "error");
  }
}

async function restoreSession(fileName, mediaType, translations) {
  log(`Restaurando sesión: ${fileName}`);

  state.currentFile = fileName;
  state.mediaType = mediaType;

  // Cargar media en el player
  const encodedFileName = encodeURIComponent(fileName);
  if (mediaType === "video") {
    elements.videoPlayer.src = `${API_BASE}/video/${encodedFileName}`;
    elements.videoPlayer.load();
    elements.videoPlayer.style.display = "block";
    elements.audioPlayer.style.display = "none";
    localStorage.setItem("lastDownloadedFile", fileName);
    localStorage.setItem("lastMediaType", "video");
  } else {
    elements.audioPlayer.src = `${API_BASE}/audio/${encodedFileName}`;
    elements.audioPlayer.load();
    elements.audioPlayer.style.display = "block";
    elements.videoPlayer.style.display = "none";
  }

  showInfo(elements.downloadInfo, `Restaurado: ${fileName}`, "success");
  elements.transcribeBtn.disabled = false;

  // Transcripción — llega del disco en milisegundos
  try {
    elements.transcript.value = "Restaurando transcripción…";
    const resp = await fetch(`${API_BASE}/api/transcribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_name: fileName, language: null, task_id: crypto.randomUUID() }),
    });
    const data = await resp.json();
    if (resp.ok && data.status === "ok") {
      state.transcriptionData = data;
      state.sourceLanguage = data.language;
      elements.transcript.value = data.text;
      elements.translateBtn.disabled = false;
      showInfo(elements.transcriptInfo,
        `Idioma: ${data.language} | ${data.segments.length} segmentos | Restaurado desde caché`,
        "success");
      if (mediaType === "video") elements.playerLink.classList.remove("hidden");
    }
  } catch {
    log("No se pudo restaurar la transcripción", "warning");
  }

  // Traducción — también del disco si existe
  if (translations.length > 0) {
    const lang = translations.includes("es") ? "es" : translations[0];
    try {
      elements.translation.value = "Restaurando traducción…";
      const resp = await fetch(`${API_BASE}/api/translate-transcript`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_name: fileName, target_lang: lang, task_id: crypto.randomUUID() }),
      });
      const data = await resp.json();
      if (resp.ok && data.status === "ok") {
        state.translationData = data;
        state.targetLanguage = lang;
        elements.translation.value = data.translated_text;
        enableExportButtons();
        showInfo(elements.translationInfo,
          `${data.source_lang} → ${data.target_lang} | ${data.segments.length} segmentos | Restaurado desde caché`,
          "success");
      }
    } catch {
      log("No se pudo restaurar la traducción", "warning");
    }
  }

  log(`✓ Sesión restaurada: ${fileName}`, "success");
  document.querySelector(".container:not(#history-section)").scrollIntoView({ behavior: "smooth" });
}

// ============================================
// INIT
// ============================================

async function init() {
  log("🚀 Flowxy-Translator iniciado");

  await fetchGPUStats();
  _gpuPollTimer = setInterval(fetchGPUStats, 30000); // idle: cada 30s

  await loadHistory();

  log("Sistema listo. Pega una URL o arrastra un archivo para comenzar.");
}

// Start app
init();
