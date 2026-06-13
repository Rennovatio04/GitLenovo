# td_osc_to_uniforms.py — Script DAT de TouchDesigner · Mac M3 Max · P4
# Recibe mensajes OSC de deeplab_runtime.py y actualiza uniforms de los GLSL TOPs.
#
# Setup en TouchDesigner:
#   1. OSC In DAT  → puerto 9000, UDP
#   2. Script DAT  → este archivo, Execute On: Table Change
#   3. GLSL TOPs con los nombres exactos de abajo
#
# Nombres de TOPs requeridos:
#   glsl_halo      — halo_glow_precise.glsl
#   glsl_glitch    — glitch_precise.glsl
#   glsl_particles — particles_precise.glsl
#
# Mapeo par.valueN en TouchDesigner:
#   glsl_halo:
#     value0=uFlowMean  value1=uCoverageRatio  value2=uPresence  value3=uTime
#   glsl_glitch:
#     value0=uTrigger  value1=uMotionRatio  value2=uNoiseLevel  value3=uTime
#   glsl_particles:
#     value0=uFlowMean  value1=uMotionRatio  value2=uPresence
#     value3=uCoverageRatio  value4=uNoiseLevel  value5=uTime

def onTableChange(dat):
    """Llamado por TouchDesigner cada vez que llega un paquete OSC."""

    top_halo      = op('glsl_halo')
    top_glitch    = op('glsl_glitch')
    top_particles = op('glsl_particles')

    t = absTime.seconds

    for row in range(dat.numRows):
        address = dat[row, 0].val
        val     = dat[row, 1].val
        try:
            val_f = float(val)
        except (ValueError, TypeError):
            continue

        if address == '/jifrex/p4/flow_mean':
            if top_halo:      top_halo.par.value0      = val_f
            if top_particles: top_particles.par.value0  = val_f

        elif address == '/jifrex/p4/motion_ratio':
            if top_glitch:    top_glitch.par.value1     = val_f
            if top_particles: top_particles.par.value1  = val_f

        elif address == '/jifrex/p4/trigger':
            if top_glitch:    top_glitch.par.value0     = val_f

        elif address == '/jifrex/p4/presence':
            if top_halo:      top_halo.par.value2       = val_f
            if top_particles: top_particles.par.value2  = val_f

        elif address == '/jifrex/p4/coverage_ratio':
            if top_halo:      top_halo.par.value1       = val_f
            if top_particles: top_particles.par.value3  = val_f

        elif address == '/jifrex/p4/noise_level':
            if top_glitch:    top_glitch.par.value2     = val_f
            if top_particles: top_particles.par.value4  = val_f

        # Disponible para uso futuro:
        # elif address == '/jifrex/p4/blob_area':   pass
        # elif address == '/jifrex/p4/blob_count':  pass

    # uTime en todos los shaders
    if top_halo:      top_halo.par.value3      = t
    if top_glitch:    top_glitch.par.value3     = t
    if top_particles: top_particles.par.value5  = t
