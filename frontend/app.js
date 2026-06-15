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

  // GPU & Log (opcional)
  gpuStats: document.getElementById("gpu-stats"),
  footerGpu: document.getElementById("footerGpu"), // Puede ser null
  log: document.getElementById("logConsole"), // Puede ser null
  clearLogBtn: document.getElementById("clearLogBtn"), // Puede ser null
};

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

async function downloadAudio(url, downloadVideo = false) {
  log(downloadVideo ? "Descargando video..." : "Descargando audio...");
  setButtonLoading(elements.downloadBtn, true);
  hideInfo(elements.downloadInfo);

  try {
    const resp = await fetch(`${API_BASE}/api/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        download_video: downloadVideo
      }),
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
  }
}

async function transcribeAudio(fileName, language) {
  log("Transcribiendo con Whisper...");
  setButtonLoading(elements.transcribeBtn, true);
  hideInfo(elements.transcriptInfo);
  elements.transcript.value = "Transcribiendo... (esto puede tomar un momento)";

  try {
    const resp = await fetch(`${API_BASE}/api/transcribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        file_name: fileName,
        language: language || null,
      }),
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

      // Habilitar traducción
      elements.translateBtn.disabled = false;

      // Mostrar link al player si es video (puede ver con subtítulos originales)
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
    setButtonLoading(elements.transcribeBtn, false);
  }
}

async function translateTranscript(fileName, targetLang) {
  log(`Traduciendo a ${targetLang}...`);
  setButtonLoading(elements.translateBtn, true);
  hideInfo(elements.translationInfo);
  elements.translation.value = "Traduciendo... (esto puede tomar un momento)";

  try {
    const resp = await fetch(`${API_BASE}/api/translate-transcript`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        file_name: fileName,
        target_lang: targetLang,
      }),
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

      // Habilitar exportación
      enableExportButtons();

      // Mostrar link al player si es video
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
    setButtonLoading(elements.translateBtn, false);
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

  const includeTts = elements.includeTtsCheck.checked;

  log(`Generando video con subtítulos${includeTts ? " + TTS" : ""}...`);

  // Mostrar progress bar
  elements.exportVideoProgress.classList.remove("hidden");
  elements.exportVideoBtn.disabled = true;
  elements.exportProgressBar.style.width = "0%";
  elements.exportProgressText.textContent = "Iniciando exportación...";

  // Simular progreso (ya que el proceso es largo)
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress += 5;
    if (progress <= 90) {
      elements.exportProgressBar.style.width = `${progress}%`;

      if (progress < 30) {
        elements.exportProgressText.textContent = "Generando archivo SRT...";
      } else if (progress < 60) {
        elements.exportProgressText.textContent = "Quemando subtítulos en video...";
      } else if (includeTts && progress < 90) {
        elements.exportProgressText.textContent = "Generando audio TTS...";
      }
    }
  }, 1000);

  try {
    const resp = await fetch(`${API_BASE}/api/export-video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        file_name: state.currentFile,
        include_tts: includeTts,
      }),
    });

    clearInterval(progressInterval);
    elements.exportProgressBar.style.width = "100%";

    const data = await resp.json();

    if (resp.ok && data.status === "ok") {
      elements.exportProgressText.textContent = "✓ Completado!";

      log(`✓ Video exportado: ${data.file_name}`, "success");

      // Mostrar info y link de descarga
      const sizeMB = (data.size_bytes / (1024 * 1024)).toFixed(2);
      showInfo(
        elements.exportVideoInfo,
        `Video generado: ${data.file_name} (${sizeMB} MB) - ${includeTts ? "Con TTS" : "Sin TTS"}`,
        "success"
      );

      // Crear link de descarga
      const downloadLink = document.createElement("a");
      downloadLink.href = `${API_BASE}${data.file_path}`;
      downloadLink.download = data.file_name;
      downloadLink.textContent = "⬇️ DESCARGAR VIDEO FINAL";
      downloadLink.style.cssText = "display: block; margin-top: 1rem; padding: 1rem; background: var(--accent-success); color: white; text-align: center; text-decoration: none; border-radius: var(--radius-md); font-weight: bold;";

      elements.exportVideoInfo.appendChild(downloadLink);

      // Ocultar progress después de 2 segundos
      setTimeout(() => {
        elements.exportVideoProgress.classList.add("hidden");
        elements.exportVideoBtn.disabled = false;
      }, 2000);
    } else {
      throw new Error(data.detail || "Error exportando video");
    }
  } catch (error) {
    clearInterval(progressInterval);
    log(`Error: ${error.message}`, "error");
    showInfo(elements.exportVideoInfo, `Error: ${error.message}`, "error");
    elements.exportVideoProgress.classList.add("hidden");
    elements.exportVideoBtn.disabled = false;
  }
}

// ============================================
// INIT
// ============================================

async function init() {
  log("🚀 Flowxy-Translator iniciado");
  log("Versión: 1.0.0 | GPU-Optimized");

  // Fetch GPU stats
  await fetchGPUStats();

  // Update GPU stats every 5 seconds
  setInterval(fetchGPUStats, 5000);

  log("Sistema listo. Pega una URL para comenzar.");
}

// Start app
init();
