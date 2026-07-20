"""应用主题：白天 / 黑夜 / 跟随系统。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

ThemeMode = Literal["light", "dark", "system"]

_STYLES_DIR = Path(__file__).parent / "styles"


def resolve_effective_theme(mode: str) -> str:
    """将 light/dark/system 解析为 light 或 dark。"""
    mode = (mode or "system").lower()
    if mode in ("light", "dark"):
        return mode
    # system
    app = QApplication.instance()
    if app is not None:
        try:
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return "light"
            if scheme == Qt.ColorScheme.Dark:
                return "dark"
        except Exception:
            pass
    return "dark"


def load_theme_qss(theme: str) -> str:
    name = "dark.qss" if theme == "dark" else "light.qss"
    path = _STYLES_DIR / name
    # 兼容旧文件名 main.qss
    if not path.exists() and theme == "dark":
        path = _STYLES_DIR / "main.qss"
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("加载主题失败 %s: %s", path, e)
        return ""


def apply_app_theme(mode: str | None = None) -> str:
    """
    应用主题到 QApplication。
    mode 为空时从 SettingsManager 读取。
    返回实际生效的 light/dark。
    """
    if mode is None:
        try:
            from zentray.services.settings_manager import SettingsManager

            mode = SettingsManager().appearance.theme
        except Exception:
            mode = "system"

    effective = resolve_effective_theme(mode)
    qss = load_theme_qss(effective)
    app = QApplication.instance()
    if app is not None and qss:
        app.setStyleSheet(qss)
    return effective
