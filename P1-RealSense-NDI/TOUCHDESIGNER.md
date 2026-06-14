# TouchDesigner — Guía de Operación Completa
## P1 · RealSense D435i + NDI · Aún Sorprendo · JIFREX

> **Para el operador técnico:** esta guía asume que sabes moverte en TouchDesigner
> (crear operators, conectar cables, abrir el editor de scripts), pero que nunca
> has visto este proyecto. Deberías poder montar el patch completo en 2 horas
> siguiendo estos pasos en orden.

---

## Concepto artístico — qué estamos construyendo

La instalación reacciona a la presencia de un visitante frente a la RealSense D435i.
La cámara ve en profundidad (como un radar): detecta exactamente dónde está el
cuerpo en el espacio, sin importar la ropa ni la iluminación.

Cuando el visitante se mueve:
- El borde de su silueta adquiere un **halo azulado** que pulsa (más brillante cuanto
  más rápido se mueve — referencia directa a "Les Bleus de Barcelona" de Picasso)
- Movimientos bruscos disparan un **glitch** que fragmenta el frame digitalmente
  (Picasso fragmentó las perspectivas; nosotros fragmentamos los píxeles)
- Una **estela de partículas** emerge del borde de la silueta y persiste 2-3 segundos
  después de cada movimiento (la huella temporal que Picasso dejaba en el lienzo)

Cuando el visitante sale o se queda quieto, la imagen decae lentamente a negro.

**Flujo completo de la experiencia:**
1. El visitante entra al espacio — Python detecta presencia, OSC llega a TD
2. Primera vez que se mueve — el halo aparece tenue y crece con el movimiento
3. Movimiento rápido — el glitch explota brevemente, partículas en el borde
4. Quietud — las partículas decaen en 2-3 s, el halo baja a pulso mínimo
5. El visitante sale — todo decae a negro en ~3 segundos

---

## Antes de abrir TouchDesigner

### Máquinas involucradas

| Máquina | Rol | Sistema |
|---------|-----|---------|
| **MSI Katana GF66** | Captura + segmentación + emisión | Windows 11 |
| **MacBook Pro M3 Max** | TouchDesigner + proyección | macOS |

Las dos máquinas deben estar en la **misma red LAN** (mismo switch o router).
**Recomendado: cable Ethernet directo o switch gigabit — nunca Wi-Fi en producción.**
El Wi-Fi introduce jitter de latencia que hace que los uniforms lleguen con retraso
variable, produciendo artefactos visuales (el halo "salta" en lugar de fluir).

### En la MSI — hacer PRIMERO, antes de abrir TD

```powershell
# 1. Editar la IP del Mac (OBLIGATORIO — sin esto nada llega a TD)
notepad C:\Users\USUARIO\GitLenovo\P1-RealSense-NDI\config.py
# Cambiar la línea: OSC_HOST = "192.168.1.XX"  →  IP real del Mac
# Para encontrar la IP del Mac: en el Mac, abrir Terminal → ifconfig | grep "inet "

# 2. Activar el entorno Python
cd C:\Users\USUARIO\GitLenovo\P1-RealSense-NDI
.\venv\Scripts\Activate.ps1

# 3. Terminal A — MCP bridge (ajuste de parámetros en vivo, opcional pero útil)
#    Dejar corriendo en esta terminal
python mcp_bridge.py

# 4. Terminal B — Pipeline principal (en OTRA terminal PowerShell)
python webcam_runtime.py
```

El log de Terminal B debe verse así en los primeros segundos:
```
[      ]  30.0 fps | blob=    0px | flow=0.000 | motion=0.000 | cooldown= 0
```
Si no aparece el log o aparece un error de `OSC_HOST`, verificar la IP.
Si aparece `[RS] pyrealsense2 no disponible`, la cámara RealSense no está conectada
— el sistema entra en modo simulación con webcam normal (útil para pruebas).

### Verificar que NDI está llegando al Mac

Instalar **NDI Tools** (gratuito, de Vizrt) en el Mac si no está instalado.
Abrir **NDI Video Monitor** → debe aparecer `JIFREX-MSI-MASK` en la lista de fuentes.
Si no aparece:
- El firewall de Windows está bloqueando NDI → abrir Windows Defender →
  "Permitir una aplicación a través del firewall" → añadir el proceso de Python
