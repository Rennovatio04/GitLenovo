// ─────────────────────────────────────────────────────────────────────────────
// particulas_perspectiva.glsl — Partículas diferenciadas por perspectiva
// Aún Sorprendo · JIFREX
//
// Tres comportamientos de partícula según la perspectiva activa:
//   Frontal  (uPerspective=0): expansión radial — el cuerpo se expande hacia afuera
//   Lateral  (uPerspective=1): traslación horizontal — movimiento en eje Z cubista
//   Cenital  (uPerspective=2): espiral — huella circular desde arriba
//
// Red en TouchDesigner: este shader se conecta en un Feedback TOP loop
//   [composite_multicamara] ──┐
//                             ├──► [GLSL: particulas_perspectiva] ──► [Feedback TOP]
//   [Feedback TOP] ───────────┘                                              │
//   [máscara compuesta] ──────────────────────────────────────────────────────┘
//
// Inputs:
//   [0] = composite_multicamara (frame actual con 3 siluetas coloreadas)
//   [1] = Feedback TOP (frame anterior — acumula la estela)
//   [2] = máscara compuesta = max(mask_a, mask_b, mask_c) de las 3 cámaras
//
// Uniforms (par.value0 … par.value9 en TouchDesigner):
//   value0  = uPerspective   (fijo: 0, 1, o 2 según qué perspectiva está activa)
//   value1  = uFlowA         (OSC /multicam/a/flow_mean)
//   value2  = uFlowB         (OSC /multicam/b/flow_mean)
//   value3  = uFlowC         (OSC /multicam/c/flow_mean)
//   value4  = uMotionA       (OSC /multicam/a/motion)
//   value5  = uMotionB       (OSC /multicam/b/motion)
//   value6  = uMotionC       (OSC /multicam/c/motion)
//   value7  = uTripleRatio   (OSC /multicam/triple_ratio)
//   value8  = uAnyPresence   (OSC /multicam/any_presence)
//   value9  = uTime          (absTime.seconds)
//
// Nota: uPerspective puede ser un valor fijo (no vía OSC) si se quiere
// que cada instancia del shader maneje solo su perspectiva.
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[3];
uniform vec4      uTDOutputInfo;

uniform float uPerspective;   // 0=frontal, 1=lateral, 2=cenital (puede ser fijo)
uniform float uFlowA;
uniform float uFlowB;
uniform float uFlowC;
uniform float uMotionA;
uniform float uMotionB;
uniform float uMotionC;
uniform float uTripleRatio;
uniform float uAnyPresence;
uniform float uTime;

in  vec4 vUV;
out vec4 fragColor;

