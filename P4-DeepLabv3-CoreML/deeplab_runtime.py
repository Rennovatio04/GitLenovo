# ─────────────────────────────────────────────────────────────────────────────
# deeplab_runtime.py — Pipeline principal P4
# Aún Sorprendo · Exposición Pablo Picasso · JIFREX
#
# !! Mac M3 Max recomendada !! (CoreML en Neural Engine, GPU libre para TD)
# !! Python 3.11 o 3.12     !! (TensorFlow compatible)
#
# Flujo:
#   Webcam 1080p/60fps → DeepLabv3 (CoreML / TF / simulado)
#   → blob_analysis Antimodular → optical flow → trigger anti-FP
#   → Syphon (máscara subpixel-accurate) + OSC (8 métricas) → TouchDesigner
#
# Arranque:
#   python deeplab_runtime.py              # pipeline completo
#   python deeplab_runtime.py --simulate   # fuerza simulación
#   python deeplab_runtime.py --preview    # ventana de debug cv2
# ─────────────────────────────────────────────────────────────────────────────

import sys
import time
import argparse
import tempfile
import os
import numpy as np
import cv2

import config
from deeplab_segmentor import DeepLabSegmentor
from blob_analysis      import analyze as blob_analyze
from osc_client         import P4OSCClient
from syphon_share       import SyphonShare
from mcp_bridge         import start as start_mcp, get_live_params


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_project_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_DIR, path)


def optical_flow(prev_gray: np.ndarray, curr_gray: np.ndarray):
    """Optical Flow Farneback → (flow_mean, motion_ratio)."""
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0
    )
    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    return float(np.mean(mag)), float(np.mean(mag > 1.0))


def write_mask_atomic(mask: np.ndarray, path: str = "latest_mask.png"):
    """Escritura atómica de la máscara — evita frame parcialmente escrito."""
    out_path = resolve_project_path(path)
    fd, tmp = tempfile.mkstemp(suffix=".png", dir=PROJECT_DIR)
    os.close(fd)
    cv2.imwrite(tmp, mask)
    os.replace(tmp, out_path)


