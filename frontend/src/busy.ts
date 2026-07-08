// Contador global de tareas activas — el Header lo usa para acelerar el
// polling de GPU stats (4s con tareas en curso, 30s en idle).
// Store externo mínimo compatible con useSyncExternalStore.

let activeTasks = 0;
const listeners = new Set<() => void>();

export function getBusyCount(): number {
  return activeTasks;
}

export function subscribeBusy(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function setBusy(delta: number): void {
  activeTasks = Math.max(0, activeTasks + delta);
  listeners.forEach((l) => l());
}

/** Envuelve una promesa marcando la app como ocupada mientras dura. */
export async function tracked<T>(promise: Promise<T>): Promise<T> {
  setBusy(1);
  try {
    return await promise;
  } finally {
    setBusy(-1);
  }
}
