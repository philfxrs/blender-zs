bl_info = {
    "name": "Natural Language Modeling Assistant",
    "author": "OpenAI Assistant",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > NL Modeler",
    "description": "Generate and edit objects via natural language prompts.",
    "category": "3D View",
}

import bpy
import json
import math
import re
from mathutils import Vector


UNIT_MAP = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "米": 1.0,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "厘米": 0.01,
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "毫米": 0.001,
}

COLOR_KEYWORDS = {
    "red": (1.0, 0.0, 0.0),
    "红": (1.0, 0.0, 0.0),
    "blue": (0.0, 0.4, 1.0),
    "蓝": (0.0, 0.4, 1.0),
    "green": (0.0, 0.8, 0.2),
    "绿": (0.0, 0.8, 0.2),
    "yellow": (1.0, 0.9, 0.1),
    "黄": (1.0, 0.9, 0.1),
    "white": (0.95, 0.95, 0.95),
    "白": (0.95, 0.95, 0.95),
    "black": (0.05, 0.05, 0.05),
    "黑": (0.05, 0.05, 0.05),
    "gray": (0.5, 0.5, 0.5),
    "grey": (0.5, 0.5, 0.5),
    "灰": (0.5, 0.5, 0.5),
    "orange": (1.0, 0.5, 0.0),
    "橙": (1.0, 0.5, 0.0),
    "purple": (0.6, 0.2, 0.7),
    "紫": (0.6, 0.2, 0.7),
    "pink": (1.0, 0.5, 0.7),
    "粉": (1.0, 0.5, 0.7),
    "brown": (0.4, 0.25, 0.1),
    "棕": (0.4, 0.25, 0.1),
}

MATERIAL_KEYWORDS = {
    "wood": ["wood", "木", "木质", "木头"],
    "metal": ["metal", "金属"],
    "glass": ["glass", "玻璃"],
}

TEMPLATE_KEYWORDS = {
    "cube": ["cube", "立方", "方块", "正方体"],
    "sphere": ["sphere", "球", "球体"],
    "cylinder": ["cylinder", "圆柱"],
    "cone": ["cone", "圆锥"],
    "torus": ["torus", "圆环"],
    "plane": ["plane", "平面"],
    "table": ["table", "桌", "桌子", "餐桌"],
    "bookshelf": ["bookshelf", "书架", "书柜"],
}


def convert_value(value_str, unit_str):
    try:
        value = float(value_str)
    except ValueError:
        return None
    if unit_str:
        unit_str = unit_str.lower()
        value *= UNIT_MAP.get(unit_str, 1.0)
    return value


def ensure_material(name, preset=None, color=None):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    principled = None
    if mat.node_tree:
        principled = mat.node_tree.nodes.get("Principled BSDF")
        if principled is None:
            principled = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
            output = mat.node_tree.nodes.get("Material Output")
            if output is None:
                output = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
            mat.node_tree.links.new(principled.outputs[0], output.inputs[0])
    if principled:
        base_color = principled.inputs.get("Base Color")
        metallic = principled.inputs.get("Metallic")
        roughness = principled.inputs.get("Roughness")
        transmission = principled.inputs.get("Transmission")
        ior = principled.inputs.get("IOR")
        if preset == "wood":
            if base_color:
                base_color.default_value = (0.6, 0.4, 0.2, 1.0)
            if roughness:
                roughness.default_value = 0.6
            if metallic:
                metallic.default_value = 0.0
        elif preset == "metal":
            if base_color:
                base_color.default_value = (0.8, 0.8, 0.8, 1.0)
            if metallic:
                metallic.default_value = 1.0
            if roughness:
                roughness.default_value = 0.2
        elif preset == "glass":
            if base_color:
                base_color.default_value = (0.9, 0.95, 1.0, 1.0)
            if transmission:
                transmission.default_value = 0.95
            if ior:
                ior.default_value = 1.45
            if roughness:
                roughness.default_value = 0.1
            if metallic:
                metallic.default_value = 0.0
        if color and base_color:
            base_color.default_value = (*color, 1.0)
        if color and roughness:
            roughness.default_value = 0.4
    return mat


