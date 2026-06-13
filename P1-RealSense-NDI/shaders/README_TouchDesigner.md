# Fase 3 — Setup TouchDesigner · Mac M3 Max
## Aún Sorprendo · JIFREX · P1 RealSense D435i + NDI

---

## Red de nodos (orden de conexión)

```
[NDI In TOP]           ← recibe máscara desde MSI vía red local (~8 ms)
      │
      ├──────────────────────────────────────────────┐
      │                                              │
[GLSL TOP: halo_glow]           [Null TOP: mask_orig] (copia limpia de la máscara)
      │
[GLSL TOP: glitch] ←── también recibe mask_orig como input[1]
      │
      ├──────────────────────────────────────────────┐
      │                                              │
[GLSL TOP: feedback_particles] ←── input[1]: Feedback TOP
      │                        ←── input[2]: mask_orig
      │
[Feedback TOP] ────────────────────────────────────────┘
  opacidad: 0.92 (ajustar en sala)
      │
[Level TOP] ← brillo/contraste final
      │
[Out TOP] → 2x Epson PowerLite 5510 via HDBaseT Cat6A
```

---

## Configuración OSC In

| Parámetro | Valor |
|-----------|-------|
| Protocol | UDP |
| Port | 9000 |
| Local Address | (tu IP del Mac) |

Conectar **OSC In DAT** → **Script DAT** con `td_osc_to_uniforms.py`  
Execute On: `Table Change`

---

## Uniforms por GLSL TOP

### glsl_halo (halo_glow.glsl)

| Uniform | Tipo | Fuente | Valor inicial |
|---------|------|--------|---------------|
| uFlowMean | float | OSC /jifrex/flow_mean | 0.0 |
| uTime | float | absTime.seconds | auto |

### glsl_glitch (glitch.glsl)

| Uniform | Tipo | Fuente | Valor inicial |
|---------|------|--------|---------------|
| uTrigger | float | OSC /jifrex/trigger | 0.0 |
| uMotionRatio | float | OSC /jifrex/motion_ratio | 0.0 |
| uTime | float | absTime.seconds | auto |

### glsl_particles (feedback_particles.glsl)

| Uniform | Tipo | Fuente | Valor inicial |
|---------|------|--------|---------------|
| uFlowMean | float | OSC /jifrex/flow_mean | 0.0 |
| uMotionRatio | float | OSC /jifrex/motion_ratio | 0.0 |
| uPresence | float | OSC /jifrex/presence | 0.0 |
| uTime | float | absTime.seconds | auto |

---

## Hot-reload de shaders (Folder DAT)

TouchDesigner recarga los shaders automáticamente al detectar cambios en el archivo `.glsl`.

1. Agregar **Folder DAT** apuntando a `P1-RealSense-NDI/shaders/`
2. Conectarlo a cada **GLSL TOP** → parámetro `GLSL TOP > Pixel Shader > File`
3. Activar `File Active`: ON

Cuando modifiques cualquier `.glsl` y guardes, TouchDesigner lo recarga en < 1 s sin interrumpir el stream.

---

## Secuencia de experiencia del visitante

| Estado | Condición OSC | Efecto visual |
|--------|--------------|---------------|
| **Reposo** | presence=0, quietud > 3 s | Fade gradual → piso con patrones abstractos |
| **Presencia** | presence=1, flow_mean < 0.5 | Silueta fragmentada en planos, halo suave |
| **Movimiento lento** | flow_mean 0.5–1.5 | Halos crecen, estelas del Feedback TOP |
| **Movimiento brusco** | trigger=1, motion_ratio > 0.7 | Glitch + flash blanco + partículas máximas |

---

## Calibración en sala (Galería Fernando Cano)

- **Feedback opacity**: empezar en 0.92, bajar si las estelas tapan la máscara
- **halo radius** (`radius` en halo_glow.glsl línea 35): ajustar según distancia proyector–piso
- **numParticles** (feedback_particles.glsl línea 60): máx 36, bajar si hay lag en TD
- **Throw calculado**: ~4.79 m → imagen ~2.4 m ancho. Verificar keystone de los Epson.
- Correr prueba de 8 horas continuas antes de la inauguración.

---

## Archivos de esta carpeta

| Archivo | Descripción |
|---------|-------------|
| `halo_glow.glsl` | Shader 1: detección de bordes + halo proporcional a flow_mean |
| `glitch.glsl` | Shader 2: RGB split + UV warp, activo solo en trigger |
| `feedback_particles.glsl` | Shader 3: partículas del borde + estela Feedback |
| `td_osc_to_uniforms.py` | Script DAT: OSC → uniforms de los GLSL TOPs |
| `README_TouchDesigner.md` | Este archivo |
