# ─────────────────────────────────────────────────────────────────────────────
# osc_client.py — Envío de métricas OSC a TouchDesigner
# P4 · Aún Sorprendo · JIFREX
#
# Rutas OSC (puerto 9000):
#   /jifrex/p4/trigger        float  0 o 1
#   /jifrex/p4/presence       float  0 o 1
#   /jifrex/p4/flow_mean      float  0.0–3.0
#   /jifrex/p4/motion_ratio   float  0.0–1.0
#   /jifrex/p4/blob_area      int    píxeles
#   /jifrex/p4/noise_level    float  0.0–N
#   /jifrex/p4/coverage_ratio float  0.0–1.0  (nuevo en P4 — Antimodular)
#   /jifrex/p4/blob_count     int    número de personas
# ─────────────────────────────────────────────────────────────────────────────

from pythonosc import udp_client
import config


class P4OSCClient:

    def __init__(self, host: str, port: int):
        self._client = udp_client.SimpleUDPClient(host, port)

    def send(self, trigger: int, presence: int, flow_mean: float,
             motion_ratio: float, blob_area: int, noise_level: float,
             coverage_ratio: float, blob_count: int):
        s = self._client.send_message
        s("/jifrex/p4/trigger",        float(trigger))
        s("/jifrex/p4/presence",       float(presence))
        s("/jifrex/p4/flow_mean",      float(flow_mean))
        s("/jifrex/p4/motion_ratio",   float(motion_ratio))
        s("/jifrex/p4/blob_area",      int(blob_area))
        s("/jifrex/p4/noise_level",    float(noise_level))
        s("/jifrex/p4/coverage_ratio", float(coverage_ratio))
        s("/jifrex/p4/blob_count",     int(blob_count))
