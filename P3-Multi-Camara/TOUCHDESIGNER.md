# TouchDesigner — Guía de Operación Completa
## P3 · Multi-Cámara · 3 Perspectivas Simultáneas · Aún Sorprendo · JIFREX

> **Para el operador técnico:** esta guía asume que sabes moverte en TouchDesigner
> pero nunca has visto este proyecto. P3 es el más ambicioso de los 4 — 3 entradas
> Syphon simultáneas, un composite Screen blend de 3 capas, y un shader de partículas
> con comportamiento diferenciado por perspectiva. Calcular ~3 horas para el montaje.

---

## Concepto artístico — qué estamos construyendo

Picasso no pintaba lo que veía desde un ángulo. Pintaba lo que sabía que estaba ahí
desde todos los ángulos posibles simultáneamente — la nariz de frente y de perfil en
el mismo plano, el ojo desde arriba y desde el costado en el mismo cuadro.

P3 hace esto literalmente: **3 cámaras en 3 ángulos distintos capturan al visitante
al mismo tiempo** y las 3 siluetas se componen en una sola imagen.

| Cámara | Ángulo | Color | Referencia de Picasso | Lo que captura |
|--------|--------|-------|----------------------|----------------|
| A — OAK-D Pro W | Frontal | Azul | Les Bleus de Barcelona | Como nos vemos en un espejo |
| B — Logitech C922 | Lateral derecho | Ocre | Bailarines sobre cuero | La dimensión que el espejo nunca muestra |
| C — Logitech C922 | Cenital (desde arriba) | Rosa | Geneviève sobre papel Japón | La vista que nunca tenemos de nuestro propio cuerpo |

**El principio del Screen blend:**
- Una silueta sola → su color puro (azul, ocre, o rosa)
- Dos siluetas superpuestas → mezcla Screen de 2 colores (azul + ocre = verde-amarillo)
- Las 3 siluetas superpuestas → **luz blanca brillante**

Donde las 3 perspectivas coinciden es donde Picasso tenía la "certeza máxima" —
el punto del objeto que existe sin importar desde dónde lo mires. El sistema lo
marca con luz blanca.

**Por qué Screen blend y no Additive:**
Screen blend: `resultado = 1 - (1-A)(1-B)(1-C)`
Con Add puro: `resultado = A + B + C` → se satura a blanco rápidamente con valores bajos
Con Screen: los colores oscuros apenas se afectan entre sí; solo los valores altos
(siluetas sólidas) producen la mezcla visible. Esto hace que el fondo negro permanezca
negro aunque las 3 cámaras lo estén capturando.

**Flujo temporal de la experiencia:**
1. Sin visitante: tres halos de color pulsantes en el piso señalan las posiciones de las 3 cámaras
2. El visitante entra al espacio de la cámara A: aparece su silueta azul
3. El visitante se mueve para que la cámara B también lo vea: azul + ocre = mezcla verde-amarillo
4. El visitante está en el centro donde las 3 cámaras se solapan: aparece el blanco brillante
5. El visitante sale: las siluetas desaparecen, quedan las partículas y la estela
6. De vuelta a los halos pulsantes de reposo

---

## Antes de abrir TouchDesigner

### Una sola máquina — Mac M3 Max (obligatorio)

Este proyecto NO puede correr en ningún otro hardware. Los requisitos son:
- **3 puertos Thunderbolt 4 libres**: un puerto dedicado por cámara
- **Neural Engine de 16 núcleos**: para correr 3 instancias de MediaPipe simultáneamente
- **GPU Metal de 40 núcleos**: para renderizar en TouchDesigner sin competencia con Python
- **36 GB RAM unificada**: Python + MediaPipe×3 + TD sin thrashing

Un hub USB compartido DESTRUYE la sincronización de frames. Cada cámara en su propio puerto TB4:

| Puerto TB4 | Cámara | Rol |
|-----------|--------|-----|
| TB4 #1 | OAK-D Pro W | Frontal — usa DepthAI SDK, no OpenCV directamente |
| TB4 #2 | Logitech C922 | Lateral derecho |
| TB4 #3 | Logitech C922 | Cenital |

### En Python — hacer PRIMERO, antes de abrir TD

