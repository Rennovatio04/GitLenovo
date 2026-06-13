# td_osc_to_uniforms.py — Script DAT de TouchDesigner · Mac M3 Max · P3
# Recibe mensajes OSC de multicam_runtime.py y actualiza uniforms de los GLSL TOPs.
#
# Setup en TouchDesigner:
#   1. OSC In DAT  → puerto 9000, UDP
#   2. Script DAT  → este archivo, Execute On: Table Change
#   3. Los GLSL TOPs deben existir con los nombres exactos de abajo
#
# Nombres de TOPs requeridos (DEBEN coincidir exactamente):
#   glsl_composite  — composite_multicamara.glsl
#   glsl_distort_a  — distorsion_uv.glsl (uPerspective=0, frontal)
#   glsl_distort_b  — distorsion_uv.glsl (uPerspective=1, lateral)
#   glsl_distort_c  — distorsion_uv.glsl (uPerspective=2, cenital)
#   glsl_particles  — particulas_perspectiva.glsl
#
# Mapeo de parámetros en GLSL TOPs (par.value0 … par.valueN):
#   glsl_composite:
#     value0=uFlowA  value1=uFlowB  value2=uFlowC
#     value3=uTripleRatio  value4=uAnyPresence  value5=uTime
#   glsl_distort_a/b/c:
#     value0=uPerspective (FIJO: 0, 1, 2)  value1=uFlowMean  value2=uTime
#   glsl_particles:
#     value0=uPerspective (fijo o dinámico)
#     value1=uFlowA  value2=uFlowB  value3=uFlowC
#     value4=uMotionA  value5=uMotionB  value6=uMotionC
#     value7=uTripleRatio  value8=uAnyPresence  value9=uTime

def onTableChange(dat):
    """Llamado por TouchDesigner cada vez que llega un paquete OSC."""

    top_comp    = op('glsl_composite')
    top_dist_a  = op('glsl_distort_a')
    top_dist_b  = op('glsl_distort_b')
    top_dist_c  = op('glsl_distort_c')
    top_part    = op('glsl_particles')

    t = absTime.seconds

    # Asegurar uPerspective fijo en los distort (no cambia via OSC)
    if top_dist_a: top_dist_a.par.value0 = 0.0   # frontal
    if top_dist_b: top_dist_b.par.value0 = 1.0   # lateral
    if top_dist_c: top_dist_c.par.value0 = 2.0   # cenital

    for row in range(dat.numRows):
        address = dat[row, 0].val
        val     = dat[row, 1].val
        try:
            val_f = float(val)
        except (ValueError, TypeError):
            continue

        # ── Distribución OSC → uniforms ────────────────────────────────────────
        if address == '/multicam/a/flow_mean':
            if top_comp:   top_comp.par.value0    = val_f
            if top_dist_a: top_dist_a.par.value1  = val_f
            if top_part:   top_part.par.value1    = val_f

        elif address == '/multicam/b/flow_mean':
            if top_comp:   top_comp.par.value1    = val_f
            if top_dist_b: top_dist_b.par.value1  = val_f
            if top_part:   top_part.par.value2    = val_f

        elif address == '/multicam/c/flow_mean':
            if top_comp:   top_comp.par.value2    = val_f
            if top_dist_c: top_dist_c.par.value1  = val_f
            if top_part:   top_part.par.value3    = val_f

        elif address == '/multicam/a/motion':
            if top_part:   top_part.par.value4    = val_f

        elif address == '/multicam/b/motion':
            if top_part:   top_part.par.value5    = val_f

        elif address == '/multicam/c/motion':
            if top_part:   top_part.par.value6    = val_f

        elif address == '/multicam/triple_ratio':
            if top_comp:   top_comp.par.value3    = val_f
            if top_part:   top_part.par.value7    = val_f

        elif address == '/multicam/any_presence':
            if top_comp:   top_comp.par.value4    = val_f
            if top_part:   top_part.par.value8    = val_f

        # Disponible para uso futuro:
        # elif address == '/multicam/double_ratio': pass
        # elif address == '/multicam/[a|b|c]/presence': pass

    # uTime en todos los shaders (absTime.seconds del patch TD)
    if top_comp:   top_comp.par.value5   = t
    if top_dist_a: top_dist_a.par.value2 = t
    if top_dist_b: top_dist_b.par.value2 = t
    if top_dist_c: top_dist_c.par.value2 = t
    if top_part:   top_part.par.value9   = t
