"""Stills and a short movie of a hills map's lava with the engine's scroll faked: a glow moves through the flow's own surface by its UVs (V is metres along the flow), with nothing floating on top.
A look target for the engine: the shipped material is flat colour.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_lava_movie.py -- volcanic_peaks_fissures
Add --stills for one frame from each shot. Writes art/preview/lava_movie_<map>_vN.mp4 and lava_shot_<map>_<shot>_vN.png (never overwrites).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import render_hills_maps as rh  # noqa: E402
import render_preview as rp  # noqa: E402

FPS, SHOT_SECONDS = 24, 3
SPEED = 0.45  # metres a second along the flow


def next_movie(name):
    """rp.next_n counts stills only, so a movie's next number is counted here, or it would overwrite the last."""
    n = 1
    while os.path.exists(os.path.join(hk.ART, "preview", f"lava_movie_{name}_v{n}.mp4")):
        n += 1
    return n


def look(cam, frm, to):
    cam.location = frm
    cam.rotation_euler = (to - frm).to_track_quat("-Z", "Y").to_euler()


def glow():
    """What the engine's shader would do: noise stretched across the flow, scrolled down it by V, between deep and hot orange."""
    mat = bpy.data.materials["lava_flow"]
    tree = mat.node_tree
    nodes, links = tree.nodes, tree.links
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    split = nodes.new("ShaderNodeSeparateXYZ")
    time = nodes.new("ShaderNodeValue")
    minus = nodes.new("ShaderNodeMath")
    minus.operation = "SUBTRACT"
    join = nodes.new("ShaderNodeCombineXYZ")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.2
    noise.inputs["Detail"].default_value = 1.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.34, 0.68
    ramp.color_ramp.elements[0].color = (*hk.linear("lava"), 1.0)
    ramp.color_ramp.elements[0].color = (0.62, 0.11, 0.015, 1.0)
    ramp.color_ramp.elements[1].color = (1.0, 0.62, 0.12, 1.0)
    emit = nodes.new("ShaderNodeEmission")
    output = nodes.get("Material Output")
    links.new(uv.outputs["UV"], split.inputs[0])
    links.new(split.outputs["Y"], minus.inputs[0])
    links.new(time.outputs[0], minus.inputs[1])
    links.new(split.outputs["X"], join.inputs["X"])
    links.new(minus.outputs[0], join.inputs["Y"])
    links.new(join.outputs[0], noise.inputs["Vector"])
    links.new(noise.outputs[0], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], emit.inputs["Color"])
    # Mostly glow, with some of the light left on it so its shape still shows.
    lit = nodes.new("ShaderNodeBsdfDiffuse")
    mix = nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.45
    links.new(ramp.outputs["Color"], lit.inputs["Color"])
    links.new(emit.outputs[0], mix.inputs[1])
    links.new(lit.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    return time


def shots(name, cells):
    z = rh.HEIGHTS[name]
    path = rh.flow_cells(rh.MAPS[name])
    start = hk.cell_position(*path[0]) + Vector((0, 0, z[path[0]]))
    end = hk.cell_position(*path[-1]) + Vector((0, 0, z[path[-1]]))
    crater = rh.FLOW_LINES[name][0]
    side = (start + crater) / 2
    target, distance = rh.fm.framing(cells)
    middle = target + Vector((0, 0, (min(z.values()) + max(z.values())) / 2))
    distance += 1.0
    away = (start - crater).to_2d().to_3d().normalized()
    el = math.radians(rh.fm.PITCH)
    return {
        "cone": (side + away * 7.0 + Vector((0, -4.5, 5.0)), side),
        "edge": (end + Vector((-1.0, -5.0, 2.2)), end + Vector((0.4, 0, -0.25))),
        "front": (middle + Vector((0, -math.cos(el), math.sin(el))) * distance, middle),
        "turned": (middle + Vector((0, math.cos(el), math.sin(el))) * distance, middle),
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    name = next(a for a in args if not a.startswith("--"))
    hk.empty_scene()
    col = hk.new_collection("map")
    t = rh.templates()
    cells = rh.build_map(t, col, name)
    rh.checks_on_heights(name)
    rh.fm.visibility(name, cells)
    print(f"TRIS {name}: map {rh.fm.triangles(col)}")
    for ob in col.objects:
        if "lava_flow" in ob.name or "peaks" in ob.name:
            print("PIECE", ob.name, sum(len(f.vertices) - 2 for f in ob.data.polygons))
    rh.place_minis(t, col, name, cells)
    target, distance = rh.fm.framing(cells)
    rp.stage(target, distance + 1.0, rh.fm.PITCH)
    scene = bpy.context.scene
    cam = scene.camera
    views = shots(name, cells)
    time = glow().outputs[0]
    if "--stills" in args:
        time.default_value = 0.4
        for shot, (frm, to) in views.items():
            look(cam, frm, to)
            rp.render(f"lava_shot_{name}_{shot}")
        return
    order = [views[k] for k in ("cone", "edge")]

    def step(s, *_):
        f = s.frame_current
        look(cam, *order[min((f - 1) // (FPS * SHOT_SECONDS), len(order) - 1)])
        time.default_value = SPEED * f / FPS

    bpy.app.handlers.frame_change_pre.append(step)
    scene.frame_start, scene.frame_end = 1, FPS * SHOT_SECONDS * len(order)
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = 800, 500
    try:
        scene.render.image_settings.media_type = "VIDEO"
    except (AttributeError, TypeError):
        pass
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = os.path.join(hk.ART, "preview", f"lava_movie_{name}_v{next_movie(name)}.mp4")
    bpy.ops.render.render(animation=True)
    print("MOVIE", scene.render.filepath)


main()
