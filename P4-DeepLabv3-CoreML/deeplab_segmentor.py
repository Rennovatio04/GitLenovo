# ─────────────────────────────────────────────────────────────────────────────
# deeplab_segmentor.py — Wrapper de inferencia DeepLabv3
# P4 · Aún Sorprendo · JIFREX
#
# Backends disponibles (en orden de prioridad):
#   1. CoreML   — macOS + Neural Engine M3 Max (15–25 ms/frame) ← ÓPTIMO
#   2. TF       — TensorFlow CPU/CUDA fallback (~50–80 ms/frame en CPU)
#   3. Simulate — Silueta sintética animada para desarrollo sin hardware/modelo
#
# El backend se detecta automáticamente según la plataforma y los paquetes
# instalados. No hay que cambiar código para pasar de desarrollo a producción.
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import time
import numpy as np
import cv2

import config


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_project_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_DIR, path)


class DeepLabSegmentor:
    """
    Segmentador semántico basado en DeepLabv3 MobileNetV2.

    Clase 15 PASCAL VOC = "person".
    Devuelve máscara binaria uint8 en la resolución original de la cámara
    (resize desde 513×513 con interpolación NEAREST para preservar bordes).
    """

    def __init__(self):
        self.backend    = "simulate"
        self._model     = None
        self._t_last    = 0.0
        self._input_sz  = config.DEEPLAB_INPUT_SIZE  # 513
        self._model_path = resolve_project_path(config.COREML_MODEL_PATH)

        self._init_backend()

    def _init_backend(self):
        """Detecta y carga el backend disponible."""

        # 1. Intentar CoreML (macOS M3 Max)
        if sys.platform == "darwin":
            try:
                import coremltools as ct
                if os.path.exists(self._model_path):
                    self._model  = ct.models.MLModel(self._model_path)
                    self.backend = "coreml"
                    print(f"[DeepLab] Backend: CoreML → {self._model_path}")
                    print("[DeepLab] Neural Engine M3 Max — latencia esperada: 15–25 ms/frame")
                    return
                else:
                    print(f"[DeepLab] {self._model_path} no encontrado")
                    print("[DeepLab] Ejecutar: python convert_to_coreml.py")
            except ImportError:
                print("[DeepLab] coremltools no instalado")

        # 2. Intentar TensorFlow (cualquier plataforma — más lento)
        try:
            import tensorflow as tf
            import tensorflow_hub as hub
            print("[DeepLab] Backend: TensorFlow Hub (CPU/GPU) — más lento que CoreML")
            self._tf  = tf
            self._hub = hub
            self._hub_model = hub.load("https://tfhub.dev/tensorflow/deeplabv3/1")
            self.backend     = "tensorflow"
            print("[DeepLab] TF Hub cargado — primera inferencia será lenta (~3 s)")
            return
        except (ImportError, Exception) as e:
            print(f"[DeepLab] TensorFlow no disponible: {e}")

        # 3. Simulación
        print("[DeepLab] Backend: simulación (sin modelo real)")
        self.backend = "simulate"

    # ── Inferencia ─────────────────────────────────────────────────────────────

    def segment(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Segmenta un frame BGR y devuelve máscara binaria uint8 en la
        misma resolución que el frame de entrada.

        Retorna: np.ndarray uint8 (H×W), valores 0 o 255
        """
        h, w = frame_bgr.shape[:2]

        if self.backend == "coreml":
            return self._infer_coreml(frame_bgr, h, w)
        elif self.backend == "tensorflow":
            return self._infer_tf(frame_bgr, h, w)
        else:
            return self._simulate(h, w)

    def _preprocess(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Preprocesamiento estándar DeepLabv3: resize 513×513, normalizar [0,1]."""
        sz = self._input_sz
        resized = cv2.resize(frame_bgr, (sz, sz), interpolation=cv2.INTER_LINEAR)
        rgb     = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        return rgb.astype(np.float32) / 255.0

    def _postprocess(self, class_map: np.ndarray, h: int, w: int) -> np.ndarray:
        """
        Extrae clase 15 (person) y hace upsample a resolución original.
        Usa INTER_NEAREST para preservar bordes subpixel-accurate.
        Aplica morfología para limpiar artefactos de borde.
        """
        person = (class_map == config.PERSON_CLASS_ID).astype(np.uint8) * 255
        upsampled = cv2.resize(person, (w, h), interpolation=cv2.INTER_NEAREST)
        kernel    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned   = cv2.morphologyEx(upsampled, cv2.MORPH_OPEN, kernel)
        cleaned   = cv2.morphologyEx(cleaned,   cv2.MORPH_CLOSE, kernel)
        return cleaned

    def _infer_coreml(self, frame_bgr: np.ndarray, h: int, w: int) -> np.ndarray:
        """Inferencia via CoreML en Neural Engine M3 Max."""
        from PIL import Image
        sz      = self._input_sz
        resized = cv2.resize(frame_bgr, (sz, sz))
        rgb_pil = Image.fromarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))

        result    = self._model.predict({"ImageTensor": rgb_pil})

        # El modelo puede devolver SemanticPredictions (class indices) o PersonMask
        if "PersonMask" in result:
            person_small = (result["PersonMask"].squeeze() > config.MASK_THRESHOLD)
            person_small = person_small.astype(np.uint8) * 255
            return cv2.resize(person_small, (w, h), interpolation=cv2.INTER_NEAREST)
        elif "SemanticPredictions" in result:
            class_map = result["SemanticPredictions"].squeeze().astype(np.int32)
            return self._postprocess(class_map, h, w)
        else:
            # Fallback: primer output disponible
            first_key = list(result.keys())[0]
            arr = result[first_key].squeeze()
            if arr.ndim == 2:
                return self._postprocess(arr.astype(np.int32), h, w)
            return np.zeros((h, w), dtype=np.uint8)

    def _infer_tf(self, frame_bgr: np.ndarray, h: int, w: int) -> np.ndarray:
        """Inferencia via TensorFlow Hub (fallback — más lento)."""
        tf  = self._tf
        sz  = self._input_sz
        inp = self._preprocess(frame_bgr)
        inp_t = tf.constant(inp[np.newaxis], dtype=tf.float32)

        result    = self._hub_model(inp_t)
        class_map = tf.math.argmax(result["default"], axis=-1).numpy().squeeze()
        return self._postprocess(class_map, h, w)

    def _simulate(self, h: int, w: int) -> np.ndarray:
        """Silueta sintética de alta calidad para desarrollo sin modelo."""
        t    = time.time()
        mask = np.zeros((h, w), dtype=np.uint8)
        # Silueta humana estilizada (elipse + cabeza)
        cx = int(w * 0.5 + np.sin(t * 0.35) * w * 0.12)
        cy = int(h * 0.5)
        # Tronco
        cv2.ellipse(mask, (cx, cy), (int(w * 0.055), int(h * 0.28)), 0, 0, 360, 255, -1)
        # Cabeza
        cv2.circle(mask, (cx, int(cy - h * 0.30)), int(w * 0.035), 255, -1)
        # Brazos: simulan movimiento
        arm_angle = np.sin(t * 0.8) * 40
        for side in [-1, 1]:
            ax = cx + int(side * w * 0.09)
            ay = int(cy - h * 0.05)
            cv2.ellipse(mask, (ax, ay), (int(w * 0.018), int(h * 0.12)),
                        arm_angle * side, 0, 360, 255, -1)
        return mask

    def latency_ms(self) -> float:
        """Latencia de la última inferencia en ms (solo informativo)."""
        return self._t_last * 1000.0
