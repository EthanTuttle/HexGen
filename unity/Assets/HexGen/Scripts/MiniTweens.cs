using System.Collections.Generic;
using UnityEngine;

namespace HexGen
{
    /// Minis have no walking or swinging animations; actions move the whole mini
    /// (design/07 Presentation.md -> Art direction): the attacker does a little hop toward its target,
    /// and the mini that gets hit recoils (tilts back). Heights, distances and timings are prototype values.
    public static class MiniTweens
    {
        public const float HopTime = 0.42f, HopHeight = 0.35f, HopReach = 0.3f;
        public const float RecoilTime = 0.5f, RecoilTilt = 18f, RecoilPush = 0.12f;

        /// Offset and tilt of an attacker `t` seconds into its hop toward `dir` (unit, ground plane).
        public static void Hop(float t, Vector3 dir, out Vector3 offset, out Quaternion tilt)
        {
            float u = Mathf.Clamp01(t / HopTime);
            float arc = 4f * u * (1f - u);                  // up and down
            float lunge = Mathf.Sin(u * Mathf.PI);          // out and back
            offset = Vector3.up * (HopHeight * arc) + dir * (HopReach * lunge);
            tilt = Quaternion.AngleAxis(10f * lunge, Vector3.Cross(Vector3.up, dir));   // lean into it
        }

        /// Offset and tilt of a target `t` seconds after it is hit from direction `dir` (attacker -> target).
        public static void Recoil(float t, Vector3 dir, out Vector3 offset, out Quaternion tilt)
        {
            float u = Mathf.Clamp01(t / RecoilTime);
            // A quick knock back, then an eased settle with a small overshoot.
            float k = u < 0.18f ? u / 0.18f : 1f - EaseOutBack((u - 0.18f) / 0.82f);
            offset = dir * (RecoilPush * k);
            tilt = Quaternion.AngleAxis(RecoilTilt * k, Vector3.Cross(Vector3.up, dir));
        }

        static float EaseOutBack(float x)
        {
            const float c1 = 1.4f, c3 = c1 + 1f;
            return 1f + c3 * Mathf.Pow(x - 1f, 3) + c1 * Mathf.Pow(x - 1f, 2);
        }
    }

    /// Plays attacks on the combat board in a loop (Space plays the next one now).
    public class CombatDemo : MonoBehaviour
    {
        public World World;
        public bool Loop = true;
        public float Gap = 1.6f;

        // Who attacks whom. The stand-in layout is render_standin_minis.board; reach isn't checked here.
        static readonly (string, string)[] Attacks =
        {
            ("hero", "enemy_b"), ("enemy_c", "chelmsford"), ("chelmsford", "enemy_c"), ("enemy_b", "small"),
        };

        readonly Dictionary<Transform, (Vector3 pos, Quaternion rot)> rest = new();
        int next;
        float started = -100f;
        Transform attacker, target;
        Vector3 dir;

        public void Init()
        {
            rest.Clear();
            foreach (var m in World.CombatMinis.Values) rest[m] = (m.localPosition, m.localRotation);
        }

        public void Play(int index, float now)
        {
            ResetPose();
            var (a, b) = Attacks[index % Attacks.Length];
            attacker = World.CombatMinis[a];
            target = World.CombatMinis[b];
            dir = target.localPosition - attacker.localPosition;
            dir.y = 0;
            dir.Normalize();
            started = now;
        }

        void ResetPose()
        {
            foreach (var (m, p) in rest) { m.localPosition = p.pos; m.localRotation = p.rot; }
        }

        public void Pose(float now)
        {
            if (attacker == null) return;
            float t = now - started;
            MiniTweens.Hop(t, dir, out var ho, out var ht);
            attacker.localPosition = rest[attacker].pos + ho;
            attacker.localRotation = ht * rest[attacker].rot;
            // The hit lands as the hop reaches its target, halfway through.
            float hit = MiniTweens.HopTime * 0.5f;
            if (t >= hit)
            {
                MiniTweens.Recoil(t - hit, dir, out var ro, out var rt);
                target.localPosition = rest[target].pos + ro;
                target.localRotation = rt * rest[target].rot;
            }
        }

        void Update()
        {
            if (rest.Count == 0) Init();
            float now = HexClock.Now;
            var kb = UnityEngine.InputSystem.Keyboard.current;
            bool manual = kb != null && kb.spaceKey.wasPressedThisFrame;
            if (manual || (Loop && now - started > Gap)) Play(next++, now);
            Pose(now);
        }
    }
}
