"""
skeleton_runtime.py — Pipeline principal P2 · 30 fps · una sola máquina (MSI o Mac)
Aún Sorprendo · Exposición Pablo Picasso · JIFREX
Galería Universitaria Fernando Cano · UAEMEx / FUNIBER

A diferencia de P1 (RealSense + presencia binaria), P2 usa webcam RGB normal +
MediaPipe Holistic para extraer 17 joints semánticos y decidir QUÉ PARTE del
cuerpo se mueve. Genera 6 triggers semánticos y detecta hasta 2 personas.

Pipeline por frame:
  1. Captura webcam RGB 1080p
  2. MediaPipe Holistic → pose landmarks (33) + máscara de segmentación
  3. Optical Flow Farneback → flow_mean + motion_ratio (movimiento global)
  4. Conteo de personas (blob_count) vía máscara de segmentación
  5. zone_detector → 6 triggers semánticos (manos, cadera, cabeza, salto,
     pose estática, 2 personas)
  6. OSC semántico → TouchDesigner (:9000)
  7. Spout (Windows) / Syphon (macOS) → overlay esqueleto+máscara hacia TD GPU→GPU

Modo simulación: si MediaPipe o la webcam no están disponibles, genera datos
sintéticos para poder desarrollar y verificar el resto del pipeline.
"""

import sys
import time
import platform

import cv2
import numpy as np

# Consola UTF-8 robusta (evita UnicodeEncodeError con '→', '·' en cp1252/Windows).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

import config
from osc_client import OSCClient
from zone_detector import ZoneDetector
from mcp_bridge import start as start_mcp, get_live_params

# ── MediaPipe (opcional para modo simulación) ─────────────────────────────────
try:
    import mediapipe as mp
    _MP_OK = True
except ImportError:
    _MP_OK = False
    print("[MP] mediapipe no disponible — modo simulación activo.")

# ── Compartir frame GPU→GPU (Spout en Windows, Syphon en macOS) ───────────────
_IS_WINDOWS = platform.system() == "Windows"
_IS_MACOS   = platform.system() == "Darwin"


class FrameShare:
    """
    Abstracción Spout/Syphon. Comparte el overlay del esqueleto con TouchDesigner
    por GPU sin pasar por disco ni red (~1 ms). Si la librería nativa no está
    instalada, degrada silenciosamente a no-op (el sistema sigue por OSC).
    """

    def __init__(self, name: str, width: int, height: int):
        self._sender = None
        self._backend = "none"
        self._w, self._h = width, height
        if not config.SHARE_ENABLE:
            return
        try:
            if _IS_WINDOWS:
                # SpoutGL: https://pypi.org/project/SpoutGL/
                import SpoutGL
                self._spout = SpoutGL.SpoutSender()
                self._spout.setSenderName(name)
                self._sender = self._spout
                self._backend = "spout"
            elif _IS_MACOS:
                # syphon-python: https://pypi.org/project/syphon-python/
                import syphon
                from syphon.utils.numpy import copy_image_to_mtl_texture
                from syphon.utils.raw import create_mtl_texture
                self._syphon_mod = syphon
                self._copy = copy_image_to_mtl_texture
                self._texture = create_mtl_texture(
                    syphon.utils.raw.create_mtl_device(), width, height)
                self._sender = syphon.SyphonMetalServer(name)
                self._backend = "syphon"
        except Exception as exc:   # noqa: BLE001 — degradación intencional
            print(f"[SHARE] backend no disponible ({exc}) — sin GPU share.")
            self._sender = None
            self._backend = "none"
        print(f"[SHARE] backend = {self._backend} · fuente = '{name}'")

    def send(self, bgr: np.ndarray):
        if self._sender is None:
            return
        try:
            if self._backend == "spout":
                rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
                self._spout.sendImage(
                    rgba.tobytes(), self._w, self._h, 0x1908, False, 0)  # GL_RGBA
            elif self._backend == "syphon":
                rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
                self._copy(rgba, self._texture)
                self._sender.publish_frame_texture(self._texture)
        except Exception as exc:   # noqa: BLE001
            print(f"[SHARE] error de envío: {exc}")

    def destroy(self):
        try:
            if self._backend == "spout":
                self._spout.releaseSender()
            elif self._backend == "syphon":
                self._sender.stop()
        except Exception:   # noqa: BLE001
            pass


