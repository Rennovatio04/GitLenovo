# TouchDesigner — Guía de Operación Completa
## P3 · Multi-Cámara · 3 Perspectivas Simultáneas · Aún Sorprendo · JIFREX

---

## Antes de abrir TouchDesigner

### Una sola máquina — Mac M3 Max (obligatorio)

Python y TouchDesigner corren en el **mismo Mac M3 Max**.  
Las 3 texturas viajan por Syphon (GPU→GPU, ~1 ms por textura, sin red).  
Las métricas viajan por OSC UDP loopback.

> **CRÍTICO — Thunderbolt 4:** cada cámara DEBE estar en su propio puerto TB4.  
> Un hub USB compartido destruye la sincronización de frames.
>
> | Puerto | Cámara |
> |--------|--------|
> | TB4 #1 | OAK-D Pro W (frontal) |
> | TB4 #2 | Logitech C922 (lateral) |
> | TB4 #3 | Logitech C922 (cenital) |

### En Python (hacer primero)

```bash
# 1. Python 3.11 o 3.12
python3 --version

# 2. Activar entorno
source venv/bin/activate

# 3. Verificar que DepthAI ve la OAK-D
python3 -c "import depthai as dai; print(dai.Device.getAllAvailableDevices())"

# 4. Terminal A — MCP bridge (opcional)
python mcp_bridge.py

# 5. Terminal B — Pipeline (con preview para verificar)
python multicam_runtime.py --preview
```

Verificar en el log que sync_delta < 33ms:
```
[      ] 29.8fps | sync= 18ms (97% OK) | A=0.21 B=0.18 C=0.14 | triple=0.0012
```

---

## Abrir TouchDesigner

1. Abrir TouchDesigner en el Mac M3 Max
2. **File → New** → proyecto en blanco
3. Guardar como: `P3_JIFREX_MultiCamara.toe`

---

## Paso 1 — Crear el OSC In DAT

1. Click derecho → **DAT** → `OSC In`
2. Renombrar: `osc_in`
3. Parámetros:
   - **Protocol**: UDP
   - **Port**: `9000`
   - **Local Address**: dejar vacío
   - **Active**: ON
4. Verificar: tabla muestra `/multicam/triple_ratio`, `/multicam/a/flow_mean`, etc.

---

## Paso 2 — Crear el Script DAT

1. Click derecho → **DAT** → `Script`
2. Renombrar: `osc_to_uniforms`
3. Conectar: salida de `osc_in` → entrada de `osc_to_uniforms`
4. **Execute**: `Table Change`
5. Abrir editor → pegar contenido de `shaders/td_osc_to_uniforms.py` → cerrar

---

## Paso 3 — Crear las 3 entradas Syphon

> Una por cámara. Cada una recibe la máscara de su perspectiva.

### Cámara A — Frontal (azul)
1. Click derecho → **TOP** → `Syphon Spout In`
2. Renombrar: `syphon_in_a`
3. Parámetros:
   - **Server Name**: `JIFREX-CAM-A-FRONTAL`
4. Verificar: silueta del visitante desde el frente

### Cámara B — Lateral derecha (ocre)
1. Click derecho → **TOP** → `Syphon Spout In`
2. Renombrar: `syphon_in_b`
3. Parámetros:
   - **Server Name**: `JIFREX-CAM-B-LATERAL`

### Cámara C — Cenital (rosa)
1. Click derecho → **TOP** → `Syphon Spout In`
2. Renombrar: `syphon_in_c`
3. Parámetros:
   - **Server Name**: `JIFREX-CAM-C-CENITAL`

**Verificar los 3**: si alguno aparece negro, Python no está emitiendo ese servidor.  
Causa frecuente: `syphon-python` no instalado → `pip install syphon-python`.

---

## Paso 4 — Crear los 3 GLSL TOP de distorsión UV

> Una instancia por cámara. Cada perspectiva tiene su deformación geométrica.  
> `uPerspective` es un valor FIJO (no viene de OSC):  
> A = 0.0 (radial), B = 1.0 (horizontal), C = 2.0 (espiral)

### glsl_distort_a — frontal (radial)
1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_distort_a`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `syphon_in_a`
4. Parámetros:
   - **Pixel Shader File**: `shaders/distorsion_uv.glsl`
   - **File Active**: ON
5. Uniforms:
   - `uPerspective`  value0 = **`0.0`** ← FIJO, no cambia con OSC
   - `uFlowMean`     value0 = `0`
   - `uTime`         value0 = `0`

### glsl_distort_b — lateral (deformación horizontal)
1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_distort_b`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `syphon_in_b`
4. Mismo shader: `shaders/distorsion_uv.glsl`
5. Uniforms:
   - `uPerspective`  value0 = **`1.0`** ← FIJO
   - `uFlowMean`     value0 = `0`
   - `uTime`         value0 = `0`

