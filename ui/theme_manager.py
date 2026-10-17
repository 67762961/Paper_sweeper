# -*- coding: utf-8 -*-
"""Fluent 主题的初始化与持久化。

qconfig 的配置文件固定为 ``config/gui.json``，与 ``Setting.yml``（任务参数）、
``Gui_state.yml``（任务开关）物理隔离，避免互相覆盖。
"""

import logging
import os

from qfluentwidgets import Theme, qconfig, setTheme, setThemeColor

from . import theme

# 界面偏好配置文件（config/ 已在 .gitignore 中）
CONFIG_PATH = "config/gui.json"
DEFAULT_THEME = Theme.LIGHT


def init_theme(config_path=CONFIG_PATH):
    """读取界面配置并应用主题与强调色；首次运行使用浅色主题。

    返回当前生效的 Theme，供后续主题切换使用。
    """
    try:
        if os.path.exists(config_path):
            qconfig.load(config_path)
        else:
            setTheme(DEFAULT_THEME)
    except Exception as error:
        logging.warning("读取界面配置失败，使用默认主题: %s", error)
        setTheme(DEFAULT_THEME)

    setThemeColor(theme.COLOR_ACCENT)
    return qconfig.theme


def save_theme(theme_mode):
    """切换并持久化主题（供设置界面调用）"""
    setTheme(theme_mode, save=True)
    return qconfig.theme
