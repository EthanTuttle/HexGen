using System;
using System.Collections.Generic;
using UnityEngine;
using static HexGen.WaterShapes;

namespace HexGen
{
    /// Builds the drawn water for all river tiles: flat water plates, banks, dressing, bobbing boats,
    /// and a world-space data texture with the two values the water shader needs
    /// (render_animation.water_mesh: depth = distance to the nearest shore, flow = direction and speed).
    /// The reference stores those per vertex of a dense mesh; here they live in a texture so the
    /// shader can read them per pixel and the plates can stay simple.
    public static class WaterBuilder
    {
        const double RiverSpeed = 0.6, LakeSpeed = 0.15;
        const float TexelSize = 0.05f;   // metres per data texel

        public class WaterTile
        {
            public Vector2Int Tile;
            public Vector2 At;           // tile centre, Blender coords
            public bool[] Mask;
            public TileWater Shape;
        }

        public class Result
        {
            public MeshKit Plates = new(), Dressing = new();
            public List<(Vector3 at, double angle, int index)> Boats = new();   // Blender coords
            public Texture2D Data;
            public Vector4 DataRect;     // Unity world: min x, min z, size x, size z
        }

        public static Result Build(List<WaterTile> tiles)
        {
            var res = new Result();
            Color water = Hex.Palette("water"), bank = Hex.Palette("bank"), reed = Hex.Palette("reed"),
                rock = Hex.Palette("rock"), lily = Hex.Palette("lily"), trunk = Hex.Palette("trunk");
            var shores = new List<(List<Vector2> pts, int sign, double speed)>();
            int boatIndex = 0;

            foreach (var t in tiles)
            {
                string seed = $"{t.Tile.x},{t.Tile.y}";
                var w = t.Shape;
                Vector3 V(P p, float z = 0) => new(t.At.x + (float)p.x, t.At.y + (float)p.y, z);

                // Plates (top only, at the plate's top height 0.03).
                foreach (var poly in w.Outlines)
                {
                    var pts = new List<Vector2>();
                    foreach (var p in poly) pts.Add(p.V);
                    var idx = Triangulate(pts);
                    var v3 = new List<Vector3>();
                    foreach (var p in pts) v3.Add(new Vector3(t.At.x + p.x, t.At.y + p.y, 0.03f));
                    res.Plates.Triangles(v3, idx, water);
                }

                // Banks: quads along each shore on its land side, 0.025 high.
                foreach (var curve in w.Shores)
                    foreach (var quad in BankStrip(curve, 0.22))
                        res.Dressing.Face(new[] { V(quad[0], 0.025f), V(quad[1], 0.025f), V(quad[2], 0.025f), V(quad[3], 0.025f) }, bank);

                // Dressing (water.add_water), same random draws as the reference.
                var d = Dress(w, seed);
                var rng = new PyRandom(seed + "-props");
                foreach (var p in d.Reeds)
                    for (int k = 0; k < 3; k++)
                    {
                        double jx = p.x + rng.Uniform(-0.12, 0.12), jy = p.y + rng.Uniform(-0.12, 0.12);
                        res.Dressing.Cone(V(new P(jx, jy)), 0.05f, (float)rng.Uniform(0.35, 0.6), reed, 4);
                    }
                foreach (var p in d.Rocks)
                    res.Dressing.Blob(V(p), (float)rng.Uniform(0.12, 0.2), rock, 0, 0.6f);
                foreach (var p in d.Lilies)
                    res.Dressing.Cylinder(V(p), (float)rng.Uniform(0.14, 0.22), 0.02f, lily, 7, 0.03f);
                foreach (var (p, ang) in d.Jetties)
                {
                    P dir = new(Math.Cos(ang), Math.Sin(ang));
                    P tip = p + dir * 0.7;
                    res.Dressing.Box(V(tip), new Vector3(1.6f, 0.45f, 0.06f), trunk, 0.12f, (float)ang);
                    foreach (int s in new[] { -1, 1 })
                        res.Dressing.Cylinder(V(tip + dir * (0.6 * s)), 0.05f, 0.2f, trunk);
                }
                foreach (var (p, ang) in d.Boats)
                    res.Boats.Add((V(p), ang, boatIndex++));

                // Flow along each shore (render_animation.water_mesh).
                double h = Downhill(t.Tile.x, t.Tile.y);
                var inflow = new bool[6];
                for (int i = 0; i < 6; i++)
                {
                    var n = t.Tile + Hex.Neighbours[i];
                    inflow[i] = Downhill(n.x, n.y) < h;
                }
                double speed = w.Kind == "river" || w.Kind == "spring" ? RiverSpeed : LakeSpeed;
                var signs = FlowSigns(w.Ends, inflow);
                for (int k = 0; k < w.Shores.Count; k++)
                {
                    var pts = new List<Vector2>();
                    foreach (var p in w.Shores[k]) pts.Add(t.At + p.V);
                    shores.Add((pts, signs[k], speed));
                }
            }

            BakeData(tiles, shores, res);
            return res;
        }

