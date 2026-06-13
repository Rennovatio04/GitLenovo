// ─────────────────────────────────────────────────────────────────────────────
// distorsion_uv.glsl — Distorsión UV por perspectiva
// Aún Sorprendo · JIFREX
//
// Se aplica ANTES del composite_multicamara.glsl — una instancia por cámara.
// Cada perspectiva tiene una transformación UV diferente que refleja
// la naturaleza geométrica de ese ángulo de visión.
//
// Crear 3 instancias en TouchDesigner:
//   glsl_distort_a  → uPerspective = 0  (frontal: deformación radial)
//   glsl_distort_b  → uPerspective = 1  (lateral: deformación horizontal / eje Z)
//   glsl_distort_c  → uPerspective = 2  (cenital: rotación / espiral)
//
// Inputs:
//   [0] = Syphon In de la cámara correspondiente (máscara binaria)
//
// Uniforms (par.value0/1/2 en TouchDesigner):
//   value0  = uPerspective  (0=frontal, 1=lateral, 2=cenital)
//   value1  = uFlowMean     (OSC /multicam/[a|b|c]/flow_mean)
//   value2  = uTime         (absTime.seconds)
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[1];
uniform vec4      uTDOutputInfo;

uniform float uPerspective;   // 0=frontal, 1=lateral, 2=cenital
uniform float uFlowMean;      // distorsión proporcional al movimiento
uniform float uTime;

in  vec4 vUV;
out vec4 fragColor;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i),           hash(i + vec2(1.0, 0.0)), u.x),
               mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

void main() {
    vec2  uv = vUV.st;
    float fm = clamp(uFlowMean, 0.0, 3.0);
    float t  = uTime;
    vec2  distorted_uv;

    if (uPerspective < 0.5) {
        // ── Frontal: deformación radial sutil ──────────────────────────────────
        // Como un espejo levemente deformado, que revela la textura del espacio
        vec2  center = vec2(0.5, 0.5);
        vec2  d      = uv - center;
        float r      = length(d);
        float warp   = fm * 0.007 * noise(uv * 7.0 + t * 0.25);
        distorted_uv = uv + d * warp * r;

    } else if (uPerspective < 1.5) {
        // ── Lateral: deformación horizontal (profundidad eje Z) ────────────────
        // La cámara lateral captura la dimensión que el espejo nunca muestra:
        // la profundidad del cuerpo en el espacio
        float shear  = fm * 0.013 * sin(uv.y * 3.14159 * 2.0 + t * 0.45);
        float stretch = 1.0 + fm * 0.006 * cos(uv.y * 5.0 + t * 0.3);
        distorted_uv = vec2(uv.x * stretch + shear, uv.y);

    } else {
        // ── Cenital: rotación leve alrededor del centro (huella en espiral) ────
        // La vista desde arriba nunca es estática: el cuerpo deja una huella
        // que gira y se expande en el espacio
        vec2  center = vec2(0.5, 0.5);
        vec2  d      = uv - center;
        float angle  = fm * 0.035 * sin(t * 0.6);
        float c      = cos(angle);
        float s      = sin(angle);
        distorted_uv = center + vec2(c * d.x - s * d.y, s * d.x + c * d.y);
    }

    distorted_uv = clamp(distorted_uv, 0.0, 1.0);
    fragColor    = texture(sTD2DInputs[0], distorted_uv);
}
