using UnityEngine;

namespace HexGen
{
    /// One clock for everything that moves (water, boats, tweens), so captures can step it by hand.
    public static class HexClock
    {
        static readonly int TimeId = Shader.PropertyToID("_HexTime");
        public static float Now { get; private set; }
        public static bool Manual;

        public static void Set(float t)
        {
            Now = t;
            Shader.SetGlobalFloat(TimeId, t);
        }

        public static void Tick()
        {
            if (!Manual) Set(Time.time);
        }
    }
}