        /// A boat (water.add_boat) built at the origin, spun by its angle; the caller bobs it.
        public static Mesh BoatMesh(double angle)
        {
            var kit = new MeshKit();
            kit.Box(Vector3.zero, new Vector3(0.9f, 0.36f, 0.14f), Hex.Palette("trunk"), 0.03f, (float)angle);
            kit.Box(Vector3.zero, new Vector3(0.5f, 0.26f, 0.06f), Hex.Palette("boat"), 0.17f, (float)angle);
            return kit.ToMesh("boat");
        }

        static void BakeData(List<WaterTile> tiles, List<(List<Vector2> pts, int sign, double speed)> shores, Result res)
        {
            // Bounds of all water tiles, Blender coords.
            float minX = float.MaxValue, minY = float.MaxValue, maxX = float.MinValue, maxY = float.MinValue;
            foreach (var t in tiles)
            {
                minX = Mathf.Min(minX, t.At.x - Hex.TileApothem); maxX = Mathf.Max(maxX, t.At.x + Hex.TileApothem);
                minY = Mathf.Min(minY, t.At.y - Hex.TileRadius); maxY = Mathf.Max(maxY, t.At.y + Hex.TileRadius);
            }
            int w = Mathf.CeilToInt((maxX - minX) / TexelSize), h = Mathf.CeilToInt((maxY - minY) / TexelSize);
            var px = new Color[w * h];

            // Segments with their flow vector, for the nearest-shore search.
            var segA = new List<Vector2>();
            var segB = new List<Vector2>();
            var segFlow = new List<Vector2>();
            var segRiver = new List<bool>();
            foreach (var (pts, sign, speed) in shores)
                for (int k = 1; k < pts.Count; k++)
                {
                    segA.Add(pts[k - 1]);
                    segB.Add(pts[k]);
                    var tan = (pts[k] - pts[k - 1]).normalized;
                    segFlow.Add(tan * (float)(sign * speed));
                    segRiver.Add(speed == RiverSpeed);
                }

            var centres = new List<Vector2>();
            foreach (var t in tiles) centres.Add(t.At);
            for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
            {
                var p = new Vector2(minX + (x + 0.5f) * TexelSize, minY + (y + 0.5f) * TexelSize);
                // Only texels on a water tile (a little margin so filtering at the edges is right).
                bool near = false;
                foreach (var c in centres)
                    if ((p - c).sqrMagnitude < (Hex.TileRadius + 0.2f) * (Hex.TileRadius + 0.2f)) { near = true; break; }
                if (!near) { px[y * w + x] = new Color(10, 0, 0, 0); continue; }
                float best = float.MaxValue;
                int bi = -1;
                for (int s = 0; s < segA.Count; s++)
                {
                    var ab = segB[s] - segA[s];
                    float tt = Mathf.Clamp01(Vector2.Dot(p - segA[s], ab) / Mathf.Max(ab.sqrMagnitude, 1e-12f));
                    float d = (p - (segA[s] + ab * tt)).sqrMagnitude;
                    if (d < best) { best = d; bi = s; }
                }
                float dist = Mathf.Sqrt(best);
                Vector2 flow = Vector2.zero;
                if (bi >= 0)
                {
                    // Rivers flow across their whole width; lakes only drift near the shore.
                    float fade = segRiver[bi] ? 1f : Mathf.Max(0f, 1f - dist / 2.5f);
                    flow = segFlow[bi] * fade;
                }
                // Stored in Unity world axes: Blender (x, y) -> Unity (-x, -z).
                px[y * w + x] = new Color(Mathf.Min(dist, 10f), -flow.x, -flow.y, 0);
            }

            var tex = new Texture2D(w, h, TextureFormat.RGBAHalf, false, true)
            {
                name = "water_data", wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear
            };
            tex.SetPixels(px);
            tex.Apply(false, false);
            res.Data = tex;
            // Texel (x, y) sits at Blender (minX + x, minY + y), i.e. Unity (-(minX + x), -(minY + y)).
            // The shader maps Unity world back with uv = ((-wx) - minX, (-wz) - minY) / size.
            res.DataRect = new Vector4(minX, minY, maxX - minX, maxY - minY);
        }