### glsl_distort_c — cenital (rotación)
1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_distort_c`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `syphon_in_c`
4. Mismo shader: `shaders/distorsion_uv.glsl`
5. Uniforms:
   - `uPerspective`  value0 = **`2.0`** ← FIJO
   - `uFlowMean`     value0 = `0`
   - `uTime`         value0 = `0`

---

## Paso 5 — Crear el GLSL TOP: glsl_composite

> Screen blend de las 3 siluetas coloreadas → triple coincidencia = blanco brillante

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_composite`  ← **nombre exacto**
3. Conectar:
   - Entrada [0]: cable de `glsl_distort_a`
   - Entrada [1]: cable de `glsl_distort_b`
   - Entrada [2]: cable de `glsl_distort_c`
4. Parámetros:
   - **Pixel Shader File**: `shaders/composite_multicamara.glsl`
   - **File Active**: ON
   - **Inputs**: asegurarse de que el GLSL TOP acepta 3 inputs — en **Common** → **Input Count**: `3`
5. Uniforms:
   - `uFlowA`        value0 = `0`
   - `uFlowB`        value0 = `0`
   - `uFlowC`        value0 = `0`
   - `uTripleRatio`  value0 = `0`
   - `uAnyPresence`  value0 = `0`
   - `uTime`         value0 = `0`

---

## Paso 6 — Crear la máscara compuesta para partículas

> `glsl_particles` necesita la máscara combinada de las 3 cámaras en input[2]

1. Click derecho → **TOP** → `Composite`
2. Renombrar: `mask_composite`
3. Conectar:
   - Entrada: las 3 salidas de `syphon_in_a`, `syphon_in_b`, `syphon_in_c`
4. Parámetros:
   - **Operation**: `Maximum` (equivalente a `max(a, b, c)` en GLSL)

---

## Paso 7 — Crear el Feedback TOP

1. Click derecho → **TOP** → `Feedback`
2. Renombrar: `feedback_loop`
3. Parámetros:
   - **Target TOP**: `glsl_particles` (se completará en el paso 8)
   - **Opacity**: `0.90`

---

## Paso 8 — Crear el GLSL TOP: glsl_particles

> Partículas con comportamiento diferente por perspectiva + estela Feedback

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_particles`  ← **nombre exacto**
3. Conectar:
   - Entrada [0]: cable de `glsl_composite`
   - Entrada [1]: cable de `feedback_loop`
   - Entrada [2]: cable de `mask_composite`
4. Parámetros:
   - **Pixel Shader File**: `shaders/particulas_perspectiva.glsl`
   - **File Active**: ON
   - **Input Count**: `3`
5. Uniforms:
   - `uPerspective`  value0 = `0`  ← puede quedar fijo en 0, o asignarlo dinámicamente
   - `uFlowA`        value0 = `0`
   - `uFlowB`        value0 = `0`
   - `uFlowC`        value0 = `0`
   - `uMotionA`      value0 = `0`
   - `uMotionB`      value0 = `0`
   - `uMotionC`      value0 = `0`
   - `uTripleRatio`  value0 = `0`
   - `uAnyPresence`  value0 = `0`
   - `uTime`         value0 = `0`
6. Volver a `feedback_loop` → **Target TOP**: escribir `glsl_particles` → loop cerrado

---

## Paso 9 — Level TOP y Out TOP

1. Click derecho → **TOP** → `Level`
   - Renombrar: `level_final`
   - Conectar: cable de `glsl_particles` → entrada de `level_final`
   - **Brightness**: `1.0`, **Contrast**: `1.05`

2. Click derecho → **TOP** → `Out`
   - Renombrar: `out_proyector`
   - Conectar: cable de `level_final` → entrada de `out_proyector`
   - **Dialogs → Window Placement** → seleccionar los 2 proyectores Epson

---

## Diagrama completo de conexiones

```
[Python multicam_runtime.py — Mac M3 Max]
    │ Syphon A (~1ms)   │ Syphon B (~1ms)   │ Syphon C (~1ms)   │ OSC :9000
    ▼                   ▼                   ▼                   ▼
[syphon_in_a]       [syphon_in_b]       [syphon_in_c]       [osc_in]
    │                   │                   │                   │
