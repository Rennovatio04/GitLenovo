# ─────────────────────────────────────────────────────────────────────────────
# mcp_bridge.py — Ajuste de parámetros P3 en tiempo real vía OSC
# P3 · Aún Sorprendo · JIFREX
#
# Puerto de escucha : MCP_LISTEN_PORT  (9001)
# Puerto de respuesta: MCP_RESPOND_PORT (9002)
#
# Uso desde cualquier cliente OSC:
#   /mcp/set/sync_window_ms     <float>
#   /mcp/set/mask_threshold     <float>
#   /mcp/set/triple_threshold   <float>
#   /mcp/set/mp_model_complexity <float>  (requiere reinicio de hilos)
#   /mcp/get/params             → responde en :9002 con /mcp/params/<key>
# ─────────────────────────────────────────────────────────────────────────────

import threading
from pythonosc import dispatcher, osc_server, udp_client
import config

_params = {
    "sync_window_ms":      float(config.SYNC_WINDOW_MS),
    "mask_threshold":      config.MASK_THRESHOLD,
    "triple_threshold":    config.TRIPLE_THRESHOLD,
    "mp_model_complexity": float(config.MP_MODEL_COMPLEXITY),
}
_lock = threading.Lock()


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
    print(f"[MCP] Escuchando en :{config.MCP_LISTEN_PORT} "
          f"→ responde en :{config.MCP_RESPOND_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    start()
