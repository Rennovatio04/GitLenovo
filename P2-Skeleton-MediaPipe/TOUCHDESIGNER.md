# TouchDesigner — Guía de Operación Completa
## P2 · Skeleton Semántico MediaPipe · Aún Sorprendo · JIFREX

---

## Antes de abrir TouchDesigner

### Una sola máquina — MSI o Mac

P2 corre en una **sola máquina**: Python y TouchDesigner en el mismo equipo.  
La textura viaja por Spout (Windows) o Syphon (macOS) — sin red, latencia ~1 ms.

| Plataforma | Textura | OSC |
|-----------|---------|-----|
| Windows (MSI) | **Spout** → `SpoutGL` pip | UDP loopback `127.0.0.1:9000` |
| macOS (Mac M3 Max) | **Syphon** → `syphon-python` pip | UDP loopback `127.0.0.1:9000` |

### En Python (hacer primero)

```bash
# 1. Activar entorno (Python 3.11 o 3.12 — OBLIGATORIO)
source venv/bin/activate          # macOS
.\venv\Scripts\Activate.ps1      # Windows

# 2. Editar config.py si TD no corre en la misma máquina
#    OSC_HOST = "127.0.0.1"  ← dejar así si es la misma máquina
#    CAM_INDEX = 0           ← verificar el índice real de la webcam

# 3. Terminal A — MCP bridge (opcional, ajuste en vivo)
python mcp_bridge.py

# 4. Terminal B — Pipeline principal
python skeleton_runtime.py
```

Verificar que el log aparece:
```
[   zona_hands] 29.8 fps | blob=1 | flow=0.42 | hip_v=  2.1° | static=0.0s
```

---

## Abrir TouchDesigner

1. **Misma máquina** donde corre Python
2. Menú **File → New** → proyecto en blanco
3. Guardar como: `P2_JIFREX_Skeleton.toe`

---

## Paso 1 — Crear el OSC In DAT

> Recibe 8+ rutas semánticas desde skeleton_runtime.py

1. Click derecho → **DAT** → `OSC In`
2. Renombrar: `osc_in`
3. Parámetros:
   - **Protocol**: UDP
   - **Port**: `9000`
   - **Local Address**: dejar vacío
   - **Active**: ON
4. Verificar: la tabla muestra rutas `/cuerpo/trigger_zona`, `/cuerpo/flow_mean`, etc.

---

## Paso 2 — Crear el Script DAT

1. Click derecho → **DAT** → `Script`
2. Renombrar: `osc_to_uniforms`
3. Conectar: salida de `osc_in` → entrada de `osc_to_uniforms`
4. Parámetros:
   - **Execute**: `Table Change`
5. Abrir editor → pegar contenido de `shaders/td_osc_to_uniforms.py` → cerrar

---

## Paso 3 — Crear la entrada de video

> El overlay del esqueleto llega desde Python por Spout o Syphon

### En Windows (Spout)
1. Click derecho → **TOP** → `Spout In`
2. Renombrar: `skeleton_in`
3. Parámetros:
   - **Source Name**: `JIFREX-P2-SKELETON`

### En macOS (Syphon)
1. Click derecho → **TOP** → `Syphon Spout In`
2. Renombrar: `skeleton_in`
3. Parámetros:
   - **Application**: (seleccionar la app Python de la lista desplegable)
   - **Server Name**: `JIFREX-P2-SKELETON`

**Verificar**: el TOP muestra el overlay del esqueleto sobre fondo negro.  
Si aparece negro: Python no está enviando el share. Verificar que `syphon-python` o `SpoutGL` está instalado y que `SHARE_ENABLE = True` en `config.py`.

---

## Paso 4 — Crear GLSL TOP: glsl_hands

> Trigger 1: planos geométricos cubistas (mano extendida)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_hands`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `skeleton_in`
4. Parámetros:
   - **Pixel Shader File**: `shaders/zona_hands.glsl`
   - **File Active**: ON
5. Pestaña **Vectors 1** — agregar uniforms:
   - `uHandTrigger`  value0 = `0`
   - `uWristHeight`  value0 = `0`
   - `uArmOpenR`     value0 = `0`
   - `uTime`         value0 = `0`

---

## Paso 5 — Crear GLSL TOP: glsl_torso

> Trigger 2: estelas circulares (rotación de cadera)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_torso`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `glsl_hands`
4. Parámetros:
   - **Pixel Shader File**: `shaders/zona_torso.glsl`
   - **File Active**: ON