[glsl_distort_a]   [glsl_distort_b]   [glsl_distort_c]   [osc_to_uniforms]
uPerspective=0.0   uPerspective=1.0   uPerspective=2.0        │
    │                   │                   │       (actualiza uniforms en todos los shaders)
    └───────────────────┴───────────────────┘
                        │ [0][1][2]
                        ▼
                [glsl_composite]  ← uFlowA/B/C, uTripleRatio, uAnyPresence, uTime
                        │
                        │    ┌─── [mask_composite: Composite TOP MAX]
                        │    │    ← syphon_in_a + syphon_in_b + syphon_in_c
                        ▼    ▼
                [glsl_particles] ← input[0]: glsl_composite
                        │        ← input[1]: feedback_loop
                        │        ← input[2]: mask_composite
                        │
                [feedback_loop: Feedback TOP]  opacidad: 0.90
                └──→ (Target TOP = glsl_particles)
                        │
                [level_final: Level TOP]
                        │
                [out_proyector: Out TOP]
                        │
              2× Epson PowerLite 5510 via HDBaseT Cat6A
```

---

## Nombres de operadores — tabla crítica

| Operador | Tipo | Nombre en TD | Verificar |
|----------|------|-------------|-----------|
| `osc_in` | DAT OSC In | `osc_in` | Tabla con /multicam/... |
| `osc_to_uniforms` | DAT Script | `osc_to_uniforms` | Sin errores en consola |
| `syphon_in_a` | TOP Syphon Spout In | `syphon_in_a` | Muestra silueta frontal |
| `syphon_in_b` | TOP Syphon Spout In | `syphon_in_b` | Muestra silueta lateral |
| `syphon_in_c` | TOP Syphon Spout In | `syphon_in_c` | Muestra silueta cenital |
| `glsl_distort_a` | TOP GLSL | **`glsl_distort_a`** | uPerspective=0 fijo |
| `glsl_distort_b` | TOP GLSL | **`glsl_distort_b`** | uPerspective=1 fijo |
| `glsl_distort_c` | TOP GLSL | **`glsl_distort_c`** | uPerspective=2 fijo |
| `mask_composite` | TOP Composite | `mask_composite` | Modo: Maximum |
| `glsl_composite` | TOP GLSL | **`glsl_composite`** | Input Count = 3 |
| `glsl_particles` | TOP GLSL | **`glsl_particles`** | Input Count = 3 |
| `feedback_loop` | TOP Feedback | `feedback_loop` | Target = glsl_particles |
| `level_final` | TOP Level | `level_final` | Brightness = 1.0 |
| `out_proyector` | TOP Out | `out_proyector` | Proyectores Epson |

---

## Verificación del efecto cubista

1. **Un visitante solo** frente a la cámara A: silueta azul sola
2. **Un visitante** frente a A y B simultáneamente: azul + ocre = Screen blend (verde-amarillo)
3. **Un visitante** frente a las 3 cámaras: **luz blanca brillante** — triple coincidencia
4. El log de Python debe mostrar `[TRIPLE]` cuando hay solapamiento suficiente

Si la luz blanca no aparece:
- Verificar que las 3 máscaras se solapan en la imagen compuesta
- Verificar que `mask_composite` usa **Maximum** (no Average ni Add)
- Ajustar `TRIPLE_THRESHOLD` en `config.py` o vía MCP bridge

---

## Lista de verificación antes de la inauguración

- [ ] OAK-D Pro W detectada por DepthAI (aparece en `getAllAvailableDevices()`)
- [ ] sync_delta en log < 33ms (aparece como `sync= XXms`)
- [ ] Las 3 entradas Syphon muestran imagen (no negro)
- [ ] `glsl_composite`: triple coincidencia produce blanco con las manos
- [ ] `glsl_particles`: partículas con comportamiento diferente por perspectiva
- [ ] `feedback_loop`: estela persiste ~2 segundos
- [ ] Halos de reposo (azul/ocre/rosa) visibles cuando no hay visitante
- [ ] Proyectores: keystone y posición correctas en el piso
- [ ] Prueba de 8 horas continuas

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| Syphon en negro | Python no emite | Verificar `syphon-python` instalado y runtime corriendo |
| sync_delta > 33ms | Hub USB compartido | Conectar cada cámara a su propio puerto TB4 directamente |
| Sin luz blanca | Masks no solapan | Verificar posiciones físicas de las 3 cámaras |
| `glsl_composite` en negro | Input Count incorrecto | GLSL TOP → Common → Input Count = 3 |
| `glsl_particles` sin estela | Feedback no cerrado | Verificar Target TOP = `glsl_particles` en Feedback TOP |
| OSC sin datos | config.py IP incorrecta | Verificar `OSC_HOST = "127.0.0.1"` (misma máquina) |
