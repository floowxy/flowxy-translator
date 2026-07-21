import { useEffect, useState } from "react";
import { api } from "../api";
import { InfoBox } from "./InfoBox";
import {
  NLLB_MODEL_SIZES,
  PRESET_ORDER,
  WHISPER_MODEL_SIZES,
} from "../types";
import type { ConfigOverrides, PresetName, SettingsResponse, SystemSpecs } from "../types";

/**
 * Panel de configuración por hardware — sección especial fuera del flujo
 * numerado (mismo patrón que HistorySection). Colapsada por defecto: es un
 * ajuste poco frecuente, no debe competir con los pasos principales.
 *
 * Aplicar un preset nuevo requiere reiniciar el servidor — los modelos están
 * cacheados en el proceso, no hay recarga en caliente.
 */
export function SettingsSection() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [specs, setSpecs] = useState<SystemSpecs | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<PresetName>("standard");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [draftOverrides, setDraftOverrides] = useState<ConfigOverrides>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!open || settings) return;
    setLoading(true);
    setError(null);
    Promise.all([api.systemSpecs(), api.getSettings()])
      .then(([specsData, settingsData]) => {
        setSpecs(specsData);
        setSettings(settingsData);
        setSelectedPreset(settingsData.saved.preset);
        setDraftOverrides(settingsData.saved.overrides);
      })
      .catch((e) => setError(`No se pudo cargar la configuración: ${(e as Error).message}`))
      .finally(() => setLoading(false));
  }, [open, settings]);

  async function handleSavePreset(preset: PresetName) {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const data = await api.saveSettings(preset, {});
      setSettings(data);
      setSelectedPreset(preset);
      setDraftOverrides({});
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveAdvanced() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const data = await api.saveSettings(selectedPreset, draftOverrides);
      setSettings(data);
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  function updateOverride<K extends keyof ConfigOverrides>(key: K, value: ConfigOverrides[K]) {
    setDraftOverrides((prev) => ({ ...prev, [key]: value }));
  }

  const restartRequired = settings?.restart_required || saved;
  const hasOverrides = Object.keys(draftOverrides).length > 0;
  const effective = settings?.saved.effective;

  return (
    <div className="container" style={{ paddingBottom: 0 }}>
      <section className="card">
        <button
          className="settings-toggle"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
        >
          <span className="step-label">Configuración</span>
          <h2 style={{ margin: 0 }}>
            Hardware del sistema <span className="settings-chevron">{open ? "▾" : "▸"}</span>
          </h2>
        </button>

        {open && (
          <div className="settings-body">
            {loading && <p className="section-desc">Detectando specs…</p>}

            {specs && settings && (
              <>
                <div className="specs-grid">
                  <div className="spec-item">
                    <span className="spec-label">GPU</span>
                    <span className="spec-value">{specs.gpu_name ?? "Sin GPU NVIDIA (CPU)"}</span>
                  </div>
                  <div className="spec-item">
                    <span className="spec-label">VRAM</span>
                    <span className="spec-value">
                      {specs.vram_total_gb != null ? `${specs.vram_total_gb} GB` : "N/A"}
                    </span>
                  </div>
                  <div className="spec-item">
                    <span className="spec-label">Núcleos CPU</span>
                    <span className="spec-value">{specs.cpu_cores ?? "desconocido"}</span>
                  </div>
                  <div className="spec-item">
                    <span className="spec-label">RAM</span>
                    <span className="spec-value">
                      {specs.ram_total_gb != null ? `${specs.ram_total_gb} GB` : "desconocido"}
                    </span>
                  </div>
                </div>

                <div className="preset-grid">
                  {PRESET_ORDER.map((name) => {
                    const meta = settings.presets[name];
                    const isSelected = selectedPreset === name;
                    return (
                      <button
                        key={name}
                        className={`preset-card${isSelected ? " selected" : ""}`}
                        disabled={saving}
                        onClick={() => handleSavePreset(name)}
                      >
                        <span className="preset-card-label">{meta.label}</span>
                        <span className="preset-card-desc">{meta.description}</span>
                        {name === specs.recommended_preset && (
                          <span className="preset-card-badge">Recomendado para esta máquina</span>
                        )}
                      </button>
                    );
                  })}
                </div>

                <button
                  className="btn btn-tertiary"
                  style={{ marginTop: "0.75rem" }}
                  onClick={() => setAdvancedOpen((o) => !o)}
                >
                  {advancedOpen ? "Ocultar configuración avanzada" : "Configuración avanzada"}
                </button>

                {advancedOpen && effective && (
                  <div className="advanced-panel">
                    <div className="advanced-field">
                      <label>Modelo Whisper</label>
                      <select
                        className="select-field"
                        value={draftOverrides.WHISPER_MODEL_SIZE ?? effective.WHISPER_MODEL_SIZE}
                        onChange={(e) => updateOverride("WHISPER_MODEL_SIZE", e.target.value)}
                      >
                        {WHISPER_MODEL_SIZES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                    <div className="advanced-field">
                      <label>Modelo NLLB</label>
                      <select
                        className="select-field"
                        value={draftOverrides.NLLB_MODEL_SIZE ?? effective.NLLB_MODEL_SIZE}
                        onChange={(e) => updateOverride("NLLB_MODEL_SIZE", e.target.value)}
                      >
                        {NLLB_MODEL_SIZES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                    <div className="advanced-field">
                      <label>Whisper beam size</label>
                      <input
                        type="number" min={1} max={10} className="input-field"
                        value={draftOverrides.WHISPER_BEAM_SIZE ?? effective.WHISPER_BEAM_SIZE}
                        onChange={(e) => updateOverride("WHISPER_BEAM_SIZE", Number(e.target.value))}
                      />
                    </div>
                    <div className="advanced-field">
                      <label>Whisper best_of</label>
                      <input
                        type="number" min={1} max={10} className="input-field"
                        value={draftOverrides.WHISPER_BEST_OF ?? effective.WHISPER_BEST_OF}
                        onChange={(e) => updateOverride("WHISPER_BEST_OF", Number(e.target.value))}
                      />
                    </div>
                    <div className="advanced-field">
                      <label>NLLB beam size</label>
                      <input
                        type="number" min={1} max={10} className="input-field"
                        value={draftOverrides.NLLB_BEAM_SIZE ?? effective.NLLB_BEAM_SIZE}
                        onChange={(e) => updateOverride("NLLB_BEAM_SIZE", Number(e.target.value))}
                      />
                    </div>
                    <div className="advanced-field">
                      <label>NLLB batch size</label>
                      <input
                        type="number" min={1} max={64} className="input-field"
                        value={draftOverrides.NLLB_BATCH_SIZE ?? effective.NLLB_BATCH_SIZE}
                        onChange={(e) => updateOverride("NLLB_BATCH_SIZE", Number(e.target.value))}
                      />
                    </div>
                    <div className="advanced-field">
                      <label>NLLB repetition penalty</label>
                      <input
                        type="number" min={1} max={2} step={0.05} className="input-field"
                        value={draftOverrides.NLLB_REPETITION_PENALTY ?? effective.NLLB_REPETITION_PENALTY}
                        onChange={(e) => updateOverride("NLLB_REPETITION_PENALTY", Number(e.target.value))}
                      />
                    </div>
                    <div className="advanced-field">
                      <label>NLLB no-repeat n-gram</label>
                      <input
                        type="number" min={0} max={10} className="input-field"
                        value={draftOverrides.NLLB_NO_REPEAT_NGRAM ?? effective.NLLB_NO_REPEAT_NGRAM}
                        onChange={(e) => updateOverride("NLLB_NO_REPEAT_NGRAM", Number(e.target.value))}
                      />
                    </div>
                    <div className="checkbox-group advanced-field-checkbox">
                      <label>
                        <input
                          type="checkbox"
                          checked={draftOverrides.NLLB_CONTEXT_AWARE ?? effective.NLLB_CONTEXT_AWARE}
                          onChange={(e) => updateOverride("NLLB_CONTEXT_AWARE", e.target.checked)}
                        />
                        <span>Traducción con contexto entre grupos (DP grouper)</span>
                      </label>
                    </div>

                    <div className="button-group" style={{ marginTop: "0.75rem" }}>
                      <button
                        className={`btn btn-primary${saving ? " loading" : ""}`}
                        disabled={saving}
                        onClick={handleSaveAdvanced}
                      >
                        Guardar avanzado
                      </button>
                      <button
                        className="btn btn-secondary"
                        disabled={saving || !hasOverrides}
                        onClick={() => setDraftOverrides({})}
                      >
                        Restaurar valores del preset
                      </button>
                    </div>
                  </div>
                )}

                {restartRequired && (
                  <InfoBox kind="warning">
                    Reinicia el servidor para aplicar los cambios — los modelos ya están
                    cargados en memoria y no se recargan en caliente.
                  </InfoBox>
                )}
              </>
            )}

            {error && <InfoBox kind="error">{error}</InfoBox>}
          </div>
        )}
      </section>
    </div>
  );
}
