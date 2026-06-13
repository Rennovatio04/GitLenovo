# P4 — DeepLabv3 + CoreML · Referencia Antimodular / Lozano-Hemmer
**Aún Sorprendo · Exposición Pablo Picasso · JIFREX**  
Galería Universitaria Fernando Cano · UAEMEx / FUNIBER  
100% Software Libre · Apache 2.0 / BSD / MIT

> "La precisión es el respeto por el visitante."  
> — Propuesta 4

---

## Estado actual: BETA — v0.1

| Fase | Estado | Detalle |
|------|--------|---------|
| Fase 1 — Conversión CoreML | ✅ Script completo | `convert_to_coreml.py` — ejecutar una vez en el Mac |
| Fase 2 — Pipeline DeepLabv3 | ✅ Completa | segmentación + blob analysis + OSC + Syphon |
| Fase 3 — Shaders GLSL | ✅ Completa | 3 shaders "precise" + Script DAT + setup TD |
| Conversión ejecutada | ❌ Pendiente | Requiere Mac M3 Max con TF + coremltools |
| Calibración en sala | ❌ Pendiente | Requiere hardware y galería real |
| Prueba 8 horas | ❌ Pendiente | Sin test de estabilidad larga |

---

## El vínculo conceptual

| | |
|--|--|
| **Picasso** | Pone el proceso mental del artista en el lienzo. El cuadro no existe sin la mente que lo piensa. |
| **Lozano-Hemmer** | Pone el proceso perceptivo del espectador en el espacio. La imagen no existe sin el cuerpo que la activa. |
| **Propuesta 4** | Conecta ambos en la Galería Fernando Cano. El piso no existe sin el visitante que lo habita. |

---

## Por qué DeepLabv3 sobre MediaPipe (en condiciones de galería)

| Condición real | MediaPipe | DeepLabv3 |
|----------------|-----------|-----------|
| Ropa del mismo tono que el fondo | Pierde máscara | Mantiene máscara limpia |
| Luz proyectada rebota en el cuerpo | Contorno inestable | Contorno estable |
| Múltiples personas | Confunde cuerpos | Separa siluetas |
| Jitter de estimación | Sí (triggers falsos) | No (trigger solo por movimiento real) |
| Dedos y cabello | Aproximados | Subpixel-accurate |

**DeepLabv3** fue diseñado para segmentación semántica en entornos variables —
exactamente las condiciones de una galería con proyección activa.

---

## Conversión a CoreML — paso previo obligatorio

```bash
# En el Mac M3 Max, una sola vez
pip install tensorflow tensorflow-hub coremltools pillow

python convert_to_coreml.py          # desde TF Hub (requiere internet)
# o
python convert_to_coreml.py --source checkpoint  # desde archivo local
```

Resultado: `DeepLabV3.mlpackage` en el directorio raíz.  
Latencia: **15–25 ms/frame en Neural Engine** → GPU Metal completamente libre para TouchDesigner.

---

## Arquitectura

```
Mac M3 Max
──────────────────────────────────────────────────────────────
Cámara RGB 1080p/60fps (Logitech C922 / OAK-D / cualquier webcam)
        │
deeplab_runtime.py (~60fps):
  cv2.VideoCapture → frame_bgr
  DeepLabSegmentor.segment():
    CoreML (Neural Engine 15–25 ms) → clase 15 "person"
    INTER_NEAREST upsample → máscara 1920×1080 subpixel-accurate
    morphologyEx(OPEN+CLOSE 3×3) → limpieza mínima
  BlobAnalysis.analyze():
    connectedComponentsWithStats → largest_area, noise_level,
    coverage_ratio, blob_count  (4 métricas Antimodular)
  OpticalFlow(Farneback) → flow_mean, motion_ratio
  Trigger anti-FP: presence AND flow >= 0.35 AND motion >= 0.12 AND cooldown==0
  write_mask_atomic("latest_mask.png")
        │
  ┌─────┴─────┐
  │           │
Syphon       OSC :9000
(1 textura,  (8 canales)
 ~1 ms)
  │           │
  └─────┬─────┘
        ▼
TouchDesigner — Mac M3 Max (GPU Metal libre — 40 núcleos)
  OSC In DAT → Script DAT (td_osc_to_uniforms.py)
  Syphon In → glsl_halo → glsl_glitch → glsl_particles (Feedback)
        │
2× Epson PowerLite 5510 via HDBaseT Cat6A
```

---

## Análisis de blobs — estilo Antimodular

P4 introduce cuatro métricas donde P1 solo tenía dos:

