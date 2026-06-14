"""
webcam_runtime.py — Pipeline principal P1 · 30 fps · MSI Windows 11
Aún Sorprendo · Exposición Pablo Picasso · JIFREX

Fases implementadas:
  Fase 1 — Ecosistema: venv + dependencias + mcp_bridge
  Fase 2 — Interconectividad: captura → segmentación → flow → trigger → OSC + NDI

Pipeline por frame:
  1. Captura depth + RGB via pyrealsense2
  2. Alineación depth con RGB
  3. Segmentación adaptativa → máscara binaria
  4. Optical Flow Farneback → flow_mean + motion_ratio
  5. Análisis de blobs → largest_blob_area + noise_level
  6. Lógica de trigger anti-falsos positivos
  7. Escritura atómica latest_mask.png
  8. Emit OSC :9000 + Stream NDI ~8 ms
"""

import os
import time
import tempfile

import cv2
import numpy as np

import config
from osc_client import OSCClient
from ndi_stream import NDIStream
from mcp_bridge import start as start_mcp, get_live_params

try:
    import pyrealsense2 as rs
    _RS_OK = True
except ImportError:
    _RS_OK = False
    print("[RS] pyrealsense2 no disponible — modo simulación activo.")


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_project_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_DIR, path)


# ── Cámara ────────────────────────────────────────────────────────────────────

def build_realsense_pipeline():
    pipeline = rs.pipeline()
    cfg = rs.config()
    cfg.enable_stream(rs.stream.depth, config.DEPTH_WIDTH, config.DEPTH_HEIGHT,
                      rs.format.z16, config.FPS)
    cfg.enable_stream(rs.stream.color, config.COLOR_WIDTH, config.COLOR_HEIGHT,
                      rs.format.bgr8, config.FPS)
    pipeline.start(cfg)
    align = rs.align(rs.stream.color)
    return pipeline, align


def get_realsense_frames(pipeline, align):
    try:
        frames = pipeline.wait_for_frames(timeout_ms=config.RS_FRAME_TIMEOUT_MS)
    except RuntimeError as exc:
        print(f"[RS] Timeout o desconexion de camara: {exc}")
        return None, None

    aligned = align.process(frames)
    depth_frame = aligned.get_depth_frame()
    color_frame = aligned.get_color_frame()
    if not depth_frame or not color_frame:
        print("[RS] Frame incompleto recibido; reintentando.")
        return None, None
    depth_img = np.asanyarray(depth_frame.get_data())
    color_img = np.asanyarray(color_frame.get_data())
    return depth_img, color_img


# Modo simulación: webcam normal + depth sintético (para desarrollo sin cámara)
def build_sim_pipeline():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.COLOR_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.COLOR_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.FPS)
    return cap


def get_sim_frames(cap):
    ok, color_img = cap.read()
    if not ok:
        return None, None
    # depth sintético: gradiente + ruido, simula persona a ~1 m
    h, w = color_img.shape[:2]
    depth_img = np.random.randint(800, 1200, (h, w), dtype=np.uint16)
    return depth_img, color_img


# ── Procesamiento ─────────────────────────────────────────────────────────────

def segment(depth_img: np.ndarray, params: dict) -> np.ndarray:
    in_range  = (depth_img > config.DEPTH_MIN_MM) & (depth_img < config.DEPTH_MAX_MM)
    depth_cut = np.where(in_range, depth_img, 0).astype(np.float32)
    depth_8   = cv2.normalize(depth_cut, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)

    mask = cv2.adaptiveThreshold(
        depth_8, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        config.ADAPTIVE_BLOCK_SIZE,
        config.ADAPTIVE_C,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=2)
    mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    return mask


def optical_flow(prev_gray: np.ndarray, curr_gray: np.ndarray) -> tuple:
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
    )
    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    flow_mean    = float(np.mean(mag))
    motion_ratio = float(np.count_nonzero(mag > 1.0) / mag.size)
    return flow_mean, motion_ratio


def analyze_blobs(mask: np.ndarray) -> tuple:
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        return 0, 0.0
    areas       = stats[1:, cv2.CC_STAT_AREA]
    largest     = int(np.max(areas))
    noise_level = float(np.sum(areas < 100) / len(areas))
    return largest, noise_level


