# Propuesta-4-Stack-Open-Source-Referencia-Antimodular-1

## Página 1

Propuesta 4 — Stack Open Source

a Vi
/

Antimodular : Referente Lozano-Hemmer

Aun Sorprendo : Exposicién Pablo Picasso
Galeria Universitaria Fernando Cano : UAEMEx / FUNIBER - JIFREX

100% Software Libre - Alternativa de Mayor Precisién ML

## Página 2

a a

El Vinculo: Picasso : Lozano-Hemmer - Propuesta 4

mY ae

ao £
oL A \) %
— —

Picasso Lozano-Hemmer Propuesta 4
Pone el proceso mental Pone el proceso perceptivo Conecta ambos en la
del artista en el lienzo. del espectador en el espacio. Galeria Fernando Cano.
El cuadro no existe sin La imagen no existe sin el El piso no existe sin el
la mente que lo piensa. cuerpo que la activa. visitante que lo habita.

El espectador activa la obra. Sin presencia, no hay imagen.
| El cuerpo es su condicidn de existencia. — Rafael Lozano-Hemmer |

## Página 3

DeepLabv3 vs MediaPipe — Condiciones Reales de Galeria

| | MediaPipe Selfie

Ropa del mismo
tono que fondo

Mantiene mascara limpia

| aS

,

¢ Luz proyectada
rebota en cuerpo

0

Contorno estable

O |:

ZOo™,

DeepLabv3 Antimodular
Y)
Y)
Y)

fe

ees L\ Pierde joints Segmenta correctamente
e0Q~ Multiples
COIN sastantes L\ Confunde cuerpos v) Separa siluetas

x £ ¢
£)- DeepLabv3 — disefado para segmentacion semantica de alta precisién en entornos variables.

|

## Página 4

Arquitectura del Sistema — Vista General

Camara RGB 1080p/60fps - OpenCV

Python Headless — Mac M3 Max

Ee * OpenCV preprocesamiento + normalizacién
DeepLabv3 CoreML — Clase 15 person — mascara binaria
Analisis de blobs Antimodular: largest_blob_area - noise_level -
coverage_ratio - Optical Flow Farneback

Syphon GPU->GPU - (0) OSC UDP :9000 -
mascara alta precision meétricas + triggers

(J  TouchDesigner — Mac M3 Max -
oOo Syphon receiver > GLSL shaders Fase 3 JIFREX — Feedback TOP

2x Epson PowerLite 5510 via HDBaseT Cat6A

## Página 5

e “|

Conversion DeepLabv3 — CoreML - Neural Engine M3 Max

Neural Engine
16 nucleos — DeepLabv3

import coremltools as ct

import tensorflow as tf CoreML float16 - 15-25 ms/frame

model = tf.saved_model. load (deepLabv3_mnv2_pascalL)

GPU Metal
40 nucl TouchDesi
mlmodel = ct.convert(model, == gat a tcl

+ GLSL + Feedback TOP

inputs=[ct.ImageType(name=ImageTensor,
shape=(1,513,513,3))],
compute_precision=ct.precision.FLOAT16,

CPU

16 nucleos — OpenCV -

compute_units=ct.ComputeUnit.ALL) gythotmosé-itiagertenic

mlmodel. save (DeepLabV3.mLpackage)

OOO0§ 36 GB RAM unificada — margen amplisimo

al

## Página 6

Viabilidad por Configuracion de Hardware

V) Mac M3 Max sola

(x) MSI Katana sola
MSI + Mac en red

VIABLE — OPTIMA

NO RECOMENDADO

Viable con reservas

CoreML en Neural Engine + TD en GPU Metal.
Sin competencia de recursos.
Configuracién de referencia.

DeepLabv3 CUDA consume los 4 GB VRAM
antes de que TD renderice.

En CPU latencia 50-80 ms — perceptible
visualmente.

MSI corre DeepLabv3 en CPU sin TD,
emite mascara + OSC. Mac renderiza.
Mayor latencia y complejidad de red.

## Página 7

Shaders GLSL Fase 3 JJIFREX) — La Precisi6n Cambia Todo

ZN Con MediaPipe

x) Con DeepLabv3

“== Glitch / Distorsion

Bordes ruidosos = halos irregulares -

dFdx/dFdy amplifica el ruido

Trigger activado también por
oscilacién del modelo ML

Bordes subpixel-accurate — halo
perfectamente uniforme y suave

Trigger activado solo por movimiento
real — Glitch mas dramatico y menos
frecuente

°
“ee Particulas / Estela

MediaPipe

Particulas emergen de aproximacion
del contorno

Particulas emergen del contorno
exacto — incluyendo dedos y cabello

DeepLabv3

## Página 8

& Experiencia del Visitante — Secuencia de la eee

02 |

03 |

04 |

05 |

ENTRADA

Silueta perfectamente definida sobre el piso —
dedos - contorno del cabello - detalles del cuerpo

PRESENCIA

Halo uniforme y preciso. Sin ruido - sin parpadeo.
Como si el cuerpo cortara la luz del proyector.

MOVIMIENTO

Estelas siguen exactamente el contorno.
Particulas emergen del borde real, no de una aproximaci6n.

MOVIMIENTO BRUSCO « TRIGGER

Glitch solo cuando hay movimiento real —
mas raro > mas impactante.

8 HORAS DE EXPOSICION
Estabilidad garantizada.

Ciclo de auditoria MCP puede mejorar la instalacion en tiempo real.

“La precision es el respeto por el visitante.”

fe)

## Página 9

Por Que Propuesta 4

Ventajas técnicas Ventajas conceptuales
DeepLabv3 — precision de bordes ue Genealogia directa con Lozano-Hemmer —
superior en condiciones reales de galeria e declaracién artistica, no solo técnica
a

Referente ya identificado en el

CoreML float16 — Neural Engine
piaiaig documento curatorial

sin competir con TouchDesigner

Repositorio Antimodular — cddigo +> + — Shaders Halo/Glitch/Particulas
probado en museos internacionales +> aprovechan bordes subpixel-accurate

100% software libre — Apache 2.0 -
BSD : MIT - sin dependencias de proveedor

Ciclo de auditoria MCP — mejora en
tiempo real durante la exposicién

a
éy
oe)

Galeria Universitaria Fernando Cano - UAEMEx / FUNIBER - Sistema JIFREX