def box_geometry(width, depth, height, center):
    cx, cy, cz = center
    w2 = width / 2.0
    d2 = depth / 2.0
    h2 = height / 2.0
    verts = [
        (cx - w2, cy - d2, cz - h2),
        (cx + w2, cy - d2, cz - h2),
        (cx + w2, cy + d2, cz - h2),
        (cx - w2, cy + d2, cz - h2),
        (cx - w2, cy - d2, cz + h2),
        (cx + w2, cy - d2, cz + h2),
        (cx + w2, cy + d2, cz + h2),
        (cx - w2, cy + d2, cz + h2),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    return verts, faces


def build_mesh_object(name, boxes, context):
    verts_all = []
    faces_all = []
    for verts, faces in boxes:
        offset = len(verts_all)
        verts_all.extend(verts)
        for face in faces:
            faces_all.append(tuple(index + offset for index in face))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts_all, [], faces_all)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    context.collection.objects.link(obj)
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj


def create_table_object(context, width=2.0, depth=1.0, height=1.0):
    top_thickness = max(0.05, min(height * 0.15, height * 0.3))
    leg_size = max(0.05, min(width, depth) * 0.15)
    leg_height = max(0.1, height - top_thickness)
    half_height = height / 2.0
    bottom_z = -half_height
    top_z = half_height
    top_center_z = top_z - top_thickness / 2.0
    leg_center_z = bottom_z + leg_height / 2.0
    boxes = []
    boxes.append(box_geometry(width, depth, top_thickness, (0.0, 0.0, top_center_z)))
    offsets = [
        (width / 2.0 - leg_size / 2.0, depth / 2.0 - leg_size / 2.0),
        (-width / 2.0 + leg_size / 2.0, depth / 2.0 - leg_size / 2.0),
        (width / 2.0 - leg_size / 2.0, -depth / 2.0 + leg_size / 2.0),
        (-width / 2.0 + leg_size / 2.0, -depth / 2.0 + leg_size / 2.0),
    ]
    for ox, oy in offsets:
        boxes.append(box_geometry(leg_size, leg_size, leg_height, (ox, oy, leg_center_z)))
    return build_mesh_object("NL_Table", boxes, context)


def create_bookshelf_object(context, width=1.0, depth=0.3, height=2.0, shelves=4):
    frame_thickness = max(0.03, min(width, depth) * 0.08)
    shelf_thickness = max(0.02, frame_thickness * 0.8)
    back_thickness = max(0.01, min(depth * 0.3, frame_thickness))
    half_height = height / 2.0
    bottom_z = -half_height
    top_z = half_height
    inner_width = max(frame_thickness * 0.5, width - frame_thickness * 2.0)
    inner_depth = max(frame_thickness, depth - frame_thickness * 1.5)
    boxes = []
    boxes.append(
        box_geometry(
            frame_thickness,
            depth,
            height,
            (-width / 2.0 + frame_thickness / 2.0, 0.0, 0.0),
        )
    )
    boxes.append(
        box_geometry(
            frame_thickness,
            depth,
            height,
            (width / 2.0 - frame_thickness / 2.0, 0.0, 0.0),
        )
    )
    boxes.append(
        box_geometry(
            width - frame_thickness * 2.0,
            depth,
            frame_thickness,
            (0.0, 0.0, top_z - frame_thickness / 2.0),
        )
    )
    boxes.append(
        box_geometry(
            width - frame_thickness * 2.0,
            depth,
            frame_thickness,
            (0.0, 0.0, bottom_z + frame_thickness / 2.0),
        )
    )
    boxes.append(
        box_geometry(
            width - frame_thickness * 0.5,
            back_thickness,
            height - frame_thickness,
            (0.0, -depth / 2.0 + back_thickness / 2.0, frame_thickness / 2.0),
        )
    )
    if shelves > 0:
        usable_height = height - frame_thickness * 2.0
        for i in range(1, shelves + 1):
            factor = i / (shelves + 1)
            shelf_z = bottom_z + frame_thickness + usable_height * factor
            boxes.append(
                box_geometry(
                    inner_width,
                    inner_depth,
                    shelf_thickness,
                    (0.0, frame_thickness * 0.25, shelf_z),
                )
            )
    return build_mesh_object("NL_Bookshelf", boxes, context)


