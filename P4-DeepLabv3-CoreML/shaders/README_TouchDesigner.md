# Setup TouchDesigner · Mac M3 Max · P4 DeepLabv3 + CoreML
## Aún Sorprendo · JIFREX · Referencia Antimodular / Lozano-Hemmer

---

## Red de nodos

```
[Syphon In: JIFREX-P4-DEEPLAB]       ← máscara DeepLabv3 subpixel-accurate
        │
        ├──────────────────────────────────────────────────┐
        │                                                  │
[GLSL TOP: glsl_halo]               [Null TOP: mask_deeplab] (copia limpia)
  halo_glow_precise.glsl
        │
[GLSL TOP: glsl_glitch]  ←── input[1]: mask_deeplab
  glitch_precise.glsl
        │
        ├──────────────────────────────────────────────────┐
        │                                                  │
[GLSL TOP: glsl_particles] ←── input[1]: Feedback TOP
  particles_precise.glsl  ←── input[2]: mask_deeplab
        │
[Feedback TOP] ──────────────────────────────────────────────┘
  opacidad: 0.90 (ajustar en sala — empezar aquí)
        │
[Level TOP]  ← brillo/contraste final
        │
[Out TOP] → 2× Epson PowerLite 5510 via HDBaseT Cat6A
```

---

## Configuración OSC In

| Parámetro | Valor |
|-----------|-------|
| Protocol | UDP |
| Port | 9000 |
| Local Address | IP del Mac M3 Max |

Conectar **OSC In DAT** → **Script DAT** con `td_osc_to_uniforms.py`  
Execute On: `Table Change`

---

## Uniforms por GLSL TOP

### glsl_halo (halo_glow_precise.glsl)

| Par | Tipo | Fuente OSC | Notas |
|-----|------|-----------|-------|
| value0 | float | `/jifrex/p4/flow_mean` | |
| value1 | float | `/jifrex/p4/coverage_ratio` | **nuevo P4** — Antimodular |
| value2 | float | `/jifrex/p4/presence` | |
| value3 | float | `absTime.seconds` | uTime |

### glsl_glitch (glitch_precise.glsl)

| Par | Tipo | Fuente OSC | Notas |
|-----|------|-----------|-------|
| value0 | float | `/jifrex/p4/trigger` | |
| value1 | float | `/jifrex/p4/motion_ratio` | |
| value2 | float | `/jifrex/p4/noise_level` | **nuevo P4** — Antimodular |
| value3 | float | `absTime.seconds` | uTime |

### glsl_particles (particles_precise.glsl)

| Par | Tipo | Fuente OSC | Notas |
|-----|------|-----------|-------|
| value0 | float | `/jifrex/p4/flow_mean` | |
| value1 | float | `/jifrex/p4/motion_ratio` | |
| value2 | float | `/jifrex/p4/presence` | |
| value3 | float | `/jifrex/p4/coverage_ratio` | **nuevo P4** — Antimodular |
| value4 | float | `/jifrex/p4/noise_level` | **nuevo P4** — Antimodular |
| value5 | float | `absTime.seconds` | uTime |

---

## Diferencias vs P1 (misma red, mejor señal)

La red de nodos en TouchDesigner es **idéntica** a la de P1. Lo que cambia:

| Aspecto | P1 — MediaPipe | P4 — DeepLabv3 |
|---------|---------------|----------------|
| Fuente de máscara | Syphon desde MSI vía NDI | Syphon local desde Python CoreML |
| Calidad de borde | Aproximación de segmentación | Subpixel-accurate |
| Jitter de modelo | Sí (oscilación MediaPipe) | No (DeepLabv3 estable) |
| Falsos triggers | Frecuentes | Raros (solo movimiento real) |
| Partículas en dedos | No (borde demasiado ruidoso) | Sí (contorno exacto) |
| Nuevos uniforms | — | `uCoverageRatio`, `uNoiseLevel` |
| Latencia de segmentación | ~30 ms (CPU) | 15–25 ms (Neural Engine) |

---

## Secuencia de experiencia del visitante

| Estado | Condición OSC | Efecto visual (más preciso que P1) |
|--------|---------------|-----------------------------------|
| **Reposo** | `presence=0` | Negro — la sala es el lienzo |
| **Entrada** | `presence=1`, `flow_mean < 0.3` | Silueta perfecta con dedos y cabello visibles |
| **Presencia** | `presence=1`, `coverage_ratio > 0.05` | Halo uniforme proporcional a tamaño del visitante |
| **Movimiento** | `flow_mean > 0.5` | Estelas exactas del contorno + partículas |
| **Movimiento brusco** | `trigger=1` | Glitch + flash — menos frecuente, más impactante |
| **Varios visitantes** | `noise_level > 0.3` | Glitch ampliado + más bandas de distorsión |

---

## Calibración en sala (Galería Fernando Cano)

- **Feedback opacity**: 0.90 → bajar si estelas tapan detalles del contorno
- **flow_threshold** (en `config.py`): comenzar en 0.35 — más bajo que P1 (0.50) porque DeepLabv3 no tiene jitter
- **coverage_boost** (via MCP bridge): multiplicador del `coverage_ratio` → ajustar según distancia de la cámara al visitante
- **Iluminación**: DeepLabv3 es más robusto que MediaPipe ante luz proyectada rebotando en el cuerpo, pero verificar con ropa oscura sobre fondo oscuro
- Prueba de 8 horas continuas antes de la inauguración
