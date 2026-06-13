# P2 — Skeleton Semántico · MediaPipe Holistic
**Aún Sorprendo · Exposición Pablo Picasso · JIFREX**
Galería Universitaria Fernando Cano · UAEMEx / FUNIBER

> "El cuerpo no activa la instalación — conversa con ella."
> Cada parte del cuerpo que se mueve dispara una respuesta visual diferente.

---

## Estado actual: BETA — v0.1

| Fase | Estado | Detalle |
|------|--------|---------|
| Fase 1 — Ecosistema | ✅ Completa | venv, `config.py` centralizado, `mcp_bridge` |
| Fase 2 — Lógica semántica | ✅ Completa | MediaPipe Holistic → 17 joints → 6 triggers semánticos |
| Fase 3 — Shaders GLSL | ✅ Completa | 5 shaders por zona + Script DAT + setup TD |
| Detección 2 personas | ✅ Completa | `blob_count` vía máscara de segmentación + 2 centros de masa |
| GPU share (Spout/Syphon) | ⚠️ Parcial | Código listo, degrada a no-op si falta la lib nativa |
| Calibración en sala | ❌ Pendiente | Umbrales por defecto · requiere visita técnica |
| Prueba 8 h continuas | ❌ Pendiente | Sin test de estabilidad larga |

---

## Qué funciona (verificado en simulación)

- Pipeline completo a ~30 fps: captura → MediaPipe Holistic → flow → zonas → OSC → share
- **17 joints semánticos** extraídos de MediaPipe Pose (nariz, oídos, hombros,
  codos, muñecas, caderas, rodillas) — ver `config.LM`
- **Cálculo de ángulos con `arctan2`** en `zone_detector.py` (cadera, cabeza, brazos)
- **6 triggers semánticos** completos (ver tabla abajo), cada uno con su cooldown
- **Detección de 2 personas**: máscara de segmentación de MediaPipe → blobs →
  verificación de dos centros de masa separados (`blob_count`)
- **OSC semántico** a TouchDesigner: rutas `/cuerpo/...` (qué parte se mueve, qué
  zona disparó, blob_count) + métricas continuas (ángulos, velocidades)
- **Spout (Windows) / Syphon (macOS)**: comparte el overlay del esqueleto GPU→GPU
  (~1 ms). El runtime elige el backend según la plataforma y degrada con
  elegancia si la librería nativa no está instalada (el sistema sigue por OSC)
- **MCP bridge** en puerto 9001: ajuste de los 11 umbrales semánticos en vivo sin
  reiniciar el pipeline
- **Modo simulación** sin webcam ni MediaPipe: esqueleto sintético animado para
  desarrollar y verificar en cualquier máquina
- **5 shaders GLSL** por zona corporal + Script DAT + setup completo de TD

---

## Diferencias clave vs P1

| | P1 — RealSense | P2 — Skeleton Semántico |
|--|---------------|------------------------|
| Sensor | RealSense D435i (profundidad) | Webcam RGB normal 1080p |
| Detección | Presencia / silueta binaria | Qué PARTE del cuerpo se mueve (17 joints) |
| Respuesta visual | Una respuesta única | Respuesta diferente por zona corporal |
| Triggers | 1 (presencia + movimiento) | 6 semánticos (uno por zona/gesto) |
| Personas | 1 | Hasta 2 simultáneas (diálogo cubista) |
| Transporte de video | NDI (~8 ms, por red) | Spout/Syphon (~1 ms, GPU→GPU local) |
| Máquinas | MSI + Mac (dos) | Una sola (MSI **o** Mac) |
| OSC | 6 canales planos | Rutas semánticas `/cuerpo/...` |
| Visitante | Activa la instalación | Conversa con ella |

---

## Triggers semánticos

| # | Zona / Gesto | Respuesta visual | Lógica de detección | Shader |
|---|-------------|------------------|---------------------|--------|
| 1 | Mano extendida | Planos geométricos fragmentados cubistas, paleta fría azul-blanco | `wrist_right.y < shoulder_right.y - umbral` | `zona_hands.glsl` |
| 2 | Rotación de cadera | Velocidad de estelas proporcional al ángulo | `abs(hip_angle - prev_hip_angle) > 15°` | `zona_torso.glsl` |
| 3 | Inclinación de cabeza | Cambio de paleta de color completa (temperatura por roll/pitch) | `atan2(nose.y - ear.y, nose.x - ear.x)` | `zona_head.glsl` |
| 4 | Salto / movimiento brusco | Glitch + partículas máximas | `motion_ratio > 0.7` | `global_glitch.glsl` |
| 5 | Pose estática > 3 s | Fade gradual → reposo | `flow_mean < 0.5` durante 90 frames | Level TOP (ver setup TD) |
| 6 | 2 personas simultáneas | Diálogo cubista entre cuerpos *(exclusivo P2)* | `blob_count > 1` + dos centros de masa | `dual_body.glsl` |