def parse_prompt_heuristic(prompt):
    result = {
        "template": "cube",
    }
    text = prompt.strip()
    if not text:
        return result
    lower = text.lower()
    for template, keywords in TEMPLATE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lower or keyword in text:
                result["template"] = template
                break
        if result["template"] == template:
            break
    if re.search(r"贴地|吸附地面|snap\s*to\s*ground|落地", text, re.IGNORECASE):
        result["snap_to_ground"] = True
    array_match = re.search(r"阵列\s*(\d+)\s*[x×]\s*(\d+)\s*[x×]\s*(\d+)", text, re.IGNORECASE)
    if array_match:
        result["array"] = [int(array_match.group(i)) for i in range(1, 4)]
    else:
        array_match_en = re.search(r"array\s*(\d+)\s*[x×]\s*(\d+)\s*[x×]\s*(\d+)", lower)
        if array_match_en:
            result["array"] = [int(array_match_en.group(i)) for i in range(1, 4)]
    material_found = None
    for preset, keywords in MATERIAL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text or keyword in lower:
                material_found = {"preset": preset}
                break
        if material_found:
            break
    if material_found:
        result["material"] = material_found
    color_match = None
    for keyword, color in COLOR_KEYWORDS.items():
        if keyword in text or keyword in lower:
            color_match = color
            break
    hex_match = re.search(r"#([0-9a-fA-F]{6})", text)
    if hex_match:
        hex_value = hex_match.group(1)
        color_match = tuple(int(hex_value[i:i + 2], 16) / 255.0 for i in range(0, 6, 2))
    if color_match:
        result.setdefault("material", {})
        result["material"]["color"] = list(color_match)
    dimension_patterns = {
        "width": ["宽度", "宽", "width", "长"],
        "depth": ["深度", "深", "depth"],
        "height": ["高度", "高", "height"],
        "radius": ["半径", "radius"],
        "diameter": ["直径", "diameter"],
        "size": ["尺寸", "size"],
    }
    for key, keywords in dimension_patterns.items():
        for keyword in keywords:
            pattern = rf"{keyword}[是为:=\s]*([-+]?\d*\.?\d+)(?:\s*(m|cm|mm|米|厘米|毫米))?"
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                value = convert_value(matches[-1].group(1), matches[-1].group(2))
                if value is not None:
                    result[key] = value
                break
    if "diameter" in result and "radius" not in result:
        result["radius"] = result["diameter"] / 2.0
    shelf_match = re.search(r"(层|隔板|shelves?)\D*(\d+)", text, re.IGNORECASE)
    if shelf_match:
        result["shelves"] = int(shelf_match.group(2))
    pos_match = re.search(r"位置[是为:=\s]*([-,\d\.\s米厘米毫米mcm]+)", text, re.IGNORECASE)
    if pos_match:
        coords = re.findall(r"([-+]?\d*\.?\d+)(?:\s*(m|cm|mm|米|厘米|毫米))?", pos_match.group(1))
        if len(coords) >= 3:
            result["location"] = [convert_value(num, unit) or 0.0 for num, unit in coords[:3]]
    else:
        pos_match_en = re.search(r"location[is:=\s]*([-,\d\.\s米厘米毫米mcm]+)", text, re.IGNORECASE)
        if pos_match_en:
            coords = re.findall(r"([-+]?\d*\.?\d+)(?:\s*(m|cm|mm|米|厘米|毫米))?", pos_match_en.group(1))
            if len(coords) >= 3:
                result["location"] = [convert_value(num, unit) or 0.0 for num, unit in coords[:3]]
    axis_patterns = {
        "x": [r"x\s*[:=]?", r"x轴", r"沿x", r"x\s*axis", r"沿\s*x"],
        "y": [r"y\s*[:=]?", r"y轴", r"沿y", r"y\s*axis", r"沿\s*y"],
        "z": [r"z\s*[:=]?", r"z轴", r"沿z", r"高度", r"z\s*axis", r"沿\s*z"],
    }
    for axis, patterns in axis_patterns.items():
        for pattern in patterns:
            regex = rf"{pattern}\s*([-+]?\d*\.?\d+)(?:\s*(m|cm|mm|米|厘米|毫米))?"
            match = re.search(regex, text, re.IGNORECASE)
            if match:
                result[f"location_{axis}"] = convert_value(match.group(1), match.group(2))
                break
    rot_match = re.search(r"旋转[是为:=\s]*([-,\d\.\s度deg]+)", text, re.IGNORECASE)
    if rot_match:
        values = re.findall(r"([-+]?\d*\.?\d+)", rot_match.group(1))
        if len(values) >= 3:
            result["rotation"] = [float(v) for v in values[:3]]
    for axis in ("x", "y", "z"):
        match = re.search(rf"(?:绕?{axis}轴旋转|{axis}\s*rot(?:ation)?)\s*([-+]?\d*\.?\d+)", lower)
        if match:
            result.setdefault("rotation_axes", {})[axis] = float(match.group(1))
    scale_match = re.search(r"缩放[是为:=\s]*([-,\d\.\s]+)", text, re.IGNORECASE)
    if scale_match:
        values = re.findall(r"([-+]?\d*\.?\d+)", scale_match.group(1))
        if len(values) == 1:
            result["scale"] = float(values[0])
        elif len(values) >= 3:
            result["scale_xyz"] = [float(v) for v in values[:3]]
    uniform_match = re.search(r"scale\s*([-+]?\d*\.?\d+)", lower)
    if uniform_match:
        result["scale"] = float(uniform_match.group(1))
    for axis in ("x", "y", "z"):
        match = re.search(rf"scale\s*{axis}\s*([-+]?\d*\.?\d+)", lower)
        if match:
            result.setdefault("scale_axes", {})[axis] = float(match.group(1))
    return result