// ── Utilidades ────────────────────────────────────────────────────────────────
float hash(vec2 p)  { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float hash3(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
               mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

// Detecta el borde de la máscara compuesta usando derivadas parciales
float maskEdge(vec2 uv) {
    float c  = texture(sTD2DInputs[2], uv).r;
    float dx = dFdx(c);
    float dy = dFdy(c);
    return clamp(sqrt(dx*dx + dy*dy) * 9.0, 0.0, 1.0);
}

float particle(vec2 uv, vec2 pos, float size) {
    return smoothstep(size, 0.0, length(uv - pos));
}

void main() {
    vec2  uv = vUV.st;
    float t  = uTime;

    // ── Seleccionar flow/motion/color según perspectiva ────────────────────────
    float fm, mr;
    vec3 pColor;

    if (uPerspective < 0.5) {
        // Frontal — azul
        fm     = uFlowA;
        mr     = uMotionA;
        pColor = vec3(0.25, 0.55, 1.0);
    } else if (uPerspective < 1.5) {
        // Lateral — ocre
        fm     = uFlowB;
        mr     = uMotionB;
        pColor = vec3(1.0, 0.78, 0.28);
    } else {
        // Cenital — rosa
        fm     = uFlowC;
        mr     = uMotionC;
        pColor = vec3(1.0, 0.52, 0.72);
    }

    fm = clamp(fm, 0.0, 3.0);
    mr = clamp(mr, 0.0, 1.0);

    // ── 1. Estela del Feedback TOP con decay ──────────────────────────────────
    // Decay más largo en zonas de triple coincidencia (máxima certeza artística)
    vec4  prev  = texture(sTD2DInputs[1], uv);
    float decay = (uAnyPresence > 0.5)
        ? mix(0.94, 0.97, uTripleRatio)   // 0.94 normal → 0.97 en triple
        : 0.74;                             // fade rápido cuando no hay visitante
    prev.rgb *= decay;

    // ── 2. Frame composite actual ──────────────────────────────────────────────
    vec4 current = texture(sTD2DInputs[0], uv);

    // ── 3. Detección del borde de la máscara ──────────────────────────────────
    float uvEdge = maskEdge(uv);

    // ── 4. Partículas con comportamiento según perspectiva ─────────────────────
    int   numPart = int(10.0 + mr * 22.0);   // 10 – 32 partículas
    float partLum = 0.0;

    for (int i = 0; i < 32; i++) {
        if (i >= numPart) break;

        float fi   = float(i);
        float seed = fi * 0.139 + floor(t * 4.0) * 0.027;
        float life = fract(t * (0.018 + mr * 0.038) * 5.0 + hash(vec2(fi, seed)));
        float size = mix(0.012, 0.002, life);

        // Ruido de turbulencia (igual para todas las perspectivas)
        float nx = noise(uv * 9.0 + t * 0.22) * 0.011;
        float ny = noise(uv * 9.0 + t * 0.22 + 5.3) * 0.011;

        vec2 velocity;

        if (uPerspective < 0.5) {
            // ── Frontal: expansión RADIAL desde el punto actual ────────────────
            // El cuerpo "irradia" desde su silueta en todas las direcciones
            float angle = hash3(vec3(fi, seed, 1.0)) * 6.28318;
            float spd   = 0.018 + mr * 0.028;
            velocity    = vec2(cos(angle), sin(angle)) * spd;

        } else if (uPerspective < 1.5) {
            // ── Lateral: traslación HORIZONTAL ────────────────────────────────
            // Simula el movimiento que el eje Z captura: desplazamiento lateral
            float dir = (hash3(vec3(fi, seed, 2.0)) > 0.5) ? 1.0 : -1.0;
            float spd = (0.012 + mr * 0.022) * dir;
            float vy  = (hash3(vec3(fi, seed, 3.0)) - 0.5) * 0.006;
            velocity  = vec2(spd, vy);

        } else {
            // ── Cenital: ESPIRAL hacia afuera ──────────────────────────────────
            // Desde arriba el cuerpo deja una huella que se expande en espiral
            float base_angle = hash3(vec3(fi, seed, 4.0)) * 6.28318;
            float spin       = life * 6.28318 * 1.8;   // rotación acumulada
            float angle      = base_angle + spin;
            float r          = life * (0.015 + mr * 0.032);
            velocity         = vec2(cos(angle) * r, sin(angle) * r) * 0.9;
        }

        vec2  pos    = uv + (velocity + vec2(nx, ny)) * life;
        float weight = uvEdge * (1.0 - life);   // solo emite desde bordes reales
        partLum     += particle(uv, pos, size) * weight;
    }

    partLum = clamp(partLum, 0.0, 1.0);

    // ── 5. En triple coincidencia, las partículas se vuelven blancas ──────────
    // El punto donde los 3 ángulos convergen = máxima claridad = blanco Picasso
    float tripleBonus = uTripleRatio * 1.8;
    pColor = mix(pColor, vec3(1.0, 0.97, 0.93), clamp(tripleBonus * 0.45, 0.0, 1.0));

    // ── 6. Composite final ─────────────────────────────────────────────────────
    vec3 col = prev.rgb;
    col      = max(col, current.rgb);                              // Screen con actual
    col     += pColor * partLum * (1.0 + fm * 0.35 + tripleBonus); // partículas encima
    col      = clamp(col, 0.0, 1.0);

    float alpha = clamp(prev.a * decay + current.a + partLum * 0.8, 0.0, 1.0);
    fragColor   = vec4(col, alpha);
}
