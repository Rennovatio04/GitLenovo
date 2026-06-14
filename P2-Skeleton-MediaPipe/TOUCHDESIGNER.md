# TouchDesigner — Guía de Operación Completa
## P2 · Skeleton Semántico MediaPipe · Aún Sorprendo · JIFREX

> **Para el operador técnico:** esta guía asume que sabes moverte en TouchDesigner
> pero nunca has visto este proyecto. Deberías poder montar el patch completo en
> 2.5 horas siguiendo estos pasos en orden. P2 es el más complejo de los 4
> proyectos — 5 GLSL TOPs, 2 CHOPs adicionales, y 6 triggers semánticos diferentes.

---

## Concepto artístico — qué estamos construyendo

P2 no detecta solo SI hay alguien — detecta **qué parte del cuerpo se mueve**.
MediaPipe Holistic extrae 17 joints semánticos del cuerpo: hombros, codos, muñecas,
caderas, rodillas, nariz, orejas. Cada parte del cuerpo que se activa dispara una
respuesta visual diferente.

El visitante no "activa" la instalación — **conversa con ella**.
Cada gesto tiene su propia voz visual:

| Gesto | Lo que ves en la proyección |
|-------|---------------------------|
| Levantar la mano | Planos geométricos azul-blanco (cubismo fragmentado) brotan de la palma |
| Girar la cadera | Estelas circulares naranjas que giran al ritmo de la rotación |
| Inclinar la cabeza | La temperatura de color de TODA la sala cambia (frío/cálido) |
| Saltar o gesticular explosivamente | Glitch digital total con partículas voladoras |
| Quedarse quieto > 3 s | Todo se desvanece gradualmente hasta el negro |
| Dos personas simultáneas | El espacio entre los cuerpos se fragmenta en diálogo cubista |

**Referencia artística:** los "Bailarines" de Picasso de los años 40-50, donde el
movimiento del cuerpo fragmenta el espacio en planos simultáneos. P2 hace esto
en tiempo real: la parte del cuerpo que se mueve "fragmenta" el espacio a su alrededor.

**Flujo temporal completo:**
1. El visitante entra — el overlay del esqueleto aparece en el frame Syphon
2. Primera mano levantada — planos azules cubistas emergen desde la posición de la mano
3. El visitante gira la cadera — los planos se disuelven y aparecen estelas naranjas circulares
4. El visitante inclina la cabeza — la paleta de color completa del frame se transforma
5. Un salto — glitch máximo con partículas en todo el frame durante ~0.5 s
6. Dos personas — el espacio entre ellas se convierte en un diálogo de planos fracturados
7. Quietud > 3 s — todo hace fade a negro lentamente (Trigger 5)
8. Un nuevo movimiento — el ciclo vuelve a empezar desde el gesto activo

---

## Antes de abrir TouchDesigner

### Una sola máquina — Python y TD en la misma máquina

P2 corre en una **sola máquina**: Python y TouchDesigner en el mismo equipo.
La textura del esqueleto viaja por Syphon (macOS) o Spout (Windows) — sin red,
directo entre procesos en la GPU, latencia ~1 ms.

| Plataforma | Textura | OSC |
|-----------|---------|-----|
| macOS (Mac M3 Max) — **recomendado** | **Syphon** (`syphon-python`) | UDP loopback `127.0.0.1:9000` |
| Windows (MSI) | **Spout** (`SpoutGL`) | UDP loopback `127.0.0.1:9000` |

### En Python — hacer PRIMERO, antes de abrir TD

```bash
# 1. Verificar Python 3.11 o 3.12 (OBLIGATORIO — MediaPipe no existe para 3.13+)
python3 --version   # debe mostrar 3.11.x o 3.12.x

# 2. Activar entorno
source venv/bin/activate          # macOS
.\venv\Scripts\Activate.ps1      # Windows

# 3. Verificar la configuración (editar si necesario)
#    OSC_HOST = "127.0.0.1"   ← correcto si TD corre en la misma máquina
#    CAM_INDEX = 0             ← verificar que es el índice correcto de la webcam
#    SHARE_ENABLE = True       ← para que el overlay llegue a TD por Syphon/Spout

# 4. Terminal A — MCP bridge (opcional pero útil para calibración en sala)
#    Dejar corriendo en esta terminal
python mcp_bridge.py

# 5. Terminal B — Pipeline principal (en OTRA terminal)
python skeleton_runtime.py
```

