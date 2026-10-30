"""Shared helpers for HexGen's prototype art scripts (run inside Blender).

Units: 1 Blender unit = 1 glTF metre. Z is up; pivots sit at the centre, at ground level (z = 0).
Rules and numbers: design/06 Multiplayer & tech.md -> Engine prototype.
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

# --- Sizes -----------------------------------------------------------------

CELL_FLATS = 1.0                                  # combat cell, across its flats (flat-top)
CELL_RADIUS = CELL_FLATS / math.sqrt(3)           # centre to corner
TILE_RADIUS = 4.5                                 # map tile, centre to corner (pointy-top): 9.0 tall
TILE_APOTHEM = TILE_RADIUS * math.sqrt(3) / 2     # centre to edge: about 3.9, so about 7.8 wide
INNER = 0.45                                      # centre piece reaches this share of the apothem
SOIL_TOP, SOIL_BOTTOM = -0.15, -0.6               # tile sides: light band, then dark band

# --- Palette (placeholders: exploration v8b and combat v14 mockup colours) --

PALETTE = {
    "plains": "#A8CF7E",
    "forest": "#5E8F5A",
    "farmland": "#DCC562",
    "river": "#86BEDB",
    "village": "#E6C590",
    "soil_light": "#8A6446",
    "soil_dark": "#6B4C35",
    # props
    "grass_ink": "#4F7A33",
    "leaf": "#4E8049",
    "leaf_dark": "#3B6A3A",
    "trunk": "#7A5236",
    "field_a": "#DCC562",
    "field_b": "#C9A94A",
    "field_c": "#9DBF5E",
    "hedge": "#4F7A33",
    "water": "#86BEDB",
    "bank": "#C9B58A",
    "wall": "#EFE2C6",
    "roof": "#B5523B",
    "road": "#CDB58A",
    "fence": "#8A6446",
    "rock": "#A9A39A",
    "flower": "#F2D46B",
    "slot": "#F6EFE4",
    "backdrop": "#CFE4F2",
    # combat cells
    "cell_grass_a": "#8DBB7A",
    "cell_grass_b": "#96C283",
    "cell_grass_c": "#88B575",
}

TERRAINS = ["plains", "forest", "farmland", "river", "village"]


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material(name):
    """One flat-colour material per palette entry, made once."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    hexcol = PALETTE[name].lstrip("#")
    rgb = [srgb_to_linear(int(hexcol[i:i + 2], 16) / 255) for i in (0, 2, 4)]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    mat.diffuse_color = (*rgb, 1.0)
    return mat


# --- Hex maths -------------------------------------------------------------

def hex_corners(radius, pointy, z=0.0):
    start = 90 if pointy else 0
    return [Vector((radius * math.cos(math.radians(start - 60 * i)),
                    radius * math.sin(math.radians(start - 60 * i)), z)) for i in range(6)]


def edge_normal(i):
    """Unit vector out of a pointy-top tile's edge i. Edge 0 faces +X; i counts anticlockwise in 60 degree steps."""
    a = math.radians(60 * i)
    return Vector((math.cos(a), math.sin(a), 0))


# Axial neighbour offsets for pointy-top tiles, matching edge_normal(i).
NEIGHBOURS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


def tile_position(q, r):
    """World position of a pointy-top tile at axial (q, r); r grows southward (-Y)."""
    return Vector((2 * TILE_APOTHEM * (q + r / 2), -1.5 * TILE_RADIUS * r, 0))


def cell_position(q, r):
    """World position of a flat-top combat cell at axial (q, r)."""
    return Vector((1.5 * CELL_RADIUS * q, -CELL_FLATS * (r + q / 2), 0))


def in_centre(p, margin=0.0):
    """Inside the centre piece: the inner hexagon whose edges face the tile's edges."""
    return all(p.dot(edge_normal(i)) <= INNER * TILE_APOTHEM - margin for i in range(6))


def in_edge_wedge(p, x0=None, x1=None, margin=0.0):
    """Inside edge 0's wedge (facing +X), between depths x0 and x1 along the edge normal."""
    x0 = INNER * TILE_APOTHEM if x0 is None else x0
    x1 = TILE_APOTHEM if x1 is None else x1
    return (x0 + margin <= p.x <= x1 - margin
            and abs(p.y) <= p.x * math.tan(math.radians(30)) - margin / math.cos(math.radians(30)))


def scatter(rng, inside, count, min_dist, bounds, tries=400):
    """Up to `count` points that pass `inside` and stay `min_dist` apart."""
    pts = []
    (x0, x1), (y0, y1) = bounds
    for _ in range(tries):
        if len(pts) >= count:
            break
        p = Vector((rng.uniform(x0, x1), rng.uniform(y0, y1), 0))
        if inside(p) and all((p - q).length >= min_dist for q in pts):
            pts.append(p)
    return pts