```bash
# 1. Verificar Python 3.11 o 3.12
python3 --version   # debe ser 3.11.x o 3.12.x

# 2. Activar entorno
source venv/bin/activate

# 3. Verificar que DepthAI detecta la OAK-D Pro W (CRÍTICO para cámara A)
python3 -c "import depthai as dai; devs = dai.Device.getAllAvailableDevices(); print(f'{len(devs)} dispositivos OAK-D:', devs)"
# Debe mostrar: 1 dispositivos OAK-D: [<DeviceInfo ...>]
# Si muestra 0: la cámara OAK-D no está en el TB4 correcto o el SDK no está instalado

# 4. Verificar los índices de las Logitech C922 (pueden variar según el orden de conexión)
python3 -c "import cv2; [print(f'Cam {i}: {cv2.VideoCapture(i).isOpened()}') for i in range(6)]"
# Anotar qué índices (1, 2, 3...) corresponden a las C922

# 5. Editar config.py con los índices reales
#    CAM_B_INDEX = <índice C922 lateral>
#    CAM_C_INDEX = <índice C922 cenital>
#    OSC_HOST = "127.0.0.1"  (TD en el mismo Mac)

# 6. Terminal A — MCP bridge (opcional)
python mcp_bridge.py

# 7. Terminal B — Pipeline (con preview para verificar sincronización)
python multicam_runtime.py --preview
```

Verificar en el log que la sincronización es correcta:
```
[      ] 29.8fps | sync= 18ms (97% OK) | A=0.21 B=0.18 C=0.14 | triple=0.0012
[TRIPLE] 29.7fps | sync= 22ms (94% OK) | A=0.82 B=0.71 C=0.65 | triple=0.0412
```
- `sync= 18ms`: diferencia entre el frame más antiguo y el más nuevo en el triplete.
  Debe ser < 33ms (1 frame a 30fps). Si es mayor, un hub USB está compartiendo bandwidth.
- `97% OK`: porcentaje de triplicaciones en que los 3 frames cayeron dentro de la ventana de sync.
  Debe ser > 90% para que el efecto de coincidencia sea coherente.
- `A=0.82`: `flow_mean` de la cámara A. Muestra cuánto movimiento hay en cada perspectiva.
- `triple=0.0412`: fracción de píxeles donde las 3 siluetas se solapan. >0.04 dispara el tag `[TRIPLE]`.

---

## Abrir TouchDesigner

1. Abrir TouchDesigner en el Mac M3 Max (mismo Mac donde corre Python)
2. **File → New** → proyecto en blanco
3. Guardar como: `P3_JIFREX_MultiCamara.toe` en el directorio del proyecto

---

## Paso 1 — Crear el OSC In DAT

**Qué recibe:** 12 canales OSC que incluyen métricas individuales por cámara
(flow, motion, presence de A, B y C) más métricas globales (triple_ratio,
double_ratio, any_presence). Esto permite que los shaders reaccionen a la dinámica
de cada perspectiva individualmente.

1. Click derecho → **DAT** → `OSC In`
2. Renombrar: `osc_in`
3. Parámetros:
   - **Protocol**: UDP
   - **Port**: `9000`
   - **Local Address**: dejar vacío
   - **Active**: ON
4. **Verificar:** tabla muestra `/multicam/triple_ratio`, `/multicam/a/flow_mean`,
   `/multicam/b/presence`, etc.

---

## Paso 2 — Crear el Script DAT

**Qué hace:** distribuye los 12 canales OSC a los uniforms de los 5 GLSL TOPs.
Los tres `glsl_distort_*` reciben el `flow_mean` de su cámara respectiva.
El `glsl_composite` recibe los flujos de las 3 cámaras y el triple_ratio.
El `glsl_particles` recibe todos los uniforms necesarios para diferenciarse por perspectiva.

1. Click derecho → **DAT** → `Script`
2. Renombrar: `osc_to_uniforms`
3. Conectar: salida de `osc_in` → entrada de `osc_to_uniforms`
4. **Execute**: `Table Change`
5. Abrir editor → pegar contenido de `shaders/td_osc_to_uniforms.py` → cerrar

---

## Paso 3 — Crear las 3 entradas Syphon

**Qué son:** Python emite 3 servidores Syphon simultáneos — uno por cámara.
Cada uno contiene la máscara binaria (silueta blanca sobre negro) desde esa perspectiva.

