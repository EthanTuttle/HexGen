using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace HexGen.EditorTools
{
    /// Keeps a copy of the repo's art/export/*.glb in Assets/Resources/Art (gitignored), so glTFast
    /// imports them while art/ stays the one source of truth. Runs when the editor loads and from the menu.
    [InitializeOnLoad]
    public static class ArtSync
    {
        static ArtSync() => EditorApplication.delayCall += () => Sync(false);

        public static string Source => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "art", "export"));
        const string Dest = "Assets/Resources/Art";

        [MenuItem("HexGen/Sync art from art/export")]
        static void SyncMenu() => Sync(true);

        public static void Sync(bool log)
        {
            if (!Directory.Exists(Source)) { Debug.LogWarning($"HexGen: no art at {Source}"); return; }
            Directory.CreateDirectory(Dest);
            int copied = 0;
            foreach (var src in Directory.GetFiles(Source, "*.glb"))
            {
                var dst = Path.Combine(Dest, Path.GetFileName(src));
                if (File.Exists(dst) && File.ReadAllBytes(dst).SequenceEqual(File.ReadAllBytes(src))) continue;
                File.Copy(src, dst, true);
                copied++;
            }
            if (copied > 0) AssetDatabase.Refresh();
            if (log || copied > 0) Debug.Log($"HexGen: art synced from {Source} ({copied} updated)");
        }
    }
}
