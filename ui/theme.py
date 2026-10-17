# -*- coding: utf-8 -*-
"""界面设计 token：颜色、间距、圆角、字号。

界面代码统一从这里取值，避免颜色与尺寸散落在组件里。

颜色分两套：``COLOR_*`` 常量是**浅色主题**取值，深色主题的差异值集中在
``_DARK_COLORS``。组件里取色请用下面的工具函数，不要直接引用常量：

- ``theme.color(name)``：当前主题下的取值（绘制 / 即时样式用）；
- ``theme.light_color(name)`` / ``theme.dark_color(name)``：给 Fluent 标签
  这类「一次设置浅色与深色两套取值、由库自动切换」的控件用。

当前是否深色由 ``ui/theme_manager.py`` 在切换主题后同步（``set_dark_mode``）。
"""

# ---- 窗口与面板 ----
COLOR_PANEL_BG = "#f8f9fa"          # 左右面板底色
COLOR_CARD_BG = "#ffffff"           # 任务行卡片底色

# ---- 文字 ----
COLOR_TEXT_PRIMARY = "#1f2328"      # 主标题
COLOR_TEXT_SECONDARY = "#6b7280"    # 次要说明
COLOR_TEXT_TERTIARY = "#8a9099"     # 上次运行时间、提示语
COLOR_TEXT_MUTED = "#9aa0a6"        # 已关闭任务的标题
COLOR_TEXT_DISABLED = "#b8bcc2"     # 禁用态文字

# ---- 强调色与交互 ----
COLOR_ACCENT = "#0d6bc2"            # 主强调色（比原 #007BFF 深一档）
COLOR_ACCENT_TEXT = "#0d6bc2"       # 强调文字（与主强调色保持一致）
COLOR_ACCENT_HOVER_BG = "#e6eff9"   # 轮廓按钮悬停底
COLOR_ACCENT_PRESSED_BG = "#cfe0f2"  # 轮廓按钮按下底
COLOR_HOVER_BG = "#e9ecef"          # 图标按钮悬停底
COLOR_PRESSED_BG = "#dee2e6"        # 图标按钮按下底

# ---- 任务行状态 ----
COLOR_ROW_BORDER = "#e3e6ea"        # 常规边框
COLOR_ROW_BG_OFF = "#f7f8fa"        # 关闭开关后的底色
COLOR_ROW_BORDER_OFF = "#eceef1"    # 关闭开关后的边框
COLOR_ROW_BG_RUNNING = "#e8f2ff"    # 运行中底色

# ---- 开关 ----
COLOR_TRACK_OFF = "#c9ced6"         # 开关关闭时轨道
COLOR_TRACK_DISABLED = "#d8dbe0"    # 开关禁用时轨道
COLOR_KNOB = "#ffffff"              # 开关滑块

# ---- 今日状态图标 ----
COLOR_STATUS_DONE = "#2e7d32"       # 今日已完成：对勾
COLOR_STATUS_PENDING = "#b26a00"    # 今日未完成：感叹号
COLOR_STATUS_RUNNING = "#0d6bc2"    # 运行中：播放三角

# ---- 日志行着色 ----
COLOR_LOG_TEXT = "#1f2328"          # 无前缀日志（正文）
COLOR_LOG_ERROR = "#c42b1c"         # ERROR / 错误
COLOR_LOG_SKIP = "#c77700"          # SKIP-
COLOR_LOG_TASK = "#0f5fa0"          # TASK- / MAIN-

