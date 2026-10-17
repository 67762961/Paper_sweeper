# -*- coding: utf-8 -*-
"""Fluent 主题初始化与切换。

主题偏好由 ``ui/prefs.py`` 写入 ``config/gui.json``（自管 JSON），
``qconfig`` 只负责运行时的主题状态，不再把配置文件交给它托管，
避免界面偏好与任务配置互相覆盖。

每次切换后同步 ``ui/theme.py`` 的深浅标记：自绘组件（今日状态图标、日志行着色）
与轮廓按钮需要按当前主题取色，Fluent 标签则一次设置浅色 / 深色两套取值。
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


def _sync_dark_mode(*_args):
    """把 qconfig 解析后的实际主题同步给 theme（「跟随系统」时也能拿到真实深浅）"""
    theme.set_dark_mode(qconfig.theme == Theme.DARK)


# 模块导入即连接，保证先于界面组件收到通知：组件处理 themeChangedFinished 时
# theme 里的深浅标记已经是新值
qconfig.themeChangedFinished.connect(_sync_dark_mode)


def current_mode():
    """当前保存的主题模式（light / dark / auto）"""
    return prefs.load_prefs()["theme"]


def init_theme():
    """启动时读取偏好并应用主题与强调色"""
    mode = prefs.load_prefs()["theme"]
    setTheme(THEME_BY_MODE.get(mode, Theme.LIGHT))
    setThemeColor(theme.color("COLOR_ACCENT"))
    return mode


def apply_theme(mode):
    """切换并持久化主题；返回实际生效的模式"""
    if mode not in THEME_BY_MODE:
        mode = "light"
    current = prefs.load_prefs()
    current["theme"] = mode
    prefs.save_prefs(current)
    setTheme(THEME_BY_MODE[mode])
    setThemeColor(theme.color("COLOR_ACCENT"))
    return mode


def toggle_theme():
    """浅色 / 深色之间快速切换（跟随系统时首次切换到深色）"""
    saved = prefs.load_prefs()["theme"]
    next_mode = "light" if saved == "dark" else "dark"
    return apply_theme(next_mode)


def is_dark():
    """当前是否处于深色主题（跟随系统时由 qconfig 解析后的结果）"""
    return qconfig.theme == Theme.DARK
