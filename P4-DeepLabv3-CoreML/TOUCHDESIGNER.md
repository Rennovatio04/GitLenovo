# TouchDesigner — Guía de Operación Completa
## P4 · DeepLabv3 + CoreML · Referencia Antimodular · Aún Sorprendo · JIFREX

> **Para el operador técnico:** esta guía asume que sabes moverte en TouchDesigner
> pero nunca has visto este proyecto. P4 es el más robusto visualmente — la
> calidad de la silueta es notablemente superior a P1/P2 y eso se traduce directamente
> en efectos más precisos y elegantes. Calcular ~2 horas para el montaje completo.

---

## Concepto artístico — qué estamos construyendo

P4 vincula dos artistas: Pablo Picasso y Rafael Lozano-Hemmer (Antimodular).

| | |
|--|--|
| **Picasso** | Ponía el proceso mental del artista en el lienzo — el cuadro no existe sin la mente que lo piensa |
| **Lozano-Hemmer** | Pone el proceso perceptivo del espectador en el espacio — la imagen no existe sin el cuerpo que la activa |
| **P4** | Conecta ambos en la Galería Fernando Cano — el piso no existe sin el visitante que lo habita |

La diferencia técnica clave de P4: **DeepLabv3** (un modelo de segmentación semántica
de Google) producce una silueta **subpixel-accurate** — con los contornos del cabello,
los dedos individuales, y la silueta de la ropa visibles con una precisión que MediaPipe
no puede igualar. Esto cambia la estética de toda la instalación:

| Aspecto | P1/P2 (MediaPipe) | P4 (DeepLabv3) |
|---------|-------------------|----------------|
| Calidad del borde de la silueta | Aproximado, puede parpadear en el borde | Subpixel-accurate, estable entre frames |
| Halo | Irregular, sigue el ruido del borde | Perfectamente uniforme y suave |
| Partículas | Emergen de la aproximación del borde | Emergen de dedos y cabello (contorno exacto) |
| Frecuencia de glitch | Más frecuente (el jitter de modelo dispara triggers) | Poco frecuente — solo movimiento real |

**Vínculo con Lozano-Hemmer (Antimodular):**
El `coverage_ratio` — nueva métrica exclusiva de P4 — cuantifica la "ocupación del
espacio" del visitante: qué fracción del frame cubre su cuerpo. Lozano-Hemmer
trabaja sistemáticamente con esta idea: la presencia del cuerpo en el espacio es
medible, y esa medición puede convertirse en imagen. Cuanto más llena el visitante
el frame, más intenso el halo, más partículas, más estela.

**Flujo de la experiencia:**
1. El visitante entra — DeepLabv3 produce la silueta subpixel en 15-25 ms
2. Al acercarse a la cámara (coverage aumenta): el halo crece en proporción
3. En movimiento: halo pulsante + partículas del borde (incluyendo dedos)
4. Movimiento brusco: glitch — más escaso que en P1, más impactante
5. Al alejarse: el halo decrece, las partículas se disuelven
6. Al salir: la estela decae en ~2-3 s y la imagen vuelve a negro

---

## Antes de abrir TouchDesigner

### Una sola máquina — Mac M3 Max (recomendado)

Python y TouchDesigner corren en el **mismo Mac M3 Max**.
La textura viaja por Syphon (GPU→GPU, ~1 ms). OSC por loopback.
DeepLabv3 en el **Neural Engine** (15-25 ms/frame) → GPU Metal completamente
libre para TouchDesigner.

> **Modo alternativo MSI+Mac:** si se decide usar el MSI con Python headless
> y el Mac con TouchDesigner, reemplazar el `Syphon Spout In TOP` por un `NDI In TOP`
> apuntando a la fuente NDI que el MSI emitiría. Esta guía documenta el caso óptimo.

### PASO PREVIO OBLIGATORIO — Conversión del modelo CoreML

**Este paso se ejecuta UNA SOLA VEZ en el Mac M3 Max antes de la primera exhibición.**
El modelo resultante (`DeepLabV3.mlpackage`) es lo que permite la inferencia rápida.
Sin él, el sistema usa TensorFlow en CPU (~50-80 ms) o simulación.

