using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace HexGen
{
    /// Line-by-line port of art/scripts/water.py (shapes, flow and dressing positions).
    /// Works in one tile's own Blender coordinates: pointy-top, centre at the origin, edge 0 facing +X.
    /// Maths is done in doubles, like Python, so the curves match the Blender previews.
    public static class WaterShapes
    {
        public const double R = 4.5;
        public static readonly double A = R * Math.Sqrt(3) / 2;
        public const double RiverWidth = 1.5;
        public const double LakeMargin = 0.25;
        public const double Meander = 0.9;
        public const double Wobble = 0.18;
        public const int Samples = 18;

        public struct P
        {
            public double x, y;
            public P(double x, double y) { this.x = x; this.y = y; }
            public static P operator +(P a, P b) => new(a.x + b.x, a.y + b.y);
            public static P operator -(P a, P b) => new(a.x - b.x, a.y - b.y);
            public static P operator *(P a, double s) => new(a.x * s, a.y * s);
            public Vector2 V => new((float)x, (float)y);
        }

        public static double Dot(P a, P b) => a.x * b.x + a.y * b.y;
        public static double Length(P a) => Math.Sqrt(a.x * a.x + a.y * a.y);   // math.hypot

        static double Rad(double deg) => deg * Math.PI / 180.0;
        public static P Normal(int i) => new(Math.Cos(Rad(60 * i)), Math.Sin(Rad(60 * i)));
        public static P Corner(int i) => new(R * Math.Cos(Rad(60 * i + 30)), R * Math.Sin(Rad(60 * i + 30)));

        public static P EdgePoint(int i, double t)
        {
            P s = Corner(i - 1), e = Corner(i);
            return s + (e - s) * t;
        }

        public static P ClampInside(P p, double inset = 0.01)
        {
            for (int i = 0; i < 6; i++)
            {
                double over = Dot(p, Normal(i)) - (A - inset);
                if (over > 0) p = p - Normal(i) * over;
            }
            return p;
        }

        static int Mod6(int i) => ((i % 6) + 6) % 6;

        // --- 1. Water along each edge ---------------------------------------------------------------

        public static (double, double)? EdgeInterval(bool[] water, int i)
        {
            if (!water[i]) return null;
            bool startTri = water[Mod6(i - 1)], endTri = water[Mod6(i + 1)];
            if (!(startTri || endTri))
            {
                double half = RiverWidth / R / 2;
                return (0.5 - half, 0.5 + half);
            }
            return (startTri ? 0.0 : LakeMargin, endTri ? 1.0 : 1.0 - LakeMargin);
        }

        public static bool IsLake(bool[] water)
        {
            for (int i = 0; i < 6; i++)
                if (water[i] && water[(i + 1) % 6]) return true;
            return false;
        }

        // --- 2. Shores --------------------------------------------------------------------------------

        static List<P> Bezier(P p0, P p1, P p2, P p3, int n = Samples)
        {
            var pts = new List<P>();
            for (int k = 0; k <= n; k++)
            {
                double t = (double)k / n, u = 1 - t;
                pts.Add(p0 * (u * u * u) + p1 * (3 * u * u * t) + (p2 * (3 * u * t * t) + p3 * (t * t * t)));
            }
            return pts;
        }

        static List<P> Shore(P p, int edgeP, P q, int edgeQ, P sway, PyRandom rng, double wobble)
        {
            double k = Math.Min(Math.Max(0.5 * Length(q - p), 0.6), 3.0);
            P c1 = p - Normal(edgeP) * k;
            P c2 = q - Normal(edgeQ) * k;
            var bez = Bezier(p, c1, c2, q);
            var pts = new List<P>();
            for (int j = 0; j < bez.Count; j++)
            {
                double s = Math.Sin(Math.PI * j / Samples);
                pts.Add(bez[j] + sway * (s * s));
            }
            if (wobble != 0)
            {
                double phase = rng.Uniform(0, 6.28), freq = rng.Uniform(2.5, 4.0);
                var outp = new List<P>();
                for (int kk = 0; kk < pts.Count; kk++)
                {
                    double t = (double)kk / (pts.Count - 1);
                    P nxt = pts[Math.Min(kk + 1, pts.Count - 1)], prv = pts[Math.Max(kk - 1, 0)];
                    P tan = nxt - prv;
                    double len = Length(tan);
                    P side = new P(-tan.y, tan.x) * (1 / (len != 0 ? len : 1));
                    outp.Add(pts[kk] + side * (wobble * Math.Sin(phase + freq * t * Math.PI) * Math.Sin(t * Math.PI)));
                }
                pts = outp;
            }
            return pts.Select(pt => ClampInside(pt)).ToList();
        }

        static List<P> Circle(P centre, double radius, PyRandom rng, double wobble, int n = 20)
        {
            double phase = rng.Uniform(0, 6.28);
            var pts = new List<P>();
            for (int k = 0; k < n; k++)
            {
                double a = 2 * Math.PI * k / n;
                pts.Add(centre + new P(Math.Cos(a), Math.Sin(a)) * (radius * (1 + wobble * Math.Sin(3 * a + phase))));
            }
            return pts;
        }

        public class TileWater
        {
            public List<List<P>> Outlines = new();
            public List<List<P>> Shores = new();
            public string Kind;
            public List<(int?, int?)> Ends = new();
        }

        class Run
        {
            public int StartEdge, EndEdge;
            public double StartT, EndT;
            public List<P> Pts;
        }

        public static TileWater Compute(bool[] water, string seed)
        {
            var rng = new PyRandom(seed);
            double swayAngle = rng.Uniform(0, 2 * Math.PI);
            P sway = new P(Math.Cos(swayAngle), Math.Sin(swayAngle)) * (rng.Uniform(0.4, 1.0) * Meander);
            var res = new TileWater();

            if (!water.Any(w => w))
            {
                var ring = Circle(new P(0, 0), 1.7, rng, 0.12);
                res.Outlines.Add(ring);
                res.Shores.Add(ring.Concat(ring.Take(1)).ToList());
                res.Kind = "pond";
                res.Ends.Add((null, null));
                return res;
            }

            var spans = new List<(int i, double t0, double t1)>();
            for (int i = 0; i < 6; i++)
            {
                var iv = EdgeInterval(water, i);
                if (iv.HasValue) spans.Add((i, iv.Value.Item1, iv.Value.Item2));
            }
            bool lake = IsLake(water);

            if (spans.Count == 1 && !lake)
            {
                var (i, t0, t1) = spans[0];
                P pondAt = Normal(i) * -0.6;
                P p = EdgePoint(i, t1), q = EdgePoint(i, t0);
                P n = Normal(i);
                var bankA = Shore(p, i, pondAt + new P(-n.y, n.x) * 0.7, i, sway, rng, 0);
                var bankB = Shore(pondAt + new P(n.y, -n.x) * 0.7, i, q, i, sway, rng, 0);
                var channel = new List<P> { EdgePoint(i, t0), EdgePoint(i, t1) };
                channel.AddRange(bankA.Skip(1));
                channel.AddRange(bankB.Take(bankB.Count - 1));
                var pond = Circle(pondAt + sway, 1.3, rng, 0.12);
                res.Outlines.Add(channel);
                res.Outlines.Add(pond);
                res.Shores.Add(bankA);
                res.Shores.Add(bankB);
                res.Shores.Add(pond.Concat(pond.Take(1)).ToList());
                res.Kind = "spring";
                res.Ends.Add((i, null));
                res.Ends.Add((null, i));
                res.Ends.Add((null, null));
                return res;
            }

            // Walk round the edge, merging stretches that meet at a water corner.
            var runs = new List<Run>();
            foreach (var (i, t0, t1) in spans)
            {
                var pts = new List<P> { EdgePoint(i, t0), EdgePoint(i, t1) };
                if (runs.Count > 0 && runs[^1].EndEdge == i - 1 && runs[^1].EndT == 1.0 && t0 == 0.0)
                {
                    runs[^1].Pts.AddRange(pts.Skip(1));
                    runs[^1].EndEdge = i;
                    runs[^1].EndT = t1;
                }
                else
                    runs.Add(new Run { StartEdge = i, StartT = t0, EndEdge = i, EndT = t1, Pts = pts });
            }
            if (runs.Count > 1 && runs[^1].EndEdge == 5 && runs[^1].EndT == 1.0
                && runs[0].StartEdge == 0 && runs[0].StartT == 0.0)
            {
                var last = runs[^1];
                runs.RemoveAt(runs.Count - 1);
                var merged = new List<P>(last.Pts);
                merged.AddRange(runs[0].Pts.Skip(1));
                runs[0].Pts = merged;
                runs[0].StartEdge = last.StartEdge;
                runs[0].StartT = last.StartT;
            }
            if (runs.Count == 1 && spans.Count == 6 && spans.All(s => s.t0 == 0.0 && s.t1 == 1.0))
            {
                res.Outlines.Add(Enumerable.Range(0, 6).Select(Corner).ToList());
                res.Kind = "lake";
                return res;
            }

            var outline = new List<P>();
            for (int k = 0; k < runs.Count; k++)
            {
                var run = runs[k];
                var nxt = runs[(k + 1) % runs.Count];
                outline.AddRange(run.Pts);
                var curve = Shore(run.Pts[^1], run.EndEdge, nxt.Pts[0], nxt.StartEdge,
                                  !lake ? sway : sway * 0.4, rng, lake ? Wobble : 0);
                outline.AddRange(curve.Skip(1).Take(curve.Count - 2));
                res.Shores.Add(curve);
                res.Ends.Add((run.EndEdge, nxt.StartEdge));
            }
            res.Outlines.Add(outline);
            res.Kind = lake ? "lake" : "river";
            return res;
        }

        // --- 3. Flow ------------------------------------------------------------------------------------

        public static double Downhill(int q, int r) => r - 0.3 * q;

        public static List<int> FlowSigns(List<(int?, int?)> ends, bool[] inflow)
        {
            var signs = new List<int>();
            foreach (var (a, b) in ends)
            {
                if (a == null && b == null) signs.Add(0);
                else if (b == null) signs.Add(inflow[a.Value] ? 1 : -1);
                else if (a == null) signs.Add(inflow[b.Value] ? -1 : 1);
                else if (inflow[a.Value] && !inflow[b.Value]) signs.Add(1);
                else if (inflow[b.Value] && !inflow[a.Value]) signs.Add(-1);
                else signs.Add(0);
            }
            return signs;
        }

        public static bool PointIn(List<P> poly, P p)
        {
            bool inside = false;
            int n = poly.Count;
            for (int k = 0; k < n; k++)
            {
                P a = poly[k], b = poly[(k - 1 + n) % n];
                if ((a.y > p.y) != (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x)
                    inside = !inside;
            }
            return inside;
        }

        public static List<P[]> BankStrip(List<P> curve, double d)
        {
            var outs = new List<P>();
            for (int k = 0; k < curve.Count; k++)
            {
                P tan = curve[Math.Min(k + 1, curve.Count - 1)] - curve[Math.Max(k - 1, 0)];
                double len = Length(tan);
                outs.Add(curve[k] + new P(tan.y, -tan.x) * (d / (len != 0 ? len : 1)));
            }
            var quads = new List<P[]>();
            for (int k = 0; k < curve.Count - 1; k++)
                quads.Add(new[] { curve[k], outs[k], outs[k + 1], curve[k + 1] });
            return quads;
        }

        // --- 4. Dressing ---------------------------------------------------------------------------------

        public class Dressing
        {
            public List<P> Reeds = new(), Rocks = new(), Lilies = new();
            public List<(P, double)> Jetties = new(), Boats = new();
        }

        public static Dressing Dress(TileWater w, string seed)
        {
            var rng = new PyRandom(seed + "-dress");
            var d = new Dressing();
            foreach (var curve in w.Shores)
            {
                for (int k = 2; k < curve.Count - 2; k += 3)
                {
                    P tan = curve[k + 1] - curve[k - 1];
                    if (Length(tan) < 1e-6) continue;
                    P outv = new P(tan.y, -tan.x) * (1 / Length(tan));
                    double r = rng.Random();
                    if (r < 0.4) d.Reeds.Add(ClampInside(curve[k] + outv * 0.2, 0.2));
                    else if (r < 0.5) d.Rocks.Add(ClampInside(curve[k] + outv * 0.25, 0.3));
                    else if (r < 0.7 && (w.Kind == "lake" || w.Kind == "pond")) d.Lilies.Add(curve[k] - outv * 0.6);
                }
            }
            if (w.Kind == "lake" && w.Shores.Count > 0 && rng.Random() < 0.5)
            {
                // max(shores, key=len): the first longest
                var curve = w.Shores[0];
                foreach (var c in w.Shores) if (c.Count > curve.Count) curve = c;
                int k = curve.Count / 2;
                P tan = curve[k + 1] - curve[k - 1];
                double len = Length(tan);
                P inward = new P(-tan.y, tan.x) * (1 / (len != 0 ? len : 1));
                d.Jetties.Add((curve[k], Math.Atan2(inward.y, inward.x)));
            }
            if ((w.Kind == "lake" || w.Kind == "pond") && rng.Random() < 0.6)
            {
                var poly = w.Outlines[0];
                for (int n = 0; n < 60; n++)
                {
                    P p = new P(rng.Uniform(-A, A), rng.Uniform(-R, R));
                    if (!PointIn(poly, p)) continue;
                    bool clear = true;
                    foreach (var c in w.Shores)
                        for (int j = 0; j < c.Count; j += 2)
                            if (Length(p - c[j]) <= 1.0) { clear = false; break; }
                    if (clear)
                    {
                        d.Boats.Add((p, rng.Uniform(0, 2 * Math.PI)));
                        break;
                    }
                }
            }
            return d;
        }
    }
}
