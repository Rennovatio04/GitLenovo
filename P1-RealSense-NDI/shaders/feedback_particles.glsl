// ─────────────────────────────────────────────────────────────────────────────
// feedback_particles.glsl — Shader 3: Partículas / Estela
// Aún Sorprendo · JIFREX · Fase 3
//
// Este shader se conecta dentro de un loop Feedback TOP en TouchDesigner:
//
//   [glitch TOP] ──┐
//                  ├─► [GLSL TOP: feedback_particles] ──► [Feedback TOP] ─┐
//                  └──────────────────────────────────────────────────────┘
//
// Entrada  [0]: frame actual (salida de glitch.glsl)
// Entrada  [1]: frame anterior (Feedback TOP con opacidad < 1)
// Entrada  [2]: máscara binaria (NDI desde MSI)
// Uniforms : uFlowMean, uMotionRatio, uTime
// Técnica  : partículas emergen del borde de la máscara
//            feedback con decay → estela persistente
//            densidad de partículas proporcional a uMotionRatio
//
// En TouchDesigner: opacidad del Feedback TOP = 0.92 (ajustar en sala)
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[3];
uniform vec4      uTDOutputInfo;
uniform float     uFlowMean;       // OSC /jifrex/flow_mean
uniform float     uMotionRatio;    // OSC /jifrex/motion_ratio
uniform float     uPresence;       // OSC /jifrex/presence  (0 o 1)
uniform float     uTime;

in  vec4 vUV;
out vec4 fragColor;

// ── Utilidades ────────────────────────────────────────────────────────────────
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

float hash3(vec3 p) {
    return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453);
}

// ── Noise 2D suave ────────────────────────────────────────────────────────────
float noise(vec2 p) {
    vec2  i = floor(p);
    vec2  f = fract(p);
    vec2  u = f * f * (3.0 - 2.0 * f);
    float a = hash(i + vec2(0.0, 0.0));
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

// ── Detección de borde de la máscara ─────────────────────────────────────────
float maskEdge(vec2 uv, vec2 px) {
    float c  = texture(sTD2DInputs[2], uv).r;
    float dx = dFdx(c);
    float dy = dFdy(c);
    return clamp(sqrt(dx*dx + dy*dy) * 6.0, 0.0, 1.0);
}

// ── Partícula: devuelve luminosidad en uv dada la posición de la partícula ───
float particle(vec2 uv, vec2 pPos, float size) {
    float d = length(uv - pPos);
    return smoothstep(size, 0.0, d);
}

void main() {
    vec2  uv   = vUV.st;
    vec2  px   = uTDOutputInfo.zw;
    float t    = uTime;
    float fm   = clamp(uFlowMean, 0.0, 3.0);
    float mr   = clamp(uMotionRatio, 0.0, 1.0);

    // ── 1. Frame anterior con decay (estela) ──────────────────────────────────
    vec4 prev = texture(sTD2DInputs[1], uv);
    // Decay más rápido cuando no hay presencia (fade a negro en quietud > 3 s)
    float decay = (uPresence > 0.5) ? 0.96 : mix(0.96, 0.75, (1.0 - uPresence));
    prev.rgb *= decay;

    // ── 2. Frame actual (glitch) ──────────────────────────────────────────────
    vec4 current = texture(sTD2DInputs[0], uv);

    // ── 3. Partículas emergentes del borde ────────────────────────────────────
    float edge    = maskEdge(uv, px);
    float partCol = 0.0;

    // Número de partículas proporcional a motion_ratio
    int numParticles = int(12.0 + mr * 24.0);   // 12 – 36 partículas

    // La emisión se ancla al fragmento actual si está en el borde,
    // luego cada slot de partícula evoluciona desde ese punto de origen.
    float uvEdge = maskEdge(uv, px);

    for (int i = 0; i < 36; i++) {
        if (i >= numParticles) break;

        float fi   = float(i);
        float seed = fi * 0.137 + floor(t * 4.0) * 0.031;

        // Ángulo y velocidad de este slot
        float angle = hash3(vec3(fi, seed, 3.0)) * 6.28318;
        float speed = (0.018 + mr * 0.035) * (0.5 + hash3(vec3(fi, seed, 2.0)) * 0.5);

        // Vida: ciclo continuo por slot (0→1)
        float life = fract(t * speed * 5.0 + hash(vec2(fi, seed)));

        // Posición: nace en el fragmento actual y viaja hacia afuera
        vec2 velocity  = vec2(cos(angle), sin(angle)) * speed;
        velocity.y    -= 0.006 * life;   // gravedad negativa leve
        float nx = noise(uv * 10.0 + t * 0.25) * 0.018;
        float ny = noise(uv * 10.0 + t * 0.25 + 5.5) * 0.018;
        vec2 pos = uv + (velocity + vec2(nx, ny)) * life;

        float size   = mix(0.009, 0.002, life);
        float weight = uvEdge * (1.0 - life);   // solo emite en bordes reales
        partCol += particle(uv, pos, size) * weight;
    }

    partCol = clamp(partCol, 0.0, 1.0);

    // Color de partículas: azul-blanco proporcional al flow
    vec3 partColor = mix(
        vec3(0.3, 0.6, 1.0),    // azul suave — movimiento lento
        vec3(0.9, 0.95, 1.0),   // blanco frío — movimiento intenso
        fm * 0.4
    );

    // ── 4. Composite final ────────────────────────────────────────────────────
    vec3 col = prev.rgb;
    col      = max(col, current.rgb);                    // Screen blend con actual
    col     += partColor * partCol * (1.0 + fm * 0.5);  // partículas encima
    col      = clamp(col, 0.0, 1.0);

    float alpha = clamp(prev.a * decay + current.a + partCol * 0.8, 0.0, 1.0);

    fragColor = vec4(col, alpha);
}
