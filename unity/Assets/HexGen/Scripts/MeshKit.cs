using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace HexGen
{
    /// Builds flat-shaded, vertex-coloured low-poly meshes, like hexkit.Piece.
    /// Takes Blender coordinates (z up, faces anticlockwise seen from outside) and converts on ToMesh().
    public class MeshKit
    {
        readonly List<Vector3> verts = new();
        readonly List<Color> colours = new();
        readonly List<int> tris = new();

        public int VertexCount => verts.Count;

        /// One convex or fan-able face, anticlockwise seen from outside.
        public void Face(IList<Vector3> poly, Color c)
        {
            int start = verts.Count;
            Color lin = c.linear;
            foreach (var p in poly)
            {
                verts.Add(Hex.ToUnity(p));
                colours.Add(lin);
            }
            // Faces still look anticlockwise on screen after the mapping, and Unity's front faces are
            // clockwise, so reverse the order (glTFast does the same for the imported tiles).
            for (int i = 1; i < poly.Count - 1; i++)
            {
                tris.Add(start);
                tris.Add(start + i + 1);
                tris.Add(start + i);
            }
        }

        /// Triangles that already have their own vertices (e.g. an ear-clipped outline), anticlockwise.
        public void Triangles(IList<Vector3> pts, IList<int> idx, Color c)
        {
            int start = verts.Count;
            Color lin = c.linear;
            foreach (var p in pts)
            {
                verts.Add(Hex.ToUnity(p));
                colours.Add(lin);
            }
            for (int i = 0; i + 2 < idx.Count; i += 3)
            {
                tris.Add(start + idx[i]);
                tris.Add(start + idx[i + 2]);
                tris.Add(start + idx[i + 1]);
            }
        }

        public void Prism(IList<Vector2> outline, float z0, float z1, Color top, Color? side = null)
        {
            Color s = side ?? top;
            int n = outline.Count;
            var t = new Vector3[n];
            var b = new Vector3[n];
            for (int i = 0; i < n; i++)
            {
                t[i] = new Vector3(outline[i].x, outline[i].y, z1);
                b[n - 1 - i] = new Vector3(outline[i].x, outline[i].y, z0);
            }
            Face(t, top);
            Face(b, s);
            for (int i = 0; i < n; i++)
            {
                int j = (i + 1) % n;
                Face(new[]
                {
                    new Vector3(outline[i].x, outline[i].y, z0), new Vector3(outline[j].x, outline[j].y, z0),
                    new Vector3(outline[j].x, outline[j].y, z1), new Vector3(outline[i].x, outline[i].y, z1)
                }, s);
            }
        }

        static Vector3 Rot(Vector3 v, float spin)
        {
            float c = Mathf.Cos(spin), s = Mathf.Sin(spin);
            return new Vector3(c * v.x - s * v.y, s * v.x + c * v.y, v.z);
        }

        public void Cone(Vector3 at, float radius, float height, Color c, int segments = 6, float z = 0, float spin = 0)
        {
            var ring = new Vector3[segments];
            for (int i = 0; i < segments; i++)
            {
                float a = 2 * Mathf.PI * i / segments;
                ring[i] = at + Rot(new Vector3(radius * Mathf.Cos(a), radius * Mathf.Sin(a), 0), spin) + new Vector3(0, 0, z);
            }
            var apex = at + new Vector3(0, 0, z + height);
            for (int i = 0; i < segments; i++)
                Face(new[] { ring[i], ring[(i + 1) % segments], apex }, c);
            var cap = new Vector3[segments];
            for (int i = 0; i < segments; i++) cap[i] = ring[segments - 1 - i];
            Face(cap, c);
        }

        public void Cylinder(Vector3 at, float radius, float height, Color c, int segments = 6, float z = 0)
        {
            var ring = new Vector2[segments];
            for (int i = 0; i < segments; i++)
            {
                float a = 2 * Mathf.PI * i / segments;
                ring[i] = new Vector2(at.x + radius * Mathf.Cos(a), at.y + radius * Mathf.Sin(a));
            }
            Prism(ring, at.z + z, at.z + z + height, c);
        }

        public void Box(Vector3 at, Vector3 size, Color c, float z = 0, float spin = 0)
        {
            var o = new Vector2[4];
            Vector2[] corners = { new(-0.5f, -0.5f), new(0.5f, -0.5f), new(0.5f, 0.5f), new(-0.5f, 0.5f) };
            for (int i = 0; i < 4; i++)
            {
                var v = Rot(new Vector3(corners[i].x * size.x, corners[i].y * size.y, 0), spin);
                o[i] = new Vector2(at.x + v.x, at.y + v.y);
            }
            Prism(o, at.z + z, at.z + z + size.z, c);
        }

        static readonly Vector3[] IcoV;
        static readonly int[] IcoF =
        {
            0, 11, 5, 0, 5, 1, 0, 1, 7, 0, 7, 10, 0, 10, 11, 1, 5, 9, 5, 11, 4, 11, 10, 2, 10, 7, 6, 7, 1, 8,
            3, 9, 4, 3, 4, 2, 3, 2, 6, 3, 6, 8, 3, 8, 9, 4, 9, 5, 2, 4, 11, 6, 2, 10, 8, 6, 7, 9, 8, 1
        };

        static MeshKit()
        {
            float t = (1f + Mathf.Sqrt(5f)) / 2f;
            IcoV = new[]
            {
                new Vector3(-1, t, 0), new Vector3(1, t, 0), new Vector3(-1, -t, 0), new Vector3(1, -t, 0),
                new Vector3(0, -1, t), new Vector3(0, 1, t), new Vector3(0, -1, -t), new Vector3(0, 1, -t),
                new Vector3(t, 0, -1), new Vector3(t, 0, 1), new Vector3(-t, 0, -1), new Vector3(-t, 0, 1)
            };
            for (int i = 0; i < IcoV.Length; i++) IcoV[i] = IcoV[i].normalized;
        }

        /// A squashed icosahedron (bmesh create_icosphere, subdivisions=1).
        public void Blob(Vector3 at, float radius, Color c, float z = 0, float squash = 1)
        {
            for (int f = 0; f < IcoF.Length; f += 3)
            {
                var tri = new Vector3[3];
                for (int k = 0; k < 3; k++)
                {
                    var v = IcoV[IcoF[f + k]] * radius;
                    v.z *= squash;
                    tri[k] = at + new Vector3(0, 0, z) + v;
                }
                // The table above is anticlockwise in a right-handed frame, so it already faces outward.
                Face(tri, c);
            }
        }

        public Mesh ToMesh(string name)
        {
            var m = new Mesh { name = name, indexFormat = IndexFormat.UInt32 };
            m.SetVertices(verts);
            m.SetColors(colours);
            m.SetTriangles(tris, 0);
            m.RecalculateNormals();
            m.RecalculateBounds();
            return m;
        }
    }
}
