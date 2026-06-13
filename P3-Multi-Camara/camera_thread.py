# ─────────────────────────────────────────────────────────────────────────────
# camera_thread.py — Hilo de captura + MediaPipe por cámara
# P3 · Aún Sorprendo · JIFREX
#
# Cada cámara corre en su propio hilo daemon independiente.
# El hilo principal lee CameraResult.latest sin bloqueo.
#
# Cámara A (OAK-D Pro W): usa DepthAI SDK. Si no está disponible,
#   hace fallback a cv2.VideoCapture en CAM_A_FALLBACK_IDX.
# Cámaras B y C (Logitech C922): cv2.VideoCapture directa.
#
# Si la cámara no está disponible: modo simulación con silueta sintética animada.
# ─────────────────────────────────────────────────────────────────────────────

import threading
import time
import numpy as np
import cv2

try:
    import mediapipe as mp
    _MP_AVAILABLE = True
except ImportError:
    _MP_AVAILABLE = False
    print("[CameraThread] MediaPipe no disponible — usando simulacion")

import config


class CameraResult:
    """Resultado inmutable de un frame de una cámara."""
    __slots__ = ("timestamp_ms", "mask", "flow_mean", "motion_ratio", "presence", "frame_bgr")

    def __init__(self, ts: int, mask: np.ndarray, flow: float,
                 motion: float, presence: int, frame: np.ndarray):
        self.timestamp_ms = ts
        self.mask         = mask
        self.flow_mean    = flow
        self.motion_ratio = motion
        self.presence     = presence
        self.frame_bgr    = frame


