# P2 — Skeleton Semántico · MediaPipe Holistic
**Aún Sorprendo · Exposición Pablo Picasso · JIFREX**
Galería Universitaria Fernando Cano · UAEMEx / FUNIBER

> "El cuerpo no activa la instalación — conversa con ella."
> Cada parte del cuerpo que se mueve dispara una respuesta visual diferente.

---

## Estado actual: BETA — v0.2

| Fase | Estado | Detalle |
|------|--------|---------|
| Fase 1 — Ecosistema | ✅ Completa | venv, `config.py` centralizado, `mcp_bridge` |
| Fase 2 — Lógica semántica | ✅ Completa | MediaPipe Holistic → 17 joints → 6 triggers semánticos |
| Fase 3 — Shaders GLSL | ✅ Completa | 5 shaders por zona + Script DAT + setup TD |
| Detección 2 personas | ⚠️ Experimental | `blob_count` vía máscara de segmentación; requiere validar con 2 siluetas reales |
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
- **Detección experimental de 2 personas**: máscara de segmentación de
  MediaPipe → blobs → verificación de dos centros de masa separados
  (`blob_count`). Si no hay máscara válida, el runtime publica `0`.
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
| 6 | 2 siluetas simultáneas | Diálogo cubista entre cuerpos *(exclusivo P2)* | `blob_count > 1` + dos centros de masa | `dual_body.glsl` |

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

## Auditoría técnica — para IA o revisor externo

> Esta sección permite a un auditor verificar el sistema sin leer cada archivo desde cero.

### Mapa de responsabilidades

| Archivo | Función principal | Entradas | Salidas |
|---------|------------------|----------|---------|
| `config.py` | Parámetros y constantes | — | `LM` (17 joints), `OSC_*`, umbrales, `CAM_INDEX` |
| `skeleton_runtime.py` | Loop principal ~30 fps | Webcam / simulado | OSC semántico + Spout/Syphon overlay |
| `zone_detector.py` | 6 triggers semánticos | `landmarks` (17 joints) | Zona activa + métricas angulares |
| `osc_client.py` | Transporte OSC semántico | Métricas + zona activa | Datagramas UDP rutas `/cuerpo/...` |
| `mcp_bridge.py` | 11 parámetros en vivo | OSC `:9001` | Diccionario `_params` thread-safe |
| `shaders/zona_hands.glsl` | Trigger 1 — manos | Overlay esqueleto + máscara | Planos geométricos azul-blanco |
| `shaders/zona_torso.glsl` | Trigger 2 — cadera | Overlay + `uHipAngle` | Estelas circulares proporcionales |
| `shaders/zona_head.glsl` | Trigger 3 — cabeza | Overlay + `uHeadRoll` `uHeadPitch` | Cambio de paleta por ángulo |
| `shaders/global_glitch.glsl` | Trigger 4 — salto | Overlay + `uMotionRatio` | Glitch + partículas máximas |
| `shaders/dual_body.glsl` | Trigger 6 — 2 personas | Overlay + `uBlobCount` | Diálogo cubista dual |
| `shaders/td_osc_to_uniforms.py` | Script DAT TD | Tabla OSC In DAT | `par.value` en 5 GLSL TOPs |

### Flujo de datos completo