- Alternativa rápida: desactivar el firewall temporalmente para verificar que eso es el problema

---

## Abrir TouchDesigner en el Mac

1. Abrir TouchDesigner (versión 2023.x o superior recomendada)
2. Menú **File → New** → proyecto en blanco
3. Guardar como: `P1_JIFREX_Aun_Sorprendo.toe` en el directorio del proyecto
   (`C:\Users\USUARIO\GitLenovo\P1-RealSense-NDI\` — si estás en el Mac, montar
   el directorio compartido o clonar el repo en el Mac también)

---

## Paso 1 — Crear el OSC In DAT

**Qué hace:** recibe todas las métricas que Python calcula en la MSI — cuánto se
mueve el visitante, si disparó el trigger, el tamaño de la silueta, etc.
Llega por UDP como paquetes OSC, aproximadamente a 30 fps sincronizado con la cámara.

**Por qué un DAT y no un CHOP:** el OSC In DAT permite leer múltiples rutas con
nombres semánticos (`/jifrex/flow_mean`, `/jifrex/trigger`) en una sola tabla.
Luego el Script DAT del Paso 2 distribuye cada valor al uniform correcto de cada shader.

1. En el **Network Editor**, click derecho → **Add Operator** → pestaña **DAT** → `OSC In`
2. Renombrar el operador: doble clic en el nombre → escribir `osc_in`
3. En el panel de parámetros (derecha):
   - **Protocol**: UDP
   - **Port**: `9000`
   - **Local Address**: (dejar vacío — escucha en todas las interfaces del Mac)
   - **Active**: ON (debe estar en verde)
4. **Verificar:** cuando Python está corriendo en la MSI, la tabla del DAT debe
   mostrar filas con `/jifrex/flow_mean`, `/jifrex/trigger`, `/jifrex/presence`, etc.
   Si la tabla está vacía: la MSI no está enviando OSC, o la IP está mal.

---

## Paso 2 — Crear el Script DAT

**Qué hace:** cada vez que llega un nuevo mensaje OSC (la tabla cambia), este script
lee los valores y los escribe directamente como parámetros de los GLSL TOPs.
Es el "cable invisible" entre la física del movimiento del visitante y los shaders.

**Por qué un Script DAT y no un OSC CHOP:** el Script DAT permite leer rutas con
nombres arbitrarios y enviarlas a operators específicos por nombre (`op('glsl_halo')`),
manteniendo el código limpio y sin depender de la estructura de CHOPs.

1. Click derecho → **DAT** → `Script`
2. Renombrar: `osc_to_uniforms`
3. Conectar: arrastrar el cable de salida de `osc_in` → entrada de `osc_to_uniforms`
4. En parámetros del Script DAT:
   - **Execute**: `Table Change`
     *(esto ejecuta el script cada vez que la tabla OSC recibe nuevos datos — aprox. 30 fps)*
5. Click en el ícono de lápiz del Script DAT para abrir el editor
6. Borrar el contenido por defecto
7. Copiar y pegar el contenido completo del archivo `shaders/td_osc_to_uniforms.py`
8. Cerrar el editor — se guarda automáticamente
9. **Verificar:** en la consola de TD (menú Dialogs → Textport), no debe aparecer
   ningún error en rojo. Si aparece `op('glsl_halo') not found`, el nombre del
   GLSL TOP no coincide — revisar el Paso 5.

---

## Paso 3 — Crear el NDI In TOP

**Qué hace:** recibe la máscara binaria (silueta blanca sobre negro) que Python
calcula en la MSI y transmite por NDI a través de la red LAN. La latencia es ~8 ms
en una red gigabit — suficientemente rápida para que los shaders la procesen en tiempo real.

**Por qué NDI y no Syphon:** Syphon funciona solo en la misma máquina (GPU→GPU).
Como P1 usa dos máquinas (MSI y Mac), necesitamos un protocolo de red. NDI es el
estándar para video profesional por red y TouchDesigner lo soporta nativamente.

1. Click derecho → **TOP** → `NDI In`
2. Renombrar: `ndi_mask`
3. En parámetros:
   - **Source Name**: `JIFREX-MSI-MASK`
     *(este nombre debe coincidir EXACTAMENTE con `NDI_SOURCE_NAME` en `config.py` de la MSI)*
   - **Resolution**: `Use Source` (para aceptar automáticamente la resolución de la MSI)
4. **Verificar:** el TOP debe mostrar la silueta del visitante en blanco sobre negro.
   Si aparece negro: la MSI no está enviando NDI, o el nombre de fuente no coincide.
   Si aparece "waiting for source": el firewall de Windows está bloqueando NDI en la MSI.

**Qué deberías ver en este TOP:**
- Con la cámara apuntando a una persona: silueta blanca sobre negro
- Sin nadie frente a la cámara: negro puro (con posible ruido mínimo)
- Con muchas personas o ruido de fondo: múltiples siluetas fragmentadas
  (ajustar `DEPTH_MIN_MM` / `DEPTH_MAX_MM` en `config.py` de la MSI)

---

## Paso 4 — Crear el Null TOP de máscara limpia

**Qué hace:** crea una referencia adicional a la máscara NDI. Varios shaders
necesitan la máscara original (sin modificar por shaders anteriores) para funcionar
correctamente — `glsl_glitch` la usa para confinar la distorsión a la silueta,
y `glsl_particles` la usa para detectar el borde donde nacen las partículas.

Si conectáramos la salida de `glsl_halo` como máscara para `glsl_glitch`, el borde
ya vendría modificado por el primer shader y las partículas no nacerían en el lugar
correcto.

1. Click derecho → **TOP** → `Null`
2. Renombrar: `mask_orig`
3. Conectar: cable de salida de `ndi_mask` → entrada de `mask_orig`

---

## Paso 5 — Crear el GLSL TOP: glsl_halo

**Concepto artístico:** el halo es la primera respuesta visual del sistema al
movimiento. Cuando el visitante se mueve lentamente, el borde de su silueta brilla
con un azul tenue. Cuando se mueve rápido, el halo crece y palpita — la instalación
"respira" al ritmo del visitante. Esta pulsación es la referencia directa a la
energía cinética que Picasso expresaba en sus figuras en movimiento.

**Qué deberías ver en este TOP:**
- Visitante quieto: silueta blanca fría con un halo azul muy sutil que pulsa lentamente
- Visitante moviéndose lento (flow_mean ≈ 0.3–0.5): aureola azulada alrededor de la silueta
- Visitante moviéndose rápido (flow_mean > 1.0): halo brillante azul-blanco pulsando,
  visible incluso en una sala con luz ambiental moderada
- Nadie frente a la cámara: negro completo (alpha = 0)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_halo`  ← **el nombre DEBE ser exactamente este** (lo usa el Script DAT)
3. Conectar: cable de `ndi_mask` → entrada [0] de `glsl_halo`
4. En parámetros del GLSL TOP:
   - Pestaña **TOP** → **Pixel Shader** → **File**: click en carpeta →
     navegar a `shaders/halo_glow.glsl` (ruta relativa al directorio del proyecto)
   - **File Active**: ON
5. Pestaña **Vectors 1** — agregar los uniforms:

   | Slot | Uniform Name | Valor inicial | Qué controla |
   |------|-------------|--------------|--------------|
   | `uniform0` | `uFlowMean` | `0` | Intensidad del halo. 0 = sin movimiento, 1.0+ = movimiento activo |
   | `uniform1` | `uTime` | `0` | Tiempo para la animación del pulso. Conectar a `absTime.seconds` |

   Cómo agregar uniforms en TD:
   - En la sección **Vectors 1**, click en el `+` para agregar una fila
   - **Par Name**: `uniform0` → **Uniform Name**: `uFlowMean` → **value0**: `0`
   - Repetir para `uTime`

   > Los valores se actualizarán automáticamente desde `osc_to_uniforms` cada frame.
   > Los valores iniciales son los que se ven cuando Python no está corriendo.

   **Explicación de cada uniform:**
   - `uFlowMean` (rango 0–3+): magnitud promedio del optical flow en píxeles/frame.
     En el shader se usa para escalar la intensidad del halo (`haloIntensity * (1 + uFlowMean * 2.5)`).
     Un valor de 0 produce el halo mínimo; 1.0 duplica la intensidad; 2.0+ produce el halo máximo.
   - `uTime` (segundos crecientes): se usa para la animación del pulso (`sin(uTime * 3.0)`).
     Conectar a `absTime.seconds` en TD para que se actualice automáticamente:
     hacer click derecho en el campo value0 de `uTime` → **Add Reference** → `absTime.seconds`.

---

## Paso 6 — Crear el GLSL TOP: glsl_glitch

**Concepto artístico:** el glitch es la respuesta al movimiento brusco — el sistema
"rompe" el frame cuando la energía del visitante supera un umbral. Es el equivalente
digital de la fragmentación cubista: el espacio se astilla en planos de color
desplazados. Pero a diferencia de Picasso (que siempre fragmentaba), el glitch aquí
es escaso — solo aparece cuando hay verdadero movimiento explosivo, lo que hace que
cuando aparece tenga mucho más impacto.

**Qué deberías ver en este TOP:**
- Sin trigger (visitante quieto o moviéndose suave): imagen idéntica al TOP anterior (pass-through)
- En el momento del trigger: flash blanco intenso seguido de bandas horizontales
  desplazadas con aberración cromática (rojo desplazado a la derecha, azul a la izquierda)
- La intensidad del glitch escala con `uMotionRatio` — más fracción del frame en
  movimiento = bandas más anchas y RGB split más pronunciado

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_glitch`  ← **exactamente este nombre**
3. Conectar:
   - Entrada [0]: cable de salida de `glsl_halo` (el frame ya procesado con el halo)
   - Entrada [1]: cable de salida de `mask_orig` (la máscara original sin modificar)
     *(input[1] permite confinar la distorsión a la silueta real del visitante)*
4. En parámetros:
   - **Pixel Shader File**: `shaders/glitch.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Uniform Name | Valor inicial | Qué controla |
   |------|-------------|--------------|--------------|
   | `uniform0` | `uTrigger` | `0` | 0 = sin glitch (pass-through), 1 = glitch activo |
   | `uniform1` | `uMotionRatio` | `0` | Fracción de píxeles en movimiento (0–1). Escala la intensidad del glitch |
   | `uniform2` | `uTime` | `0` | Tiempo para las bandas animadas |

   **Explicación de cada uniform:**
   - `uTrigger`: el shader hace un branch explícito — si < 0.5, devuelve el pixel
     original sin cambio. Esto asegura que el glitch no afecta frames normales.
     El trigger tiene un cooldown de 30 frames (~1 s) en Python para que no sea continuo.
   - `uMotionRatio`: fracción de píxeles con movimiento > 1px. Valores típicos:
     0.05–0.15 en movimiento normal, 0.3–0.7 en movimiento rápido, >0.7 = salto.
     Controla el ancho de las bandas de glitch y la separación del RGB split.
   - `uTime`: usado para randomizar las bandas en cada frame. Si se queda en 0,
     el glitch sería siempre el mismo patrón — conectar a `absTime.seconds`.

---

## Paso 7 — Crear el Feedback TOP

**Qué hace y por qué:** el Feedback TOP guarda el frame anterior y lo devuelve como
input al shader del siguiente frame. Esto crea el efecto de "estela" o "rastro":
las partículas que nacen en el borde de la silueta no desaparecen inmediatamente
sino que persisten y decaen gradualmente.

**Cómo funciona el loop:**
```
glsl_particles (frame N) → [proyectado] → Feedback TOP → input[1] de glsl_particles (frame N+1)
```
Cada frame, el shader recibe su propio output del frame anterior multiplicado
por `decay` (0.96 por defecto). Después de 30 frames (1 s), la estela es 0.96^30 = 0.294,
es decir, visible pero claramente atenuada. Después de 75 frames (~2.5 s), desaparece.

**Por qué `Opacity: 0.92` en el Feedback TOP y no en el shader:**
El Feedback TOP aplica su propia opacidad antes de devolver el frame. En el shader,
el decay adicional (0.96) actúa sobre el frame ya atenuado. El valor 0.92 en el
Feedback TOP es el punto de partida — ajustar en sala.

1. Click derecho → **TOP** → `Feedback`
2. Renombrar: `feedback_loop`
3. En parámetros:
   - **Target TOP**: `glsl_particles` (escribir el nombre — se conectará en el Paso 8)
   - **Opacity**: `0.92`
     - Si el valor fuera 1.0: la estela sería permanente (los píxeles se acumularían
       y la imagen se saturaría de blanco)
     - Si el valor fuera 0.80: la estela desaparecería en menos de 1 segundo
       (0.80^30 = 0.001 — invisible después de 30 frames)
     - 0.92 produce una estela de ~2.5 s visible, que en sala con luz proyectada
       típica es un balance correcto

---

## Paso 8 — Crear el GLSL TOP: glsl_particles

**Concepto artístico:** las partículas son la huella temporal del cuerpo en el
espacio — emergen del borde exacto de la silueta y flotan hacia afuera, dejando
un rastro que persiste un momento después de que el cuerpo se ha movido. Es la
respuesta al gesto anterior, no al gesto presente. Como en el cubismo: vemos el
tiempo condensado en el espacio.

**Qué deberías ver en este TOP:**
- Visitante quieto: partículas tenues emergiendo del borde (densidad mínima)
- Visitante en movimiento: lluvia de partículas azul-blanco del borde de la silueta,
  con estela que persiste ~2.5 s tras cada movimiento
- El color de las partículas va de azul suave (movimiento lento) a blanco frío
  (movimiento intenso) — cuantificando visualmente la energía
- Sin visitante: la estela decae rápidamente a negro (~0.75 por frame)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_particles`  ← **exactamente este nombre**
3. Conectar:
   - Entrada [0]: cable de salida de `glsl_glitch`
   - Entrada [1]: cable de salida de `feedback_loop`
   - Entrada [2]: cable de salida de `mask_orig`
   - **CRÍTICO — Input Count:** en la pestaña **Common** del GLSL TOP,
     asegurarse de que **Input Count = 3** (por defecto es 1 — hay que aumentarlo)
4. En parámetros:
   - **Pixel Shader File**: `shaders/feedback_particles.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):

   | Slot | Uniform Name | Valor inicial | Qué controla |
   |------|-------------|--------------|--------------|
   | `uniform0` | `uFlowMean` | `0` | Velocidad de partículas. A mayor flow, más rápidas |
   | `uniform1` | `uMotionRatio` | `0` | Densidad: cuántas partículas nacen por frame |
   | `uniform2` | `uPresence` | `0` | 1 = visitante detectado (decay lento), 0 = sin visitante (decay rápido) |
   | `uniform3` | `uTime` | `0` | Tiempo para la animación de partículas |

   **Explicación de cada uniform:**
   - `uFlowMean`: escalala velocidad angular y la velocidad de escape de las partículas.
     Con flow 0, las partículas casi no se mueven. Con flow 1.5, vuelan del borde.
   - `uMotionRatio`: controla `numParticles = int(12 + motionRatio * 24)`, es decir
     entre 12 y 36 partículas activas por frame. En reposo, 12 partículas tenues.
   - `uPresence`: cuando es 0 (sin visitante), el decay baja de 0.96 a 0.75.
     Esto hace que la estela desaparezca en ~5 frames (no ~75) cuando el visitante sale.
   - `uTime`: conectar a `absTime.seconds` igual que en los otros shaders.