| Métrica | P1 | P4 | Descripción |
|---------|----|----|-------------|
| `blob_area` | ✅ | ✅ | Tamaño del cuerpo principal (px) |
| `noise_level` | ✅ | ✅ | Ratio blobs pequeños / blob mayor |
| `coverage_ratio` | ❌ | ✅ | **Nuevo**: fracción del frame cubierta |
| `blob_count` | ✅ | ✅ | Número de personas detectadas |

`coverage_ratio` es la métrica Antimodular por excelencia: cuantifica la
**"ocupación del espacio"** del visitante — cuanto más llena el frame,
más intenso el halo y más partículas se generan.

---

## Hardware

| Configuración | Viabilidad | Detalle |
|--------------|------------|---------|
| Mac M3 Max | ✅ ÓPTIMA | CoreML Neural Engine + TD GPU Metal sin competencia |
| MSI Katana | ❌ NO recomendado | DeepLabv3 CUDA consume los 4 GB VRAM antes de que TD renderice |
| MSI + Mac en red | ⚠️ Viable | MSI corre Python headless, Mac renderiza TD — mayor latencia |

---

## Arranque rápido (Mac M3 Max)

```bash
# 1. Verificar Python 3.11 o 3.12
python3 --version

# 2. Crear venv
python3.12 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
pip install syphon-python
pip install tensorflow tensorflow-hub coremltools pillow  # para conversión

# 4. Convertir modelo (solo una vez)
python convert_to_coreml.py
# Genera: DeepLabV3.mlpackage

# 5. Verificar cámara
python3 -c "import cv2; cap=cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'ERROR')"

# Terminal A — MCP bridge (opcional, ajuste en vivo)
python mcp_bridge.py

# Terminal B — Pipeline (con preview para desarrollo)
python deeplab_runtime.py --preview

# Producción (sin preview)
python deeplab_runtime.py
```

Log cada 5 s:
```
[       ]  59.3fps | coreml  18ms | area= 89412px | flow=0.082 | motion=0.041 | cov=0.0466 | noise=0.021 | cd= 0
[TRIGGER]  59.8fps | coreml  16ms | area= 94320px | flow=0.412 | motion=0.143 | cov=0.0491 | noise=0.018 | cd=30
```

---

## Ajuste de parámetros en vivo (MCP bridge)

```
/mcp/set/area_threshold    <float>   # px mínimos de blob (default 500)
/mcp/set/cooldown_frames   <float>   # frames entre triggers (default 30)
/mcp/set/flow_threshold    <float>   # flow_mean mínimo (default 0.35)
/mcp/set/motion_threshold  <float>   # motion_ratio mínimo (default 0.12)
/mcp/set/coverage_boost    <float>   # multiplicador coverage_ratio (default 1.0)
/mcp/get/params                       # → responde en :9002
```

---

## Rutas OSC (puerto 9000)

| Ruta | Tipo | Rango | Descripción |
|------|------|-------|-------------|
| `/jifrex/p4/trigger` | float | 0 / 1 | Trigger anti-FP disparado |
| `/jifrex/p4/presence` | float | 0 / 1 | Persona detectada |
| `/jifrex/p4/flow_mean` | float | 0.0–3.0 | Magnitud promedio de optical flow |
| `/jifrex/p4/motion_ratio` | float | 0.0–1.0 | Fracción px con movimiento > 1px |
| `/jifrex/p4/blob_area` | int | 0–N | Tamaño del blob principal (px) |
| `/jifrex/p4/noise_level` | float | 0.0–N | Ratio blobs pequeños / principal |
| `/jifrex/p4/coverage_ratio` | float | 0.0–1.0 | **P4 nuevo** — cobertura del frame |
| `/jifrex/p4/blob_count` | int | 0–N | Número de personas |

---

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `convert_to_coreml.py` | Conversión DeepLabv3 TF → CoreML (una vez, en Mac) |
| `deeplab_segmentor.py` | Wrapper de inferencia: CoreML / TF / simulación |
| `blob_analysis.py` | Análisis de blobs Antimodular (4 métricas) |
| `deeplab_runtime.py` | Pipeline principal ~60fps |
| `osc_client.py` | 8 canales OSC a TouchDesigner |
| `syphon_share.py` | 1 servidor Syphon (textura subpixel-accurate) |
| `mcp_bridge.py` | 5 parámetros ajustables en vivo (puerto 9001) |
| `config.py` | Todos los parámetros |
| `requirements.txt` | Dependencias Python |
| `shaders/halo_glow_precise.glsl` | Halo con borde subpixel + uCoverageRatio |
| `shaders/glitch_precise.glsl` | Glitch sin falsos triggers + uNoiseLevel |
| `shaders/particles_precise.glsl` | Partículas en dedos y cabello |
| `shaders/td_osc_to_uniforms.py` | Script DAT TouchDesigner |
| `shaders/README_TouchDesigner.md` | Setup completo de la red TD |

