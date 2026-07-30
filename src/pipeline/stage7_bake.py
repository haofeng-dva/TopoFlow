"""Stage 7：使用 Blender Cycles 烘焙贴图。"""

from pathlib import Path

from src.pipeline.stage5_uv import _import_statement
from src.tools.blender import run_blender_script


def _write_default_pbr_maps(directory: Path, resolution: int) -> dict:
    from PIL import Image
    defaults = {
        "basecolor": (180, 180, 180),
        "metallic": (0, 0, 0),
        "roughness": (153, 153, 153),
        "emission": (0, 0, 0),
    }
    outputs = {}
    for name, color in defaults.items():
        path = directory / f"{name}.png"
        Image.new("RGB", (resolution, resolution), color).save(path)
        outputs[name] = str(path)
    return outputs


def run(low_poly_uv_path: str, high_poly_path: str, strategy: dict, config: dict | None = None) -> dict:
    low = Path(low_poly_uv_path).expanduser().resolve()
    high = Path(high_poly_path).expanduser().resolve()
    if not low.is_file() or not high.is_file():
        raise FileNotFoundError("Stage 7 需要存在的高模和带 UV 低模")
    settings = config or {}
    resolution = int(strategy.get("bake_resolution", 2048))
    normal_space = strategy.get("normal_space", "directx")
    bake_margin = int(strategy.get("bake_margin", 8))
    bake_samples = int(strategy.get("bake_samples", 8))
    cage_extrusion = float(strategy.get("cage_extrusion", 0.02))
    maps_dir = low.parent / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)
    normal_path = maps_dir / f"normal_{'dx' if normal_space == 'directx' else 'gl'}.png"
    ao_path = maps_dir / "ao.png"
    curvature_path = maps_dir / "curvature.png"
    low_import = _import_statement(low)
    high_import = _import_statement(high)
    script = f'''
import bpy

def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def ensure_material(obj):
    material = bpy.data.materials.new(name=f"TopoFlow_{{obj.name}}")
    material.use_nodes = True
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return material

def image_node(material, name, color_space):
    nodes = material.node_tree.nodes
    node = nodes.new("ShaderNodeTexImage")
    image = bpy.data.images.new(name, width={resolution}, height={resolution}, alpha=False, float_buffer=False)
    image.colorspace_settings.name = color_space
    node.image = image
    nodes.active = node
    node.select = True
    return node, image

def save(image, path):
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()

clear()
{high_import}
high_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
for obj in high_objects: obj.name = "HIGH_" + obj.name
{low_import}
low_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and not obj.name.startswith("HIGH_")]
if not low_objects or not high_objects:
    raise RuntimeError("烘焙场景缺少高模或低模")
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = {bake_samples}
scene.render.image_settings.file_format = "PNG"
scene.render.bake.margin = {bake_margin}
scene.render.bake.use_clear = True

# Normal：高模到低模。
for low_obj in low_objects:
    material = ensure_material(low_obj)
    node, image = image_node(material, "TopoFlow_Normal", "Non-Color")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in high_objects: obj.select_set(True)
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = {cage_extrusion}
    scene.render.bake.normal_space = "TANGENT"
    bpy.ops.object.bake(type="NORMAL")
    save(image, {repr(str(normal_path))})
    break

# AO：低模自身遮蔽。
low_obj = low_objects[0]
material = low_obj.data.materials[0]
node, image = image_node(material, "TopoFlow_AO", "Non-Color")
bpy.ops.object.select_all(action="DESELECT")
low_obj.select_set(True)
bpy.context.view_layer.objects.active = low_obj
scene.render.bake.use_selected_to_active = False
bpy.ops.object.bake(type="AO")
save(image, {repr(str(ao_path))})

# Curvature：Cycles Pointiness 通过 Emit 烘焙。
scene.render.engine = "CYCLES"
material = ensure_material(low_obj)
nodes = material.node_tree.nodes
links = material.node_tree.links
nodes.clear()
output = nodes.new("ShaderNodeOutputMaterial")
emission = nodes.new("ShaderNodeEmission")
geometry = nodes.new("ShaderNodeNewGeometry")
image_node_curv, image_curv = image_node(material, "TopoFlow_Curvature", "Non-Color")
links.new(geometry.outputs["Pointiness"], emission.inputs["Color"])
links.new(emission.outputs["Emission"], output.inputs["Surface"])
nodes.active = image_node_curv
bpy.ops.object.bake(type="EMIT")
save(image_curv, {repr(str(curvature_path))})
'''
    print(f"[Stage 7] Blender 烘焙: {resolution}px, {normal_space}")
    blender_result = run_blender_script(
        script, str(low.parent),
        settings.get("blender_path", strategy.get("blender_path", "")),
        int(settings.get("worker_timeout", strategy.get("worker_timeout", 3600))),
    )
    outputs = {"normal": str(normal_path), "ao": str(ao_path), "curvature": str(curvature_path)}
    missing = [name for name, path in outputs.items() if not Path(path).is_file()]
    if missing:
        output_tail = (blender_result.stdout or blender_result.stderr or "")[-4000:]
        raise RuntimeError(f"Blender 未生成贴图: {', '.join(missing)}\n{output_tail}")
    outputs.update(_write_default_pbr_maps(maps_dir, resolution))
    return outputs