WEDGE_BOUNDS = ((INNER * TILE_APOTHEM, TILE_APOTHEM), (-TILE_RADIUS / 2, TILE_RADIUS / 2))
CENTRE_BOUNDS = ((-INNER * TILE_APOTHEM, INNER * TILE_APOTHEM), (-INNER * TILE_RADIUS, INNER * TILE_RADIUS))


# --- Geometry builder ------------------------------------------------------

class Piece:
    """Builds one low-poly object out of flat-coloured parts."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []

    def _slot(self, mat_name):
        if mat_name not in self.mats:
            self.mats.append(mat_name)
        return self.mats.index(mat_name)

    def _paint(self, verts, mat_name):
        idx = self._slot(mat_name)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = idx

    def prism(self, outline, z0, z1, mat_name, side_mat=None):
        """Extrude a convex outline (list of XY points, anticlockwise) from z0 up to z1."""
        bm = self.bm
        bottom = [bm.verts.new((p.x, p.y, z0)) for p in outline]
        top = [bm.verts.new((p.x, p.y, z1)) for p in outline]
        top_face = bm.faces.new(top)
        top_face.material_index = self._slot(mat_name)
        bm.faces.new(list(reversed(bottom))).material_index = self._slot(side_mat or mat_name)
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((bottom[i], bottom[j], top[j], top[i])).material_index = self._slot(side_mat or mat_name)
        return top_face

    def flat(self, outline, z, mat_name):
        """A thin plate lying on the ground (field strips, water, roads)."""
        return self.prism(outline, 0.0, z, mat_name)

    def cone(self, at, radius, height, mat_name, segments=6, z=0.0, spin=0.0):
        m = Matrix.Translation(at + Vector((0, 0, z + height / 2))) @ Matrix.Rotation(spin, 4, "Z")
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=True, segments=segments,
                                  radius1=radius, radius2=0.0, depth=height, matrix=m)
        self._paint(r["verts"], mat_name)

    def cylinder(self, at, radius, height, mat_name, segments=6, z=0.0):
        m = Matrix.Translation(at + Vector((0, 0, z + height / 2)))
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segments,
                                  radius1=radius, radius2=radius, depth=height, matrix=m)
        self._paint(r["verts"], mat_name)

    def blob(self, at, radius, mat_name, z=0.0, squash=1.0):
        m = Matrix.Translation(at + Vector((0, 0, z))) @ Matrix.Diagonal((1, 1, squash, 1))
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=1, radius=radius, matrix=m)
        self._paint(r["verts"], mat_name)

    def box(self, at, size, mat_name, z=0.0, spin=0.0):
        m = (Matrix.Translation(at + Vector((0, 0, z + size[2] / 2))) @ Matrix.Rotation(spin, 4, "Z")
             @ Matrix.Diagonal((*size, 1)))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._paint(r["verts"], mat_name)

    def gable_roof(self, at, w, d, h, mat_name, z, spin=0.0):
        """A triangular prism roof, ridge along the house's length (w)."""
        rot = Matrix.Rotation(spin, 4, "Z")
        pts = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0),
               (-w / 2, 0, h), (w / 2, 0, h)]
        v = [self.bm.verts.new(at + Vector((0, 0, z)) + rot @ Vector(p)) for p in pts]
        idx = self._slot(mat_name)
        for f in ((v[0], v[3], v[2], v[1]), (v[0], v[1], v[5], v[4]), (v[2], v[3], v[4], v[5]),
                  (v[0], v[4], v[3]), (v[1], v[2], v[5])):
            self.bm.faces.new(f).material_index = idx

    def finish(self, collection, location=(0, 0, 0)):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        for m in self.mats:
            mesh.materials.append(material(m))
        for poly in mesh.polygons:
            poly.use_smooth = False
        obj = bpy.data.objects.new(self.name, mesh)
        obj.location = location
        collection.objects.link(obj)
        return obj


# --- Files -----------------------------------------------------------------

ART = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def empty_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def next_version(folder, stem):
    """Path for the next unused version, e.g. tiles_v3.blend. Never overwrites an earlier file."""
    os.makedirs(folder, exist_ok=True)
    n = 1
    while os.path.exists(os.path.join(folder, f"{stem}_v{n}.blend")):
        n += 1
    return os.path.join(folder, f"{stem}_v{n}.blend")


def new_collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def seeded(name):
    return random.Random(name)
