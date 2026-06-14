# ─────────────────────────────────────────────────────────────────────────────
# P4 — DeepLabv3 + CoreML · Referencia Antimodular / Lozano-Hemmer
# Aún Sorprendo · Exposición Pablo Picasso · JIFREX
# config.py — Todos los parámetros del sistema
#
# Mac M3 Max REQUERIDA — CoreML en Neural Engine (15–25 ms/frame)
# GPU Metal (40 núcleos) completamente libre para TouchDesigner
# 100% Software Libre: Apache 2.0 / BSD / MIT
# ─────────────────────────────────────────────────────────────────────────────

# ── OSC — TouchDesigner en Mac M3 Max ─────────────────────────────────────────
OSC_HOST         = "127.0.0.1"   # EDITAR: IP real si TD corre en otra máquina
OSC_PORT         = 9000
MCP_LISTEN_PORT  = 9001
MCP_RESPOND_PORT = 9002

# ── Cámara ────────────────────────────────────────────────────────────────────
CAM_INDEX    = 0           # VERIFICAR: índice de la cámara RGB 1080p
FRAME_WIDTH  = 1920
FRAME_HEIGHT = 1080
TARGET_FPS   = 60          # C922 puede 60fps a 1080p; OAK-D Pro W también
CAM_RETRY_SECONDS = 5.0    # reintento de apertura si la cámara se pierde en vivo

# ── DeepLabv3 CoreML ──────────────────────────────────────────────────────────
COREML_MODEL_PATH = "DeepLabV3.mlpackage"   # generado por convert_to_coreml.py
DEEPLAB_INPUT_SIZE = 513   # resolución de entrada de DeepLabv3 MobileNetV2
PERSON_CLASS_ID   = 15     # clase PASCAL VOC 15 = "person"
MASK_THRESHOLD    = 0.5    # para modelos con salida probabilística

# ── Blob analysis — estilo Antimodular ────────────────────────────────────────
AREA_THRESHOLD      = 500    # px mínimos para considerar un blob como persona
NOISE_BLOB_RATIO    = 0.1    # blobs menores al 10% del blob mayor = ruido
COOLDOWN_FRAMES     = 30     # frames entre triggers consecutivos
FLOW_THRESHOLD      = 0.35   # umbral de flow_mean para trigger
                              # más bajo que P1 (0.5) porque DeepLabv3 no produce
                              # oscilación de modelo que genera falsos triggers
MOTION_THRESHOLD    = 0.12   # más bajo que P1 (0.15) — misma razón

# ── Syphon ────────────────────────────────────────────────────────────────────
SYPHON_SERVER_NAME = "JIFREX-P4-DEEPLAB"

# ── MCP — parámetros ajustables en tiempo real ───────────────────────────────
# (actualizables vía OSC :9001 sin reiniciar)
MCP_DEFAULTS = {
    "area_threshold":   float(AREA_THRESHOLD),
    "cooldown_frames":  float(COOLDOWN_FRAMES),
    "flow_threshold":   FLOW_THRESHOLD,
    "motion_threshold": MOTION_THRESHOLD,
    "coverage_boost":   1.0,   # multiplicador del coverage_ratio para OSC
}