```bash
# En el Mac M3 Max, con internet, UNA SOLA VEZ
pip install tensorflow tensorflow-hub coremltools pillow
python convert_to_coreml.py

# Verificar que se generó el archivo:
ls -lh DeepLabV3.mlpackage
# Debe mostrar el directorio con el modelo (~10-15 MB)
```

El script descarga el modelo desde TF Hub y lo convierte al formato CoreML
optimizado para el Neural Engine de Apple Silicon. El tiempo de conversión
es ~5 minutos en el M3 Max. Una vez generado, no vuelve a necesitar internet.

### En Python — hacer PRIMERO, antes de abrir TD

```bash
# 1. Verificar Python 3.11 o 3.12
python3 --version

# 2. Activar entorno
source venv/bin/activate

# 3. Verificar que el modelo CoreML existe
ls DeepLabV3.mlpackage   # debe existir

# 4. Terminal A — MCP bridge (opcional)
python mcp_bridge.py

# 5. Terminal B — Pipeline (con preview para verificar la silueta)
python deeplab_runtime.py --preview
```

El log de arranque debe mostrar:
```
[P4] Backend: CoreML
[P4] Camara 0 abierta — 1920x1080
```
Y el log periódico debe mostrar:
```
[       ]  59.3fps | coreml  18ms | area= 89412px | flow=0.082 | motion=0.041 | cov=0.0466 | noise=0.021 | cd= 0
```
Campos del log:
- `coreml 18ms`: confirma que el Neural Engine está corriendo (no CPU). Si muestra `tensorflow` o `simulate`, el modelo CoreML no se encontró.
- `area= 89412px`: tamaño del blob principal en píxeles. Con visitante a 2m: ~80K-120K px
- `cov=0.0466`: coverage_ratio — el 4.66% del frame está cubierto por la persona
- `noise=0.021`: muy bajo = silueta limpia. Alto = varios blobs o fondo ruidoso
- `cd= 0`: cooldown. Cuando es > 0, no dispararán triggers aunque haya movimiento

Con `--preview`, se abre una ventana mostrando el frame original con la silueta
superpuesta en cyan. Verificar que la silueta incluye **los dedos y el contorno
del cabello** — esto distingue P4 de los otros proyectos.

---

## Abrir TouchDesigner

1. Abrir TouchDesigner en el Mac M3 Max
2. **File → New** → proyecto en blanco
3. Guardar como: `P4_JIFREX_DeepLab.toe` en el directorio del proyecto

---

## Paso 1 — Crear el OSC In DAT

**Qué recibe:** 8 canales OSC que incluyen las 4 métricas estilo Antimodular de P4
(`blob_area`, `noise_level`, `coverage_ratio`, `blob_count`) más las métricas estándar
de movimiento (`flow_mean`, `motion_ratio`, `trigger`, `presence`).

1. Click derecho → **DAT** → `OSC In`
2. Renombrar: `osc_in`
3. Parámetros:
   - **Protocol**: UDP
   - **Port**: `9000`
   - **Local Address**: dejar vacío
   - **Active**: ON
4. **Verificar:** tabla muestra `/jifrex/p4/trigger`, `/jifrex/p4/coverage_ratio`, etc.
   Nota el prefijo `/jifrex/p4/` — diferente al `/jifrex/` de P1 para facilitar
   el uso simultáneo de ambos sistemas en un mismo patch de TD si se desea.

---

## Paso 2 — Crear el Script DAT

**Diferencia clave vs P1/P2:** el Script DAT de P4 mapea las rutas
`/jifrex/p4/coverage_ratio` y `/jifrex/p4/noise_level` a uniforms que no
existen en los otros proyectos. Verificar que se pega el script correcto.

1. Click derecho → **DAT** → `Script`
2. Renombrar: `osc_to_uniforms`
3. Conectar: salida de `osc_in` → entrada de `osc_to_uniforms`
4. **Execute**: `Table Change`
5. Abrir editor → pegar contenido de `shaders/td_osc_to_uniforms.py` → cerrar

---

## Paso 3 — Crear el Syphon In TOP

**Qué es esta textura:** la máscara binaria de DeepLabv3 — silueta blanca perfectamente
definida sobre negro. La diferencia con P1/P2 es inmediatamente visible: el borde
tiene una precisión que permite identificar dedos individuales y el contorno del cabello.