def build_preview(frame_bgr: np.ndarray, mask: np.ndarray,
                  backend: str, fps: float, blob_area: int,
                  flow_m: float, triple: bool, coverage: float) -> np.ndarray:
    """Preview de debug: frame original + overlay de la máscara."""
    h, w = frame_bgr.shape[:2]
    preview = cv2.resize(frame_bgr, (960, 540))
    ph, pw = preview.shape[:2]
    mask_r = cv2.resize(mask, (pw, ph))
    # Overlay cyan sobre la máscara
    overlay  = preview.copy()
    overlay[mask_r > 0] = (0, 220, 180)
    preview  = cv2.addWeighted(preview, 0.6, overlay, 0.4, 0)
    label = "TRIGGER" if triple else "       "
    cv2.putText(preview,
        f"[{label}] {fps:.1f}fps | {backend} | area={blob_area}px | "
        f"flow={flow_m:.2f} | cov={coverage:.3f}",
        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return preview


def main():
    parser = argparse.ArgumentParser(description="P4 DeepLab Runtime — JIFREX")
    parser.add_argument("--simulate", action="store_true",
                        help="Forzar simulación")
    parser.add_argument("--preview",  action="store_true",
                        help="Mostrar ventana de debug cv2")
    args = parser.parse_args()

    print("=" * 60)
    print("  P4 — DeepLabv3 + CoreML · Referencia Antimodular")
    print("  Aun Sorprendo · JIFREX")
    print(f"  OSC -> {config.OSC_HOST}:{config.OSC_PORT}")
    print("=" * 60)

    start_mcp(blocking=False)

    segmentor = DeepLabSegmentor()
    if args.simulate:
        segmentor.backend = "simulate"
        print("[P4] Modo simulacion forzado")

    print(f"[P4] Backend: {segmentor.backend}")

    osc    = P4OSCClient(config.OSC_HOST, config.OSC_PORT)
    syphon = SyphonShare(config.SYPHON_SERVER_NAME)

    cap = cv2.VideoCapture(config.CAM_INDEX)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS,          config.TARGET_FPS)
        use_cam = True
        print(f"[P4] Camara {config.CAM_INDEX} abierta — {config.FRAME_WIDTH}x{config.FRAME_HEIGHT}")
    else:
        use_cam = False
        print(f"[P4] Camara {config.CAM_INDEX} no disponible — usando modelo sin frame real")

    prev_gray = None
    cooldown  = 0

    t_last_log  = time.time()
    frame_count = 0
    fps         = 0.0

    try:
        while True:
            t_loop = time.time()

            # ── Captura ────────────────────────────────────────────────────────
            if use_cam:
                ok, frame_bgr = cap.read()
                if not ok:
                    frame_bgr = None
            else:
                frame_bgr = None

            # ── Segmentación ───────────────────────────────────────────────────
            t_seg_start = time.time()
            if frame_bgr is not None:
                mask = segmentor.segment(frame_bgr)
            else:
                # Simulación sin frame
                h, w = config.FRAME_HEIGHT, config.FRAME_WIDTH
                mask = segmentor._simulate(h, w)
                frame_bgr = np.zeros((h, w, 3), dtype=np.uint8)
            t_seg_ms = (time.time() - t_seg_start) * 1000

            # ── Análisis de blobs Antimodular ──────────────────────────────────
            blobs = blob_analyze(mask)

            # ── Optical Flow ───────────────────────────────────────────────────
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            if prev_gray is None:
                prev_gray = gray
                flow_mean    = 0.0
                motion_ratio = 0.0
            else:
                flow_mean, motion_ratio = optical_flow(prev_gray, gray)
                prev_gray = gray

            # ── Parámetros en vivo desde MCP bridge ───────────────────────────
            lp = get_live_params()
            area_thr     = int(lp.get("area_threshold",   config.AREA_THRESHOLD))
            cooldown_max = int(lp.get("cooldown_frames",  config.COOLDOWN_FRAMES))
            flow_thr     = float(lp.get("flow_threshold",    config.FLOW_THRESHOLD))
            motion_thr   = float(lp.get("motion_threshold",  config.MOTION_THRESHOLD))
            cov_boost    = float(lp.get("coverage_boost",    1.0))

            # ── Trigger anti-falsos positivos ──────────────────────────────────
            triggered = False
            if cooldown > 0:
                cooldown -= 1

            if (blobs.presence and
                    blobs.largest_area >= area_thr and
                    flow_mean          >= flow_thr and
                    motion_ratio       >= motion_thr and
                    cooldown == 0):
                triggered = True
                cooldown  = cooldown_max

            # ── Syphon (máscara subpixel-accurate) ────────────────────────────
            syphon.send(mask)

            # ── Escritura atómica de máscara ───────────────────────────────────
            write_mask_atomic(mask)

            # ── OSC ────────────────────────────────────────────────────────────
            osc.send(
                trigger        = int(triggered),
                presence       = blobs.presence,
                flow_mean      = flow_mean,
                motion_ratio   = motion_ratio,
                blob_area      = blobs.largest_area,
                noise_level    = blobs.noise_level,
                coverage_ratio = blobs.coverage_ratio * cov_boost,
                blob_count     = blobs.blob_count,
            )

            # ── Preview ────────────────────────────────────────────────────────
            if args.preview:
                pv = build_preview(frame_bgr, mask, segmentor.backend, fps,
                                   blobs.largest_area, flow_mean,
                                   triggered, blobs.coverage_ratio)
                cv2.imshow("P4 DeepLabv3 Preview", pv)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            # ── Logging cada 5 s ───────────────────────────────────────────────
            frame_count += 1
            now = time.time()
            if now - t_last_log >= 5.0:
                fps    = frame_count / (now - t_last_log)
                label  = "TRIGGER" if triggered else "       "
                print(
                    f"[{label}] {fps:4.1f}fps | {segmentor.backend} {t_seg_ms:4.0f}ms | "
                    f"area={blobs.largest_area:6d}px | "
                    f"flow={flow_mean:.3f} | motion={motion_ratio:.3f} | "
                    f"cov={blobs.coverage_ratio:.4f} | noise={blobs.noise_level:.3f} | "
                    f"cd={cooldown:2d}"
                )
                frame_count = 0
                t_last_log  = now

            # ── Control de FPS ─────────────────────────────────────────────────
            elapsed = time.time() - t_loop
            sleep_t = max(0.0, (1.0 / config.TARGET_FPS) - elapsed)
            time.sleep(sleep_t)

    except KeyboardInterrupt:
        print("\n[P4] Deteniendo...")
    finally:
        if cap.isOpened():
            cap.release()
        syphon.close()
        if args.preview:
            cv2.destroyAllWindows()
        print("[P4] Cerrado.")


if __name__ == "__main__":
    main()