```
Webcam 1080p (Logitech C922 / simulada)  @30fps
  └─ cv2.VideoCapture(CAM_INDEX)
      └─ MediaPipe Holistic(model_complexity=1):
           .pose_landmarks[33] → filtrar a LM (17 joints seleccionados)
           .segmentation_mask → float32 → uint8 thresholded
      └─ Optical Flow Farneback(prev_gray, curr_gray) → flow_mean, motion_ratio
      └─ count_people():
           cv2.connectedComponentsWithStats(mask) → blob_count
           verificar 2 centros de masa separados > DUAL_MIN_SEPARATION
      └─ zone_detector.detect(landmarks, params):
           arctan2(wrist.y - shoulder.y, ...) → mano_extendida (trigger 1)
           abs(hip_angle - prev_hip_angle)    → rotacion_cadera (trigger 2)
           atan2(nose.y - ear.y, ...)         → inclinacion_cabeza (trigger 3)
           motion_ratio > 0.7                 → salto (trigger 4)
           flow_mean < 0.5 durante 90f        → pose_estatica (trigger 5)
           blob_count > 1                     → dual_body (trigger 6)
      └─ OSCClient.send_semantic():
           /cuerpo/trigger_zona  (string: zona activa)
           /cuerpo/blob_count    (int)
           /cuerpo/metrica/flow_mean     (float)
           /cuerpo/metrica/motion_ratio  (float)
           /cuerpo/metrica/hip_angle     (float, grados)
           /cuerpo/metrica/head_roll     (float, grados)
           /cuerpo/metrica/head_pitch    (float, grados)
           /cuerpo/pose_estatica (float: segundos de quietud)
      └─ FrameShare.send(overlay_bgra):
           Windows → Spout (SpoutGL) ~1ms GPU→GPU
           macOS   → Syphon (syphon-python) ~1ms GPU→GPU
           fallback → no-op (sin error, OSC continúa)
```

### Índice de joints (config.LM)

| Nombre | Índice MP | Descripción |
|--------|-----------|-------------|
| `nose` | 0 | Nariz |
| `left_ear` / `right_ear` | 7 / 8 | Orejas |
| `left_shoulder` / `right_shoulder` | 11 / 12 | Hombros |
| `left_elbow` / `right_elbow` | 13 / 14 | Codos |
| `left_wrist` / `right_wrist` | 15 / 16 | Muñecas |
| `left_hip` / `right_hip` | 23 / 24 | Caderas |
| `left_knee` / `right_knee` | 25 / 26 | Rodillas |

Cada landmark tiene `(x, y, z, visibility)`. El detector filtra joints con `visibility < MP_MIN_VIS`.

### Rutas OSC completas (puerto 9000)

| Ruta OSC | Tipo | Rango | Descripción |
|----------|------|-------|-------------|
| `/cuerpo/trigger_zona` | string | zona_hands, zona_torso, zona_head, global, pose_estatica, none | Zona dominante del frame |
| `/cuerpo/blob_count` | int | 0–2+ | Personas detectadas |
| `/cuerpo/metrica/flow_mean` | float | 0.0–3.0 | Magnitud promedio del flujo óptico |
| `/cuerpo/metrica/motion_ratio` | float | 0.0–1.0 | Fracción de píxeles con movimiento > 1px |
| `/cuerpo/metrica/hip_angle` | float | -180.0–180.0 | Ángulo relativo de cadera (arctan2) |
| `/cuerpo/metrica/head_roll` | float | -90.0–90.0 | Inclinación lateral de cabeza |
| `/cuerpo/metrica/head_pitch` | float | -90.0–90.0 | Inclinación frontal de cabeza |
| `/cuerpo/pose_estatica` | float | 0.0–N | Segundos de quietud acumulada |

Las rutas históricas sin el prefijo `/metrica/` siguen emitiéndose como alias de
compatibilidad para patches de TouchDesigner anteriores.

### Puntos de integración críticos

| Punto | Protocolo | Puerto | Latencia esperada |
|-------|-----------|--------|------------------|
| Python → TouchDesigner (métricas) | OSC / UDP | 9000 | < 2 ms |
| Python → TouchDesigner (video) | Spout/Syphon | GPU compartido | ~1 ms |
| Consola → Python (parámetros) | OSC / UDP | 9001 | < 2 ms |
| Python → Consola (respuesta) | OSC / UDP | 9002 | < 2 ms |

### Estado de cada módulo