class CameraThread(threading.Thread):
    """
    Hilo dedicado a una cámara. Produce CameraResult accesible via get_latest().

    Parámetros:
        cam_id   — "A", "B", o "C"
        cam_name — nombre descriptivo para logging
        source   — índice int para C922, None para OAK-D Pro W
        use_oak  — True = intentar DepthAI SDK antes de fallback
    """

    def __init__(self, cam_id: str, cam_name: str, source, use_oak: bool = False):
        super().__init__(daemon=True, name=f"cam-{cam_name}")
        self.cam_id      = cam_id
        self.cam_name    = cam_name
        self.source      = source
        self.use_oak     = use_oak
        self._lock       = threading.Lock()
        self._latest: CameraResult | None = None
        self._stop       = threading.Event()
        self._prev_gray  = None
        self._mp_holistic = None

    def get_latest(self) -> "CameraResult | None":
        with self._lock:
            return self._latest

    def stop(self):
        self._stop.set()

    # ── MediaPipe ─────────────────────────────────────────────────────────────

    def _init_mediapipe(self):
        if not _MP_AVAILABLE:
            return
        mp_holistic = mp.solutions.holistic
        self._mp_holistic = mp_holistic.Holistic(
            model_complexity=config.MP_MODEL_COMPLEXITY,
            min_detection_confidence=config.MP_MIN_DETECTION_CONF,
            min_tracking_confidence=config.MP_MIN_TRACKING_CONF,
            enable_segmentation=config.MP_ENABLE_SEGMENTATION,
            smooth_segmentation=config.MP_SMOOTH_SEGMENTATION,
        )

    def _segment(self, frame_rgb: np.ndarray, mp_result) -> np.ndarray:
        """Extrae máscara de segmentación limpia de MediaPipe (uint8 0/255)."""
        h, w = frame_rgb.shape[:2]
        if mp_result is not None and mp_result.segmentation_mask is not None:
            raw = (mp_result.segmentation_mask > config.MASK_THRESHOLD).astype(np.uint8) * 255
        else:
            raw = np.zeros((h, w), dtype=np.uint8)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask   = cv2.morphologyEx(raw, cv2.MORPH_OPEN, kernel)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    # ── Optical Flow ──────────────────────────────────────────────────────────

    def _optical_flow(self, gray: np.ndarray) -> tuple[float, float]:
        """Devuelve (flow_mean, motion_ratio) respecto al frame anterior."""
        if self._prev_gray is None:
            self._prev_gray = gray
            return 0.0, 0.0
        flow = cv2.calcOpticalFlowFarneback(
            self._prev_gray, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        self._prev_gray = gray
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        return float(np.mean(mag)), float(np.mean(mag > 1.0))

    # ── Simulación ────────────────────────────────────────────────────────────

    def _simulate_frame(self) -> tuple[np.ndarray, np.ndarray, float, float, int]:
        """Silueta elíptica animada para desarrollo sin hardware."""
        h, w = config.FRAME_HEIGHT, config.FRAME_WIDTH
        t    = time.time()
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        # Cada cámara tiene posición ligeramente distinta para que el efecto
        # de triple coincidencia sea visible en simulación
        offsets = {"A": 0.0, "B": 0.1, "C": -0.1}
        ox = offsets.get(self.cam_id, 0.0)
        cx = int(w * (0.5 + ox + np.sin(t * 0.4 + ord(self.cam_id)) * 0.08))
        cy = int(h * 0.5)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.ellipse(mask, (cx, cy), (60, 130), 0, 0, 360, 255, -1)
        flow_mean    = abs(np.sin(t * 1.2 + ord(self.cam_id))) * 1.5
        motion_ratio = abs(np.sin(t * 0.8 + ord(self.cam_id))) * 0.5
        presence     = 1
        return frame, mask, flow_mean, motion_ratio, presence

    def _publish(self, ts: int, frame_bgr: np.ndarray, mask: np.ndarray,
                 fm: float, mr: float, presence: int):
        result = CameraResult(ts, mask, fm, mr, presence, frame_bgr)
        with self._lock:
            self._latest = result

    # ── Backends de captura ───────────────────────────────────────────────────

    def _run_webcam(self):
        """Captura con cv2.VideoCapture (Logitech C922 o fallback)."""
        cap = cv2.VideoCapture(self.source if self.source is not None else 0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)
        use_real = cap.isOpened()
        if not use_real:
            print(f"[{self.cam_name}] Camara {self.source} no disponible — simulacion")
        self._init_mediapipe()

        while not self._stop.is_set():
            ts = int(time.time() * 1000)
            if use_real:
                ok, frame_bgr = cap.read()
                if not ok:
                    frame_bgr, mask, fm, mr, presence = self._simulate_frame()
                else:
                    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                    gray      = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                    mp_result = self._mp_holistic.process(frame_rgb) if self._mp_holistic else None
                    mask      = self._segment(frame_rgb, mp_result)
                    fm, mr    = self._optical_flow(gray)
                    presence  = 1 if np.any(mask > 0) else 0
            else:
                frame_bgr, mask, fm, mr, presence = self._simulate_frame()

            self._publish(ts, frame_bgr, mask, fm, mr, presence)

        if cap.isOpened():
            cap.release()
        if self._mp_holistic:
            self._mp_holistic.close()

    def _run_oak(self):
        """Captura con OAK-D Pro W vía DepthAI SDK."""
        try:
            import depthai as dai

            pipeline = dai.Pipeline()
            cam_rgb  = pipeline.create(dai.node.ColorCamera)
            cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_720_P)
            cam_rgb.setFps(config.TARGET_FPS)
            cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
            xout = pipeline.create(dai.node.XLinkOut)
            xout.setStreamName("rgb")
            cam_rgb.video.link(xout.input)

            self._init_mediapipe()
            print(f"[{self.cam_name}] OAK-D Pro W conectada via DepthAI")

            with dai.Device(pipeline) as device:
                q = device.getOutputQueue("rgb", maxSize=4, blocking=False)
                while not self._stop.is_set():
                    in_rgb = q.tryGet()
                    if in_rgb is None:
                        time.sleep(0.001)
                        continue
                    ts        = int(time.time() * 1000)
                    frame_bgr = in_rgb.getCvFrame()
                    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                    gray      = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                    mp_result = self._mp_holistic.process(frame_rgb) if self._mp_holistic else None
                    mask      = self._segment(frame_rgb, mp_result)
                    fm, mr    = self._optical_flow(gray)
                    presence  = 1 if np.any(mask > 0) else 0
                    self._publish(ts, frame_bgr, mask, fm, mr, presence)

        except ImportError:
            print(f"[{self.cam_name}] DepthAI no instalado — fallback a webcam")
            self.source = config.CAM_A_FALLBACK_IDX
            self._run_webcam()
            return
        except Exception as e:
            print(f"[{self.cam_name}] OAK-D error ({e}) — fallback a webcam")
            self.source = config.CAM_A_FALLBACK_IDX
            self._run_webcam()
            return

        if self._mp_holistic:
            self._mp_holistic.close()

    # ── Thread entry point ────────────────────────────────────────────────────

    def run(self):
        print(f"[{self.cam_name}] Hilo iniciado (oak={self.use_oak})")
        if self.use_oak:
            self._run_oak()
        else:
            self._run_webcam()
        print(f"[{self.cam_name}] Hilo terminado")
