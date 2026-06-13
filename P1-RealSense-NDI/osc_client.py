"""
osc_client.py — Envía métricas y triggers al Mac M3 Max (TouchDesigner :9000).
"""

from pythonosc.udp_client import SimpleUDPClient
import config


class OSCClient:
    def __init__(self):
        self._client = SimpleUDPClient(config.OSC_HOST, config.OSC_PORT)
        print(f"[OSC] Apuntando a {config.OSC_HOST}:{config.OSC_PORT}")

    def send_trigger(self, triggered: bool):
        self._client.send_message(config.OSC_TRIGGER, 1 if triggered else 0)

    def send_metrics(self, flow_mean: float, motion_ratio: float,
                     blob_area: int, presence: bool, noise_level: float):
        self._client.send_message(config.OSC_FLOW_MEAN,    float(flow_mean))
        self._client.send_message(config.OSC_MOTION_RATIO, float(motion_ratio))
        self._client.send_message(config.OSC_BLOB_AREA,    int(blob_area))
        self._client.send_message(config.OSC_PRESENCE,     1 if presence else 0)
        self._client.send_message(config.OSC_NOISE,        float(noise_level))