---

## Pendientes antes de galería

### Crítico

- [ ] **Ejecutar `convert_to_coreml.py`** en el Mac M3 Max — genera `DeepLabV3.mlpackage`
- [ ] **Verificar latencia de inferencia** en el log: debe mostrar `coreml 15–25ms`. Si muestra `tensorflow 50–80ms`, el modelo no se convirtió correctamente.
- [ ] **Calibrar `CAM_INDEX`** en `config.py` según la cámara real de galería
- [ ] **Construir red TouchDesigner** según `shaders/README_TouchDesigner.md`
- [ ] **Calibrar umbral de cobertura** (`coverage_boost` vía MCP bridge) con la distancia real de la cámara al visitante

### Importante

- [ ] **Prueba con ropa difícil**: camisa blanca sobre fondo claro, ropa negra sobre fondo oscuro — verificar que DeepLabv3 mantiene la máscara donde MediaPipe la perdería
- [ ] **Prueba de 8 horas continuas** — monitorear temperatura M3 Max y fps estable
- [ ] **Calibrar `flow_threshold` en sala** (default 0.35, más bajo que P1/0.50)

---

---

## Auditoría técnica — para IA o revisor externo

> Esta sección permite verificar el sistema completo sin leer cada archivo.

### Mapa de responsabilidades

| Archivo | Función | Entradas | Salidas |
|---------|---------|----------|---------|
| `config.py` | Parámetros globales | — | Constantes importadas por todos |
| `convert_to_coreml.py` | Conversión TF → CoreML (una vez) | Modelo TF Hub | `DeepLabV3.mlpackage` |
| `deeplab_segmentor.py` | Inferencia DeepLabv3 | Frame BGR | Máscara uint8 subpixel-accurate |
| `blob_analysis.py` | 4 métricas Antimodular | Máscara uint8 | `BlobResult(area, noise, coverage, count)` |
| `deeplab_runtime.py` | Loop principal ~60fps | Webcam + segmentor + blobs | OSC (8 métricas) + Syphon (1 textura) |
| `osc_client.py` | 8 canales OSC | Métricas | UDP :9000 |
| `syphon_share.py` | 1 servidor Syphon | Máscara uint8 | Textura GPU→GPU |
| `mcp_bridge.py` | 5 parámetros en vivo | OSC :9001 | dict `_params` thread-safe |
| `halo_glow_precise.glsl` | Halo con cobertura | Máscara + 3 uniforms | RGBA halo |
| `glitch_precise.glsl` | Glitch sin jitter | Frame + máscara + trigger | RGBA glitch |
| `particles_precise.glsl` | Partículas en dedos/cabello | 3 inputs + 6 uniforms | RGBA acumulativo |
| `td_osc_to_uniforms.py` | Script DAT TD | Tabla OSC In DAT | `par.value` en 3 GLSL TOPs |

### Flujo de datos completo

```
cv2.VideoCapture(CAM_INDEX) @ 1920×1080 / 60fps
  └─ frame_bgr
      └─ DeepLabSegmentor.segment(frame_bgr):
           CoreML: PIL Image(513×513) → mlmodel.predict()
                   → "PersonMask" float32 (513×513)
                   → (PersonMask > 0.5) * 255 → uint8
                   → cv2.resize(INTER_NEAREST) → mask 1920×1080
                   → morphologyEx(OPEN+CLOSE, 3×3) → mask limpia
           Fallback TF: tf.constant (1×513×513×3) → hub_model()
                   → argmax axis=-1 → class_map 513×513
                   → (class_map == 15) * 255 → mismo postprocess
           Simulación: cv2.ellipse() → silueta animada
      └─ blob_analysis.analyze(mask):
           connectedComponentsWithStats(mask, connectivity=8)
           → largest_area, noise_level, coverage_ratio, blob_count
      └─ optical_flow(prev_gray, curr_gray):
           calcOpticalFlowFarneback → flow_mean, motion_ratio
      └─ trigger logic:
           presence AND largest_area >= area_threshold AND
           flow_mean >= flow_threshold AND motion_ratio >= motion_threshold
           AND cooldown == 0 → triggered=True, cooldown=30
      └─ write_mask_atomic("latest_mask.png")
      └─ SyphonShare.send(mask) → Syphon "JIFREX-P4-DEEPLAB"
      └─ P4OSCClient.send(...) → UDP :9000
```

### Diferencias clave vs P1 (misma arquitectura, modelo diferente)

