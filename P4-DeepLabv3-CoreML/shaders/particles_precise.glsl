// ─────────────────────────────────────────────────────────────────────────────
// particles_precise.glsl — Partículas emergentes del contorno exacto
// Aún Sorprendo · JIFREX P4 · DeepLabv3 + CoreML
//
// Versión mejorada de P1/feedback_particles.glsl.
//
// El cambio fundamental: con MediaPipe las partículas emergían de una
// APROXIMACIÓN del contorno. Con DeepLabv3 emergen del contorno EXACTO,
// incluyendo dedos individuales, contorno del cabello, y ropa.
//
// Por qué importa artísticamente: Lozano-Hemmer (Antimodular) trabaja con la
// precisión de la silueta como declaración sobre la presencia del cuerpo.
// "La silueta perfecta es la huella perfecta."
//
// Mejoras técnicas:
//   1. maskEdge multiplier: 6.0 → 11.0 (bordes limpios permiten mayor amplitud)
//   2. uCoverageRatio: más partículas cuando el visitante llena más el frame
//   3. Partículas "dedos": partículas más pequeñas y densas en bordes finos
//      (las áreas de alto-dFdx con baja máscara = extremidades)
//
// Red TouchDesigner:
//   [halo TOP] ──┐
//                ├──► [GLSL: particles_precise] ──► [Feedback TOP] ─┐
//   [Feedback] ──┘                                                    │
//   [máscara]  ──────────────────────────────────────────────────────┘
//
// Inputs:
//   [0] = glitch_precise TOP (frame actual)
//   [1] = Feedback TOP (frame anterior con decay)
//   [2] = máscara DeepLabv3 (Syphon)
//
// Uniforms (par.value0…par.value5):
//   value0 = uFlowMean       (OSC /jifrex/p4/flow_mean)
//   value1 = uMotionRatio    (OSC /jifrex/p4/motion_ratio)
//   value2 = uPresence       (OSC /jifrex/p4/presence)
//   value3 = uCoverageRatio  (OSC /jifrex/p4/coverage_ratio)  ← nuevo P4
//   value4 = uNoiseLevel     (OSC /jifrex/p4/noise_level)     ← nuevo P4
//   value5 = uTime           (absTime.seconds)
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[3];
uniform vec4      uTDOutputInfo;

uniform float uFlowMean;       // 0.0–3.0
uniform float uMotionRatio;    // 0.0–1.0
uniform float uPresence;       // 0 o 1
uniform float uCoverageRatio;  // 0.0–1.0 (Antimodular: ocupación del espacio)
uniform float uNoiseLevel;     // 0.0–N   (Antimodular: ruido de blobs)
uniform float uTime;

in  vec4 vUV;
out vec4 fragColor;

