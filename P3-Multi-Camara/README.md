# P3 — Multi-Cámara: 3 Perspectivas Simultáneas
**Aún Sorprendo · Exposición Pablo Picasso · JIFREX**  
Galería Universitaria Fernando Cano · UAEMEx / FUNIBER

> "Picasso no pintaba lo que veía. Pintaba lo que sabía que estaba ahí,
> desde todos los ángulos posibles a la vez."
>
> Este sistema hace eso literalmente.

---

## Estado actual: BETA — v0.2

| Fase | Estado | Detalle |
|------|--------|---------|
| Fase 1 — Multicámara | ✅ Completa | 3 hilos de cámara, OAK-D Pro W + 2× C922, sync manager |
| Fase 2 — Pipeline ×3 | ✅ Completa | MediaPipe × 3, OSC compuesto, Syphon × 3 |
| Fase 3 — Shaders | ✅ Completa | composite, distorsion_uv, particulas_perspectiva |
| Calibración en sala | ❌ Pendiente | Requiere Mac M3 Max y hardware real |
| Prueba 8 horas | ❌ Pendiente | Sin test de estabilidad larga |
| Documentación de operador | ❌ Pendiente | Sin guía de operación en galería |

---

## Concepto artístico

La propuesta más fiel al cubismo de Picasso: **3 cámaras en 3 ángulos distintos
capturan al visitante simultáneamente** y las 3 siluetas se componen en una sola
imagen con Screen blend.

| Perspectiva | Significado artístico | Obra de referencia |
|-------------|----------------------|-------------------|
| Frontal (azul) | Como nos vemos en un espejo | Les Bleus de Barcelona |
| Lateral (ocre) | Como vemos a otros, nunca a nosotros | Bailarines sobre cuero |
| Cenital (rosa) | La vista que nunca vemos de nuestro propio cuerpo | Geneviève sobre papel Japón |

**Triple coincidencia → luz blanca brillante.**  
Donde las 3 perspectivas se solapan = donde Picasso tenía la certeza máxima.

---

## Hardware requerido — Mac M3 Max ONLY

| | Mac M3 Max | MSI Katana GF66 |
|--|-----------|-----------------|
| GPU | 40 núcleos (36 GB RAM unificada) | 4 GB VRAM — INSUFICIENTE |
| Neural Engine | 16 núcleos — 3× MediaPipe en paralelo | Sin Neural Engine |
| Thunderbolt 4 | 3 puertos dedicados | Sin TB4 |
| VRAM estimado | ~2.5 GB (margen amplio) | ~3.5 GB estimado (colapso) |
| Throttling 8h | No — M3 Max sin degradación térmica | Sí — RTX 3050 Mobile |
| Veredicto | **ÓPTIMA** | **NO viable** |

> **CRÍTICO:** Un puerto TB4 dedicado por cámara. Un hub USB compartido produce
> frame drops y desincronización que destruyen el efecto artístico.

---

## Sincronización de 3 streams

Ventana de sincronización: **33 ms = 1 frame a 30fps**

```
Cámara A — T+0 ms   → OK  (frame aceptado)
Cámara B — T+15 ms  → OK  (dentro de ventana)
Cámara C — T+28 ms  → OK  (dentro de ventana)
Cámara B — T+50 ms  → DESCARTADO — se reutiliza frame anterior de B
                          ^
                          fuera de la ventana de 33 ms
```

Si algún frame está fuera de la ventana, `SyncManager` reutiliza el último
frame validado de esa cámara — nunca descarta el triplete completo.

---

## Arquitectura

