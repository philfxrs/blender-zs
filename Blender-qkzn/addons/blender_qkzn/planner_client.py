"""规划器模块：将中文自然语言解析为 Blender 可执行计划。"""

from __future__ import annotations

import re
from typing import List, Optional

from . import llm_client, utils
from .schemas import LLMConfig, Plan, PlanStep, validate_plan


_COLOR_PATTERN = "|".join(utils.available_color_words())
_MATERIAL_PATTERN = "玻璃|金属|木纹|塑料"

_ADD_CUBE_RE = re.compile(
    rf"添加(?:一个)?(?:(?P<material>{_MATERIAL_PATTERN})材质的)?(?:(?P<color>{_COLOR_PATTERN})的?)?(立方体|方块|cube)",
    re.IGNORECASE,
)
_ADD_SPHERE_RE = re.compile(
    rf"添加(?:一个)?(?:(?P<material>{_MATERIAL_PATTERN})(?:材质)?的?)?(?:(?P<color>{_COLOR_PATTERN})的?)?(球体|圆球)",
    re.IGNORECASE,
)
_APPLY_MATERIAL_RE = re.compile(
    rf"应用(?:.*?)(?P<material>{_MATERIAL_PATTERN})(?:材质)?",
    re.IGNORECASE,
)
_MOVE_RE = re.compile(
    r"移动到\s*X(?P<x>-?\d+(?:\.\d+)?)\s*Y(?P<y>-?\d+(?:\.\d+)?)\s*Z(?P<z>-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def parse_command(text: str, use_llm: bool = False, llm_config: Optional[LLMConfig] = None) -> Plan:
    """将中文命令解析为 Plan，如果启用 LLM 则优先调用外部接口。"""

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("请输入有效的命令文本")

    logger = utils.get_logger(__name__)

    if use_llm:
        try:
            config = llm_config or LLMConfig(api_url=None, api_key=None, timeout=30)
            plan_obj = llm_client.generate_plan(cleaned, config)
            logger.info("LLM 解析成功，返回计划")
            return validate_plan(plan_obj)
        except Exception as exc:  # pragma: no cover - 网络相关异常在测试中难模拟
            logger.warning("LLM 解析失败，回退到规则解析：%s", exc)

    steps: List[PlanStep] = []

    for match in _ADD_CUBE_RE.finditer(cleaned):
        color = match.group("color")
        material = match.group("material")
        steps.append(PlanStep(op="mesh.primitive_cube_add", args={}))
        if material:
            steps.append(PlanStep(op="material.assign", args={"spec": material}))
        if color and not material:
            steps.append(PlanStep(op="material.assign", args={"spec": color}))

    for match in _ADD_SPHERE_RE.finditer(cleaned):
        color = match.group("color")
        material = match.group("material")
        steps.append(PlanStep(op="mesh.primitive_uv_sphere_add", args={}))
        if material:
            steps.append(PlanStep(op="material.assign", args={"spec": material}))
        if color and not material:
            steps.append(PlanStep(op="material.assign", args={"spec": color}))

    for match in _APPLY_MATERIAL_RE.finditer(cleaned):
        material = match.group("material")
        steps.append(PlanStep(op="material.assign", args={"spec": material}))

    move_match = _MOVE_RE.search(cleaned)
    if move_match:
        steps.append(
            PlanStep(
                op="object.move",
                args={
                    "location": (
                        float(move_match.group("x")),
                        float(move_match.group("y")),
                        float(move_match.group("z")),
                    )
                },
            )
        )

    if not steps:
        raise ValueError("未能解析命令，请尝试更简单的描述或启用 LLM")

    logger.info("规则解析生成 %d 步计划", len(steps))
    return Plan(steps=steps)
