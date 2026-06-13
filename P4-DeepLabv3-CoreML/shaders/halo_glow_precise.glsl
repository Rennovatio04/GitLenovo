// ─────────────────────────────────────────────────────────────────────────────
// halo_glow_precise.glsl — Halo/Glow con bordes subpixel-accurate
// Aún Sorprendo · JIFREX P4 · DeepLabv3 + CoreML
//
// Versión mejorada de P1/halo_glow.glsl.
// La diferencia no está en el algoritmo — está en la calidad del input:
//   MediaPipe → bordes ruidosos → halos irregulares con artefactos de oscilación
//   DeepLabv3 → bordes subpixel-accurate → halo perfectamente uniforme y suave
//
// Mejoras específicas de esta versión:
//   1. Edge multiplier aumentado de 6.0 a 9.0 (el border limpio lo permite)
//   2. uCoverageRatio: nuevo uniform Antimodular — el halo escala con la
//      "ocupación" del visitante en el espacio, no solo con su movimiento
//   3. Paleta expandida: coverage_ratio controla la temperatura del halo
//
// Inputs:
//   [0] = máscara DeepLabv3 (Syphon "JIFREX-P4-DEEPLAB")
//
// Uniforms (par.value0…par.value3 en TouchDesigner):
//   value0 = uFlowMean       (OSC /jifrex/p4/flow_mean)
//   value1 = uCoverageRatio  (OSC /jifrex/p4/coverage_ratio)  ← nuevo P4
//   value2 = uPresence       (OSC /jifrex/p4/presence)
//   value3 = uTime           (absTime.seconds)
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[1];
uniform vec4      uTDOutputInfo;

uniform float uFlowMean;       // 0.0–3.0
uniform float uCoverageRatio;  // 0.0–1.0 — fracción del frame cubierta (Antimodular)
uniform float uPresence;       // 0 o 1
uniform float uTime;

in  vec4 vUV;
out vec4 fragColor;

void main() {
    vec2  uv  = vUV.st;
    float fm  = clamp(uFlowMean, 0.0, 3.0);
    float cov = clamp(uCoverageRatio, 0.0, 1.0);
    float t   = uTime;

    float mask = texture(sTD2DInputs[0], uv).r;

    // ── Detección de borde subpixel-accurate ──────────────────────────────────
    // Con DeepLabv3, dFdx/dFdy captura el borde real del cuerpo sin ruido de modelo.
    // El multiplicador 9.0 (vs 6.0 en P1) es viable porque el borde es limpio.
    float dx   = dFdx(mask);
    float dy   = dFdy(mask);
    float edge = clamp(sqrt(dx*dx + dy*dy) * 9.0, 0.0, 1.0);

    // ── Halo radial: 16 muestras en distancia progresiva ─────────────────────
    vec2  px       = uTDOutputInfo.zw;
    float haloSum  = 0.0;
    float radius   = 0.04 + cov * 0.02;   // halo crece con la cobertura

    for (int i = 0; i < 16; i++) {
        float angle = float(i) * 6.28318 / 16.0;
        vec2  offset = vec2(cos(angle), sin(angle)) * radius * float(i + 1) / 8.0;
        haloSum += texture(sTD2DInputs[0], clamp(uv + offset * px * 80.0, 0.0, 1.0)).r;
    }
    float haloDist = 1.0 - clamp(haloSum / 16.0, 0.0, 1.0);

    // ── Intensidad del halo — proporcional a flow + cobertura (Antimodular) ───
    float haloIntensity = haloDist * edge
        * (1.0 + fm * 2.5 + cov * 1.5)
        * uPresence;

    // ── Paleta: temperatura controlada por coverage_ratio ─────────────────────
    // coverage bajo (visitante pequeño): azul frío (Bleus de Barcelona)
    // coverage alto (visitante cerca): plata → blanco (Lozano-Hemmer)
    vec3 halo_cold = vec3(0.25, 0.55, 1.00);   // azul
    vec3 halo_warm = vec3(0.85, 0.92, 1.00);   // plata-blanco
    vec3 haloColor = mix(halo_cold, halo_warm, cov);

    // ── Relleno de silueta: muy sutil, solo indica la presencia ───────────────
    vec3 fillColor = vec3(0.05, 0.08, 0.20);
    vec3 col       = mask * fillColor + haloColor * haloIntensity;

    // ── Pulso suave en reposo (presence=1 pero sin movimiento) ────────────────
    float restPulse = (1.0 - clamp(fm * 2.0, 0.0, 1.0))
                    * uPresence
                    * (0.05 + 0.03 * sin(t * 1.8));
    col += haloColor * restPulse;

    col = clamp(col, 0.0, 1.0);
    float alpha = clamp(mask + haloIntensity, 0.0, 1.0);
    fragColor   = vec4(col, alpha);
}
