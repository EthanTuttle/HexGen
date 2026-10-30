using UnityEngine;
using UnityEngine.Rendering;

namespace HexGen
{
    /// The pastel backdrop and the light drifting with a time-of-day value (look test 2).
    /// Rule (design/07 Presentation.md -> Art direction): soft peach at dawn, pale sky-blue at midday,
    /// rose at dusk, a darker, cooler pastel at night. The exact colours are still an open question there,
    /// so every number below is a PLACEHOLDER for the look test; midday uses the palette's backdrop colour.
    [ExecuteAlways]
    public class DayCycle : MonoBehaviour
    {
        [Range(0, 24)] public float Hour = 12f;
        public bool Running;
        public float HoursPerSecond = 1f;
        public Light Sun;
        public Camera[] Cameras;

        struct Key
        {
            public float Hour;
            public Color Backdrop, Light;
            public float Intensity, Ambient;
            public Vector3 Dir;    // Unity world direction the light travels
        }

        // Midday's light direction is the Blender previews' sun (render_preview.stage), converted to Unity.
        static readonly Vector3 NoonDir = new(-0.6952f, -0.6124f, -0.3764f);

        static Key[] keys;

        static Color Hexc(string h) { ColorUtility.TryParseHtmlString(h, out var c); return c; }

        static Key[] Keys() => keys ??= new[]
        {
            new Key { Hour = 0,  Backdrop = Hexc("#8F9BBE"), Light = Hexc("#AFC0FF"), Intensity = 0.55f, Ambient = 0.55f, Dir = new Vector3(-0.3f, -0.8f, -0.5f) },
            new Key { Hour = 6,  Backdrop = Hexc("#F8D9C2"), Light = Hexc("#FFE2C8"), Intensity = 1.3f, Ambient = 0.65f, Dir = new Vector3(-0.85f, -0.35f, -0.4f) },
            new Key { Hour = 12, Backdrop = Hexc("#CFE4F2"), Light = Hexc("#FFF8EE"), Intensity = 1.6f, Ambient = 0.6f,  Dir = NoonDir },
            new Key { Hour = 18, Backdrop = Hexc("#EFC3CC"), Light = Hexc("#FFDCD0"), Intensity = 1.3f, Ambient = 0.65f, Dir = new Vector3(0.8f, -0.35f, -0.5f) },
            new Key { Hour = 24, Backdrop = Hexc("#8F9BBE"), Light = Hexc("#AFC0FF"), Intensity = 0.55f, Ambient = 0.55f, Dir = new Vector3(-0.3f, -0.8f, -0.5f) },
        };

        public static string Phase(float hour) =>
            hour < 4.5f || hour >= 20.5f ? "night" : hour < 9f ? "dawn" : hour < 15.5f ? "midday" : hour < 20.5f ? "dusk" : "night";

        void Update()
        {
            if (Running && Application.isPlaying) Hour = Mathf.Repeat(Hour + HoursPerSecond * Time.deltaTime, 24f);
            Apply();
        }

        public void Apply()
        {
            var k = Keys();
            int i = 0;
            while (i < k.Length - 2 && Hour >= k[i + 1].Hour) i++;
            float t = Mathf.InverseLerp(k[i].Hour, k[i + 1].Hour, Hour);
            t = t * t * (3 - 2 * t);   // ease, so each colour holds a little around its hour
            Color back = Color.Lerp(k[i].Backdrop, k[i + 1].Backdrop, t);
            if (Cameras != null)
                foreach (var c in Cameras)
                    if (c) c.backgroundColor = back;
            if (Sun)
            {
                Sun.color = Color.Lerp(k[i].Light, k[i + 1].Light, t);
                Sun.intensity = Mathf.Lerp(k[i].Intensity, k[i + 1].Intensity, t);
                var dir = Vector3.Slerp(k[i].Dir.normalized, k[i + 1].Dir.normalized, t);
                Sun.transform.rotation = Quaternion.LookRotation(dir, Vector3.up);
            }
            Shader.SetGlobalVector("_HexBackdrop", back.linear);
            // Soft light from the backdrop fills the shadows (the previews light the scene with it at half strength).
            float amb = Mathf.Lerp(k[i].Ambient, k[i + 1].Ambient, t);
            var ambient = back.linear * amb;
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = ambient;
            var sh = new SphericalHarmonicsL2();
            sh.AddAmbientLight(ambient);
            RenderSettings.ambientProbe = sh;
        }
    }
}
