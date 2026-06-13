// ─────────────────────────────────────────────────────────────────────────────
// halo_glow.glsl — Shader 1: Halo / Glow
// Aún Sorprendo · JIFREX · Fase 3
//
// Entrada  [0]: máscara binaria (NDI desde MSI)
// Uniforms : uFlowMean (float) — intensidad del halo proporcional al movimiento
// Técnica  : dFdx/dFdy detectan bordes subpixel → distancia → halo suave
//
// En TouchDesigner: GLSL TOP · Uniform DAT con uFlowMean conectado a OSC CHOP
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[1];
uniform vec4      uTDOutputInfo;   // .xy = resolución, .zw = 1/resolución
uniform float     uFlowMean;       // 0.0 – 1.0+  desde OSC /jifrex/flow_mean
uniform float     uTime;           // segundos — conectar a Beat CHOP o Timer CHOP

in  vec4 vUV;
out vec4 fragColor;

// ── Paleta cubista (azul-plata, referencia Les Bleus de Barcelona) ────────────
vec3 palette(float t) {
    vec3 blue   = vec3(0.09, 0.35, 0.95);
    vec3 white  = vec3(0.90, 0.92, 1.00);
    vec3 silver = vec3(0.60, 0.65, 0.75);
    if (t < 0.5) return mix(silver, blue,  t * 2.0);
    else         return mix(blue,   white, (t - 0.5) * 2.0);
}

void main() {
    vec2 uv  = vUV.st;
    vec2 px  = uTDOutputInfo.zw;   // tamaño de un pixel en UV

    float mask = texture(sTD2DInputs[0], uv).r;

    // ── Detección de borde vía derivadas parciales ────────────────────────────
    float dx = dFdx(mask);
    float dy = dFdy(mask);
    float edge = sqrt(dx * dx + dy * dy);   // magnitud del gradiente en borde

    // ── Distancia al borde via blur radial (16 muestras) ─────────────────────
    float edgeDist = 0.0;
    int   samples  = 16;
    float radius   = 0.025;   // radio del halo en UV (~25 px en 1280px)
    for (int i = 0; i < samples; i++) {
        float angle = (float(i) / float(samples)) * 6.28318;
        vec2  offset = vec2(cos(angle), sin(angle)) * radius;
        float s = texture(sTD2DInputs[0], uv + offset * px * 40.0).r;
        edgeDist += s;
    }
    edgeDist /= float(samples);

    // ── Intensidad del halo: mayor flujo = halo más brillante ────────────────
    float haloIntensity = edgeDist * (1.0 + uFlowMean * 2.5);
    haloIntensity       = clamp(haloIntensity, 0.0, 1.0);

    // ── Pulso suave sincronizado con movimiento ───────────────────────────────
    float pulse = 0.85 + 0.15 * sin(uTime * 3.0 + uFlowMean * 8.0);

    // ── Silueta base + halo coloreado ────────────────────────────────────────
    vec3 haloColor = palette(haloIntensity * pulse);
    vec3 col       = mask * vec3(0.85, 0.90, 1.00)        // silueta blanca fría
                   + haloIntensity * haloColor * pulse;    // halo coloreado

    // ── Edge highlight (línea de borde nítida) ────────────────────────────────
    float edgeLine = clamp(edge * 8.0, 0.0, 1.0);
    col += edgeLine * vec3(0.6, 0.8, 1.0) * (1.0 + uFlowMean);

    float alpha = clamp(mask + haloIntensity * 0.8, 0.0, 1.0);

    fragColor = vec4(col, alpha);
}
