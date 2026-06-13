# Setup TouchDesigner · P2 Skeleton Semántico
## Aún Sorprendo · JIFREX · MediaPipe Holistic

Una sola máquina (MSI o Mac). El frame del esqueleto llega por **Spout**
(Windows) o **Syphon** (macOS), no por NDI. Los datos semánticos llegan por
**OSC :9000**.

---

## Red de nodos (orden de conexión)

```
[Spout In TOP]  (Windows)  ó  [Syphon Spout In TOP] (macOS)
   fuente: "JIFREX-P2-SKELETON"  ← overlay esqueleto + máscara desde Python
      │
[GLSL TOP: glsl_hands]      ← Trigger 1 · planos cubistas fríos (mano extendida)
      │
[GLSL TOP: glsl_torso]      ← Trigger 2 · estelas circulares (rotación cadera)
      │
[GLSL TOP: glsl_head]       ← Trigger 3 · transición de paleta (inclinación)
      │
      ├───────────────────────────────────────────────┐
      │                                               │
[GLSL TOP: glsl_glitch] ←── input[1]: Feedback TOP    │  (Trigger 4 · salto)
      │                                               │
[Feedback TOP] ─────────────────────────────────────────┘
   opacidad: 0.90 (ajustar en sala)
      │
[GLSL TOP: glsl_dual]       ← Trigger 6 · diálogo cubista (2 personas)
      │
[Level TOP: fade_global]    ← Trigger 5 · fade a reposo (pose estática > 3 s)
      │
[Out TOP] → 2× Epson PowerLite 5510
```

La cadena es **acumulativa**: cada GLSL TOP recibe como `input[0]` la salida del
anterior, de modo que los efectos se superponen sin pelearse. `glsl_glitch` vive
dentro de un loop Feedback para las partículas con estela.

---

## Configuración Spout / Syphon In

| Plataforma | Operador | Source Name |
|-----------|----------|-------------|
| Windows (MSI) | **Spout In TOP** | `JIFREX-P2-SKELETON` |
| macOS (Mac) | **Syphon Spout In TOP** | `JIFREX-P2-SKELETON` |

Latencia GPU→GPU ~1 ms. Si el TOP aparece negro, verificar que
`skeleton_runtime.py` esté corriendo y que `SHARE_ENABLE = True` en `config.py`.

---

## Configuración OSC In

| Parámetro | Valor |
|-----------|-------|
| Protocol | UDP |
| Port | 9000 |
| Local Address | 127.0.0.1 (una máquina) o IP del render |

Conectar **OSC In DAT** → **Script DAT** con `td_osc_to_uniforms.py`
· Execute On: `Table Change`

El OSC In DAT debe estar en modo que entregue **un argumento por columna**
(address en col 0, args en col 1, 2, 3...). Es el modo por defecto del OSC In DAT.

---

## Uniforms por GLSL TOP

### glsl_hands (zona_hands.glsl) — Trigger 1

| Uniform | Slot | Fuente OSC | Inicial |
|---------|------|-----------|---------|
| uHandTrigger | value0 | /cuerpo/mano_derecha[0] | 0.0 |
| uWristHeight | value1 | /cuerpo/mano_derecha[1] | 0.0 |
| uArmOpenR | value2 | /cuerpo/metrica/arm_open_right | 0.0 |
| uTime | value3 | absTime.seconds | auto |

### glsl_torso (zona_torso.glsl) — Trigger 2

| Uniform | Slot | Fuente OSC | Inicial |
|---------|------|-----------|---------|
| uHipTrigger | value0 | /cuerpo/cadera[0] | 0.0 |
| uHipAngle | value1 | /cuerpo/cadera[1] | 0.0 |
| uHipVelocity | value2 | /cuerpo/cadera[2] | 0.0 |
| uTime | value3 | absTime.seconds | auto |

### glsl_head (zona_head.glsl) — Trigger 3

| Uniform | Slot | Fuente OSC | Inicial |
|---------|------|-----------|---------|
| uHeadTrigger | value0 | /cuerpo/cabeza[0] | 0.0 |
| uHeadRoll | value1 | /cuerpo/cabeza[1] | 0.0 |
| uHeadPitch | value2 | /cuerpo/cabeza[2] | 0.0 |
| uTime | value3 | absTime.seconds | auto |

### glsl_glitch (global_glitch.glsl) — Trigger 4

