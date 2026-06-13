# Setup TouchDesigner · Mac M3 Max · P3 Multi-Cámara
## Aún Sorprendo · JIFREX · 3 Perspectivas Simultáneas

---

## Red de nodos completa

```
[Syphon In A: JIFREX-CAM-A-FRONTAL]     ← frontal (azul)
         │
[GLSL TOP: glsl_distort_a]  uPerspective=0 (distorsión radial)
         │
[Syphon In B: JIFREX-CAM-B-LATERAL]     ← lateral derecha (ocre)
         │
[GLSL TOP: glsl_distort_b]  uPerspective=1 (deformación horizontal)
         │
[Syphon In C: JIFREX-CAM-C-CENITAL]     ← cenital (rosa)
         │
[GLSL TOP: glsl_distort_c]  uPerspective=2 (rotación espiral)
         │
         └── (las 3 distort feeds van a composite) ──► [GLSL TOP: glsl_composite]
                                                              │
                                                    [GLSL TOP: glsl_particles] ──┐
                                                              │                  │
                                                    [Feedback TOP] ──────────────┘
                                                     opacity: 0.90
                                                              │
                                                    [Level TOP] ← brillo/contraste final
                                                              │
                                                    [Out TOP] → 2× Epson PowerLite 5510
                                                               via HDBaseT Cat6A
```

---

## Configuración de las 3 entradas Syphon

| Syphon In TOP | Nombre servidor | Perspectiva | Color |
|---------------|-----------------|-------------|-------|
| `syphon_in_a` | `JIFREX-CAM-A-FRONTAL` | Frontal | Azul (0.09, 0.35, 0.95) |
| `syphon_in_b` | `JIFREX-CAM-B-LATERAL` | Lateral | Ocre (0.95, 0.66, 0.12) |
| `syphon_in_c` | `JIFREX-CAM-C-CENITAL` | Cenital | Rosa (0.95, 0.38, 0.65) |

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

### glsl_composite (composite_multicamara.glsl)

| Par | Tipo | Fuente OSC | Notas |
|-----|------|-----------|-------|
| value0 | float | `/multicam/a/flow_mean` | |
| value1 | float | `/multicam/b/flow_mean` | |
| value2 | float | `/multicam/c/flow_mean` | |
| value3 | float | `/multicam/triple_ratio` | 0.0–1.0 |
| value4 | float | `/multicam/any_presence` | 0 o 1 |
| value5 | float | `absTime.seconds` | uTime |

### glsl_distort_a / glsl_distort_b / glsl_distort_c (distorsion_uv.glsl)

| Par | Tipo | Fuente | Notas |
|-----|------|--------|-------|
| value0 | float | **FIJO** | A=0.0, B=1.0, C=2.0 |
| value1 | float | OSC `/multicam/[a|b|c]/flow_mean` | |
| value2 | float | `absTime.seconds` | uTime |

### glsl_particles (particulas_perspectiva.glsl)

| Par | Tipo | Fuente | Notas |
|-----|------|--------|-------|
| value0 | float | **FIJO** | Perspectiva dominante (0/1/2) o dinámico |
| value1 | float | `/multicam/a/flow_mean` | |
| value2 | float | `/multicam/b/flow_mean` | |
| value3 | float | `/multicam/c/flow_mean` | |
| value4 | float | `/multicam/a/motion` | |
| value5 | float | `/multicam/b/motion` | |
| value6 | float | `/multicam/c/motion` | |
| value7 | float | `/multicam/triple_ratio` | |
| value8 | float | `/multicam/any_presence` | |
| value9 | float | `absTime.seconds` | uTime |

---

## Máscara compuesta para particulas_perspectiva

El `glsl_particles` necesita la máscara compuesta en input[2].
Crear un **Composite TOP** en modo MAX conectando las 3 salidas de los Syphon In:
```
Max(syphon_in_a, syphon_in_b, syphon_in_c) → glsl_particles input[2]
```

---

## Hot-reload de shaders

1. Agregar **Folder DAT** apuntando a la carpeta `/shaders/`
2. Conectarlo a cada **GLSL TOP** → `Pixel Shader > File`
3. Activar `File Active`: ON

Los shaders se recargan automáticamente al guardar el `.glsl`, sin interrumpir el stream.

---

## Secuencia de experiencia del visitante

| Estado | Condición OSC | Efecto visual |
|--------|---------------|---------------|
| **Reposo** | `any_presence=0` | Tres halos de color pulsantes sobre el piso (azul, ocre, rosa) |
| **1 perspectiva** | solo una cámara detecta | Silueta coloreada + partículas de esa perspectiva |
| **2 perspectivas** | doble solapamiento | 2 colores mezclados por Screen blend + decay acumulado |
| **Triple coincidencia** | `triple_ratio > 0.04` | LUZ BLANCA BRILLANTE — el cubismo hecho literal |
| **Movimiento intenso** | `flow_mean > 1.5` | Distorsiones UV ampliadas + partículas máximas |

---

## Calibración en sala (Galería Fernando Cano)

- **Feedback opacity**: comenzar en 0.90, bajar si las estelas tapan las siluetas
- **uAnyPresence halos**: ajustar posiciones UV (`halo_a`, `halo_b`, `halo_c`) en `composite_multicamara.glsl` según el layout real del piso de galería
- **Posiciones de cámaras**: la sync < 33 ms requiere cables USB directos a los 3 puertos TB4 — NO hubs
- **TRIPLE_THRESHOLD** en `config.py`: subir a 0.08–0.10 si la galería tiene muchos reflejos que generan falsos solapamientos
- Prueba de 8 horas continuas antes de la inauguración