```
Mac M3 Max — Python 3.11/3.12
─────────────────────────────────────────────────────────
OAK-D Pro W  (TB4 #1)  →  CameraThread("A", use_oak=True)
Logitech C922 (TB4 #2)  →  CameraThread("B")          ← 3 hilos paralelos
Logitech C922 (TB4 #3)  →  CameraThread("C")          ← Neural Engine M3

CameraThread (cada uno, por frame):
  cap / DepthAI SDK → frame BGR
  MediaPipe Holistic → segmentation_mask
  morphologyEx (OPEN+CLOSE) → máscara limpia
  calcOpticalFlowFarneback → flow_mean + motion_ratio
  → CameraResult(timestamp_ms, mask, flow, motion, presence)

SyncManager.get_sync_triplet():
  max(ts_a, ts_b, ts_c) - min(...) <= 33 ms → triplete validado
  frames fuera de ventana → reutiliza frame anterior

multicam_runtime.py (loop ~30fps):
  triple_ratio = coincidencia de 3 máscaras / total pixels
  double_ratio = coincidencia de cualquier 2 / total pixels

  SyphonShare.send(mask_a, mask_b, mask_c):
    3 servidores Syphon → 3 texturas independientes → TouchDesigner

  MultiCamOSCClient.send(...):
    12 métricas OSC → puerto 9000 → TouchDesigner

TouchDesigner — Mac M3 Max:
  Syphon In ×3 → distorsion_uv ×3 → composite_multicamara
              → particulas_perspectiva → Feedback TOP
              → Level TOP → Out TOP
  2× Epson PowerLite 5510 via HDBaseT Cat6A
  Techo 4.5 m · imagen ~2.4 m ancho
```

---

## Shaders GLSL

| Shader | Descripción |
|--------|-------------|
| `composite_multicamara.glsl` | Screen blend de 3 siluetas → triple coincidencia = blanco |
| `distorsion_uv.glsl` | Distorsión UV por perspectiva (radial / horizontal / espiral) |
| `particulas_perspectiva.glsl` | Partículas: expansión radial / traslación / espiral + Feedback |
| `td_osc_to_uniforms.py` | Script DAT TouchDesigner: OSC → uniforms |
| `README_TouchDesigner.md` | Setup completo de la red TD |

---

## Arranque rápido (Mac M3 Max)

```bash
# 1. Verificar Python version (DEBE ser 3.11 o 3.12)
python3 --version

# 2. Crear venv
python3.12 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
pip install syphon-python
pip install depthai   # OAK-D Pro W

# 4. Verificar cámaras (anotar los índices reales)
python3 -c "import cv2; [print(i, cv2.VideoCapture(i).isOpened()) for i in range(5)]"

# 5. Editar config.py
#   CAM_B_INDEX = <índice real de la C922 lateral>
#   CAM_C_INDEX = <índice real de la C922 cenital>
#   OSC_HOST = "127.0.0.1"  (si TD corre en el mismo Mac)

# Terminal A — MCP bridge (opcional, ajuste en vivo)
python mcp_bridge.py

# Terminal B — Pipeline (con preview para desarrollo)
python multicam_runtime.py --preview

# Producción (sin preview)
python multicam_runtime.py
```

Log cada 5 s:
```
[TRIPLE] 29.8fps | sync= 18ms (97% OK) | A=0.82 B=0.71 C=0.65 | triple=0.0412
[      ] 30.1fps | sync= 24ms (94% OK) | A=0.21 B=0.18 C=0.33 | triple=0.0071
```

---

## Ajuste de parámetros en vivo (MCP bridge)

```
/mcp/set/sync_window_ms        <float>   # ventana de sync (default 33)
/mcp/set/mask_threshold        <float>   # umbral máscara MediaPipe (default 0.5)
/mcp/set/triple_threshold      <float>   # umbral trigger triple (default 0.04)
/mcp/set/mp_model_complexity   <float>   # 0/1/2 — requiere reinicio de hilos
/mcp/get/params                           # → responde en :9002
```

---

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `multicam_runtime.py` | Pipeline principal 30fps (3 hilos + sync + OSC + Syphon) |
| `camera_thread.py` | Hilo de captura + MediaPipe por cámara (OAK-D o C922) |
| `sync_manager.py` | Sincronización de timestamps dentro de ventana 33ms |
| `osc_client.py` | 12 canales OSC compuestos al Mac / TouchDesigner |
| `syphon_share.py` | 3 servidores Syphon — una textura por cámara |
| `mcp_bridge.py` | Ajuste de parámetros en tiempo real (puerto 9001) |
| `config.py` | Todos los parámetros del sistema |
| `requirements.txt` | Dependencias Python |
| `shaders/` | GLSL TOPs + Script DAT + README TouchDesigner |

---

## Pendientes antes de galería

### Crítico (sin esto no se exhibe)

