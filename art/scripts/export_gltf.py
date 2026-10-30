"""Exports a kit .blend to art/export/<kit>.glb for Godot and Unity.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b art/tiles/tiles_vN.blend --python art/scripts/export_gltf.py
Each object becomes one named node at the origin; the engines instance pieces by name.
The version is dropped from the file name (tiles_v3.blend -> tiles.glb), so the engines always load the latest export.
"""
import os
import re

import bpy

ART = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
stem = re.sub(r"_v\d+$", "", os.path.splitext(os.path.basename(bpy.data.filepath))[0])
out = os.path.join(ART, "export", f"{stem}.glb")
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out,
    export_format="GLB",
    use_selection=False,
    export_apply=True,       # apply modifiers Ethan adds while refining
    export_yup=True,         # both engines are Y-up
    export_materials="EXPORT",
    export_cameras=False,
    export_lights=False,
)
print("EXPORTED", out)