# ── Cámara ────────────────────────────────────────────────────────────────────

def open_camera():
    cap = cv2.VideoCapture(config.CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          config.FPS)
    return cap


# ── Extracción de landmarks ───────────────────────────────────────────────────

def landmarks_to_dict(pose_landmarks, width, height):
    """
    Convierte los pose_landmarks de MediaPipe a {idx: (x, y, z, visibility)}
    en coordenadas normalizadas (0..1). Solo conserva los índices semánticos
    que usamos (config.LM), pero el dict admite cualquier índice.
    """
    if pose_landmarks is None:
        return None
    out = {}
    for idx in config.LM.values():
        lm = pose_landmarks.landmark[idx]
        out[idx] = (lm.x, lm.y, lm.z, lm.visibility)
    return out


# ── Optical Flow (movimiento global) ──────────────────────────────────────────

def optical_flow(prev_gray, curr_gray):
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
    )
    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    flow_mean    = float(np.mean(mag))
    motion_ratio = float(np.count_nonzero(mag > 1.0) / mag.size)
    return flow_mean, motion_ratio


# ── Conteo de personas (trigger 6) ────────────────────────────────────────────

def count_people(seg_mask, params):
    """
    Trigger 6 — 2 personas simultáneas.
    A partir de la máscara de segmentación de MediaPipe Holistic, cuenta blobs
    de persona y verifica que haya al menos dos centros de masa separados.

    Devuelve (blob_count, centros) donde centros es lista de (cx, cy) normalizados.
    """
    if seg_mask is None:
        return 1, []

    h, w = seg_mask.shape[:2]
    binary = (seg_mask > config.SEG_THRESHOLD).astype(np.uint8) * 255
    k = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (config.SEG_MORPH_KERNEL, config.SEG_MORPH_KERNEL))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  k, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k, iterations=2)

    n, _, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

    centers = []
    for i in range(1, n):   # 0 es el fondo
        if stats[i, cv2.CC_STAT_AREA] >= config.BLOB_MIN_AREA:
            cx, cy = centroids[i]
            centers.append((cx / w, cy / h))

    # Dos personas reales: 2+ centros separados más que el umbral.
    sep_thr = params.get("dual_min_separation", config.DUAL_MIN_SEPARATION)
    blob_count = 1
    if len(centers) >= 2:
        centers_sorted = sorted(centers, key=lambda c: c[0])
        max_sep = 0.0
        for a in range(len(centers_sorted)):
            for b in range(a + 1, len(centers_sorted)):
                d = abs(centers_sorted[a][0] - centers_sorted[b][0])
                max_sep = max(max_sep, d)
        if max_sep >= sep_thr:
            blob_count = 2

    return blob_count, centers


# ── Overlay del esqueleto (lo que se comparte por Spout/Syphon) ───────────────

