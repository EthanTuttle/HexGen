using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace HexGen
{
    /// Sets up the look-test scene: light, camera, the world, the day cycle and the combat demo.
    /// Tab switches between the map and the combat board.
    public class Bootstrap : MonoBehaviour
    {
        public World World;
        public Camera Cam;
        public CameraRig Rig;
        public DayCycle Day;
        public CombatDemo Demo;
        public bool InCombat;

        public const float MapPitch = 50f, MapDistance = 62f, CombatDistance = 17f;

        void Awake() => Setup(this);

        /// Builds everything under `host`. Used by Play mode and by the capture script in edit mode.
        public static void Setup(Bootstrap b)
        {
            ConfigurePipeline();
            var host = b.transform;

            var sunGo = new GameObject("Sun");
            sunGo.transform.SetParent(host, false);
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.75f;
#if UNITY_EDITOR
            sun.lightmapBakeType = LightmapBakeType.Realtime;
#endif
            RenderSettings.sun = sun;
            RenderSettings.skybox = null;

            var camGo = new GameObject("Camera");
            camGo.transform.SetParent(host, false);
            camGo.tag = "MainCamera";
            b.Cam = camGo.AddComponent<Camera>();
            b.Cam.clearFlags = CameraClearFlags.SolidColor;
            b.Cam.fieldOfView = 25.4f;    // the previews' 50 mm lens at 16:10
            b.Cam.nearClipPlane = 0.3f;
            b.Cam.farClipPlane = 600f;
            var data = camGo.AddComponent<UniversalAdditionalCameraData>();
            data.renderPostProcessing = false;    // no tone mapping: flat colours stay as authored
            data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
            data.antialiasingQuality = AntialiasingQuality.High;

            b.World = World.Build(host);

            b.Rig = camGo.AddComponent<CameraRig>();
            b.Rig.Cam = b.Cam;
            b.Rig.Pitch = MapPitch;
            b.Rig.Frame(b.World.MapCentre, MapDistance);

            b.Day = host.gameObject.AddComponent<DayCycle>();
            b.Day.Sun = sun;
            b.Day.Cameras = new[] { b.Cam };
            b.Day.Apply();

            b.Demo = b.World.CombatRoot.gameObject.AddComponent<CombatDemo>();
            b.Demo.World = b.World;
        }

        public static void ConfigurePipeline()
        {
            if (GraphicsSettings.currentRenderPipeline is UniversalRenderPipelineAsset urp)
            {
                urp.shadowDistance = 150f;
                urp.shadowCascadeCount = 4;
                urp.msaaSampleCount = 4;
                urp.mainLightShadowmapResolution = 4096;
                urp.useSRPBatcher = false;
            }
        }

        public void ShowCombat(bool combat)
        {
            InCombat = combat;
            if (combat) Rig.Frame(World.CombatRoot.position + Hex.ToUnity(new Vector2(0, -0.4f)), CombatDistance);
            else Rig.Frame(World.MapCentre, MapDistance);
        }

        void Start()
        {
            // "-hexshot <file.png>": save a screenshot of the running game after a few seconds, then quit
            // (used to check a build end to end).
            var args = System.Environment.GetCommandLineArgs();
            int i = System.Array.IndexOf(args, "-hexshot");
            if (i >= 0 && i + 1 < args.Length) StartCoroutine(ShotAndQuit(args[i + 1]));
        }

        System.Collections.IEnumerator ShotAndQuit(string path)
        {
            yield return new WaitForSeconds(3f);
            Day.Hour = 9f;
            yield return new WaitForSeconds(0.5f);
            ScreenCapture.CaptureScreenshot(path);
            yield return new WaitForSeconds(1f);
            Application.Quit();
        }

        void Update()
        {
            HexClock.Tick();
            var kb = Keyboard.current;
            if (kb == null) return;
            if (kb.tabKey.wasPressedThisFrame) ShowCombat(!InCombat);
            if (kb.tKey.wasPressedThisFrame) Day.Running = !Day.Running;
            if (kb.leftBracketKey.isPressed) Day.Hour = Mathf.Repeat(Day.Hour - 6f * Time.deltaTime, 24f);
            if (kb.rightBracketKey.isPressed) Day.Hour = Mathf.Repeat(Day.Hour + 6f * Time.deltaTime, 24f);
            if (kb.digit1Key.wasPressedThisFrame) Day.Hour = 6f;
            if (kb.digit2Key.wasPressedThisFrame) Day.Hour = 12f;
            if (kb.digit3Key.wasPressedThisFrame) Day.Hour = 18f;
            if (kb.digit4Key.wasPressedThisFrame) Day.Hour = 0f;
        }

        void OnGUI()
        {
            GUI.color = new Color(0.2f, 0.2f, 0.25f, 0.85f);
            GUI.Label(new Rect(12, 8, 900, 22),
                $"{(InCombat ? "Combat" : "Map")}  ·  {Day.Hour:00.0} h ({DayCycle.Phase(Day.Hour)}{(Day.Running ? ", running" : "")})  ·  " +
                "Tab map/combat · drag pan · wheel zoom · right-drag or Q/E rotate · F frame · T run clock · [ ] scrub · 1-4 dawn/noon/dusk/night · Space attack");
        }
    }
}
