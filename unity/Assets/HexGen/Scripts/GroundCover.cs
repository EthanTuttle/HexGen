using System;
using System.Collections.Generic;
using UnityEngine;
using static HexGen.WaterShapes;

namespace HexGen
{
    /// Port of art/scripts/ground_cover.py: one world-space scatter of tufts, flowers and pebbles whose
    /// density fades toward the neighbour's within BLEND metres of a tile edge.
    public static class GroundCover
    {
        public const double Cell = 0.55;
        public const double Blend = 1.6;

        // Share of cells that get a prop, per terrain (placeholders from ground_cover.py).
        static readonly Dictionary<string, double> Density = new()
        {
            ["plains"] = 0.5, ["river"] = 0.3, ["forest"] = 0.18, ["farmland"] = 0.0, ["village"] = 0.0,
        };

        public static double Hash01(long ix, long iy, long k)
        {
            uint h = unchecked((uint)(ix * 374761393L + iy * 668265263L + k * 1442695041L));
            h = unchecked((h ^ (h >> 13)) * 1274126177u);
            h ^= h >> 16;
            return h / 4294967296.0;
        }

        public static Vector2Int TileAt(double x, double y)
        {
            double r = -y / (1.5 * R);
            double q = x / (2 * A) - r / 2;
            double s = -q - r;
            double rq = Math.Round(q), rr = Math.Round(r), rs = Math.Round(s);   // banker's rounding, like Python
            double dq = Math.Abs(rq - q), dr = Math.Abs(rr - r), ds = Math.Abs(rs - s);
            if (dq > dr && dq > ds) rq = -rr - rs;
            else if (dr > ds) rr = -rq - rs;
            return new Vector2Int((int)rq, (int)rr);
        }

        public static P TileCentre(int q, int r) => new(2 * A * (q + r / 2.0), -1.5 * R * r);

        static double DensityAt(Dictionary<Vector2Int, string> terrains, double x, double y, out Vector2Int tile)
        {
            tile = TileAt(x, y);
            if (!terrains.TryGetValue(tile, out var own)) return 0.0;
            P c = TileCentre(tile.x, tile.y);
            P local = new(x - c.x, y - c.y);
            double dOwn = Density[own], dens = dOwn;
            for (int i = 0; i < 6; i++)
            {
                double toEdge = A - Dot(local, Normal(i));
                if (toEdge < Blend)
                {
                    var n = tile + Hex.Neighbours[i];
                    double dOther = terrains.TryGetValue(n, out var other) ? Density[other] : dOwn;
                    dens += 0.5 * (1 - toEdge / Blend) * (dOther - dOwn);
                }
            }
            return Math.Max(0.0, dens);
        }

        public struct Prop
        {
            public string Kind;
            public double X, Y;
            public long Ix, Iy;
        }

        public static List<Prop> Scatter(Dictionary<Vector2Int, string> terrains,
                                         Dictionary<Vector2Int, TileWater> waterShapes)
        {
            double minX = double.MaxValue, maxX = double.MinValue, minY = double.MaxValue, maxY = double.MinValue;
            foreach (var t in terrains.Keys)
            {
                P c = TileCentre(t.x, t.y);
                minX = Math.Min(minX, c.x); maxX = Math.Max(maxX, c.x);
                minY = Math.Min(minY, c.y); maxY = Math.Max(maxY, c.y);
            }
            var outp = new List<Prop>();
            for (long ix = (long)Math.Floor((minX - A) / Cell); ix < (long)Math.Ceiling((maxX + A) / Cell); ix++)
            for (long iy = (long)Math.Floor((minY - R) / Cell); iy < (long)Math.Ceiling((maxY + R) / Cell); iy++)
            {
                double x = (ix + Hash01(ix, iy, 0)) * Cell;
                double y = (iy + Hash01(ix, iy, 1)) * Cell;
                double dens = DensityAt(terrains, x, y, out var tile);
                if (Hash01(ix, iy, 3) >= dens) continue;
                if (waterShapes.TryGetValue(tile, out var w))
                {
                    P c = TileCentre(tile.x, tile.y);
                    P p = new(x - c.x, y - c.y);
                    bool skip = false;
                    foreach (var o in w.Outlines) if (PointIn(o, p)) { skip = true; break; }
                    if (!skip)
                        foreach (var curve in w.Shores)
                        {
                            foreach (var s in curve) if (Length(p - s) < 0.45) { skip = true; break; }
                            if (skip) break;
                        }
                    if (skip) continue;
                }
                double k = Hash01(ix, iy, 2);
                outp.Add(new Prop { Kind = k < 0.7 ? "tuft" : k < 0.93 ? "flower" : "pebble", X = x, Y = y, Ix = ix, Iy = iy });
            }
            return outp;
        }

        /// Builds the scatter into one mesh (add_ground_cover).
        public static void Build(MeshKit kit, Dictionary<Vector2Int, string> terrains,
                                 Dictionary<Vector2Int, TileWater> waterShapes)
        {
            Color ink = Hex.Palette("grass_ink"), flower = Hex.Palette("flower"), rock = Hex.Palette("rock");
            foreach (var p in Scatter(terrains, waterShapes))
            {
                var rng = new PyRandom(Hash01(p.Ix, p.Iy, 4));
                var at = new Vector3((float)p.X, (float)p.Y, 0);
                if (p.Kind == "tuft")
                {
                    float rad = (float)rng.Uniform(0.12, 0.2), h = (float)rng.Uniform(0.2, 0.35);
                    kit.Cone(at, rad, h, ink, 4, 0, (float)rng.Uniform(0, 1));
                }
                else if (p.Kind == "flower")
                    kit.Box(at, new Vector3(0.08f, 0.08f, 0.12f), flower, 0, (float)rng.Uniform(0, 1));
                else
                    kit.Blob(at, (float)rng.Uniform(0.07, 0.12), rock, 0, 0.6f);
            }
        }
    }
}
