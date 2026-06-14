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
        self._threads = (thread_a, thread_b, thread_c)
        self._validated = [None, None, None]    # últimos frames aceptados por cámara
        self._in_sync = 0
        self._out_of_sync = 0

    def get_sync_triplet(self, sync_window_ms: int | None = None) -> "tuple[CameraResult, CameraResult, CameraResult] | None":
        """
        Devuelve triplete (a, b, c) o None si aún no hay datos de todas las cámaras.

        Si una cámara llega fuera de la ventana de sincronización, conserva
        el último frame validado de esa cámara para no propagar saltos.
        """
        current = [t.get_latest() for t in self._threads]
        for i, frame in enumerate(current):
            if self._validated[i] is None and frame is not None:
                self._validated[i] = frame

        if any(frame is None for frame in self._validated):
            return None

        window = config.SYNC_WINDOW_MS if sync_window_ms is None else int(sync_window_ms)
        reference_ts = max(
            (frame.timestamp_ms for frame in current if frame is not None),
            default=max(frame.timestamp_ms for frame in self._validated if frame is not None),
        )

        selected = []
        for i, live_frame in enumerate(current):
            candidate = live_frame if live_frame is not None else self._validated[i]
            if candidate is not None and reference_ts - candidate.timestamp_ms <= window:
                selected.append(candidate)
            else:
                selected.append(self._validated[i])

        if any(frame is None for frame in selected):
            return None

        timestamps = [frame.timestamp_ms for frame in selected]
        t_max = max(timestamps)
        t_min = min(timestamps)
        delta = t_max - t_min

        if delta <= window:
            self._validated = list(selected)
            self._in_sync += 1
            return (selected[0], selected[1], selected[2])

        self._out_of_sync += 1
        return None

    def stats(self) -> dict:
        """Estadísticas de sincronización para logging."""
        total = self._in_sync + self._out_of_sync
        ratio = self._in_sync / total if total > 0 else 0.0
        return {
            "in_sync":     self._in_sync,
            "out_of_sync": self._out_of_sync,
            "sync_ratio":  ratio,
        }