1. Click derecho → **TOP** → `Syphon Spout In`
2. Renombrar: `syphon_mask`
3. Parámetros:
   - **Application**: seleccionar la app Python de la lista desplegable
   - **Server Name**: `JIFREX-P4-DEEPLAB`
     *(debe coincidir con `SYPHON_SERVER_NAME` en `config.py`)*
4. **Verificar:** el TOP muestra la silueta del visitante.
   **Clave de verificación:** si puedes distinguir los dedos de la mano cuando
   el visitante la levanta, el modelo CoreML está funcionando correctamente.
   Si el borde es borroso o cuadrado, se está usando TensorFlow en CPU — el modelo
   CoreML no se encontró. Ejecutar `python convert_to_coreml.py` y reiniciar.

**Si aparece negro:**
- Python no está corriendo, o `SHARE_ENABLE = True` no está en `config.py`
- `syphon-python` no instalado: `pip install syphon-python`
- El nombre `JIFREX-P4-DEEPLAB` no coincide con `SYPHON_SERVER_NAME` en `config.py`
- El backend es `simulate`: el modelo no se encontró → ejecutar `convert_to_coreml.py`

---

## Paso 4 — Crear el Null TOP de máscara limpia

**Por qué:** el GLSL TOP `glsl_glitch` necesita la máscara original (sin modificar
por el halo) para confinar el glitch a la silueta real. El `glsl_particles` también
la necesita para detectar el borde exacto donde nacen las partículas.
Un Null TOP crea una referencia sin costo de procesamiento.

1. Click derecho → **TOP** → `Null`
2. Renombrar: `mask_orig`
3. Conectar: cable de `syphon_mask` → entrada de `mask_orig`

---

## Paso 5 — Crear el GLSL TOP: glsl_halo

**Concepto:** el halo de P4 tiene dos diferencias fundamentales con el de P1:

1. **Precisión:** el multiplicador del borde es 9.0 (vs 6.0 en P1), porque con
   DeepLabv3 el borde es tan limpio que un multiplicador alto no produce artefactos.
   El resultado es un halo más definido y elegante.

2. **`uCoverageRatio` (Antimodular):** el tamaño del halo no depende solo del
   movimiento — también depende de cuánto espacio ocupa el visitante en el frame.
   Un visitante cerca de la cámara (coverage 0.15) tiene un halo mayor que uno lejos
   (coverage 0.03). El cuerpo determina su propia escala visual.

**Qué deberías ver:**
- Visitante lejos (1.5m+, coverage < 0.03): halo azul tenue, muy contenido
- Visitante a distancia normal (2m, coverage 0.05): halo azul-plata de tamaño medio
- Visitante cerca de la cámara (1m, coverage 0.15+): halo grande, casi blanco
- Sin movimiento pero presente: halo pulsa suavemente en reposo (~0.05 amplitud)
- Con movimiento rápido: halo palpita intensamente, crece hasta el límite del frame

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_halo`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `syphon_mask`
4. Parámetros:
   - **Pixel Shader File**: `shaders/halo_glow_precise.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Uniform Name | Rango | Qué controla |
   |------|-------------|-------|--------------|
   | `uniform0` | `uFlowMean` | 0.0–3.0 | Intensidad de pulsación y brillo del halo. 0 = reposo, 1.5+ = máximo |
   | `uniform1` | `uCoverageRatio` | 0.0–1.0 | Tamaño del halo y temperatura de color. Más coverage = halo más grande y más blanco |
   | `uniform2` | `uPresence` | 0 ó 1 | Activa el halo de reposo cuando el visitante está quieto. 0 = sin halo |
   | `uniform3` | `uTime` | segundos | Animación del pulso de reposo |

   **Calibración de `uCoverageRatio` en sala:**
   El coverage depende de la distancia de la cámara al visitante y de la resolución.
   Con la cámara a 2m y resolución 1920×1080, los valores típicos son:
   - Visitante muy cerca (1m): 0.15–0.25
   - Distancia normal de galería (2m): 0.04–0.10
   - Visitante lejos (3m+): 0.01–0.04

   Si los valores son siempre muy bajos, usar el MCP bridge para amplificarlos:
   ```
   Enviar a :9001 → /mcp/set/coverage_boost 3.0
   ```
   Con `coverage_boost = 3.0`, un coverage real de 0.04 se envía a TD como 0.12.

