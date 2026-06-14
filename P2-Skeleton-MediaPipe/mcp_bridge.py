"""
mcp_bridge.py — Auditoría y ajuste de umbrales en tiempo real vía OSC · P2 · JIFREX
Permite modificar los umbrales semánticos sin reiniciar skeleton_runtime.py.

Uso (terminal separada):
  python mcp_bridge.py

Comandos OSC entrantes en puerto 9001:
  /mcp/set/hand_raise_margin        <float>   margen de mano sobre hombro
  /mcp/set/hip_rot_threshold_deg    <float>   grados de rotación de cadera
  /mcp/set/head_roll_threshold_deg  <float>   grados de inclinación de cabeza
  /mcp/set/motion_ratio_threshold   <float>   umbral de salto / movimiento brusco
  /mcp/set/static_flow_threshold    <float>   flujo máximo para "pose estática"
  /mcp/set/static_frames            <int>     frames de quietud para fade
  /mcp/set/dual_min_separation      <float>   separación mínima entre 2 personas
  /mcp/set/cooldown_hands           <int>
  /mcp/set/cooldown_torso           <int>
  /mcp/set/cooldown_head            <int>
  /mcp/set/cooldown_global          <int>
  /mcp/get/params                   → responde en /mcp/params (JSON) en :9002
"""

import json
import threading

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

import config

# Parámetros vivos. Las claves coinciden con las que lee zone_detector.
_params = {
    "hand_raise_margin":       config.HAND_RAISE_MARGIN,
    "hip_rot_threshold_deg":   config.HIP_ROT_THRESHOLD_DEG,
    "head_roll_threshold_deg": config.HEAD_ROLL_THRESHOLD_DEG,
    "motion_ratio_threshold":  config.MOTION_RATIO_THRESHOLD,
    "static_flow_threshold":   config.STATIC_FLOW_THRESHOLD,
    "static_frames":           config.STATIC_FRAMES,
    "dual_min_separation":     config.DUAL_MIN_SEPARATION,
    "cooldown_hands":          config.COOLDOWN_HANDS,
    "cooldown_torso":          config.COOLDOWN_TORSO,
    "cooldown_head":           config.COOLDOWN_HEAD,
    "cooldown_global":         config.COOLDOWN_GLOBAL,
}
_lock = threading.Lock()


def get_live_params() -> dict:
    """Llamar desde skeleton_runtime para leer los parámetros actualizados."""
    with _lock:
        return dict(_params)


def _handle_set(address: str, *args):
    key = address.split("/")[-1]
    with _lock:
        if key in _params and args:
            # Conserva el tipo original (int o float) del parámetro.
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

    try:
        server = ThreadingOSCUDPServer(("0.0.0.0", config.MCP_LISTEN_PORT), dispatcher)
    except OSError as exc:
        print(f"[MCP] Puerto {config.MCP_LISTEN_PORT} ocupado ({exc}) — usando bridge existente.")
        return None
    print(f"[MCP] Bridge P2 activo en puerto {config.MCP_LISTEN_PORT}")

    if blocking:
        server.serve_forever()
    else:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server


if __name__ == "__main__":
    start(blocking=True)
