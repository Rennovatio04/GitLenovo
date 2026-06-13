# Propuesta-1-RealSense-D435i-NDI-1

## Página 1

Propuesta 1 —
RealSense D4351 + ND

Aun Sorprendo : Exposicién Pablo Picasso” be hes cal

Galeria Universitaria Fernando Cano - UAEMEx / FUNIBER

() IMPLEMENTADA — Fases 1 y 2 completadas - Fase 3 en desarrollo

## Página 2

El Vinculo con Picasso

66

El cubismo no es
una manera de ver
es una manera

de pensar. ,,

Pablo Picasso

Lenguaje de Picasso

Lenguaje del sistema

Descomponer un
rostro en vistas
simultaneas

Fragmentar la nube
de puntos 3D
en planos

Ver al sujeto desde
todos los angulos

Camara de profundidad
captura el volumen
completo

## Página 3

Arquitectura del Sistema — Vista General

Intel RealSense D435i
y

Python Headless — MSI Windows
+ Nube de puntos 3D + 17 joints + Optical Flow + Trigger logic

L L

Disco local mask.png gp NDI en red ~8 ms

[ ~l\\- OSC UDP :9000 por LAN < 2 ms

HH TouchDesigner — Mac M3 Max
+ Shaders GLSL Metal + Feedback TOP
2x Epson PowerLite 5510

Techo 4.5 m - 20° inclinacién - Zona 4.5 m x 3m

## Página 4

Hardware — Dos Maquinas, Roles Separados

MSI Katana GF66 Pe MacBook Pro M3 Max
- Servidor de Vision aa - Servidor de Render

¢ Intel Core i5-11400H - 6C/12T - 4.5 GHz ¢ M3 Max: 16C CPU - 40C GPU

¢ RTX 3050 Mobile 4 GB VRAM — no renderiza ¢ 36 GB RAM unificada a 400 GB/s

¢ 64 GB DDR4 RAM ¢ macOS - Syphon - TouchDesigner

¢ Windows 11 — Unico SO RealSense compatible ¢ Z\ INCOMPATIBLE con RealSense D435i

e Python 3.11 - pyrealsense2 - OpenCV - NDI SDK

‘©, Captura > Procesa > Emite OSC + NDI Recibe NDI > Shaders Metal > Proyecta

v) MSI + Mac = Arquitectura OPTIMA

## Página 5

Camara + Proyectores — Specs Clave

Tecnologia:

Estéreo activo infrarrojo

Resolucion depth:

1280x720 @ 30 fps

Alcance util:

0.3 m- 3.0m

Campo de visi6n:

87° x 58°

SDK:

pyrealsense2 — solo Windows/Linux

~) Funciona con cualquier iluminacién — IR activo, no depende de luz visible

Luminosidad:

5,500 lumenes

Resolucion:

WUXGA 1920x1200

Throw calculado:

~4.79 m — imagen ~2.4 m ancho

Cableado:

HDBaseT Cat6A hasta 100 m sin repetidor

Montaje:

C-clamps - cable de acero obligatorio - 10.8 kg c/u

## Página 6

Pipeline — webcam_runtime.py (30 fps)

|

<< 4 _ _-_e_<_

POV @@ © ® ©

)) GD xa 2 Il Do FB

=~
—
fe}
~~
wa

Captura — frame depth + RGB via pyrealsense2
Alineacién — depth con RGB > coordenadas 3D
Segmentacién — mascara binaria con umbral adaptativo
Optical Flow Farneback — flow_mean + motion_ratio
Analisis de blobs — largest_blob_area + noise_level
Légica de trigger — decide si hay evento visual
Escritura atomica — latest_mask.png via os.replace()

Emit OSC > puerto 9000 Mac

Stream NDI > mascara en tiempo real ~8 ms

Sin interfaz grafica -
ciclo continuo por frame

## Página 7

Logica de Trigger — Anti-Falsos Positivos

NO = ignorar

i 2
(sombra, reflejo) pe lom ee O0lex:

NO — persona

a z iflow_mean > 0?
estatica, no disparar ae

NO — esperar

30 frames (~1 s) ~Cooldown = 0?

AREA_THRESHOLD: Optical Flow: COOLDOWN:

500 px minimo - flow_mean = 0 — no dispara - 30 frames ~1s-
Elimina sombras y reflejos Persona estatica no genera evento Cada explosion es evento discreto

## Página 8

Shaders GLSL — Fase 3 - A cargo de JIFREX

Halo / Glow

y= |

<

TECNICA
dFdx/dFdy detectan bordes - edgeDist * (1 + uFlowMean)

Glitch / Distorsion

TECNICA

Desplazamiento UV con sin/cos - uMotionRatio * 0.02

Particulas / Estela

TECNICA

Particle SOP + Feedback TOP opacidad < 1

CONTROLADO POR
flow_mean via uniform uFlowMean

CONTROLADO POR
trigger_triggered + motion_ratio

CONTROLADO POR
flow_mean - densidad <— motion_ratio

(ex Folder DAT hot-reload — TouchDesigner recarga shaders automaticamente

## Página 9

Experiencia del Visitante — Secuencia

REPOSO DETECCION PRESENCIA MOVIMIENTO LENTO MOVIMIENTO BRUSCO 3K
Piso con patrones Nube de puntos 3D Silueta fragmentada en Halos suaves + estelas Trigger - Glitch +
geométricos abstractos detecta presencia - planos geométricos - Feedback TOP particulas emanando
funciona con distintos angulos y
cualquier luz opacidades
= >

Quietud > 3 s — Fade gradual — Reposo

“El cuerpo del visitante se convierte en el lienzo. Cada movimiento es un trazo.”

rN Piso de parquet reflectante amplifica efecto — segunda capa de luz fragmentada

## Página 10

Estado del Proyecto y Proximos Pasos

V) Fase 1 — Ecosistema MCP ©) Completada Sage NS
venv - mcp_bridge.py - Repositorio Antimodular indexado lene | : : I
ae os DA a
V) Fase 2 — Interconectividad ™) Completada ee ae
webcam_runtime.py - OSC mapeado - NDI MSI<+Mac funcional ‘s
eS

se5

“xs, Fase 3 — Estética y Shaders C Pendiente JIFREX
Le

N ; Shader Halo - Shader Glitch + Particulas + Feedback TOP -
Calibracién en sala - main_v1.toe

see

Rafael Lozano-Hemmer RealSense TouchDesigner N DI 4
/ Antimodular SDK 2.0 + Metal + Syphon NewTek mS

Sistema de Proyeccién Reactiva Interactiva - JIFREX - UAEMEx / FUNIBER