---

## Paso 9 — Cerrar el loop del Feedback TOP

Este es el paso más importante para que el efecto de estela funcione:

1. Seleccionar `feedback_loop`
2. Parámetro **Target TOP**: escribir `glsl_particles`
3. **Verificar:** el Feedback TOP debe mostrar un pequeño preview del frame anterior
   de `glsl_particles`. Si muestra negro, el loop no está cerrado correctamente.

El loop queda así:
```
glsl_particles → [out actual]
     ↑
feedback_loop ← [Target TOP: glsl_particles]
```
`feedback_loop` lee el output de `glsl_particles` del frame pasado y lo pasa
como input[1] de `glsl_particles` en el frame actual. Así el shader puede
mezclar "lo que está pasando ahora" con "lo que pasó antes".

---

## Paso 10 — Level TOP y Out TOP

1. Click derecho → **TOP** → `Level`
   - Renombrar: `level_final`
   - Conectar: cable de `glsl_particles` → entrada de `level_final`
   - **Brightness**: `1.0` (ajustar en sala — si los proyectores son muy brillantes,
     bajar a 0.85 para que el negro sea negro y no gris oscuro)
   - **Contrast**: `1.05` (leve aumento para que el blanco brille más contra el negro)
   - **Gamma**: dejar en `1.0` (los shaders ya están calibrados linealmente)

