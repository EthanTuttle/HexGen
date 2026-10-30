using System.Collections.Generic;
using UnityEngine;

namespace HexGen
{
    /// Hex maths and palette, ported from art/scripts/hexkit.py.
    /// Shape code works in Blender's ground plane (x right, y north, z up), like the Python references,
    /// and converts to Unity at the end: Blender (x, y, z) -> Unity (-x, z, -y), the same mapping glTFast
    /// gives the imported tiles (the glTF exporter turns Z-up into Y-up, glTFast mirrors X).
    public static class Hex
    {
        public const float CellFlats = 1.0f;
        public static readonly float CellRadius = CellFlats / Mathf.Sqrt(3f);
        public const float TileRadius = 4.5f;
        public static readonly float TileApothem = TileRadius * Mathf.Sqrt(3f) / 2f;

        // Axial neighbour offsets for pointy-top tiles; edge 0 faces +X (Blender), anticlockwise in 60 degree steps.
        public static readonly Vector2Int[] Neighbours =
        {
            new(1, 0), new(1, -1), new(0, -1), new(-1, 0), new(-1, 1), new(0, 1)
        };

        public static Vector2 TilePosition(int q, int r) =>
            new(2f * TileApothem * (q + r / 2f), -1.5f * TileRadius * r);

        public static Vector2 CellPosition(int q, int r) =>
            new(1.5f * CellRadius * q, -CellFlats * (r + q / 2f));

        public static Vector3 ToUnity(Vector2 b, float height = 0f) => new(-b.x, height, -b.y);
        public static Vector3 ToUnity(Vector3 b) => new(-b.x, b.z, -b.y);

        /// A rotation of `radians` anticlockwise about Blender's Z, as a Unity rotation.
        public static Quaternion Spin(float radians) => Quaternion.Euler(0f, -radians * Mathf.Rad2Deg, 0f);

        public static Vector2[] Corners(float radius, bool pointy)
        {
            float start = pointy ? 90f : 0f;
            var c = new Vector2[6];
            for (int i = 0; i < 6; i++)
            {
                float a = (start - 60f * i) * Mathf.Deg2Rad;
                c[i] = new Vector2(radius * Mathf.Cos(a), radius * Mathf.Sin(a));
            }
            return c;
        }

        // --- Palette (hexkit.PALETTE: placeholders from the mockups) ---------------------------------

        static readonly Dictionary<string, string> PaletteHex = new()
        {
            ["plains"] = "#A8CF7E", ["forest"] = "#5E8F5A", ["farmland"] = "#DCC562", ["river"] = "#86BEDB",
            ["village"] = "#E6C590", ["soil_light"] = "#8A6446", ["soil_dark"] = "#6B4C35",
            ["grass_ink"] = "#4F7A33", ["leaf"] = "#4E8049", ["leaf_dark"] = "#3B6A3A", ["trunk"] = "#7A5236",
            ["water"] = "#86BEDB", ["bank"] = "#C9B58A", ["reed"] = "#6E8F3E", ["lily"] = "#5E9E4E",
            ["boat"] = "#E9DCC0", ["cobble"] = "#BCB2A4", ["rock"] = "#A9A39A", ["flower"] = "#F2D46B",
            ["slot"] = "#F6EFE4", ["backdrop"] = "#CFE4F2",
        };

        public static Color Palette(string name)
        {
            ColorUtility.TryParseHtmlString(PaletteHex[name], out var c);
            return c;
        }

        /// Ground colour on top of a terrain's base slab (build_tiles.GROUND).
        public static string Ground(string terrain) => terrain switch
        {
            "river" => "plains",
            "village" => "cobble",
            "farmland" => "plains",
            _ => terrain,
        };
    }
}
