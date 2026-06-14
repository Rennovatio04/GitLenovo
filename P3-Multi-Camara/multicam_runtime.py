# ─────────────────────────────────────────────────────────────────────────────
# multicam_runtime.py — Pipeline principal P3 · Multi-Cámara
# Aún Sorprendo · Exposición Pablo Picasso · JIFREX
#
# !! Mac M3 Max REQUERIDA !! — Ver README.md sección Hardware
# !! Python 3.11 o 3.12    !! — MediaPipe no soporta 3.13/3.14
#
# Arquitectura:
#   3 hilos de cámara (CameraThread) → SyncManager → composite → OSC + Syphon
#
# Arranque:
#   python multicam_runtime.py              # pipeline completo
#   python multicam_runtime.py --simulate   # fuerza modo simulación (sin hardware)
#   python multicam_runtime.py --preview    # muestra ventana de preview cv2
# ─────────────────────────────────────────────────────────────────────────────

import sys
import time
import argparse
import numpy as np
import cv2

import config
from camera_thread import CameraThread
from sync_manager  import SyncManager
from osc_client    import MultiCamOSCClient
from syphon_share  import SyphonShare
from mcp_bridge    import start as start_mcp, get_live_params


def compute_triple_coincidence(mask_a: np.ndarray,
                                mask_b: np.ndarray,
                                mask_c: np.ndarray) -> float:
    """Fracción de píxeles donde los 3 cuerpos coinciden."""
    triple = (mask_a > 0) & (mask_b > 0) & (mask_c > 0)
    return float(np.sum(triple)) / mask_a.size if mask_a.size > 0 else 0.0


def compute_double_coincidence(mask_a: np.ndarray,
                                mask_b: np.ndarray,
                                mask_c: np.ndarray) -> float:
    """Fracción de píxeles con al menos 2 de 3 cuerpos solapados."""
    double = (
        ((mask_a > 0) & (mask_b > 0)) |
        ((mask_b > 0) & (mask_c > 0)) |
        ((mask_a > 0) & (mask_c > 0))
    )
    return float(np.sum(double)) / mask_a.size if mask_a.size > 0 else 0.0


def build_preview(mask_a: np.ndarray, mask_b: np.ndarray, mask_c: np.ndarray,
                  h: int = 360, w: int = 640) -> np.ndarray:
    """
    Preview BGR del Screen-blend reducido para ventana de debug.
    No va a TouchDesigner — solo para validación en desarrollo.
    """
    a  = cv2.resize(mask_a, (w, h)).astype(np.float32) / 255.0
    b  = cv2.resize(mask_b, (w, h)).astype(np.float32) / 255.0
    c  = cv2.resize(mask_c, (w, h)).astype(np.float32) / 255.0
    ca = np.array(config.COLOR_A, dtype=np.float32)
    cb = np.array(config.COLOR_B, dtype=np.float32)
    cc = np.array(config.COLOR_C, dtype=np.float32)
    col_a = a[..., None] * ca[None, None, :]
    col_b = b[..., None] * cb[None, None, :]
    col_c = c[..., None] * cc[None, None, :]
    screen = 1.0 - (1.0 - col_a) * (1.0 - col_b) * (1.0 - col_c)
    # Convertir RGB → BGR para cv2
    bgr = (screen[:, :, ::-1] * 255).astype(np.uint8)
    return bgr