**Importante:** los 3 servidores Syphon corren desde el mismo proceso Python.
En TD, los 3 `Syphon Spout In` TOP deben apuntar a la misma Application pero a
distintos Server Names.

### Cámara A — Frontal (azul en el composite)
1. Click derecho → **TOP** → `Syphon Spout In`
2. Renombrar: `syphon_in_a`
3. Parámetros:
   - **Application**: seleccionar la app Python de la lista
   - **Server Name**: `JIFREX-CAM-A-FRONTAL`
4. **Verificar:** silueta del visitante desde el frente, en blanco sobre negro.
   La silueta debe ser limpia, sin demasiado ruido de fondo.

### Cámara B — Lateral derecha (ocre en el composite)
1. Click derecho → **TOP** → `Syphon Spout In`
2. Renombrar: `syphon_in_b`
3. Parámetros:
   - **Application**: misma app Python que en A
   - **Server Name**: `JIFREX-CAM-B-LATERAL`
4. **Verificar:** silueta desde el lateral derecho. La silueta se verá más delgada
   que la frontal (proyección lateral del cuerpo).

### Cámara C — Cenital (rosa en el composite)
1. Click derecho → **TOP** → `Syphon Spout In`
2. Renombrar: `syphon_in_c`
3. Parámetros:
   - **Application**: misma app Python que en A
   - **Server Name**: `JIFREX-CAM-C-CENITAL`
4. **Verificar:** silueta desde arriba. Deberías ver la "huella" del cuerpo —
   hombros anchos, cabeza en el centro, pies en la parte inferior de la imagen.

**Si alguno aparece negro:**
- Verificar que `syphon-python` está instalado en el venv: `pip install syphon-python`
- Verificar que Python está corriendo con `SHARE_ENABLE = True` en `config.py`
- Verificar que los nombres coinciden exactamente con `SYPHON_SERVER_A/B/C` en `config.py`

---

## Paso 4 — Crear los 3 GLSL TOP de distorsión UV

**Qué hacen:** cada perspectiva tiene su propia deformación geométrica que refleja
la naturaleza de ese ángulo de visión. La distorsión es proporcional al movimiento
(`uFlowMean`) — cuando el visitante está quieto, la distorsión es casi imperceptible;
cuando se mueve, la perspectiva "se deforma" ligeramente.

**El uniform `uPerspective` es FIJO — no viene de OSC:**
- `0.0` → frontal: deformación radial (como un espejo levemente curvado)
- `1.0` → lateral: deformación horizontal (simula la perspectiva del eje Z)
- `2.0` → cenital: rotación suave alrededor del centro (huella en espiral)

Los 3 usan el **mismo archivo GLSL** (`distorsion_uv.glsl`) pero con `uPerspective`
diferente — un solo shader con 3 comportamientos selectivos via un `if` en el código.

### glsl_distort_a — frontal (deformación radial)

**Qué verás:** la silueta frontal azul se "ondula" ligeramente hacia afuera desde
el centro cuando hay movimiento — como si el espejo de frente estuviera hecho de agua.

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_distort_a`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `syphon_in_a`
4. Parámetros:
   - **Pixel Shader File**: `shaders/distorsion_uv.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Uniform Name | Valor | Qué controla |
   |------|-------------|-------|--------------|
   | `uniform0` | `uPerspective` | **`0.0`** (FIJO, no cambia) | Selecciona el tipo de distorsión: 0 = radial |
   | `uniform1` | `uFlowMean` | `0` (actualizado por OSC) | Intensidad de la distorsión. Flow alto = más ondulación |
   | `uniform2` | `uTime` | `0` (actualizado por OSC) | Animación temporal de la distorsión |

### glsl_distort_b — lateral (deformación horizontal)

**Qué verás:** la silueta lateral ocre se "encoge" y "estira" horizontalmente con
el movimiento — simulando cómo la profundidad del cuerpo se proyecta en la vista lateral.

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_distort_b`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `syphon_in_b`
4. Mismo shader: `shaders/distorsion_uv.glsl`
5. Uniforms:
   - `uPerspective` → **`1.0`** (FIJO)
   - `uFlowMean` → `0`
   - `uTime` → `0`

### glsl_distort_c — cenital (rotación)

**Qué verás:** la silueta cenital rosa rota ligeramente alrededor del centro con el
movimiento — como una huella en el suelo que gira mientras el cuerpo se mueve arriba.

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_distort_c`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `syphon_in_c`
4. Mismo shader: `shaders/distorsion_uv.glsl`
5. Uniforms:
   - `uPerspective` → **`2.0`** (FIJO)
   - `uFlowMean` → `0`
   - `uTime` → `0`

