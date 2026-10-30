using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace HexGen.EditorTools
{
    /// Makes Assets/Scenes/Prototype.unity: one object with the Bootstrap, which builds everything in Play mode.
    public static class SceneSetup
    {
        public const string ScenePath = "Assets/Scenes/Prototype.unity";

        [MenuItem("HexGen/Rebuild prototype scene")]
        public static void Run()
        {
            ArtSync.Sync(false);
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            new GameObject("HexGen").AddComponent<Bootstrap>();
            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            Bootstrap.ConfigurePipeline();
            AssetDatabase.SaveAssets();
            Debug.Log("HexGen: scene ready at " + ScenePath);
        }
    }
}
