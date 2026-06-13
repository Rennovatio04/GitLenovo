# td_osc_to_uniforms.py
# Script DAT de TouchDesigner — P2 Skeleton Semántico · JIFREX
# Recibe rutas OSC semánticas de skeleton_runtime.py y actualiza los uniforms
# de los GLSL TOPs por zona corporal.
#
# Setup en TouchDesigner:
#   1. OSC In DAT  → puerto 9000
#   2. Script DAT  → este archivo, Execute On: Table Change
#   3. Los GLSL TOPs deben tener los uniforms declarados (ver tabla abajo)
#
# A diferencia de P1 (6 canales planos), P2 usa rutas semánticas con varios
# argumentos por mensaje. El OSC In DAT entrega cada argumento en una columna:
#   col 0 = address · col 1 = arg0 · col 2 = arg1 · col 3 = arg2 ...
#
# Uniforms por shader (nombre del GLSL TOP → uniforms):
#   glsl_hands  : uHandTrigger, uWristHeight, uArmOpenR, uTime
#   glsl_torso  : uHipTrigger, uHipAngle, uHipVelocity, uTime
#   glsl_head   : uHeadTrigger, uHeadRoll, uHeadPitch, uTime
#   glsl_glitch : uGlitch, uMotionRatio, uFlowMean, uTime
#   glsl_dual   : uBlobCount, uTime


def _f(dat, row, col, default=0.0):
    """Lee una celda como float con fallback seguro."""
    try:
        return float(dat[row, col].val)
    except (ValueError, TypeError, AttributeError):
        return default


def onTableChange(dat):
    """Llamado por TouchDesigner cada vez que llega un mensaje OSC."""

    # Referencias a los GLSL TOPs (ajustar nombres según tu red TD).
    top_hands  = op('glsl_hands')
    top_torso  = op('glsl_torso')
    top_head   = op('glsl_head')
    top_glitch = op('glsl_glitch')
    top_dual   = op('glsl_dual')

    t = absTime.seconds

    for row in range(dat.numRows):
        address = dat[row, 0].val

        # ── Trigger 1 — Mano extendida ────────────────────────────────────────
        if address == '/cuerpo/mano_derecha':
            if top_hands:
                top_hands.par.value0 = _f(dat, row, 1)   # uHandTrigger
                top_hands.par.value1 = _f(dat, row, 2)   # uWristHeight

        # ── Trigger 2 — Rotación de cadera ────────────────────────────────────
        elif address == '/cuerpo/cadera':
            if top_torso:
                top_torso.par.value0 = _f(dat, row, 1)   # uHipTrigger
                top_torso.par.value1 = _f(dat, row, 2)   # uHipAngle
                top_torso.par.value2 = _f(dat, row, 3)   # uHipVelocity

        # ── Trigger 3 — Inclinación de cabeza ─────────────────────────────────
        elif address == '/cuerpo/cabeza':
            if top_head:
                top_head.par.value0 = _f(dat, row, 1)    # uHeadTrigger
                top_head.par.value1 = _f(dat, row, 2)    # uHeadRoll
                top_head.par.value2 = _f(dat, row, 3)    # uHeadPitch

        # ── Trigger 4 — Salto / movimiento brusco ─────────────────────────────
        elif address == '/cuerpo/global/glitch':
            if top_glitch:
                top_glitch.par.value0 = _f(dat, row, 1)  # uGlitch

        elif address == '/cuerpo/metrica/motion_ratio':
            if top_glitch:
                top_glitch.par.value1 = _f(dat, row, 1)  # uMotionRatio

        elif address == '/cuerpo/metrica/flow_mean':
            if top_glitch:
                top_glitch.par.value2 = _f(dat, row, 1)  # uFlowMean

        # ── Trigger 6 — 2 personas ────────────────────────────────────────────
        elif address == '/cuerpo/blob_count':
            if top_dual:
                top_dual.par.value0 = _f(dat, row, 1)    # uBlobCount

        # ── Métricas extra para zona_hands (apertura de brazo derecho) ────────
        elif address == '/cuerpo/metrica/arm_open_right':
            if top_hands:
                top_hands.par.value2 = _f(dat, row, 1)   # uArmOpenR

        # /cuerpo/pose_estatica y /cuerpo/trigger_zona se pueden conectar a un
        # Switch TOP o a un Level TOP de fade global (ver README_TouchDesigner).

    # ── uTime en todos los shaders ────────────────────────────────────────────
    if top_hands:  top_hands.par.value3  = t
    if top_torso:  top_torso.par.value3  = t
    if top_head:   top_head.par.value3   = t
    if top_glitch: top_glitch.par.value3 = t
    if top_dual:   top_dual.par.value1   = t