---

## Paso 5 — Crear el GLSL TOP: glsl_composite

**Este es el shader principal de P3 — el que implementa el cubismo simultáneo.**
Recibe las 3 siluetas distorsionadas y las compone con Screen blend, produciendo:
- Silueta sola: su color puro
- Dos siluetas superpuestas: mezcla de 2 colores
- Tres siluetas superpuestas: luz blanca brillante

**Qué deberías ver:**
- Sin visitante: 3 halos pulsantes de color (azul/ocre/rosa) en las posiciones
  de las 3 cámaras (estado de "invitación" — la sala llama al visitante)
- Un visitante en el área A: silueta azul sola
- Un visitante visible en A y B: silueta verde-amarillo (Screen de azul+ocre)
- Un visitante en el cruce de las 3 perspectivas: explosión de luz blanca

**CRÍTICO — Input Count:** este GLSL TOP recibe 3 inputs, no 1. Si Input Count es 1,
solo verás la cámara A y las otras 2 serán ignoradas.

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_composite`  ← **nombre exacto**
3. Conectar:
   - Entrada [0]: cable de `glsl_distort_a` (frontal — azul)
   - Entrada [1]: cable de `glsl_distort_b` (lateral — ocre)
   - Entrada [2]: cable de `glsl_distort_c` (cenital — rosa)
4. En la pestaña **Common** → **Input Count**: `3`
5. Parámetros:
   - **Pixel Shader File**: `shaders/composite_multicamara.glsl`
   - **File Active**: ON
6. Uniforms (Vectors 1):

   | Slot | Uniform Name | Rango | Qué controla |
   |------|-------------|-------|--------------|
   | `uniform0` | `uFlowA` | 0.0–3.0 | Flow de cámara A. Escala la saturación del azul frontal |
   | `uniform1` | `uFlowB` | 0.0–3.0 | Flow de cámara B. Escala la saturación del ocre lateral |
   | `uniform2` | `uFlowC` | 0.0–3.0 | Flow de cámara C. Escala la saturación del rosa cenital |
   | `uniform3` | `uTripleRatio` | 0.0–1.0 | Fracción de píxeles con triple coincidencia. Refuerza el brillo blanco |
   | `uniform4` | `uAnyPresence` | 0 ó 1 | Si hay alguien en alguna cámara. 0 = modo halos de reposo |
   | `uniform5` | `uTime` | segundos | Para animar los halos de reposo y la modulación |

   **Cómo funciona el Screen blend en el shader:**
   ```glsl
   vec3 result = 1.0 - (1.0 - col_a) * (1.0 - col_b) * (1.0 - col_c);
   ```
   - Si col_a=0, col_b=0, col_c=0 → result = 1 - 1×1×1 = 0 (negro)
   - Si col_a=0.09,0.35,0.95 y los demás son 0 → result = azul solo
   - Si col_a y col_b tienen valores → Screen blend produce mezcla intermedia
   - Si los 3 son altos → result se acerca a vec3(1,1,1) (blanco brillante)

---

## Paso 6 — Crear la máscara compuesta para partículas

**Por qué:** el shader de partículas necesita saber dónde están los bordes de las 3
siluetas combinadas para que las partículas nazcan en los bordes reales del cuerpo.
Si usáramos solo una cámara, las partículas saldrían solo del contorno frontal.
Con la máscara compuesta, las partículas salen del contorno desde todas las perspectivas.

**Maximum vs Average:** usamos `Maximum` porque queremos que cualquier silueta activa
contribuya al borde. Con `Average`, las siluetas de cámaras con poca señal "diluirían"
las siluetas fuertes. Con `Maximum`, si cualquier cámara ve un borde, ese borde existe.

1. Click derecho → **TOP** → `Composite`
2. Renombrar: `mask_composite`
3. Conectar:
   - Agregar `syphon_in_a`, `syphon_in_b`, `syphon_in_c` como entradas
     (click derecho en el operador → Add Input → repetir para las 3)
4. Parámetros:
   - **Operation**: `Maximum` (`max(a, b, c)` para cada canal)

---

## Paso 7 — Crear el Feedback TOP

**Por qué la estela es más larga en triple coincidencia:**
En el shader de partículas, el decay es variable:
- Presencia normal: `decay = 0.94` (estela de ~1.5 s)
- Triple coincidencia: `decay = 0.97` (estela de ~3 s)

El punto donde Picasso tenía la "certeza máxima" deja una huella más larga en el espacio.

1. Click derecho → **TOP** → `Feedback`
2. Renombrar: `feedback_loop`
3. Parámetros:
   - **Target TOP**: `glsl_particles` (se completará en el paso siguiente)
   - **Opacity**: `0.90`
     (0.90 es el punto de partida — calibrar en sala según la luz ambiental)

---

## Paso 8 — Crear el GLSL TOP: glsl_particles

**Las partículas tienen 3 comportamientos distintos según la perspectiva activa:**
- Perspectiva frontal (uPerspective=0): **expansión radial** — el cuerpo "irradia" energía
  hacia afuera en todas las direcciones (como la proyección de la energía corporal)
- Perspectiva lateral (uPerspective=1): **traslación horizontal** — las partículas se
  desplazan de izquierda a derecha (simulan la dimensión que la cámara lateral captura)
- Perspectiva cenital (uPerspective=2): **espiral** — las partículas rotan hacia afuera
  (desde arriba, el movimiento parece un torbellino)

**En triple coincidencia, las partículas de las 3 perspectivas se vuelven blancas** —
el mismo color de la luz blanca del composite, reforzando visualmente el momento
de máxima certeza cubista.

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_particles`  ← **nombre exacto**
3. Conectar:
   - Entrada [0]: cable de `glsl_composite` (frame actual)
   - Entrada [1]: cable de `feedback_loop` (frame anterior — estela)
   - Entrada [2]: cable de `mask_composite` (bordes combinados de las 3 cámaras)
