# ─────────────────────────────────────────────────────────────────────────────
# syphon_share.py — Servidor Syphon (1 textura de alta precisión)
# P4 · Aún Sorprendo · JIFREX
#
# macOS ONLY. En otros sistemas: no-op silencioso.
# La textura que se envía es la máscara DeepLabv3 — bordes subpixel-accurate.
# ─────────────────────────────────────────────────────────────────────────────

import sys
import numpy as np


class SyphonShare:
    """
    Un servidor Syphon para la máscara DeepLabv3.
    Fallback silencioso si syphon-python no está instalado.
    """

    def __init__(self, server_name: str):
        self.backend     = "none"
        self._server     = None
        self._name       = server_name

        if sys.platform != "darwin":
            print("[SyphonShare] No es macOS — Syphon deshabilitado (no-op)")
            return

        try:
            import syphon
            self._server = syphon.SyphonServer(server_name)
            self.backend = "syphon"
            print(f"[SyphonShare] Activo: '{server_name}'")
        except ImportError:
            print("[SyphonShare] syphon-python no instalado — no-op. "
                  "Instalar: pip install syphon-python")
        except Exception as e:
            print(f"[SyphonShare] Error: {e} — no-op")

    def send(self, mask: np.ndarray):
        """Envía la máscara binaria DeepLabv3 como textura RGBA."""
        if self.backend != "syphon" or self._server is None:
            return
        h, w = mask.shape[:2]
        alpha = mask.astype(np.float32) / 255.0
        rgba  = np.stack([alpha, alpha, alpha, alpha], axis=-1)
        try:
            self._server.publish_frame_texture(rgba)
        except Exception:
            pass

    def close(self):
        if self._server is not None:
            try:
                self._server.stop()
            except Exception:
                pass
