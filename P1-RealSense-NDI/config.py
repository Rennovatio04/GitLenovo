# Configuración central P1 — RealSense D435i + NDI
# Ajustar OSC_HOST con la IP real del Mac antes de correr en el MSI.

# ── RealSense D435i ───────────────────────────────────────────────────────────
DEPTH_WIDTH  = 1280
DEPTH_HEIGHT = 720
COLOR_WIDTH  = 1280
COLOR_HEIGHT = 720
FPS          = 30

# ── Segmentación ──────────────────────────────────────────────────────────────
DEPTH_MIN_MM        = 300    # 0.3 m — distancia mínima útil
DEPTH_MAX_MM        = 3000   # 3.0 m — distancia máxima útil
ADAPTIVE_BLOCK_SIZE = 51     # bloque umbral adaptativo (debe ser impar)
ADAPTIVE_C          = 2

# ── Trigger (anti-falsos positivos) ───────────────────────────────────────────
AREA_THRESHOLD   = 500    # px mínimos de blob para considerar presencia
COOLDOWN_FRAMES  = 30     # ~1 s a 30 fps entre eventos
FLOW_THRESHOLD   = 0.5    # flow_mean mínimo para movimiento real
MOTION_THRESHOLD = 0.15   # motion_ratio mínimo para trigger

# ── Archivos de salida ────────────────────────────────────────────────────────
MASK_PATH = "latest_mask.png"

# ── OSC → MacBook Pro M3 Max ──────────────────────────────────────────────────
OSC_HOST = "192.168.1.XX"   # ← cambiar por IP real del Mac en red local
OSC_PORT = 9000

OSC_TRIGGER      = "/jifrex/trigger"
OSC_FLOW_MEAN    = "/jifrex/flow_mean"
OSC_MOTION_RATIO = "/jifrex/motion_ratio"
OSC_BLOB_AREA    = "/jifrex/blob_area"
OSC_PRESENCE     = "/jifrex/presence"
OSC_NOISE        = "/jifrex/noise_level"

# ── MCP bridge ────────────────────────────────────────────────────────────────
MCP_LISTEN_PORT  = 9001
MCP_RESPOND_PORT = 9002

# ── NDI ───────────────────────────────────────────────────────────────────────
NDI_SOURCE_NAME = "JIFREX-MSI-MASK"