---

## Paso 6 — Crear el GLSL TOP: glsl_glitch

**Concepto:** el glitch de P4 es el mismo algoritmo que P1 pero con una diferencia
fundamental de comportamiento: se dispara mucho menos frecuentemente.

En P1 con MediaPipe, el modelo produce pequeñas oscilaciones en el borde de la
silueta (el "jitter de estimación") que el optical flow interpreta como movimiento,
disparando el glitch con más frecuencia de lo artísticamente deseado.

En P4 con DeepLabv3, los bordes son estables entre frames. El optical flow solo
detecta movimiento real del cuerpo. Resultado: el glitch aparece solo cuando el
visitante se mueve de verdad. Cada disparo es más raro y por tanto más impactante.

El uniform `uNoiseLevel` (Antimodular): si hay varias personas o el fondo tiene
ruido, el noise_level sube y el glitch se vuelve más intenso — más caos visual
corresponde a más fragmentación digital.

**Qué deberías ver:**
- Sin trigger: el frame de `glsl_halo` pasa exactamente sin cambio
- Al trigger: flash blanco inmediato, luego bandas horizontales desplazadas con
  aberración cromática. La frecuencia de bandas escala con `motion_ratio`.
- Con `noise_level` alto: más bandas, más intensas (múltiples personas = más caos)
- El glitch dura un frame visual (el trigger tiene cooldown de 30 frames = ~0.5 s)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_glitch`  ← **nombre exacto**
3. Conectar:
   - Entrada [0]: cable de `glsl_halo`
   - Entrada [1]: cable de `mask_orig`
4. Parámetros:
   - **Pixel Shader File**: `shaders/glitch_precise.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Uniform Name | Rango | Qué controla |
   |------|-------------|-------|--------------|
   | `uniform0` | `uTrigger` | 0 ó 1 | Activa el glitch. 0 = pass-through exacto (sin modificación del frame) |
   | `uniform1` | `uMotionRatio` | 0.0–1.0 | Intensidad: ancho de las bandas y separación del RGB split |
   | `uniform2` | `uNoiseLevel` | 0.0–2.0 | Ruido Antimodular: más blobs = más bandas y más intensidad |
   | `uniform3` | `uTime` | segundos | Para randomizar las bandas entre frames |

   **Sobre el threshold de trigger (`uTrigger`):**
   El trigger tiene cooldown de 30 frames (~0.5 s) en Python. Si el glitch
   dispara demasiado frecuentemente en sala (ropa del mismo color que el fondo,
   fondo en movimiento), subir `flow_threshold` via MCP bridge:
   ```
   Enviar a :9001 → /mcp/set/flow_threshold 0.45
   ```
   El default es 0.35 (más bajo que P1/0.50 porque DeepLabv3 no produce jitter).

---

## Paso 7 — Crear el Feedback TOP

**Cómo funciona el loop:**
En cada frame, `glsl_particles` recibe como input[1] su propia salida del frame anterior,
multiplicada por `decay`. Las partículas que nacieron en el borde de la silueta persisten
y decaen progresivamente. La velocidad de decay depende de `uPresence` y `uCoverageRatio`:
- Con presencia y coverage alto: decay = 0.97 (estela de ~3 s)
- Con presencia y coverage bajo: decay = 0.94 (estela de ~1.5 s)
- Sin presencia: decay = 0.72 (estela desaparece en ~5 frames)

1. Click derecho → **TOP** → `Feedback`
2. Renombrar: `feedback_loop`
3. Parámetros:
   - **Target TOP**: `glsl_particles` (se completará en el paso siguiente)
   - **Opacity**: `0.90`

---

## Paso 8 — Crear el GLSL TOP: glsl_particles

**Lo que hace este shader que los otros no pueden:**
Con DeepLabv3, el shader puede detectar extremidades finas (dedos, cabello) como
una categoría de borde especial (`thinEdge`), y generar un segundo set de partículas
más pequeñas y densas solo en esos bordes. El resultado es una "niebla de partículas"
que sale específicamente de los dedos cuando el visitante mueve las manos — un efecto
que es imposible de lograr con la calidad de silueta de MediaPipe.

