// ─────────────────────────────────────────────────────────────────────────────
// feedback_particles.glsl — Shader 3: Partículas del borde + estela temporal
// Aún Sorprendo · JIFREX · P1 · RealSense D435i + NDI · v0.2
//
// CONCEPTO ARTÍSTICO:
//   Las partículas son la huella temporal del cuerpo — emergen del borde exacto
//   de la silueta y flotan hacia afuera, dejando un rastro que persiste un momento
//   después de que el cuerpo se ha movido. Vemos el tiempo condensado en el espacio.
//   El color varía de azul suave (movimiento lento) a blanco frío (movimiento intenso).
//
// QUÉ DEBERÍAS VER:
//   - Visitante quieto: 12 partículas tenues emergiendo del borde (densidad mínima)
//   - En movimiento moderado: 24+ partículas azules del borde, con estela de ~2.5 s
//   - Movimiento intenso (flow > 1.5): partículas blancas rápidas, muy visibles
//   - Sin visitante (uPresence=0): la estela decae rápidamente (~0.2 s)
//
// TÉCNICA — LOOP DE FEEDBACK:
//   Este shader se conecta dentro de un loop Feedback TOP en TouchDesigner:
//
//   [glitch TOP] ──┐
//                  ├─► [GLSL TOP: feedback_particles] ──► [Feedback TOP] ─┐
//   [Feedback TOP] ┘                                                        │
//   [mask_orig] ─────────────────────────────────────────────────────────────┘
//
//   En cada frame:
//   - input[0] = frame actual (salida de glitch.glsl)
//   - input[1] = este mismo shader del frame ANTERIOR, multiplicado por Opacity del Feedback TOP
//   - input[2] = máscara binaria original (para detectar borde)
//
//   El decay de las partículas es DOBLE:
//   1. Feedback TOP multiplica el frame anterior por 0.92 (Opacity)
//   2. Este shader multiplica el result de prev por 0.96 (variable según presencia)
//   Decay total por frame: 0.92 × 0.96 = 0.883 → estela visible ~2.5 s
//
// CORRECCIÓN v0.2 (bug de emisión):
//   v0.1: Las partículas se generaban en coordenadas UV aleatorias → efecto invisible.
//   v0.2: La emisión se ancla al fragmento actual si está en el borde (uvEdge > 0).
//         Cada slot de partícula SOLO EMITE en píxeles donde hay borde real.
//
// Entrada  [0]: frame actual (salida de glitch.glsl)
// Entrada  [1]: frame anterior (Feedback TOP — opacidad 0.92)
// Entrada  [2]: máscara binaria original (NDI desde MSI)
//
// Uniforms (actualizados por osc_to_uniforms cada frame):
//   uFlowMean    ← OSC /jifrex/flow_mean    (0.0–3.0)
//   uMotionRatio ← OSC /jifrex/motion_ratio (0.0–1.0)
//   uPresence    ← OSC /jifrex/presence     (0 ó 1)
//   uTime        ← absTime.seconds
//
// En TouchDesigner:
//   Feedback TOP → Opacity: 0.92
//   Feedback TOP → Target TOP: glsl_particles  (este mismo operator)
// ─────────────────────────────────────────────────────────────────────────────

uniform sampler2D sTD2DInputs[3];
uniform vec4      uTDOutputInfo;
uniform float     uFlowMean;       // OSC /jifrex/flow_mean   — 0 = quieto, 1.5+ = movimiento activo
uniform float     uMotionRatio;    // OSC /jifrex/motion_ratio — 0 = ningún px, 1 = todos en mov.
uniform float     uPresence;       // OSC /jifrex/presence    — 1 = persona detectada, 0 = sin nadie
uniform float     uTime;           // absTime.seconds en TD

in  vec4 vUV;
out vec4 fragColor;

// ── Utilidades de hash/noise ───────────────────────────────────────────────────
// hash(vec2): pseudo-random de alta calidad basado en sin+fract.
// Se usa para distribuir las partículas aleatoriamente sin patrones visibles.
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

// hash3(vec3): versión 3D para diversificar seeds entre ángulo, velocidad y ciclo de vida.
float hash3(vec3 p) {
    return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453);
}