def align_object_to_ground(obj):
    min_z = min((obj.matrix_world @ Vector(corner)).z for corner in obj.bound_box)
    obj.location.z -= min_z


def set_object_dimensions(obj, data):
    target_map = {
        "width": 0,
        "depth": 1,
        "height": 2,
    }
    dims = obj.dimensions.copy()
    if "size" in data:
        size_target = data["size"]
        if size_target > 0:
            base_scale = list(obj.scale)
            for axis in range(3):
                if dims[axis] > 0:
                    base_scale[axis] *= size_target / dims[axis]
            obj.scale = base_scale
            dims = obj.dimensions.copy()
    for key, axis in target_map.items():
        if key in data and dims[axis] > 0:
            factor = data[key] / dims[axis]
            scale = list(obj.scale)
            scale[axis] *= factor
            obj.scale = scale
            dims = obj.dimensions.copy()
    if "radius" in data and obj.dimensions.x > 0 and obj.dimensions.y > 0:
        radius_target = data["radius"]
        if radius_target > 0:
            current_radius_x = obj.dimensions.x / 2.0
            current_radius_y = obj.dimensions.y / 2.0
            scale = list(obj.scale)
            if current_radius_x > 0:
                scale[0] *= radius_target / current_radius_x
            if current_radius_y > 0:
                scale[1] *= radius_target / current_radius_y
            obj.scale = scale


def apply_material_to_object(obj, material_data):
    if not material_data:
        return
    preset = material_data.get("preset")
    color = material_data.get("color")
    name_parts = ["NL_Material"]
    if preset:
        name_parts.append(preset.title())
    if color:
        name_parts.append("Color")
    mat = ensure_material("_".join(name_parts), preset=preset, color=tuple(color) if color else None)
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def apply_transforms(obj, data):
    if "scale" in data:
        factor = data["scale"]
        base_scale = list(obj.scale)
        obj.scale = [component * factor for component in base_scale]
    if "scale_xyz" in data:
        base_scale = list(obj.scale)
        obj.scale = [base_scale[i] * data["scale_xyz"][i] for i in range(3)]
    if "scale_axes" in data:
        scale = list(obj.scale)
        for axis, value in data["scale_axes"].items():
            index = "xyz".index(axis)
            scale[index] *= value
        obj.scale = scale
    set_object_dimensions(obj, data)
    if "location" in data:
        obj.location = Vector(data["location"])
    for axis in "xyz":
        key = f"location_{axis}"
        if key in data:
            index = "xyz".index(axis)
            loc = list(obj.location)
            loc[index] = data[key]
            obj.location = Vector(loc)
    if "rotation" in data:
        obj.rotation_euler = [math.radians(v) for v in data["rotation"]]
    if "rotation_axes" in data:
        rot = list(obj.rotation_euler)
        for axis, value in data["rotation_axes"].items():
            index = "xyz".index(axis)
            rot[index] = math.radians(value)
        obj.rotation_euler = rot