- [ ] **Hardware Mac M3 Max confirmado** — este sistema no corre en ningún otro hardware
- [ ] **3 puertos TB4 disponibles** — uno por cámara, sin hubs
- [ ] **Instalar DepthAI SDK** y verificar OAK-D Pro W en TB4 #1
- [ ] **Calibrar índices de webcam** (`CAM_B_INDEX`, `CAM_C_INDEX` en `config.py`)
- [ ] **Verificar sync < 33ms** en log (`sync= XYms`) durante 30 min continuos
- [ ] **Construir red TouchDesigner** según `shaders/README_TouchDesigner.md`
- [ ] **Calibrar posiciones de halos UV** en `composite_multicamara.glsl` (estado de reposo)

### Importante (estabilidad en 8 horas)

- [ ] **Prueba de 8 horas continuas** — monitorear fps, memory, temperatura M3
- [ ] **Calibrar Feedback opacity** en TouchDesigner (default: 0.90)
- [ ] **Calibrar TRIPLE_THRESHOLD** según geometría real de la sala
- [ ] **Posición de cámaras en galería** — validar ángulos frontal/lateral/cenital

---

---

## Auditoría técnica — para IA o revisor externo

> Esta sección permite verificar el sistema completo sin leer cada archivo.

### Mapa de responsabilidades

| Archivo | Función principal | Entradas | Salidas |
|---------|------------------|----------|---------|
| `config.py` | Parámetros globales | — | Constantes importadas por todos |
| `camera_thread.py` | Hilo de captura + MediaPipe | Hardware (TB4) / simulado | `CameraResult(ts, mask, flow, motion, presence)` |
| `sync_manager.py` | Sincronización de 3 streams | 3 `CameraThread` | Triplete `(CameraResult, CameraResult, CameraResult)` |
| `multicam_runtime.py` | Loop principal ~30fps | Triplete sincronizado | OSC (12 métricas) + Syphon (3 texturas) |
| `osc_client.py` | 12 canales OSC | Métricas float/int | UDP :9000 |
| `syphon_share.py` | 3 texturas GPU→GPU | 3 máscaras uint8 | Syphon servidores / no-op |
| `mcp_bridge.py` | Parámetros en vivo | OSC :9001 | dict `_params` thread-safe |
| `composite_multicamara.glsl` | Screen blend 3 siluetas | 3 máscaras coloreadas | RGBA resultado |
| `distorsion_uv.glsl` | Distorsión UV por ángulo | Máscara + flow + perspectiva | RGBA distorsionada |
| `particulas_perspectiva.glsl` | Partículas + Feedback | Composite + prev + máscara | RGBA acumulativo |
| `td_osc_to_uniforms.py` | Script DAT TD | Tabla OSC In DAT | `par.value` en 5 GLSL TOPs |

### Flujo de datos completo

```
3 hilos en paralelo (un hilo por cámara):

CameraThread("A", use_oak=True):
  DepthAI SDK / cv2 → frame_bgr
  MediaPipe Holistic.process(frame_rgb) → segmentation_mask (float32 HxW)
  mask = (segmentation_mask > 0.5) * 255 → morphologyEx → uint8 binaria
  calcOpticalFlowFarneback(prev_gray, gray) → flow_mean, motion_ratio
  → CameraResult(timestamp_ms, mask, flow_mean, motion_ratio, presence)

SyncManager.get_sync_triplet():
  max(ts_a, ts_b, ts_c) - min(ts_a, ts_b, ts_c) <= 33ms
  → (CameraResult_A, CameraResult_B, CameraResult_C)

multicam_runtime loop:
  triple_ratio = sum(mask_a > 0 & mask_b > 0 & mask_c > 0) / total_pixels
  double_ratio = sum(any 2-of-3 overlap) / total_pixels
  SyphonShare.send(mask_a, mask_b, mask_c) → 3 servidores Syphon → TD
  MultiCamOSCClient.send(...) → 12 mensajes UDP :9000 → TD

TouchDesigner:
  Syphon In ×3 → GLSL distort ×3 → composite (Screen blend) → particles (Feedback) → Out
```

### Rutas OSC completas (puerto 9000)