2. Click derecho → **TOP** → `Out`
   - Renombrar: `out_proyector`
   - Conectar: cable de `level_final` → entrada de `out_proyector`
   - En parámetros → **Output**: seleccionar la pantalla/proyector correspondiente

---

## Paso 11 — Configurar salida de proyectores

**2× Epson PowerLite 5510** conectados via HDBaseT Cat6A (cable de red de alta calidad)
Resolución nativa: **WUXGA — 1920×1200** (no 1920×1080 — los 1200px son importantes)

1. Menú **Dialogs → Window Placement**
2. Agregar una ventana de salida por cada proyector:
   - **Resolution**: `1920 × 1200` (WUXGA nativa del Epson 5510)
   - **Display**: seleccionar el display del proyector correspondiente
   - **TOP**: `out_proyector`
3. Si los proyectores son dos pantallas extendidas:
   - Crear dos `Out TOP` con el mismo input (`level_final`)
   - En Window Placement, asignar cada Out TOP a su proyector

**Calibración de keystone en sala:**
Los proyectores están en el techo a 4.5 m de altura proyectando hacia abajo.
El keystone (corrección trapecial) se ajusta directamente en el proyector con el
control remoto del Epson — NO en TouchDesigner. En TD ajustamos la imagen de salida;
el keystone físico lo hace el proyector.

