using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace HexGen.EditorTools
{
    /// Renders the look-test screenshots into unity/screens/ without entering Play mode (works in batch mode):
    ///   Unity -batchmode -projectPath unity -executeMethod HexGen.EditorTools.Capture.Run
    /// Add "-hexframes <folder>" to also write a 6 s, 24 fps PNG sequence of the moving water.
    public static class Capture
    {
        static string Screens => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "screens"));

        [MenuItem("HexGen/Capture screenshots")]
        public static void Run()
        {
            try
            {
                Shoot(Arg("-hexframes"));
                if (Application.isBatchMode) EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                if (Application.isBatchMode) EditorApplication.Exit(1);
            }
        }

        static string Arg(string name)
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, name);
            return i >= 0 && i + 1 < args.Length ? args[i + 1] : null;
        }

        static void Shoot(string frames)
        {
            ArtSync.Sync(false);
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var b = new GameObject("HexGen").AddComponent<Bootstrap>();
            Bootstrap.Setup(b);
            HexClock.Manual = true;
            Directory.CreateDirectory(Screens);
            var cam = b.Cam;
            var boats = UnityEngine.Object.FindObjectsByType<BoatBob>(FindObjectsSortMode.None);

            void At(float t)
            {
                HexClock.Set(t);
                foreach (var bb in boats) bb.Apply(t);
            }

            // The Blender previews' framing: camera from the south, tilted down by `elevation`.
            void Stage(Vector2 targetBlender, float distance, float elevation, Vector3 offset = default)
            {
                b.Rig.Pitch = elevation;
                b.Rig.Frame(Hex.ToUnity(targetBlender) + offset, distance);
            }

            void Hour(float h) { b.Day.Hour = h; b.Day.Apply(); }

            At(1.0f);
            Hour(12f);
            LogWaterCheck();

            // 1. Map board, same framing as art/preview/map_preview_v6.png (render_preview.stage(2, -2), 74, 45).
            Stage(new Vector2(2, -2), 74, 45);
            Save(cam, "map_board_v1.png", 1600, 1000);

            // 2. The map from the game camera (50 degree tilt), and the time-of-day backdrop.
            Stage(new Vector2(2, -2), Bootstrap.MapDistance, Bootstrap.MapPitch);
            Save(cam, "map_game_camera_v1.png", 1600, 1000);
            foreach (var (h, name) in new[] { (6f, "dawn"), (18f, "dusk"), (0f, "night") })
            {
                Hour(h);
                Save(cam, $"map_{name}_v1.png", 1600, 1000);
            }
            Hour(12f);

            // 3. Water: the reference video's framing (render_animation: (5, -5), 46, 42) and a close-up.
            Stage(new Vector2(5, -5), 46, 42);
            Save(cam, "water_anim_framing_v1.png", 1280, 800);
            Stage(Hex.TilePosition(-1, 2) + new Vector2(2.5f, 1.5f), 16, 40);
            At(2.2f);
            Save(cam, "water_closeup_v1.png", 1600, 1000);
            At(1.0f);

            // 4. The stand-in party on a map tile (render_standin_minis.map_tile framing: (0.6, -0.9), 22, 45).
            Stage(Hex.TilePosition(World.PartyTile.x, World.PartyTile.y) + new Vector2(0.6f, -0.9f), 22, 45);
            Save(cam, "party_on_tile_v1.png", 1600, 1000);

            // 5. Combat board (render_preview combat framing: (0, -0.4), 20, 48), then mid-attack.
            Stage(new Vector2(0, -0.4f), 20, 48, World.CombatOrigin);
            Save(cam, "combat_board_v1.png", 1600, 1000);
            b.Demo.Init();
            b.Demo.Play(0, 0f);
            b.Demo.Pose(MiniTweens.HopTime * 0.5f);
            Save(cam, "combat_hop_v1.png", 1600, 1000);
            b.Demo.Pose(MiniTweens.HopTime * 0.5f + 0.09f);
            Save(cam, "combat_recoil_v1.png", 1600, 1000);
            b.Demo.Play(0, 0f);
            b.Demo.Pose(10f);

            // 6. Optional: frames of moving water for a video.
            if (!string.IsNullOrEmpty(frames))
            {
                Directory.CreateDirectory(frames);
                Stage(new Vector2(5, -5), 46, 42);
                for (int f = 0; f < 24 * 6; f++)
                {
                    At(f / 24f);
                    Save(cam, null, 1280, 800, Path.Combine(frames, $"frame_{f:000}.png"));
                }
            }
            Debug.Log("HexGen: captures written to " + Screens);
        }

        /// First outline point per water tile, to compare with water.py (the port must match exactly).
        static void LogWaterCheck()
        {
            var sb = new System.Text.StringBuilder("HexGen water check:");
            foreach (var (tile, terrain) in World.Map)
            {
                if (terrain != "river") continue;
                var mask = new bool[6];
                for (int i = 0; i < 6; i++)
                    mask[i] = World.Map.TryGetValue(tile + Hex.Neighbours[i], out var n) && n == "river";
                var w = WaterShapes.Compute(mask, $"{tile.x},{tile.y}");
                var p = w.Outlines[0][w.Outlines[0].Count / 2];
                sb.Append($" {tile.x},{tile.y}:{w.Kind}:{p.x:F6},{p.y:F6}");
            }
            sb.Append($" rnd:{new PyRandom("0,-1").Random():F12} frnd:{new PyRandom(GroundCover.Hash01(3, -7, 4)).Random():F12}");
            Debug.Log(sb.ToString());
        }

        static void Save(Camera cam, string name, int w, int h, string path = null)
        {
            var desc = new RenderTextureDescriptor(w, h, RenderTextureFormat.ARGB32, 24)
            {
                sRGB = true, msaaSamples = 4
            };
            var rt = new RenderTexture(desc);
            var prev = cam.targetTexture;
            cam.targetTexture = rt;
            cam.aspect = (float)w / h;
            cam.Render();
            var active = RenderTexture.active;
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            RenderTexture.active = active;
            cam.targetTexture = prev;
            cam.ResetAspect();
            File.WriteAllBytes(path ?? Path.Combine(Screens, name), tex.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(tex);
            rt.Release();
            UnityEngine.Object.DestroyImmediate(rt);
        }
    }
}
