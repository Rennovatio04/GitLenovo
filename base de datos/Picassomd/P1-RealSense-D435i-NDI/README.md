# Propuesta 1 — RealSense D435i + NDI

**Proyecto:** Aún Sorprendo — Exposición Pablo Picasso  
**Venue:** Galería Universitaria Fernando Cano, UAEMEx / FUNIBER  
**Sistema:** JIFREX — Sistema de Proyección Reactiva Interactiva  
**Estado:** Fases 1 y 2 completadas · Fase 3 en desarrollo

---

## Concepto

Inspirada en el cubismo: así como Picasso descomponía un rostro en vistas simultáneas, el sistema fragmenta la nube de puntos 3D del visitante en planos geométricos proyectados sobre el piso.

---

## Arquitectura

| Capa | Tecnología |
|------|-----------|
| Captura | Intel RealSense D435i (stereo IR, 1280×720 @ 30 fps) |
| Procesamiento | Python headless — MSI Windows 11 |
| Pipeline | pyrealsense2 → segmentación → Optical Flow Farneback → trigger logic |
| Transmisión | NDI (~8 ms) + OSC UDP :9000 (< 2 ms) |
| Render | TouchDesigner — MacBook Pro M3 Max |
| Proyección | 2× Epson PowerLite 5510 (5500 lm, WUXGA) via HDBaseT Cat6A |

### Dos máquinas, roles separados

- **MSI Katana GF66** (Windows 11): servidor de visión. Único SO compatible con RealSense.
- **MacBook Pro M3 Max**: servidor de render. Shaders GLSL Metal + Feedback TOP.

---

## Pipeline `webcam_runtime.py` (30 fps)

1. Captura frame depth + RGB via `pyrealsense2`
2. Alineación depth con RGB → coordenadas 3D
3. Segmentación con umbral adaptativo → máscara binaria
4. Optical Flow Farneback → `flow_mean` + `motion_ratio`
5. Análisis de blobs → `largest_blob_area` + `noise_level`
6. Lógica de trigger (anti-falsos positivos: umbral 500 px + cooldown 30 frames)
7. Escritura atómica `latest_mask.png` via `os.replace()`
8. Emit OSC → puerto 9000 Mac + Stream NDI

---

## Shaders — Fase 3 (JIFREX)

| Shader | Técnica | Controlado por |
|--------|---------|---------------|
| Halo / Glow | `dFdx/dFdy` detectan bordes | `flow_mean` |
| Glitch / Distorsión | Desplazamiento UV con sin/cos | `trigger_triggered` + `motion_ratio` |
| Partículas / Estela | Particle SOP + Feedback TOP | `flow_mean` + `motion_ratio` |

---

## Estado de fases

- [x] Fase 1 — Ecosistema MCP (`venv`, `mcp_bridge.py`, repositorio Antimodular indexado)
- [x] Fase 2 — Interconectividad (`webcam_runtime.py`, OSC mapeado, NDI MSI↔Mac funcional)
- [ ] Fase 3 — Shaders Halo + Glitch + Partículas + Feedback TOP + calibración en sala

---

## Archivo fuente

`Propuesta-1-RealSense-D435i-NDI-1.md`