El log debe aparecer en los primeros segundos:
```
[          ----] 29.8 fps | blob=1 | flow=0.42 | motion=0.31 | hip_v= 2.1° | head_roll= -4.3° | static=0.0s
```
Campos del log:
- `zona_hands` / `zona_torso` / `zona_head` / `global` / `----`: qué trigger está activo
- `blob`: número de personas detectadas (1 o 2)
- `flow`: magnitud del optical flow global
- `hip_v`: velocidad angular de la cadera en grados/frame
- `head_roll`: inclinación lateral de la cabeza en grados
- `static`: segundos de quietud acumulada (al llegar a 3s dispara el Trigger 5)

Si el log muestra `SIMULACIÓN`: MediaPipe o la webcam no están disponibles.
El sistema sigue funcionando con datos sintéticos — útil para verificar los shaders.

---

## Abrir TouchDesigner

1. **Misma máquina** donde corre Python (crítico para Syphon/Spout)
2. Menú **File → New** → proyecto en blanco
3. Guardar como: `P2_JIFREX_Skeleton.toe` en el directorio del proyecto

---

## Paso 1 — Crear el OSC In DAT

**Qué hace:** recibe las 8+ rutas semánticas desde Python — no solo números planos
sino información sobre QUÉ parte del cuerpo se mueve, a qué ángulo, con qué velocidad.
Por ejemplo: `/cuerpo/cadera` lleva el trigger (0/1) + el ángulo en grados + la velocidad
angular — tres valores en un mismo mensaje.

1. Click derecho → **DAT** → `OSC In`
2. Renombrar: `osc_in`
3. Parámetros:
   - **Protocol**: UDP
   - **Port**: `9000`
   - **Local Address**: dejar vacío (escucha en todas las interfaces — loopback incluido)
   - **Active**: ON
4. **Verificar:** la tabla debe mostrar rutas como `/cuerpo/trigger_zona`, `/cuerpo/metrica/flow_mean`,
   `/cuerpo/cadera`, etc. Si la tabla está vacía y Python está corriendo, verificar que
   `OSC_HOST = "127.0.0.1"` en `config.py` (misma máquina).

---

## Paso 2 — Crear el Script DAT

**Qué hace:** lee la tabla OSC y distribuye cada valor al uniform correcto de cada GLSL TOP.
El script sabe que `/cuerpo/mano_derecha[0]` va a `glsl_hands.uHandTrigger`,
que `/cuerpo/cadera[1]` va a `glsl_torso.uHipAngle`, etc.

**Por qué esto es complejo:** a diferencia de P1 (un mensaje → un uniform), P2 envía
mensajes con múltiples valores (`/cuerpo/cadera` lleva trigger, ángulo y velocidad juntos).
El Script DAT desempaqueta estos arrays y los distribuye a los uniforms correspondientes.

1. Click derecho → **DAT** → `Script`
2. Renombrar: `osc_to_uniforms`
3. Conectar: salida de `osc_in` → entrada de `osc_to_uniforms`
4. Parámetros:
   - **Execute**: `Table Change`
5. Abrir editor → pegar contenido de `shaders/td_osc_to_uniforms.py` → cerrar
6. **Verificar:** sin errores en el Textport de TD. Si aparece `op('glsl_hands') not found`,
   el nombre del GLSL TOP no coincide exactamente (son case-sensitive).

---

## Paso 3 — Crear la entrada de video (Spout/Syphon)

**Qué es este video:** el overlay del esqueleto que Python dibuja — líneas de hueso
sobre un fondo oscuro, con la máscara de persona como tinte azul tenue. Este es el
"lienzo" sobre el que los shaders de zona dibujan sus efectos.

**Por qué no una cámara directa:** los shaders necesitan saber dónde están los huesos
para poder dibujar los efectos en las posiciones correctas del cuerpo. Python dibuja
los huesos explícitamente y los comparte como textura lista para los shaders.

