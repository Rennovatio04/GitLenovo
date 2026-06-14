// ─────────────────────────────────────────────────────────────────────────────
// halo_glow.glsl — Shader 1: Halo / Glow por movimiento
// Aún Sorprendo · JIFREX · P1 · RealSense D435i + NDI
//
// CONCEPTO ARTÍSTICO:
//   La respuesta más sutil del sistema. El borde de la silueta adquiere
//   un halo azulado que respira y pulsa con el movimiento del visitante.
//   Referencia directa a "Les Bleus de Barcelona" de Picasso: la paleta
//   azul-plata es la misma temperatura de color de la Época Azul.
//   A mayor velocidad de movimiento, más brillante y cálido el halo.
//
// QUÉ DEBERÍAS VER:
//   - Visitante quieto: silueta blanca fría con halo azul muy tenue pulsando
//   - Movimiento lento: aureola azulada visible alrededor de toda la silueta
//   - Movimiento rápido (flow > 1.0): halo azul-blanco brillante, palpitando
//   - Sin nadie: negro completo (alpha = 0)
//
// TÉCNICA:
//   1. dFdx/dFdy detectan el borde de la máscara (transición 0→1 del NDI)
//   2. Un muestreo radial de 16 puntos calcula la "distancia al borde" aproximada
//   3. La intensidad del halo combina esa distancia con uFlowMean
//   4. La paleta interpola plata→azul→blanco según la intensidad
//
// Entrada  [0]: máscara binaria (NDI desde MSI) — canal R: 0.0 o 1.0
// Uniforms : uFlowMean (flow_mean del optical flow) · uTime (tiempo del patch)
//
// En TouchDesigner: GLSL TOP · uniforms actualizados por osc_to_uniforms Script DAT
//   uFlowMean ← OSC /jifrex/flow_mean   (rango real 0.0–3.0)
//   uTime     ← absTime.seconds         (conectar manualmente en TD)
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[1];
uniform vec4      uTDOutputInfo;   // .xy = resolución en px, .zw = 1/resolución (tamaño de 1px en UV)
uniform float     uFlowMean;       // 0.0 – 3.0+  magnitud promedio del optical flow
uniform float     uTime;           // segundos — conectar a absTime.seconds en TD

in  vec4 vUV;
out vec4 fragColor;

// ── Paleta cubista (azul-plata, referencia directa a Les Bleus de Barcelona) ─────
// t=0.0 → plata (silueta en reposo)
// t=0.5 → azul oscuro (movimiento medio)
// t=1.0 → blanco frío (movimiento intenso)
vec3 palette(float t) {
    vec3 blue   = vec3(0.09, 0.35, 0.95);   // azul JIFREX (mismo que COLOR_A en P3)
    vec3 white  = vec3(0.90, 0.92, 1.00);   // blanco frío — máximo movimiento
    vec3 silver = vec3(0.60, 0.65, 0.75);   // plata — reposo
    if (t < 0.5) return mix(silver, blue,  t * 2.0);       // plata → azul (primera mitad)
    else         return mix(blue,   white, (t - 0.5) * 2.0); // azul → blanco (segunda mitad)
}

