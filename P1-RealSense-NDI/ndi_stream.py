"""
ndi_stream.py — Emite la máscara como fuente NDI visible en TouchDesigner.
Latencia objetivo: ~8 ms en red local.
"""

import numpy as np
import cv2
import config

try:
    import NDIlib as ndi
    _NDI_OK = True
except Exception as e:
    _NDI_OK = False
    print(f"[NDI] No disponible: {e}")


class NDIStream:
    def __init__(self):
        self._send = None
        if not _NDI_OK:
            return

        if not ndi.initialize():
            print("[NDI] Error al inicializar NDIlib.")
            return

        settings = ndi.SendCreate()
        settings.ndi_name = config.NDI_SOURCE_NAME
        self._send = ndi.send_create(settings)

        if self._send:
            print(f"[NDI] Fuente activa: '{config.NDI_SOURCE_NAME}'")
        else:
            print("[NDI] No se pudo crear fuente.")

    def send_frame(self, frame_bgr: np.ndarray):
        if not self._send:
            return

        h, w = frame_bgr.shape[:2]
        frame_rgba = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGBA)

        vf = ndi.VideoFrameV2()
        vf.data       = frame_rgba
        vf.FourCC     = ndi.FOURCC_VIDEO_TYPE_RGBA
        vf.xres       = w
        vf.yres       = h
        vf.frame_rate_N = config.FPS
        vf.frame_rate_D = 1

        ndi.send_send_video_v2(self._send, vf)

    def destroy(self):
        if _NDI_OK and self._send:
            ndi.send_destroy(self._send)
            ndi.destroy()
            print("[NDI] Fuente cerrada.")
