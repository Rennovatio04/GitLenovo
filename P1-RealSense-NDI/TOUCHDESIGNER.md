# TouchDesigner — Guía de Operación Completa
## P1 · RealSense D435i + NDI · Aún Sorprendo · JIFREX

---

## Antes de abrir TouchDesigner

### Máquinas involucradas

| Máquina | Rol | Sistema |
|---------|-----|---------|
| **MSI Katana GF66** | Captura + segmentación + emisión | Windows 11 |
| **MacBook Pro M3 Max** | TouchDesigner + proyección | macOS |

Las dos máquinas deben estar en la **misma red LAN** (mismo switch o router).  
Recomendado: cable Ethernet directo o switch gigabit — no Wi-Fi en producción.

### En la MSI (hacer primero, antes de abrir TD)

```powershell
# 1. Editar config.py — poner la IP real del Mac
notepad C:\Users\USUARIO\GitLenovo\P1-RealSense-NDI\config.py
# Cambiar: OSC_HOST = "192.168.1.XX"  → IP real del Mac

# 2. Activar entorno
cd C:\Users\USUARIO\GitLenovo\P1-RealSense-NDI
.\venv\Scripts\Activate.ps1

# 3. Terminal A — MCP bridge (ajuste en vivo, opcional)
python mcp_bridge.py

# 4. Terminal B — Pipeline principal
python webcam_runtime.py
```

Verificar que el log aparece en Terminal B:
```
[      ]  30.0 fps | blob=    0px | flow=0.000 | motion=0.000 | cooldown= 0
```

### Verificar NDI activo (en el Mac)

Instalar **NDI Tools** (gratuito, de Vizrt) en el Mac.  
Abrir **NDI Video Monitor** → debe aparecer `JIFREX-MSI-MASK` en la lista de fuentes.  
Si no aparece: el firewall de Windows está bloqueando NDI → permitir en Windows Defender.

---

## Abrir TouchDesigner en el Mac

1. Abrir TouchDesigner (versión 2023.x o superior)
2. Menú **File → New** → proyecto en blanco
3. Guardar como: `P1_JIFREX_Aun_Sorprendo.toe` en el directorio del proyecto

---

## Paso 1 — Crear el OSC In DAT

> Recibe las métricas de Python (flow_mean, trigger, presence, etc.)

1. En el **Network Editor**, click derecho → **Add Operator** → pestaña **DAT** → `OSC In`
2. Renombrar el operador: doble clic en el nombre → escribir `osc_in`
3. En el panel de parámetros (derecha):
   - **Protocol**: UDP
   - **Port**: `9000`
   - **Local Address**: (dejar vacío — escucha en todas las interfaces)
   - **Active**: ON (checkbox)
4. Verificar: cuando Python está corriendo en MSI, la tabla del DAT debe mostrar filas con `/jifrex/flow_mean`, `/jifrex/trigger`, etc.

---

## Paso 2 — Crear el Script DAT

> Distribuye los mensajes OSC a los uniforms de los shaders

1. Click derecho → **DAT** → `Script`
2. Renombrar: `osc_to_uniforms`
3. Conectar: arrastrar el cable de salida de `osc_in` → entrada de `osc_to_uniforms`
4. En parámetros del Script DAT:
   - **Execute**: `Table Change`
5. Click en el ícono de lápiz del Script DAT para abrir el editor
6. Borrar el contenido por defecto
7. Copiar y pegar el contenido completo de `shaders/td_osc_to_uniforms.py`
8. Cerrar el editor — se guarda automáticamente

---

## Paso 3 — Crear el NDI In TOP

> Recibe la máscara binaria desde MSI (~8 ms de latencia en LAN)

1. Click derecho → **TOP** → `NDI In`
2. Renombrar: `ndi_mask`
3. En parámetros:
   - **Source Name**: `JIFREX-MSI-MASK`
   - **Resolution**: `1280 x 720` (o `Use Source`)
4. Verificar: el TOP debe mostrar la silueta en blanco sobre negro
5. Si aparece negro: MSI no está enviando NDI, o el nombre de fuente no coincide

---

## Paso 4 — Crear el Null TOP de máscara limpia

> Copia de la máscara para dar como input[1]/input[2] a los shaders que la necesitan

1. Click derecho → **TOP** → `Null`
2. Renombrar: `mask_orig`
3. Conectar: cable de salida de `ndi_mask` → entrada de `mask_orig`

