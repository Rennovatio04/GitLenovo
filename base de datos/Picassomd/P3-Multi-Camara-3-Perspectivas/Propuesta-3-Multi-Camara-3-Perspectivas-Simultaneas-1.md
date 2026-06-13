# Propuesta-3-Multi-Camara-3-Perspectivas-Simultaneas-1

## Página 1

Propuesta 3 — Multi-Camara °
3 Perspectivas Simultaneas

Aun Sorprendo - Exposicién Pablo Picasso
Galeria Universitaria Fernando Cano - UAEMEx / FUNIBER - Sistema JIFREX

L
)

x

Alternativa de alta fidelidad artistica — Mac M3 Max requerida

## Página 2

El Principio Fundamental
del Cubismo — Hecho Literal

“Picasso no pintaba lo que veia.
Pintaba lo que sabia que estaba ahi,
desde todos los angulos posibles a la vez."

Lenguaje de Picasso

Lenguaje del Sistema

Nariz de frente + ojos de perfil

Silueta frontal + lateral + cenital

Multiples puntos de vista

3 camaras en 3 angulos distintos

Simultaneidad como método

3 streams procesados en paralelo

Zonas de superposicion =
maxima informacion

Triple coincidencia =
luz blanca brillante

Vv

TRIPLE COINCIDENCIA
LUZ BLANCA BRILLANTE

## Página 3

Las Tres Perspectivas y Su Significado

O

Camara A — OAK-D Pro W - Frontal

Como nos vemos en un espejo -
Anchura del cuerpo y postura

eee

Les Bleus de Barcelona

Oo

Camara B — Logitech C922 - Lateral Derecha

Como vemos a otros sin que nos vean -
Profundidad en eje Z

eee |

Bailarines sobre cuero

Camara C — Logitech C922 - Cenital

La vista que nunca vemos de nosotros
mismos : Huella en el espacio

ea

Genevieve sobre papel Japon

## Página 4

Arquitectura del Sistema — Vista General

Camara A Camara B Camara C
OAK-D Pro W Logitech C922 Logitech C922
TB4 #1 TB4 #2 TB4 #3

depth + RGB RGB RGB

Instancia MediaPipe #1 Instancia MediaPipe #2 Instancia MediaPipe #3
mascara_a - flow_a mascara_b - flow_b mascara_c - flow_c

J

Python headless
3 hilos en paralelo - Neural Engine M3 Max
Sincronizacion < 33 ms
OSC compuesto - Syphon GPU->GPU

J

| TouchDesigner — Mac M3 Max

Syphon x3 - Composite TOP Screen - GLSL TOP - Feedback TOP
2x Epson PowerLite 5510 via HDBaseT Cat6A

## Página 5

CRITICO — Un Puerto Thunderbolt 4 por Camara

Tres camaras en un hub USB compartido producen frame drops
y desincronizacién que destruyen el efecto artistico.

CORRECTO

CamaraA - 40 Gbps dedicados

CamaraB + 40 Gbps dedicados

CamaraC + 40 Gbps dedicados

Proyector ~- Independiente

() INCORRECTO

HubUSB > CamaraA

HubUSB —> CamaraB

HubUSB -> CamaraC

Frame drops : Desincronizacion - Efecto artistico destruido

Device

O44 TB4#1 Camara A

Os TB4#2 Camara B

Os TB4#3 Camara C

HDMI Proyector

Bandwidth
40 Gbps dedicados
40 Gbps dedicados
40 Gbps dedicados

Independiente

## Página 6

Sincronizacion de 3 Streams — El Mayor Desafio Tecnico

Las 3 camaras capturan a frecuencias distintas —
sus timestamps no estan sincronizados.

33 ms
1
'
1
\
Frame A—T+Oms > / OK —-------- pe eres a ca a ee ag ner goa e enna
'
Frame B—T#15ms > OK 9 wanna ene eeeeen ence enee @--- = 2-H ene nee dona nnn n enn ne ence nee nner
\
\
Frame C—T+28ms > / OK — ~~~ -- =~ == 2-22 nen nnn nnn enn eee @---4----------------------------------------------
1
\
Frame B — T+50 ms — > DESCARTADO — seusa frame anterior -------------------------- 4 BA oe @---------------
\
t t t 1 t t t >
Oms 10 ms 20 ms 30 ms 40 ms 50 ms 60 ms
Vani
[_ ventana de sincronizacion: 33 ms = 1 frame a 30 fps | | a ))
(SY

## Página 7

Hardware — Por Que Solo la Mac M3 Max

MacBook Pro M3 Max ©) OPTIMA MSI Katana ®) NO viable

