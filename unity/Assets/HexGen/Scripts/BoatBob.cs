using UnityEngine;

namespace HexGen
{
    /// Boats bob gently (render_animation.bob_boats).
    public class BoatBob : MonoBehaviour
    {
        public float Phase;
        float baseY;
        bool started;

        public void Apply(float s)
        {
            if (!started) { baseY = transform.localPosition.y; started = true; }
            var p = transform.localPosition;
            p.y = baseY + 0.03f * Mathf.Sin(2 * Mathf.PI * s / 2 + Phase);
            transform.localPosition = p;
            // A roll about Blender's X axis, which is Unity's -X.
            transform.localRotation = Quaternion.AngleAxis(-0.05f * Mathf.Rad2Deg * Mathf.Sin(2 * Mathf.PI * s / 3 + Phase), Vector3.right);
        }

        void Update() => Apply(HexClock.Now);
    }
}