def add_primitive_from_cmd(context, data):
    template = data.get("template", "cube")
    try:
        if template == "cube":
            bpy.ops.mesh.primitive_cube_add(size=1)
            obj = context.active_object
        elif template == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, segments=32, ring_count=16)
            obj = context.active_object
        elif template == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1.0)
            obj = context.active_object
        elif template == "cone":
            bpy.ops.mesh.primitive_cone_add(radius1=0.5, depth=1.0)
            obj = context.active_object
        elif template == "torus":
            bpy.ops.mesh.primitive_torus_add()
            obj = context.active_object
        elif template == "plane":
            bpy.ops.mesh.primitive_plane_add(size=1)
            obj = context.active_object
        elif template == "table":
            width = data.get("width", 2.0)
            depth = data.get("depth", 1.0)
            height = data.get("height", 1.0)
            obj = create_table_object(context, width, depth, height)
        elif template == "bookshelf":
            width = data.get("width", 1.2)
            depth = data.get("depth", 0.3)
            height = data.get("height", 2.0)
            shelves = int(data.get("shelves", 4))
            obj = create_bookshelf_object(context, width, depth, height, shelves)
        else:
            bpy.ops.mesh.primitive_cube_add(size=1)
            obj = context.active_object
    except RuntimeError as exc:
        raise RuntimeError(f"无法创建几何体: {exc}")
    if obj is None:
        raise RuntimeError("对象创建失败")
    obj.name = f"NL_{template.title()}"
    apply_transforms(obj, data)
    apply_material_to_object(obj, data.get("material"))
    if data.get("snap_to_ground"):
        align_object_to_ground(obj)
    context.view_layer.update()
    created_objects = [obj]
    if "array" in data:
        counts = data["array"]
        if len(counts) == 3 and any(c > 1 for c in counts):
            dims = obj.dimensions.copy()
            spacing = Vector((dims.x if dims.x > 0 else 1.0, dims.y if dims.y > 0 else 1.0, dims.z if dims.z > 0 else 1.0))
            base_location = Vector(obj.location)
            for ix in range(counts[0]):
                for iy in range(counts[1]):
                    for iz in range(counts[2]):
                        if ix == 0 and iy == 0 and iz == 0:
                            continue
                        duplicate = obj.copy()
                        duplicate.data = obj.data.copy()
                        context.collection.objects.link(duplicate)
                        offset = Vector((ix * spacing.x, iy * spacing.y, iz * spacing.z))
                        duplicate.location = base_location + offset
                        apply_material_to_object(duplicate, data.get("material"))
                        created_objects.append(duplicate)
            context.view_layer.update()
    return created_objects[0]


def find_target_object(context):
    obj = context.active_object
    if obj:
        return obj
    last_name = getattr(context.scene, "nl_modeler_last_created", "")
    if last_name:
        return context.scene.objects.get(last_name)
    return None


def update_last_created(scene, obj):
    if obj:
        scene.nl_modeler_last_created = obj.name


class NLModelerProperties(bpy.types.PropertyGroup):
    prompt: bpy.props.StringProperty(name="Prompt", description="Natural language prompt", default="", options={"MULTILINE"})


class NLAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    mock_api_key: bpy.props.StringProperty(name="Mock API Key", subtype='PASSWORD', description="占位字段，无需真实联网")

    def draw(self, context):
        layout = self.layout
        layout.label(text="Natural Language Modeling Assistant 偏好设置")
        layout.prop(self, "mock_api_key")


