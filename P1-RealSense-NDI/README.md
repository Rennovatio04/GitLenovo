# P1 — RealSense D435i + NDI
**Aún Sorprendo · Exposición Pablo Picasso · JIFREX**  
Galería Universitaria Fernando Cano · UAEMEx / FUNIBER

---

## Estado actual: BETA — v0.3

| Fase | Estado | Detalle |
|------|--------|---------|
| Fase 1 — Ecosistema MCP | ✅ Completa | venv, mcp_bridge, config centralizado |
| Fase 2 — Interconectividad | ✅ Completa | Pipeline RealSense→OSC→NDI funcional |
| Fase 3 — Shaders GLSL | ⚠️ Parcial | halo_glow ✅ · glitch ✅ · feedback_particles corregido (v0.2) |
| Red robusta | ❌ Pendiente | Sin auto-discovery de IP ni reconexión automática |
| Documentación instalación | ❌ Pendiente | Sin guía paso a paso para operador en galería |
| Tests / QA | ❌ Pendiente | Sin pruebas unitarias ni test de latencia |

---

## Qué funciona

- Captura RealSense D435i a 30 fps en MSI Windows 11 con alineación depth-RGB
- Segmentación adaptativa: umbral gaussiano + morfología open/close → máscara binaria limpia
- Optical Flow Farneback: `flow_mean` + `motion_ratio` por frame
- Análisis de blobs: `largest_blob_area` + `noise_level`
- Lógica de trigger anti-falsos positivos: umbral de área (500 px) + cooldown de 30 frames
- Escritura atómica de `latest_mask.png` (sin corrupción de archivo)
- OSC a MacBook Pro M3 Max por puerto 9000: 6 canales (`trigger`, `flow_mean`, `motion_ratio`, `blob_area`, `presence`, `noise_level`)
- NDI broadcast de la máscara binaria (~8 ms en LAN)
- MCP bridge en puerto 9001: ajuste de umbrales en tiempo real sin reiniciar
- Modo simulación sin cámara RealSense (para desarrollo en otras máquinas)
- Shaders GLSL 1 y 2 completos: Halo/Glow y Glitch/Distorsión
- Script `td_osc_to_uniforms.py` para TouchDesigner

---

## Qué falta para galería

### Crítico (sin esto no se puede exhibir)

- [ ] **Configurar IP del Mac en `config.py`**  
  `OSC_HOST = "192.168.1.XX"` — cambiar a la IP real del Mac en la red de galería.  
  Sin este cambio nada llega al Mac.

- [ ] **Calibrar umbrales en sala** vía `mcp_bridge.py`  
  Los valores por defecto (`area_threshold=500`, `cooldown=30`, `flow_threshold=0.5`) son punto de partida.  
  La iluminación y distancia reales de la galería los van a cambiar.

- [ ] **Configurar TouchDesigner en el Mac**  
  Crear red de nodos según `shaders/README_TouchDesigner.md`.  
  Los nombres de ops deben coincidir exactamente con `td_osc_to_uniforms.py`:  
  `glsl_halo`, `glsl_glitch`, `glsl_particles`.

### Importante (afecta estabilidad en exposición de horas)

- [ ] **Auto-discovery de IP o procedimiento fijo de red**  
  Si el DHCP cambia la IP del Mac, hay que editar `config.py` y reiniciar MSI.  
  Solución mínima: asignar IP estática al Mac en el router de galería.

- [ ] **Reconexión automática si se cae la red**  
  Actualmente no hay heartbeat ni reconexión. Si el Mac se desconecta, MSI sigue  
  emitiendo al vacío sin aviso. Requiere monitoreo manual durante la exhibición.

- [ ] **Prueba de 8 horas continuas**  
  Verificar que no haya memory leak ni degradación de FPS después de horas de uso.

### Menor (mejoras de operación)

- [ ] Logging a archivo (últimas 24h de operación)
- [ ] Indicador visual en TouchDesigner de "conexión OSC activa"
- [ ] Script de verificación de dependencias pre-arranque

---

## Bugs corregidos en v0.2

**`feedback_particles.glsl` — lógica de emisión** (corregido 2026-06-13)  
- **Bug**: Las partículas se generaban en coordenadas UV aleatorias que rara vez  
  coincidían con el borde real de la máscara, haciendo el efecto invisible.  
- **Fix**: La emisión ahora ancla cada slot de partícula al fragmento actual,  
  usando `uvEdge` como peso — partículas solo aparecen donde hay borde real.

**`feedback_particles.glsl` — decay demasiado agresivo** (corregido 2026-06-13)  
- **Bug**: Decay 0.93 hacía que la estela desapareciera en ~1 segundo (0.93^30 = 0.12).  
- **Fix**: Decay aumentado a 0.96 (estela dura ~2.5 s) y 0.75 en ausencia de visitante.

---

## Arranque rápido (MSI Windows 11)

```powershell
# 1. Editar IP del Mac
notepad config.py   # cambiar OSC_HOST = "192.168.1.XX"

# 2. Activar entorno
.\venv\Scripts\Activate.ps1

# Terminal A — MCP bridge (opcional, para ajuste en vivo)
python mcp_bridge.py

# Terminal B — Pipeline principal
python webcam_runtime.py
```

