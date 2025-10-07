"""UI 面板定义：在 3D 视图的侧边栏提供交互。"""

from __future__ import annotations

import bpy
from bpy.types import Panel


class QKZNAIAssistantPanel(Panel):
    """AI 助手面板，提供命令输入与操作按钮。"""

    bl_label = "AI 助手"
    bl_idname = "QKZN_PT_ai_assistant"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "ai_input", text="命令")
        layout.prop(scene, "ai_use_llm", text="使用 LLM")

        row = layout.row(align=True)
        op = row.operator("wm.addon_userpref_show", text="设置", icon="PREFERENCES")
        op.module = __package__

        row = layout.row(align=True)
        row.operator("qkzn.run_ai_command", text="执行", icon="PLAY")
        row.operator("qkzn.clear_log", text="清空", icon="TRASH")
