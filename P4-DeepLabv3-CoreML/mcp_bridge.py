# ─────────────────────────────────────────────────────────────────────────────
# mcp_bridge.py — Ajuste de parámetros P4 en tiempo real vía OSC
# P4 · Aún Sorprendo · JIFREX
#
# "Ciclo de auditoría MCP: mejora en tiempo real durante la exposición"
# — Propuesta 4, ventaja conceptual Antimodular
#
# Puerto de escucha : 9001
# Puerto de respuesta: 9002
#
# Parámetros ajustables sin reiniciar:
#   /mcp/set/area_threshold    <float>  — px mínimos para considerar blob
#   /mcp/set/cooldown_frames   <float>  — frames entre triggers
#   /mcp/set/flow_threshold    <float>  — flow_mean mínimo para trigger
#   /mcp/set/motion_threshold  <float>  — motion_ratio mínimo para trigger
#   /mcp/set/coverage_boost    <float>  — multiplicador del coverage_ratio en OSC
#   /mcp/get/params            → responde en :9002 con /mcp/params/<key>
# ─────────────────────────────────────────────────────────────────────────────

import threading
from pythonosc import dispatcher, osc_server, udp_client
import config

_params = dict(config.MCP_DEFAULTS)
_lock   = threading.Lock()


def get_live_params() -> dict:
    with _lock:
        return dict(_params)


def _on_set(address: str, *args):
    key = address.split("/")[-1]
    with _lock:
        if key in _params and args:
            _params[key] = float(args[0])
            print(f"[MCP] {key} = {_params[key]}")


def _on_get(address: str, *args):
    client = udp_client.SimpleUDPClient(config.OSC_HOST, config.MCP_RESPOND_PORT)
    with _lock:
        for k, v in _params.items():
            client.send_message(f"/mcp/params/{k}", v)


def start():
    d = dispatcher.Dispatcher()
    d.map("/mcp/set/*", _on_set)
    d.map("/mcp/get/params", _on_get)
    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", config.MCP_LISTEN_PORT), d)
    print(f"[MCP] Escuchando en :{config.MCP_LISTEN_PORT} → "
          f"responde en :{config.MCP_RESPOND_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    start()