5. Uniforms:
   - `uHipTrigger`   value0 = `0`
   - `uHipAngle`     value0 = `0`
   - `uHipVelocity`  value0 = `0`
   - `uTime`         value0 = `0`

---

## Paso 6 — Crear GLSL TOP: glsl_head

> Trigger 3: transición de paleta por inclinación de cabeza

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_head`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `glsl_torso`
4. Parámetros:
   - **Pixel Shader File**: `shaders/zona_head.glsl`
   - **File Active**: ON
5. Uniforms:
   - `uHeadTrigger`  value0 = `0`
   - `uHeadRoll`     value0 = `0`
   - `uHeadPitch`    value0 = `0`
   - `uTime`         value0 = `0`

---

## Paso 7 — Crear el Feedback TOP

1. Click derecho → **TOP** → `Feedback`
2. Renombrar: `feedback_loop`
3. Parámetros:
   - **Target TOP**: `glsl_glitch` (se completará en el paso 8)
   - **Opacity**: `0.90`

---

## Paso 8 — Crear GLSL TOP: glsl_glitch

> Trigger 4: glitch + partículas en salto/movimiento brusco (con Feedback)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_glitch`  ← **nombre exacto**
3. Conectar:
   - Entrada [0]: cable de `glsl_head`
   - Entrada [1]: cable de `feedback_loop`
4. Parámetros:
   - **Pixel Shader File**: `shaders/global_glitch.glsl`
   - **File Active**: ON
5. Uniforms:
   - `uGlitch`       value0 = `0`
   - `uMotionRatio`  value0 = `0`
   - `uFlowMean`     value0 = `0`
   - `uTime`         value0 = `0`
6. Volver a `feedback_loop` → **Target TOP**: escribir `glsl_glitch` → loop cerrado

---

## Paso 9 — Crear GLSL TOP: glsl_dual

> Trigger 6: diálogo cubista entre 2 cuerpos simultáneos

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_dual`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `glsl_glitch`
4. Parámetros:
   - **Pixel Shader File**: `shaders/dual_body.glsl`
   - **File Active**: ON
5. Uniforms:
   - `uBlobCount`  value0 = `1`
   - `uTime`       value0 = `0`

---

## Paso 10 — Trigger 5: fade a reposo (pose estática)

> No tiene shader propio — se implementa con un Level TOP + CHOP

1. Click derecho → **CHOP** → `Constant`
   - Renombrar: `pose_estatica_chop`
   - Agregar un canal: nombre `v1`, valor inicial `1.0`

2. Click derecho → **CHOP** → `Lag`
   - Renombrar: `fade_lag`
   - Conectar: salida de `pose_estatica_chop` → entrada de `fade_lag`
   - Parámetros:
     - **Lag +**: `0` (subida inmediata al detectar movimiento)
     - **Lag -**: `2.0` (fade de 2 segundos al dejar de moverse)

3. Click derecho → **TOP** → `Level`
   - Renombrar: `fade_global`
   - Conectar entrada [0]: cable de `glsl_dual`
   - Parámetro **Opacity** → hacer clic derecho → `Export` → seleccionar canal de `fade_lag`

4. En `osc_to_uniforms` (Script DAT), el código ya mapea `/cuerpo/pose_estatica`:
   cuando llega valor `1.0` → `pose_estatica_chop.par.value0 = 0` (inicia el fade).

---

## Paso 11 — Out TOP

1. Click derecho → **TOP** → `Out`
2. Renombrar: `out_proyector`
3. Conectar: cable de `fade_global` → entrada de `out_proyector`
4. **Dialogs → Window Placement**: configurar salida a los proyectores Epson

---

## Diagrama completo de conexiones

```
[Python skeleton_runtime.py — misma máquina]
    │ Spout/Syphon (~1ms)    │ OSC UDP :9000 (loopback)
    ▼                        ▼
[skeleton_in: Spout/Syphon In TOP]    [osc_in: OSC In DAT]
    │                                      │
    │                              [osc_to_uniforms: Script DAT]
    │                                      │ (actualiza par.value en cada shader)
    ▼
[glsl_hands]  ← uHandTrigger, uWristHeight, uArmOpenR, uTime
    │
[glsl_torso]  ← uHipTrigger, uHipAngle, uHipVelocity, uTime
    │
[glsl_head]   ← uHeadTrigger, uHeadRoll, uHeadPitch, uTime
    │
[glsl_glitch] ← input[1]: feedback_loop
    │            uGlitch, uMotionRatio, uFlowMean, uTime
    │
[feedback_loop: Feedback TOP]  opacidad: 0.90
    └──→ (Target TOP = glsl_glitch — loop cerrado)
    │
