// Video Player with Real-time Subtitles - OPTIMIZED
// Flowxy-Translator

// El frontend es servido por el propio backend FastAPI, así que las
// rutas relativas siempre apuntan al servidor correcto (host y puerto).
const API_BASE = "";

let currentSegments = [];
let currentVideo = null;
let currentSegmentIndex = -1;
let lastUpdateTime = 0;

// Word highlighting state
let _lastWordSegment = -1;
let _wordSpans = [];

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadAvailableVideos();
    setupEventListeners();
});

function setupEventListeners() {
    const video = document.getElementById('videoPlayer');
    const subtitleMode = document.getElementById('subtitleMode');
    const videoSelect = document.getElementById('videoSelect');

    // Video selection
    videoSelect.addEventListener('change', handleVideoChange);

    // Subtitle mode change — reset word cache
    subtitleMode.addEventListener('change', () => {
        _lastWordSegment = -1;
        _wordSpans = [];
        updateSubtitleMode();
    });

    // Video time update for subtitle synchronization
    video.addEventListener('timeupdate', updateSubtitles);

    // Error handling
    video.addEventListener('error', handleVideoError);

    // Seeking - update immediately
    video.addEventListener('seeked', () => {
        currentSegmentIndex = -1; // Reset index to force re-search
        updateSubtitles();
    });
}

async function loadAvailableVideos() {
    try {
        const fileName = localStorage.getItem('lastDownloadedFile');
        const mediaType = localStorage.getItem('lastMediaType');
        const select = document.getElementById('videoSelect');

        if (fileName && mediaType === 'video') {
            const option = document.createElement('option');
            option.value = fileName;
            option.textContent = decodeURIComponent(fileName);
            option.selected = true;
            select.appendChild(option);

            await loadVideo(fileName);
        } else {
            showStatus('No hay videos disponibles. Descarga un video primero desde la página principal.');
        }
    } catch (error) {
        showError('Error cargando lista de videos: ' + error.message);
    }
}

async function handleVideoChange(e) {
    const fileName = e.target.value;
    if (fileName) {
        await loadVideo(fileName);
    }
}

async function loadVideo(fileName) {
    try {
        showStatus('Cargando video...');

        const video = document.getElementById('videoPlayer');
        video.src = `${API_BASE}/video/${encodeURIComponent(fileName)}`;
        currentVideo = fileName;

        // Load subtitles from new API endpoint
        await loadSubtitles(fileName);

        showStatus(`Video cargado: ${fileName}`);
    } catch (error) {
        showError('Error cargando video: ' + error.message);
    }
}

async function loadSubtitles(fileName) {
    try {
        showStatus('Cargando subtítulos...');

        // El backend cachea la transcripción con el nombre de archivo completo
        // (incluyendo extensión) como prefijo de la clave, así que se debe
        // usar el mismo nombre aquí para que coincida.
        const response = await fetch(`${API_BASE}/api/subtitles/${encodeURIComponent(fileName)}`);

        if (response.ok) {
            const data = await response.json();
            currentSegments = data.segments;
            currentSegmentIndex = -1; // Reset index

            showStatus(`Subtítulos cargados: ${currentSegments.length} segmentos (${data.language})`);

            // Pre-sort segments by start time for binary search
            currentSegments.sort((a, b) => a.start - b.start);
        } else {
            const error = await response.json();
            showStatus('No se encontraron subtítulos. Transcribe el video primero en la página principal.');
            currentSegments = [];
        }
    } catch (error) {
        console.error('Error loading subtitles:', error);
        showStatus('Sin subtítulos disponibles. Transcribe el video primero.');
        currentSegments = [];
    }
}