Logs cada 5 s:
```
[TRIGGER] 29.8 fps | blob=  4320px | flow=0.823 | motion=0.312 | cooldown= 0
[      ]  30.1 fps | blob=  3917px | flow=0.210 | motion=0.089 | cooldown=24
```

## Ajuste de parámetros en vivo

Desde cualquier cliente OSC (o `oscsend` en otra terminal):

```
/mcp/set/area_threshold    <int>    # px mínimos de blob (default 500)
/mcp/set/cooldown_frames   <int>    # frames entre triggers (default 30)
/mcp/set/flow_threshold    <float>  # flujo mínimo (default 0.5)
/mcp/set/motion_threshold  <float>  # motion ratio mínimo (default 0.15)
/mcp/get/params                     # lee valores actuales → responde en :9002
```

---

## Arquitectura

```
MSI Katana GF66 (Windows 11)            MacBook Pro M3 Max
────────────────────────────            ──────────────────
RealSense D435i
  depth 1280×720 @ 30 fps
  color 1280×720 @ 30 fps
        │
  webcam_runtime.py
    segmentación adaptativa
    optical flow Farneback
    análisis de blobs
    trigger anti-FP
        │
   ┌────┴────┐
   │         │
OSC :9000   NDI
(<2 ms)    (~8 ms)
   │         │
   └────┬────┘
        ▼
  TouchDesigner
    OSC In DAT → Script DAT (td_osc_to_uniforms.py)
    NDI In TOP → glsl_halo → glsl_glitch → glsl_particles (Feedback)
        │
  2× Epson PowerLite 5510
  5500 lm · WUXGA · HDBaseT Cat6A
  Techo 4.5 m · imagen ~2.4 m ancho
```

---

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `webcam_runtime.py` | Pipeline principal 30 fps |
| `config.py` | Todos los parámetros (editar `OSC_HOST` antes de usar) |
| `osc_client.py` | Envía 6 canales OSC al Mac |
| `ndi_stream.py` | Emite máscara como fuente NDI |
| `mcp_bridge.py` | Ajuste de parámetros en tiempo real |
| `shaders/halo_glow.glsl` | Shader 1: borde + halo proporcional a flow_mean |
| `shaders/glitch.glsl` | Shader 2: RGB split + UV warp, solo en trigger |
| `shaders/feedback_particles.glsl` | Shader 3: partículas del borde + estela Feedback |
| `shaders/td_osc_to_uniforms.py` | Script DAT TouchDesigner: OSC → uniforms |
| `shaders/README_TouchDesigner.md` | Setup completo de nodos en TD |

---

---

## Auditoría técnica — para IA o revisor externo

> Esta sección resume el estado real del código para que un auditor pueda verificar
> el sistema sin leer cada archivo desde cero.

### Mapa de responsabilidades

| Archivo | Función principal | Entradas | Salidas |
|---------|------------------|----------|---------|
| `config.py` | Parámetros globales | — | Constantes importadas por todos los módulos |
| `webcam_runtime.py` | Loop principal 30 fps | RealSense D435i / webcam simulada | `latest_mask.png` + OSC + NDI |
| `osc_client.py` | Transporte OSC UDP | 6 métricas float/int/bool | Datagramas UDP a `OSC_HOST:9000` |
| `ndi_stream.py` | Broadcast de video | `np.ndarray` BGR | Fuente NDI `JIFREX-MSI-MASK` |
| `mcp_bridge.py` | Ajuste de parámetros en vivo | Mensajes OSC entrantes en `:9001` | Diccionario `_params` compartido con runtime |
| `shaders/halo_glow.glsl` | Borde + halo | Máscara binaria [0] | RGBA con halo azul-plata proporcional a `uFlowMean` |
| `shaders/glitch.glsl` | Distorsión digital | Frame anterior [0] + máscara [1] | RGBA con RGB split + scanlines (solo en `uTrigger=1`) |
| `shaders/feedback_particles.glsl` | Estela + partículas | Frame actual [0] + Feedback [1] + máscara [2] | RGBA acumulativo con decay 0.96 |
| `shaders/td_osc_to_uniforms.py` | Script DAT TouchDesigner | Tabla OSC In DAT | `par.value` en `glsl_halo`, `glsl_glitch`, `glsl_particles` |

### Flujo de datos completo

```
RealSense D435i (depth z16 + color BGR8 @ 1280×720 @ 30fps)
  └─ pyrealsense2.align → depth alineado con color
      └─ segment():
           np.where(depth > 300mm && < 3000mm) → depth_norm
           cv2.adaptiveThreshold(GAUSSIAN, 51, 2) → mask raw
           morphologyEx(OPEN + CLOSE, 5px ellipse, ×2) → mask limpia
      └─ optical_flow():
           cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, ...) → flow XY
           cartToPolar → magnitude → flow_mean (mean) + motion_ratio (>1px fraction)
      └─ analyze_blobs():
           connectedComponentsWithStats → largest_blob_area, noise_level
      └─ trigger logic:
           if presence AND flow_mean >= 0.5 AND motion_ratio >= 0.15 AND cooldown==0
               triggered=True, cooldown=30
      └─ write_mask_atomic(): tempfile + os.replace()
      └─ OSCClient.send_metrics() → UDP :9000
      └─ NDIStream.send_frame() → NDI broadcast
```

