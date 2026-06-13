// ─────────────────────────────────────────────────────────────────────────────
// global_glitch.glsl — Trigger 4: Salto / movimiento brusco
// Aún Sorprendo · JIFREX · P2 Skeleton Semántico
//
// Respuesta visual: glitch máximo + partículas máximas. Reacción global de toda
// la proyección a un movimiento brusco del cuerpo (salto, gesto explosivo).
// Lógica de disparo (Python): motion_ratio > 0.7.
//
// Entrada  [0]: salida acumulada de la cadena (esqueleto + zonas)
// Entrada  [1]: frame anterior (Feedback TOP) para estela de partículas
// Uniforms : uGlitch (0/1), uMotionRatio (0..1), uFlowMean (0..3), uTime
//
// En TouchDesigner: GLSL TOP dentro de un Feedback TOP · uniforms desde
//   td_osc_to_uniforms.py
//   uGlitch      ← /cuerpo/global/glitch
//   uMotionRatio ← /cuerpo/metrica/motion_ratio
//   uFlowMean    ← /cuerpo/metrica/flow_mean
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[2];
uniform vec4      uTDOutputInfo;
uniform float     uGlitch;        // 0 o 1
uniform float     uMotionRatio;   // 0..1
uniform float     uFlowMean;      // 0..3
uniform float     uTime;

in  vec4 vUV;
out vec4 fragColor;

float hash(float n)  { return fract(sin(n) * 43758.5453); }
float hash2(vec2 p)  { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

float particle(vec2 uv, vec2 p, float size) {
    return smoothstep(size, 0.0, length(uv - p));
}

void main() {
    vec2  uv  = vUV.st;
    float t   = uTime;
    float g   = clamp(uGlitch, 0.0, 1.0);
    float mr  = clamp(uMotionRatio, 0.0, 1.0);
    float fm  = clamp(uFlowMean, 0.0, 3.0);

    vec4 cur  = texture(sTD2DInputs[0], uv);
    vec4 prev = texture(sTD2DInputs[1], uv);

    // ── Sin disparo: pass-through con estela mínima en decaimiento ────────────
    if (g < 0.5) {
        vec3 fade = max(cur.rgb, prev.rgb * 0.85);
        fragColor = vec4(fade, max(cur.a, prev.a * 0.85));
        return;
    }

    // ── Glitch máximo (intensidad escala con motion_ratio) ────────────────────
    float intensity = (0.5 + mr) * 0.04;

    // Bandas horizontales desplazadas + RGB split agresivo.
    float band      = floor(uv.y * 32.0);
    float bandNoise = hash2(vec2(band, floor(t * 18.0)));
    float active    = step(0.45, hash2(vec2(band, floor(t * 10.0))));
    float shift     = (bandNoise - 0.5) * intensity * 4.0 * active;
    vec2  uvg       = vec2(uv.x + shift, uv.y);

    float split = intensity * 2.5 * active;
    float r = texture(sTD2DInputs[0], uvg + vec2( split, 0.0)).r;
    float gg= texture(sTD2DInputs[0], uvg).g;
    float b = texture(sTD2DInputs[0], uvg - vec2( split, 0.0)).b;
    vec3  col = vec3(r, gg, b);

    // Bloques digitales aleatorios (corte cubista del frame).
    vec2  blk   = floor(uv * vec2(24.0, 14.0));
    float glitchBlk = step(0.85, hash2(blk + floor(t * 14.0)));
    col = mix(col, col.gbr, glitchBlk * mr);

    // ── Partículas máximas emergiendo de todo el frame ────────────────────────
    float partCol = 0.0;
    int   nP = int(20.0 + mr * 40.0);          // hasta 60 partículas
    for (int i = 0; i < 60; i++) {
        if (i >= nP) break;
        float fi   = float(i);
        float seed = fi * 0.157 + floor(t * 6.0) * 0.041;
        vec2  origin = vec2(hash2(vec2(fi, 1.0)), hash2(vec2(fi, 2.0)));
        float life   = fract(t * (0.6 + mr) + hash(fi));
        float ang    = hash2(vec2(fi, seed)) * 6.28318;
        vec2  pos    = origin + vec2(cos(ang), sin(ang)) * life * (0.1 + mr * 0.2);
        float size   = mix(0.010, 0.002, life);
        partCol     += particle(uv, pos, size) * (1.0 - life);
    }
    partCol = clamp(partCol, 0.0, 1.0);
    vec3 partColor = mix(vec3(0.6, 0.8, 1.0), vec3(1.0), fm * 0.3);

    // Flash blanco en el instante del disparo.
    float flash = exp(-fract(t * 0.5) * 14.0) * 0.4;

    col += partColor * partCol * (1.2 + fm * 0.6);
    col += flash;

    // Estela: combina con el frame previo (Feedback) para que las partículas
    // dejen rastro al saltar.
    col = max(col, prev.rgb * 0.9);

    float alpha = clamp(cur.a + partCol * 0.8 + flash, 0.0, 1.0);
    fragColor = vec4(clamp(col, 0.0, 1.0), alpha);
}