4. En la pestaña **Common** → **Input Count**: `3`
5. Parámetros:
   - **Pixel Shader File**: `shaders/particulas_perspectiva.glsl`
   - **File Active**: ON
6. Uniforms (Vectors 1):

   | Slot | Uniform Name | Valor inicial | Qué controla |
   |------|-------------|--------------|--------------|
   | `uniform0` | `uPerspective` | `0` | Comportamiento de partículas: 0=radial, 1=horizontal, 2=espiral |
   | `uniform1` | `uFlowA` | `0` | Flow cámara A (frontal) |
   | `uniform2` | `uFlowB` | `0` | Flow cámara B (lateral) |
   | `uniform3` | `uFlowC` | `0` | Flow cámara C (cenital) |
   | `uniform4` | `uMotionA` | `0` | Motion ratio cámara A — densidad de partículas A |
   | `uniform5` | `uMotionB` | `0` | Motion ratio cámara B |
   | `uniform6` | `uMotionC` | `0` | Motion ratio cámara C |
   | `uniform7` | `uTripleRatio` | `0` | Triple coincidencia — hace partículas blancas y estela más larga |
   | `uniform8` | `uAnyPresence` | `0` | Si hay visitante — controla el decay |
   | `uniform9` | `uTime` | `0` | Tiempo para la animación |

   **Nota sobre `uPerspective`:** este uniform puede quedar en 0 si solo se quiere
   el comportamiento frontal (radial) para todas las perspectivas. Para una experiencia
   completa, el Script DAT puede actualizarlo dinámicamente según qué cámara tiene
   más movimiento (`max(flowA, flowB, flowC)` → perspectiva dominante).

7. Volver a `feedback_loop` → **Target TOP**: `glsl_particles` → loop cerrado

---

## Paso 9 — Level TOP y Out TOP

1. Click derecho → **TOP** → `Level`
   - Renombrar: `level_final`
   - Conectar: cable de `glsl_particles` → entrada de `level_final`
   - **Brightness**: `1.0` (ajustar en sala — si el blanco del triple es demasiado
     cegador, bajar a 0.90)
   - **Contrast**: `1.05`