// ── Utilidades ────────────────────────────────────────────────────────────────
float hash(vec2 p)  { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float hash3(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
float noise(vec2 p) {
    vec2 i = floor(p); vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
               mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

// maskEdge con multiplicador 11.0 — bordes DeepLabv3 lo permiten sin ruido
float maskEdge(vec2 uv) {
    float c  = texture(sTD2DInputs[2], uv).r;
    float dx = dFdx(c);
    float dy = dFdy(c);
    return clamp(sqrt(dx*dx + dy*dy) * 11.0, 0.0, 1.0);
}

// Borde "fino" — extremidades y dedos: alta derivada, máscara baja
float thinEdge(vec2 uv) {
    float c    = texture(sTD2DInputs[2], uv).r;
    float edge = maskEdge(uv);
    // Extremidades tienen c bajo pero dFdx/dFdy alto
    return edge * clamp(1.0 - c * 2.0, 0.0, 1.0);
}

float particle(vec2 uv, vec2 pos, float size) {
    return smoothstep(size, 0.0, length(uv - pos));
}

void main() {
    vec2  uv = vUV.st;
    float t  = uTime;
    float fm = clamp(uFlowMean, 0.0, 3.0);
    float mr = clamp(uMotionRatio, 0.0, 1.0);
    float cov = clamp(uCoverageRatio, 0.0, 1.0);

    // ── 1. Estela del Feedback TOP ────────────────────────────────────────────
    vec4  prev  = texture(sTD2DInputs[1], uv);
    // Decay ajustado por cobertura: visitante grande = estela más larga
    float decay = (uPresence > 0.5)
        ? mix(0.94, 0.97, cov)   // 0.94 (poca cobertura) → 0.97 (mucha cobertura)
        : 0.72;
    prev.rgb *= decay;

    // ── 2. Frame actual ────────────────────────────────────────────────────────
    vec4 current = texture(sTD2DInputs[0], uv);

    // ── 3. Bordes (normal y fino para extremidades) ────────────────────────────
    float uvEdge = maskEdge(uv);
    float uvThin = thinEdge(uv);    // dedos, cabello, ropa fina

    // ── 4. Partículas principales — contorno exacto ────────────────────────────
    // Número proporcional a motion + coverage (Antimodular: el visitante que llena
    // más el espacio genera más partículas — más presencia = más huella)
    int numParticles = int(14.0 + mr * 20.0 + cov * 8.0);   // 14–42 partículas
    numParticles = min(numParticles, 42);
    float partCol = 0.0;

    for (int i = 0; i < 42; i++) {
        if (i >= numParticles) break;
        float fi   = float(i);
        float seed = fi * 0.137 + floor(t * 4.0) * 0.031;
        float angle = hash3(vec3(fi, seed, 3.0)) * 6.28318;
        float speed = (0.016 + mr * 0.032 + cov * 0.012)
                    * (0.5 + hash3(vec3(fi, seed, 2.0)) * 0.5);
        float life  = fract(t * speed * 5.0 + hash(vec2(fi, seed)));
        vec2 velocity  = vec2(cos(angle), sin(angle)) * speed;
        velocity.y    -= 0.005 * life;   // leve gravedad invertida (ascendente)
        float nx = noise(uv * 11.0 + t * 0.22) * 0.015;
        float ny = noise(uv * 11.0 + t * 0.22 + 5.5) * 0.015;
        vec2 pos   = uv + (velocity + vec2(nx, ny)) * life;
        float size = mix(0.010, 0.002, life);
        float w    = uvEdge * (1.0 - life);
        partCol   += particle(uv, pos, size) * w;
    }

    // ── 5. Partículas finas — dedos y cabello (subpixel detail de DeepLabv3) ───
    // Solo en P4: dedos y cabello generan partículas más pequeñas y densas
    int numThin = int(8.0 + mr * 10.0);
    float thinCol = 0.0;

    for (int i = 0; i < 18; i++) {
        if (i >= numThin) break;
        float fi   = float(i) + 100.0;
        float seed = fi * 0.211 + floor(t * 6.0) * 0.019;
        float angle = hash3(vec3(fi, seed, 5.0)) * 6.28318;
        float speed = 0.008 + mr * 0.012;
        float life  = fract(t * speed * 7.0 + hash(vec2(fi, seed)));
        vec2 velocity = vec2(cos(angle), sin(angle)) * speed;
        vec2 pos      = uv + velocity * life;
        float size    = mix(0.005, 0.001, life);
        float w       = uvThin * (1.0 - life);
        thinCol      += particle(uv, pos, size) * w;
    }

    partCol  = clamp(partCol, 0.0, 1.0);
    thinCol  = clamp(thinCol, 0.0, 1.0);

    // ── 6. Color de partículas ────────────────────────────────────────────────
    // Frío (azul) → caliente (blanco) según intensidad de movimiento
    vec3 partColor = mix(
        vec3(0.28, 0.58, 1.00),    // azul suave — movimiento lento
        vec3(0.92, 0.96, 1.00),    // blanco frío — movimiento intenso
        fm * 0.38
    );
    // Partículas de dedos/cabello: ligeramente más frías (más precisas, más etéreas)
    vec3 thinColor = vec3(0.45, 0.70, 1.00);

    // ── 7. Composite final ────────────────────────────────────────────────────
    vec3 col = prev.rgb;
    col      = max(col, current.rgb);
    col     += partColor * partCol  * (1.0 + fm * 0.45 + cov * 0.3);
    col     += thinColor * thinCol  * (0.6 + fm * 0.25);    // más sutiles
    col      = clamp(col, 0.0, 1.0);

    float alpha = clamp(
        prev.a * decay + current.a + (partCol + thinCol * 0.5) * 0.8,
        0.0, 1.0
    );
    fragColor = vec4(col, alpha);
}
