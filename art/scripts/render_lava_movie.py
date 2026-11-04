"""A short movie of a hills map's lava flowing: bright flecks and dark crust drift down the flow's centre line, from the crater down the cone's side,
from cell to cell in flow_to's direction and over the map's edge. A look target for the engine; the crust on the shipped pieces stands still.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_lava_movie.py -- volcanic_peaks_fissures
Add --stills for one frame from each shot. Writes art/preview/lava_movie_<map>_vN.mp4 and lava_shot_<map>_<shot>_vN.png (never overwrites).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import render_hills_maps as rh  # noqa: E402
import render_preview as rp  # noqa: E402

FPS, SHOT_SECONDS = 24, 3
SPEED = 0.45  # along the flow, a second
GAP = 0.2     # between flecks along the line


def along(line):
    lengths = [(b - a).length for a, b in zip(line, line[1:])]
    total = sum(lengths)

    def at(d):
        d %= total
        for k, n in enumerate(lengths):
            if d <= n:
                return line[k].lerp(line[k + 1], d / (n or 1)), (line[k + 1] - line[k]).normalized()
            d -= n
        return line[-1], (line[-1] - line[-2]).normalized()
    return at, total


def fleck(col, name, mat):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(hk.material(mat))
    ob = bpy.data.objects.new(name, mesh)
    col.objects.link(ob)
    return ob


def look(cam, frm, to):
    cam.location = frm
    cam.rotation_euler = (to - frm).to_track_quat("-Z", "Y").to_euler()


def shots(name, cells):
    z = rh.HEIGHTS[name]
    path = rh.flow_cells(rh.MAPS[name])
    start = hk.cell_position(*path[0]) + Vector((0, 0, z[path[0]]))
    end = hk.cell_position(*path[-1]) + Vector((0, 0, z[path[-1]]))
    line = rh.FLOW_LINES[name]
    crater = line[0]
    side = (start + crater) / 2
    middle = rh.fm.framing(cells)[0] + Vector((0, 0, (min(z.values()) + max(z.values())) / 2))
    distance = rh.fm.framing(cells)[1] + 1.0
    away = (start - crater).to_2d().to_3d().normalized()
    return {
        "cone": (side + away * 7.0 + Vector((0, -4.5, 5.0)), side),
        "edge": (end + Vector((-1.0, -5.0, 2.2)), end + Vector((0.4, 0, -0.25))),
        "map": (middle + Vector((0, -math.cos(math.radians(rh.fm.PITCH)), math.sin(math.radians(rh.fm.PITCH)))) * distance, middle),
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    name = next(a for a in args if not a.startswith("--"))
    hk.empty_scene()
    col = hk.new_collection("map")
    t = rh.templates()
    cells = rh.build_map(t, col, name)
    rh.place_minis(t, col, name, cells)
    target, distance = rh.fm.framing(cells)
    rp.stage(target, distance + 1.0, rh.fm.PITCH)
    scene = bpy.context.scene
    cam = scene.camera
    views = shots(name, cells)
    if "--stills" in args:
        for shot, (frm, to) in views.items():
            look(cam, frm, to)
            rp.render(f"lava_shot_{name}_{shot}")
        return
    at, total = along(rh.FLOW_LINES[name])
    moving = []
    hk.PALETTE.setdefault("lava_hot", "#FFC94A")
    for k in range(int(total / GAP)):
        dark = k % 3 == 0
        ob = fleck(col, f"fleck_{k}", "basalt_dark" if dark else "lava_hot")
        r = (0.075 if dark else 0.04) * (0.8 + 0.5 * ((k * 7) % 5) / 5)
        ob.scale = (r, r, r * 0.4)
        moving.append((ob, k * GAP, ((k * 13) % 9 / 8 - 0.5) * 0.3))
    frames = FPS * SHOT_SECONDS * len(views)
    order = list(views.values())

    def step(s, *_):
        f = s.frame_current
        frm, to = order[min((f - 1) // (FPS * SHOT_SECONDS), len(order) - 1)]
        look(cam, frm, to)
        for ob, d0, off in moving:
            q, d = at(d0 + SPEED * f / FPS)
            across = Vector((-d.y, d.x, 0))
            # Near the middle where it runs steeply down the cone's side or the board's, as the stream is thin there.
            across = across.normalized() * off * (0.2 if abs(d.z) > 0.25 else 1.0) if across.length > 0.05 else Vector((off * 0.3, 0, 0))
            ob.location = q + across + Vector((0, 0, 0.03))

    bpy.app.handlers.frame_change_pre.append(step)
    scene.frame_start, scene.frame_end = 1, frames
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = 960, 600
    try:
        scene.render.image_settings.media_type = "VIDEO"
    except (AttributeError, TypeError):
        pass
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = os.path.join(hk.ART, "preview", f"lava_movie_{name}_v{rp.next_n(f'lava_movie_{name}')}.mp4")
    bpy.ops.render.render(animation=True)
    print("MOVIE", scene.render.filepath)


main()
