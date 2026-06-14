# ─────────────────────────────────────────────────────────────────────────────
# Configuración central P2 — Skeleton Semántico MediaPipe Holistic
# Aún Sorprendo · Exposición Pablo Picasso · JIFREX
# Galería Universitaria Fernando Cano · UAEMEx / FUNIBER
#
# Ajustar OSC_HOST con la IP real de la máquina que corre TouchDesigner antes
# de arrancar en galería. En modo "una sola máquina" usar "127.0.0.1".
# ─────────────────────────────────────────────────────────────────────────────

# ── Captura webcam RGB ────────────────────────────────────────────────────────
CAM_INDEX    = 0       # índice de cámara (Logitech C922 Pro / BRIO)
CAM_WIDTH    = 1920    # 1080p horizontal
CAM_HEIGHT   = 1080
FPS          = 30      # MediaPipe Holistic en CPU i5 sostiene ~30 fps

# ── MediaPipe Holistic ────────────────────────────────────────────────────────
MP_MODEL_COMPLEXITY      = 1      # 0=lite (rápido) · 1=full · 2=heavy (preciso, lento)
MP_MIN_DETECTION_CONF    = 0.5
MP_MIN_TRACKING_CONF     = 0.5
MP_SMOOTH_LANDMARKS      = True   # filtrado temporal interno de MediaPipe

# Índices de pose landmarks de MediaPipe Pose (33 joints) que usamos como los
# "17 joints semánticos" del sistema. Referencia oficial MediaPipe:
#   0  nariz
#   7  oído izquierdo      8  oído derecho
#   11 hombro izquierdo    12 hombro derecho
#   13 codo izquierdo      14 codo derecho
#   15 muñeca izquierda    16 muñeca derecha
#   23 cadera izquierda    24 cadera derecha
#   25 rodilla izquierda   26 rodilla derecha
LM = {
    "nose":          0,
    "ear_left":      7,
    "ear_right":     8,
    "shoulder_left": 11,
    "shoulder_right":12,
    "elbow_left":    13,
    "elbow_right":   14,
    "wrist_left":    15,
    "wrist_right":   16,
    "hip_left":      23,
    "hip_right":     24,
    "knee_left":     25,
    "knee_right":    26,
}

# ── Umbrales por zona / trigger semántico ─────────────────────────────────────
# Todos en coordenadas normalizadas MediaPipe (0..1, origen arriba-izquierda),
# salvo los ángulos (grados) y los ratios (0..1).

# Trigger 1 — Mano extendida (zona_hands)
#   landmark[16].y < landmark[12].y - HAND_RAISE_MARGIN
#   (muñeca derecha por encima del hombro derecho)
HAND_RAISE_MARGIN   = 0.08    # margen normalizado (~8% de la altura del frame)

# Trigger 2 — Rotación de cadera (zona_torso)
#   abs(hip_angle - prev_hip_angle) > HIP_ROT_THRESHOLD_DEG
HIP_ROT_THRESHOLD_DEG = 15.0  # grados de cambio entre frames

# Trigger 3 — Inclinación de cabeza (zona_head)
#   roll = atan2(nose.y - ear.y, nose.x - ear.x)
#   se dispara cuando |roll| supera HEAD_ROLL_THRESHOLD_DEG
HEAD_ROLL_THRESHOLD_DEG = 12.0

# Trigger 4 — Salto / movimiento brusco (global)
#   motion_ratio > MOTION_RATIO_THRESHOLD
MOTION_RATIO_THRESHOLD = 0.7

# Trigger 5 — Pose estática > 3 s (global)
#   flow_mean < STATIC_FLOW_THRESHOLD durante STATIC_FRAMES frames
STATIC_FLOW_THRESHOLD = 0.5
STATIC_FRAMES         = 90    # 90 frames ≈ 3 s a 30 fps

# Trigger 6 — 2 personas simultáneas (dual_body)
#   blob_count > 1 + dos centros de masa separados
DUAL_MIN_SEPARATION = 0.18    # separación mínima normalizada entre centros de masa
BLOB_MIN_AREA       = 1500    # px mínimos de silueta para contar como persona

