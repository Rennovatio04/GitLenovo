# GitLenovo

Repositorio base de **Aún Sorprendo · JIFREX**, una colección de **4 propuestas
de instalación reactiva** para la exposición de Pablo Picasso en la Galería
Universitaria Fernando Cano.

El proyecto combina **visión por computadora**, **análisis corporal**,
**segmentación**, **OSC**, **NDI / Spout / Syphon** y **TouchDesigner** para
convertir la presencia del visitante en imagen proyectada en tiempo real.

## Qué hay en este repositorio

| Carpeta | Qué contiene | Tecnología principal | Resultado visual |
|---------|---------------|----------------------|------------------|
| `P1-RealSense-NDI` | Propuesta basada en profundidad con RealSense D435i | RealSense + OpenCV + OSC + NDI | Silueta binaria reactiva con shaders |
| `P2-Skeleton-MediaPipe` | Propuesta semántica por partes del cuerpo | MediaPipe Holistic + OpenCV + OSC + Spout/Syphon | Respuestas distintas según manos, cabeza, cadera y quietud |
| `P3-Multi-Camara` | Propuesta cubista con 3 perspectivas simultáneas | MediaPipe ×3 + SyncManager + OSC + Syphon | Composición multicámara con coincidencia triple |
| `P4-DeepLabv3-CoreML` | Propuesta de segmentación precisa con CoreML | DeepLabv3 + CoreML/TensorFlow + OSC + Syphon | Máscara de alta precisión para halo, glitch y partículas |

## Objetivo del proyecto

Construir y comparar cuatro enfoques técnicos para una misma pieza interactiva:

1. **Presencia por profundidad**.
2. **Lectura semántica del cuerpo**.
3. **Visión simultánea desde varios ángulos**.
4. **Segmentación precisa con modelo de IA**.

Cada carpeta es una propuesta autónoma con su propio runtime, configuración,
dependencias, shaders y documentación de auditoría.

## Estructura general

Cada propuesta sigue casi la misma organización:

| Tipo de archivo | Función |
|-----------------|---------|
| `README.md` | Estado actual, arquitectura, auditoría y pendientes |
| `config.py` | Parámetros centrales: puertos, IP, thresholds, cámara, nombres de share |
| `*_runtime.py` | Loop principal en tiempo real |
| `mcp_bridge.py` | Ajuste de parámetros en vivo vía OSC |
| `osc_client.py` | Envío de métricas a TouchDesigner |
| `shaders/` | GLSL + Script DAT + guía para TouchDesigner |
| `requirements.txt` | Dependencias Python por propuesta |

## Componentes principales

### 1. Captura y percepción

- **Intel RealSense D435i** en P1.
- **Webcam RGB** en P2 y P4.
- **OAK-D Pro W + 2 webcams C922** en P3.
- **MediaPipe Holistic** para landmarks y segmentación en P2/P3.
- **DeepLabv3** para segmentación semántica precisa en P4.
- **OpenCV** para captura, optical flow, blobs, morfología y preview.

### 2. Lógica interactiva

- **Optical Flow Farneback** para medir movimiento global.
- **Análisis de blobs** para presencia, ruido, cobertura y conteo de personas.
- **Triggers** por gesto, quietud, coincidencia o cobertura según propuesta.
- **MCP bridge** para recalibrar parámetros sin reiniciar el sistema.

### 3. Comunicación con el render

- **OSC / UDP** para enviar métricas numéricas a TouchDesigner.
- **NDI** en P1 para compartir video por red.
- **Spout** en Windows y **Syphon** en macOS para compartir texturas localmente.

### 4. Render y proyección

- **TouchDesigner** como entorno principal de composición visual.
- **GLSL TOPs** para halo, glitch, partículas, distorsión y composición.
- **Proyectores Epson PowerLite 5510** como salida final planeada.

## Software necesario

### Base común

- **Python 3.11 o 3.12** recomendado.
- **TouchDesigner** en la máquina de render.
- **Git** para control de versiones.

### Librerías frecuentes

- `opencv-python`
- `numpy`
- `python-osc`
- `Pillow`

### Según la propuesta

| Propuesta | Software / SDK adicional |
|-----------|---------------------------|
| P1 | `pyrealsense2`, `ndi-python`, SDK NDI de Vizrt |
| P2 | `mediapipe`, `SpoutGL` o `syphon-python` |
| P3 | `mediapipe`, `depthai`, `syphon-python` |
| P4 | `coremltools`, `tensorflow`, `tensorflow-hub`, `syphon-python` |

## Requisitos de hardware

| Propuesta | Hardware mínimo realista | Observaciones |
|-----------|---------------------------|---------------|
| P1 | MSI Windows 11 + RealSense D435i + Mac de render | Requiere red estable para OSC/NDI |
| P2 | Una sola máquina con webcam RGB | Más sensible a iluminación de sala |
| P3 | **Mac M3 Max** + OAK-D Pro W + 2 C922 | Requiere 3 entradas de cámara y buena sincronización |
| P4 | **Mac M3 Max** + webcam RGB | Ideal para CoreML en Neural Engine |

## Flujo técnico general

```text
Sensor / Cámara
  → Runtime Python
  → Segmentación / Skeleton / Flow / Blobs
  → Triggers + métricas
  → OSC + video/share
  → TouchDesigner
  → GLSL / composición
  → Proyección
```

## Datos técnicos clave para que funcione

### Red y puertos

- **OSC principal**: puerto `9000`
- **MCP listen**: puerto `9001`
- **MCP response**: puerto `9002`
- P1 usa además **NDI** como transporte de video por red.

### Entorno Python

- Evitar Python 3.13/3.14 en propuestas con MediaPipe.
- Usar un **venv por propuesta**, porque las dependencias no son idénticas.
- P4 requiere conversión previa de `DeepLabV3.mlpackage` para CoreML real.

### Integración con TouchDesigner

- Los nombres de operadores en TD deben coincidir con los scripts `td_osc_to_uniforms.py`.
- Si el share GPU no está instalado, algunos proyectos siguen enviando OSC pero no textura.
- Los shaders están pensados para trabajar con señales de trigger, flow, blob, coverage o zonas corporales.

### Calibración

- Todas las propuestas requieren ajustar **thresholds** en sala.
- P2 y P3 dependen más de **iluminación** y encuadre.
- P1 depende más de **distancia**, profundidad y red.
- P4 depende de **modelo CoreML**, cámara y hardware Apple Silicon.

## Estado actual del repositorio

| Carpeta | Estado de auditoría | Riesgo principal |
|---------|---------------------|------------------|
| `P1-RealSense-NDI` | Reauditada 2026-06-14 | Red/IP fija y prueba prolongada |
| `P2-Skeleton-MediaPipe` | Reauditada 2026-06-14 | Iluminación real de sala |
| `P3-Multi-Camara` | Reauditada 2026-06-14 | Hardware Mac M3 Max + sync real |
| `P4-DeepLabv3-CoreML` | Reauditada 2026-06-14 | Conversión CoreML y hardware real |

## Dónde revisar cada detalle

- **Si quieres entender la propuesta**: abre el `README.md` de cada carpeta.
- **Si quieres cambiar parámetros**: revisa `config.py`.
- **Si quieres ejecutar el sistema**: usa el `*_runtime.py`.
- **Si quieres integrar con TouchDesigner**: revisa `shaders/` y `TOUCHDESIGNER.md`.
- **Si quieres auditar el estado técnico**: al final de cada README hay hallazgos, mejoras aplicadas y bloque **“Listo para próxima auditoría”**.
