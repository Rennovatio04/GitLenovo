# Auditoría técnica posterior — 2026-06-14

## Correcciones aplicadas

### P1 · RealSense + NDI
- `webcam_runtime.py` ya no queda bloqueado indefinidamente esperando frames.
- Se añadió timeout explícito de RealSense y reinicio del pipeline tras fallos consecutivos.
- La próxima auditoría debe validar la recuperación con desconexión física real de la D435i.

### P2 · Skeleton MediaPipe
- `count_people()` ahora publica `0` cuando no existe máscara válida, en vez de inventar una persona.
- La documentación se alineó con las rutas OSC canónicas `/cuerpo/metrica/...`.
- Se mantienen aliases OSC legacy para no romper patches anteriores de TouchDesigner.
- La detección de dos personas queda marcada como experimental hasta validarla con hardware y dos siluetas reales.

### P3 · Multi-Cámara
- `SyncManager` ya no devuelve tripletas que siguen fuera de la ventana de sincronización.
- Cuando el fallback con el frame validado no alcanza a reentrar en ventana, el runtime omite esa composición.

### P4 · DeepLabv3 CoreML
- La simulación ya solo ocurre con `--simulate`.
- Si la cámara falla, el runtime emite máscara vacía, resetea el flow y reintenta reconectar la captura.
- Se eliminó el caso en el que una caída de cámara fabricaba presencia falsa.

## Revisiones pendientes para la siguiente auditoría

1. P1: desconectar y reconectar la RealSense durante 10-15 minutos para confirmar que el reinicio del pipeline siempre recupera OSC y NDI.
2. P2: probar `blob_count` con dos personas reales, personas parcialmente ocluidas y pérdida intermitente de `segmentation_mask`.
3. P2: validar que TouchDesigner reciba igual las rutas canónicas y las legacy sin duplicar efectos.
4. P3: medir `sync_ratio` y confirmar que descartar tripletas fuera de ventana no introduce huecos visibles en la composición.
5. P4: apagar o desconectar la webcam en caliente para verificar reconexión automática y ausencia total de triggers falsos.
6. P4: repetir una corrida larga para confirmar que el path de máscara vacía no degrada FPS ni deja `cooldown` atascado.
