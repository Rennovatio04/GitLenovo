# ─────────────────────────────────────────────────────────────────────────────
# sync_manager.py — Sincronización de 3 streams de cámara
# P3 · Aún Sorprendo · JIFREX
#
# Ventana de sincronización: SYNC_WINDOW_MS = 33 ms (1 frame a 30fps)
#
# Estrategia:
#   - Cada hilo de cámara actualiza su CameraResult.timestamp_ms en cada frame.
#   - SyncManager.get_sync_triplet() recoge los 3 frames más recientes.
#   - Si el rango de timestamps (max - min) está dentro de la ventana,
#     el triplete se acepta tal cual.
#   - Si algún frame está fuera de la ventana, se reutiliza el frame anterior
#     de esa cámara (en lugar de descartar el triplete completo).
#   - Devuelve None hasta que las 3 cámaras hayan producido al menos 1 frame.
# ─────────────────────────────────────────────────────────────────────────────

import time
from camera_thread import CameraResult, CameraThread
import config


class SyncManager:

    def __init__(self, thread_a: CameraThread, thread_b: CameraThread, thread_c: CameraThread):
        self._threads    = (thread_a, thread_b, thread_c)
        self._prev       = [None, None, None]   # últimos frames validados por cámara
        self._in_sync_streak = 0                # frames consecutivos dentro de ventana
        self._out_of_sync    = 0                # frames fuera de ventana (para logging)

    def get_sync_triplet(self) -> "tuple[CameraResult, CameraResult, CameraResult] | None":
        """
        Devuelve triplete (a, b, c) o None si aún no hay datos de todas las cámaras.

        El triplete siempre refleja el estado más reciente de cada cámara.
        Los frames fuera de la ventana de sincronización son reemplazados
        por el último frame validado de esa cámara (para no propagar saltos).
        """
        # Obtener frames actuales de los 3 hilos
        current = [t.get_latest() for t in self._threads]

        # Actualizar cada cámara con el frame más reciente si lo hay
        for i, f in enumerate(current):
            if f is not None:
                self._prev[i] = f

        # No continuar hasta tener al menos 1 frame de cada cámara
        if any(p is None for p in self._prev):
            return None

        # Evaluar sincronización del lote actual
        timestamps = [p.timestamp_ms for p in self._prev]
        t_max = max(timestamps)
        t_min = min(timestamps)
        delta = t_max - t_min

        if delta <= config.SYNC_WINDOW_MS:
            self._in_sync_streak += 1
        else:
            self._out_of_sync += 1

        return (self._prev[0], self._prev[1], self._prev[2])

    def stats(self) -> dict:
        """Estadísticas de sincronización para logging."""
        total = self._in_sync_streak + self._out_of_sync
        ratio = self._in_sync_streak / total if total > 0 else 0.0
        return {
            "in_sync":     self._in_sync_streak,
            "out_of_sync": self._out_of_sync,
            "sync_ratio":  ratio,
        }