class NL_OT_generate(bpy.types.Operator):
    bl_idname = "nl_modeler.generate_from_prompt"
    bl_label = "Generate from Prompt"
    bl_description = "根据自然语言提示生成几何体"

    def execute(self, context):
        prompt = context.scene.nl_modeler_props.prompt
        data = parse_prompt_heuristic(prompt)
        try:
            obj = add_primitive_from_cmd(context, data)
        except Exception as exc:  # noqa: BLE001
            self.report({'ERROR'}, f"生成失败: {exc}")
            return {'CANCELLED'}
        update_last_created(context.scene, obj)
        self.report({'INFO'}, f"已生成 {obj.name}")
        return {'FINISHED'}


class NL_OT_edit(bpy.types.Operator):
    bl_idname = "nl_modeler.edit_from_prompt"
    bl_label = "Edit from Prompt"
    bl_description = "根据自然语言提示编辑选中对象或最后生成对象"

    def execute(self, context):
        target = find_target_object(context)
        if target is None:
            self.report({'ERROR'}, "未找到可编辑对象")
            return {'CANCELLED'}
        prompt = context.scene.nl_modeler_props.prompt
        data = parse_prompt_heuristic(prompt)
        try:
            apply_transforms(target, data)
            apply_material_to_object(target, data.get("material"))
            if data.get("snap_to_ground"):
                align_object_to_ground(target)
            context.view_layer.update()
        except Exception as exc:  # noqa: BLE001
            self.report({'ERROR'}, f"编辑失败: {exc}")
            return {'CANCELLED'}
        update_last_created(context.scene, target)
        self.report({'INFO'}, f"已编辑 {target.name}")
        return {'FINISHED'}


class NL_PT_panel(bpy.types.Panel):
    bl_label = "NL Modeler"
    bl_idname = "NL_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "NL Modeler"

    def draw(self, context):
        layout = self.layout
        props = context.scene.nl_modeler_props
        layout.prop(props, "prompt", text="")
        row = layout.row(align=True)
        row.operator(NL_OT_generate.bl_idname, icon='ADD')
        row.operator(NL_OT_edit.bl_idname, icon='MODIFIER')
        box = layout.box()
        box.label(text="解析结果：")
        data = parse_prompt_heuristic(props.prompt)
        preview = json.dumps(data, ensure_ascii=False, indent=2)
        for line in preview.splitlines():
            box.label(text=line)
        last_created = context.scene.nl_modeler_last_created
        if last_created:
            layout.label(text=f"最后生成：{last_created}")


CLASSES = (
    NLModelerProperties,
    NLAddonPreferences,
    NL_OT_generate,
    NL_OT_edit,
    NL_PT_panel,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.nl_modeler_props = bpy.props.PointerProperty(type=NLModelerProperties)
    bpy.types.Scene.nl_modeler_last_created = bpy.props.StringProperty(name="Last Created Object", default="")


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, "nl_modeler_props"):
        del bpy.types.Scene.nl_modeler_props
    if hasattr(bpy.types.Scene, "nl_modeler_last_created"):
        del bpy.types.Scene.nl_modeler_last_created


if __name__ == "__main__":
    register()

# 安装与验证步骤
# 1. 在 Blender 中打开 编辑 > 首选项 > 插件，点击“安装...”，选择本文件。
# 2. 勾选“Natural Language Modeling Assistant”启用插件，在 3D 视图侧栏找到“NL Modeler”面板。
# 3. 在 Prompt 文本框输入描述，点击“Generate from Prompt”或“Edit from Prompt”验证生成与编辑功能。
# 可用 Prompt 示例（至少 3 条）
# - "创建一张木质餐桌，宽 2m 深 1m 高 0.75m，贴地，阵列 2x1x1。"
# - "书架，宽 1.2m 高 2.2m 深 0.35m，5 层，颜色 #ffcc66，贴地。"
# - "将选中物体改成金属材质，缩放 1.5，旋转 0 45 0 并吸附地面。"