[glsl_dual]   ← uBlobCount, uTime
    │
[fade_global: Level TOP]  ← Opacity exportada desde fade_lag CHOP
    │
[out_proyector: Out TOP]
    │
2× Epson PowerLite 5510 via HDBaseT Cat6A
```

---

## Nombres de operadores — tabla de referencia crítica

> **Si un nombre no coincide exactamente, el Script DAT no enviará los uniforms.**

| Operador | Tipo | Nombre en TD | Shader / Propósito |
|----------|------|-------------|-------------------|
| `osc_in` | DAT OSC In | `osc_in` | Recibe OSC de Python |
| `osc_to_uniforms` | DAT Script | `osc_to_uniforms` | Distribuye OSC a shaders |
| `skeleton_in` | TOP Spout/Syphon | `skeleton_in` | Video de Python |
| `glsl_hands` | TOP GLSL | **`glsl_hands`** | Trigger 1 mano |
| `glsl_torso` | TOP GLSL | **`glsl_torso`** | Trigger 2 cadera |
| `glsl_head` | TOP GLSL | **`glsl_head`** | Trigger 3 cabeza |
| `glsl_glitch` | TOP GLSL | **`glsl_glitch`** | Trigger 4 salto |
| `glsl_dual` | TOP GLSL | **`glsl_dual`** | Trigger 6 dos cuerpos |
| `feedback_loop` | TOP Feedback | `feedback_loop` | Estela de glitch |
| `pose_estatica_chop` | CHOP Constant | `pose_estatica_chop` | Trigger 5 reposo |
| `fade_lag` | CHOP Lag | `fade_lag` | Suaviza el fade |
| `fade_global` | TOP Level | `fade_global` | Fade de opacidad global |
| `out_proyector` | TOP Out | `out_proyector` | Salida a proyectores |

---

## Rutas OSC de referencia rápida

| Ruta | Tipo | Va a |
|------|------|------|
| `/cuerpo/trigger_zona` | string | Debug / Switch TOP opcional |
| `/cuerpo/mano_derecha` | float[3] | `glsl_hands` uniforms 0,1,2 |
| `/cuerpo/cadera` | float[3] | `glsl_torso` uniforms 0,1,2 |
| `/cuerpo/cabeza` | float[3] | `glsl_head` uniforms 0,1,2 |
| `/cuerpo/global/glitch` | float | `glsl_glitch` uniform 0 |
| `/cuerpo/metrica/motion_ratio` | float | `glsl_glitch` uniform 1 |
| `/cuerpo/metrica/flow_mean` | float | `glsl_glitch` uniform 2 |
| `/cuerpo/blob_count` | float | `glsl_dual` uniform 0 |
| `/cuerpo/pose_estatica` | float[2] | `pose_estatica_chop` |

---

## Lista de verificación antes de la inauguración

- [ ] Python 3.11 o 3.12 confirmado (`python --version`)
- [ ] `skeleton_runtime.py` corre sin errores
- [ ] `skeleton_in` TOP: muestra overlay de esqueleto (no negro)
- [ ] `osc_in` DAT: tabla muestra rutas `/cuerpo/...`
- [ ] Levantar brazo → `glsl_hands` reacciona (planos azules)
- [ ] Rotar cadera → `glsl_torso` reacciona (estelas circulares)
- [ ] Inclinar cabeza → `glsl_head` cambia la paleta
- [ ] Saltar → `glsl_glitch` dispara (flash + distorsión)
- [ ] Quietud > 3 s → `fade_global` hace fade lentamente
- [ ] Dos personas frente a la cámara → `glsl_dual` activo
- [ ] Proyectores: imagen correctamente keystone en el piso
- [ ] Prueba de 8 horas continuas

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `skeleton_in` en negro | Spout/Syphon no instalado | `pip install SpoutGL` (Win) o `pip install syphon-python` (Mac) |
| `skeleton_in` en negro | Nombre de servidor no coincide | Verificar `SHARE_SENDER_NAME` en `config.py` |
| Ningún trigger dispara | Python 3.13/3.14 | MediaPipe no tiene wheels — reinstalar con Python 3.12 |
| Joints inestables | Iluminación difícil | Subir `MP_MODEL_COMPLEXITY` a 2 en `config.py` (cuesta fps) |
| Trigger 5 (fade) no funciona | Export mal configurado | Verificar que `fade_global.par.Opacity` tiene el Export de `fade_lag` |
| Glitch muy frecuente | Jitter de joints | Subir `motion_ratio_threshold` vía MCP bridge `:9001` |
