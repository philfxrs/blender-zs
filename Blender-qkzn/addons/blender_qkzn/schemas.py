"""数据模型定义，使用 Pydantic 提供强类型校验。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, root_validator


class PlanStep(BaseModel):
    """单个计划步骤，描述一个 Blender 操作。"""

    op: str
    args: Dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    """完整计划，由多个步骤组成。"""

    steps: List[PlanStep]

    @root_validator
    def check_steps_not_empty(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values.get("steps"):
            raise ValueError("计划步骤不能为空")
        return values


class LLMConfig(BaseModel):
    """LLM 请求配置。"""

    api_url: Optional[str]
    api_key: Optional[str]
    timeout: int = 30


def validate_plan(raw: Any) -> Plan:
    """验证任意对象能否转为 Plan，错误时抛出中文提示。"""

    try:
        if isinstance(raw, Plan):
            return raw
        if isinstance(raw, dict) and "steps" in raw:
            return Plan.parse_obj(raw)
        if isinstance(raw, list):
            return Plan(steps=[PlanStep.parse_obj(item) for item in raw])
        raise TypeError("计划数据结构不正确，需为列表或包含 steps 的字典")
    except (ValidationError, TypeError, ValueError) as exc:  # pragma: no cover - 错误路径
        raise ValueError(f"计划校验失败：{exc}") from exc
