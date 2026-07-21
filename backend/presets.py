"""
Presets de hardware — permiten que alguien con distinta VRAM/CPU use el
proyecto sin editar backend/config.py a mano.

Cada preset es un DELTA sobre los defaults ya declarados en config.py
("standard" está vacío a propósito: los valores hardcodeados en config.py
SON el preset standard, una sola fuente de verdad). config.py llama a
resolve_effective_config() para fusionar preset + overrides explícitos del
usuario sobre esos defaults.

No importa backend.config (evitaría un ciclo) — recibe base_dir y defaults
como parámetros.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

PresetName = str  # "cpu" | "low-vram" | "standard" | "high-end"

CONFIG_FILENAME = "config.local.json"

# ── Presets: deltas sobre los defaults de config.py ──────────────────────────
PRESETS: Dict[PresetName, Dict[str, Any]] = {
    "cpu": {
        "WHISPER_MODEL_SIZE": "base",
        "WHISPER_BEAM_SIZE": 1,
        "WHISPER_BEST_OF": 1,
        "NLLB_MODEL_SIZE": "600M",
        "NLLB_BEAM_SIZE": 1,
        "NLLB_BATCH_SIZE": 4,
    },
    "low-vram": {
        "WHISPER_MODEL_SIZE": "small",
        "NLLB_MODEL_SIZE": "600M",
        "NLLB_BATCH_SIZE": 8,
    },
    "standard": {},  # los defaults actuales de config.py
    "high-end": {
        "WHISPER_MODEL_SIZE": "large-v3",
        "WHISPER_BEAM_SIZE": 8,
        "WHISPER_BEST_OF": 8,
        "NLLB_BEAM_SIZE": 8,
        "NLLB_BATCH_SIZE": 32,
    },
}

PRESET_METADATA: Dict[PresetName, Dict[str, Any]] = {
    "cpu": {
        "label": "Solo CPU",
        "description": "Sin GPU NVIDIA disponible. Modelos más chicos y decodificación "
                        "greedy (sin beam search) — beam=5 en CPU es demasiado lento.",
        "approx_vram_gb": 0,
    },
    "low-vram": {
        "label": "VRAM reducida",
        "description": "GPU con 4-6 GB de VRAM. Whisper small + NLLB 600M.",
        "approx_vram_gb": 5,
    },
    "standard": {
        "label": "Estándar",
        "description": "GPU con ~8 GB de VRAM (ej. RTX 4060 Ti). Whisper medium + NLLB 1.3B.",
        "approx_vram_gb": 8,
    },
    "high-end": {
        "label": "Gama alta",
        "description": "GPU con 12+ GB de VRAM. Whisper large-v3 y beam sizes más altos.",
        "approx_vram_gb": 12,
    },
}

# Whitelist de claves editables desde el frontend — todo lo demás (SERVER_PORT,
# CORS_ORIGINS, rutas, etc.) queda fuera de alcance y el POST lo rechaza.
CONFIGURABLE_KEYS: Dict[str, Dict[str, Any]] = {
    "WHISPER_MODEL_SIZE": {"type": "enum", "values": ["tiny", "base", "small", "medium", "large-v2", "large-v3"]},
    "WHISPER_BEAM_SIZE": {"type": "int", "min": 1, "max": 10},
    "WHISPER_BEST_OF": {"type": "int", "min": 1, "max": 10},
    "NLLB_MODEL_SIZE": {"type": "enum", "values": ["600M", "1.3B"]},
    "NLLB_BEAM_SIZE": {"type": "int", "min": 1, "max": 10},
    "NLLB_BATCH_SIZE": {"type": "int", "min": 1, "max": 64},
    "NLLB_REPETITION_PENALTY": {"type": "float", "min": 1.0, "max": 2.0},
    "NLLB_NO_REPEAT_NGRAM": {"type": "int", "min": 0, "max": 10},
    "NLLB_CONTEXT_AWARE": {"type": "bool"},
}


def validate_overrides(overrides: Dict[str, Any]) -> Optional[str]:
    """Valida overrides contra CONFIGURABLE_KEYS. None si son válidos, o un mensaje de error."""
    for key, value in overrides.items():
        spec = CONFIGURABLE_KEYS.get(key)
        if spec is None:
            return f"Clave no configurable: {key}"
        if spec["type"] == "enum" and value not in spec["values"]:
            return f"{key} debe ser uno de {spec['values']}"
        if spec["type"] == "int" and (not isinstance(value, int) or isinstance(value, bool)):
            return f"{key} debe ser un entero"
        if spec["type"] == "int" and not (spec["min"] <= value <= spec["max"]):
            return f"{key} debe estar entre {spec['min']} y {spec['max']}"
        if spec["type"] == "float" and not isinstance(value, (int, float)):
            return f"{key} debe ser numérico"
        if spec["type"] == "float" and not (spec["min"] <= value <= spec["max"]):
            return f"{key} debe estar entre {spec['min']} y {spec['max']}"
        if spec["type"] == "bool" and not isinstance(value, bool):
            return f"{key} debe ser booleano"
    return None


def recommend_preset() -> PresetName:
    """Preset sugerido según la VRAM/CUDA detectada realmente en esta máquina."""
    from backend.utils.gpu_stats import get_cuda_info, get_gpu_stats

    cuda_info = get_cuda_info()
    if not cuda_info.get("available"):
        return "cpu"

    gpu = get_gpu_stats()
    vram_gb = gpu.get("memory", {}).get("total_gb") if gpu.get("available") else None
    if vram_gb is None:
        return "standard"  # CUDA disponible pero no se pudo leer VRAM: no asumir de más
    if vram_gb < 7:
        return "low-vram"
    if vram_gb < 11:
        return "standard"
    return "high-end"


def _config_path(base_dir: Path) -> Path:
    return base_dir / CONFIG_FILENAME


def load_local_config(base_dir: Path) -> Dict[str, Any]:
    """Lee config.local.json. {} si no existe o está corrupto."""
    path = _config_path(base_dir)
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"No se pudo leer {CONFIG_FILENAME}: {e}")
    return {}


def save_local_config(base_dir: Path, preset: PresetName, overrides: Dict[str, Any]) -> None:
    from datetime import datetime, timezone

    data = {
        "version": 1,
        "preset": preset,
        "overrides": overrides,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    _config_path(base_dir).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def resolve_effective_config(
    base_dir: Path, defaults: Dict[str, Any]
) -> Tuple[Dict[str, Any], PresetName, Dict[str, Any]]:
    """
    Fusiona preset + overrides sobre los defaults de config.py.

    Sin config.local.json: usa recommend_preset() (auto-detección) y overrides
    vacíos, SIN persistir nada — cada arranque vuelve a detectar hasta que el
    usuario guarde explícitamente un preset desde el frontend.

    Returns: (config_efectivo, preset_usado, overrides_usados)
    """
    saved = load_local_config(base_dir)
    preset = saved.get("preset") or recommend_preset()
    overrides = saved.get("overrides") or {}

    effective = dict(defaults)
    effective.update(PRESETS.get(preset, {}))
    effective.update(overrides)
    return effective, preset, overrides
