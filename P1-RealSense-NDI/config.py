# Configuración central P1 — RealSense D435i + NDI
# Aún Sorprendo · Exposición Pablo Picasso · JIFREX
#
# ANTES DE CORRER: cambiar OSC_HOST con la IP real del Mac.
# Para encontrarla: en el Mac → Terminal → ifconfig | grep "inet "

# ── RealSense D435i ───────────────────────────────────────────────────────────
# La D435i captura a 1280×720 en ambos streams simultáneamente.
# Resoluciones menores (640×480) aumentarían el FPS pero reducirían la calidad
# de la máscara y el optical flow — no recomendado para galería.
DEPTH_WIDTH  = 1280
DEPTH_HEIGHT = 720
COLOR_WIDTH  = 1280
COLOR_HEIGHT = 720
FPS          = 30     # 30 fps es el límite estable de la D435i a esta resolución

# ── Segmentación por profundidad ──────────────────────────────────────────────
# Solo los píxeles entre DEPTH_MIN_MM y DEPTH_MAX_MM se consideran "persona".
# Ajustar según el espacio real de la galería:
#   - Si la cámara está cerca de una pared, reducir DEPTH_MAX_MM para no capturar la pared
#   - Si el visitante puede estar muy cerca de la cámara, reducir DEPTH_MIN_MM
DEPTH_MIN_MM        = 300    # 0.3 m — filtra la zona ciega de la D435i (< 20 cm no fiable)
DEPTH_MAX_MM        = 3000   # 3.0 m — a más de 3m la señal de profundidad tiene mucho ruido

# Umbral adaptativo gaussiano: cada bloque de 51×51 píxeles calcula su propio umbral.
# ADAPTIVE_BLOCK_SIZE debe ser impar; aumentarlo reduce el ruido pero pierde detalle.
# ADAPTIVE_C = 2 hace el umbral ligeramente más conservador (requiere más contraste).
ADAPTIVE_BLOCK_SIZE = 51
ADAPTIVE_C          = 2

# ── Trigger anti-falsos positivos ─────────────────────────────────────────────
# El trigger se dispara solo si SE CUMPLEN LAS 4 CONDICIONES SIMULTÁNEAMENTE:
#   1. El blob más grande tiene área >= AREA_THRESHOLD
#   2. flow_mean >= FLOW_THRESHOLD (hay movimiento real)
#   3. motion_ratio >= MOTION_THRESHOLD (suficiente fracción del frame en movimiento)
#   4. El cooldown llegó a 0

# Área mínima del blob para considerar que hay una persona.
# A 2m de distancia, una persona ocupa ~4000-8000 px. A 3m, ~1500-3000 px.
# 500 px filtra ruido de fondo sin rechazar personas lejanas.
AREA_THRESHOLD   = 500

# Frames entre triggers consecutivos. 30 frames ≈ 1 s a 30fps.
# Evita que el glitch se dispare repetidamente durante un salto continuo.
COOLDOWN_FRAMES  = 30

# Flujo óptico mínimo en píxeles/frame para considerar movimiento real.
# Valor 0.5: movimiento moderado (caminar en el lugar no lo dispara).
# Subir a 0.8+ si hay demasiados triggers en movimiento normal.
FLOW_THRESHOLD   = 0.5

# Fracción mínima del frame con movimiento > 1px.
# Valor 0.15: al menos el 15% de los píxeles deben moverse.
# Filtra triggers donde solo una pequeña parte del cuerpo se mueve.
MOTION_THRESHOLD = 0.15

# ── Archivos de salida ────────────────────────────────────────────────────────
# Escritura atómica (via tempfile + os.replace) para evitar leer frames parciales.
MASK_PATH = "latest_mask.png"

# ── OSC → MacBook Pro M3 Max ──────────────────────────────────────────────────
# EDITAR: cambiar a la IP real del Mac en la red de galería.
# La IP del Mac se puede ver en: Preferencias del Sistema → Red → Avanzado → TCP/IP
# O en Terminal: ifconfig | grep "inet "
OSC_HOST = "192.168.1.XX"   # ← OBLIGATORIO: cambiar por IP real del Mac
OSC_PORT = 9000

# Rutas OSC enviadas a TouchDesigner en :9000
# Los shaders de TD leen estas rutas via el Script DAT osc_to_uniforms.
OSC_TRIGGER      = "/jifrex/trigger"       # float 0/1 — trigger disparado
OSC_FLOW_MEAN    = "/jifrex/flow_mean"     # float 0-3+ — magnitud de movimiento
OSC_MOTION_RATIO = "/jifrex/motion_ratio"  # float 0-1 — fracción de píxeles en mov.
OSC_BLOB_AREA    = "/jifrex/blob_area"     # int — tamaño del blob principal en px
OSC_PRESENCE     = "/jifrex/presence"      # float 0/1 — persona detectada
OSC_NOISE        = "/jifrex/noise_level"   # float — ratio blobs pequeños/principal

# ── MCP bridge (ajuste en vivo) ───────────────────────────────────────────────
# El MCP bridge escucha comandos de ajuste en :9001 y responde en :9002.
# Permite cambiar AREA_THRESHOLD, COOLDOWN_FRAMES, etc. sin reiniciar Python.
# Usar desde el Mac con cualquier app OSC, o con oscsend en Terminal.
MCP_LISTEN_PORT  = 9001
MCP_RESPOND_PORT = 9002

# ── NDI (video de la máscara hacia TouchDesigner) ─────────────────────────────
# La máscara binaria se emite como fuente NDI con este nombre.
# En TouchDesigner: NDI In TOP → Source Name = JIFREX-MSI-MASK
# Latencia en LAN gigabit: ~8 ms (1 frame más algunos ms de red).
NDI_SOURCE_NAME = "JIFREX-MSI-MASK"