**Cómo funciona `thinEdge` en el shader:**
```glsl
float thinEdge(vec2 uv) {
    float c    = texture(sTD2DInputs[2], uv).r;  // valor de la máscara (0 o 1)
    float edge = maskEdge(uv);                    // gradiente en el borde
    // En las extremidades: el gradiente es alto PERO la máscara es baja
    // (porque son regiones pequeñas donde el valor de la máscara transiciona rápido)
    return edge * clamp(1.0 - c * 2.0, 0.0, 1.0);
}
```
Los dedos tienen `c` bajo (poca área de máscara) pero `edge` alto (el borde cambia
bruscamente). La multiplicación selecciona exactamente esas regiones.

**Qué deberías ver:**
- Silueta quieta: partículas tenues emergiendo del borde, incluyendo los dedos
- En movimiento: lluvia de partículas del borde + partículas finas en dedos/cabello
- Movimiento muy rápido (flow > 1.5): partículas casi blancas, densas, veloces
- Visitante cerca (coverage alto): más partículas, estela más larga
- Sin visitante: la estela decae rápidamente (~5 frames) a negro

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_particles`  ← **nombre exacto**
3. Conectar:
   - Entrada [0]: cable de `glsl_glitch`
   - Entrada [1]: cable de `feedback_loop`
   - Entrada [2]: cable de `mask_orig`
4. En la pestaña **Common** → **Input Count**: `3`
   *(CRÍTICO: sin esto, el shader no puede detectar el borde de la máscara)*
5. Parámetros:
   - **Pixel Shader File**: `shaders/particles_precise.glsl`
   - **File Active**: ON
6. Uniforms (Vectors 1):

   | Slot | Uniform Name | Rango | Qué controla |
   |------|-------------|-------|--------------|
   | `uniform0` | `uFlowMean` | 0.0–3.0 | Velocidad y color de las partículas. 0 = azul lento, 3+ = blanco veloz |
   | `uniform1` | `uMotionRatio` | 0.0–1.0 | Densidad: `numParticles = 14 + motionRatio×20 + coverage×8` (14 a 42 partículas) |
   | `uniform2` | `uPresence` | 0 ó 1 | Controla el decay: 1 = decay lento, 0 = decay rápido (fade a negro) |
   | `uniform3` | `uCoverageRatio` | 0.0–1.0 | Densidad adicional y estela más larga según ocupación del espacio |
   | `uniform4` | `uNoiseLevel` | 0.0–2.0 | Ruido Antimodular — no usado directamente en partículas pero disponible para extensiones |
   | `uniform5` | `uTime` | segundos | Animación y randomización de partículas |

7. Volver a `feedback_loop` → **Target TOP**: escribir `glsl_particles` → loop cerrado

---

## Paso 9 — Level TOP y Out TOP

1. Click derecho → **TOP** → `Level`
   - Renombrar: `level_final`
   - Conectar: cable de `glsl_particles` → entrada de `level_final`
   - **Brightness**: `1.0`
   - **Gamma**: `1.0` (los shaders ya están calibrados linealmente)
   - **Contrast**: `1.05`

2. Click derecho → **TOP** → `Out`
   - Renombrar: `out_proyector`
   - Conectar: cable de `level_final` → entrada de `out_proyector`
   - **Dialogs → Window Placement** → configurar los 2 proyectores Epson
   - **Resolution**: `1920 × 1200` (WUXGA nativo del Epson 5510)

---

## Diagrama completo de conexiones

```
[Python deeplab_runtime.py — Mac M3 Max]
    │ CoreML Neural Engine (15–25ms/frame)
    │
    │ Syphon (~1ms)                 │ OSC UDP :9000 (loopback, <1ms)
    ▼                               ▼
