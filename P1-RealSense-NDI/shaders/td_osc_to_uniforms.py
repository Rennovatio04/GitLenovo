# td_osc_to_uniforms.py
# Script DAT de TouchDesigner — Mac M3 Max
# Recibe mensajes OSC de webcam_runtime.py (MSI) y actualiza uniforms de los GLSL TOPs.
#
# Setup en TouchDesigner:
#   1. OSC In DAT  → conectado al puerto 9000
#   2. Script DAT  → este archivo, con Execute On: Table Change
#   3. Los GLSL TOPs deben tener los uniforms declarados (ver abajo)
#
# Uniforms requeridos por shader:
#   halo_glow          : uFlowMean (float), uTime (float)
#   glitch             : uTrigger (float), uMotionRatio (float), uTime (float)
#   feedback_particles : uFlowMean (float), uMotionRatio (float),
#                        uPresence (float), uTime (float)

def onTableChange(dat):
    """Llamado por TouchDesigner cada vez que llega un mensaje OSC."""

    # Referencias a los GLSL TOPs (ajustar nombres según tu red TD)
    top_halo      = op('glsl_halo')
    top_glitch    = op('glsl_glitch')
    top_particles = op('glsl_particles')

    # Tiempo global del patch
    t = absTime.seconds

    for row in range(dat.numRows):
        address = dat[row, 0].val
        val     = dat[row, 1].val

        try:
            val_f = float(val)
        except (ValueError, TypeError):
            continue

        # ── Distribución de mensajes OSC a uniforms ───────────────────────────
        if address == '/jifrex/flow_mean':
            if top_halo:      top_halo.par.value0      = val_f
            if top_particles: top_particles.par.value0  = val_f

        elif address == '/jifrex/motion_ratio':
            if top_glitch:    top_glitch.par.value1     = val_f
            if top_particles: top_particles.par.value1  = val_f

        elif address == '/jifrex/trigger':
            if top_glitch:    top_glitch.par.value0     = val_f

        elif address == '/jifrex/presence':
            if top_particles: top_particles.par.value2  = val_f

        elif address == '/jifrex/blob_area':
            pass   # disponible para uso futuro

        elif address == '/jifrex/noise_level':
            pass   # disponible para uso futuro

    # Actualizar uTime en todos los shaders
    if top_halo:      top_halo.par.value1      = t
    if top_glitch:    top_glitch.par.value2     = t
    if top_particles: top_particles.par.value3  = t
