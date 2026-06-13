"""
zone_detector.py — Detección semántica por zona corporal · P2 · JIFREX
Aún Sorprendo · Exposición Pablo Picasso · Galería Fernando Cano

A diferencia de P1 (que detecta presencia binaria), este módulo decide
QUÉ PARTE del cuerpo se mueve y traduce cada gesto a un evento semántico.

Zonas:
  zona_upper — hombros, codos, muñecas → extensión/flexión, apertura de brazos
  zona_lower — caderas, rodillas       → rotación lateral, cuclillas/salto
  zona_head  — nariz, oídos            → pitch y roll (inclinación)

Implementa los 6 triggers semánticos (ver tabla en README). El detector es
sin estado de cámara: recibe landmarks normalizados (0..1) por frame y mantiene
internamente el historial mínimo necesario (ángulo previo de cadera, contador
de pose estática, cooldowns por zona).

Cada landmark se pasa como dict {idx: (x, y, z, visibility)} usando los índices
de MediaPipe Pose definidos en config.LM.
"""

import math
from collections import deque

import config


def _angle_deg(ax, ay, bx, by):
    """Ángulo en grados del vector (b - a) respecto al eje X, vía arctan2."""
    return math.degrees(math.atan2(by - ay, bx - ax))


def _visible(lm, idx, min_vis=0.4):
    """True si el landmark existe y supera la visibilidad mínima."""
    p = lm.get(idx)
    return p is not None and p[3] >= min_vis