[syphon_mask: Syphon Spout In]   [osc_in: OSC In DAT]
    │ silueta subpixel-accurate        │
    │ (dedos y cabello visibles)  [osc_to_uniforms: Script DAT]
    │                                  │ actualiza 3 GLSL TOPs a ~60fps
    ├──→ [mask_orig: Null TOP]         │
    │        │                         │
    │        │                         ▼
    └──→ [glsl_halo]  ←── uFlowMean, uCoverageRatio, uPresence, uTime
              │            qué ves: halo uniforme proporcional a coverage y flow
              │            cuanto más llena el frame el visitante, mayor el halo
              │
         [glsl_glitch]  ← input[1]: mask_orig (confina glitch a silueta real)
              │             uTrigger, uMotionRatio, uNoiseLevel, uTime
              │             qué ves: pass-through limpio / glitch preciso al trigger
              │             (menos frecuente que P1 — más impactante cuando ocurre)
              │
         [glsl_particles]  ← input[1]: feedback_loop
              │              ← input[2]: mask_orig (borde exacto DeepLabv3)
              │               uFlowMean, uMotionRatio, uPresence,
              │               uCoverageRatio, uNoiseLevel, uTime
              │               qué ves: partículas del borde + partículas finas
              │               en dedos y cabello (exclusivo de P4)
              │
         [feedback_loop: Feedback TOP]  Opacity: 0.90
         └──→ Target TOP = glsl_particles  (loop cerrado)
              │
         [level_final: Level TOP]  Brightness: 1.0, Contrast: 1.05
              │
         [out_proyector: Out TOP]
              │
    2× Epson PowerLite 5510 via HDBaseT Cat6A
    Techo 4.5 m · WUXGA 1920×1200 · 5500 lm
