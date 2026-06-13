// ─────────────────────────────────────────────────────────────────────────────
// glitch_precise.glsl — Glitch/Distorsión sin falsos triggers
// Aún Sorprendo · JIFREX P4 · DeepLabv3 + CoreML
//
// Versión mejorada de P1/glitch.glsl.
//
// El problema de P1 con MediaPipe: el modelo produce pequeñas oscilaciones
// en los bordes (jitter de estimación) que el sistema interpretaba como
// movimiento, disparando el glitch con más frecuencia de lo deseado.
//
// Con DeepLabv3:
//   - Bordes estables entre frames (sin jitter de modelo)
//   - El optical flow solo detecta movimiento real del cuerpo
//   - El glitch se dispara MENOS veces pero cada disparo es más impactante
//   - "La precisión es el respeto por el visitante" — Propuesta 4
//
// El algoritmo es idéntico a P1 — la mejora viene del input limpio.
// uNoiseLevel (Antimodular): ruido de blobs → amplifica el glitch en escenas
// con múltiples personas (más caos visual = más glitch = más Picasso).
//
// Inputs:
//   [0] = halo_glow_precise TOP (frame procesado)
//   [1] = máscara DeepLabv3 (para confinar la distorsión)
//
// Uniforms (par.value0…par.value3):
//   value0 = uTrigger      (OSC /jifrex/p4/trigger)
//   value1 = uMotionRatio  (OSC /jifrex/p4/motion_ratio)
//   value2 = uNoiseLevel   (OSC /jifrex/p4/noise_level)  ← nuevo P4
//   value3 = uTime         (absTime.seconds)
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[2];
uniform vec4      uTDOutputInfo;

uniform float uTrigger;      // 0 o 1 — trigger anti-FP
uniform float uMotionRatio;  // 0.0–1.0
uniform float uNoiseLevel;   // 0.0–N — blobs pequeños / Antimodular
uniform float uTime;

in  vec4 vUV;
out vec4 fragColor;

float hash(float x) { return fract(sin(x * 127.1) * 43758.5453); }

void main() {
    vec2 uv = vUV.st;

    // Pass-through cuando no hay trigger — el frame sigue limpio
    if (uTrigger < 0.5) {
        fragColor = texture(sTD2DInputs[0], uv);
        return;
    }

    float t  = uTime;
    float mr = clamp(uMotionRatio, 0.0, 1.0);
    float nl = clamp(uNoiseLevel,  0.0, 2.0);    // noise level Antimodular

    // ── Flash blanco en el momento del trigger ─────────────────────────────────
    // flashAge: tiempo desde el trigger (reconstruido como ciclo continuo)
    float flashAge = fract(t * 0.5) * 2.0;
    float flash    = exp(-flashAge * 10.0) * 0.40;

    // ── Bandas de glitch: cada banda tiene su desplazamiento horizontal ────────
    float bandFreq = 8.0 + mr * 12.0 + nl * 4.0;  // más bandas con más ruido
    float band     = floor(uv.y * bandFreq) / bandFreq;
    float bandSeed = hash(band + floor(t * 15.0) * 0.07);

    // Solo algunas bandas se distorsionan
    vec2 distorted_uv = uv;
    if (bandSeed > 0.55) {
        float strength = (bandSeed - 0.55) * (0.18 + mr * 0.14 + nl * 0.06);
        distorted_uv.x += (hash(band + t) - 0.5) * strength;
    }
    distorted_uv = clamp(distorted_uv, 0.0, 1.0);

    // ── Aberración cromática RGB split ────────────────────────────────────────
    float split = 0.008 + mr * 0.012 + nl * 0.004;
    float r = texture(sTD2DInputs[0], clamp(distorted_uv + vec2( split, 0.0), 0.0, 1.0)).r;
    float g = texture(sTD2DInputs[0], distorted_uv).g;
    float b = texture(sTD2DInputs[0], clamp(distorted_uv - vec2( split, 0.0), 0.0, 1.0)).b;
    float a = texture(sTD2DInputs[0], distorted_uv).a;

    vec3 col = vec3(r, g, b);

    // ── Scanlines digitales ────────────────────────────────────────────────────
    float scanline = sin(uv.y * 600.0) * 0.5 + 0.5;
    col *= mix(1.0, scanline, 0.12 * mr);

    // ── Flash blanco ──────────────────────────────────────────────────────────
    col += vec3(flash);

    col = clamp(col, 0.0, 1.0);
    fragColor = vec4(col, clamp(a + flash, 0.0, 1.0));
}