def main():
    parser = argparse.ArgumentParser(description="P3 Multi-Camera Runtime — JIFREX")
    parser.add_argument("--simulate", action="store_true",
                        help="Forzar modo simulación (sin hardware)")
    parser.add_argument("--preview", action="store_true",
                        help="Mostrar ventana de preview cv2")
    args = parser.parse_args()

    print("=" * 60)
    print("  P3 — Multi-Camera Runtime")
    print("  Aun Sorprendo · JIFREX")
    print(f"  OSC -> {config.OSC_HOST}:{config.OSC_PORT}")
    print(f"  Sync window: {config.SYNC_WINDOW_MS} ms")
    print("=" * 60)

    if args.simulate:
        print("[P3] Modo simulacion forzado")

    start_mcp(blocking=False)

    # Crear hilos de cámara
    thread_a = CameraThread("A", "frontal-OAK",
                            source=None if not args.simulate else config.CAM_A_FALLBACK_IDX,
                            use_oak=not args.simulate)
    thread_b = CameraThread("B", "lateral-C922",
                            source=config.CAM_B_INDEX,
                            use_oak=False)
    thread_c = CameraThread("C", "cenital-C922",
                            source=config.CAM_C_INDEX,
                            use_oak=False)

    sync   = SyncManager(thread_a, thread_b, thread_c)
    osc    = MultiCamOSCClient(config.OSC_HOST, config.OSC_PORT)
    syphon = SyphonShare(config.SYPHON_SERVER_A,
                         config.SYPHON_SERVER_B,
                         config.SYPHON_SERVER_C)

    # Arrancar los 3 hilos de cámara en paralelo
    thread_a.start()
    thread_b.start()
    thread_c.start()

    t_last_log  = time.time()
    frame_count = 0
    fps         = 0.0
    in_window   = 0

    try:
        while True:
            t_loop = time.time()
            live_params = get_live_params()
            sync_window_ms = int(live_params.get("sync_window_ms", config.SYNC_WINDOW_MS))
            triple_threshold = float(live_params.get("triple_threshold", config.TRIPLE_THRESHOLD))

            triplet = sync.get_sync_triplet(sync_window_ms=sync_window_ms)
            if triplet is None:
                time.sleep(0.005)
                continue

            fa, fb, fc = triplet

            # Métricas de composición
            triple_ratio = compute_triple_coincidence(fa.mask, fb.mask, fc.mask)
            double_ratio = compute_double_coincidence(fa.mask, fb.mask, fc.mask)
            any_presence = int(fa.presence or fb.presence or fc.presence)

            # Video → TouchDesigner via Syphon (3 texturas independientes)
            syphon.send(fa.mask, fb.mask, fc.mask)

            # Métricas → TouchDesigner via OSC
            osc.send(
                a_presence=fa.presence, a_flow=fa.flow_mean, a_motion=fa.motion_ratio,
                b_presence=fb.presence, b_flow=fb.flow_mean, b_motion=fb.motion_ratio,
                c_presence=fc.presence, c_flow=fc.flow_mean, c_motion=fc.motion_ratio,
                triple_ratio=triple_ratio,
                double_ratio=double_ratio,
                any_presence=any_presence,
            )

            # Preview de debug (opcional)
            if args.preview:
                preview = build_preview(fa.mask, fb.mask, fc.mask)
                cv2.imshow("P3 Screen Blend Preview", preview)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            # Logging cada 5 s
            frame_count += 1
            now = time.time()
            if now - t_last_log >= 5.0:
                fps    = frame_count / (now - t_last_log)
                stats  = sync.stats()
                ts_a   = fa.timestamp_ms
                ts_b   = fb.timestamp_ms
                ts_c   = fc.timestamp_ms
                delta  = max(ts_a, ts_b, ts_c) - min(ts_a, ts_b, ts_c)
                label  = "TRIPLE" if triple_ratio > triple_threshold else (
                         "DOUBLE" if double_ratio > 0.05 else "      ")
                print(
                    f"[{label}] {fps:4.1f}fps | "
                    f"sync={delta:3d}/{sync_window_ms:2d}ms ({stats['sync_ratio']*100:.0f}% OK) | "
                    f"A={fa.flow_mean:.2f} B={fb.flow_mean:.2f} C={fc.flow_mean:.2f} | "
                    f"triple={triple_ratio:.4f}"
                )
                frame_count = 0
                t_last_log  = now

            # Mantener ~TARGET_FPS
            elapsed = time.time() - t_loop
            sleep_t = max(0.0, (1.0 / config.TARGET_FPS) - elapsed)
            time.sleep(sleep_t)

    except KeyboardInterrupt:
        print("\n[P3] Deteniendo...")
    finally:
        thread_a.stop()
        thread_b.stop()
        thread_c.stop()
        thread_a.join(timeout=2.0)
        thread_b.join(timeout=2.0)
        thread_c.join(timeout=2.0)
        syphon.close()
        if args.preview:
            cv2.destroyAllWindows()
        print("[P3] Cerrado.")


if __name__ == "__main__":
    main()
