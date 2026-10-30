using System.Collections.Generic;
using UnityEngine;

namespace HexGen
{
    /// Builds the prototype's world: the test map (render_preview.build_map), the stand-in party on a
    /// map tile and the radius-4 combat board with stand-ins (render_standin_minis). Works in edit mode too,
    /// so the capture script can build it without entering Play mode.
    public class World
    {
        // Pointy-top axial (q, r) -> terrain: render_preview.MAP.
        public static readonly Dictionary<Vector2Int, string> Map = new()
        {
            [new(0, 0)] = "forest", [new(1, -1)] = "forest", [new(1, 0)] = "forest",
            [new(0, 1)] = "plains", [new(-2, 0)] = "plains",
            [new(-1, 0)] = "village", [new(-1, -1)] = "village",
            [new(2, -1)] = "farmland", [new(2, -2)] = "farmland", [new(1, -2)] = "farmland", [new(0, -2)] = "farmland",
            // a lake (four touching tiles), a river running out of it with a bend, ending in a spring
            [new(-2, 1)] = "river", [new(-2, 2)] = "river", [new(-1, 1)] = "river", [new(-1, 2)] = "river",
            [new(0, 2)] = "river", [new(1, 1)] = "river", [new(2, 0)] = "river", [new(3, 0)] = "river",
            // a pond: a water tile with no water neighbours
            [new(0, -1)] = "river",
        };

        // Farms and villages count as joined (render_preview.LINKED / BORDERED).
        static bool Linked(string a, string b) =>
            a == b || (a == "farmland" && b == "village") || (a == "village" && b == "farmland");
        static readonly HashSet<string> Bordered = new() { "farmland", "village" };

        // Where the party stands on the map, and the combat board's place in the Unity world.
        public static readonly Vector2Int PartyTile = new(0, 1);
        public static readonly Vector3 CombatOrigin = new(400, 0, 0);

        public Transform Root, MapRoot, CombatRoot;
        public Vector3 MapCentre;          // Unity world: render_preview's camera target (2, -2, 0)
        public Material WaterMaterial;
        public readonly Dictionary<string, Transform> CombatMinis = new();
        public readonly List<Transform> Party = new();

        Dictionary<string, GameObject> tiles, cells, minis;
        Material flatMat, groundMat;

        public static World Build(Transform parent)
        {
            var w = new World();
            w.Root = new GameObject("World").transform;
            w.Root.SetParent(parent, false);
            w.tiles = LoadKit("Art/tiles");
            w.cells = LoadKit("Art/combat_cells");
            w.minis = LoadKit("Art/standin_minis");
            w.flatMat = new Material(Shader.Find("HexGen/FlatLit")) { name = "flat" };
            w.groundMat = new Material(Shader.Find("HexGen/Ground")) { name = "ground" };
            w.BuildMap();
            w.BuildParty();
            w.BuildCombat();
            return w;
        }

        static Dictionary<string, GameObject> LoadKit(string path)
        {
            var root = Resources.Load<GameObject>(path);
            if (root == null)
                throw new System.Exception($"Missing {path}.glb in Resources: run HexGen > Sync art from art/export");
            var d = new Dictionary<string, GameObject>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                if (t != root.transform) d[t.name] = t.gameObject;
            return d;
        }

        static GameObject Place(Dictionary<string, GameObject> kit, string name, Transform parent, Vector2 at, float angle = 0)
        {
            var go = Object.Instantiate(kit[name], parent);
            go.name = name;
            go.transform.localPosition = Hex.ToUnity(at);
            go.transform.localRotation = Hex.Spin(angle);
            go.transform.localScale = Vector3.one;
            return go;
        }

        GameObject MeshObject(string name, Mesh mesh, Material mat, Transform parent, bool shadows = true)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = shadows ? UnityEngine.Rendering.ShadowCastingMode.On : UnityEngine.Rendering.ShadowCastingMode.Off;
            return go;
        }

        // --- Map -----------------------------------------------------------------------------------------