2. Click derecho → **TOP** → `Out`
   - Renombrar: `out_proyector`
   - Conectar: cable de `level_final` → entrada de `out_proyector`
   - **Dialogs → Window Placement** → seleccionar los 2 proyectores Epson
   - **Resolution**: `1920 × 1200` (WUXGA nativo del Epson 5510)

---

## Diagrama completo de conexiones

```
[Python multicam_runtime.py — Mac M3 Max]
    │ Syphon A (~1ms)   │ Syphon B (~1ms)   │ Syphon C (~1ms)   │ OSC :9000 (loopback)
    ▼                   ▼                   ▼                   ▼
[syphon_in_a]       [syphon_in_b]       [syphon_in_c]       [osc_in: OSC In DAT]
 silueta frontal     silueta lateral     silueta cenital          │
    │                   │                   │              [osc_to_uniforms: Script DAT]
    ▼                   ▼                   ▼                   │ actualiza 5 GLSL TOPs
[glsl_distort_a]   [glsl_distort_b]   [glsl_distort_c]         │
uPerspective=0.0   uPerspective=1.0   uPerspective=2.0         │
radial             horizontal         rotación/espiral          │
    │                   │                   │                   │
    └───────────────────┴───────────────────┘                   │
                        │ 3 entradas [0][1][2]                  │
                        ▼                                       │
                [glsl_composite]  ←─────────── uFlowA/B/C, uTripleRatio,
                        │                      uAnyPresence, uTime
                        │   qué ves: Screen blend 3 siluetas
                        │            solo → color puro
                        │            doble → mezcla de colores
                        │            triple → LUZ BLANCA BRILLANTE
                        │
               [mask_composite: Composite TOP]  ← syphon_in_a,b,c (Operation: Maximum)
                        │  máscara unificada de las 3 cámaras
                        │
                        ▼ input[0]
                [glsl_particles] ← input[1]: feedback_loop
                        │          ← input[2]: mask_composite
                        │           uPerspective, uFlowA/B/C, uMotionA/B/C,
                        │           uTripleRatio, uAnyPresence, uTime
                        │
                [feedback_loop: Feedback TOP]  Opacity: 0.90
                └──→ Target TOP = glsl_particles  (loop cerrado)
                        │
                [level_final: Level TOP]  Brightness: 1.0
                        │
                [out_proyector: Out TOP]
                        │
              2× Epson PowerLite 5510 via HDBaseT Cat6A
              Techo 4.5 m · WUXGA 1920×1200 · 5500 lm
```

---

## Nombres de operadores — tabla crítica

| Operador | Tipo | Nombre exacto | Verificar |
|----------|------|--------------|-----------|
| OSC In DAT | DAT | `osc_in` | Tabla con `/multicam/...` |
| Script DAT | DAT | `osc_to_uniforms` | Sin errores en consola TD |
| Syphon frontal | TOP | `syphon_in_a` | Silueta frontal visible (blanco/negro) |
| Syphon lateral | TOP | `syphon_in_b` | Silueta lateral visible |
| Syphon cenital | TOP | `syphon_in_c` | Silueta cenital visible |
| GLSL distorsión A | TOP | **`glsl_distort_a`** | uPerspective=0.0 fijo |
| GLSL distorsión B | TOP | **`glsl_distort_b`** | uPerspective=1.0 fijo |
| GLSL distorsión C | TOP | **`glsl_distort_c`** | uPerspective=2.0 fijo |
| Composite TOP | TOP | `mask_composite` | Operation: Maximum |
| GLSL composite | TOP | **`glsl_composite`** | Input Count=3, 6 uniforms |
| GLSL partículas | TOP | **`glsl_particles`** | Input Count=3, 10 uniforms |
| Feedback TOP | TOP | `feedback_loop` | Target=glsl_particles, Opacity=0.90 |
| Level TOP | TOP | `level_final` | Brightness=1.0 |
| Out TOP | TOP | `out_proyector` | Pantalla correcta |

---

## Verificación del efecto cubista

Esta secuencia permite verificar que el Screen blend funciona correctamente:

1. **Sin visitante:** deben aparecer 3 halos pulsantes de color (azul/ocre/rosa)
   en el frame. Si no aparecen: verificar `uAnyPresence = 0` en `glsl_composite`
   cuando Python no detecta presencia.