```

---

## Diferencia visual vs P1 — qué esperar al comparar en TouchDesigner

Si tienes acceso a un patch de P1 para comparar, estas son las diferencias
visuales específicas a buscar:

| Lo que buscas | En P1 (syphon/NDI mask) | En P4 (syphon_mask) |
|--------------|------------------------|---------------------|
| Borde de silueta con mano levantada | Borde pixelado o borroso | Dedos individuales visibles |
| Halo en `glsl_halo` con quietud | Irregular, con "burbujas" de artefacto | Perfectamente uniforme y suave |
| Frecuencia de glitch sin movimiento activo | Puede disparar 2-3 veces por minuto | No dispara — solo con movimiento real |
| Partículas de `glsl_particles` | Emergen de la aproximación del borde | Emergen visiblemente de los dedos |
| `uCoverageRatio` | No existe | 0.04–0.10 para visitante a 2m |

---

## Nombres de operadores — tabla crítica

| Operador | Tipo | Nombre exacto | Verificar |
|----------|------|--------------|-----------|
| OSC In DAT | DAT | `osc_in` | Tabla muestra `/jifrex/p4/...` |
| Script DAT | DAT | `osc_to_uniforms` | Sin errores en Textport |
| Syphon In TOP | TOP | `syphon_mask` | Silueta con dedos visibles (no negro) |
| Null TOP | TOP | `mask_orig` | Mismo frame que syphon_mask |
| GLSL TOP 1 | TOP | **`glsl_halo`** | halo_glow_precise.glsl cargado |
| GLSL TOP 2 | TOP | **`glsl_glitch`** | glitch_precise.glsl cargado |
| GLSL TOP 3 | TOP | **`glsl_particles`** | particles_precise.glsl, Input Count=3 |
| Feedback TOP | TOP | `feedback_loop` | Target TOP = glsl_particles |
| Level TOP | TOP | `level_final` | Brightness=1.0, Gamma=1.0 |
| Out TOP | TOP | `out_proyector` | Pantalla correcta, resolución WUXGA |

---

## Calibración de `coverage_ratio` en sala

`uCoverageRatio` es la métrica central de P4 — el "uniform Antimodular". Controla:
- El tamaño del halo en `glsl_halo` (más coverage = halo más grande)
- La densidad de partículas en `glsl_particles` (más coverage = más partículas)
- El decay del Feedback (más coverage = estela más larga)

Los valores cambian con la distancia de la cámara al espacio de interacción:

| Distancia visitante–cámara | coverage_ratio típico | Acción |
|---------------------------|----------------------|--------|
| 1 m (muy cerca) | 0.15–0.25 | Sin ajuste necesario |
| 2 m (galería normal) | 0.04–0.10 | Sin ajuste o coverage_boost leve |
| 3 m (cámara alta en techo) | 0.01–0.04 | Usar coverage_boost 2.0–3.0 |

Ajuste en vivo sin reiniciar:
```
Enviar a :9001 → /mcp/set/coverage_boost  <float>
```
Con `coverage_boost = 2.0`, un coverage real de 0.04 llega a TD como 0.08,
activando efectos que con el valor crudo serían demasiado sutiles para verlos.

---

## Lista de verificación antes de la inauguración

- [ ] `DeepLabV3.mlpackage` existe en el directorio del proyecto
- [ ] Log de Python muestra `Backend: CoreML` y `coreml XYms` (no tensorflow ni simulate)
- [ ] `syphon_mask` TOP: silueta visible **con dedos y cabello** (verificar con mano levantada)
- [ ] `osc_in` DAT: tabla muestra `/jifrex/p4/coverage_ratio` (confirmación de que el sistema P4 está corriendo)
- [ ] `glsl_halo`: halo uniforme y suave — sin irregularidades en el borde
- [ ] `glsl_glitch`: glitch no dispara en reposo; sí dispara al saltar o gesticular bruscamente
- [ ] `glsl_particles`: partículas emergen de los bordes finos (dedos visibles al mover la mano)
- [ ] `feedback_loop`: estela de ~2 s en movimiento normal, ~3 s cuando el visitante está cerca
- [ ] `coverage_ratio` calibrado para la distancia real de la cámara (`coverage_boost` ajustado)
- [ ] Proyectores: keystone y posición correctas en el piso
- [ ] Prueba de 8 horas continuas (temperatura M3 Max, fps estable, sin memory leak)

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `syphon_mask` negro | `DeepLabV3.mlpackage` no existe | Ejecutar `python convert_to_coreml.py` |
| Backend muestra `simulate` | mlpackage fuera del directorio de trabajo | Verificar que el archivo está en el mismo directorio que `deeplab_runtime.py` |
| Backend muestra `tensorflow` | mlpackage no encontrado en macOS pero TF sí | Verificar ruta en `config.py → COREML_MODEL_PATH` |
| Latencia > 40ms en log | CoreML usa CPU en lugar de Neural Engine | Reconvertir con `compute_units=ct.ComputeUnit.ALL` (ya está así por defecto, pero verificar) |
| Halo irregular | Máscara llega con artifacts | Verificar que Syphon está usando GPU directo (`pip show syphon-python` → versión instalada) |
| Glitch muy frecuente | `flow_threshold` bajo | Subir a 0.45 vía `/mcp/set/flow_threshold 0.45` en :9001 |
| `coverage_ratio` siempre 0 | Máscara sin píxeles activos | Verificar que `syphon_mask` muestra la silueta (no negro) |
| `glsl_particles` Input Count incorrecto | Por defecto es 1 | GLSL TOP → pestaña Common → **Input Count = 3** |
| `osc_to_uniforms` con error | Nombre de op incorrecto | Verificar tabla de nombres — son case-sensitive |

---

## Rutas OSC de referencia rápida

| Ruta | Tipo | Rango | Va a |
|------|------|-------|------|
| `/jifrex/p4/trigger` | float 0/1 | 0 ó 1 | `glsl_glitch` uTrigger |
| `/jifrex/p4/presence` | float 0/1 | 0 ó 1 | `glsl_halo` uPresence + `glsl_particles` uPresence |
| `/jifrex/p4/flow_mean` | float | 0.0–3.0 | `glsl_halo` uFlowMean + `glsl_particles` uFlowMean |
| `/jifrex/p4/motion_ratio` | float | 0.0–1.0 | `glsl_glitch` uMotionRatio + `glsl_particles` uMotionRatio |
| `/jifrex/p4/coverage_ratio` | float | 0.0–1.0 | `glsl_halo` uCoverageRatio + `glsl_particles` uCoverageRatio |
| `/jifrex/p4/noise_level` | float | 0.0–2.0 | `glsl_glitch` uNoiseLevel + `glsl_particles` uNoiseLevel |
| `/jifrex/p4/blob_area` | int | 0–N px | Disponible para debug (Text TOP en el monitor del operador) |
| `/jifrex/p4/blob_count` | int | 0–N | Disponible para debug (Text TOP en el monitor del operador) |