### En macOS (Syphon) — caso principal
1. Click derecho → **TOP** → `Syphon Spout In`
2. Renombrar: `skeleton_in`
3. Parámetros:
   - **Application**: seleccionar la app Python de la lista desplegable
     (generalmente aparece como `python3.11` o `python3.12`)
   - **Server Name**: `JIFREX-P2-SKELETON`
     *(debe coincidir EXACTAMENTE con `SHARE_SENDER_NAME` en `config.py`)*

### En Windows (Spout)
1. Click derecho → **TOP** → `Spout In`
2. Renombrar: `skeleton_in`
3. Parámetros:
   - **Source Name**: `JIFREX-P2-SKELETON`

**Verificar:** el TOP muestra el overlay del esqueleto sobre fondo oscuro.
Deberías ver líneas blancas conectando las articulaciones y nodos en cada joint.
Si aparece negro: Python no está enviando el share. Verificar:
- `SHARE_ENABLE = True` en `config.py`
- `pip install syphon-python` (macOS) o `pip install SpoutGL` (Windows) en el venv activo
- En Python, el log debe mostrar `[SHARE] backend = syphon · fuente = 'JIFREX-P2-SKELETON'`

---

## Paso 4 — Crear GLSL TOP: glsl_hands

**Concepto:** cuando el visitante levanta la mano, el sistema responde con planos
geométricos fragmentados que brotan desde la posición de la palma. La densidad de
los planos crece con la altura de la muñeca — cuanto más alto levanta la mano,
más planos aparecen. Las líneas de fractura entre planos son las "aristas cubistas"
— exactamente como Picasso fragmentaba los objetos en planos adyacentes.

**Paleta:** azul fría (referencia directa a la "Época Azul" / Les Bleus de Barcelona).
El azul contrasta con el naranja del torso y el gris neutro del sistema en reposo.

**Qué deberías ver:**
- Sin trigger: el frame pasa sin cambios (pass-through)
- Mano levantada al nivel del hombro: planos azules tenues cubren el frame
- Mano bien alta (por encima de la cabeza): planos densos azul-blanco intenso,
  con líneas de fractura blancas brillantes entre ellos
- Los planos "brotan" desde la altura de la muñeca hacia arriba — hay un gradiente
  de densidad que va de 0 (abajo) a 1 (a la altura de la mano)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_hands`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `skeleton_in`
4. Parámetros:
   - **Pixel Shader File**: `shaders/zona_hands.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Uniform Name | Rango | Qué controla |
   |------|-------------|-------|--------------|
   | `uniform0` | `uHandTrigger` | 0 ó 1 | Activa/desactiva el efecto. 0 = pass-through |
   | `uniform1` | `uWristHeight` | 0.0–1.0 | Altura de la muñeca normalizada (0=abajo, 1=arriba). Controla la densidad y posición de los planos |
   | `uniform2` | `uArmOpenR` | 0.0–90.0 grados | Apertura del brazo. Escala la visibilidad de los planos (brazo más abierto = planos más visibles) |
   | `uniform3` | `uTime` | segundos | Animación lenta de los planos (respiración) |

   **Explicación de `uWristHeight`:** en MediaPipe, las coordenadas Y van de 0 (arriba)
   a 1 (abajo) — al revés de lo que intuitivamente esperaríamos. Python invierte esto
   antes de enviarlo, de modo que `uWristHeight = 1.0` significa "mano arriba" y
   `uWristHeight = 0.0` significa "mano abajo". En el shader, esto controla el gradiente
   que hace que los planos "broten" desde la posición de la mano hacia arriba.

---

## Paso 5 — Crear GLSL TOP: glsl_torso

**Concepto:** cuando el visitante gira la cadera, el sistema responde con estelas
circulares que giran exactamente al mismo ritmo. La velocidad de las estelas es
directamente proporcional a la velocidad angular de la cadera — si el visitante
gira lentamente, las estelas giran lentamente; si gira rápido, las estelas se disparan.

La paleta es naranja-ámbar, en contraste con el azul frío de las manos. En Picasso,
el torso y la cadera aparecen con colores terrosos en sus obras de los años 40-50
("Bailarín sobre cuero" — referencia explícita).