2. **Un visitante frente a cámara A solamente:** silueta azul pura. Si se ve de otro
   color, verificar que `syphon_in_b` y `syphon_in_c` están completamente en negro.

3. **Mismo visitante en campo visual de A y B simultáneamente:** la superposición
   debe producir un color intermedio verde-amarillo-dorado (Screen blend de azul+ocre).
   Si se ve simplemente aditivo (demasiado brillante), verificar que el shader usa
   Screen blend (`1 - (1-A)(1-B)`) y no Add.

4. **Visitante en el cruce de las 3 perspectivas:** debe aparecer **luz blanca brillante**.
   Si no aparece: verificar que las 3 máscaras se solapan en la imagen compuesta
   (ajustar posiciones de cámaras en sala hasta que haya overlap real en el espacio).

5. **Log de Python debe mostrar `[TRIPLE]`** cuando el visitante está en el cruce.
   Si nunca aparece: ajustar `TRIPLE_THRESHOLD` a un valor menor (default 0.04 = 4%
   de los píxeles) via `/mcp/set/triple_threshold 0.02`.

---

## Calibración en sala — halos de reposo

Los halos de reposo (estado sin visitante) tienen posiciones hardcodeadas en el
shader (`halo_a = vec2(0.28, 0.50)`, etc.). Estas posiciones asumen que las
cámaras apuntan a zonas horizontalmente distribuidas en el frame.

Si la geometría de la sala es diferente (por ejemplo, las cámaras apuntan a zonas
distintas), editar las posiciones directamente en `composite_multicamara.glsl`:

```glsl
// Ajustar estas coordenadas UV según la posición real de cada perspectiva:
vec2 halo_a = vec2(0.28, 0.50);   // izquierda — zona de la cámara frontal
vec2 halo_b = vec2(0.50, 0.50);   // centro    — zona de la cámara lateral
vec2 halo_c = vec2(0.72, 0.50);   // derecha   — zona de la cámara cenital
```

Con `File Active: ON`, los halos se actualizan al guardar el `.glsl` — sin reiniciar TD.

---

## Lista de verificación antes de la inauguración

- [ ] OAK-D Pro W detectada por DepthAI (`getAllAvailableDevices()` muestra 1 dispositivo)
- [ ] `sync_delta` en log < 33ms constantemente (verificar durante 30 min continuos)
- [ ] Las 3 entradas Syphon muestran imagen (no negro)
- [ ] Un visitante en A: silueta azul
- [ ] Un visitante en A+B: mezcla Screen azul+ocre
- [ ] Un visitante en A+B+C: luz blanca brillante + tag `[TRIPLE]` en log
- [ ] Halos de reposo (azul/ocre/rosa) visibles cuando no hay visitante
- [ ] `glsl_particles`: partículas con comportamiento visual distinto por perspectiva
- [ ] `feedback_loop`: estela persiste ~2 s normal, ~3 s en triple coincidencia
- [ ] Proyectores: keystone y posición correctas en el piso
- [ ] Prueba de 8 horas continuas — monitorear temperatura M3 Max y fps

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| Syphon en negro | Python no emite | Verificar `syphon-python` instalado y runtime corriendo con `--preview` para confirmar que las 3 cámaras tienen imagen |
| `sync_delta` > 33ms permanentemente | Hub USB compartido | Conectar cada cámara a su propio puerto TB4 directamente — no hay alternativa |
| Sin luz blanca en triple | Máscaras no se solapan en UV | Ajustar posiciones físicas de las 3 cámaras hasta que los 3 ángulos cubran el mismo espacio |
| `glsl_composite` negro | Input Count incorrecto | GLSL TOP → pestaña Common → **Input Count = 3** |
| `glsl_particles` negro | Input Count o Feedback no cerrado | Input Count = 3; verificar Target TOP = `glsl_particles` en Feedback TOP |
| Halos de reposo no aparecen | `uAnyPresence` siempre 1 | Python detecta "presencia" sin nadie — subir `MASK_THRESHOLD` en `config.py` |
| Partículas solo radiales | `uPerspective` siempre 0 | El Script DAT no actualiza este uniform — revisar que las líneas de `glsl_particles` están en `td_osc_to_uniforms.py` |
| OSC sin datos | config.py IP incorrecta | Verificar `OSC_HOST = "127.0.0.1"` (misma máquina) |