---

## Paso 12 — Folder DAT para hot-reload de shaders

**Qué hace:** cuando guardas un archivo `.glsl` con tu editor, el GLSL TOP lo
detecta automáticamente y lo recarga sin que tengas que hacer nada en TD.
Esto es esencial para el ajuste artístico en sala — puedes editar el shader en
un editor externo y ver el resultado en tiempo real en los proyectores.

1. Click derecho → **DAT** → `Folder`
2. Renombrar: `shader_folder`
3. Parámetros:
   - **Folder**: ruta absoluta a la carpeta `P1-RealSense-NDI/shaders/`
   - **Include Extensions**: `glsl`
4. Verificar: el DAT muestra los 3 archivos `.glsl` del proyecto

Con `File Active: ON` en cada GLSL TOP, TouchDesigner monitorea el archivo directamente.
El Folder DAT es opcional pero centraliza la referencia y facilita el trabajo.

---

## Diagrama completo de conexiones

```
[MSI: webcam_runtime.py]
    │ NDI (~8ms LAN)           │ OSC UDP :9000 (<2ms LAN)
    ▼                           ▼
[ndi_mask: NDI In TOP]       [osc_in: OSC In DAT]
    │                              │
    ├──→ [mask_orig: Null]    [osc_to_uniforms: Script DAT]
    │        │                     │ actualiza par.value en cada GLSL TOP
    │        │                     │ (~30 fps, sincronizado con la cámara)
    │        │                     ▼
    └──→ [glsl_halo]  ←── uniforms: uFlowMean=X, uTime=T
              │            qué ves: silueta + halo azul pulsante
              │
         [glsl_glitch] ←── input[1]: mask_orig (máscara sin modificar)
              │              uniforms: uTrigger=0/1, uMotionRatio=X, uTime=T
              │              qué ves: igual que halo, + glitch al trigger
              │
         [glsl_particles] ←── input[1]: feedback_loop (frame anterior)
              │               ←── input[2]: mask_orig (para detectar borde)
              │                uniforms: uFlowMean, uMotionRatio, uPresence, uTime
              │                qué ves: partículas del borde + estela persistente
              │
         [feedback_loop: Feedback TOP]
              │ Opacity: 0.92
              │ Target TOP: glsl_particles (loop cerrado)
              │
         [level_final: Level TOP]
              │ Brightness: 1.0, Contrast: 1.05
              │
         [out_proyector: Out TOP]
              │
    2× Epson PowerLite 5510 via HDBaseT Cat6A
    Techo 4.5 m · WUXGA 1920×1200 · 5500 lm
```