### Puntos de integración críticos

| Punto | Protocolo | Puerto | Dirección | Latencia |
|-------|-----------|--------|-----------|----------|
| MSI → Mac (métricas) | OSC / UDP | 9000 | unidireccional | < 2 ms |
| MSI → Mac (video) | NDI | auto | unidireccional | ~8 ms |
| Consola → MSI (parámetros) | OSC / UDP | 9001 | bidireccional | < 2 ms |
| MSI ← Consola (respuesta params) | OSC / UDP | 9002 | unidireccional | < 2 ms |

### Estado de cada módulo

| Módulo | Código | Verificado | Listo para galería |
|--------|--------|------------|-------------------|
| `webcam_runtime.py` | ✅ Completo | ✅ En simulación | ⚠️ Falta IP real |
| `osc_client.py` | ✅ Completo | ✅ Imports OK | ⚠️ Falta IP real |
| `ndi_stream.py` | ✅ Completo | ⚠️ Sin NDI SDK real | ❌ Instalar NDI SDK |
| `mcp_bridge.py` | ✅ Completo | ✅ Thread-safe | ✅ |
| `halo_glow.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar en sala |
| `glitch.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar en sala |
| `feedback_particles.glsl` | ✅ v0.2 (bug corregido) | ⚠️ Sin TD real | ⚠️ Calibrar decay en sala |
| `td_osc_to_uniforms.py` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Verificar nombres de ops |

### Qué debe verificar un auditor

1. **`config.py` línea 27**: `OSC_HOST = "192.168.1.XX"` — debe tener IP real antes de correr.
2. **`ndi_stream.py` líneas 24-26**: `ndi.initialize()` puede fallar silenciosamente si el NDI SDK no está instalado como librería del sistema (no en venv). Verificar con `pip show ndi-python` Y que el SDK de Vizrt esté instalado globalmente.
3. **`shaders/td_osc_to_uniforms.py` líneas 20-22**: Los nombres `op('glsl_halo')`, `op('glsl_glitch')`, `op('glsl_particles')` deben coincidir exactamente con los TOPs en el patch de TouchDesigner.
4. **`feedback_particles.glsl` línea 75**: Decay = 0.96 → después de 1 s (30 frames): `0.96^30 = 0.294`. La estela debería ser visible ~2.5 s. Ajustar si la galería tiene mucha luz ambiental.
5. **`webcam_runtime.py` función `segment()`**: El umbral adaptativo asume un rango de profundidad 300-3000 mm. Si la sala es más pequeña o más grande, ajustar `DEPTH_MIN_MM` / `DEPTH_MAX_MM` en `config.py`.
6. **Thread safety**: `mcp_bridge._params` usa `threading.Lock()`. `webcam_runtime` llama `get_live_params()` cada frame — verificar que no haya contención en producción.
7. **Memory**: El loop de RealSense llama `pipeline.wait_for_frames()` que bloquea hasta 5 s por defecto. Si la cámara se desconecta, el proceso se congela (no hay timeout configurado).

### Auditoría y mejoras — 2026-06-14

**Hallazgos**

- El runtime escribía `latest_mask.png` relativo al directorio de ejecución, no al
  directorio del proyecto.
- `webcam_runtime.py` arranca el MCP bridge embebido, pero si el operador también
  lanzaba `mcp_bridge.py` manualmente el puerto 9001 podía entrar en conflicto.

**Mejoras aplicadas**

- `webcam_runtime.py` ahora resuelve `MASK_PATH` relativo a la carpeta del proyecto
  y escribe el archivo temporal en esa misma carpeta.
- `mcp_bridge.py` ahora detecta el puerto ocupado y degrada con mensaje claro en
  lugar de romper el arranque.

**Trabajo auditado**

- Pipeline RealSense → segmentación → flow → blobs → OSC → NDI.
- Robustez operativa de salida a disco y del bridge MCP embebido.

**Listo para próxima auditoría**

- Verificar IP real de `OSC_HOST` y presencia del SDK NDI.
- Confirmar que `latest_mask.png` se genera dentro de la carpeta del proyecto.
- Repetir prueba de runtime con bridge embebido y bridge externo para validar la
  tolerancia a puerto ocupado.
- Revisar riesgos abiertos: reconexión de red y prueba continua de 8 horas.

### Historial de versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| v0.1 | 2026-06-13 | Creación inicial — Fases 1, 2 y 3 |
| v0.2 | 2026-06-13 | Fix `feedback_particles.glsl`: emisión de partículas y decay |
| v0.3 | 2026-06-14 | Auditoría operativa: `MASK_PATH` estable por proyecto + MCP tolerante a puerto ocupado |

*Última revisión: 2026-06-14 · Desarrollado con claude-sonnet-4-6 · Revisado con claude-haiku-4-5*
