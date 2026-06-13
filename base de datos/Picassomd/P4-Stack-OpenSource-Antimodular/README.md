# Propuesta 4 — Stack Open Source / Referencia Antimodular

**Proyecto:** Aún Sorprendo — Exposición Pablo Picasso  
**Venue:** Galería Universitaria Fernando Cano, UAEMEx / FUNIBER  
**Sistema:** JIFREX — Sistema de Proyección Reactiva Interactiva  
**Estado:** 100% software libre — alternativa de mayor precisión ML

---

## Concepto

Conecta el lenguaje de Picasso con el de **Rafael Lozano-Hemmer** (Antimodular):

| | |
|--|--|
| **Picasso** | Pone el proceso mental del artista en el lienzo. El cuadro no existe sin la mente que lo piensa. |
| **Lozano-Hemmer** | Pone el proceso perceptivo del espectador en el espacio. La imagen no existe sin el cuerpo que la activa. |
| **Propuesta 4** | Conecta ambos en la Galería Fernando Cano. El piso no existe sin el visitante que lo habita. |

---

## Diferenciador técnico: DeepLabv3 vs MediaPipe

| Condición real de galería | MediaPipe | DeepLabv3 |
|---|---|---|
| Ropa del mismo tono que fondo | Pierde máscara | Mantiene máscara limpia |
| Luz proyectada rebota en cuerpo | Contorno inestable | Contorno estable |
| Múltiples personas | Confunde cuerpos | Separa siluetas |

DeepLabv3 fue diseñado para segmentación semántica de alta precisión en entornos variables — exactamente las condiciones de una galería con proyección activa.

---

## Arquitectura

```
Cámara RGB 1080p/60fps — OpenCV
        │
Python Headless — Mac M3 Max
  OpenCV preprocesamiento + normalización
  DeepLabv3 CoreML (Clase 15 "person") → máscara binaria subpixel-accurate
  Análisis Antimodular: largest_blob_area · noise_level · coverage_ratio
  Optical Flow Farneback → triggers
        │
  Syphon GPU→GPU        OSC UDP :9000
        │                     │
  TouchDesigner — Mac M3 Max
  Syphon receiver → GLSL shaders (Fase 3 JIFREX) → Feedback TOP
        │
  2× Epson PowerLite 5510 via HDBaseT Cat6A
```

---

## Conversión DeepLabv3 → CoreML (Neural Engine M3 Max)

```python
import coremltools as ct
import tensorflow as tf

model = tf.saved_model.load("deepLabv3_mnv2_pascal")
mlmodel = ct.convert(
    model,
    inputs=[ct.ImageType(name="ImageTensor", shape=(1, 513, 513, 3))],
    compute_precision=ct.precision.FLOAT16,
    compute_units=ct.ComputeUnit.ALL
)
mlmodel.save("DeepLabV3.mlpackage")
```

**Resultado:** 15–25 ms/frame en Neural Engine, dejando GPU Metal (40 núcleos) completamente libre para TouchDesigner.

---

## Viabilidad por hardware

| Configuración | Viabilidad |
|---|---|
| Mac M3 Max sola | ✅ ÓPTIMA — CoreML en Neural Engine + TD en GPU Metal sin competencia |
| MSI Katana sola | ❌ NO recomendado — DeepLabv3 CUDA consume los 4 GB VRAM antes de que TD renderice |
| MSI + Mac en red | ⚠️ Viable con reservas — mayor latencia y complejidad |

---

## Impacto en shaders (Fase 3 JIFREX)

| Shader | Con MediaPipe | Con DeepLabv3 |
|--------|--------------|--------------|
| Halo/Glow | Bordes ruidosos, halos irregulares | Bordes subpixel-accurate, halo uniforme y suave |
| Glitch | Trigger activado también por oscilación del modelo ML | Trigger solo por movimiento real → más dramático, menos frecuente |
| Partículas | Emergen de aproximación del contorno | Emergen del contorno exacto, incluyendo dedos y cabello |

---

## Ventajas

**Técnicas**
- Precisión de bordes superior en condiciones reales de galería
- CoreML float16 en Neural Engine sin competir con TouchDesigner
- Repositorio Antimodular: código probado en museos internacionales
- 100% software libre (Apache 2.0 / BSD / MIT) — sin dependencias de proveedor
- Ciclo de auditoría MCP: mejora en tiempo real durante la exposición

**Conceptuales**
- Genealogía directa con Lozano-Hemmer — declaración artística, no solo técnica
- Referente ya identificado en el documento curatorial
- Shaders aprovechan bordes subpixel-accurate para mayor impacto visual

---

## Archivo fuente

`Propuesta-4-Stack-Open-Source-Referencia-Antimodular-1.md`