void main() {
    vec2 uv  = vUV.st;
    vec2 px  = uTDOutputInfo.zw;   // tamaño de 1 píxel en coordenadas UV

    // La máscara NDI llega como canal rojo: 0.0 = fondo, 1.0 = persona
    float mask = texture(sTD2DInputs[0], uv).r;

    // ── Detección de borde vía derivadas parciales ────────────────────────────
    // dFdx y dFdy calculan el cambio del valor de la máscara entre píxeles adyacentes.
    // En el interior de la silueta: mask varía poco → dx y dy son ~0
    // En el borde de la silueta: mask salta de 0 a 1 → dx y dy son grandes
    // La magnitud del gradiente (sqrt(dx²+dy²)) es alta solo en el borde.
    float dx = dFdx(mask);
    float dy = dFdy(mask);
    float edge = sqrt(dx * dx + dy * dy);   // 0 en interior/fondo, >0 en borde

    // ── Distancia al borde vía muestreo radial (16 puntos) ───────────────────
    // Muestreamos 16 puntos en un radio r=0.025 UV alrededor del pixel actual.
    // Promediamos los valores de máscara en esos 16 puntos.
    // Si estamos cerca de la silueta: varios de los 16 puntos tendrán mask=1 → promedio alto
    // Si estamos lejos de la silueta: todos los puntos tienen mask=0 → promedio ~0
    // Esto crea el "brillo que se extiende desde la silueta hacia afuera".
    float edgeDist = 0.0;
    int   samples  = 16;
    float radius   = 0.025;   // radio del halo en UV (~25 px en imagen de 1280px)
    for (int i = 0; i < samples; i++) {
        float angle  = (float(i) / float(samples)) * 6.28318;  // 2π distribuido en 16 pasos
        vec2  offset = vec2(cos(angle), sin(angle)) * radius;
        // px * 40.0 convierte el offset UV a píxeles reales de la textura
        float s = texture(sTD2DInputs[0], uv + offset * px * 40.0).r;
        edgeDist += s;
    }
    edgeDist /= float(samples);   // promedio: 0.0 (lejos de silueta) → 1.0 (dentro)

    // ── Intensidad del halo: mayor flujo = halo más brillante ────────────────
    // uFlowMean = 0 → factor = 1.0 (halo mínimo)
    // uFlowMean = 1 → factor = 3.5
    // uFlowMean = 2 → factor = 6.0 (halo máximo visible)
    float haloIntensity = edgeDist * (1.0 + uFlowMean * 2.5);
    haloIntensity       = clamp(haloIntensity, 0.0, 1.0);

    // ── Pulso suave sincronizado con movimiento ───────────────────────────────
    // sin(uTime * 3.0): oscila 3 veces por segundo (lento, como respiración)
    // + uFlowMean * 8.0: desplaza la fase del seno según la velocidad —
    //   más movimiento = oscilación más acelerada en fase (no en frecuencia)
    // Resultado: 0.85 + 0.15 * sin(...) → oscila entre 0.70 y 1.00
    // A mayor movimiento, la pulsación "apura" en lugar de hacerse más rápida.
    float pulse = 0.85 + 0.15 * sin(uTime * 3.0 + uFlowMean * 8.0);

    // ── Silueta base + halo coloreado ────────────────────────────────────────
    // La silueta tiene un color blanco-frío fijo (base de la figura).
    // El halo agrega color proporcional al movimiento encima de la silueta.
    vec3 haloColor = palette(haloIntensity * pulse);
    vec3 col       = mask * vec3(0.85, 0.90, 1.00)        // silueta blanca fría
                   + haloIntensity * haloColor * pulse;    // halo coloreado proporcional

    // ── Línea de borde nítida (arista del cuerpo) ─────────────────────────────
    // edge es la magnitud del gradiente — alta solo en el borde de la máscara.
    // Multiplicar × 8 lo convierte en una línea binaria (0 ó ~1).
    // Color azul-blanco claro, intensidad escala con flow para que "brille más"
    // cuanto más rápido se mueve el visitante.
    float edgeLine = clamp(edge * 8.0, 0.0, 1.0);
    col += edgeLine * vec3(0.6, 0.8, 1.0) * (1.0 + uFlowMean);

    // ── Alpha: la silueta es opaca, el halo es semitransparente ──────────────
    // mask = 1 dentro de la silueta → alpha = 1 (completamente opaco)
    // haloIntensity * 0.8 fuera de la silueta → alpha proporcional al halo
    float alpha = clamp(mask + haloIntensity * 0.8, 0.0, 1.0);

    fragColor = vec4(col, alpha);
}
