"""通用工具模块，封装日志、配置访问与颜色映射逻辑。"""

from __future__ import annotations

import logging
from typing import Dict, Tuple, Optional, Iterable

try:
    import bpy
except ImportError:  # pragma: no cover - 测试环境下可能没有 bpy
    bpy = None  # type: ignore[assignment]


_COLOR_MAP: Dict[str, Tuple[float, float, float]] = {
    "红色": (1.0, 0.0, 0.0),
    "绿色": (0.0, 1.0, 0.0),
    "蓝色": (0.0, 0.0, 1.0),
    "黄色": (1.0, 1.0, 0.0),
    "白色": (1.0, 1.0, 1.0),
    "黑色": (0.0, 0.0, 0.0),
    "紫色": (0.5, 0.0, 0.5),
    "青色": (0.0, 1.0, 1.0),
    "品红": (1.0, 0.0, 1.0),
    "橙色": (1.0, 0.5, 0.0),
}


def get_logger(name: str) -> logging.Logger:
    """获取带有中文格式提示的 logger。"""

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(levelname)s][%(name)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def set_log_level(level: str) -> None:
    """根据首选项调整全局日志级别。"""

    logging.getLogger().setLevel(level.upper())


def get_preferences() -> Optional[object]:
    """安全获取插件首选项，测试环境下返回 None。"""

    if bpy is None:
        return None
    addon_name = __name__.split(".")[0]
    prefs = bpy.context.preferences.addons.get(addon_name) if bpy else None
    return getattr(prefs, "preferences", None) if prefs else None


def color_from_text(text: str) -> Optional[Tuple[float, float, float]]:
    """根据中文颜色词返回 RGB 值。"""

    return _COLOR_MAP.get(text)


def available_color_words() -> Iterable[str]:
    """返回可识别的颜色词集合。"""

    return _COLOR_MAP.keys()


def ensure_logger_level_from_prefs() -> None:
    """读取首选项并设置日志级别。"""

    prefs = get_preferences()
    if prefs and getattr(prefs, "log_level", None):
        set_log_level(prefs.log_level)