def write_mask_atomic(mask: np.ndarray):
    mask_path = resolve_project_path(config.MASK_PATH)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png", dir=PROJECT_DIR)
    os.close(tmp_fd)
    cv2.imwrite(tmp_path, mask)
    os.replace(tmp_path, mask_path)


def restart_realsense_pipeline(pipeline):
    try:
        pipeline.stop()
    except RuntimeError:
        pass
    try:
        return build_realsense_pipeline()
    except RuntimeError as exc:
        print(f"[RS] No se pudo reiniciar la RealSense: {exc}")
        return None, None


# ── Loop principal ────────────────────────────────────────────────────────────

def main():
    sim_mode = not _RS_OK

    print("=" * 60)
    print(" JIFREX · P1 RealSense D435i + NDI")
    print(f" Modo: {'SIMULACIÓN (sin cámara)' if sim_mode else 'RealSense D435i'}")
    print(f" OSC  → {config.OSC_HOST}:{config.OSC_PORT}")
    print(f" NDI  → '{config.NDI_SOURCE_NAME}'")
    print("=" * 60)

    # Fase 1: arrancar MCP bridge en hilo daemon
    start_mcp(blocking=False)

    # Fase 2: inicializar cámara, OSC, NDI
    if sim_mode:
        cap = build_sim_pipeline()
    else:
        try:
            pipeline, align = build_realsense_pipeline()
        except RuntimeError as exc:
            print(f"[RS] No se pudo inicializar la RealSense ({exc}) — modo simulacion.")
            sim_mode = True
            cap = build_sim_pipeline()

    osc = OSCClient()
    ndi = NDIStream()

    prev_gray = None
    cooldown = 0
    frame_count = 0
    t_start = time.perf_counter()
    capture_failures = 0

    try:
        while True:
            # 1. Captura
            if sim_mode:
                depth_img, color_img = get_sim_frames(cap)
            else:
                depth_img, color_img = get_realsense_frames(pipeline, align)

            if depth_img is None:
                prev_gray = None
                if not sim_mode:
                    capture_failures += 1
                    if capture_failures >= config.RS_MAX_CONSECUTIVE_FAILURES:
                        print("[RS] Reintentando inicializar pipeline RealSense...")
                        new_pipeline, new_align = restart_realsense_pipeline(pipeline)
                        capture_failures = 0
                        if new_pipeline is not None and new_align is not None:
                            pipeline, align = new_pipeline, new_align
                continue
            capture_failures = 0

            # 2-3. Segmentación
            params = get_live_params()   # parámetros vivos del MCP bridge
            mask   = segment(depth_img, params)

            # 4. Optical Flow
            curr_gray = cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)
            if prev_gray is None:
                prev_gray = curr_gray
                continue

            flow_mean, motion_ratio = optical_flow(prev_gray, curr_gray)
            prev_gray = curr_gray

            # 5. Blobs
            largest_blob_area, noise_level = analyze_blobs(mask)

            # 6. Presencia + trigger
            presence = largest_blob_area >= params["area_threshold"]

            triggered = False
            if cooldown > 0:
                cooldown -= 1
            elif (presence
                  and flow_mean    >= params["flow_threshold"]
                  and motion_ratio >= params["motion_threshold"]):
                triggered = True
                cooldown  = params["cooldown_frames"]

            # 7. Escritura atómica
            write_mask_atomic(mask)

            # 8a. OSC
            osc.send_metrics(flow_mean, motion_ratio, largest_blob_area,
                             presence, noise_level)
            osc.send_trigger(triggered)

            # 8b. NDI
            ndi.send_frame(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))

            # Log cada 5 s
            frame_count += 1
            elapsed = time.perf_counter() - t_start
            if elapsed >= 5.0:
                fps = frame_count / elapsed
                tag = "TRIGGER" if triggered else "      "
                print(f"[{tag}] {fps:.1f} fps | "
                      f"blob={largest_blob_area:5d}px | "
                      f"flow={flow_mean:.3f} | "
                      f"motion={motion_ratio:.3f} | "
                      f"cooldown={cooldown:2d}")
                frame_count = 0
                t_start     = time.perf_counter()

    except KeyboardInterrupt:
        print("\n[JIFREX] Detenido.")
    finally:
        if sim_mode:
            cap.release()
        else:
            try:
                pipeline.stop()
            except RuntimeError:
                pass
        ndi.destroy()


if __name__ == "__main__":
    main()