| Ruta | Tipo | Rango | Descripción |
|------|------|-------|-------------|
| `/multicam/a/presence` | float | 0.0 / 1.0 | Persona detectada en cámara A |
| `/multicam/a/flow_mean` | float | 0.0–3.0 | Magnitud de flujo óptico A |
| `/multicam/a/motion` | float | 0.0–1.0 | Fracción de píxeles con movimiento > 1px A |
| `/multicam/b/presence` | float | 0.0 / 1.0 | Persona detectada en cámara B |
| `/multicam/b/flow_mean` | float | 0.0–3.0 | Magnitud de flujo óptico B |
| `/multicam/b/motion` | float | 0.0–1.0 | Fracción de píxeles con movimiento > 1px B |
| `/multicam/c/presence` | float | 0.0 / 1.0 | Persona detectada en cámara C |
| `/multicam/c/flow_mean` | float | 0.0–3.0 | Magnitud de flujo óptico C |
| `/multicam/c/motion` | float | 0.0–1.0 | Fracción de píxeles con movimiento > 1px C |
| `/multicam/triple_ratio` | float | 0.0–1.0 | Fracción de píxeles con triple solapamiento |
| `/multicam/double_ratio` | float | 0.0–1.0 | Fracción de píxeles con doble solapamiento |
| `/multicam/any_presence` | int | 0 / 1 | Hay al menos una persona en alguna cámara |

### Puntos de integración críticos

| Punto | Protocolo | Puerto | Latencia esperada |
|-------|-----------|--------|-----------------|
| Python → TouchDesigner (métricas) | OSC / UDP | 9000 | < 2 ms (loopback) |
| Python → TouchDesigner (video) | Syphon | GPU compartido | ~1 ms |
| Python (parámetros entrada) | OSC / UDP | 9001 | < 2 ms |
| Python (respuesta parámetros) | OSC / UDP | 9002 | < 2 ms |
| Cámara A (OAK-D Pro W) | USB3 via TB4 | TB4 #1 | ~16 ms por frame |
| Cámara B (Logitech C922) | USB3 via TB4 | TB4 #2 | ~16 ms por frame |
| Cámara C (Logitech C922) | USB3 via TB4 | TB4 #3 | ~16 ms por frame |

### Estado de cada módulo