**Qué deberías ver:**
- Sin trigger: pass-through del frame anterior
- Cadera rotando: campo de anillos concéntricos naranja-ámbar alrededor del centro
  del frame, que giran en la misma dirección que la cadera
- Cuanto más rápido rota la cadera, más rápido giran los anillos y más saturados
  son los colores
- Los anillos se disuelven hacia los bordes (falloff radial)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_torso`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `glsl_hands`
   *(la cadena es lineal: cada shader recibe la salida del anterior)*
4. Parámetros:
   - **Pixel Shader File**: `shaders/zona_torso.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Uniform Name | Rango | Qué controla |
   |------|-------------|-------|--------------|
   | `uniform0` | `uHipTrigger` | 0 ó 1 | Activa el campo de estelas. 0 = pass-through |
   | `uniform1` | `uHipAngle` | -180° a 180° | Ángulo actual de la cadera (arctan2). Determina la dirección de giro de las estelas |
   | `uniform2` | `uHipVelocity` | grados/frame | Velocidad angular suavizada. Controla la velocidad de giro y el brillo de las estelas |
   | `uniform3` | `uTime` | segundos | Tiempo base para la animación de los anillos |

   **Explicación de `uHipAngle`:** Python calcula el ángulo de la cadera como
   `arctan2(hip_right.y - hip_left.y, hip_right.x - hip_left.x)` en cada frame.
   Cuando la cadera está horizontal, el ángulo es 0. Al rotar, el ángulo cambia.
   En el shader, el SIGNO del ángulo determina si las estelas giran en sentido
   horario o antihorario — el sistema "sigue" físicamente la rotación del visitante.

---

## Paso 6 — Crear GLSL TOP: glsl_head

**Concepto:** la cabeza controla la "temperatura emocional" de TODA la composición.
Inclinar la cabeza a un lado hace la sala más fría (azul); al otro lado, más cálida
(ámbar). Mirar arriba/abajo cambia el brillo y la saturación. Es la respuesta más
íntima del sistema — el visitante literalmente "colorea el espacio" con su postura.

Esta es la respuesta más sutil y la que tarda más en descubrir — muchos visitantes
la descubren por accidente al inclinar la cabeza para ver mejor el efecto de sus
manos o su cadera.

**Qué deberías ver:**
- Sin trigger: el frame pasa con un hue shift muy sutil y continuo (respiración neutra)
- Cabeza inclinada a la izquierda (roll negativo): la sala se "enfría" — todo vira hacia azul
- Cabeza inclinada a la derecha (roll positivo): la sala se "calienta" — todo vira hacia ámbar
- Cabeza mirando arriba (pitch positivo): todo se vuelve más brillante
- Cabeza mirando abajo (pitch negativo): leve desaturación
- La transición es gradual y suave — no hay un punto de corte abrupto

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_head`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `glsl_torso`
4. Parámetros:
   - **Pixel Shader File**: `shaders/zona_head.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Uniform Name | Rango | Qué controla |
   |------|-------------|-------|--------------|
   | `uniform0` | `uHeadTrigger` | 0 ó 1 | Activa el recoloreo activo. 0 = recoloreo mínimo ("respiración") |
   | `uniform1` | `uHeadRoll` | -90° a 90° | Inclinación lateral. Mapea directamente a frío (izq) ↔ cálido (der) |
   | `uniform2` | `uHeadPitch` | -90° a 90° | Inclinación frontal. Controla la intensidad de la tinción |
   | `uniform3` | `uTime` | segundos | Animación de hue shift continuo muy lento |

   **Rango efectivo de `uHeadRoll`:** el shader normaliza ±45° como el rango útil
   (valores fuera de ese rango se saturan). En condiciones normales de galería,
   inclinar la cabeza 30° ya produce un cambio de temperatura visible.

---

## Paso 7 — Crear el Feedback TOP

**Qué hace:** guarda el frame anterior de `glsl_glitch` y lo retroalimenta como
input[1] en el mismo shader el siguiente frame. Esto crea la "estela" del glitch —
los rastros de partículas que quedan después de un salto.

**Por qué Opacity 0.90 aquí (en lugar de 0.92 como en P1):**
P2 tiene más efectos activos simultáneamente (hands + torso + head + glitch),
por lo que la acumulación del Feedback es más intensa. Con 0.90, la estela
desaparece en ~2 s (0.90^20 = 0.12), manteniendo el balance visual.

