# TouchDesigner — Guía de Operación Completa
## P4 · DeepLabv3 + CoreML · Referencia Antimodular · Aún Sorprendo · JIFREX

---

## Antes de abrir TouchDesigner

### Una sola máquina — Mac M3 Max (recomendado)

Python y TouchDesigner corren en el **mismo Mac M3 Max**.  
La textura viaja por Syphon (GPU→GPU, ~1 ms). OSC por loopback.  
Neural Engine corre DeepLabv3 (15–25 ms/frame) → GPU Metal completamente libre para TD.

> Si se usa MSI + Mac en red: Python en MSI emite la máscara por NDI,  
> TouchDesigner en Mac la recibe. Reemplazar el `Syphon In TOP` por un `NDI In TOP`.  
> Esta guía asume el caso óptimo: Mac M3 Max sola.

### Requisito previo — Conversión del modelo

```bash
# EJECUTAR UNA SOLA VEZ en el Mac M3 Max
pip install tensorflow tensorflow-hub coremltools pillow
python convert_to_coreml.py
# → Genera: DeepLabV3.mlpackage (15–25 ms/frame en Neural Engine)
```

### En Python (hacer primero)

```bash
# 1. Activar entorno (Python 3.11 o 3.12)
source venv/bin/activate

# 2. Verificar que el modelo existe
ls DeepLabV3.mlpackage    # debe existir

# 3. Terminal A — MCP bridge (opcional, ajuste en vivo)
python mcp_bridge.py

# 4. Terminal B — Pipeline
python deeplab_runtime.py --preview
```

Verificar en el log:
```
[       ]  59.3fps | coreml  18ms | area= 89412px | flow=0.082 | cov=0.0466
```
La columna `coreml 18ms` confirma que está usando el Neural Engine.  
Si dice `tensorflow` o `simulate`, el modelo no se encontró.

---

## Abrir TouchDesigner

1. Abrir TouchDesigner en el Mac M3 Max
2. **File → New** → proyecto en blanco
3. Guardar como: `P4_JIFREX_DeepLab.toe`

---

## Paso 1 — Crear el OSC In DAT

1. Click derecho → **DAT** → `OSC In`
2. Renombrar: `osc_in`
3. Parámetros:
   - **Protocol**: UDP
   - **Port**: `9000`
   - **Local Address**: dejar vacío
   - **Active**: ON
4. Verificar: tabla muestra `/jifrex/p4/trigger`, `/jifrex/p4/flow_mean`, `/jifrex/p4/coverage_ratio`, etc.

---

## Paso 2 — Crear el Script DAT

1. Click derecho → **DAT** → `Script`
2. Renombrar: `osc_to_uniforms`
3. Conectar: salida de `osc_in` → entrada de `osc_to_uniforms`
4. **Execute**: `Table Change`
5. Abrir editor → pegar contenido de `shaders/td_osc_to_uniforms.py` → cerrar

---

## Paso 3 — Crear el Syphon In TOP

> Recibe la máscara DeepLabv3 subpixel-accurate desde Python

1. Click derecho → **TOP** → `Syphon Spout In`
2. Renombrar: `syphon_mask`
3. Parámetros:
   - **Server Name**: `JIFREX-P4-DEEPLAB`
4. Verificar: el TOP muestra la silueta del visitante en blanco sobre negro.  
   La silueta debe incluir dedos y contorno del cabello (eso distingue a DeepLabv3 de MediaPipe).

Si aparece negro:
- Python no está corriendo
- `syphon-python` no está instalado: `pip install syphon-python`
- El nombre `JIFREX-P4-DEEPLAB` no coincide con `SYPHON_SERVER_NAME` en `config.py`

---

## Paso 4 — Crear el Null TOP de máscara limpia

> Copia de la máscara para input[1] y input[2] de los shaders que la necesitan

1. Click derecho → **TOP** → `Null`
2. Renombrar: `mask_orig`
3. Conectar: cable de `syphon_mask` → entrada de `mask_orig`

---

## Paso 5 — Crear el GLSL TOP: glsl_halo

> Halo con bordes subpixel-accurate + uCoverageRatio (Antimodular)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_halo`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `syphon_mask`
4. Parámetros:
   - **Pixel Shader File**: `shaders/halo_glow_precise.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Nombre | Descripción | Valor inicial |
   |------|--------|-------------|---------------|
   | value0 | `uFlowMean` | Movimiento promedio | `0.0` |
   | value1 | `uCoverageRatio` | Ocupación del frame (Antimodular) | `0.0` |
   | value2 | `uPresence` | Persona detectada | `0.0` |
   | value3 | `uTime` | Tiempo del patch | `0.0` |

---

## Paso 6 — Crear el GLSL TOP: glsl_glitch