40 nucleos GPU -

TouchDesigner con 3 texturas Syphon
+ shaders multicapa. ~2.3—2.8 GB
usados de 36 GB

4 GB VRAM —

3 texturas + TD + Feedback TOP =
~3.5 GB estimados. Margen < 500 MB.
Colapso en cualquier pico

? 16 nucleos Neural Engine -
-o 3 instancias MediaPipe en paralelo,
& una por hilo dedicado

36 GB RAM unificada - 400 GB/s -
ooog Total estimado ~4.5—6 GB —
margenamplisimo P| Sin Thunderbolt 4 —
3 puertos Thunderbolt 4 - 3 camaras por USB 3.0 compartido,
Un bus dedicado por camara — sin ancho de banda garantizado

sin contencién

Throttling térmico —
RTX 3050 Mobile se degrada
en sesiones de 8 horas

## Página 8

Shaders GLSL — Composicion Multicapa : Fase 3 JIFREX

// 1. Muestreo de mascaras (siluetas)

float mask_a = texture(uMaskA, vUV).r;
float mask_b = texture(uMaskB, vUV).r;
float mask_c = texture(uMaskC, vUV).r;

// 2. Colores asignados a cada mascara

vec3 col_a = vec3(0.09, 0.35, 0.95);
vec3 col_b vec3(@.95, 0.66, 0.12);
vec3 col_c = vec3(0.95, 0.38, 0.65);

// 3. Aplicar mascaras a los colores
col_a *= mask_a;
col_b *= mask_b;
col_c *= mask_c;

// 4. Composicion final con Screen blend

// frontal
// lateral
// cenital

vec3 result = 1.0 - (1.0 - col_a) * (1.0 - col_b) * (1.0 - col_c);

// zonas de triple superposicién > blanco > cubismo

fragColor = vec4(result, 1.0);

Composici6n multicapa

* Combina 3 siluetas con colores
diferenciados

* Triple coincidencia — blanco brillante

Distorsion de perspectiva

* Transformaciones UV por angulo

real en espacio 2D

Particulas por perspectiva

¢ Frontal: expansion radial

+ Lateral: traslacion horizontal
* Cenital: dispersion en espiral

## Página 9

1
x<

periencia del Visitante — Secuencia

ENTRADA -— Tres halos de color aparecen sobre el piso - Azul - Ocre - Rosa
SILUETA FRONTAL azul — Contorno principal, como en un espejo

SILUETA LATERAL ocre — El perfil que ves de otros, nunca de ti mismo

SILUETA CENITAL rosa — La vista desde arriba que nunca has visto
de tu propio cuerpo

COMPOSICION DINAMICA — Triple coincidencia: LUZ BLANCA -
Doble: mezcla de colores - Simple: color puro

CADA MOVIMIENTO — Reorganiza la composicién de manera Unica —
la experiencia es siempre nueva

ll @ Grp

@+@-O-@): @@

“El visitante se ve a si mismo como Picasso vela a sus modelos:
desde todos los angulos a la vez.”

ee

## Página 10

Fases de Implementacion — Propuesta 3

Shaders GLSL +
() Calibracién

Configuracién Pipeline de Composicién en
Multicamara Visién x3 TouchDesigner

gb

-

lk Cc) eae
ord

Shader composicién multicapa

(2)

OAK-D Pro W en Python DepthAl

SDK 3 mascaras en tiempo real ¢ 3 Syphon receivers
2x Logitech C922 en TB4 #2 y #3 © Syphon x3 (una textura por camara) © Composite TOP modo Screen Shader distorsién UV
3 hilos de captura paralelos * OSC compuesto con métricas ¢ Transparencias por perspectiva Calibracién puntos en el piso

Verificacién sincronizacién < 33 ms por camara ¢ Feedback TOP multicapa Prueba de 8 horas continuas

y,
Mac M3 Max — Configuracion de Referencia )
+ La propuesta mas fiel al cubismo _