# ─────────────────────────────────────────────────────────────────────────────
# syphon_share.py — 3 servidores Syphon para texturas de cámara
# P3 · Aún Sorprendo · JIFREX
#
# macOS ONLY (Mac M3 Max). En Windows o si syphon-python no está instalado,
# los envíos son no-op y el runtime continúa funcionando via OSC.
#
# Instalación en macOS:
#   pip install syphon-python
#
# En TouchDesigner: Syphon In TOP con nombre igual a SYPHON_SERVER_A/B/C
# ─────────────────────────────────────────────────────────────────────────────

import sys
import numpy as np


class SyphonShare:
    """
    Gestiona 3 servidores Syphon independientes (uno por cámara).
    Cada textura es una máscara binaria en escala de grises enviada como RGBA.

    Si syphon-python no está disponible, todos los métodos son no-op.
    El pipeline de OSC + MediaPipe sigue funcionando — solo falta el video.
    """

    def __init__(self, name_a: str, name_b: str, name_c: str):
        self.backend  = "none"
        self._servers = [None, None, None]
        self._names   = [name_a, name_b, name_c]

        if sys.platform != "darwin":
            print("[SyphonShare] No es macOS — Syphon deshabilitado (no-op)")
            return

        try:
            import syphon
            self._syphon = syphon
            self._servers = [
                syphon.SyphonServer(name_a),
                syphon.SyphonServer(name_b),
                syphon.SyphonServer(name_c),
            ]
            self.backend = "syphon"
            print(f"[SyphonShare] Activo: '{name_a}' | '{name_b}' | '{name_c}'")
        except ImportError:
            print("[SyphonShare] syphon-python no instalado — no-op. "
                  "Instalar con: pip install syphon-python")
        except Exception as e:
            print(f"[SyphonShare] Error al iniciar servidores Syphon: {e} — no-op")

    def send(self, mask_a: np.ndarray, mask_b: np.ndarray, mask_c: np.ndarray):
        """
        Envía las 3 máscaras como texturas RGBA a TouchDesigner vía Syphon.
        Si el backend no está disponible, es no-op silencioso.
        """
        if self.backend != "syphon":
            return
        for server, mask in zip(self._servers, (mask_a, mask_b, mask_c)):
            if server is None:
                continue
            h, w = mask.shape[:2]
            # Máscara uint8 (HxW) → RGBA float32 (todos los canales = gris)
            alpha  = mask.astype(np.float32) / 255.0
            rgba   = np.stack([alpha, alpha, alpha, alpha], axis=-1)
            try:
                server.publish_frame_texture(rgba)
            except Exception:
                pass  # no interrumpir el runtime por error de Syphon

    def close(self):
        for server in self._servers:
            if server is not None:
                try:
                    server.stop()
                except Exception:
                    pass