---

## Calibración en sala — protocolo paso a paso

El orden importa. Calibrar en el orden incorrecto hace que ajustes posteriores
invaliden los anteriores.

### 1. Verificar el video NDI primero
- Colocarse frente a la RealSense D435i en el MSI
- El TOP `ndi_mask` debe mostrar la silueta claramente
- Si la silueta tiene agujeros o es irregular: ajustar `DEPTH_MIN_MM` y `DEPTH_MAX_MM`
  en `config.py` de la MSI (default 300mm–3000mm — ajustar según el espacio real)

### 2. Calibrar el threshold de presencia
- Usar el MCP bridge desde el Mac (o cualquier app OSC) para ajustar:
  ```
  Enviar a MSI:9001 → /mcp/set/area_threshold  <int>
  ```
- Con nadie frente a la cámara, `blob_area` en el log debe ser < 100 px
- Con el visitante, debe ser > 1000 px
- `area_threshold` (default 500) debe quedar entre estos dos valores

### 3. Calibrar el trigger
- Moverse lentamente: el log NO debe mostrar `[TRIGGER]`
- Moverse rápido / saltar: el log SÍ debe mostrar `[TRIGGER]`
- Si el trigger es demasiado fácil: subir `flow_threshold` (default 0.5) o `motion_threshold`
- Si nunca dispara: bajarlos

