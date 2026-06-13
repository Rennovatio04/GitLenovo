// ─────────────────────────────────────────────────────────────────────────────
// zona_hands.glsl — Trigger 1: Mano extendida
// Aún Sorprendo · JIFREX · P2 Skeleton Semántico
//
// Respuesta visual: planos geométricos fragmentados cubistas que emergen de la
// posición de la mano. Paleta fría azul-blanco.
// Lógica de disparo (Python): landmark[16].y < landmark[12].y - umbral.
//
// Entrada  [0]: overlay esqueleto+máscara (Spout/Syphon desde skeleton_runtime)
// Uniforms : uHandTrigger (0/1), uWristHeight (0..1), uArmOpenR (deg), uTime
//
// En TouchDesigner: GLSL TOP · uniforms desde td_osc_to_uniforms.py
//   uHandTrigger ← /cuerpo/mano_derecha[0]
//   uWristHeight ← /cuerpo/mano_derecha[1]
//   uArmOpenR    ← /cuerpo/metrica/arm_open_right
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[1];
uniform vec4      uTDOutputInfo;
uniform float     uHandTrigger;   // 0 o 1  — mano extendida
uniform float     uWristHeight;   // 0..1   — altura de la muñeca (0 abajo, 1 arriba)
uniform float     uArmOpenR;      // grados — apertura del brazo derecho
uniform float     uTime;

in  vec4 vUV;
out vec4 fragColor;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

// ── Paleta fría azul-blanco (Les Bleus, referencia cubista temprana) ──────────
vec3 coldPalette(float t) {
    vec3 deep  = vec3(0.04, 0.12, 0.42);   // azul profundo
    vec3 blue  = vec3(0.15, 0.45, 0.92);   // azul medio
    vec3 white = vec3(0.92, 0.96, 1.00);   // blanco frío
    if (t < 0.5) return mix(deep, blue,  t * 2.0);
    else         return mix(blue, white, (t - 0.5) * 2.0);
}

// ── Plano cubista: celdas de Voronoi facetadas que fracturan el espacio ───────
// Devuelve (intensidad de faceta, índice de celda) para colorear cada plano.
vec2 cubistPlanes(vec2 uv, float scale, float t) {
    vec2 g  = uv * scale;
    vec2 gi = floor(g);
    vec2 gf = fract(g);

    float minDist = 8.0;
    vec2  cellId  = vec2(0.0);
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            vec2 n  = vec2(float(x), float(y));
            // Punto de la celda animado lentamente → planos que respiran.
            vec2 p  = n + 0.5 + 0.35 * sin(t * 0.6 + 6.2831 * hash(gi + n));
            float d = length(n + p - gf);
            if (d < minDist) {
                minDist = d;
                cellId  = gi + n;
            }
        }
    }
    // Bordes nítidos entre facetas (líneas de fractura cubista).
    float facet = smoothstep(0.02, 0.08, minDist);
    return vec2(facet, hash(cellId));
}

void main() {
    vec2  uv  = vUV.st;
    float trig = clamp(uHandTrigger, 0.0, 1.0);

    vec4  base = texture(sTD2DInputs[0], uv);

    // Sin disparo: pass-through (el sistema espera el gesto).
    if (trig < 0.5) {
        fragColor = base;
        return;
    }

    // La densidad de planos crece con la altura de la muñeca y la apertura.
    float openN = clamp(uArmOpenR / 90.0, 0.0, 1.0);
    float scale = mix(6.0, 16.0, clamp(uWristHeight, 0.0, 1.0));

    vec2  planes = cubistPlanes(uv, scale, uTime);
    float facet  = planes.x;        // 0 en líneas de fractura, 1 dentro de faceta
    float cellH  = planes.y;        // identificador de celda para variar tono

    // Cada faceta toma un tono frío distinto; las líneas de fractura van a blanco.
    float tone   = fract(cellH + uWristHeight * 0.3 + uTime * 0.02);
    vec3  plane  = coldPalette(tone);

    // Fractura: líneas brillantes entre planos (aristas cubistas).
    float fracture = (1.0 - facet);
    vec3  col = mix(plane * 0.7, vec3(1.0), fracture);

    // Los planos emergen desde la posición vertical de la mano: gradiente que
    // sube con uWristHeight (efecto "brotan desde la palma").
    float emerge = smoothstep(uWristHeight + 0.15, uWristHeight - 0.25, uv.y);
    col *= mix(0.25, 1.0, emerge);

    // Mezcla con el esqueleto base para no perder la silueta.
    col = max(col * (0.6 + 0.4 * openN), base.rgb);

    float alpha = clamp(base.a + facet * 0.6 + fracture, 0.0, 1.0);
    fragColor = vec4(clamp(col, 0.0, 1.0), alpha);
}