La zona dominante de cada frame se publica en `/cuerpo/trigger_zona`
(`zona_hands`, `zona_torso`, `zona_head`, `global`, `pose_estatica`, `none`).

---

## Arquitectura

```
Una sola máquina (MSI Katana o MacBook Pro M3 Max)
──────────────────────────────────────────────────
Webcam RGB 1080p (Logitech C922 / BRIO)
        │
  skeleton_runtime.py  (~30 fps, CPU/Neural Engine, GPU libre)
    MediaPipe Holistic ── 17 joints + máscara de segmentación
    Optical Flow Farneback ── flow_mean + motion_ratio
    zone_detector.py ── 6 triggers semánticos (arctan2)
    count_people() ── blob_count (2 personas)
        │
   ┌────┴─────┐
   │          │
OSC :9000   Spout/Syphon
semántico   overlay esqueleto
(<2 ms)     (~1 ms, GPU→GPU)
   │          │
   └────┬─────┘
        ▼
  TouchDesigner
    OSC In DAT → Script DAT (td_osc_to_uniforms.py)
    Spout/Syphon In TOP → glsl_hands → glsl_torso → glsl_head
                         → glsl_glitch (Feedback) → glsl_dual → fade_global
        │
  2× Epson PowerLite 5510
```

Componentes:

| Archivo | Descripción |
|---------|-------------|
| `skeleton_runtime.py` | Pipeline principal 30 fps (captura, MP, flow, zonas, OSC, share) |
| `zone_detector.py` | Detección semántica por zona + 6 triggers (arctan2, cooldowns) |
| `osc_client.py` | Rutas OSC semánticas `/cuerpo/...` |
| `mcp_bridge.py` | Ajuste de 11 umbrales en tiempo real (puerto 9001) |
| `config.py` | Todos los parámetros (editar `OSC_HOST` y umbrales) |
| `shaders/zona_hands.glsl` | Trigger 1: planos cubistas fríos |
| `shaders/zona_torso.glsl` | Trigger 2: estelas circulares por rotación de cadera |
| `shaders/zona_head.glsl` | Trigger 3: transición de paleta por inclinación |
| `shaders/global_glitch.glsl` | Trigger 4: glitch + partículas en salto |
| `shaders/dual_body.glsl` | Trigger 6: diálogo cubista entre 2 cuerpos |
| `shaders/td_osc_to_uniforms.py` | Script DAT TouchDesigner: OSC → uniforms |
| `shaders/README_TouchDesigner.md` | Setup completo de la red TD |

---

## Arranque rápido

### Requisito de Python

**Crear el venv con Python 3.11 o 3.12.** MediaPipe publica wheels solo para
Python 3.9–3.12; **no funciona en 3.13/3.14**. NumPy queda fijado a `< 2.0`
porque MediaPipe 0.10.x todavía no soporta NumPy 2.x.

```powershell
# 1. Crear venv con Python 3.11/3.12
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r requirements.txt
#   Windows: pip install SpoutGL
#   macOS:   pip install syphon-python

# 3. Editar config.py
#   OSC_HOST = "127.0.0.1"   (una máquina)  ó  IP del render (dos máquinas)
#   CAM_INDEX = 0            (verificar el índice de la webcam)

# Terminal A — MCP bridge (opcional, ajuste en vivo)
python mcp_bridge.py

# Terminal B — Pipeline principal
python skeleton_runtime.py
```

Si MediaPipe o la webcam no están disponibles, el runtime entra en **modo
simulación** (esqueleto sintético animado) para que puedas validar OSC y los
shaders sin hardware.

Log cada 5 s:
```
[   zona_hands] 29.8 fps | blob=1 | flow=0.42 | motion=0.31 | hip_v=  2.1° | head_roll=  -4.3° | static=0.0s
[         ----] 30.1 fps | blob=2 | flow=0.18 | motion=0.07 | hip_v=  0.4° | head_roll=  -1.1° | static=2.7s
```

