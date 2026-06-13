// ─────────────────────────────────────────────────────────────────────────────
// zona_torso.glsl — Trigger 2: Rotación de cadera
// Aún Sorprendo · JIFREX · P2 Skeleton Semántico
//
// Respuesta visual: campo de estelas circulares cuya velocidad es proporcional
// al ángulo/velocidad de rotación de la cadera. Las estelas giran exactamente
// al ritmo del movimiento del visitante.
// Lógica de disparo (Python): abs(hip_angle - prev_hip_angle) > 15°.
//
// Entrada  [0]: overlay esqueleto+máscara (input previo de la cadena)
// Uniforms : uHipTrigger (0/1), uHipAngle (deg), uHipVelocity (deg/frame), uTime
//
// En TouchDesigner: GLSL TOP · uniforms desde td_osc_to_uniforms.py
//   uHipTrigger  ← /cuerpo/cadera[0]
//   uHipAngle    ← /cuerpo/cadera[1]   (/cuerpo/metrica/hip_angle)
//   uHipVelocity ← /cuerpo/cadera[2]   (/cuerpo/metrica/hip_velocity)
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[1];
uniform vec4      uTDOutputInfo;
uniform float     uHipTrigger;    // 0 o 1
uniform float     uHipAngle;      // grados — orientación actual de la cadera
uniform float     uHipVelocity;   // grados/frame — velocidad angular suavizada
uniform float     uTime;

in  vec4 vUV;
out vec4 fragColor;

#define TAU 6.28318530718

// ── Paleta cálida (estelas naranja-ocre, contraste con zona_hands) ────────────
vec3 warmPalette(float t) {
    vec3 ocre   = vec3(0.55, 0.35, 0.10);
    vec3 orange = vec3(0.95, 0.55, 0.15);
    vec3 amber  = vec3(1.00, 0.85, 0.55);
    if (t < 0.5) return mix(ocre,   orange, t * 2.0);
    else         return mix(orange, amber,  (t - 0.5) * 2.0);
}

void main() {
    vec2  uv  = vUV.st;
    float ar  = uTDOutputInfo.x / max(uTDOutputInfo.y, 1.0);  // aspect ratio
    vec4  base = texture(sTD2DInputs[0], uv);

    // Centro de la composición (centro de masa proyectado del cuerpo).
    vec2 c = uv - vec2(0.5);
    c.x   *= ar;                       // corrige aspecto para anillos circulares
    float r     = length(c);           // radio desde el centro
    float theta = atan(c.y, c.x);      // ángulo polar

    // ── Velocidad de rotación de las estelas ──────────────────────────────────
    // Proporcional a la velocidad angular de la cadera. Sin movimiento, las
    // estelas casi se detienen; al girar la cadera, aceleran.
    float velN  = clamp(uHipVelocity / 30.0, 0.0, 1.5);   // normaliza ~30°/frame
    float trig  = clamp(uHipTrigger, 0.0, 1.0);
    float spin  = uTime * (0.2 + velN * 4.0) * (0.4 + trig * 0.6);

    // Dirección de giro según el signo del ángulo de cadera (hacia dónde rotó).
    float dir   = sign(uHipAngle == 0.0 ? 1.0 : uHipAngle);

    // ── Campo de estelas circulares ───────────────────────────────────────────
    // Anillos concéntricos modulados por el ángulo polar + rotación temporal.
    float rings  = sin(r * 40.0 - spin * 2.0);
    float swirl  = sin(theta * 6.0 + dir * spin + r * 12.0);
    float trail  = 0.5 + 0.5 * rings * swirl;

    // Las estelas se desvanecen hacia el borde (composición centrada).
    float falloff = smoothstep(0.75, 0.05, r);
    trail *= falloff;

    // Intensidad sube con la velocidad: estelas más vivas al girar rápido.
    float intensity = trail * (0.3 + velN * 0.9);

    vec3 col = warmPalette(clamp(intensity, 0.0, 1.0)) * intensity;

    // Mezcla aditiva con el esqueleto base (las estelas envuelven al cuerpo).
    col = base.rgb + col * (0.5 + trig * 0.5);

    float alpha = clamp(base.a + intensity * 0.7, 0.0, 1.0);
    fragColor = vec4(clamp(col, 0.0, 1.0), alpha);
}
