// Shared lighting for HexGen's own shaders: URP's PBR lighting (main light, soft shadows, SSAO,
// ambient from the probe), so they match the glTFast-imported tiles.
#ifndef HEXGEN_LIT_INCLUDED
#define HEXGEN_LIT_INCLUDED

#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

half4 HexShade(float3 positionWS, float3 normalWS, float4 positionCS, half3 albedo, half smoothness, half3 emission)
{
    InputData id = (InputData)0;
    id.positionWS = positionWS;
    id.positionCS = positionCS;
    id.normalWS = normalize(normalWS);
    id.viewDirectionWS = GetWorldSpaceNormalizeViewDir(positionWS);
    id.shadowCoord = TransformWorldToShadowCoord(positionWS);
    id.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(positionCS);
    id.bakedGI = SampleSH(id.normalWS);
    id.shadowMask = half4(1, 1, 1, 1);

    SurfaceData s = (SurfaceData)0;
    s.albedo = albedo;
    s.metallic = 0;
    s.specular = 0;
    s.smoothness = smoothness;
    s.occlusion = 1;
    s.emission = emission;
    s.alpha = 1;
    return UniversalFragmentPBR(id, s);
}

// --- Shadow caster / depth / depth-normals passes -----------------------------------------------

float3 _LightDirection;
float3 _LightPosition;

struct HexDepthAttributes
{
    float4 positionOS : POSITION;
    float3 normalOS : NORMAL;
};

struct HexDepthVaryings
{
    float4 positionCS : SV_POSITION;
    float3 normalWS : TEXCOORD0;
};

HexDepthVaryings HexShadowVert(HexDepthAttributes v)
{
    HexDepthVaryings o;
    float3 ws = TransformObjectToWorld(v.positionOS.xyz);
    float3 nws = TransformObjectToWorldNormal(v.normalOS);
#if _CASTING_PUNCTUAL_LIGHT_SHADOW
    float3 ld = normalize(_LightPosition - ws);
#else
    float3 ld = _LightDirection;
#endif
    float4 cs = TransformWorldToHClip(ApplyShadowBias(ws, nws, ld));
#if UNITY_REVERSED_Z
    cs.z = min(cs.z, UNITY_NEAR_CLIP_VALUE);
#else
    cs.z = max(cs.z, UNITY_NEAR_CLIP_VALUE);
#endif
    o.positionCS = cs;
    o.normalWS = nws;
    return o;
}

HexDepthVaryings HexDepthVert(HexDepthAttributes v)
{
    HexDepthVaryings o;
    o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
    o.normalWS = TransformObjectToWorldNormal(v.normalOS);
    return o;
}

half4 HexDepthFrag(HexDepthVaryings i) : SV_Target { return 0; }

half4 HexDepthNormalsFrag(HexDepthVaryings i) : SV_Target
{
    float3 n = normalize(i.normalWS);
#if defined(_GBUFFER_NORMALS_OCT)
    float2 oct = PackNormalOctQuadEncode(n);
    float2 rg = saturate(oct * 0.5 + 0.5);
    return half4(PackFloat2To888(rg), 0);
#else
    return half4(n, 0);
#endif
}

#endif