        /// Ear clipping for a simple polygon (anticlockwise). Returns anticlockwise triangles.
        public static List<int> Triangulate(List<Vector2> pts)
        {
            var result = new List<int>();
            var idx = new List<int>();
            for (int i = 0; i < pts.Count; i++) idx.Add(i);
            // Drop duplicate neighbours, which break ear tests.
            for (int i = idx.Count - 1; i >= 0 && idx.Count > 3; i--)
                if ((pts[idx[i]] - pts[idx[(i + 1) % idx.Count]]).sqrMagnitude < 1e-10f) idx.RemoveAt(i);
            if (SignedArea(pts, idx) < 0) idx.Reverse();

            int guard = 0;
            while (idx.Count > 3 && guard++ < 10000)
            {
                bool clipped = false;
                for (int i = 0; i < idx.Count; i++)
                {
                    int a = idx[(i - 1 + idx.Count) % idx.Count], b = idx[i], c = idx[(i + 1) % idx.Count];
                    if (Cross(pts[a], pts[b], pts[c]) <= 1e-9f) continue;
                    bool inside = false;
                    foreach (int o in idx)
                    {
                        if (o == a || o == b || o == c) continue;
                        if (InTri(pts[o], pts[a], pts[b], pts[c])) { inside = true; break; }
                    }
                    if (inside) continue;
                    result.Add(a); result.Add(b); result.Add(c);
                    idx.RemoveAt(i);
                    clipped = true;
                    break;
                }
                if (!clipped)
                {
                    // Degenerate or slightly self-touching outline: clip the most convex corner anyway.
                    int bestI = 0;
                    float bestC = float.MinValue;
                    for (int i = 0; i < idx.Count; i++)
                    {
                        float cr = Cross(pts[idx[(i - 1 + idx.Count) % idx.Count]], pts[idx[i]], pts[idx[(i + 1) % idx.Count]]);
                        if (cr > bestC) { bestC = cr; bestI = i; }
                    }
                    result.Add(idx[(bestI - 1 + idx.Count) % idx.Count]); result.Add(idx[bestI]); result.Add(idx[(bestI + 1) % idx.Count]);
                    idx.RemoveAt(bestI);
                }
            }
            if (idx.Count == 3) { result.Add(idx[0]); result.Add(idx[1]); result.Add(idx[2]); }
            return result;
        }

        static float SignedArea(List<Vector2> pts, List<int> idx)
        {
            float a = 0;
            for (int i = 0; i < idx.Count; i++)
            {
                var p = pts[idx[i]];
                var q = pts[idx[(i + 1) % idx.Count]];
                a += p.x * q.y - q.x * p.y;
            }
            return a / 2;
        }

        static float Cross(Vector2 a, Vector2 b, Vector2 c) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);

        static bool InTri(Vector2 p, Vector2 a, Vector2 b, Vector2 c) =>
            Cross(a, b, p) >= 0 && Cross(b, c, p) >= 0 && Cross(c, a, p) >= 0;
    }
}