        void BuildMap()
        {
            MapRoot = new GameObject("Map").transform;
            MapRoot.SetParent(Root, false);
            MapCentre = Hex.ToUnity(new Vector2(2, -2));
            var waterTiles = new List<WaterBuilder.WaterTile>();
            var waterShapes = new Dictionary<Vector2Int, WaterShapes.TileWater>();

            foreach (var (tile, terrain) in Map)
            {
                int q = tile.x, r = tile.y;
                var at = Hex.TilePosition(q, r);
                var holder = new GameObject($"tile_{q}_{r}_{terrain}").transform;
                holder.SetParent(MapRoot, false);
                var baseGo = Place(tiles, $"base_{terrain}", holder, at);
                PaintGround(baseGo, tile, terrain);
                if (terrain == "river")
                {
                    // Water is drawn per tile from its own water neighbours (water.py).
                    var mask = new bool[6];
                    for (int i = 0; i < 6; i++)
                        mask[i] = Map.TryGetValue(tile + Hex.Neighbours[i], out var n) && n == "river";
                    var shape = WaterShapes.Compute(mask, $"{q},{r}");
                    waterTiles.Add(new WaterBuilder.WaterTile { Tile = tile, At = at, Mask = mask, Shape = shape });
                    waterShapes[tile] = shape;
                    continue;
                }
                Place(tiles, $"{terrain}_centre", holder, at);
                var joined = new bool[6];
                for (int i = 0; i < 6; i++)
                    joined[i] = Map.TryGetValue(tile + Hex.Neighbours[i], out var n) && Linked(terrain, n);
                for (int i = 0; i < 6; i++)
                {
                    float ang = Mathf.Deg2Rad * 60 * i;
                    Place(tiles, $"{terrain}_edge_{(joined[i] ? "same" : "other")}", holder, at, ang);
                    // Carry a neighbouring edge's border out to this joined edge, so borders run on between tiles.
                    if (Bordered.Contains(terrain) && joined[i] && tiles.ContainsKey("border_join_l"))
                    {
                        if (!joined[(i + 1) % 6]) Place(tiles, "border_join_l", holder, at, ang);
                        if (!joined[(i + 5) % 6]) Place(tiles, "border_join_r", holder, at, ang);
                    }
                }
            }

            // Water: plates, banks and dressing, bobbing boats.
            var water = WaterBuilder.Build(waterTiles);
            WaterMaterial = new Material(Shader.Find("HexGen/Water")) { name = "water" };
            WaterMaterial.SetTexture("_WaterData", water.Data);
            WaterMaterial.SetVector("_WaterRect", water.DataRect);
            MeshObject("water", water.Plates.ToMesh("water"), WaterMaterial, MapRoot, false);
            MeshObject("water_dressing", water.Dressing.ToMesh("water_dressing"), flatMat, MapRoot);
            foreach (var (at, angle, index) in water.Boats)
            {
                var boat = MeshObject($"boat_{index}", WaterBuilder.BoatMesh(angle), flatMat, MapRoot);
                boat.transform.localPosition = Hex.ToUnity(at);
                boat.AddComponent<BoatBob>().Phase = index;
            }

            // Small ground cover across the whole map from one world-space pattern.
            var cover = new MeshKit();
            GroundCover.Build(cover, Map, waterShapes);
            MeshObject("ground_cover", cover.ToMesh("ground_cover"), flatMat, MapRoot);

            // Pale empty slots around the land.
            var slots = new MeshKit();
            var slotSet = new HashSet<Vector2Int>();
            foreach (var t in Map.Keys)
                foreach (var n in Hex.Neighbours)
                    if (!Map.ContainsKey(t + n)) slotSet.Add(t + n);
            var corners = Hex.Corners(Hex.TileRadius * 0.94f, true);
            System.Array.Reverse(corners);   // anticlockwise
            foreach (var s in slotSet)
            {
                var c = Hex.TilePosition(s.x, s.y);
                var outline = new Vector2[6];
                for (int i = 0; i < 6; i++) outline[i] = corners[i] + c;
                slots.Prism(outline, -0.3f, -0.28f, Hex.Palette("slot"));
            }
            MeshObject("slots", slots.ToMesh("slots"), flatMat, MapRoot, false);
        }

