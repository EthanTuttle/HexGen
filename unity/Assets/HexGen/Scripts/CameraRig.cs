using UnityEngine;
using UnityEngine.InputSystem;

namespace HexGen
{
    /// The tilted hex-screen camera (design/07 Presentation.md -> Camera and controls): drag to pan,
    /// wheel to zoom, right-drag to rotate (snapping to 60 degree steps on release), Q/E rotate 60 degrees,
    /// F frames the current view again. The tilt and zoom limits are prototype values.
    public class CameraRig : MonoBehaviour
    {
        public Camera Cam;
        public Vector3 Target;
        public float Pitch = 50f;           // degrees down from the horizon
        public float Distance = 60f;
        public float MinDistance = 8f, MaxDistance = 110f;
        public float Yaw;                   // degrees; 0 looks north (from the south, like the previews)

        float yawGoal, distGoal;
        Vector3 targetGoal;
        Vector3 homeTarget;
        float homeDistance;
        Vector2 lastMouse;
        bool panning, rotating;
        Plane ground = new(Vector3.up, Vector3.zero);

        public void Frame(Vector3 target, float distance, float yaw = 0f)
        {
            homeTarget = targetGoal = Target = target;
            homeDistance = distGoal = Distance = distance;
            yawGoal = Yaw = yaw;
            ground = new Plane(Vector3.up, new Vector3(0, target.y, 0));
            Apply();
        }

        public void Apply()
        {
            var rot = Quaternion.Euler(Pitch, 180f + Yaw, 0f);
            Cam.transform.rotation = rot;
            Cam.transform.position = Target - rot * Vector3.forward * Distance;
        }

        void Update()
        {
            var mouse = Mouse.current;
            var kb = Keyboard.current;
            if (mouse != null)
            {
                Vector2 m = mouse.position.ReadValue();
                // Zoom toward the cursor's ground point keeps the view steady under the pointer.
                float scroll = mouse.scroll.ReadValue().y;
                if (Mathf.Abs(scroll) > 0.01f)
                    distGoal = Mathf.Clamp(distGoal * Mathf.Pow(0.9f, Mathf.Sign(scroll)), MinDistance, MaxDistance);

                if (mouse.leftButton.wasPressedThisFrame) { panning = true; lastMouse = m; }
                if (mouse.leftButton.wasReleasedThisFrame) panning = false;
                if (panning && GroundPoint(lastMouse, out var a) && GroundPoint(m, out var b))
                    targetGoal += a - b;

                if (mouse.rightButton.wasPressedThisFrame) { rotating = true; lastMouse = m; }
                if (rotating) yawGoal += (m.x - lastMouse.x) * 0.25f;
                if (mouse.rightButton.wasReleasedThisFrame)
                {
                    rotating = false;
                    yawGoal = Mathf.Round(yawGoal / 60f) * 60f;
                }
                lastMouse = m;
            }
            if (kb != null)
            {
                if (kb.qKey.wasPressedThisFrame) yawGoal = Mathf.Round(yawGoal / 60f) * 60f - 60f;
                if (kb.eKey.wasPressedThisFrame) yawGoal = Mathf.Round(yawGoal / 60f) * 60f + 60f;
                if (kb.fKey.wasPressedThisFrame) { targetGoal = homeTarget; distGoal = homeDistance; }
                if (kb.equalsKey.wasPressedThisFrame || kb.numpadPlusKey.wasPressedThisFrame)
                    distGoal = Mathf.Clamp(distGoal * 0.8f, MinDistance, MaxDistance);
                if (kb.minusKey.wasPressedThisFrame || kb.numpadMinusKey.wasPressedThisFrame)
                    distGoal = Mathf.Clamp(distGoal * 1.25f, MinDistance, MaxDistance);
            }

            float k = 1f - Mathf.Exp(-12f * Time.unscaledDeltaTime);
            Yaw = rotating ? yawGoal : Mathf.Lerp(Yaw, yawGoal, k);
            Distance = Mathf.Lerp(Distance, distGoal, k);
            Target = panning ? targetGoal : Vector3.Lerp(Target, targetGoal, k);
            Apply();
        }

        bool GroundPoint(Vector2 screen, out Vector3 p)
        {
            var ray = Cam.ScreenPointToRay(screen);
            if (ground.Raycast(ray, out float d)) { p = ray.GetPoint(d); return true; }
            p = default;
            return false;
        }
    }
}
