"""执行器模块：负责按顺序执行规划好的步骤。"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from . import materials, utils
from .schemas import Plan, PlanStep, validate_plan

try:
    import bpy
except ImportError:  # pragma: no cover - 测试环境无 bpy
    bpy = None  # type: ignore[assignment]


class ExecutionError(RuntimeError):
    """执行过程中的统一异常类型。"""


def _resolve_bpy_operator(path: str) -> Callable[..., Any]:
    """根据路径字符串获取 bpy 操作函数。"""

    if bpy is None:
        raise ExecutionError("当前环境缺少 bpy，无法执行操作")
    parts = path.split(".")
    target: Any = bpy.ops
    for part in parts:
        target = getattr(target, part)
    return target


def _execute_single_step(step: PlanStep) -> None:
    """执行单个步骤，支持内建操作与自定义伪操作。"""

    logger = utils.get_logger(__name__)
    logger.debug("执行步骤: %s", step)

    if step.op == "material.assign":
        if bpy is None:
            raise ExecutionError("缺少 bpy，无法应用材质")
        active_obj = bpy.context.active_object
        materials.apply_material(active_obj, step.args.get("spec"))
        return

    if step.op == "object.move":
        if bpy is None:
            raise ExecutionError("缺少 bpy，无法移动对象")
        active_obj = bpy.context.active_object
        if active_obj is None:
            raise ExecutionError("当前没有激活对象，无法移动")
        location = step.args.get("location")
        if not isinstance(location, Sequence):
            raise ExecutionError("移动指令缺少 location 参数")
        active_obj.location = location
        return

    operator = _resolve_bpy_operator(step.op)
    operator(**step.args)


def execute_plan(plan_input: Any) -> None:
    """执行计划并记录日志统计信息。"""

    plan: Plan = validate_plan(plan_input)
    logger = utils.get_logger(__name__)
    success = 0
    failed = 0

    for index, step in enumerate(plan.steps, start=1):
        try:
            _execute_single_step(step)
            success += 1
            logger.info("步骤 %d 成功: %s", index, step.op)
        except Exception as exc:  # pragma: no cover - 错误路径
            failed += 1
            logger.error("步骤 %d 失败 (%s): %s", index, step.op, exc)

    logger.info("计划执行完毕，总步骤 %d，成功 %d，失败 %d", len(plan.steps), success, failed)

    if failed:
        raise ExecutionError(f"计划执行存在失败步骤：成功 {success} / 失败 {failed}")
