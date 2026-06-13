"""
osc_client.py — Envía rutas OSC semánticas a TouchDesigner (:9000) · P2 · JIFREX
Aún Sorprendo · Exposición Pablo Picasso

A diferencia de P1 (6 canales planos de presencia/flow), P2 envía rutas
semánticas: qué PARTE del cuerpo se mueve, qué zona disparó, y cuántas
personas hay. TouchDesigner enruta cada mensaje a su shader por zona.

Esquema OSC:
  /cuerpo/mano_derecha     <trigger 0/1> <wrist_height 0..1>
  /cuerpo/cadera           <trigger 0/1> <hip_angle deg> <hip_velocity deg/f>
  /cuerpo/cabeza           <trigger 0/1> <head_roll deg> <head_pitch deg>
  /cuerpo/pose_estatica    <trigger 0/1> <static_secs>
  /cuerpo/trigger_zona     <string: zona que disparó>
  /cuerpo/blob_count       <int 1 o 2>
  /cuerpo/global/glitch    <trigger 0/1>
  /cuerpo/metrica/...      métricas continuas por zona (ángulos, velocidades)
"""

from pythonosc.udp_client import SimpleUDPClient
import config


class OSCClient:
    def __init__(self):
        self._client = SimpleUDPClient(config.OSC_HOST, config.OSC_PORT)
        print(f"[OSC] Rutas semánticas → {config.OSC_HOST}:{config.OSC_PORT}")

    # ── Triggers semánticos por zona ──────────────────────────────────────────
    def send_hand(self, triggered: bool, wrist_height: float):
        """/cuerpo/mano_derecha — trigger 1 (mano extendida)."""
        self._client.send_message(
            config.OSC_HAND_RIGHT,
            [1 if triggered else 0, float(wrist_height)],
        )

    def send_hip(self, triggered: bool, hip_angle: float, hip_velocity: float):
        """/cuerpo/cadera — trigger 2 (rotación de cadera)."""
        self._client.send_message(
            config.OSC_HIP,
            [1 if triggered else 0, float(hip_angle), float(hip_velocity)],
        )

    def send_head(self, triggered: bool, head_roll: float, head_pitch: float):
        """/cuerpo/cabeza — trigger 3 (inclinación de cabeza)."""
        self._client.send_message(
            config.OSC_HEAD,
            [1 if triggered else 0, float(head_roll), float(head_pitch)],
        )

    def send_static(self, triggered: bool, static_secs: float):
        """/cuerpo/pose_estatica — trigger 5 (pose estática > 3 s)."""
        self._client.send_message(
            config.OSC_STATIC_POSE,
            [1 if triggered else 0, float(static_secs)],
        )

    def send_glitch(self, triggered: bool):
        """/cuerpo/global/glitch — trigger 4 (salto / movimiento brusco)."""
        self._client.send_message(config.OSC_GLOBAL_GLITCH, 1 if triggered else 0)

    def send_trigger_zone(self, zone: str):
        """/cuerpo/trigger_zona — qué zona reclamó el disparo del frame."""
        self._client.send_message(config.OSC_TRIGGER_ZONE, zone if zone else "none")

    def send_blob_count(self, count: int):
        """/cuerpo/blob_count — trigger 6 (1 o 2 personas)."""
        self._client.send_message(config.OSC_BLOB_COUNT, int(count))

    # ── Métricas continuas (alimentan los uniforms de los shaders) ────────────
    def send_metrics(self, m: dict, flow_mean: float, motion_ratio: float):
        """Envía las métricas continuas que los shaders usan como uniforms."""
        self._client.send_message(config.OSC_HIP_ANGLE,      float(m["hip_angle"]))
        self._client.send_message(config.OSC_HIP_VELOCITY,   float(m["hip_velocity"]))
        self._client.send_message(config.OSC_HEAD_ROLL,      float(m["head_roll"]))
        self._client.send_message(config.OSC_HEAD_PITCH,     float(m["head_pitch"]))
        self._client.send_message(config.OSC_ARM_OPEN_LEFT,  float(m["arm_open_l"]))
        self._client.send_message(config.OSC_ARM_OPEN_RIGHT, float(m["arm_open_r"]))
        self._client.send_message(config.OSC_FLOW_MEAN,      float(flow_mean))
        self._client.send_message(config.OSC_MOTION_RATIO,   float(motion_ratio))

    # ── Envío completo por frame (conveniencia) ───────────────────────────────
    def send_frame(self, m: dict, flow_mean: float, motion_ratio: float,
                   blob_count: int):
        """Empaqueta todos los mensajes de un frame en orden semántico."""
        self.send_hand(m["hand_raised"], m["wrist_height"])
        self.send_hip(m["hip_rotated"], m["hip_angle"], m["hip_velocity"])
        self.send_head(m["head_tilted"], m["head_roll"], m["head_pitch"])
        self.send_static(m["static_pose"], m["static_secs"])
        self.send_glitch(m["glitch"])
        self.send_trigger_zone(m["trigger_zone"])
        self.send_blob_count(blob_count)
        self.send_metrics(m, flow_mean, motion_ratio)