// Binary search for current segment (O(log n) instead of O(n))
function findSegmentIndex(time) {
    if (currentSegments.length === 0) return -1;

    // Check if we can use the cached index (common case: video playing forward)
    if (currentSegmentIndex >= 0 && currentSegmentIndex < currentSegments.length) {
        const seg = currentSegments[currentSegmentIndex];
        if (time >= seg.start && time <= seg.end) {
            return currentSegmentIndex; // Still in same segment
        }

        // Check next segment (most common case when playing)
        if (currentSegmentIndex + 1 < currentSegments.length) {
            const nextSeg = currentSegments[currentSegmentIndex + 1];
            if (time >= nextSeg.start && time <= nextSeg.end) {
                return currentSegmentIndex + 1;
            }
        }
    }

    // Binary search
    let left = 0;
    let right = currentSegments.length - 1;

    while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        const seg = currentSegments[mid];

        if (time >= seg.start && time <= seg.end) {
            return mid;
        } else if (time < seg.start) {
            right = mid - 1;
        } else {
            left = mid + 1;
        }
    }

    return -1; // No segment found
}

function updateSubtitles() {
    const video = document.getElementById('videoPlayer');
    const currentTime = video.currentTime;
    const subtitleMode = document.getElementById('subtitleMode').value;
    const subtitleDiv = document.getElementById('currentSubtitle');

    // Throttle updates to every 50ms for performance
    const now = Date.now();
    if (now - lastUpdateTime < 50) {
        return;
    }
    lastUpdateTime = now;

    if (subtitleMode === 'none' || currentSegments.length === 0) {
        subtitleDiv.style.display = 'none';
        return;
    }

    // Find current segment using optimized search
    const segmentIndex = findSegmentIndex(currentTime);

    if (segmentIndex >= 0) {
        currentSegmentIndex = segmentIndex;
        const currentSegment = currentSegments[segmentIndex];

        subtitleDiv.style.display = 'inline-block';

        if (subtitleMode === 'bilingual') {
            subtitleDiv.classList.add('bilingual');
            const translated = currentSegment.translated || currentSegment.text;
            subtitleDiv.innerHTML = `
                <span class="subtitle-original">${escapeHtml(currentSegment.text)}</span>
                <span class="subtitle-translated">${escapeHtml(translated)}</span>
            `;
            _lastWordSegment = -1; // reset para cuando cambie a otro modo
        } else if (subtitleMode === 'translated') {
            subtitleDiv.classList.remove('bilingual');
            subtitleDiv.textContent = currentSegment.translated || currentSegment.text;
            _lastWordSegment = -1;
        } else {
            // Modo original — word highlighting
            subtitleDiv.classList.remove('bilingual');
            renderWithWordHighlight(currentSegment, segmentIndex, currentTime, subtitleDiv);
        }
    } else {
        subtitleDiv.style.display = 'none';
    }
}

function renderWithWordHighlight(segment, segmentIndex, currentTime, container) {
    const words = segment.words || [];

    // Re-render spans solo cuando cambia el segmento
    if (segmentIndex !== _lastWordSegment) {
        _lastWordSegment = segmentIndex;
        _wordSpans = [];
        container.innerHTML = '';

        if (words.length === 0) {
            container.textContent = segment.text;
            return;
        }

        words.forEach((w) => {
            const span = document.createElement('span');
            span.textContent = w.word + ' ';
            span.dataset.start = w.start;
            span.dataset.end = w.end;
            _wordSpans.push(span);
            container.appendChild(span);
        });
    }

    // Actualizar highlight eficientemente (solo clases, no re-render)
    _wordSpans.forEach((span) => {
        const active = currentTime >= parseFloat(span.dataset.start) &&
                       currentTime <= parseFloat(span.dataset.end);
        span.className = active ? 'word-highlight' : '';
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateSubtitleMode() {
    // Immediate update when mode changes
    updateSubtitles();
}

function handleVideoError(e) {
    const video = e.target;
    let errorMessage = 'Error desconocido';

    switch (video.error.code) {
        case 1:
            errorMessage = 'Carga del video abortada';
            break;
        case 2:
            errorMessage = 'Error de red';
            break;
        case 3:
            errorMessage = 'Error de decodificación';
            break;
        case 4:
            errorMessage = 'Formato de video no soportado';
            break;
    }

    showError(`Error de video: ${errorMessage}`);
}

function showStatus(message) {
    const statusDiv = document.getElementById('status');
    const errorDiv = document.getElementById('error');
    statusDiv.textContent = message;
    errorDiv.style.display = 'none';
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    const statusDiv = document.getElementById('status');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    statusDiv.textContent = '';
}