> Glitch sin falsos triggers (DeepLabv3 no produce jitter de modelo)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_glitch`  ← **nombre exacto**
3. Conectar:
   - Entrada [0]: cable de `glsl_halo`
   - Entrada [1]: cable de `mask_orig`
4. Parámetros:
   - **Pixel Shader File**: `shaders/glitch_precise.glsl`
   - **File Active**: ON
5. Uniforms:

   | Slot | Nombre | Descripción | Valor inicial |
   |------|--------|-------------|---------------|
   | value0 | `uTrigger` | Trigger anti-FP | `0.0` |
   | value1 | `uMotionRatio` | Fracción de pixels en movimiento | `0.0` |
   | value2 | `uNoiseLevel` | Ruido de blobs (Antimodular) | `0.0` |
   | value3 | `uTime` | Tiempo del patch | `0.0` |

---

## Paso 7 — Crear el Feedback TOP

1. Click derecho → **TOP** → `Feedback`
2. Renombrar: `feedback_loop`
3. Parámetros:
   - **Target TOP**: `glsl_particles` (se completará en el paso 8)
   - **Opacity**: `0.90`

---

## Paso 8 — Crear el GLSL TOP: glsl_particles

> Partículas que emergen del contorno exacto — incluyendo dedos y cabello

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_particles`  ← **nombre exacto**
3. Conectar:
   - Entrada [0]: cable de `glsl_glitch`
   - Entrada [1]: cable de `feedback_loop`
   - Entrada [2]: cable de `mask_orig`
4. Parámetros:
   - **Pixel Shader File**: `shaders/particles_precise.glsl`
   - **File Active**: ON
   - **Input Count**: `3`
5. Uniforms:

   | Slot | Nombre | Descripción | Valor inicial |
   |------|--------|-------------|---------------|
   | value0 | `uFlowMean` | Movimiento promedio | `0.0` |
   | value1 | `uMotionRatio` | Fracción de pixels en movimiento | `0.0` |
   | value2 | `uPresence` | Persona detectada | `0.0` |
   | value3 | `uCoverageRatio` | Ocupación del frame | `0.0` |
   | value4 | `uNoiseLevel` | Ruido de blobs | `0.0` |
   | value5 | `uTime` | Tiempo del patch | `0.0` |

6. Volver a `feedback_loop` → **Target TOP**: escribir `glsl_particles` → loop cerrado

---

## Paso 9 — Level TOP y Out TOP

1. Click derecho → **TOP** → `Level`
   - Renombrar: `level_final`
   - Conectar: cable de `glsl_particles` → entrada de `level_final`
   - **Brightness**: `1.0`, **Gamma**: `1.0`, **Contrast**: `1.05`

2. Click derecho → **TOP** → `Out`
   - Renombrar: `out_proyector`
   - Conectar: cable de `level_final` → entrada de `out_proyector`
   - **Dialogs → Window Placement** → configurar los 2 proyectores Epson

---

## Diagrama completo de conexiones