### 4. Calibrar el halo en la sala con luz proyectada
- Con los proyectores encendidos y la imagen proyectada en el piso,
  el halo debe ser visible con el visitante a la distancia normal de interacción (~2m)
- Si el halo es demasiado brillante: bajar `Brightness` en el `level_final` Level TOP
- Si el halo apenas se ve: subir `Contrast` o editar `haloIntensity` en `halo_glow.glsl`

### 5. Calibrar la estela de partículas
- Moverse frente a la cámara 3 segundos, luego quedarse quieto
- La estela debe persistir ~2-3 segundos y luego desaparecer
- Si la estela es demasiado persistente: bajar `Opacity` en el Feedback TOP (de 0.92 a 0.88)
- Si la estela desaparece muy rápido: subirla (hasta 0.95 máximo — más y se acumula)

### 6. Prueba de 8 horas
- Dejar el sistema corriendo 8 horas continuas
- Monitorear FPS (debe mantenerse en ~30 fps)
- Si el FPS baja: verificar que TouchDesigner no tiene Preview habilitado (en el Perform Mode
  no se renderiza el Network Editor, ahorrando GPU)
- Verificar que no hay memory leak (el uso de RAM debe ser estable)

---

## Nombres de operadores — tabla de referencia crítica

> **Si un nombre no coincide exactamente, el Script DAT no podrá encontrar el operator
> y producirá un error silencioso — los uniforms no se actualizarán.**

| Operador | Tipo | Nombre exacto | Verificar |
|----------|------|--------------|-----------|
| OSC In DAT | DAT | `osc_in` | Tabla muestra `/jifrex/...` |
| Script DAT | DAT | `osc_to_uniforms` | Sin errores en consola TD |
| NDI In TOP | TOP | `ndi_mask` | Silueta visible (no negro) |
| Null TOP | TOP | `mask_orig` | Mismo frame que ndi_mask |
| GLSL TOP 1 | TOP | **`glsl_halo`** | halo_glow.glsl cargado |
| GLSL TOP 2 | TOP | **`glsl_glitch`** | glitch.glsl cargado |
| GLSL TOP 3 | TOP | **`glsl_particles`** | feedback_particles.glsl, Input Count=3 |
| Feedback TOP | TOP | `feedback_loop` | Target TOP = glsl_particles |
| Level TOP | TOP | `level_final` | Brightness=1.0 |
| Out TOP | TOP | `out_proyector` | Pantalla/proyector seleccionado |