class ZoneDetector:
    """
    Detector semántico con estado mínimo. Una instancia por persona principal.
    El conteo de 2 personas (trigger 6) se resuelve fuera, en el runtime, a
    partir de la máscara de segmentación; aquí solo se consume blob_count.
    """

    def __init__(self):
        # Estado temporal
        self._prev_hip_angle  = None
        self._static_counter  = 0
        self._hip_vel_window  = deque(maxlen=5)   # suaviza velocidad de cadera

        # Cooldowns por zona (frames restantes)
        self._cd_hands  = 0
        self._cd_torso  = 0
        self._cd_head   = 0
        self._cd_global = 0

    # ── Tick de cooldowns (llamar una vez por frame) ──────────────────────────
    def _tick_cooldowns(self):
        if self._cd_hands  > 0: self._cd_hands  -= 1
        if self._cd_torso  > 0: self._cd_torso  -= 1
        if self._cd_head   > 0: self._cd_head   -= 1
        if self._cd_global > 0: self._cd_global -= 1

    # ── zona_upper — brazos / manos ───────────────────────────────────────────
    def detect_upper(self, lm, params):
        """
        Trigger 1 — Mano extendida.
        Lógica: landmark[16].y < landmark[12].y - umbral
                (muñeca derecha por encima del hombro derecho).
        Además calcula apertura de brazos (abducción) para métricas continuas.

        Devuelve dict con:
          hand_raised  : bool   (trigger 1, ya filtrado por cooldown)
          wrist_height : float  (altura normalizada de la muñeca, métrica)
          arm_open_l   : float  ángulo de apertura del brazo izquierdo
          arm_open_r   : float  ángulo de apertura del brazo derecho
        """
        L = config.LM
        margin = params.get("hand_raise_margin", config.HAND_RAISE_MARGIN)

        hand_raised  = False
        wrist_height = 0.0
        arm_open_l   = 0.0
        arm_open_r   = 0.0

        # Trigger 1: muñeca derecha sobre hombro derecho.
        if _visible(lm, L["wrist_right"]) and _visible(lm, L["shoulder_right"]):
            wrist_y    = lm[L["wrist_right"]][1]
            shoulder_y = lm[L["shoulder_right"]][1]
            wrist_height = 1.0 - wrist_y   # 0 abajo, 1 arriba (más intuitivo)
            # En coordenadas MediaPipe, Y crece hacia abajo → "por encima" = Y menor.
            if wrist_y < shoulder_y - margin and self._cd_hands == 0:
                hand_raised    = True
                self._cd_hands = params.get("cooldown_hands", config.COOLDOWN_HANDS)

        # Apertura de brazos: ángulo hombro→muñeca respecto a la vertical.
        if _visible(lm, L["shoulder_left"]) and _visible(lm, L["wrist_left"]):
            sx, sy = lm[L["shoulder_left"]][0], lm[L["shoulder_left"]][1]
            wx, wy = lm[L["wrist_left"]][0],   lm[L["wrist_left"]][1]
            arm_open_l = abs(_angle_deg(sx, sy, wx, wy))

        if _visible(lm, L["shoulder_right"]) and _visible(lm, L["wrist_right"]):
            sx, sy = lm[L["shoulder_right"]][0], lm[L["shoulder_right"]][1]
            wx, wy = lm[L["wrist_right"]][0],   lm[L["wrist_right"]][1]
            arm_open_r = abs(_angle_deg(sx, sy, wx, wy))

        return {
            "hand_raised":  hand_raised,
            "wrist_height": float(wrist_height),
            "arm_open_l":   float(arm_open_l),
            "arm_open_r":   float(arm_open_r),
        }

    # ── zona_lower — caderas / rotación ───────────────────────────────────────
    def detect_lower(self, lm, params):
        """
        Trigger 2 — Rotación de cadera.
        Lógica: abs(hip_angle - prev_hip_angle) > umbral_grados.
        hip_angle = ángulo de la línea cadera_izq → cadera_der respecto al eje X.
        Al rotar el torso, esa línea cambia de orientación entre frames.

        Devuelve dict con:
          hip_rotated  : bool   (trigger 2, filtrado por cooldown)
          hip_angle    : float  ángulo actual (grados)
          hip_velocity : float  velocidad angular suavizada (grados/frame)
        """
        L = config.LM
        thr = params.get("hip_rot_threshold_deg", config.HIP_ROT_THRESHOLD_DEG)

        hip_rotated  = False
        hip_angle    = 0.0
        hip_velocity = 0.0

        if _visible(lm, L["hip_left"]) and _visible(lm, L["hip_right"]):
            hlx, hly = lm[L["hip_left"]][0],  lm[L["hip_left"]][1]
            hrx, hry = lm[L["hip_right"]][0], lm[L["hip_right"]][1]
            hip_angle = _angle_deg(hlx, hly, hrx, hry)

            if self._prev_hip_angle is not None:
                # Diferencia angular envuelta a [-180, 180] para evitar saltos.
                delta = hip_angle - self._prev_hip_angle
                delta = (delta + 180.0) % 360.0 - 180.0
                self._hip_vel_window.append(abs(delta))
                hip_velocity = sum(self._hip_vel_window) / len(self._hip_vel_window)

                if abs(delta) > thr and self._cd_torso == 0:
                    hip_rotated    = True
                    self._cd_torso = params.get("cooldown_torso", config.COOLDOWN_TORSO)

            self._prev_hip_angle = hip_angle

        return {
            "hip_rotated":  hip_rotated,
            "hip_angle":    float(hip_angle),
            "hip_velocity": float(hip_velocity),
        }

    # ── zona_head — inclinación de cabeza ─────────────────────────────────────
    def detect_head(self, lm, params):
        """
        Trigger 3 — Inclinación de cabeza.
        Lógica: roll = atan2(nose.y - ear.y, nose.x - ear.x).
        El roll mide la inclinación lateral (oído→nariz). El pitch se estima a
        partir de la posición vertical de la nariz respecto al promedio de oídos.

        Devuelve dict con:
          head_tilted : bool   (trigger 3, filtrado por cooldown)
          head_roll   : float  grados de inclinación lateral
          head_pitch  : float  grados de inclinación arriba/abajo (estimado)
        """
        L = config.LM
        thr = params.get("head_roll_threshold_deg", config.HEAD_ROLL_THRESHOLD_DEG)

        head_tilted = False
        head_roll   = 0.0
        head_pitch  = 0.0

        nose_ok = _visible(lm, L["nose"])
        el_ok   = _visible(lm, L["ear_left"])
        er_ok   = _visible(lm, L["ear_right"])

        if nose_ok and (el_ok or er_ok):
            nx, ny = lm[L["nose"]][0], lm[L["nose"]][1]

            # Centro de los oídos disponibles (oído→nariz define el roll).
            ears = []
            if el_ok: ears.append(lm[L["ear_left"]])
            if er_ok: ears.append(lm[L["ear_right"]])
            ex = sum(e[0] for e in ears) / len(ears)
            ey = sum(e[1] for e in ears) / len(ears)

            # roll: ángulo del vector oído→nariz respecto al eje X.
            head_roll = _angle_deg(ex, ey, nx, ny)

            # pitch estimado: cuánto sube/baja la nariz respecto a la línea de
            # oídos, normalizado por la separación interaural (escala-invariante).
            if el_ok and er_ok:
                inter = math.hypot(
                    lm[L["ear_left"]][0]  - lm[L["ear_right"]][0],
                    lm[L["ear_left"]][1]  - lm[L["ear_right"]][1],
                ) + 1e-6
                head_pitch = math.degrees(math.atan2(ny - ey, inter))

            if abs(head_roll) > thr and self._cd_head == 0:
                head_tilted   = True
                self._cd_head = params.get("cooldown_head", config.COOLDOWN_HEAD)

        return {
            "head_tilted": head_tilted,
            "head_roll":   float(head_roll),
            "head_pitch":  float(head_pitch),
        }

    # ── Triggers globales (4 y 5) ─────────────────────────────────────────────
    def detect_global(self, flow_mean, motion_ratio, params):
        """
        Trigger 4 — Salto / movimiento brusco: motion_ratio > umbral.
        Trigger 5 — Pose estática > 3 s: flow_mean < umbral durante N frames.

        Devuelve dict con:
          glitch       : bool   (trigger 4, filtrado por cooldown)
          static_pose  : bool   (trigger 5)
          static_secs  : float  segundos acumulados de quietud
        """
        mr_thr   = params.get("motion_ratio_threshold", config.MOTION_RATIO_THRESHOLD)
        fl_thr   = params.get("static_flow_threshold",  config.STATIC_FLOW_THRESHOLD)
        st_frames= params.get("static_frames",          config.STATIC_FRAMES)

        # Trigger 4 — movimiento brusco.
        glitch = False
        if motion_ratio > mr_thr and self._cd_global == 0:
            glitch          = True
            self._cd_global = params.get("cooldown_global", config.COOLDOWN_GLOBAL)

        # Trigger 5 — pose estática sostenida.
        if flow_mean < fl_thr:
            self._static_counter += 1
        else:
            self._static_counter = 0

        static_pose = self._static_counter >= st_frames
        static_secs = self._static_counter / float(config.FPS)

        return {
            "glitch":      glitch,
            "static_pose": static_pose,
            "static_secs": float(static_secs),
        }

    # ── Resolución de zona dominante ──────────────────────────────────────────
    @staticmethod
    def dominant_zone(upper, lower, head, glob):
        """
        Decide qué zona reclamar como disparo principal del frame para
        /cuerpo/trigger_zona. Prioridad: global (salto) > manos > cadera >
        cabeza > estática. Devuelve un string ("" si nada disparó).
        """
        if glob["glitch"]:
            return "global"
        if upper["hand_raised"]:
            return "zona_hands"
        if lower["hip_rotated"]:
            return "zona_torso"
        if head["head_tilted"]:
            return "zona_head"
        if glob["static_pose"]:
            return "pose_estatica"
        return ""

    # ── Entrada principal por frame ───────────────────────────────────────────
    def process(self, lm, flow_mean, motion_ratio, params):
        """
        Procesa un frame completo. `lm` es {idx: (x,y,z,vis)} o None si no hay
        persona detectada (en ese caso solo evalúa los triggers globales).
        Devuelve un dict plano con todas las métricas y banderas listas para OSC.
        """
        self._tick_cooldowns()

        if lm is not None:
            upper = self.detect_upper(lm, params)
            lower = self.detect_lower(lm, params)
            head  = self.detect_head(lm, params)
        else:
            # Sin esqueleto: no reseteamos el ángulo de cadera para no provocar
            # un falso disparo al reaparecer; solo neutralizamos las zonas.
            upper = {"hand_raised": False, "wrist_height": 0.0,
                     "arm_open_l": 0.0, "arm_open_r": 0.0}
            lower = {"hip_rotated": False, "hip_angle": 0.0, "hip_velocity": 0.0}
            head  = {"head_tilted": False, "head_roll": 0.0, "head_pitch": 0.0}

        glob = self.detect_global(flow_mean, motion_ratio, params)
        zone = self.dominant_zone(upper, lower, head, glob)

        return {
            # Banderas de trigger
            "hand_raised":  upper["hand_raised"],
            "hip_rotated":  lower["hip_rotated"],
            "head_tilted":  head["head_tilted"],
            "glitch":       glob["glitch"],
            "static_pose":  glob["static_pose"],
            "trigger_zone": zone,
            # Métricas continuas
            "wrist_height": upper["wrist_height"],
            "arm_open_l":   upper["arm_open_l"],
            "arm_open_r":   upper["arm_open_r"],
            "hip_angle":    lower["hip_angle"],
            "hip_velocity": lower["hip_velocity"],
            "head_roll":    head["head_roll"],
            "head_pitch":   head["head_pitch"],
            "static_secs":  glob["static_secs"],
        }