---

## Paso 5 — Crear el GLSL TOP: glsl_halo

> Shader 1: borde + halo proporcional al movimiento

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_halo`  ← **el nombre DEBE ser exactamente este**
3. Conectar: cable de `ndi_mask` → entrada [0] de `glsl_halo`
4. En parámetros del GLSL TOP:
   - Pestaña **TOP** → **Pixel Shader** → **File**: click en carpeta → navegar a `shaders/halo_glow.glsl`
   - Activar **File Active**: ON
5. Pestaña **Vectors 1** — agregar los uniforms:

   | Nombre | value0 | value1 | value2 | value3 |
   |--------|--------|--------|--------|--------|
   | `uniform0` | `uFlowMean = 0.0` | `uTime = 0.0` | — | — |

   En la práctica en TD: en la sección **Vectors 1**, hacer clic en el `+` para agregar parámetros:
   - **Par Name**: `uniform0` → **Uniform Name**: `uFlowMean` → value0 = `0`
   - **Par Name**: `uniform1` → **Uniform Name**: `uTime` → value0 = `0`

   > Los valores se actualizarán automáticamente desde `osc_to_uniforms` cada frame.

---

## Paso 6 — Crear el GLSL TOP: glsl_glitch

> Shader 2: RGB split + UV warp, activo solo en trigger

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_glitch`  ← **exactamente este nombre**
3. Conectar:
   - Entrada [0]: cable de salida de `glsl_halo`
   - Entrada [1]: cable de salida de `mask_orig`
4. En parámetros:
   - **Pixel Shader File**: `shaders/glitch.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):
   - `uTrigger`     → value0 = `0`
   - `uMotionRatio` → value0 = `0`
   - `uTime`        → value0 = `0`

---

## Paso 7 — Crear el Feedback TOP

> Acumula la estela de partículas entre frames

1. Click derecho → **TOP** → `Feedback`
2. Renombrar: `feedback_loop`
3. En parámetros:
   - **Target TOP**: `glsl_particles` (escribir el nombre — se conectará después)
   - **Opacity**: `0.92` (punto de partida — calibrar en sala)

---

## Paso 8 — Crear el GLSL TOP: glsl_particles

> Shader 3: partículas del borde + estela persistente (Feedback)

1. Click derecho → **TOP** → `GLSL`
2. Renombrar: `glsl_particles`  ← **exactamente este nombre**
3. Conectar:
   - Entrada [0]: cable de salida de `glsl_glitch`
   - Entrada [1]: cable de salida de `feedback_loop`
   - Entrada [2]: cable de salida de `mask_orig`
4. En parámetros:
   - **Pixel Shader File**: `shaders/feedback_particles.glsl`
   - **File Active**: ON
5. Uniforms (Vectors 1):
   - `uFlowMean`    → value0 = `0`
   - `uMotionRatio` → value0 = `0`
   - `uPresence`    → value0 = `0`
   - `uTime`        → value0 = `0`

---

## Paso 9 — Cerrar el loop del Feedback TOP

El Feedback TOP necesita saber qué TOP leer del frame anterior:

1. Seleccionar `feedback_loop`
2. Parámetro **Target TOP**: escribir `glsl_particles`
3. Ahora el loop está cerrado: `glsl_particles` → `feedback_loop` → `glsl_particles [input 1]`

---

## Paso 10 — Level TOP y Out TOP

1. Click derecho → **TOP** → `Level`
   - Renombrar: `level_final`
   - Conectar: cable de `glsl_particles` → entrada de `level_final`
   - **Brightness**: `1.0` (ajustar en sala según la luminancia del proyector)
   - **Contrast**: `1.05`

2. Click derecho → **TOP** → `Out`
   - Renombrar: `out_proyector`
   - Conectar: cable de `level_final` → entrada de `out_proyector`
   - En parámetros → **Output**: seleccionar la pantalla/proyector correspondiente

---

## Paso 11 — Configurar salida de proyectores

> 2× Epson PowerLite 5510 conectados via HDBaseT Cat6A

1. Menú **Dialogs → Window Placement**
2. Agregar una ventana de salida por cada proyector:
   - **Resolution**: `1920 × 1200` (WUXGA — Epson 5510)
   - **Display**: seleccionar el display del proyector correspondiente
   - **TOP**: `out_proyector`
3. Si los proyectores son dos pantallas extendidas, crear dos `Out TOP` con el mismo input

---

## Paso 12 — Folder DAT para hot-reload de shaders

> Los shaders se recargan automáticamente al guardar el .glsl

1. Click derecho → **DAT** → `Folder`
2. Renombrar: `shader_folder`
3. Parámetros:
   - **Folder**: ruta absoluta a `P1-RealSense-NDI/shaders/`
   - **Include Extensions**: `glsl`
4. En cada GLSL TOP, la ruta ya está configurada con `File Active: ON` — esto solo centraliza la referencia

---

## Diagrama completo de conexiones

```
[MSI: webcam_runtime.py]
    │ NDI (~8ms LAN)         │ OSC UDP :9000 (<2ms LAN)
    ▼                        ▼