// ── Noise 2D suave (smoothstep interpolado) ───────────────────────────────────
// Produce campo de ruido suave para la turbulencia de las partículas.
// Sin esto, las partículas vuelan en línea recta (no natural).
float noise(vec2 p) {
    vec2  i = floor(p);
    vec2  f = fract(p);
    // Suavizado cúbico de Hermite: más suave que linear, sin overshooting
    vec2  u = f * f * (3.0 - 2.0 * f);
    float a = hash(i + vec2(0.0, 0.0));
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

// ── Detección de borde de la máscara (dónde nacen las partículas) ─────────────
// Usa derivadas parciales (dFdx/dFdy) para detectar la transición 0→1 en la máscara.
// Retorna 0 en el interior y en el fondo; ~1 solo en el borde de la silueta.
// Multiplicador 6.0: amplifica el gradiente para que sea más definido.
// (En P4 se usa 11.0 porque DeepLabv3 produce bordes más limpios.)
float maskEdge(vec2 uv, vec2 px) {
    float c  = texture(sTD2DInputs[2], uv).r;
    float dx = dFdx(c);
    float dy = dFdy(c);
    return clamp(sqrt(dx*dx + dy*dy) * 6.0, 0.0, 1.0);
}

// ── Función de partícula individual ──────────────────────────────────────────
// Devuelve 1 si el UV actual está cerca de pPos (dentro de 'size'), 0 si no.
// smoothstep(size, 0, d): cuando d < size, devuelve un valor 0→1 suavizado.
// Esto crea partículas con borde suave (no cuadradas).
float particle(vec2 uv, vec2 pPos, float size) {
    float d = length(uv - pPos);
    return smoothstep(size, 0.0, d);
}

void main() {
    vec2  uv   = vUV.st;
    vec2  px   = uTDOutputInfo.zw;   // tamaño de 1px en UV
    float t    = uTime;
    float fm   = clamp(uFlowMean,   0.0, 3.0);
    float mr   = clamp(uMotionRatio,0.0, 1.0);

    // ── 1. Frame anterior con decay (estela de partículas) ────────────────────
    vec4 prev = texture(sTD2DInputs[1], uv);
    // Decay diferenciado: con presencia (visitante activo) la estela dura más.
    // Sin presencia (visitante salió), la estela desaparece rápidamente:
    //   uPresence=1 → decay=0.96 → 0.96^30 = 0.294 → visible ~2.5 s a 30fps
    //   uPresence=0 → decay=0.75 → 0.75^10 = 0.056 → desaparece en ~0.3 s
    // El mix con (1.0 - uPresence) produce la transición suave entre los dos valores.
    float decay = (uPresence > 0.5) ? 0.96 : mix(0.96, 0.75, (1.0 - uPresence));
    prev.rgb *= decay;

    // ── 2. Frame actual (salida de glitch.glsl) ───────────────────────────────
    vec4 current = texture(sTD2DInputs[0], uv);

    // ── 3. Detección del borde donde nacen las partículas ─────────────────────
    float edge    = maskEdge(uv, px);   // 0 lejos del borde, ~1 en el borde
    float partCol = 0.0;                // luminosidad total de partículas en este px

    // ── 4. Loop de partículas ─────────────────────────────────────────────────
    // Número de partículas proporcional a motion_ratio:
    //   mr=0.0 → 12 partículas (mínimo para efecto visible)
    //   mr=1.0 → 36 partículas (máximo)
    int numParticles = int(12.0 + mr * 24.0);

    // uvEdge: peso de emisión en este fragmento — solo emite si hay borde real.
    // Esto es la corrección central de v0.2: las partículas nacen donde el cuerpo
    // realmente termina, no en coordenadas aleatorias del frame.
    float uvEdge = maskEdge(uv, px);

    for (int i = 0; i < 36; i++) {
        if (i >= numParticles) break;

        float fi   = float(i);
        // seed varía con el tiempo (floor(t * 4.0) = cambia 4 veces por segundo)
        // para que las partículas no repitan exactamente el mismo patrón.
        float seed = fi * 0.137 + floor(t * 4.0) * 0.031;

        // Ángulo de escape pseudo-aleatorio (0 a 2π)
        float angle = hash3(vec3(fi, seed, 3.0)) * 6.28318;
        // Velocidad variable por partícula: base + fracción de mr
        float speed = (0.018 + mr * 0.035) * (0.5 + hash3(vec3(fi, seed, 2.0)) * 0.5);

        // Ciclo de vida normalizado (0=nace, 1=muere): ciclo continuo
        // fract() hace que cada partícula tenga su propio ciclo periódico.
        float life = fract(t * speed * 5.0 + hash(vec2(fi, seed)));

        // Posición en este frame: nace en uv y se desplaza según velocidad × vida
        vec2 velocity  = vec2(cos(angle), sin(angle)) * speed;
        // Gravedad negativa leve: las partículas tienden a flotar ligeramente hacia arriba
        velocity.y    -= 0.006 * life;
        // Turbulencia de ruido: evita líneas rectas perfectas
        float nx = noise(uv * 10.0 + t * 0.25) * 0.018;
        float ny = noise(uv * 10.0 + t * 0.25 + 5.5) * 0.018;
        vec2 pos = uv + (velocity + vec2(nx, ny)) * life;

        // Tamaño decrece con la edad: la partícula nace grande y muere pequeña
        // size: 0.009 (nacimiento) → 0.002 (muerte)
        float size   = mix(0.009, 0.002, life);
        // Peso de emisión: solo emite en bordes reales (uvEdge), y se amortigua
        // con la edad (life: 1=recién nacida, 0=ya murió → (1-life) decae)
        float weight = uvEdge * (1.0 - life);
        partCol += particle(uv, pos, size) * weight;
    }

    partCol = clamp(partCol, 0.0, 1.0);

    // ── 5. Color de partículas (azul→blanco según velocidad) ─────────────────
    // fm=0 → azul suave (movimiento lento o reposo)
    // fm=1.5+ → blanco frío (movimiento intenso)
    // fm * 0.4: el cambio de color empieza a fm=0 y satura a fm=2.5
    vec3 partColor = mix(
        vec3(0.3, 0.6, 1.0),    // azul suave — movimiento lento
        vec3(0.9, 0.95, 1.0),   // blanco frío — movimiento intenso
        fm * 0.4
    );

    // ── 6. Composite final (Screen blend) ────────────────────────────────────
    // max(prev, current): equivalente a Screen blend cuando uno de los dos es oscuro.
    // Esto combina el frame actual con la estela sin sobresaturar los colores claros.
    // + partículas encima: intensidad escala con flow (más movimiento = más brillo)
    vec3 col = prev.rgb;
    col      = max(col, current.rgb);                    // Screen blend estela + actual
    col     += partColor * partCol * (1.0 + fm * 0.5);  // partículas encima
    col      = clamp(col, 0.0, 1.0);

    float alpha = clamp(prev.a * decay + current.a + partCol * 0.8, 0.0, 1.0);

    fragColor = vec4(col, alpha);
}
