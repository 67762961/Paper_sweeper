# -*- coding: utf-8 -*-
"""Fluent 主题初始化与切换。

主题偏好由 ``ui/prefs.py`` 写入 ``config/gui.json``（自管 JSON），
``qconfig`` 只负责运行时的主题状态，不再把配置文件交给它托管，
避免界面偏好与任务配置互相覆盖。
"""

from qfluentwidgets import Theme, qconfig, setTheme, setThemeColor

from . import prefs, theme

THEME_BY_MODE = {
    "light": Theme.LIGHT,
    "dark": Theme.DARK,
    "auto": Theme.AUTO,
}
THEME_LABELS = {
    "light": "浅色",
    "dark": "深色",
    "auto": "跟随系统",
}


def current_mode():
    """当前保存的主题模式（light / dark / auto）"""
    return prefs.load_prefs()["theme"]


def init_theme():
    """启动时读取偏好并应用主题与强调色"""
    mode = prefs.load_prefs()["theme"]
    setTheme(THEME_BY_MODE.get(mode, Theme.LIGHT))
    setThemeColor(theme.COLOR_ACCENT)
    return mode


def apply_theme(mode):
    """切换并持久化主题；返回实际生效的模式"""
    if mode not in THEME_BY_MODE:
        mode = "light"
    current = prefs.load_prefs()
    current["theme"] = mode
    prefs.save_prefs(current)
    setTheme(THEME_BY_MODE[mode])
    setThemeColor(theme.COLOR_ACCENT)
    return mode


def toggle_theme():
    """浅色 / 深色之间快速切换（跟随系统时首次切换到深色）"""
    saved = prefs.load_prefs()["theme"]
    next_mode = "light" if saved == "dark" else "dark"
    return apply_theme(next_mode)


def is_dark():
    """当前是否处于深色主题（跟随系统时由 qconfig 解析后的结果）"""
    return qconfig.theme == Theme.DARK
