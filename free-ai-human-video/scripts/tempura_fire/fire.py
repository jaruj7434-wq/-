"""Mantaflow(Blender 内蔵の流体シミュレーション)で、本物の物理計算による炎と煙を作るヘルパー。"""
import bpy

from kit import key


def fire_material(name="Fire", smoke_density=0.6, flame_strength=6.0, smoke_color=(0.08, 0.075, 0.07)):
    """炎(黒体放射の色)と煙を表すボリューム素材。"""
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    n, l = mat.node_tree.nodes, mat.node_tree.links
    n.remove(n["Principled BSDF"])
    vol = n.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (*smoke_color, 1)
    vol.inputs["Temperature"].default_value = 1400.0
    dens = n.new("ShaderNodeAttribute")
    dens.attribute_name = "density"
    flame = n.new("ShaderNodeAttribute")
    flame.attribute_name = "flame"
    dmul = n.new("ShaderNodeMath")
    dmul.operation = "MULTIPLY"
    dmul.inputs[1].default_value = smoke_density
    l.new(dens.outputs["Fac"], dmul.inputs[0])
    l.new(dmul.outputs[0], vol.inputs["Density"])
    fmul = n.new("ShaderNodeMath")
    fmul.operation = "MULTIPLY"
    fmul.inputs[1].default_value = flame_strength
    l.new(flame.outputs["Fac"], fmul.inputs[0])
    l.new(fmul.outputs[0], vol.inputs["Blackbody Intensity"])
    # 炎の温度が高いところほど白っぽく(黒体放射の温度を炎の濃さで変える)
    tmap = n.new("ShaderNodeMapRange")
    tmap.inputs["To Min"].default_value = 900.0
    tmap.inputs["To Max"].default_value = 1800.0
    l.new(flame.outputs["Fac"], tmap.inputs["Value"])
    l.new(tmap.outputs["Result"], vol.inputs["Temperature"])
    l.new(vol.outputs[0], n["Material Output"].inputs["Volume"])
    return mat


def domain(scene, loc, size, resolution, cache_dir, frame_end, time_scale=1.0, noise=True, vorticity=0.25,
           material=None):
    """シミュレーションの空間(箱)。この中だけで炎と煙が計算・描画される。"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    dom = bpy.context.active_object
    dom.name = "FireDomain"
    dom.scale = size
    bpy.ops.object.transform_apply(scale=True)
    mod = dom.modifiers.new("Fluid", "FLUID")
    mod.fluid_type = "DOMAIN"
    ds = mod.domain_settings
    ds.domain_type = "GAS"
    ds.resolution_max = resolution
    ds.cache_directory = str(cache_dir)
    ds.cache_type = "ALL"
    ds.cache_frame_start, ds.cache_frame_end = 1, frame_end
    ds.time_scale = time_scale
    ds.vorticity = vorticity
    ds.use_adaptive_domain = False
    ds.burning_rate = 0.75
    ds.flame_smoke = 1.0
    ds.flame_vorticity = 0.5
    ds.alpha = 1.0        # 密度による浮力
    ds.beta = 1.0         # 熱による浮力
    ds.use_dissolve_smoke = True
    ds.dissolve_speed = 40
    if noise:
        ds.use_noise = True
        ds.noise_scale = 2
        ds.noise_strength = 1.2
    dom.data.materials.append(material or fire_material())
    return dom, ds


def flow(obj, fuel=1.0, temp=2.0, surface=0.15, kind="FIRE", velocity=None, density=0.6):
    """obj を燃料の出る場所(炎の発生源)にする。fuel_amount をキーフレームで動かせる。"""
    mod = obj.modifiers.new("Fluid", "FLUID")
    mod.fluid_type = "FLOW"
    fs = mod.flow_settings
    fs.flow_type = kind
    fs.flow_behavior = "INFLOW"
    fs.flow_source = "MESH"
    fs.surface_distance = surface
    fs.fuel_amount = fuel
    fs.temperature = temp
    fs.density = density
    if velocity is not None:
        fs.use_initial_velocity = True
        fs.velocity_coord = velocity
    obj.hide_render = True
    return fs


def key_flow(fs, frame, **values):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "CONSTANT"
    for k, v in values.items():
        setattr(fs, k, v)
        fs.keyframe_insert(k, frame=frame)


def bake(dom):
    """シミュレーションを最後まで計算してキャッシュに書き出す。"""
    with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom], selected_editable_objects=[dom]):
        bpy.ops.fluid.bake_all()