1. Click derecho → **TOP** → `Feedback`
2. Renombrar: `feedback_loop`
3. Parámetros:
   - **Target TOP**: `glsl_glitch` (se completará en el paso siguiente)
   - **Opacity**: `0.90`

---

## Paso 8 — Crear GLSL TOP: glsl_glitch (con Feedback)

**Concepto (Trigger 4 — salto o movimiento brusco):** cuando el visitante hace un
movimiento global explosivo (saltar, agitar ambos brazos, dar una vuelta), el sistema
responde con el máximo de caos visual: glitch de bandas + partículas volando desde
todos los puntos del frame, con estela de Feedback. Es la respuesta a la energía
total del cuerpo, no a una zona específica.

**Qué deberías ver:**
- Sin trigger: el frame de la cadena anterior pasa, más la estela de Feedback en decay
  (si hubo un glitch reciente, su rastro persiste unos segundos)
- Al saltar: flash blanco intenso, luego bandas horizontales desplazadas con RGB split,
  bloques de imagen mezclados, y un campo de partículas volando desde el frame
- El glitch dura ~0.5-1 s (cooldown = 30 frames a 30fps), luego la estela decae

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_glitch`  ← **nombre exacto**
3. Conectar:
   - Entrada [0]: cable de `glsl_head`
   - Entrada [1]: cable de `feedback_loop`
   - **Input Count**: en la pestaña **Common**, asegurarse de que es **2**
4. Parámetros:
   - **Pixel Shader File**: `shaders/global_glitch.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Uniform Name | Rango | Qué controla |
   |------|-------------|-------|--------------|
   | `uniform0` | `uGlitch` | 0 ó 1 | Activa el glitch máximo. 0 = estela mínima en decay |
   | `uniform1` | `uMotionRatio` | 0.0–1.0 | Intensidad del glitch. >0.7 dispara el trigger; en el shader escala las bandas y partículas |
   | `uniform2` | `uFlowMean` | 0.0–3.0 | Magnitud de movimiento. Escala el color de las partículas (más azul claro → más blanco) |
   | `uniform3` | `uTime` | segundos | Para randomizar las bandas de glitch entre frames |

6. Volver a `feedback_loop` → **Target TOP**: escribir `glsl_glitch` → loop cerrado

---

## Paso 9 — Crear GLSL TOP: glsl_dual

**Concepto (Trigger 6 — dos personas simultáneas):** cuando dos personas están
frente a la cámara al mismo tiempo, el sistema detecta dos blobs separados y activa
el diálogo cubista. El espacio entre los dos cuerpos se fragmenta en planos compartidos.
Cada mitad del frame toma un color (azul para la izquierda, ámbar para la derecha)
y en la franja central donde "se encuentran" la fragmentación es máxima.

Este es el trigger más raro y más poderoso — requiere que dos visitantes cooperen
conscientemente frente a la instalación. Cuando sucede, suele producir sorpresa y risa.

**Qué deberías ver:**
- Una persona: el frame pasa sin cambios (pass-through)
- Dos personas juntas pero en el mismo blob: sin cambio (se necesita separación mínima)
- Dos personas separadas (> 18% del ancho del frame): mitad izquierda con tinte azul,
  mitad derecha con tinte ámbar, y en el centro una banda de planos cubistas
  fragmentados que pulsa y late suavemente

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_dual`  ← **nombre exacto**
3. Conectar entrada [0]: cable de `glsl_glitch`
4. Parámetros:
   - **Pixel Shader File**: `shaders/dual_body.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Uniform Name | Rango | Qué controla |
   |------|-------------|-------|--------------|
   | `uniform0` | `uBlobCount` | 1 ó 2 | Número de personas. Si es 1, el shader hace pass-through completo |
   | `uniform1` | `uTime` | segundos | Animación del pulso en la banda central de diálogo |

---

## Paso 10 — Trigger 5: fade a reposo (pose estática)

