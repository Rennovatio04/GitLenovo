# Propuesta-2-Skeleton-Semantico-MediaPipe-Holistic-1

## Página 1

Propuesta 2 —Skeleton.semantico
| Nl eee
MediaPipe Holistic - Sistema de Proyeccién Reactiva Interactiva
| a a TN
Aun Sorprendo - Exposicién Pablo Picasso \Galeria Fernando Cano UAEMEx / FUNIBER

Alternativa Documentada - JIFREX

## Página 2

éQue hace este sistema?

0)
fi
"El cuerpo no activa la
instalacion — la conversa con ella.”

Cada parte del cuerpo que se mueve dispara
una respuesta visual diferente.

## Página 3

Cubismo como gramatica del movimiento

Oo

El Vinculo con Picasso

Sistema base
(silueta binaria)

Propuesta 2
(skeleton semantico)

Detecta presencia

Detecta qué parte se mueve

Una respuesta visual

Respuesta diferente por zona

El visitante activa

El visitante conversa

Presencia = evento

Gesto especifico = evento especifico

“La mano de Picasso no dibujaba lo mismo que su ojo veia.”._ ———————

## Página 4

Arquitectura del Sistema — Vista General

Webcam RGB 1080p / 60 fps

Python headless - MediaPipe Holistic
zona_upper zona_lower zona_hands zona_head

PIN | ©

OSC semantico :9000
/cuerpo/mano_derecha Spout / Syphon GPU>GPU
/cuerpo/cadera GPU

/cuerpo/cabeza ~1 ms latencia
/cuerpo/pose_estatica

TouchDesigner
OSC In CHOP = Select CHOP por zona — shaders por zona corporal

2x Epson PowerLite 5510

## Página 5

Los 17 Joints — Mapa del Cuerpo

MediaPi
Joint (nombre) a eee éQué detecta el sistema?
Angulo con arctan2 © Hombre izquterdo u Abertura de brazos
6% arctan2(y, x) (abduccién/aduccion)
Abertura de brazos
OuHomproiderestio a (abduccién/aduccién)
zona_upper - Pauanui Extension vs flexién
quierdo 13
Hombros, codos, o dakeotle
mufiecas Extension vs flexion
© Codo derecho 14 delicede'
“ cone Extension vs flexion
© Mufeca izquierda 15 de laimunecs
L] zona_lower _ © Mufeca derecha 16 ena peviexien
Caderas, rodillas eco
en Rotacién lateral
0 Cadera izquierda 23 dalnicadera
Rotacié6n lateral
zona_head - C1 Cadera derecha 24 de la cadera
Pitch y roll = Cuclillas 0 salto
01 Rodilla izquierda 25 (flexién/extensién)
25 26 ' Cuclillas 0 salto
yen C1 Rodilta derecha 26 (flexidn/extensidn)
{ . Centro de masa - A Nariz 0 Inclinacién (pitch)
\-¢  Promedio hombros arriba/abajo
+ caderas ae Inclinacién (roll)
A. Oido izquierdo 3 inclinacién lateral
" Inclinacién (roll)
A. Oido derecho e inclinacién lateral
Teg ees Has = Promedio hombros
Ne +caderas

## Página 6

Triggers Semanticos por Zona Corporal

Zona / Gesto

‘i 1. Mano extendida

Respuesta Visual

Planos geométricos fragmentados
cubistas

Logica de Deteccion

landmark[16].y < landmark[12].y - umbral

> 2. Rotacién de cadera
A
(\, 3. Inclinacién de cabeza

Velocidad de estelas proporcional
al Angulo

Cambio de paleta de color completa

abs(hip_angle - prev_hip_angle) > 15°

atan2(nose.y - eary, nose.x - ear.x)

ie 4. Salto / movimiento brusco

A
(} © 5. Pose estatica > 3s

f) f) 6. 2 personas simultaneas
Exclusivo de esta propuesta

Glitch + particulas maximas

Fade gradual — reposo

Didlogo cubista entre cuerpos

motion_ratio > 0.7

flow_mean < 0.5 durante 90 frames

blob_count > 1 + dos centros de masa

## Página 7

Hardware — Compatibilidad Universal

MSI Katana GF66 11UC -
Opcion de una sola maquina
me.”

MediaPipe Holistic en CPU i5-11400H
a 30 fps sin GPU

4 GB VRAM completamente libres
para TouchDesigner

¢ Spout GPU GPU ~1 ms latencia
¢ Camara Logitech C922 Pro o BRIO

MacBook Pro M3 Max -
Opcion ideal

e Neural Engine 16 nucleos dedicados
aislado del render

¢ 40 nucleos GPU libres para TouchDesigner
¢ Syphon reemplaza Spout sin

diferencia funcional
¢ 36 GB RAM sin cuello de botella

MSI sola |

Y) Viable — recomendada
Mac sola | Y) Viable — muy cOmoda
MSI + Mac | Y) Viable — dptima pero innecesaria

## Página 8

ropa similar
al fondo >
degradacion

de joints

luz directa
en camara >
pérdida de

precision angular

/\ Limitacion Critica — Iluminacion de Galeria

ersonas
p , |, sombras
cruzando al ~ -  fuertes >
fondo — 7% joints mal
confusidén del estimados
modelo

Shaders GLSL por Zona Semantica

ny zona_hands

Planos geométricos emergentes

G) Visita técnica a la Galeria Fernando Cano antes de confirmar esta propuesta.

paleta fria azul-blanco

ia zona_torso
O zona_head

Campo de estelas circulares

Transicién de paleta completa

paleta calida naranja-ocre

temperatura variable pitch

& Global trigger

Glitch + particulas maximas

motion_ratio > 0.7

## Página 9

Experiencia del Visitante — Secuencia Narrativa

ENTRADA

El sistema reconoce la presencia

BRAZO ARRIBA

Planos geométricos emergen de la posicién de la mano

ROTACION DE CADERA

Estelas del suelo giran al ritmo exacto del movimiento

INCLINACION DE CABEZA

Toda la proyeccién cambia de temperatura de color

QUIETUD > 3s

Fade lento — la proyeccién espera

—S ©)

“El visitante aprende el lenguaje de la instalacion.
Al final, se mueve diferente — con intencidn.”

## Página 10

Propuesta 2 — Por que Elegirla

r

r

Semantica
corporal

Dos visitantes
simultaneos

Cada zona del cuerpo genera una
respuesta visual distinta. No hay
instalacion equivalente en la
exposicion.

Exclusivo de esta propuesta:
didlogo cubista entre cuerpos.
blob_count > 1 activa
composicion dual.

Hardware
universal

Funciona en MSI sola, Mac sola,
o ambas. MediaPipe no toca
la GPU de render.

Entorno
XX Pendiente

Ldgica semantica
¥ Pendiente

Integracion TD
X Pendiente

Calibracion en sala
 Pendiente

Memo Akten - MediaPipe Apache 2.0 - Rafael Lozano-Hemmer - Bailarines de Picasso (afios 40-50)

Sistema de Proyeccién Reactiva Interactiva - JIFREX