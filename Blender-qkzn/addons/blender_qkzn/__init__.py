"""Blender-QKZN 插件入口模块，负责注册面板、操作符以及首选项。"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

try:
    import bpy
    from bpy.props import BoolProperty, StringProperty
    from bpy.types import AddonPreferences
except ImportError:  # pragma: no cover - 仅在非 Blender 环境触发
    bpy = None  # type: ignore[assignment]

    def BoolProperty(**_kwargs):  # type: ignore[misc]
        return None

    def StringProperty(**_kwargs):  # type: ignore[misc]
        return None

    class AddonPreferences:  # type: ignore[override]
        bl_idname = ""

        def draw(self, _context):
            return None

from . import executor, llm_client, materials, planner_client, utils

if bpy is not None:
    from . import operators, ui_panel
else:  # pragma: no cover - 测试环境不加载 UI
    operators = None  # type: ignore
    ui_panel = None  # type: ignore

if TYPE_CHECKING:
    from bpy.types import Context


bl_info = {
    "name": "Blender-QKZN AI Assistant",
    "author": "OpenAI ChatGPT",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar",
    "description": "在侧边栏提供中文自然语言 AI 助手，支持规则解析与可选 LLM",
    "warning": "",
    "category": "3D View",
}


class QKZNAddonPreferences(AddonPreferences):
    """插件首选项，用于配置外部 LLM 接口与日志级别。"""

    bl_idname = __name__

    api_url: StringProperty(
        name="LLM API 地址",
        description="可选的 HTTP LLM 服务地址，留空则仅使用本地规则解析",
        default="",
    )
    api_key: StringProperty(
        name="LLM API Key",
        description="可选的密钥或 Token",
        default="",
    )
    timeout: bpy.props.IntProperty(  # type: ignore[attr-defined]
        name="请求超时 (秒)",
        default=30,
        min=5,
        description="外部 LLM 请求的超时时间",
    )
    use_llm_default: bpy.props.BoolProperty(  # type: ignore[attr-defined]
        name="默认启用 LLM",
        default=False,
        description="勾选后默认使用 LLM 解析计划",
    )
    log_level: bpy.props.EnumProperty(  # type: ignore[attr-defined]
        name="日志级别",
        items=[
            ("INFO", "信息", "输出常规信息"),
            ("DEBUG", "调试", "输出详细调试信息"),
            ("WARNING", "警告", "仅输出警告及错误"),
            ("ERROR", "错误", "仅输出错误"),
        ],
        default="INFO",
    )

    def draw(self, context: Context) -> None:  # type: ignore[name-defined]
        layout = self.layout
        layout.label(text="配置外部 LLM 服务与默认行为")
        layout.prop(self, "api_url")
        layout.prop(self, "api_key")
        layout.prop(self, "timeout")
        layout.prop(self, "use_llm_default")
        layout.prop(self, "log_level")


CLASSES = ()
if bpy is not None:
    CLASSES = (
        QKZNAddonPreferences,
        operators.QKZNRunAICommandOperator,
        operators.QKZNClearLogOperator,
        ui_panel.QKZNAIAssistantPanel,
    )


def register() -> None:
    """注册插件中的自定义类型、首选项与属性。"""

    if bpy is None:
        raise RuntimeError("Blender 环境缺少 bpy，无法注册插件")

    for module in (executor, llm_client, materials, planner_client, ui_panel, operators, utils):
        if module is not None:
            importlib.reload(module)

    bpy.utils.register_class(QKZNAddonPreferences)
    for cls in CLASSES[1:]:
        bpy.utils.register_class(cls)

    bpy.types.Scene.ai_input = StringProperty(  # type: ignore[attr-defined]
        name="AI 命令",
        description="输入中文自然语言命令，例如：添加一个红色立方体",
        default="",
    )
    pref_default = False
    prefs = utils.get_preferences()
    if prefs and getattr(prefs, "use_llm_default", None):
        pref_default = bool(prefs.use_llm_default)
    bpy.types.Scene.ai_use_llm = BoolProperty(  # type: ignore[attr-defined]
        name="使用 LLM",
        description="在执行命令时调用配置的 LLM 服务",
        default=pref_default,
    )

    utils.get_logger(__name__).info("Blender-QKZN 插件已注册")


def unregister() -> None:
    """卸载插件时清理注册的类型与属性。"""

    if bpy is None:
        return

    del bpy.types.Scene.ai_input
    del bpy.types.Scene.ai_use_llm

    for cls in reversed(CLASSES[1:]):
        bpy.utils.unregister_class(cls)
    bpy.utils.unregister_class(QKZNAddonPreferences)

    utils.get_logger(__name__).info("Blender-QKZN 插件已卸载")


if __name__ == "__main__":
    register()
