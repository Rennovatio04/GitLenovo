# GitLenovo

Repositorio de trabajo para **Aún Sorprendo · JIFREX**, con cuatro propuestas
interactivas listas para revisión técnica y curatorial.

## Estado del repositorio

| Carpeta | Propuesta | Estado de auditoría | Riesgo principal |
|---------|-----------|---------------------|------------------|
| `P1-RealSense-NDI` | RealSense + NDI | Reauditada 2026-06-14 | Red/IP fija y prueba prolongada |
| `P2-Skeleton-MediaPipe` | Skeleton semántico | Reauditada 2026-06-14 | Iluminación real de sala |
| `P3-Multi-Camara` | Triple perspectiva | Reauditada 2026-06-14 | Hardware Mac M3 Max + sync real |
| `P4-DeepLabv3-CoreML` | DeepLabv3 + CoreML | Reauditada 2026-06-14 | Conversión CoreML y hardware real |

## Qué se dejó preparado

- Cada carpeta incluye un `README.md` con:
  - estado funcional actual,
  - hallazgos de auditoría,
  - mejoras aplicadas,
  - trabajo auditado,
  - y un bloque **listo para próxima auditoría**.
- Los runtimes principales quedaron reforzados en rutas de salida, arranque de
  bridge MCP y manejo de sincronización/cierre donde aplicaba.

## Próxima auditoría sugerida

1. Validar hardware real y red de galería.
2. Ejecutar pruebas largas de estabilidad.
3. Confirmar integración completa con TouchDesigner.
4. Cerrar riesgos operativos marcados en cada propuesta.