```
[Python deeplab_runtime.py — Mac M3 Max]
    │ CoreML Neural Engine (15–25ms)
    │
    │ Syphon (~1ms)              │ OSC UDP :9000 (loopback)
    ▼                            ▼
[syphon_mask: Syphon Spout In]  [osc_in: OSC In DAT]
    │                                │
    ├──→ [mask_orig: Null TOP]   [osc_to_uniforms: Script DAT]
    │        │                       │ (actualiza par.value en los 3 shaders)
    │        │                       ▼
    └──→ [glsl_halo]  ← uFlowMean, uCoverageRatio, uPresence, uTime
              │
         [glsl_glitch] ← input[1]: mask_orig
              │            uTrigger, uMotionRatio, uNoiseLevel, uTime
              │
         [glsl_particles] ← input[1]: feedback_loop
              │             ← input[2]: mask_orig
              │              uFlowMean, uMotionRatio, uPresence,
              │              uCoverageRatio, uNoiseLevel, uTime
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

## Diferencia visual vs P1 — qué esperar en TouchDesigner

| Aspecto | P1 (MediaPipe) | P4 (DeepLabv3) |
|---------|---------------|----------------|
| Silueta en `syphon_mask` | Borde aproximado, puede parpadear | Borde subpixel, estable entre frames |
| Halo en `glsl_halo` | Irregular, sigue el ruido del borde | Perfectamente uniforme y suave |
| Frecuencia de glitch | Frecuente (jitter de MediaPipe dispara trigger) | Poco frecuente (solo movimiento real) |
| Partículas en `glsl_particles` | Emergen de aproximación del borde | Emergen de dedos y cabello (contorno exacto) |
| uCoverageRatio | No existe | `0.04–0.10` para visitante a 2m — halo escala con esto |
| uNoiseLevel | No existe | Sube cuando hay varias personas → glitch más intenso |

---

## Nombres de operadores — tabla crítica

| Operador | Tipo | Nombre en TD | Shader / Fuente |
|----------|------|-------------|----------------|
| `osc_in` | DAT OSC In | `osc_in` | Recibe OSC de Python |
| `osc_to_uniforms` | DAT Script | `osc_to_uniforms` | Distribuye a shaders |
| `syphon_mask` | TOP Syphon Spout In | `syphon_mask` | `JIFREX-P4-DEEPLAB` |
| `mask_orig` | TOP Null | `mask_orig` | Copia de máscara |
| `glsl_halo` | TOP GLSL | **`glsl_halo`** | `halo_glow_precise.glsl` |
| `glsl_glitch` | TOP GLSL | **`glsl_glitch`** | `glitch_precise.glsl` |
| `glsl_particles` | TOP GLSL | **`glsl_particles`** | `particles_precise.glsl` |
| `feedback_loop` | TOP Feedback | `feedback_loop` | Target = glsl_particles |
| `level_final` | TOP Level | `level_final` | Brillo final |
| `out_proyector` | TOP Out | `out_proyector` | Proyectores Epson |

---

## Rutas OSC de referencia rápida

| Ruta | Tipo | Va a |
|------|------|------|
| `/jifrex/p4/trigger` | float 0/1 | `glsl_glitch` uTrigger |
| `/jifrex/p4/presence` | float 0/1 | `glsl_halo` uPresence + `glsl_particles` uPresence |
| `/jifrex/p4/flow_mean` | float 0–3 | `glsl_halo` uFlowMean + `glsl_particles` uFlowMean |
| `/jifrex/p4/motion_ratio` | float 0–1 | `glsl_glitch` uMotionRatio + `glsl_particles` uMotionRatio |
| `/jifrex/p4/coverage_ratio` | float 0–1 | `glsl_halo` uCoverageRatio + `glsl_particles` uCoverageRatio |
| `/jifrex/p4/noise_level` | float 0–N | `glsl_glitch` uNoiseLevel + `glsl_particles` uNoiseLevel |
| `/jifrex/p4/blob_area` | int | Disponible para debug / Text TOP |
| `/jifrex/p4/blob_count` | int | Disponible para debug / Text TOP |

---

## Ajuste de `coverage_ratio` en sala

`uCoverageRatio` es la métrica central de P4 (Antimodular). Controla:
- El tamaño del halo (más cobertura = halo más grande)
- La densidad de partículas
- El decay del Feedback TOP (más cobertura = estela más larga)

Valores típicos según distancia de la cámara:
| Distancia visitante–cámara | coverage_ratio esperado |
|---------------------------|------------------------|
| 1 m (muy cerca) | 0.15–0.25 |
| 2 m (galería normal) | 0.04–0.10 |
| 3 m (cámara alta) | 0.01–0.04 |

Si los valores son muy bajos, subir `coverage_boost` en MCP bridge:
```
Enviar a :9001 → /mcp/set/coverage_boost  3.0
```

---

## Lista de verificación antes de la inauguración

- [ ] `DeepLabV3.mlpackage` existe en el directorio del proyecto
- [ ] Log de Python muestra `coreml XYms` (no `tensorflow` ni `simulate`)
- [ ] `syphon_mask` TOP: muestra silueta con dedos y contorno de cabello visibles
- [ ] `osc_in` DAT: tabla muestra `/jifrex/p4/coverage_ratio` (nueva métrica de P4)
- [ ] `glsl_halo`: halo uniforme y suave (sin irregularidades en el borde)
- [ ] `glsl_glitch`: glitch solo dispara con movimiento real, NO en reposo
- [ ] `glsl_particles`: partículas emergen de los bordes finos (dedos visibles)
- [ ] `feedback_loop`: estela de ~2 segundos
- [ ] `coverage_ratio` calibrado para la distancia real de la cámara en galería
- [ ] Proyectores: keystone y posición correctas
- [ ] Prueba de 8 horas continuas

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `syphon_mask` en negro | `DeepLabV3.mlpackage` no existe | Ejecutar `python convert_to_coreml.py` |
| Backend muestra `simulate` | mlpackage no encontrado o fuera del directorio | Verificar que el archivo está en la raíz del proyecto |
| Latencia > 40ms en log | CoreML usa CPU en lugar de Neural Engine | Reconvertir con `compute_units=ct.ComputeUnit.ALL` |
| Halo irregular | Máscara llega con compresión | Verificar que Syphon está usando GPU directamente |
| Glitch muy frecuente | `flow_threshold` demasiado bajo | Subir a `0.45` vía `/mcp/set/flow_threshold 0.45` en :9001 |
| `coverage_ratio` siempre 0 | Máscara no tiene píxeles activos | Verificar que `syphon_mask` muestra la silueta |
| `glsl_particles` Input Count incorrecto | Por defecto es 1 | GLSL TOP → Common → **Input Count = 3** |