[ndi_mask: NDI In TOP]    [osc_in: OSC In DAT]
    │                        │
    ├──→ [mask_orig: Null]   └──→ [osc_to_uniforms: Script DAT]
    │        │                         │ (actualiza par.value en cada shader)
    │        │                         ▼
    └──→ [glsl_halo] ←── uniforms: uFlowMean, uTime
              │
         [glsl_glitch] ←── input[1]: mask_orig
              │             uniforms: uTrigger, uMotionRatio, uTime
              │
         [glsl_particles] ←── input[1]: feedback_loop
              │              ←── input[2]: mask_orig
              │               uniforms: uFlowMean, uMotionRatio, uPresence, uTime
              │
         [feedback_loop: Feedback TOP]  opacidad: 0.92
              │ (loop cerrado: Target TOP = glsl_particles)
              │
         [level_final: Level TOP]
              │
         [out_proyector: Out TOP]
              │
    2× Epson PowerLite 5510 via HDBaseT Cat6A
```

---

## Lista de verificación antes de la inauguración

- [ ] MSI: `webcam_runtime.py` corre sin errores, log muestra FPS
- [ ] NDI Monitor del Mac: `JIFREX-MSI-MASK` visible en la lista
- [ ] `ndi_mask` TOP: muestra silueta (no negro)
- [ ] `osc_in` DAT: tabla tiene filas con `/jifrex/flow_mean`, etc.
- [ ] `osc_to_uniforms`: no muestra errores en la consola de TD
- [ ] `glsl_halo`: halo visible alrededor de la silueta
- [ ] `glsl_glitch`: glitch activo al mover bruscamente frente a la cámara
- [ ] `glsl_particles`: estela de partículas visible en el borde de la silueta
- [ ] `feedback_loop`: estela persiste 2–3 segundos tras el movimiento
- [ ] Proyectores: imagen correctamente keystone y posicionada en el piso
- [ ] Prueba de 8 horas continuas sin caída de FPS ni memory leak

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `ndi_mask` en negro | MSI no emite / firewall | Verificar `webcam_runtime.py`, permitir NDI en Windows Defender |
| `osc_in` sin datos | IP incorrecta en `config.py` | Verificar `OSC_HOST` en MSI apunta al Mac |
| Shader muestra negro | Path del .glsl incorrecto | Verificar `File` en GLSL TOP apunta a la ruta correcta |
| `glsl_particles` sin estela | `feedback_loop` no cerrado | Verificar `Target TOP = glsl_particles` en el Feedback TOP |
| Glitch muy frecuente | `flow_threshold` bajo | Subir `flow_threshold` en `mcp_bridge.py` vía OSC :9001 |
| Glitch nunca dispara | `flow_threshold` alto | Bajar `flow_threshold` vía MCP bridge |
| Halo irregular | Ruido en la máscara NDI | Compresión NDI — verificar ancho de banda de la red |

---

## Rutas OSC de referencia rápida

| Ruta | Tipo | Descripción |
|------|------|-------------|
| `/jifrex/trigger` | float 0/1 | Trigger anti-FP |
| `/jifrex/presence` | float 0/1 | Persona detectada |
| `/jifrex/flow_mean` | float 0–3 | Magnitud de movimiento |
| `/jifrex/motion_ratio` | float 0–1 | Fracción de píxeles en movimiento |
| `/jifrex/blob_area` | int | Tamaño del blob (píxeles) |
| `/jifrex/noise_level` | float | Ruido relativo |

*Ver `shaders/README_TouchDesigner.md` para tabla completa de uniforms por shader.*
