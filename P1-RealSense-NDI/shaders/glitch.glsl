// ─────────────────────────────────────────────────────────────────────────────
// glitch.glsl — Shader 2: Glitch / Distorsión
// Aún Sorprendo · JIFREX · Fase 3
//
// Entrada  [0]: salida de halo_glow.glsl
// Entrada  [1]: máscara binaria original (NDI desde MSI)
// Uniforms : uTrigger (float 0/1), uMotionRatio (float), uTime (float)
// Técnica  : desplazamiento UV con sin/cos · RGB split · scanlines
//            Solo se activa cuando uTrigger = 1 → más raro = más impactante
//
// En TouchDesigner: GLSL TOP después del halo · Trigger desde OSC CHOP
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[2];
uniform vec4      uTDOutputInfo;
uniform float     uTrigger;       // 0 o 1  — OSC /jifrex/trigger
uniform float     uMotionRatio;   // 0.0–1.0 — OSC /jifrex/motion_ratio
uniform float     uTime;

in  vec4 vUV;
out vec4 fragColor;

// ── Hash para ruido pseudo-aleatorio ─────────────────────────────────────────
float hash(float n) { return fract(sin(n) * 43758.5453); }
float hash2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

// ── Noise 1D (para scanlines de glitch) ──────────────────────────────────────
float noise1D(float x) {
    float i = floor(x);
    float f = fract(x);
    return mix(hash(i), hash(i + 1.0), smoothstep(0.0, 1.0, f));
}

void main() {
    vec2 uv   = vUV.st;
    float t   = uTime;
    float trig = clamp(uTrigger, 0.0, 1.0);
    float mr  = clamp(uMotionRatio, 0.0, 1.0);

    // ── Sin trigger: pass-through limpio ─────────────────────────────────────
    if (trig < 0.5) {
        fragColor = texture(sTD2DInputs[0], uv);
        return;
    }

    // ── Intensidad del glitch proporcional al motion_ratio ───────────────────
    float intensity = mr * 0.02;       // uMotionRatio * 0.02 (del diseño original)

    // ── Distorsión UV horizontal (bandas de glitch) ───────────────────────────
    float band      = floor(uv.y * 24.0);
    float bandNoise = hash2(vec2(band, floor(t * 12.0)));
    float shift     = (bandNoise - 0.5) * intensity * 2.0;

    // Glitch solo en bandas aleatorias activas
    float bandActive = step(0.65, hash2(vec2(band, floor(t * 8.0))));
    vec2  uvShifted  = vec2(uv.x + shift * bandActive, uv.y);

    // ── RGB split (aberración cromática) ─────────────────────────────────────
    float splitAmt = intensity * 1.5 * bandActive;
    float r = texture(sTD2DInputs[0], uvShifted + vec2( splitAmt, 0.0)).r;
    float g = texture(sTD2DInputs[0], uvShifted                        ).g;
    float b = texture(sTD2DInputs[0], uvShifted - vec2( splitAmt, 0.0)).b;
    float a = texture(sTD2DInputs[0], uvShifted                        ).a;

    vec3 col = vec3(r, g, b);

    // ── Scanlines horizontales ────────────────────────────────────────────────
    float scanline = 0.85 + 0.15 * sin(uv.y * uTDOutputInfo.x * 0.5);
    col *= scanline;

    // ── Flash blanco en el frame exacto del trigger ───────────────────────────
    float flashAge = fract(t * 0.5);               // tiempo desde último trigger
    float flash    = exp(-flashAge * 12.0) * 0.35; // decae rápido
    col += flash * vec3(1.0, 1.0, 1.0);

    // ── Noise de pixel (textura digital) ─────────────────────────────────────
    float pixNoise = hash2(uv + vec2(floor(t * 20.0))) * 0.08 * mr;
    col           += pixNoise;

    // ── Máscara original para mantener silueta ───────────────────────────────
    float mask = texture(sTD2DInputs[1], uv).r;
    col       *= (mask + 0.15);   // solo afuera de la silueta hay poco glitch

    fragColor = vec4(clamp(col, 0.0, 1.0), clamp(a + flash, 0.0, 1.0));
}
