// ─────────────────────────────────────────────────────────────────────────────
// dual_body.glsl — Trigger 6: 2 personas simultáneas (EXCLUSIVO de P2)
// Aún Sorprendo · JIFREX · P2 Skeleton Semántico
//
// Respuesta visual: diálogo cubista entre dos cuerpos. Cuando hay dos centros
// de masa, el espacio entre ambos se fractura en planos compartidos — una
// composición dual que "conversa". Cada cuerpo tiñe su mitad y la zona de
// encuentro genera interferencia cubista.
// Lógica de disparo (Python): blob_count > 1 + dos centros de masa separados.
//
// Entrada  [0]: salida acumulada de la cadena (esqueleto + zonas + glitch)
// Uniforms : uBlobCount (1 o 2), uTime
//   (los centros se aproximan por el overlay; aquí se trabaja en espacio de
//    pantalla: mitad izquierda ↔ mitad derecha + banda central de diálogo)
//
// En TouchDesigner: GLSL TOP final antes del Level/Out · uniforms desde
//   td_osc_to_uniforms.py
//   uBlobCount ← /cuerpo/blob_count
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[1];
uniform vec4      uTDOutputInfo;
uniform float     uBlobCount;     // 1 o 2
uniform float     uTime;

in  vec4 vUV;
out vec4 fragColor;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

// ── Facetas cubistas (Voronoi) para la zona de diálogo entre cuerpos ──────────
float facets(vec2 uv, float scale, float t) {
    vec2 g  = uv * scale;
    vec2 gi = floor(g);
    vec2 gf = fract(g);
    float minDist = 8.0;
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            vec2 n = vec2(float(x), float(y));
            vec2 p = n + 0.5 + 0.4 * sin(t * 0.5 + 6.2831 * hash(gi + n));
            minDist = min(minDist, length(n + p - gf));
        }
    }
    return smoothstep(0.02, 0.10, minDist);   // 0 en aristas, 1 dentro de faceta
}

void main() {
    vec2 uv  = vUV.st;
    vec4 base = texture(sTD2DInputs[0], uv);

    // ── Una sola persona: pass-through ────────────────────────────────────────
    if (uBlobCount < 1.5) {
        fragColor = base;
        return;
    }

    // ── Dos personas: diálogo cubista ─────────────────────────────────────────
    // Tinte por lado: izquierda fría, derecha cálida (dos voces visuales).
    vec3 leftTint  = vec3(0.30, 0.55, 1.00);   // azul
    vec3 rightTint = vec3(1.00, 0.60, 0.30);   // ámbar
    float side = smoothstep(0.40, 0.60, uv.x); // 0 izq, 1 der
    vec3 tint  = mix(leftTint, rightTint, side);

    // Banda central de encuentro: máxima fractura cubista (la conversación).
    float center   = 1.0 - smoothstep(0.0, 0.28, abs(uv.x - 0.5));
    float facet    = facets(uv, mix(6.0, 18.0, center), uTime);
    float fracture = (1.0 - facet) * center;

    // El cuerpo de cada lado proyecta planos hacia el otro (intercambio).
    float lum   = dot(base.rgb, vec3(0.299, 0.587, 0.114));
    vec3  dialog = mix(base.rgb, tint * (lum + 0.2), 0.45 * (0.4 + center));

    // Aristas blancas brillantes en la zona de diálogo.
    dialog += fracture * vec3(1.0);

    // Pulso de "conversación": la banda central late suavemente.
    float pulse = 0.85 + 0.15 * sin(uTime * 2.0);
    dialog *= mix(1.0, pulse, center);

    float alpha = clamp(base.a + fracture * 0.6, 0.0, 1.0);
    fragColor = vec4(clamp(dialog, 0.0, 1.0), alpha);
}