def draw_overlay(frame, lm_dict, seg_mask, centers):
    """
    Dibuja el esqueleto semántico sobre fondo oscuro + tinte de la máscara de
    persona. Esta es la textura que TouchDesigner consume para los shaders.
    """
    h, w = frame.shape[:2]
    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    # Tinte de la máscara de persona (azul frío tenue, base cubista).
    if seg_mask is not None:
        m = (seg_mask > config.SEG_THRESHOLD).astype(np.uint8)
        canvas[:, :, 0] = m * 40   # B
        canvas[:, :, 1] = m * 20   # G

    if lm_dict is not None:
        L = config.LM
        # Conexiones semánticas del esqueleto (pares de landmarks).
        bones = [
            (L["shoulder_left"], L["elbow_left"]),
            (L["elbow_left"],    L["wrist_left"]),
            (L["shoulder_right"],L["elbow_right"]),
            (L["elbow_right"],   L["wrist_right"]),
            (L["shoulder_left"], L["shoulder_right"]),
            (L["shoulder_left"], L["hip_left"]),
            (L["shoulder_right"],L["hip_right"]),
            (L["hip_left"],      L["hip_right"]),
            (L["hip_left"],      L["knee_left"]),
            (L["hip_right"],     L["knee_right"]),
            (L["nose"],          L["ear_left"]),
            (L["nose"],          L["ear_right"]),
        ]
        def px(idx):
            x, y, _, _ = lm_dict[idx]
            return int(x * w), int(y * h)

        for a, b in bones:
            if a in lm_dict and b in lm_dict:
                cv2.line(canvas, px(a), px(b), (220, 230, 255), 3, cv2.LINE_AA)
        for idx in lm_dict:
            cv2.circle(canvas, px(idx), 6, (255, 255, 255), -1, cv2.LINE_AA)

    # Marca de centros de masa (diálogo cubista cuando hay 2 personas).
    for (cx, cy) in centers:
        cv2.circle(canvas, (int(cx * w), int(cy * h)), 14, (60, 180, 255), 2, cv2.LINE_AA)

    return canvas


# ── Datos sintéticos para modo simulación ─────────────────────────────────────

def synthetic_landmarks(t):
    """Genera un esqueleto sintético animado (un brazo que sube y baja)."""
    L = config.LM
    arm = 0.5 + 0.35 * np.sin(t * 1.5)   # muñeca derecha oscilando en altura
    base = {
        L["nose"]:          (0.50, 0.20, 0.0, 0.9),
        L["ear_left"]:      (0.46, 0.21, 0.0, 0.8),
        L["ear_right"]:     (0.54, 0.21, 0.0, 0.8),
        L["shoulder_left"]: (0.42, 0.35, 0.0, 0.9),
        L["shoulder_right"]:(0.58, 0.35, 0.0, 0.9),
        L["elbow_left"]:    (0.38, 0.50, 0.0, 0.8),
        L["elbow_right"]:   (0.62, 0.50, 0.0, 0.8),
        L["wrist_left"]:    (0.36, 0.62, 0.0, 0.8),
        L["wrist_right"]:   (0.64, arm,  0.0, 0.8),
        L["hip_left"]:      (0.45, 0.62, 0.0, 0.9),
        L["hip_right"]:     (0.55, 0.62, 0.0, 0.9),
        L["knee_left"]:     (0.45, 0.82, 0.0, 0.8),
        L["knee_right"]:    (0.55, 0.82, 0.0, 0.8),
    }
    # Pequeña rotación de cadera para ejercitar el trigger 2.
    rot = 0.04 * np.sin(t * 0.8)
    hl = base[L["hip_left"]];  hr = base[L["hip_right"]]
    base[L["hip_left"]]  = (hl[0], hl[1] + rot, hl[2], hl[3])
    base[L["hip_right"]] = (hr[0], hr[1] - rot, hr[2], hr[3])
    return base


# ── Loop principal ────────────────────────────────────────────────────────────

