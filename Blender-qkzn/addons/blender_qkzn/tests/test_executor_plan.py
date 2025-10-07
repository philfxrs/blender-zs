"""执行器执行顺序与异常处理测试。"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from blender_qkzn import executor
from blender_qkzn.schemas import Plan, PlanStep


def _prepare_fake_bpy() -> None:
    cube_add = MagicMock(name="cube_add")
    fake_mesh = SimpleNamespace(primitive_cube_add=cube_add)
    fake_ops = SimpleNamespace(mesh=fake_mesh)

    active_object = SimpleNamespace(
        name="TestObject",
        location=(0.0, 0.0, 0.0),
        material_slots=[],
        data=SimpleNamespace(materials=[]),
    )
    fake_context = SimpleNamespace(active_object=active_object)

    executor.bpy = SimpleNamespace(ops=fake_ops, context=fake_context)  # type: ignore[attr-defined]
    executor.materials.apply_material = MagicMock(name="apply_material")  # type: ignore[assignment]

    return cube_add, active_object


def test_execute_plan_success() -> None:
    cube_add, active_object = _prepare_fake_bpy()

    plan = Plan(
        steps=[
            PlanStep(op="mesh.primitive_cube_add", args={}),
            PlanStep(op="material.assign", args={"spec": "玻璃"}),
            PlanStep(op="object.move", args={"location": (1.0, 2.0, 3.0)}),
        ]
    )

    executor.execute_plan(plan)

    cube_add.assert_called_once()
    executor.materials.apply_material.assert_called_once_with(active_object, "玻璃")  # type: ignore[attr-defined]
    assert executor.bpy.context.active_object.location == (1.0, 2.0, 3.0)  # type: ignore[attr-defined]


def test_execute_plan_failure_raises() -> None:
    cube_add, _ = _prepare_fake_bpy()
    cube_add.side_effect = RuntimeError("boom")

    plan = Plan(steps=[PlanStep(op="mesh.primitive_cube_add", args={})])

    with pytest.raises(executor.ExecutionError):
        executor.execute_plan(plan)