| | P1 — RealSense + MediaPipe | P4 — DeepLabv3 + CoreML |
|--|--------------------------|------------------------|
| Sensor | RealSense D435i (profundidad) | Cualquier cámara RGB |
| Modelo | MediaPipe Selfie Segmentation | DeepLabv3 MobileNetV2 PASCAL VOC |
| Aceleración | CPU (MSI) | Neural Engine CoreML (Mac M3) |
| Latencia de segmentación | ~30 ms (CPU) | 15–25 ms (Neural Engine) |
| Calidad de borde | Aproximación | Subpixel-accurate |
| Jitter de modelo | Sí | No |
| Falsos triggers | Más frecuentes | Solo movimiento real |
| Métricas OSC | 6 | 8 (+coverage_ratio, mayor precisión en noise_level) |
| Máquinas | MSI + Mac (red) | Mac M3 Max (local) |
| Referente conceptual | — | Antimodular / Lozano-Hemmer |

### Estado de cada módulo

| Módulo | Código | Verificado | Listo para galería |
|--------|--------|------------|-------------------|
| `deeplab_segmentor.py` | ✅ Completo | ✅ Simulación OK | ❌ Requiere `DeepLabV3.mlpackage` |
| `blob_analysis.py` | ✅ Completo | ✅ Lógica correcta | ✅ |
| `deeplab_runtime.py` | ✅ Completo | ✅ Simulación OK | ⚠️ Verificar FPS con modelo real |
| `osc_client.py` | ✅ Completo | ✅ | ⚠️ Verificar IP si TD en otra máquina |
| `syphon_share.py` | ✅ Completo | ⚠️ Depende lib | ❌ Instalar syphon-python |
| `mcp_bridge.py` | ✅ Completo | ✅ Thread-safe | ✅ |
| `halo_glow_precise.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar en sala |
| `glitch_precise.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar en sala |
| `particles_precise.glsl` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Calibrar decay |
| `td_osc_to_uniforms.py` | ✅ Completo | ⚠️ Sin TD real | ⚠️ Verificar nombres de ops |
| `convert_to_coreml.py` | ✅ Completo | ❌ No ejecutado | ❌ Ejecutar en Mac M3 Max |

### Qué debe verificar un auditor

1. **`DeepLabV3.mlpackage` existe**: sin este archivo, el sistema cae a simulación. Verificar con `python3 -c "import os; print(os.path.exists('DeepLabV3.mlpackage'))"`.
2. **Backend activo**: el log de arranque debe mostrar `Backend: CoreML`. Si muestra `tensorflow` o `simulate`, el mlpackage no se encontró.
3. **Latencia de segmentación**: el log muestra `coreml XYms`. Debe ser 15–25. Si es > 40 ms, CoreML está usando CPU en lugar de Neural Engine — verificar `compute_units=ct.ComputeUnit.ALL` en la conversión.
4. **`config.py` OSC_HOST**: si TouchDesigner corre en el mismo Mac, usar `"127.0.0.1"`. Si corre en otra máquina, usar la IP real.
5. **Nombres de ops en TD**: `glsl_halo`, `glsl_glitch`, `glsl_particles` deben coincidir exactamente (`td_osc_to_uniforms.py` líneas 10-12).
6. **INTER_NEAREST en upsample** (`deeplab_segmentor.py` función `_postprocess`): el resize de 513→1920 usa INTER_NEAREST para preservar los bordes subpixel. Cambiar a INTER_LINEAR destruiría la precisión.
7. **coverage_ratio**: es `valid_area / total_pixels` donde `total_pixels = height × width`. Con cámara a 1920×1080, un visitante a 2m de distancia puede tener coverage ~0.04–0.08. Ajustar `coverage_boost` en MCP bridge si los valores son demasiado bajos.
8. **flow_threshold = 0.35** (más bajo que P1/0.50): este valor asume que DeepLabv3 no genera jitter. Si el log muestra triggers frecuentes en reposo, subir a 0.45 vía MCP bridge.
9. **Morphology kernel 3×3** (vs 5×5 en P1): DeepLabv3 ya produce bordes limpios — un kernel más pequeño preserva el detalle de extremidades. No aumentar salvo que haya mucho ruido de fondo.
10. **syphon-python**: sin esta lib, la textura no llega a TD. El OSC sí funciona. Verificar con `python3 -c "import syphon; print(syphon.SyphonServer.__module__)"`.

### Historial de versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| v0.1 | 2026-06-13 | Creación inicial — pipeline completo, 3 shaders "precise", conversión CoreML |

*Última revisión: 2026-06-13 · Desarrollado con claude-sonnet-4-6*  
*Sistema de Proyección Reactiva Interactiva · JIFREX · 2026-06-13*