---

## Ajuste de parámetros en vivo

Desde cualquier cliente OSC (puerto 9001):

```
/mcp/set/hand_raise_margin        <float>   # mano sobre hombro (default 0.08)
/mcp/set/hip_rot_threshold_deg    <float>   # rotación de cadera (default 15)
/mcp/set/head_roll_threshold_deg  <float>   # inclinación cabeza (default 12)
/mcp/set/motion_ratio_threshold   <float>   # salto/brusco (default 0.7)
/mcp/set/static_flow_threshold    <float>   # pose estática (default 0.5)
/mcp/set/static_frames            <int>     # frames de quietud (default 90)
/mcp/set/dual_min_separation      <float>   # 2 personas (default 0.18)
/mcp/set/cooldown_hands           <int>
/mcp/set/cooldown_torso           <int>
/mcp/set/cooldown_head            <int>
/mcp/set/cooldown_global          <int>
/mcp/get/params                              # → responde en :9002
```

---

## ⚠️ Limitación crítica — Iluminación de galería

**Este es el riesgo número uno de la propuesta P2.** A diferencia de P1, que usa
profundidad (insensible a la luz visible), P2 depende de que MediaPipe estime
bien los joints a partir de RGB. La iluminación de la Galería Fernando Cano puede
degradar gravemente la precisión:

- **Ropa similar al fondo** → joints mal segmentados, esqueleto inestable.
- **Luz directa en la cámara** → pérdida de precisión angular (cadera, cabeza).
- **Personas cruzando al fondo** → confusión del modelo, falsos blobs.
- **Sombras cruzadas fuertes** → joints mal estimados, triggers erráticos.

**Mitigaciones ya previstas en el código:**
- `MP_MODEL_COMPLEXITY` (0/1/2) — subir a 2 si la luz es difícil (cuesta fps).
- `MP_MIN_DETECTION_CONF` / `MP_MIN_TRACKING_CONF` — subir para rechazar joints
  dudosos.
- Filtro de visibilidad por landmark (`_visible`, `min_vis`) en `zone_detector`.
- `BLOB_MIN_AREA` y `DUAL_MIN_SEPARATION` filtran blobs espurios del fondo.
- Cooldowns por zona para no saturar con triggers de ruido.

**Acción obligatoria:** visita técnica a la Galería Fernando Cano antes de
confirmar P2. Calibrar con la luz real de sala (no se puede calibrar de antemano).

---

## Pendientes antes de galería

### Crítico (sin esto no se exhibe)

- [ ] **Visita técnica + calibración de iluminación** (ver sección anterior).
      Es el factor determinante de viabilidad de P2.
- [ ] **Editar `config.py`**: `OSC_HOST`, `CAM_INDEX`, resolución real de webcam.
- [ ] **Instalar el backend de GPU share** de la plataforma elegida
      (`SpoutGL` en Windows, `syphon-python` en macOS).
- [ ] **Construir la red de TouchDesigner** según `shaders/README_TouchDesigner.md`.
      Los nombres de los GLSL TOPs deben coincidir con `td_osc_to_uniforms.py`:
      `glsl_hands`, `glsl_torso`, `glsl_head`, `glsl_glitch`, `glsl_dual`.
- [ ] **Calibrar umbrales en sala** vía `mcp_bridge.py` con personas reales.

### Importante (estabilidad en exposición de horas)

- [ ] **Prueba de 8 horas continuas**: verificar que no haya memory leak ni
      caída de fps con MediaPipe corriendo todo el día.
- [ ] **Trigger 5 (fade a reposo)** en TD: cablear `/cuerpo/pose_estatica` al
      `Level TOP` `fade_global` con un Lag CHOP (ver setup TD).
- [ ] **Posición de webcam**: encuadre que capture cuerpo completo de pies a
      cabeza para que las zonas lower/head funcionen.

### Menor (operación)

- [ ] Logging a archivo de las últimas 24 h.
- [ ] Indicador en TD de "OSC activo / esqueleto detectado".
- [ ] Reconexión automática del share si TD se reinicia.

---

## Referencias

- MediaPipe Holistic (Apache 2.0) — Google
- Memo Akten · Rafael Lozano-Hemmer — instalación reactiva
- Bailarines de Picasso (años 40-50) — referencia coreográfica del cubismo en movimiento

---

*Sistema de Proyección Reactiva Interactiva · JIFREX · 2026-06-13*