**Concepto:** cuando el visitante lleva más de 3 segundos completamente quieto,
la instalación "descansa" también — la imagen hace un fade gradual a negro en 2 segundos.
Cuando el visitante vuelve a moverse, la imagen vuelve inmediatamente a plena intensidad.
Este mecanismo evita que la instalación "congele" con una imagen estática cuando
no hay interacción, y también crea un momento de silencio visual entre visitas.

**Por qué con Level TOP + CHOP y no con un shader:** el fade de opacidad global es
más limpio con un Lag CHOP + Level TOP que con un shader, porque afecta la opacidad
de TODA la imagen final sin interactuar con la lógica de los GLSL TOPs individuales.

1. Click derecho → **CHOP** → `Constant`
   - Renombrar: `pose_estatica_chop`
   - En la pestaña **Chan 0**: nombre `v1`, valor `1.0`
   - Este CHOP es el "interruptor": cuando Python detecta quietud, el Script DAT
     cambia su valor de 1.0 a 0.0 para iniciar el fade

2. Click derecho → **CHOP** → `Lag`
   - Renombrar: `fade_lag`
   - Conectar: salida de `pose_estatica_chop` → entrada de `fade_lag`
   - Parámetros:
     - **Lag +**: `0` (cuando el visitante se mueve de nuevo, la imagen vuelve INMEDIATAMENTE)
     - **Lag -**: `2.0` (cuando la quietud dispara, el fade tarda 2 segundos en completarse)
   - El Lag CHOP es un suavizador: convierte el cambio abrupto 1→0 del Constant CHOP
     en una curva suave de 2 segundos de duración

3. Click derecho → **TOP** → `Level`
   - Renombrar: `fade_global`
   - Conectar entrada [0]: cable de `glsl_dual`
   - Parámetro **Opacity** → hacer clic derecho → `Export` → seleccionar el canal
     del `fade_lag` CHOP
   - Con esto, cuando el CHOP vale 1.0, la imagen está a plena opacidad; cuando vale 0.0, es negra

4. **Verificar en el Script DAT:** el código ya mapea `/cuerpo/pose_estatica`:
   cuando el valor llega > 0 (segundos de quietud), el script actualiza
   `op('pose_estatica_chop').par.value0 = 0` para iniciar el fade.
   Cuando llega 0.0 (movimiento detectado), lo restaura a 1.0.

---

## Paso 11 — Out TOP

1. Click derecho → **TOP** → `Out`
2. Renombrar: `out_proyector`
3. Conectar: cable de `fade_global` → entrada de `out_proyector`
4. **Dialogs → Window Placement** → configurar salida a los 2 proyectores Epson
   - **Resolution**: `1920 × 1200` (WUXGA nativo del Epson 5510)

---

## Diagrama completo de conexiones

```
[Python skeleton_runtime.py — misma máquina]
    │                                │
    │ Syphon/Spout (~1ms)            │ OSC UDP :9000 (loopback, <1ms)
    ▼                                ▼
[skeleton_in: Syphon/Spout TOP]   [osc_in: OSC In DAT]
    │                                    │
    │                           [osc_to_uniforms: Script DAT]
    │                                    │ actualiza uniforms en GLSL TOPs
    │                                    │ al ritmo de la cámara (~30fps)
    ▼
[glsl_hands]   ← uHandTrigger, uWristHeight, uArmOpenR, uTime
    │              qué ves: planos azul-blanco desde la posición de la mano
    │
[glsl_torso]   ← uHipTrigger, uHipAngle, uHipVelocity, uTime
    │              qué ves: estelas circulares naranja-ámbar girando con la cadera
    │
[glsl_head]    ← uHeadTrigger, uHeadRoll, uHeadPitch, uTime
    │              qué ves: temperatura de color de TODO el frame cambia con la cabeza
    │
[glsl_glitch]  ← input[1]: feedback_loop (estela)
    │              ← uGlitch, uMotionRatio, uFlowMean, uTime
    │              qué ves: glitch de bandas + partículas al saltar
    │
[feedback_loop: Feedback TOP]  Opacity: 0.90
    └──→ Target TOP = glsl_glitch  (loop cerrado)
    │
[glsl_dual]    ← uBlobCount, uTime
    │              qué ves: diálogo cubista azul/ámbar cuando hay 2 personas
    │
[fade_global: Level TOP]  ← Opacity desde fade_lag CHOP
    │              qué ves: fade a negro cuando el visitante lleva > 3s quieto
    │
[out_proyector: Out TOP]
    │
2× Epson PowerLite 5510 via HDBaseT Cat6A
Techo 4.5 m · WUXGA 1920×1200 · 5500 lm
```