| Uniform | Slot | Fuente OSC | Inicial |
|---------|------|-----------|---------|
| uGlitch | value0 | /cuerpo/global/glitch | 0.0 |
| uMotionRatio | value1 | /cuerpo/metrica/motion_ratio | 0.0 |
| uFlowMean | value2 | /cuerpo/metrica/flow_mean | 0.0 |
| uTime | value3 | absTime.seconds | auto |

`input[1]` = Feedback TOP (estela de partículas).

### glsl_dual (dual_body.glsl) — Trigger 6

| Uniform | Slot | Fuente OSC | Inicial |
|---------|------|-----------|---------|
| uBlobCount | value0 | /cuerpo/blob_count | 1.0 |
| uTime | value1 | absTime.seconds | auto |

---

## Trigger 5 — Pose estática (fade a reposo)

No tiene shader propio: se implementa con un **Level TOP** (`fade_global`) al
final de la cadena cuyo `Opacity` baja cuando llega `/cuerpo/pose_estatica`.

Opción recomendada (en `td_osc_to_uniforms.py`, ya preparado el comentario):
1. Crear un **Constant CHOP** `pose_estatica` (1 canal).
2. En el Script DAT, al recibir `/cuerpo/pose_estatica` con arg0 = 1, hacer
   `op('pose_estatica').par.value0 = 1` (o usar el segundo arg = segundos quieto
   para un fade proporcional).
3. Conectar ese CHOP a `fade_global` → `Opacity` con un **Lag CHOP** (lag ~2 s)
   para que el fade sea gradual, no abrupto.

---

## Trigger / Zona dominante

`/cuerpo/trigger_zona` entrega un string (`zona_hands`, `zona_torso`,
`zona_head`, `global`, `pose_estatica`, `none`). Útil para:
- Un **Text TOP** de debug que muestre qué zona disparó.
- Un **Switch TOP** si se prefiere mostrar una sola zona a la vez en vez de la
  cadena acumulativa.

---

## Hot-reload de shaders (Folder DAT)

1. **Folder DAT** apuntando a `P2-Skeleton-MediaPipe/shaders/`
2. Conectar a cada GLSL TOP → `Pixel Shader > File`
3. `File Active`: ON

Al guardar cualquier `.glsl`, TouchDesigner recarga en < 1 s sin cortar el stream.

---

## Secuencia narrativa del visitante

| Estado | Condición OSC | Efecto |
|--------|--------------|--------|
| **Entrada** | blob_count=1, flujo bajo | Esqueleto base, escena en reposo |
| **Brazo arriba** | /cuerpo/mano_derecha[0]=1 | Planos cubistas fríos emergen de la mano |
| **Rotación de cadera** | /cuerpo/cadera[0]=1 | Estelas circulares giran al ritmo del cuerpo |
| **Inclinación de cabeza** | /cuerpo/cabeza[0]=1 | Toda la proyección cambia de temperatura |
| **Salto** | /cuerpo/global/glitch=1 | Glitch + partículas máximas |
| **Quietud > 3 s** | /cuerpo/pose_estatica[0]=1 | Fade gradual → reposo |
| **2 personas** | /cuerpo/blob_count=2 | Diálogo cubista entre cuerpos |

---

## Calibración en sala (Galería Fernando Cano)

- **Spout/Syphon source**: confirmar que el nombre coincide con
  `config.SHARE_SENDER_NAME`.
- **Feedback opacity** (glsl_glitch): empezar en 0.90, bajar si la estela tapa.
- **Umbrales semánticos**: ajustar en vivo con `mcp_bridge.py` (puerto 9001) sin
  reiniciar — ver README principal del proyecto.
- **Iluminación**: este sistema depende de joints visibles. Hacer la visita
  técnica y calibrar `MP_MIN_DETECTION_CONF` / `MP_MODEL_COMPLEXITY` con la luz
  real de la galería antes de confirmar.
- Correr prueba de 8 horas continuas antes de la inauguración.

---

## Archivos de esta carpeta

| Archivo | Descripción |
|---------|-------------|
| `zona_hands.glsl` | Trigger 1: planos cubistas fríos (mano extendida) |
| `zona_torso.glsl` | Trigger 2: estelas circulares (rotación de cadera) |
| `zona_head.glsl` | Trigger 3: transición de paleta (inclinación de cabeza) |
| `global_glitch.glsl` | Trigger 4: glitch + partículas (salto / movimiento brusco) |
| `dual_body.glsl` | Trigger 6: diálogo cubista entre 2 cuerpos |
| `td_osc_to_uniforms.py` | Script DAT: OSC semántico → uniforms |
| `README_TouchDesigner.md` | Este archivo |
