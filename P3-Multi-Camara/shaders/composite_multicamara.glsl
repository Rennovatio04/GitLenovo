// ─────────────────────────────────────────────────────────────────────────────
// composite_multicamara.glsl — GLSL TOP principal P3
// Aún Sorprendo · JIFREX · Screen blend de 3 siluetas coloreadas
//
// "Picasso no pintaba lo que veía. Pintaba lo que sabía que estaba ahí,
//  desde todos los ángulos posibles a la vez."
// Este shader implementa ese principio de forma literal.
//
// Red en TouchDesigner:
//   [Syphon In A] ──┐
//   [Syphon In B] ──┼──► [distorsion_uv A/B/C] ──► [GLSL: composite_multicamara]
//   [Syphon In C] ──┘                               └──► [particulas_perspectiva]
//                                                           └──► [Feedback TOP]
//
// Inputs:
//   [0] = máscara cámara A (frontal)  — Syphon "JIFREX-CAM-A-FRONTAL"
//   [1] = máscara cámara B (lateral)  — Syphon "JIFREX-CAM-B-LATERAL"
//   [2] = máscara cámara C (cenital)  — Syphon "JIFREX-CAM-C-CENITAL"
//
// Uniforms (par.value0 … par.value5 en TouchDesigner):
//   value0  = uFlowA        (OSC /multicam/a/flow_mean)
//   value1  = uFlowB        (OSC /multicam/b/flow_mean)
//   value2  = uFlowC        (OSC /multicam/c/flow_mean)
//   value3  = uTripleRatio  (OSC /multicam/triple_ratio)
//   value4  = uAnyPresence  (OSC /multicam/any_presence)
//   value5  = uTime         (absTime.seconds)
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[3];
uniform vec4      uTDOutputInfo;

uniform float uFlowA;        // flow_mean cámara frontal
uniform float uFlowB;        // flow_mean cámara lateral
uniform float uFlowC;        // flow_mean cámara cenital
uniform float uTripleRatio;  // fracción de triple coincidencia (0.0–1.0)
uniform float uAnyPresence;  // 1.0 si hay al menos una persona, 0.0 si no
uniform float uTime;

in  vec4 vUV;
out vec4 fragColor;

void main() {
    vec2 uv = vUV.st;

    // ── 1. Muestreo de máscaras (siluetas) ────────────────────────────────────
    float mask_a = texture(sTD2DInputs[0], uv).r;
    float mask_b = texture(sTD2DInputs[1], uv).r;
    float mask_c = texture(sTD2DInputs[2], uv).r;

    // ── 2. Colores por perspectiva ─────────────────────────────────────────────
    // Referencia directa al catálogo de obras de Picasso
    vec3 col_a = vec3(0.09, 0.35, 0.95);   // azul  — frontal  (Les Bleus de Barcelona)
    vec3 col_b = vec3(0.95, 0.66, 0.12);   // ocre  — lateral  (Bailarines sobre cuero)
    vec3 col_c = vec3(0.95, 0.38, 0.65);   // rosa  — cenital  (Geneviève sobre papel Japón)

    // Modulación de saturación por flow: más vívido con más movimiento
    float sat_a = clamp(uFlowA * 0.4, 0.0, 1.0);
    float sat_b = clamp(uFlowB * 0.4, 0.0, 1.0);
    float sat_c = clamp(uFlowC * 0.4, 0.0, 1.0);
    col_a = mix(col_a * 0.65, col_a, sat_a);
    col_b = mix(col_b * 0.65, col_b, sat_b);
    col_c = mix(col_c * 0.65, col_c, sat_c);

    // ── 3. Aplicar máscaras a los colores ─────────────────────────────────────
    col_a *= mask_a;
    col_b *= mask_b;
    col_c *= mask_c;

    // ── 4. Screen blend — el principio del cubismo hecho literal ───────────────
    //    Triple coincidencia (3 perspectivas solapadas) → blanco brillante
    //    Doble coincidencia → mezcla de 2 colores
    //    Simple → color puro de la perspectiva
    vec3 result = 1.0 - (1.0 - col_a) * (1.0 - col_b) * (1.0 - col_c);

    // ── 5. Refuerzo de brillo en zonas de triple coincidencia ─────────────────
    //    El punto donde los 3 puntos de vista coinciden tiene la mayor certeza
    //    artística: Picasso lo habría pintado con máxima intensidad
    float triple_local = mask_a * mask_b * mask_c;
    result += triple_local * vec3(0.25, 0.22, 0.20);

    // ── 6. Halos de apertura sobre el piso (estado de reposo) ─────────────────
    //    Antes de que entre el visitante, tres halos de color pulsantes
    //    señalan las posiciones de las 3 perspectivas
    if (uAnyPresence < 0.5) {
        float t      = uTime;
        float pulse  = 0.07 + 0.035 * sin(t * 1.4);
        float pulse2 = 0.07 + 0.035 * sin(t * 1.4 + 2.094);  // desfase 2π/3
        float pulse3 = 0.07 + 0.035 * sin(t * 1.4 + 4.189);  // desfase 4π/3

        // Posiciones en UV — ajustar en TouchDesigner según el espacio real de galería
        vec2 halo_a = vec2(0.28, 0.50);   // izquierda — frontal
        vec2 halo_b = vec2(0.50, 0.50);   // centro    — lateral
        vec2 halo_c = vec2(0.72, 0.50);   // derecha   — cenital

        float d_a = length(uv - halo_a);
        float d_b = length(uv - halo_b);
        float d_c = length(uv - halo_c);

        result += vec3(0.09, 0.35, 0.95) * smoothstep(0.11, 0.06, d_a) * pulse;
        result += vec3(0.95, 0.66, 0.12) * smoothstep(0.11, 0.06, d_b) * pulse2;
        result += vec3(0.95, 0.38, 0.65) * smoothstep(0.11, 0.06, d_c) * pulse3;
    }

    // ── 7. Alpha compuesto ─────────────────────────────────────────────────────
    float alpha = clamp(mask_a + mask_b + mask_c, 0.0, 1.0);

    result = clamp(result, 0.0, 1.0);
    fragColor = vec4(result, alpha);
}