| Módulo | Código | Verificado | Listo para galería |
|--------|--------|------------|-------------------|
| `skeleton_runtime.py` | ✅ Completo | ✅ En simulación | ⚠️ Calibrar en sala |
| `zone_detector.py` | ✅ Completo | ✅ Con skeleton sintético | ⚠️ Umbrales pendientes |
| `osc_client.py` | ✅ Completo | ✅ | ⚠️ Verificar IP / One-machine |
| `mcp_bridge.py` | ✅ Completo | ✅ Thread-safe | ✅ |
| `zona_hands.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar en sala |
| `zona_torso.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar en sala |
| `zona_head.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar en sala |
| `global_glitch.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar en sala |
| `dual_body.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar en sala |
| `td_osc_to_uniforms.py` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Verificar nombres de ops |
| Spout/Syphon backend | ⚠️ Código listo | ⚠️ Depende de lib nativa | ❌ Instalar SpoutGL o syphon-python |

### Qué debe verificar un auditor

1. **Python version**: Confirmar que el venv usa Python 3.11 o 3.12 con `python --version`. MediaPipe no publica wheels para 3.13/3.14.
2. **`config.py` CAM_INDEX**: El índice de webcam puede cambiar si se conecta o desconecta hardware. Verificar con `python -c "import cv2; cap=cv2.VideoCapture(0); print(cap.isOpened())"`.
3. **`config.py` OSC_HOST**: Si TouchDesigner corre en la misma máquina usar `"127.0.0.1"`. Si corre en otra máquina, poner la IP real.
4. **`zone_detector.py` visibilidad**: Los triggers 1, 2, 3 comprueban que los joints relevantes tengan `visibility > MP_MIN_VIS` (default 0.5). Si el umbral es muy alto en condiciones de galería, los triggers no dispararán aunque el gesto sea claro.
5. **Spout/Syphon**: La clase `FrameShare` hace fallback silencioso si la lib no está instalada. Verificar que el overlay llegue a TD: `python -c "from skeleton_runtime import FrameShare; s=FrameShare('test'); print(s.backend)"`.
6. **`td_osc_to_uniforms.py` nombres**: Los ops `glsl_hands`, `glsl_torso`, `glsl_head`, `glsl_glitch`, `glsl_dual` deben coincidir exactamente con los nombres en el patch de TD.
7. **MediaPipe model_complexity**: Default es 1 (equilibrado). Subir a 2 si la iluminación de galería es difícil — cuesta ~10% de fps pero mejora estabilidad angular.
8. **NumPy version**: MediaPipe 0.10.x requiere `numpy < 2.0`. Verificar con `pip show numpy`.

### Auditoría y mejoras — 2026-06-14

**Hallazgos**

- El runtime ya incorporaba el MCP bridge embebido, pero el modo "terminal A +
  terminal B" podía provocar conflicto de puerto si el bridge se ejecutaba dos
  veces.
- La lógica semántica y el flujo principal están bien separados; el mayor riesgo
  real sigue siendo la calibración de iluminación en sala, no el pipeline base.

**Mejoras aplicadas**

- `mcp_bridge.py` ahora maneja `MCP_LISTEN_PORT` ocupado y reutiliza el bridge ya
  activo en vez de abortar el arranque.
- README actualizado con el resultado de la auditoría y con foco en el riesgo real
  de despliegue: iluminación, no arquitectura.

**Trabajo auditado**

- Captura webcam → MediaPipe Holistic → `zone_detector` → OSC semántico → share GPU.
- Consistencia entre documentación operativa y comportamiento real del bridge MCP.

**Listo para próxima auditoría**

- Validar iluminación real de sala con webcam y MediaPipe.
- Confirmar que el operador puede arrancar runtime y bridge sin conflicto de puerto.
- Verificar instalación del backend correcto de share (`SpoutGL` o `syphon-python`).
- Repetir revisión sobre estabilidad larga y comportamiento de los 6 triggers con
  visitantes reales.

### Historial de versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| v0.1 | 2026-06-13 | Creación inicial — pipeline completo, 6 triggers, 5 shaders |
| v0.2 | 2026-06-14 | Auditoría operativa: MCP embebido tolerante a doble arranque y README ajustado |

*Última revisión: 2026-06-14 · Desarrollado con claude-opus-4-8 · claude-sonnet-4-6*