---

## Nombres de operadores — tabla de referencia crítica

> **Si un nombre no coincide exactamente con lo que espera el Script DAT,
> los uniforms no se actualizarán y el efecto correspondiente estará congelado.**

| Operador | Tipo | Nombre exacto | Verificar |
|----------|------|--------------|-----------|
| OSC In DAT | DAT | `osc_in` | Tabla muestra rutas `/cuerpo/...` |
| Script DAT | DAT | `osc_to_uniforms` | Sin errores en Textport |
| Syphon/Spout In | TOP | `skeleton_in` | Muestra overlay de esqueleto |
| GLSL TOP 1 | TOP | **`glsl_hands`** | zona_hands.glsl cargado |
| GLSL TOP 2 | TOP | **`glsl_torso`** | zona_torso.glsl cargado |
| GLSL TOP 3 | TOP | **`glsl_head`** | zona_head.glsl cargado |
| GLSL TOP 4 | TOP | **`glsl_glitch`** | global_glitch.glsl, Input Count=2 |
| GLSL TOP 5 | TOP | **`glsl_dual`** | dual_body.glsl cargado |
| Feedback TOP | TOP | `feedback_loop` | Target TOP = glsl_glitch |
| Constant CHOP | CHOP | `pose_estatica_chop` | Canal v1, valor 1.0 |
| Lag CHOP | CHOP | `fade_lag` | Lag- = 2.0, Lag+ = 0 |
| Level TOP | TOP | `fade_global` | Opacity exportada desde fade_lag |
| Out TOP | TOP | `out_proyector` | Pantalla/proyector seleccionado |

---

## Calibración en sala — protocolo P2

P2 es el más sensible a la calibración porque depende de la iluminación (ver sección
de Limitaciones). Calibrar en este orden:

### 1. Verificar el share Syphon/Spout
- `skeleton_in` debe mostrar el overlay del esqueleto sobre fondo oscuro
- El esqueleto debe moverse suavemente al caminar (no saltar erráticamente)
- Si el esqueleto salta: `MP_MODEL_COMPLEXITY = 2` en `config.py` (más preciso, ~10% menos fps)

### 2. Verificar los triggers individuales
- Levantar la mano lentamente: `glsl_hands` debe activarse visiblemente
  (si no responde, bajar `HAND_RAISE_MARGIN` via `/mcp/set/hand_raise_margin 0.05`)
- Girar la cadera 20° y volver: `glsl_torso` debe activarse
  (si no responde, bajar `HIP_ROT_THRESHOLD_DEG` a 10)
- Inclinar la cabeza 15°: `glsl_head` debe cambiar la temperatura de color
  (si no responde, bajar `HEAD_ROLL_THRESHOLD_DEG` a 8)
- Saltar: `glsl_glitch` debe disparar (si no, bajar `MOTION_RATIO_THRESHOLD` a 0.5)
- Quedarse quieto 3 s: `fade_global` debe bajar la opacidad
- Pararse junto a otra persona: `glsl_dual` debe activarse (separación mínima ~30 cm)

### 3. Ajustar la iluminación de galería
- Si los joints son inestables (el esqueleto "tiembla"): subir confianza de tracking
  `/mcp/set/mp_model_complexity` requiere reinicio, pero `/mcp/set/hand_raise_margin`
  puede compensar parcialmente
- Si hay personas pasando al fondo y disparan triggers: subir `BLOB_MIN_AREA`
  vía MCP bridge para ignorar siluetas pequeñas

---

## Rutas OSC de referencia rápida

