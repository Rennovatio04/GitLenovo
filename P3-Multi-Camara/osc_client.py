# ─────────────────────────────────────────────────────────────────────────────
# osc_client.py — Envío de métricas OSC compuestas (3 cámaras)
# P3 · Aún Sorprendo · JIFREX
#
# Puerto de destino: OSC_PORT (9000)
# TouchDesigner: OSC In DAT → Script DAT (td_osc_to_uniforms.py)
# ─────────────────────────────────────────────────────────────────────────────

from pythonosc import udp_client
import config


class MultiCamOSCClient:

    def __init__(self, host: str, port: int):
        self._client = udp_client.SimpleUDPClient(host, port)

    def send(self,
             a_presence: float, a_flow: float, a_motion: float,
             b_presence: float, b_flow: float, b_motion: float,
             c_presence: float, c_flow: float, c_motion: float,
             triple_ratio: float, double_ratio: float, any_presence: int):
        """Envía todas las métricas de las 3 cámaras + composición en un batch UDP."""
        s = self._client.send_message
        # Por cámara
        s("/multicam/a/presence",   float(a_presence))
        s("/multicam/a/flow_mean",  float(a_flow))
        s("/multicam/a/motion",     float(a_motion))
        s("/multicam/b/presence",   float(b_presence))
        s("/multicam/b/flow_mean",  float(b_flow))
        s("/multicam/b/motion",     float(b_motion))
        s("/multicam/c/presence",   float(c_presence))
        s("/multicam/c/flow_mean",  float(c_flow))
        s("/multicam/c/motion",     float(c_motion))
        # Composición
        s("/multicam/triple_ratio", float(triple_ratio))
        s("/multicam/double_ratio", float(double_ratio))
        s("/multicam/any_presence", int(any_presence))
