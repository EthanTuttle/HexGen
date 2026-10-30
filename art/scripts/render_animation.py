"""Renders a short looping video of the test map with moving water, as the look target for the engines' water shader.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_animation.py
Writes art/preview/water_anim_vN.mp4 (never overwrites).

What moves (rules: design/07 Presentation.md -> Art direction -> Water flows freely):
- ripples flow along rivers (a two-phase flow-map scroll) and drift slowly on lakes and ponds
- sparkle: rare, brief glints, each on its own random clock (never in step with each other)
- a foam rim at the shore that breathes in and out, and darker water away from the shore
- boats bob gently

Per water vertex the mesh carries two attributes the shader reads; the engines need the same two:
  depth  distance to the nearest shore (0 at the bank)
  flow   direction and speed of the water there
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.geometry import delaunay_2d_cdt  # noqa: E402

import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import water as wt  # noqa: E402

FPS = 24
SECONDS = 6
RIVER_SPEED = 0.6   # metres per second along rivers
LAKE_SPEED = 0.15   # drift near lake shores
GRID = 0.35         # spacing of extra points inside the water, so depth can shade smoothly


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / (ab.length_squared or 1)))
    return (p - (a + ab * t)).length, t


def water_mesh(water_tiles):
    """One mesh for all water, with depth and flow per vertex."""
    shores = []      # (points in world, flow sign, speed)
    outlines = []
    for q, r, at, mask in water_tiles:
        outs, curves, kind, ends = wt.tile_water(mask, f"{q},{r}")
        h = wt.downhill(q, r)
        inflow = [wt.downhill(q + dq, r + dr) < h for dq, dr in hk.NEIGHBOURS]
        speed = RIVER_SPEED if kind in ("river", "spring") else LAKE_SPEED
        for curve, sign in zip(curves, wt.flow_signs(ends, inflow)):
            shores.append(([at.to_2d() + Vector(p) for p in curve], sign, speed))
        outlines += [[at.to_2d() + Vector(p) for p in poly] for poly in outs]

    bm = bmesh.new()
    depth_l = bm.verts.layers.float.new("depth")
    flow_l = bm.verts.layers.float_vector.new("flow")
    for poly in outlines:
        # Points along long outline segments too (e.g. where a river crosses a tile edge), so depth is right there.
        dense = []
        for k in range(len(poly)):
            a, b = poly[k], poly[(k + 1) % len(poly)]
            steps = max(1, int((b - a).length / GRID))
            dense += [a.lerp(b, j / steps) for j in range(steps)]
        poly = dense
        pts = list(poly)
        xs, ys = [p.x for p in poly], [p.y for p in poly]
        y = min(ys) + GRID / 2
        while y < max(ys):
            x = min(xs) + GRID / 2 + (GRID / 2 if int((y - min(ys)) / GRID) % 2 else 0)
            while x < max(xs):
                p = Vector((x, y))
                if wt.point_in([tuple(v) for v in poly], (x, y)) and \
                        min(seg_dist(p, poly[k - 1], poly[k])[0] for k in range(len(poly))) > GRID * 0.4:
                    pts.append(p)
                x += GRID
            y += GRID
        verts, _, faces, *_ = delaunay_2d_cdt(pts, [], [list(range(len(poly)))], 1, 1e-5)
        bvs = [bm.verts.new((v.x, v.y, 0.03)) for v in verts]
        for f in faces:
            try:
                bm.faces.new([bvs[i] for i in f])
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)

    for v in bm.verts:
        p = v.co.to_2d()
        best = (1e9, Vector((0, 0)), 0, 0)
        for pts, sign, speed in shores:
            for k in range(1, len(pts)):
                d, _ = seg_dist(p, pts[k - 1], pts[k])
                if d < best[0]:
                    best = (d, (pts[k] - pts[k - 1]).normalized(), sign, speed)
        d, tangent, sign, speed = best
        # Rivers flow across their whole width; lakes only drift near the shore.
        fade = 1.0 if speed == RIVER_SPEED else max(0.0, 1.0 - d / 2.5)
        v[depth_l] = min(d, 10.0)
        v[flow_l] = (tangent * sign * speed * fade).to_3d()

    mesh = bpy.data.meshes.new("water")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("water", mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(water_material())
    return obj


# --- Shader ------------------------------------------------------------------

def water_material():
    mat = bpy.data.materials.new("water_animated")
    mat.use_nodes = True
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]

    def node(kind, **inputs):
        n = N.new(kind)
        for k, val in inputs.items():
            if k == "op":
                n.operation = val
            elif k == "dims":
                n.noise_dimensions = val
            else:
                n.inputs[k].default_value = val
        return n

    def math_(op, a, b=None, c=None):
        n = node("ShaderNodeMath", op=op)
        for i, x in enumerate((a, b, c)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                L.new(x, n.inputs[i])
        return n.outputs[0]

    def vec(op, a, b=None, scale=None):
        n = node("ShaderNodeVectorMath", op=op)
        L.new(a, n.inputs[0])
        if b is not None:
            L.new(b, n.inputs[1])
        if scale is not None:
            if isinstance(scale, (int, float)):
                n.inputs["Scale"].default_value = scale
            else:
                L.new(scale, n.inputs["Scale"])
        return n.outputs[0]

    # Time in seconds, keyframed so it plays back without drivers.
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"  # steady time, no easing
    t = N.new("ShaderNodeValue")
    t.outputs[0].default_value = 0.0
    t.outputs[0].keyframe_insert("default_value", frame=1)
    t.outputs[0].default_value = SECONDS
    t.outputs[0].keyframe_insert("default_value", frame=1 + FPS * SECONDS)
    time = t.outputs[0]

    depth = node("ShaderNodeAttribute")
    depth.attribute_name = "depth"
    flow = node("ShaderNodeAttribute")
    flow.attribute_name = "flow"
    pos = node("ShaderNodeNewGeometry").outputs["Position"]

    # Flow map: two copies of the ripple scroll along the flow, each restarting every 2 s, cross-faded
    # so the restart never shows.
    # Each spot's cycle is offset by a slow noise, so the restarts never line up across the water.
    period = 2.0
    offset = node("ShaderNodeTexNoise", Scale=0.25, Detail=0.0)
    L.new(pos, offset.inputs["Vector"])
    cycle = math_("ADD", math_("DIVIDE", time, period), math_("MULTIPLY", offset.outputs["Fac"], 3.0))
    ph0 = math_("FRACT", cycle)
    ph1 = math_("FRACT", math_("ADD", cycle, 0.5))
    p0 = vec("SUBTRACT", pos, vec("SCALE", flow.outputs["Vector"], scale=math_("MULTIPLY", ph0, period)))
    p1 = vec("ADD", vec("SUBTRACT", pos, vec("SCALE", flow.outputs["Vector"], scale=math_("MULTIPLY", ph1, period))),
             node("ShaderNodeCombineXYZ", X=3.7, Y=1.9, Z=0).outputs[0])
    blend = math_("ABSOLUTE", math_("MULTIPLY", math_("SUBTRACT", ph0, 0.5), 2.0))  # 1 when copy 0 restarts

    def ripples(p, scale, detail):
        n = node("ShaderNodeTexNoise", Scale=scale, Detail=detail, Roughness=0.5, dims="4D")
        L.new(p, n.inputs["Vector"])
        L.new(math_("MULTIPLY", time, 0.12), n.inputs["W"])  # slow shimmer even where water is still
        return n.outputs["Fac"]

    def flowing(scale, detail):
        mix = node("ShaderNodeMix")
        mix.data_type = "FLOAT"
        L.new(blend, mix.inputs["Factor"])
        L.new(ripples(p0, scale, detail), mix.inputs["A"])
        L.new(ripples(p1, scale, detail), mix.inputs["B"])
        return mix.outputs["Result"]

    wave = flowing(0.9, 3.0)

    # Bump from the ripples catches the sun: moving highlights.
    bump = node("ShaderNodeBump", Strength=0.7, Distance=0.08)
    L.new(wave, bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Colour: shallow near the bank, deeper further out.
    deep = node("ShaderNodeMapRange", **{"From Min": 0.2, "From Max": 2.2})
    deep.interpolation_type = "SMOOTHSTEP"
    L.new(depth.outputs["Fac"], deep.inputs["Value"])
    col = node("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs["A"].default_value = (0.36, 0.70, 0.86, 1)   # shallow
    col.inputs["B"].default_value = (0.13, 0.42, 0.66, 1)   # deep
    L.new(deep.outputs["Result"], col.inputs["Factor"])

    # Foam: a rim at the bank that breathes and frays with the ripples.
    edge = math_("ADD", 0.05, math_("ADD", math_("MULTIPLY", math_("SINE", math_("MULTIPLY", time, 1.6)), 0.03),
                                   math_("MULTIPLY", wave, 0.12)))
    foam = math_("LESS_THAN", depth.outputs["Fac"], edge)
    foamed = node("ShaderNodeMix")
    foamed.data_type = "RGBA"
    foamed.inputs["B"].default_value = (0.94, 0.97, 1.0, 1)
    L.new(math_("MULTIPLY", foam, 0.75), foamed.inputs["Factor"])
    L.new(col.outputs["Result"], foamed.inputs["A"])
    L.new(foamed.outputs["Result"], bsdf.inputs["Base Color"])

    # Sparkle: the brightest specks of the fine ripples glow, away from the foam.
    # Sparkle: the water is split into small random cells drifting with the flow. About 1 cell in 5 can
    # glint, each with its own pace (one blink every 5-8 s) and phase, and a blink lasts about a quarter second.
    drift = vec("SUBTRACT", pos, vec("SCALE", flow.outputs["Vector"], scale=time))
    cells = node("ShaderNodeTexVoronoi", Scale=2.2)
    L.new(drift, cells.inputs["Vector"])
    rand = node("ShaderNodeSeparateColor")
    L.new(cells.outputs["Color"], rand.inputs["Color"])
    can = math_("GREATER_THAN", rand.outputs[0], 0.8)
    pace = math_("DIVIDE", 6.283, math_("ADD", 5.0, math_("MULTIPLY", rand.outputs[1], 3.0)))
    wave_t = math_("SINE", math_("ADD", math_("MULTIPLY", time, pace), math_("MULTIPLY", rand.outputs[2], 6.283)))
    blink = math_("MAXIMUM", math_("DIVIDE", math_("SUBTRACT", wave_t, 0.985), 0.015), 0.0)
    dot_ = math_("LESS_THAN", cells.outputs["Distance"], 0.07)
    spark = math_("MULTIPLY", math_("MULTIPLY", can, blink),
                  math_("MULTIPLY", dot_, math_("GREATER_THAN", depth.outputs["Fac"], 0.35)))
    L.new(math_("MULTIPLY", spark, 2.5), bsdf.inputs["Emission Strength"])
    bsdf.inputs["Emission Color"].default_value = (1, 1, 1, 1)
    bsdf.inputs["Roughness"].default_value = 0.18
    return mat


def bob_boats(water_tiles, col):
    for q, r, at, mask in water_tiles:
        outs, curves, kind, _ = wt.tile_water(mask, f"{q},{r}")
        for k, (p, ang) in enumerate(wt.dressing(outs, curves, kind, f"{q},{r}")[4]):
            piece = hk.Piece(f"boat_{q}_{r}_{k}")
            wt.add_boat(piece, Vector((0, 0, 0)), ang)
            obj = piece.finish(col, at + Vector((p[0], p[1], 0)))
            for f in range(1, FPS * SECONDS + 2, 6):
                s = (f - 1) / FPS
                obj.location.z = 0.03 * math.sin(2 * math.pi * s / 2 + k)
                obj.rotation_euler.x = 0.05 * math.sin(2 * math.pi * s / 3 + k)
                obj.keyframe_insert("location", index=2, frame=f)
                obj.keyframe_insert("rotation_euler", index=0, frame=f)


def video_output(path):
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FPS * SECONDS
    try:
        scene.render.image_settings.media_type = "VIDEO"
    except (AttributeError, TypeError):
        pass
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = path


if __name__ == "__main__":
    hk.empty_scene()
    tiles = rp.load_templates(rp.latest("tiles", "tiles"))
    water_tiles = rp.build_map(tiles, animated=True)
    water_mesh(water_tiles)
    bob_boats(water_tiles, hk.new_collection("boats"))
    rp.stage(Vector((5, -5, 0)), 46, 42)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 1280, 800
    out = os.path.join(hk.ART, "preview")
    n = 1
    while os.path.exists(os.path.join(out, f"water_anim_v{n}.mp4")):
        n += 1
    path = os.path.join(out, f"water_anim_v{n}.mp4")
    if "--still" in sys.argv:  # one frame, for checking the look quickly
        scene.frame_set(FPS)
        scene.render.filepath = path.replace(".mp4", "_still.png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", scene.render.filepath)
    else:
        video_output(path)
        bpy.ops.render.render(animation=True)
        print("RENDERED", path)