---

## Lista de verificación antes de la inauguración

- [ ] MSI: `webcam_runtime.py` corre sin errores, log muestra FPS
- [ ] NDI Monitor del Mac: `JIFREX-MSI-MASK` visible en la lista
- [ ] `ndi_mask` TOP: silueta visible (no negro)
- [ ] `osc_in` DAT: tabla tiene filas con `/jifrex/flow_mean`, `/jifrex/trigger`, etc.
- [ ] `osc_to_uniforms`: sin errores en la consola de TD
- [ ] `glsl_halo`: halo azul visible al mover la mano frente a la cámara
- [ ] `glsl_glitch`: glitch dispara al hacer movimiento brusco (saltar, agitar brazos)
- [ ] `glsl_particles`: estela de partículas visible, persiste ~2.5 s tras el movimiento
- [ ] `feedback_loop`: Target TOP = glsl_particles, Opacity = 0.92
- [ ] Proyectores: imagen correctamente keystone y posicionada en el piso
- [ ] Prueba de 8 horas continuas sin caída de FPS ni memory leak
- [ ] Con nadie frente a la cámara: imagen en negro completo (no gris)
- [ ] Con visitante: halo visible, glitch al saltar, partículas persisten

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `ndi_mask` en negro | MSI no emite o firewall | Verificar `webcam_runtime.py` corriendo; permitir NDI en Windows Defender |
| `osc_in` sin datos | IP incorrecta en `config.py` | Verificar `OSC_HOST` en MSI apunta a la IP real del Mac |
| Shader muestra negro | Path del `.glsl` incorrecto | En GLSL TOP → pestaña TOP → File → verificar ruta absoluta al `.glsl` |
| `glsl_particles` sin estela | `feedback_loop` no cerrado | Verificar Target TOP = `glsl_particles` en el Feedback TOP |
| Glitch muy frecuente | `flow_threshold` bajo | Subir `flow_threshold` en el MSI vía MCP bridge: `/mcp/set/flow_threshold 0.8` |
| Glitch nunca dispara | `flow_threshold` alto o cooldown | Bajar umbral vía MCP bridge, o verificar que `osc_in` recibe datos |
| Halo irregular | Ruido en la máscara NDI | Compresión NDI — asegurarse de que hay suficiente ancho de banda (>100 Mbps) |
| FPS bajo en TD | Demasiadas ventanas de Preview | Usar **Perform Mode** (F1) durante la exhibición — elimina el overhead del editor |
| Halo siempre en 0 | `osc_to_uniforms` con error | Abrir Textport → buscar errores con `op('glsl_halo') not found` |
| Partículas en negro | Input Count incorrecto | En `glsl_particles` → Common → **Input Count = 3** |

---

## Rutas OSC de referencia rápida

| Ruta | Tipo | Rango | Descripción |
|------|------|-------|-------------|
| `/jifrex/trigger` | float 0/1 | 0 ó 1 | Trigger anti-FP disparado. Activa el glitch. Cooldown de 30 frames (~1s) |
| `/jifrex/presence` | float 0/1 | 0 ó 1 | Persona detectada (blob > `area_threshold`). Controla decay de partículas |
| `/jifrex/flow_mean` | float | 0.0–3.0 | Magnitud promedio del optical flow en px/frame. Escala halo y velocidad de partículas |
| `/jifrex/motion_ratio` | float | 0.0–1.0 | Fracción de píxeles con movimiento > 1px. Escala densidad de glitch y partículas |
| `/jifrex/blob_area` | int | 0–N | Tamaño del blob más grande en píxeles. Útil para debug con un Text TOP |
| `/jifrex/noise_level` | float | 0.0–1.0 | Ratio de blobs pequeños / blob mayor. Sube cuando hay ruido de fondo o personas múltiples |

**Cómo monitorear en TD sin interrumpir el show:**
Agregar un `Text TOP` conectado a un `Null CHOP` que lea los valores del `osc_in` DAT.
Posicionarlo fuera del rango de proyección — visible solo en el monitor del operador.

*Ver `shaders/td_osc_to_uniforms.py` para la lógica completa de mapeo OSC → uniforms.*
