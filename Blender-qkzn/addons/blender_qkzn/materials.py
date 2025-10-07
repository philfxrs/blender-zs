"""材质工具，负责读取预设并在 Blender 中创建材质。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union

from . import utils

try:
    import bpy
except ImportError:  # pragma: no cover - 测试环境无 bpy
    bpy = None  # type: ignore[assignment]

_PRESETS_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_PRESET_PATH = Path(__file__).parent / "presets" / "materials.json"


def _load_presets() -> Dict[str, Dict[str, Any]]:
    """加载 JSON 材质预设，采用懒加载缓存。"""

    global _PRESETS_CACHE
    if _PRESETS_CACHE is None:
        with _PRESET_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        _PRESETS_CACHE = {key: value for key, value in data.items()}
    return _PRESETS_CACHE


def _match_preset(name: str) -> Optional[Dict[str, Any]]:
    """根据中文名称或别名匹配预设。"""

    presets = _load_presets()
    lowered = name.lower()
    if lowered in presets:
        return presets[lowered]
    for preset in presets.values():
        for alias in preset.get("aliases", []):
            if alias.lower() == lowered:
                return preset
    return None


def ensure_material(name: str, principled: Optional[Dict[str, Any]] = None):
    """保证材质存在，并根据配置更新节点参数。"""

    if bpy is None:
        raise RuntimeError("当前环境缺少 bpy，无法创建材质")
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name=name)
        material.use_nodes = True
    if not material.use_nodes:
        material.use_nodes = True
    node_tree = material.node_tree
    if not node_tree:
        return material
    bsdf = node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    if principled:
        for key, value in principled.items():
            input_socket = bsdf.inputs.get(key)
            if input_socket is None:
                continue
            if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                sequence = list(value)
                if len(sequence) == 3:
                    sequence.append(1.0)
                input_socket.default_value = sequence  # type: ignore[assignment]
            else:
                input_socket.default_value = value  # type: ignore[assignment]
    return material


def apply_material(obj: Any, spec: Union[str, Dict[str, Any]]) -> None:
    """为对象应用材质，可通过预设或颜色词指定。"""

    if bpy is None:
        raise RuntimeError("当前环境缺少 bpy，无法应用材质")
    if obj is None:
        raise ValueError("未找到可应用材质的对象")

    principled: Optional[Dict[str, Any]] = None
    material_name = ""

    if isinstance(spec, str):
        color = utils.color_from_text(spec)
        if color:
            material_name = f"QKZN_Color_{spec}"
            principled = {"Base Color": (*color, 1.0)}
        else:
            preset = _match_preset(spec)
            if preset:
                material_name = preset["name"]
                principled = preset.get("principled")
            else:
                material_name = spec
    elif isinstance(spec, dict):
        material_name = spec.get("name", "QKZN_Custom")
        principled = spec.get("principled")
    else:
        raise TypeError("材质描述必须为字符串或字典")

    material = ensure_material(material_name or "QKZN_Default", principled)

    if obj.data is None:
        raise ValueError("当前对象没有几何数据，无法绑定材质")

    if material.name not in [slot.name for slot in obj.material_slots]:
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

    utils.get_logger(__name__).info("已为对象 %s 应用材质 %s", obj.name, material.name)
