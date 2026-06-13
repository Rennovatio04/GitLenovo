# ─────────────────────────────────────────────────────────────────────────────
# P3 — Multi-Cámara: 3 Perspectivas Simultáneas
# Aún Sorprendo · Exposición Pablo Picasso · JIFREX
# config.py — Todos los parámetros del sistema
#
# Mac M3 Max REQUERIDA — Ver README.md sección Hardware
# Python 3.11 / 3.12 (MediaPipe no disponible para 3.13/3.14)
# ─────────────────────────────────────────────────────────────────────────────

# ── OSC — TouchDesigner en Mac M3 Max ─────────────────────────────────────────
OSC_HOST         = "127.0.0.1"   # EDITAR: IP real si TD no corre en la misma máquina
OSC_PORT         = 9000
MCP_LISTEN_PORT  = 9001
MCP_RESPOND_PORT = 9002

# ── Cámaras ───────────────────────────────────────────────────────────────────
# Cámara A: OAK-D Pro W (frontal) — via DepthAI SDK, conectada en TB4 #1
CAM_A_DEVICE = None      # None = DepthAI auto-detect; si falla, usa CAM_A_FALLBACK_IDX
CAM_A_FALLBACK_IDX = 0   # índice de webcam de respaldo si OAK-D no está disponible

# Cámara B: Logitech C922 (lateral derecha) — TB4 #2
CAM_B_INDEX  = 1         # VERIFICAR: puede cambiar según el orden de conexión

# Cámara C: Logitech C922 (cenital) — TB4 #3
CAM_C_INDEX  = 2         # VERIFICAR: puede cambiar según el orden de conexión

FRAME_WIDTH  = 1280
FRAME_HEIGHT = 720
TARGET_FPS   = 30

# ── Sincronización ────────────────────────────────────────────────────────────
SYNC_WINDOW_MS = 33      # ventana de sincronización = 1 frame a 30fps
                          # frames fuera de esta ventana reutilizan el frame anterior

# ── MediaPipe ─────────────────────────────────────────────────────────────────
MP_MODEL_COMPLEXITY    = 1      # 0=rápido (30+ fps), 1=equilibrado, 2=preciso (<25 fps)
MP_MIN_DETECTION_CONF  = 0.5
MP_MIN_TRACKING_CONF   = 0.5
MP_ENABLE_SEGMENTATION = True
MP_SMOOTH_SEGMENTATION = True

# ── Paleta de colores por cámara (GLSL compatible, rango 0.0–1.0) ─────────────
COLOR_A = (0.09, 0.35, 0.95)   # azul  — frontal  (referencia: Les Bleus de Barcelona)
COLOR_B = (0.95, 0.66, 0.12)   # ocre  — lateral  (referencia: Bailarines sobre cuero)
COLOR_C = (0.95, 0.38, 0.65)   # rosa  — cenital  (referencia: Geneviève sobre papel Japón)

# ── Syphon (nombres de servidores — deben coincidir en TouchDesigner) ──────────
SYPHON_SERVER_A = "JIFREX-CAM-A-FRONTAL"
SYPHON_SERVER_B = "JIFREX-CAM-B-LATERAL"
SYPHON_SERVER_C = "JIFREX-CAM-C-CENITAL"

# ── Umbrales de detección ─────────────────────────────────────────────────────
MASK_THRESHOLD  = 0.5    # umbral para máscara de segmentación MediaPipe (0.0–1.0)
FLOW_PREV_ALPHA = 0.8    # suavizado exponencial del optical flow entre frames

# ── Triple coincidencia ───────────────────────────────────────────────────────
TRIPLE_THRESHOLD = 0.04  # fracción de píxeles con triple solapamiento para trigger OSC