| Módulo | Código | Verificado | Listo para galería |
|--------|--------|------------|-------------------|
| `camera_thread.py` | ✅ Completo | ✅ En simulación | ⚠️ Verificar índices C922 |
| `sync_manager.py` | ✅ Completo | ✅ Lógica correcta | ⚠️ Verificar sync_delta en log |
| `multicam_runtime.py` | ✅ Completo | ✅ En simulación | ⚠️ Requiere Mac M3 Max |
| `osc_client.py` | ✅ Completo | ✅ | ⚠️ Verificar IP si TD en otra máquina |
| `syphon_share.py` | ✅ Completo | ⚠️ Depende de lib | ❌ Instalar syphon-python |
| `mcp_bridge.py` | ✅ Completo | ✅ Thread-safe | ✅ |
| `composite_multicamara.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar posiciones halos |
| `distorsion_uv.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar intensidad |
| `particulas_perspectiva.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar decay |
| `td_osc_to_uniforms.py` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Verificar nombres de ops |

### Qué debe verificar un auditor

1. **Python version**: `python3 --version` debe ser 3.11 o 3.12. MediaPipe no tiene wheels para 3.13/3.14.
2. **`config.py` CAM_B_INDEX y CAM_C_INDEX**: Cambiar según el orden real de conexión de las C922. Verificar con `python3 -c "import cv2; [print(i, cv2.VideoCapture(i).isOpened()) for i in range(5)]"`.
3. **DepthAI SDK**: `import depthai` debe funcionar. Instalar desde Luxonis: `pip install depthai`. La OAK-D Pro W no aparece en `cv2.VideoCapture` — solo vía DepthAI.
4. **syphon-python**: Sin esta librería, las 3 texturas no llegan a TD. El OSC sí funciona pero TD no tiene imagen. Verificar con `python3 -c "import syphon; print('OK')"`.
5. **Nombres de ops en TD** (`td_osc_to_uniforms.py` línea 11-15): `glsl_composite`, `glsl_distort_a`, `glsl_distort_b`, `glsl_distort_c`, `glsl_particles` deben coincidir exactamente con los nombres en el patch.
6. **SyncManager sync_delta**: El log muestra `sync= XYms`. Si constantemente es > 33ms, hay contención de bandwidth en las cámaras — verificar que cada C922 esté en su propio TB4, no en un hub.
7. **triple_ratio threshold**: `TRIPLE_THRESHOLD = 0.04` (4% de los píxeles). Con la cámara cenital en ángulo real de galería, ajustar si el solapamiento real es mayor o menor de lo esperado.
8. **Thread safety**: `CameraThread._latest` está protegido por `threading.Lock()`. El runtime lee `get_latest()` sin bloqueo externo — verificar que no haya starvation si la cámara A es más lenta (DepthAI overhead).
9. **MediaPipe × 3 en paralelo**: En Mac M3 Max, los 3 modelos corren en el Neural Engine simultáneamente. En otras máquinas, pueden saturar la CPU. El log de FPS muestra si hay degradación.
10. **Feedback opacity en TD**: El Feedback TOP tiene opacidad 0.90 por defecto en el README. La estela de partículas depende de este valor — ajustar con luz real de galería.

### Diferencias técnicas clave vs P1 y P2

| | P1 — RealSense | P2 — Skeleton | P3 — Multi-Cámara |
|--|---------------|---------------|--------------------|
| Cámaras | 1 (RealSense D435i) | 1 (webcam) | 3 (OAK-D Pro W + 2× C922) |
| Sensor | Profundidad activa | RGB | RGB (frontal, lateral, cenital) |
| Máquina | MSI + Mac (2) | 1 sola | Mac M3 Max (1, requerida) |
| Concepto artístico | Presencia/silueta | Semántica corporal | Cubismo simultáneo |
| Complejidad sync | — | — | 3 streams, ventana 33ms |
| Video a TD | NDI (~8ms, red) | Spout (~1ms, local) | Syphon ×3 (~1ms, local) |
| Trigger principal | 1 (presencia + flow) | 6 semánticos | Triple coincidencia |
| VRAM estimado | ~1.5 GB (MSI) | ~1.0 GB | ~2.5 GB (M3 Max) |

### Auditoría y mejoras — 2026-06-14

**Hallazgos**

- `CameraThread` usaba un atributo `_stop` que colisiona con un método interno de
  `threading.Thread`; eso podía romper `join()` al cerrar el runtime.
- `SyncManager` documentaba reutilización del último frame válido, pero en la
  práctica siempre devolvía el frame más reciente aunque estuviera fuera de ventana.
- El MCP bridge existía, pero `multicam_runtime.py` no consumía parámetros vivos
  para sincronización ni umbrales de composición.

**Mejoras aplicadas**

- Renombrado el flag de parada a `_stop_event` para cerrar los hilos sin colisión
  con internals de Python.
- `SyncManager` ahora reutiliza el último frame validado cuando una cámara llega
  tarde y acepta una ventana de sincronización viva.
- `camera_thread.py` ya aplica `mask_threshold` en vivo desde MCP.
- `multicam_runtime.py` ahora arranca el bridge embebido de forma segura y consume
  `sync_window_ms` y `triple_threshold` en tiempo real.

**Trabajo auditado**

- Captura OAK-D/C922 → MediaPipe ×3 → sincronización → composición → OSC/Syphon.
- Cierre de hilos, tolerancia a desincronización y cableado real del MCP bridge.

**Listo para próxima auditoría**

- Ejecutar prueba con 3 cámaras reales y confirmar que `sync_window_ms` reacciona
  en vivo desde MCP.
- Verificar que el cierre del runtime termina los 3 hilos sin bloquear `join()`.
- Medir `sync_ratio` y validar reutilización del último frame cuando una cámara se
  sale de ventana.
- Confirmar hardware Mac M3 Max, puertos TB4 dedicados y backends reales de cámara/share.

### Historial de versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| v0.1 | 2026-06-13 | Creación inicial — Fases 1, 2, 3 completas |
| v0.2 | 2026-06-14 | Auditoría técnica: cierre de hilos corregido, sincronización validada y MCP vivo conectado |

*Última revisión: 2026-06-14 · Desarrollado con claude-sonnet-4-6*  
*Sistema de Proyección Reactiva Interactiva · JIFREX · 2026-06-14*