        /// The base slab's top gets the fading ground shader; its soil sides keep their imported materials.
        void PaintGround(GameObject baseGo, Vector2Int tile, string terrain)
        {
            var mr = baseGo.GetComponent<MeshRenderer>();
            var mats = mr.sharedMaterials;
            mats[0] = groundMat;
            mr.sharedMaterials = mats;
            var own = Hex.Palette(Hex.Ground(terrain));
            var mpb = new MaterialPropertyBlock();
            mpb.SetColor("_BaseColor", own);
            var nb = new Vector4[6];
            for (int i = 0; i < 6; i++)
            {
                var c = Map.TryGetValue(tile + Hex.Neighbours[i], out var n) ? Hex.Palette(Hex.Ground(n)) : own;
                nb[i] = c.linear;   // vector arrays aren't converted to linear for us
            }
            mpb.SetVectorArray("_Neighbour", nb);
            var centre = baseGo.transform.position;
            mpb.SetVector("_TileCentre", new Vector4(centre.x, centre.z, 0, 0));
            mpb.SetFloat("_Apothem", Hex.TileApothem);
            mr.SetPropertyBlock(mpb, 0);
        }

        // --- Party on a map tile ------------------------------------------------------------------------

        void BuildParty()
        {
            // render_standin_minis.PARTY: hero in front, companions close behind, a loose cluster at true scale.
            var party = new (string, Vector2Int)[]
            {
                ("standin_hero", new(0, 1)), ("standin_chelmsford", new(-1, 1)), ("standin_small", new(1, 0)), ("standin_fluffy", new(0, 0))
            };
            var holder = new GameObject("Party").transform;
            holder.SetParent(MapRoot, false);
            var at = Hex.TilePosition(PartyTile.x, PartyTile.y);
            foreach (var (name, cell) in party)
            {
                var go = Place(minis, name, holder, at + Hex.CellPosition(cell.x, cell.y) + new Vector2(0.6f, -0.4f));
                Party.Add(go.transform);
            }
        }

        // --- Combat board -------------------------------------------------------------------------------

        void BuildCombat()
        {
            CombatRoot = new GameObject("Combat").transform;
            CombatRoot.SetParent(Root, false);
            CombatRoot.localPosition = CombatOrigin;
            // render_preview.build_board: radius 4, 61 flat-top cells, some trees and rocks.
            var trees = new HashSet<Vector2Int> { new(1, -3), new(2, -3), new(-3, 1), new(-2, 2), new(3, 0) };
            var rocks = new HashSet<Vector2Int> { new(0, 2), new(-1, -1), new(2, 1) };
            const int radius = 4;
            for (int q = -radius; q <= radius; q++)
            for (int r = Mathf.Max(-radius, -q - radius); r <= Mathf.Min(radius, -q + radius); r++)
            {
                var c = new Vector2Int(q, r);
                string name = trees.Contains(c) ? "cell_tree" : rocks.Contains(c) ? "cell_rock"
                    : $"cell_grass_{"abc"[(((q - r) % 3) + 3) % 3]}";
                Place(cells, name, CombatRoot, Hex.CellPosition(q, r));
            }
            // render_standin_minis.board: the party, and three enemies facing them.
            var placed = new (string key, string piece, Vector2Int cell)[]
            {
                ("hero", "standin_hero", new(0, 0)), ("chelmsford", "standin_chelmsford", new(-1, 1)),
                ("small", "standin_small", new(1, 0)), ("fluffy", "standin_fluffy", new(-1, 2)),
                ("enemy_a", "standin_enemy", new(0, -3)), ("enemy_b", "standin_enemy", new(1, -2)),
                ("enemy_c", "standin_enemy", new(-1, -2)),
            };
            foreach (var (key, piece, cell) in placed)
            {
                var go = Place(minis, piece, CombatRoot, Hex.CellPosition(cell.x, cell.y),
                               piece == "standin_enemy" ? Mathf.PI : 0f);
                go.name = key;
                CombatMinis[key] = go.transform;
            }
        }
    }
}
