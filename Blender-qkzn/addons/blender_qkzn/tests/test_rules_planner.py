"""规划器规则解析的单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from blender_qkzn import planner_client


def test_parse_cube_with_material() -> None:
    plan = planner_client.parse_command("添加一个立方体并应用玻璃材质")
    ops = [step.op for step in plan.steps]
    assert ops == ["mesh.primitive_cube_add", "material.assign"]
    assert plan.steps[1].args["spec"] == "玻璃"


def test_parse_sphere_move() -> None:
    plan = planner_client.parse_command("添加一个蓝色球体，移动到 X1 Y-2 Z0.5")
    ops = [step.op for step in plan.steps]
    assert ops == [
        "mesh.primitive_uv_sphere_add",
        "material.assign",
        "object.move",
    ]
    assert plan.steps[1].args["spec"] == "蓝色"
    assert plan.steps[2].args["location"] == (1.0, -2.0, 0.5)


def test_parse_multi_shape_materials() -> None:
    text = "添加一个木纹材质的立方体，再添加一个金属球体"
    plan = planner_client.parse_command(text)
    ops = [step.op for step in plan.steps]
    assert ops == [
        "mesh.primitive_cube_add",
        "material.assign",
        "mesh.primitive_uv_sphere_add",
        "material.assign",
    ]
    assert plan.steps[1].args["spec"] == "木纹"
    assert plan.steps[3].args["spec"] == "金属"
