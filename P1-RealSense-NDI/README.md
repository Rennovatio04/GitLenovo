# P1 — RealSense D435i + NDI
**Aún Sorprendo · Exposición Pablo Picasso · JIFREX**  
Galería Universitaria Fernando Cano · UAEMEx / FUNIBER

---

## Estado actual: BETA — v0.2

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

*Última revisión: 2026-06-13 · Revisado con claude-haiku-4-5*
