// Moving water, ported from the node tree in art/scripts/render_animation.py:
// - ripples flow along rivers (a two-phase flow-map scroll, cross-faded, its restart offset by slow noise)
//   and drift slowly on lakes; a bump from the ripples catches the sun
// - shallow-to-deep colour by distance to the shore
// - a foam rim at the shore that breathes and frays with the ripples
// - sparkle: rare glints in small random cells drifting with the flow, each on its own clock
// Depth (distance to shore) and flow come from a world-space data texture made by WaterBuilder.
Shader "HexGen/Water"
{
    Properties
    {
        _Shallow ("Shallow (linear rgb)", Vector) = (0.36, 0.70, 0.86, 1)
        _Deep ("Deep (linear rgb)", Vector) = (0.13, 0.42, 0.66, 1)
        _Foam ("Foam (linear rgb)", Vector) = (0.94, 0.97, 1.0, 1)
        _Smoothness ("Smoothness", Range(0, 1)) = 0.82
        _Bump ("Bump strength", Float) = 0.1
        _WaterData ("Depth (r) and flow (gb)", 2D) = "black" {}
        _WaterRect ("Data rect (Blender min x, min y, size x, size y)", Vector) = (0, 0, 1, 1)
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP   // Forward+: without it the main light counts as culled
            #include "HexLit.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _Shallow, _Deep, _Foam;   // vectors, so Unity doesn't treat them as sRGB
                half _Smoothness;
                float _Bump;
                float4 _WaterRect;
            CBUFFER_END
            TEXTURE2D(_WaterData); SAMPLER(sampler_WaterData);
            float _HexTime;   // global, seconds
            float4 _HexBackdrop;   // global, linear: the pastel backdrop (DayCycle)

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                return o;
            }

            // --- Noise (stands in for Blender's Perlin noise texture: 0..1 around 0.5) -------------
            float3 hash33(float3 p)
            {
                p = float3(dot(p, float3(127.1, 311.7, 74.7)), dot(p, float3(269.5, 183.3, 246.1)), dot(p, float3(113.5, 271.9, 124.6)));
                return -1.0 + 2.0 * frac(sin(p) * 43758.5453123);
            }

            float perlin(float3 p)
            {
                float3 i = floor(p), f = frac(p);
                float3 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
                float n000 = dot(hash33(i + float3(0, 0, 0)), f - float3(0, 0, 0));
                float n100 = dot(hash33(i + float3(1, 0, 0)), f - float3(1, 0, 0));
                float n010 = dot(hash33(i + float3(0, 1, 0)), f - float3(0, 1, 0));
                float n110 = dot(hash33(i + float3(1, 1, 0)), f - float3(1, 1, 0));
                float n001 = dot(hash33(i + float3(0, 0, 1)), f - float3(0, 0, 1));
                float n101 = dot(hash33(i + float3(1, 0, 1)), f - float3(1, 0, 1));
                float n011 = dot(hash33(i + float3(0, 1, 1)), f - float3(0, 1, 1));
                float n111 = dot(hash33(i + float3(1, 1, 1)), f - float3(1, 1, 1));
                return lerp(lerp(lerp(n000, n100, u.x), lerp(n010, n110, u.x), u.y),
                            lerp(lerp(n001, n101, u.x), lerp(n011, n111, u.x), u.y), u.z);
            }

            // fBm like Blender's noise node: detail + 1 octaves, roughness 0.5, normalised to 0..1.
            float noise01(float3 p, int octaves)
            {
                float sum = 0, amp = 1, norm = 0;
                for (int k = 0; k < octaves; k++)
                {
                    sum += perlin(p) * amp;
                    norm += amp;
                    amp *= 0.5;
                    p *= 2.0;
                }
                return saturate(0.5 + 0.75 * sum / norm);
            }

            float2 hash22(float2 p)
            {
                p = float2(dot(p, float2(127.1, 311.7)), dot(p, float2(269.5, 183.3)));
                return frac(sin(p) * 43758.5453);
            }

            float hash21(float2 p, float w) { return frac(sin(dot(p, float2(12.9898, 78.233)) + w * 37.719) * 43758.5453); }

            // Ripple height at a point, with the flow map (render_animation: ph0/ph1, cross-faded).
            float Wave(float2 pos, float2 flow, float t)
            {
                const float period = 2.0;
                float offset = noise01(float3(pos * 0.25, 0), 1);
                float cycle = t / period + offset * 3.0;
                float ph0 = frac(cycle), ph1 = frac(cycle + 0.5);
                float2 p0 = pos - flow * ph0 * period;
                float2 p1 = pos - flow * ph1 * period + float2(3.7, 1.9);
                float blend = abs((ph0 - 0.5) * 2.0);
                float w = t * 0.12;
                float r0 = noise01(float3(p0 * 0.9, w), 4);
                float r1 = noise01(float3(p1 * 0.9, w), 4);
                return lerp(r0, r1, blend);
            }

            half4 frag(Varyings i) : SV_Target
            {
                float t = _HexTime;
                float2 pos = i.positionWS.xz;
                float2 uv = float2((-pos.x - _WaterRect.x) / _WaterRect.z, (-pos.y - _WaterRect.y) / _WaterRect.w);
                float4 data = SAMPLE_TEXTURE2D(_WaterData, sampler_WaterData, uv);
                float depth = data.r;
                float2 flow = data.gb;

                float wave = Wave(pos, flow, t);
                const float e = 0.04;
                float wx = Wave(pos + float2(e, 0), flow, t);
                float wz = Wave(pos + float2(0, e), flow, t);
                float2 grad = float2(wx - wave, wz - wave) / e;
                float3 n = normalize(float3(-grad.x * _Bump, 1, -grad.y * _Bump));

                // Colour: shallow near the bank, deeper further out.
                float deep = smoothstep(0.2, 2.2, depth);
                half3 col = lerp(_Shallow.rgb, _Deep.rgb, deep);

                // The previews' renderer reflects the pastel world in the water, and the ripples show
                // mostly through that; URP has no sky here, so shade the ripples and reflect the backdrop by hand.
                col *= 0.9 + 0.2 * wave;
                float3 v = GetWorldSpaceNormalizeViewDir(i.positionWS);
                float fres = pow(1.0 - saturate(dot(n, v)), 4.0);
                col = lerp(col, _HexBackdrop.rgb, saturate(0.08 + fres * 0.8));

                // Foam: a rim at the bank that breathes and frays with the ripples.
                float edge = 0.05 + sin(t * 1.6) * 0.03 + wave * 0.12;
                float foam = depth < edge ? 1.0 : 0.0;
                col = lerp(col, _Foam.rgb, foam * 0.75);

                // Sparkle: small random cells drifting with the flow; about 1 in 3 can glint,
                // each with its own pace (a blink every 3.5-6 s) and phase; a blink lasts about 0.4 s.
                float2 drift = (pos - flow * t) * 2.6;
                float2 cell = floor(drift);
                float best = 8;
                float2 bestCell = 0;
                [unroll] for (int y = -1; y <= 1; y++)
                [unroll] for (int x = -1; x <= 1; x++)
                {
                    float2 c = cell + float2(x, y);
                    float2 fp = c + hash22(c);
                    float d = length(drift - fp);
                    if (d < best) { best = d; bestCell = c; }
                }
                float can = hash21(bestCell, 1.0) > 0.65 ? 1.0 : 0.0;
                float pace = 6.283 / (3.5 + hash21(bestCell, 2.0) * 2.5);
                float waveT = sin(t * pace + hash21(bestCell, 3.0) * 6.283);
                float blink = max((waveT - 0.96) / 0.04, 0.0);
                float spark = can * blink * (best < 0.22 ? 1.0 : 0.0) * (depth > 0.35 ? 1.0 : 0.0);

                return HexShade(i.positionWS, n, i.positionCS, col, _Smoothness, spark * 2.5);
            }
            ENDHLSL
        }
        UsePass "HexGen/FlatLit/DEPTHONLY"
        UsePass "HexGen/FlatLit/DEPTHNORMALS"
    }
}
