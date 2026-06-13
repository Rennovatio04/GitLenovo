# Propuesta 3 — Multi-Cámara: 3 Perspectivas Simultáneas

**Proyecto:** Aún Sorprendo — Exposición Pablo Picasso  
**Venue:** Galería Universitaria Fernando Cano, UAEMEx / FUNIBER  
**Sistema:** JIFREX — Sistema de Proyección Reactiva Interactiva  
**Estado:** Alternativa de alta fidelidad artística — Mac M3 Max requerida

---

## Concepto

La propuesta más fiel al cubismo: Picasso no pintaba lo que veía, pintaba lo que **sabía que estaba ahí, desde todos los ángulos posibles a la vez**. Este sistema hace eso literalmente con 3 cámaras en 3 ángulos distintos procesadas en paralelo.

> "El visitante se ve a sí mismo como Picasso veía a sus modelos: desde todos los ángulos a la vez."

---

## Las 3 perspectivas

| Cámara | Posición | Significado | Obra de referencia |
|--------|----------|-------------|-------------------|
| A — OAK-D Pro W | Frontal | Como nos vemos en un espejo | Les Bleus de Barcelona |
| B — Logitech C922 | Lateral derecha | Como vemos a otros sin que nos vean | Bailarines sobre cuero |
| C — Logitech C922 | Cenital | La vista que nunca vemos de nosotros mismos | Geneviève sobre papel Japón |

**Triple coincidencia → luz blanca brillante** (Screen blend de 3 siluetas)

---

## Arquitectura

```
Cámara A (TB4 #1) ──┐
Cámara B (TB4 #2) ──┼── Python headless (3 hilos paralelos, Neural Engine M3 Max)
Cámara C (TB4 #3) ──┘         Sincronización < 33 ms
                               OSC compuesto + Syphon GPU→GPU
                                        │
                              TouchDesigner — Mac M3 Max
                         Syphon ×3 · Composite TOP · GLSL TOP · Feedback TOP
                                        │
                          2× Epson PowerLite 5510 via HDBaseT Cat6A
```

> **CRÍTICO:** Un puerto Thunderbolt 4 dedicado por cámara. Hub USB compartido produce frame drops y desincronización que destruyen el efecto artístico.

---

## Sincronización de 3 streams

Ventana de sincronización: **33 ms = 1 frame a 30 fps**  
Frames fuera de ventana son descartados y se reutiliza el frame anterior.

---

## Hardware

- **Mac M3 Max** — ÓPTIMA (40 núcleos GPU, 16 Neural Engine, 3× TB4, 36 GB RAM unificada)
- **MSI Katana** — NO viable (4 GB VRAM insuficiente para 3 texturas + TD, sin TB4)

---

## Shaders GLSL — Composición multicapa (Fase 3 JIFREX)

```glsl
// Silueta A = azul  (0.09, 0.35, 0.95)  — frontal
// Silueta B = ocre  (0.95, 0.66, 0.12)  — lateral
// Silueta C = rosa  (0.95, 0.38, 0.65)  — cenital

// Screen blend — triple coincidencia = blanco brillante
vec3 result = 1.0 - (1.0 - col_a) * (1.0 - col_b) * (1.0 - col_c);
```

| Shader | Efecto |
|--------|--------|
| Composición multicapa | 3 siluetas coloreadas + Screen blend |
| Distorsión de perspectiva | Transformaciones UV por ángulo real en espacio 2D |
| Partículas por perspectiva | Frontal: expansión radial · Lateral: traslación horizontal · Cenital: espiral |

---

## Secuencia de experiencia

1. **Entrada** — Tres halos de color aparecen sobre el piso: azul, ocre, rosa
2. **Silueta frontal** (azul) — Como en un espejo
3. **Silueta lateral** (ocre) — El perfil que ves de otros, nunca de ti
4. **Silueta cenital** (rosa) — La vista desde arriba que nunca has visto
5. **Composición dinámica** — Triple coincidencia: luz blanca · Doble: mezcla · Simple: color puro

---

## Fases de implementación

- [ ] Fase 1 — Configuración multicámara (OAK-D Pro W + 2× Logitech C922 en TB4, 3 hilos paralelos, verificación sync < 33 ms)
- [ ] Fase 2 — Pipeline de visión ×3 (3 máscaras en tiempo real, OSC compuesto, Syphon ×3)
- [ ] Fase 3 — Shaders + Calibración (Composite TOP Screen, distorsión UV, Feedback TOP multicapa, prueba 8 horas)

---

## Archivo fuente

`Propuesta-3-Multi-Camara-3-Perspectivas-Simultaneas-1.md`