# ---- 深色主题取值（未列出的 token 沿用浅色取值） ----
_DARK_COLORS = {
    "COLOR_PANEL_BG": "#1f1f1f",
    "COLOR_CARD_BG": "#2b2b2b",
    "COLOR_TEXT_PRIMARY": "#ffffff",
    "COLOR_TEXT_SECONDARY": "#c8ccd2",
    "COLOR_TEXT_TERTIARY": "#a8adb5",
    "COLOR_TEXT_MUTED": "#8b9098",
    "COLOR_TEXT_DISABLED": "#7a7f87",
    "COLOR_ACCENT": "#3d8bd6",          # 深色下也是深一档的蓝，靠亮度保证暗底可读
    "COLOR_ACCENT_TEXT": "#3d8bd6",
    "COLOR_ACCENT_HOVER_BG": "#1c3752",
    "COLOR_ACCENT_PRESSED_BG": "#24466a",
    "COLOR_HOVER_BG": "#333333",
    "COLOR_PRESSED_BG": "#3d3d3d",
    "COLOR_ROW_BORDER": "#3a3a3a",
    "COLOR_ROW_BG_OFF": "#242424",
    "COLOR_ROW_BORDER_OFF": "#303030",
    "COLOR_ROW_BG_RUNNING": "#16324f",
    "COLOR_TRACK_OFF": "#52565c",
    "COLOR_TRACK_DISABLED": "#43464b",
    "COLOR_KNOB": "#ffffff",
    "COLOR_STATUS_DONE": "#56c271",
    "COLOR_STATUS_PENDING": "#e3a33c",
    "COLOR_STATUS_RUNNING": "#3d8bd6",
    "COLOR_LOG_TEXT": "#e6e8eb",
    "COLOR_LOG_ERROR": "#ff8b82",
    "COLOR_LOG_SKIP": "#e5b263",
    "COLOR_LOG_TASK": "#67b0f0",
}

_dark_mode = False


def set_dark_mode(value):
    """记录当前是否为深色主题（由 theme_manager 在切换后调用）"""
    global _dark_mode
    _dark_mode = bool(value)


def is_dark_mode():
    """当前是否处于深色主题"""
    return _dark_mode


def light_color(name):
    """取浅色主题下的颜色取值"""
    return _lookup(name)


def dark_color(name):
    """取深色主题下的颜色取值（未单独定义的 token 沿用浅色）"""
    return _DARK_COLORS.get(name) or _lookup(name)


def color(name):
    """取当前主题下的颜色取值"""
    return dark_color(name) if _dark_mode else light_color(name)


def _lookup(name):
    """按 token 名读取浅色常量，名字写错时给出明确提示"""
    try:
        return globals()[name]
    except KeyError:
        raise KeyError(f"未定义的设计 token: {name}") from None


# ---- 尺寸 ----
SIZE_STATUS_ICON = 22               # 状态图标直径
SIZE_ICON_BUTTON = 26               # 齿轮 / 运行按钮尺寸
SIZE_TOGGLE_WIDTH = 44
SIZE_TOGGLE_HEIGHT = 24
HEIGHT_TASK_ROW = 62
WIDTH_LEFT_PANEL = 488
SIZE_RUN_BUTTON_HEIGHT = 40

RADIUS_CARD = 6                     # 任务行圆角
RADIUS_ICON_BUTTON = 13             # 图标按钮圆形半径
RADIUS_STATUS_ICON = 11             # 状态图标圆形半径
RADIUS_LOG_BOX = 4                  # 日志框圆角

SPACE_XS = 4
SPACE_SM = 6
SPACE_MD = 8
SPACE_LG = 10
SPACE_XL = 12
SPACE_XXL = 20

# ---- 字体 ----
FONT_FAMILY_UI = "Microsoft YaHei"
FONT_SIZE_TITLE = 15
FONT_SIZE_BODY = 10                 # 通用正文
FONT_SIZE_SMALL = 11                # 说明文字
FONT_SIZE_TASK_NAME = 12            # 任务行标题（比时间更醒目）
FONT_SIZE_TASK_TIME = 9             # 任务行「上次运行」时间（弱化）
FONT_FAMILY_LOG = "Consolas"
FONT_SIZE_LOG = 12
FONT_SIZE_RUN_BUTTON = 14
