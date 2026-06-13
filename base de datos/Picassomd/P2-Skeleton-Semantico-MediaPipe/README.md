# Propuesta 2 — Skeleton Semántico MediaPipe Holistic

**Proyecto:** Aún Sorprendo — Exposición Pablo Picasso  
**Venue:** Galería Universitaria Fernando Cano, UAEMEx / FUNIBER  
**Sistema:** JIFREX — Sistema de Proyección Reactiva Interactiva  
**Estado:** Alternativa documentada — todas las fases pendientes

---

## Concepto

A diferencia de P1 (que detecta presencia), esta propuesta detecta **qué parte del cuerpo se mueve** y genera una respuesta visual distinta por zona. El visitante no activa la instalación — *conversa con ella*.

> "La mano de Picasso no dibujaba lo mismo que su ojo veía."

---

## Diferencia clave vs Propuesta 1

| | P1 — RealSense | P2 — Skeleton Semántico |
|--|---------------|------------------------|
| Detección | Presencia / silueta binaria | Qué parte del cuerpo se mueve |
| Respuesta visual | Una respuesta única | Respuesta diferente por zona corporal |
| Visitante | Activa la instalación | Conversa con ella |
| Evento | Presencia = evento | Gesto específico = evento específico |

---

## Arquitectura

| Capa | Tecnología |
|------|-----------|
| Captura | Webcam RGB 1080p / 60 fps |
| Procesamiento | Python headless — MediaPipe Holistic |
| Zonas detectadas | `zona_upper`, `zona_lower`, `zona_hands`, `zona_head` |
| Transmisión | OSC semántico :9000 + Spout/Syphon GPU→GPU (~1 ms) |
| Render | TouchDesigner — OSC In CHOP → Select CHOP por zona → shaders por zona |
| Proyección | 2× Epson PowerLite 5510 |

---

## Los 17 Joints y zonas

- **zona_upper** — Hombros, codos, muñecas → extensión/flexión de brazos
- **zona_lower** — Caderas, rodillas → rotación lateral, cuclillas/salto
- **zona_head** — Nariz, oídos → pitch y roll (inclinación de cabeza)

---

## Triggers semánticos por zona

| Zona / Gesto | Respuesta Visual | Lógica |
|---|---|---|
| Mano extendida | Planos geométricos fragmentados cubistas | `landmark[16].y < landmark[12].y - umbral` |
| Rotación de cadera | Velocidad de estelas proporcional al ángulo | `abs(hip_angle - prev_hip_angle) > 15°` |
| Inclinación de cabeza | Cambio de paleta de color completa | `atan2(nose.y - ear.y, nose.x - ear.x)` |
| Salto / movimiento brusco | Glitch + partículas máximas | `motion_ratio > 0.7` |
| Pose estática > 3s | Fade gradual → reposo | `flow_mean < 0.5` durante 90 frames |
| 2 personas simultáneas | Diálogo cubista entre cuerpos *(exclusivo P2)* | `blob_count > 1` + dos centros de masa |

---

## Hardware compatible

- **MSI Katana sola** — viable y recomendada (MediaPipe en CPU i5, GPU libre para TouchDesigner)
- **Mac M3 Max sola** — muy cómoda (Neural Engine aislado del render)
- **MSI + Mac** — óptima pero innecesaria

> Limitación crítica: la iluminación de galería puede degradar la precisión de joints (ropa similar al fondo, luz directa en cámara, sombras cruzadas). Requiere visita técnica previa.

---

## Estado de fases

- [ ] Configuración entorno
- [ ] Lógica semántica
- [ ] Integración TouchDesigner
- [ ] Calibración en sala

---

## Archivo fuente

`Propuesta-2-Skeleton-Semantico-MediaPipe-Holistic-1.md`
