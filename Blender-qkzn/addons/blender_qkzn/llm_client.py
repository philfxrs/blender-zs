"""可选的 LLM HTTP 客户端，用于将文本转换成计划。"""

from __future__ import annotations

from typing import List

try:
    import requests
except ImportError:  # pragma: no cover - 测试环境可无 requests
    requests = None  # type: ignore[assignment]

from . import utils
from .schemas import LLMConfig, PlanStep, validate_plan


def generate_plan(text: str, cfg: LLMConfig) -> List[PlanStep]:
    """调用外部 LLM 服务，将文本解析为计划步骤列表。"""

    if not cfg.api_url:
        raise ValueError("未配置 LLM API 地址，无法调用外部模型")

    if requests is None:
        raise RuntimeError("当前环境未安装 requests，无法调用外部 LLM 接口")

    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    payload = {"prompt": text}
    logger = utils.get_logger(__name__)
    logger.info("请求外部 LLM: %s", cfg.api_url)

    response = requests.post(cfg.api_url, json=payload, timeout=cfg.timeout, headers=headers)
    response.raise_for_status()

    data = response.json()
    plan_raw = data.get("plan", data)
    plan = validate_plan(plan_raw)
    logger.info("LLM 返回 %d 个步骤", len(plan.steps))
    return plan.steps


# 使用说明：
#  - 如果需要接入自托管或本地 LLM，请在插件首选项中填写 API 地址与密钥。
#  - API 返回的 JSON 应包含 "plan" 字段或直接是步骤数组。
#  - 每个步骤需要提供 op 与 args 字段，例如 {"op": "mesh.primitive_cube_add", "args": {}}。
