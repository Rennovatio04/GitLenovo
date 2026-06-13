"""
mcp_bridge.py — Auditoría y ajuste de parámetros en tiempo real vía OSC.
Permite modificar umbrales del pipeline sin reiniciar webcam_runtime.py.

Uso (terminal separada en el MSI):
  python mcp_bridge.py

Comandos OSC entrantes en puerto 9001:
  /mcp/set/area_threshold    <int>
  /mcp/set/cooldown_frames   <int>
  /mcp/set/flow_threshold    <float>
  /mcp/set/motion_threshold  <float>
  /mcp/get/params            → responde en /mcp/params con valores actuales
"""

import json
import threading

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

import config

_params = {
    "area_threshold":   config.AREA_THRESHOLD,
    "cooldown_frames":  config.COOLDOWN_FRAMES,
    "flow_threshold":   config.FLOW_THRESHOLD,
    "motion_threshold": config.MOTION_THRESHOLD,
}
_lock = threading.Lock()


def get_live_params() -> dict:
    """Llamar desde webcam_runtime para leer parámetros actualizados."""
    with _lock:
        return dict(_params)


def _handle_set(address: str, *args):
    key = address.split("/")[-1]
    with _lock:
        if key in _params and args:
            _params[key] = type(_params[key])(args[0])
            print(f"[MCP] {key} actualizado → {_params[key]}")


def _handle_get(address: str, *args):
    with _lock:
        payload = json.dumps(_params)
    client = SimpleUDPClient(config.OSC_HOST, config.MCP_RESPOND_PORT)
    client.send_message("/mcp/params", payload)
    print(f"[MCP] params → {payload}")


def start(blocking: bool = True):
    dispatcher = Dispatcher()
    dispatcher.map("/mcp/set/*",      _handle_set)
    dispatcher.map("/mcp/get/params", _handle_get)

    server = ThreadingOSCUDPServer(("0.0.0.0", config.MCP_LISTEN_PORT), dispatcher)
    print(f"[MCP] Bridge activo en puerto {config.MCP_LISTEN_PORT}")

    if blocking:
        server.serve_forever()
    else:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server


if __name__ == "__main__":
    start(blocking=True)