def main():
    sim_mode = not _MP_OK

    print("=" * 64)
    print(" JIFREX · P2 Skeleton Semántico · MediaPipe Holistic")
    print(f" Plataforma: {platform.system()} · "
          f"Modo: {'SIMULACIÓN' if sim_mode else 'MediaPipe Holistic'}")
    print(f" OSC   → {config.OSC_HOST}:{config.OSC_PORT}")
    print(f" Share → '{config.SHARE_SENDER_NAME}' "
          f"({'Spout' if _IS_WINDOWS else 'Syphon' if _IS_MACOS else 'n/d'})")
    print("=" * 64)

    # MCP bridge en hilo daemon (ajuste de umbrales en vivo).
    start_mcp(blocking=False)

    osc      = OSCClient()
    detector = ZoneDetector()
    share    = FrameShare(config.SHARE_SENDER_NAME, config.CAM_WIDTH, config.CAM_HEIGHT)

    # Cámara + MediaPipe (si está disponible).
    cap = None
    holistic = None
    if not sim_mode:
        cap = open_camera()
        if not cap.isOpened():
            print("[CAM] webcam no disponible — pasando a modo simulación.")
            sim_mode = True
            cap = None
        else:
            holistic = mp.solutions.holistic.Holistic(
                model_complexity      = config.MP_MODEL_COMPLEXITY,
                min_detection_confidence = config.MP_MIN_DETECTION_CONF,
                min_tracking_confidence  = config.MP_MIN_TRACKING_CONF,
                smooth_landmarks      = config.MP_SMOOTH_LANDMARKS,
                enable_segmentation   = True,
            )

    prev_gray   = None
    frame_count = 0
    t_start     = time.perf_counter()
    t0          = time.perf_counter()

    try:
        while True:
            params = get_live_params()

            # 1. Captura ─────────────────────────────────────────────────────
            if sim_mode:
                t = time.perf_counter() - t0
                frame = np.full((config.CAM_HEIGHT, config.CAM_WIDTH, 3),
                                30, dtype=np.uint8)
                lm_dict  = synthetic_landmarks(t)
                seg_mask = None
                # flujo sintético: pulso de movimiento periódico
                flow_mean    = 0.3 + 0.6 * abs(np.sin(t * 1.5))
                motion_ratio = 0.2 + 0.6 * abs(np.sin(t * 1.5))
                time.sleep(1.0 / config.FPS)
            else:
                ok, frame = cap.read()
                if not ok:
                    continue

                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = holistic.process(rgb)

                lm_dict  = landmarks_to_dict(results.pose_landmarks,
                                             config.CAM_WIDTH, config.CAM_HEIGHT)
                seg_mask = results.segmentation_mask  # float32 0..1 o None

                # 3. Optical Flow (movimiento global) ────────────────────────
                curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_gray is None:
                    prev_gray = curr_gray
                    continue
                flow_mean, motion_ratio = optical_flow(prev_gray, curr_gray)
                prev_gray = curr_gray

            # 4. Conteo de personas (trigger 6) ──────────────────────────────
            blob_count, centers = count_people(seg_mask, params)

            # 5. Detección semántica por zona (triggers 1-5) ─────────────────
            m = detector.process(lm_dict, flow_mean, motion_ratio, params)

            # 6. OSC semántico → TouchDesigner ───────────────────────────────
            osc.send_frame(m, flow_mean, motion_ratio, blob_count)

            # 7. Spout/Syphon → overlay del esqueleto (GPU→GPU) ──────────────
            overlay = draw_overlay(frame, lm_dict, seg_mask, centers)
            share.send(overlay)

            # Log cada 5 s ───────────────────────────────────────────────────
            frame_count += 1
            elapsed = time.perf_counter() - t_start
            if elapsed >= 5.0:
                fps  = frame_count / elapsed
                zone = m["trigger_zone"] or "----"
                print(f"[{zone:>13}] {fps:4.1f} fps | "
                      f"blob={blob_count} | "
                      f"flow={flow_mean:.2f} | motion={motion_ratio:.2f} | "
                      f"hip_v={m['hip_velocity']:5.1f}° | "
                      f"head_roll={m['head_roll']:6.1f}° | "
                      f"static={m['static_secs']:.1f}s")
                frame_count = 0
                t_start     = time.perf_counter()

    except KeyboardInterrupt:
        print("\n[JIFREX] Detenido.")
    finally:
        if cap is not None:
            cap.release()
        if holistic is not None:
            holistic.close()
        share.destroy()


if __name__ == "__main__":
    main()
