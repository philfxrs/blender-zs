"""自定义 Blender 操作符，封装执行逻辑。"""

from __future__ import annotations

from typing import Optional

import bpy
from bpy.types import Context, Operator

from . import executor, planner_client, utils
from .schemas import LLMConfig


class QKZNRunAICommandOperator(Operator):
    """执行自然语言命令的操作符。"""

    bl_idname = "qkzn.run_ai_command"
    bl_label = "执行 AI 命令"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: Context) -> set[str]:
        utils.ensure_logger_level_from_prefs()
        scene = context.scene
        command = getattr(scene, "ai_input", "")
        use_llm = bool(getattr(scene, "ai_use_llm", False))

        logger = utils.get_logger(__name__)
        logger.info("收到命令：%s", command)

        prefs = utils.get_preferences()
        llm_config: Optional[LLMConfig] = None
        if prefs:
            llm_config = LLMConfig(
                api_url=getattr(prefs, "api_url", None) or None,
                api_key=getattr(prefs, "api_key", None) or None,
                timeout=int(getattr(prefs, "timeout", 30)),
            )
            if llm_config.api_url and not use_llm and getattr(prefs, "use_llm_default", False):
                use_llm = True

        try:
            plan = planner_client.parse_command(command, use_llm=use_llm, llm_config=llm_config)
            executor.execute_plan(plan)
        except Exception as exc:  # pragma: no cover - Blender 内部异常难测
            self.report({"ERROR"}, f"执行失败: {exc}")
            logger.error("执行失败：%s", exc)
            return {"CANCELLED"}

        self.report({"INFO"}, "计划执行完成")
        return {"FINISHED"}


class QKZNClearLogOperator(Operator):
    """简单重置输入的操作符。"""

    bl_idname = "qkzn.clear_log"
    bl_label = "清空命令"

    def execute(self, context: Context) -> set[str]:
        context.scene.ai_input = ""
        self.report({"INFO"}, "已清空输入")
        return {"FINISHED"}


def register() -> None:
    bpy.utils.register_class(QKZNRunAICommandOperator)
    bpy.utils.register_class(QKZNClearLogOperator)


def unregister() -> None:
    bpy.utils.unregister_class(QKZNClearLogOperator)
    bpy.utils.unregister_class(QKZNRunAICommandOperator)
