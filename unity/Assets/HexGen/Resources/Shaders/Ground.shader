// The top of a map tile's base slab. Its ground colour fades toward each neighbour's within _Blend
// metres of the shared edge, reaching the average of the two exactly at the edge, so both tiles agree
// there (the same rule as the ground cover density in art/scripts/ground_cover.py).
Shader "HexGen/Ground"
{
    Properties
    {
        _BaseColor ("Own ground colour", Color) = (0.66, 0.81, 0.49, 1)
        _Smoothness ("Smoothness", Range(0, 1)) = 0.1
        _Blend ("Fade distance (m)", Float) = 1.6
        _Apothem ("Tile apothem (m)", Float) = 3.897
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

            half4 _BaseColor;
            half _Smoothness;
            float _Blend;
            float _Apothem;
            float4 _TileCentre;           // Unity world xz in .xy
            half4 _Neighbour[6];          // ground colour across edge i (own colour where there's no tile)

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; float3 normalWS : TEXCOORD1; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float2 local = i.positionWS.xz - _TileCentre.xy;
                half3 own = _BaseColor.rgb;
                half3 col = own;
                [unroll] for (int e = 0; e < 6; e++)
                {
                    // Edge e faces Blender (cos 60e, sin 60e), which is Unity (-cos, -sin) in xz.
                    float a = radians(60.0 * e);
                    float2 n = float2(-cos(a), -sin(a));
                    float toEdge = _Apothem - dot(local, n);
                    float w = 0.5 * saturate(1.0 - toEdge / _Blend);
                    col += w * (_Neighbour[e].rgb - own);
                }
                return HexShade(i.positionWS, i.normalWS, i.positionCS, col, _Smoothness, 0);
            }
            ENDHLSL
        }
        UsePass "HexGen/FlatLit/SHADOWCASTER"
        UsePass "HexGen/FlatLit/DEPTHONLY"
        UsePass "HexGen/FlatLit/DEPTHNORMALS"
    }
}