| Ruta | Tipo | Va a |
|------|------|------|
| `/cuerpo/trigger_zona` | string | Debug — zona activa del frame |
| `/cuerpo/mano_derecha` | float[3] | `glsl_hands`: trigger / altura muñeca / apertura brazo |
| `/cuerpo/cadera` | float[3] | `glsl_torso`: trigger / ángulo / velocidad angular |
| `/cuerpo/cabeza` | float[3] | `glsl_head`: trigger / roll / pitch |
| `/cuerpo/global/glitch` | float | `glsl_glitch`: uGlitch (0 ó 1) |
| `/cuerpo/metrica/motion_ratio` | float | `glsl_glitch`: uMotionRatio |
| `/cuerpo/metrica/flow_mean` | float | `glsl_glitch`: uFlowMean |
| `/cuerpo/blob_count` | float | `glsl_dual`: uBlobCount |
| `/cuerpo/pose_estatica` | float | `pose_estatica_chop`: segundos de quietud (0 = en movimiento) |

---

## Lista de verificación antes de la inauguración

- [ ] Python 3.11 o 3.12 confirmado (`python --version`)
- [ ] `skeleton_runtime.py` corre sin errores, log muestra fps y datos
- [ ] `skeleton_in` TOP: overlay de esqueleto visible y suave (no errático)
- [ ] `osc_in` DAT: tabla muestra rutas `/cuerpo/...` actualizándose
- [ ] Levantar brazo → `glsl_hands` activa planos azules visibles
- [ ] Girar cadera → `glsl_torso` activa estelas naranjas circulares
- [ ] Inclinar cabeza → `glsl_head` cambia temperatura de color perceptiblemente
- [ ] Saltar → `glsl_glitch` dispara flash + distorsión (cooldown = 1s)
- [ ] Quietud > 3 s → `fade_global` hace fade a negro suave en 2 s
- [ ] Moverse de nuevo → imagen vuelve instantáneamente a plena intensidad
- [ ] Dos personas frente a cámara → `glsl_dual` activa diálogo cubista
- [ ] `feedback_loop`: Target TOP = glsl_glitch, Opacity = 0.90
- [ ] `pose_estatica_chop` → `fade_lag`: Export de Opacity configurado
- [ ] Proyectores: imagen correctamente keystone en el piso
- [ ] Prueba de 8 horas continuas sin caída de FPS

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `skeleton_in` negro | Syphon/Spout no instalado | `pip install SpoutGL` (Win) / `pip install syphon-python` (Mac) en el venv activo |
| `skeleton_in` negro | Nombre servidor no coincide | Verificar `SHARE_SENDER_NAME` en `config.py` coincide con Server Name en TD |
| Skeleton inestable / saltando | Python 3.13 instalado | MediaPipe no tiene wheels para 3.13 — reinstalar con Python 3.12 |
| Joints inestables en sala | Iluminación difícil | Subir `MP_MODEL_COMPLEXITY` a 2 en `config.py` y reiniciar (cuesta ~10% fps) |
| Trigger 1 (manos) nunca dispara | `HAND_RAISE_MARGIN` alto | `/mcp/set/hand_raise_margin 0.05` en :9001 |
| Trigger 5 (fade) no funciona | Export mal configurado | Click derecho en Opacity de `fade_global` → verificar Export → canal de `fade_lag` |
| Glitch muy frecuente | Jitter de joints en sala | Subir `motion_ratio_threshold` via MCP bridge a 0.80+ |
| `glsl_dual` nunca activa | Separación entre personas baja | Bajar `dual_min_separation` a 0.12 via `/mcp/set/dual_min_separation 0.12` |
| `osc_to_uniforms` con error | Nombre de op incorrecto | Verificar tabla de nombres de operadores arriba — son case-sensitive |

---

## Limitación crítica de P2 — iluminación

**Este es el riesgo número uno de la propuesta P2.** A diferencia de P1 (profundidad,
insensible a la luz visible) o P4 (DeepLabv3, entrenado para condiciones variables),
P2 depende de que MediaPipe estime bien los joints desde el color RGB. La proyección
activa de la instalación puede crear exactamente las condiciones adversas:

- **Luz proyectada rebota en el cuerpo del visitante** → contorno inestable, joints confundidos
- **Ropa blanca bajo proyección azul** → la ropa "desaparece" en la segmentación
- **Sombras cruzadas de los proyectores** → joints estimados incorrectamente

**Acción obligatoria:** visita técnica a la Galería Fernando Cano ANTES de confirmar P2.
Si la iluminación es adversa, considerar P4 (DeepLabv3 + CoreML) que es más robusto.