# ── Cooldowns por zona (frames entre disparos del mismo trigger) ──────────────
COOLDOWN_HANDS  = 20    # ~0.7 s
COOLDOWN_TORSO  = 15    # ~0.5 s (la cadera dispara seguido al girar)
COOLDOWN_HEAD   = 25    # ~0.8 s
COOLDOWN_GLOBAL = 30    # ~1.0 s (glitch global no debe saturar)

# ── Detección de silueta (para blob_count de 2 personas) ──────────────────────
# Se usa segmentación de MediaPipe Holistic (enable_segmentation=True) en lugar
# de profundidad. La máscara semántica de persona alimenta el conteo de blobs.
SEG_THRESHOLD       = 0.5     # umbral de la máscara de segmentación (0..1)
SEG_MORPH_KERNEL     = 7      # kernel morfológico open/close

# ── Spout / Syphon (GPU→GPU hacia TouchDesigner) ──────────────────────────────
# Windows (MSI) → Spout · macOS (Mac) → Syphon. El runtime elige automáticamente.
SHARE_SENDER_NAME = "JIFREX-P2-SKELETON"   # nombre de la fuente Spout/Syphon
SHARE_ENABLE      = True                    # False = sin compartir frame GPU

# El frame compartido es el overlay del esqueleto + máscara de persona, que
# TouchDesigner consume como textura para los shaders por zona.

# ── OSC → TouchDesigner ───────────────────────────────────────────────────────
OSC_HOST = "127.0.0.1"   # ← una máquina: 127.0.0.1 · dos máquinas: IP del render
OSC_PORT = 9000

# Rutas OSC semánticas (qué parte del cuerpo se mueve)
OSC_HAND_RIGHT   = "/cuerpo/mano_derecha"   # trigger 1 (0/1) + métrica altura
OSC_HIP          = "/cuerpo/cadera"         # trigger 2 (0/1) + ángulo/velocidad
OSC_HEAD         = "/cuerpo/cabeza"         # trigger 3 (0/1) + roll/pitch
OSC_STATIC_POSE  = "/cuerpo/pose_estatica"  # trigger 5 (0/1) + segundos quieto
OSC_TRIGGER_ZONE = "/cuerpo/trigger_zona"   # qué zona disparó (string)
OSC_BLOB_COUNT   = "/cuerpo/blob_count"     # 1 o 2 personas

# Métricas por zona (ángulos, velocidades, ratios)
OSC_HIP_ANGLE       = "/cuerpo/metrica/hip_angle"
OSC_HIP_VELOCITY    = "/cuerpo/metrica/hip_velocity"
OSC_HEAD_ROLL       = "/cuerpo/metrica/head_roll"
OSC_HEAD_PITCH      = "/cuerpo/metrica/head_pitch"
OSC_ARM_OPEN_LEFT   = "/cuerpo/metrica/arm_open_left"
OSC_ARM_OPEN_RIGHT  = "/cuerpo/metrica/arm_open_right"
OSC_FLOW_MEAN       = "/cuerpo/metrica/flow_mean"
OSC_MOTION_RATIO    = "/cuerpo/metrica/motion_ratio"

# Compatibilidad con documentación y patches antiguos de TouchDesigner.
OSC_HIP_ANGLE_LEGACY      = "/cuerpo/hip_angle"
OSC_HIP_VELOCITY_LEGACY   = "/cuerpo/hip_velocity"
OSC_HEAD_ROLL_LEGACY      = "/cuerpo/head_roll"
OSC_HEAD_PITCH_LEGACY     = "/cuerpo/head_pitch"
OSC_ARM_OPEN_LEFT_LEGACY  = "/cuerpo/arm_open_left"
OSC_ARM_OPEN_RIGHT_LEGACY = "/cuerpo/arm_open_right"
OSC_FLOW_MEAN_LEGACY      = "/cuerpo/flow_mean"
OSC_MOTION_RATIO_LEGACY   = "/cuerpo/motion_ratio"
OSC_GLOBAL_GLITCH   = "/cuerpo/global/glitch"     # trigger 4 (0/1)

# ── MCP bridge (ajuste de umbrales en vivo, sin reiniciar) ────────────────────
MCP_LISTEN_PORT  = 9001
MCP_RESPOND_PORT = 9002
