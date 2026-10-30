using UnityEditor;
using UnityEngine;

namespace HexGen.EditorTools
{
    /// Builds the prototype for macOS into unity/Builds/ (not committed).
    public static class BuildMac
    {
        [MenuItem("HexGen/Build for macOS")]
        public static void Run()
        {
            ArtSync.Sync(false);
            PlayerSettings.productName = "HexGen Unity prototype";
            PlayerSettings.runInBackground = true;
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { SceneSetup.ScenePath },
                locationPathName = "Builds/HexGen Unity prototype.app",
                target = BuildTarget.StandaloneOSX,
            });
            Debug.Log($"HexGen: build {report.summary.result}, {report.summary.totalErrors} errors");
            if (Application.isBatchMode) EditorApplication.Exit(report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded ? 0 : 1);
        }
    }
}
