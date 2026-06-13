// ─────────────────────────────────────────────────────────────────────────────
// zona_head.glsl — Trigger 3: Inclinación de cabeza
// Aún Sorprendo · JIFREX · P2 Skeleton Semántico
//
// Respuesta visual: transición de paleta de color completa. La temperatura del
// color de TODA la proyección varía con el pitch/roll de la cabeza — inclinar
// la cabeza "tiñe" la sala. Roll → eje frío↔cálido; pitch → brillo/saturación.
// Lógica de disparo (Python): roll = atan2(nose.y - ear.y, nose.x - ear.x).
//
// Entrada  [0]: salida acumulada de la cadena (esqueleto + zonas previas)
// Uniforms : uHeadTrigger (0/1), uHeadRoll (deg), uHeadPitch (deg), uTime
//
// En TouchDesigner: GLSL TOP · uniforms desde td_osc_to_uniforms.py
//   uHeadTrigger ← /cuerpo/cabeza[0]
//   uHeadRoll    ← /cuerpo/cabeza[1]   (/cuerpo/metrica/head_roll)
//   uHeadPitch   ← /cuerpo/cabeza[2]   (/cuerpo/metrica/head_pitch)
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[1];
uniform vec4      uTDOutputInfo;
uniform float     uHeadTrigger;   // 0 o 1
uniform float     uHeadRoll;      // grados — inclinación lateral
uniform float     uHeadPitch;     // grados — inclinación arriba/abajo
uniform float     uTime;

in  vec4 vUV;
out vec4 fragColor;

// ── Conversión a luma para preservar contraste al recolorear ──────────────────
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

// ── Rotación de matiz en el espacio RGB (aproximación rápida) ─────────────────
vec3 hueShift(vec3 col, float angle) {
    const vec3 k = vec3(0.57735);              // eje de gris normalizado
    float cosA = cos(angle);
    return col * cosA
         + cross(k, col) * sin(angle)
         + k * dot(k, col) * (1.0 - cosA);
}

// ── Gradiente de temperatura de color (frío ↔ cálido) ─────────────────────────
vec3 temperature(float t) {
    // t: 0 = muy frío (azul) · 0.5 = neutro · 1 = muy cálido (ámbar/rojo)
    vec3 cold = vec3(0.30, 0.55, 1.00);
    vec3 neut = vec3(0.85, 0.85, 0.85);
    vec3 warm = vec3(1.00, 0.55, 0.25);
    if (t < 0.5) return mix(cold, neut, t * 2.0);
    else         return mix(neut, warm, (t - 0.5) * 2.0);
}

void main() {
    vec2 uv = vUV.st;
    vec3 base = texture(sTD2DInputs[0], uv).rgb;
    float a   = texture(sTD2DInputs[0], uv).a;

    // ── Roll de la cabeza → posición en el eje de temperatura ─────────────────
    // Rango útil ±45°. Inclinar a un lado enfría, al otro calienta.
    float rollN  = clamp(uHeadRoll / 45.0, -1.0, 1.0);
    float tempT  = 0.5 + rollN * 0.5;          // 0..1

    // ── Pitch → intensidad/saturación de la tinción ──────────────────────────
    float pitchN = clamp(abs(uHeadPitch) / 45.0, 0.0, 1.0);

    // Solo aplicamos la transición cuando el gesto está activo; si no, el
    // recoloreo es sutil (la sala "respira" hacia neutro).
    float trig  = clamp(uHeadTrigger, 0.0, 1.0);
    float amount = mix(0.15, 0.9, trig) * (0.4 + pitchN * 0.6);

    // Recolorea preservando el contraste (luma del original × paleta de temp).
    float l        = luma(base);
    vec3  tempCol  = temperature(tempT) * (l + 0.15);

    // Hue shift continuo extra para que la transición sea envolvente, no plana.
    float hueAngle = rollN * 1.2 + sin(uTime * 0.3) * 0.05;
    vec3  shifted  = hueShift(base, hueAngle);

    vec3 graded = mix(shifted, tempCol, amount);

    // Viñeta cálida/fría según pitch (mira arriba = más luz en la parte alta).
    float vgn = 1.0 - 0.25 * length(uv - vec2(0.5, 0.5 - uHeadPitch * 0.004));
    graded *= clamp(vgn, 0.6, 1.0);

    fragColor = vec4(clamp(graded, 0.0, 1.0), a);
}
