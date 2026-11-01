# Sigil & Spark — "anime" look for the intro (user 2026-11-01: like a Black Clover opening: detailed 3D + 2D drawn look).
# M_PBX_AnimePP: post-process (after tonemapping) — ink outlines from depth + normals, cel light bands that keep the hue,
# saturation, manga hatching in the shadows. Used by the intro cameras (Sequencer) and testable with style_frame().
#   import pbx_anime as A; A.anime_pp(); A.style_frame('harbour')
import unreal, os

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
def log(*a): print('[anime]', *a)

HLSL = r'''
float2 uv = GetDefaultSceneTextureUV(Parameters, 14);
float2 px = View.ViewSizeAndInvSize.zw * Thick;
float3 c = SceneTextureLookup(uv, 14, false).rgb;
float d0 = SceneTextureLookup(uv, 1, false).r;
float3 n0 = SceneTextureLookup(uv, 8, false).rgb;
float ed = 0, en = 0;
float2 o[8] = { float2(1,0), float2(-1,0), float2(0,1), float2(0,-1), float2(1,1), float2(-1,1), float2(1,-1), float2(-1,-1) };
for (int i = 0; i < 8; i++)
{
    float2 u2 = uv + o[i] * px;
    float d = SceneTextureLookup(u2, 1, false).r;
    ed = max(ed, abs(d - d0) / max(min(d, d0), 1.0));
    float3 n = SceneTextureLookup(u2, 8, false).rgb;
    en = max(en, 1.0 - saturate(dot(n * 2 - 1, n0 * 2 - 1)));
}
float edge = saturate(max(smoothstep(DepthT, DepthT * 3, ed), smoothstep(NormT, NormT * 2.5, en)));
edge *= saturate(1.0 - d0 / FadeDist);
float l = dot(c, float3(0.299, 0.587, 0.114));
float lb = floor(l * Bands + 0.5) / Bands;
float ls = lerp(l, lb, Cel);
float3 col = c * (ls / max(l, 1e-4));
float g = dot(col, float3(0.299, 0.587, 0.114));
col = lerp(g.xxx, col, Sat);
float2 sp = uv * View.ViewSizeAndInvSize.xy;
float hatch = step(0.5, frac((sp.x + sp.y) / HatchPx));
float shadow = saturate((HatchL - l) / HatchL);
col *= lerp(1.0, 0.72 + 0.28 * hatch, shadow * HatchAmt);
col = lerp(col, InkColor, edge * InkAmt);
return col + Dummy * 0;
'''

PARAMS = {'Thick': 1.25, 'DepthT': 0.02, 'NormT': 0.55, 'FadeDist': 90000.0, 'Bands': 4.0, 'Cel': 0.45, 'Sat': 1.35,
          'HatchPx': 5.0, 'HatchL': 0.2, 'HatchAmt': 0.55, 'InkAmt': 0.85}

def anime_pp(rebuild=False):
    path = '/Game/PBX/Materials/M_PBX_AnimePP'
    if EAL.does_asset_exist(path) and not rebuild: return unreal.load_asset(path)
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_PBX_AnimePP', '/Game/PBX/Materials', unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
    m.set_editor_property('blendable_location', unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    cu = MEL.create_material_expression(m, unreal.MaterialExpressionCustom, -300, 0)
    cu.set_editor_property('code', HLSL)
    cu.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    names = list(PARAMS) + ['InkColor', 'Dummy']
    ins = []
    for n in names:
        ci = unreal.CustomInput(); ci.set_editor_property('input_name', n); ins.append(ci)
    cu.set_editor_property('inputs', ins)
    y = -600
    for n, v in PARAMS.items():
        p = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -800, y); y += 70
        p.set_editor_property('parameter_name', n); p.set_editor_property('default_value', v)
        MEL.connect_material_expressions(p, '', cu, n)
    ic = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -800, y)
    ic.set_editor_property('parameter_name', 'InkColor'); ic.set_editor_property('default_value', unreal.LinearColor(0.06, 0.035, 0.03, 1))
    MEL.connect_material_expressions(ic, '', cu, 'InkColor')
    st = MEL.create_material_expression(m, unreal.MaterialExpressionSceneTexture, -800, y + 120)
    st.set_editor_property('scene_texture_id', unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    MEL.connect_material_expressions(st, 'Color', cu, 'Dummy')
    MEL.connect_material_property(cu, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    log('anime pp built')
    return m

def _cam(loc, look, fov=40.0, pp=True):
    w = unreal.EditorLevelLibrary.get_editor_world()
    rot = unreal.MathLibrary.find_look_at_rotation(loc, look)
    c = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, loc, rot)
    cc = c.get_cine_camera_component()
    cc.set_editor_property('current_focal_length', 36.0 / (2 * __import__('math').tan(__import__('math').radians(fov) / 2)) * 1.0)
    fs = cc.get_editor_property('focus_settings'); fs.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE); cc.set_editor_property('focus_settings', fs)
    if pp:
        s = cc.get_editor_property('post_process_settings')
        wb = unreal.WeightedBlendable(); wb.set_editor_property('weight', 1.0); wb.set_editor_property('object', anime_pp())
        arr = unreal.WeightedBlendables(); arr.set_editor_property('array', [wb]); s.set_editor_property('weighted_blendables', arr)
        s.set_editor_property('override_auto_exposure_method', True); s.set_editor_property('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL)
        s.set_editor_property('override_auto_exposure_bias', True); s.set_editor_property('auto_exposure_bias', EXPOSURE)
        cc.set_editor_property('post_process_settings', s)
    return c

EXPOSURE = 10.5

FRAMES = {   # name: (camera loc, look at, fov) in UE cm
    'harbour': (unreal.Vector(-6500, 9000, 4200), unreal.Vector(-500, -1500, 0), 50.0),
    'plaza': (unreal.Vector(1500, 1800, 700), unreal.Vector(-600, 3300, 300), 50.0),
}

def style_frame(name='harbour', pp=True, out=None):
    loc, look, fov = FRAMES[name]
    c = _cam(loc, look, fov, pp)
    out = out or unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + f'anime_{name}{"" if pp else "_raw"}.png'
    unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, out, c)
    log('shot ->', out)
    return c, out

def exposure_sweep(name='harbour', biases=(8.5, 10.0, 11.5)):
    global EXPOSURE
    outs = []
    for b in biases:
        EXPOSURE = b; c, o = style_frame(name, True, unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + f'anime_{name}_ev{b}.png'); outs.append(o)
    return outs
