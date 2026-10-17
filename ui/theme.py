# -*- coding: utf-8 -*-
"""界面设计 token：颜色、间距、圆角、字号。

界面代码统一从这里取值，避免颜色与尺寸散落在组件里。
后续接入 Fluent 主题时，只需要调整本文件的取值（或改为从主题管理器读取）。
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
COLOR_ACCENT = "#007BFF"            # 主强调色（选中、悬停边框、开关开启）
COLOR_ACCENT_TEXT = "#007acc"       # 强调文字
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
COLOR_STATUS_DONE_BG = "#e6f4ea"    # 今日已完成：绿底
COLOR_STATUS_DONE_FG = "#1b5e20"
COLOR_STATUS_PENDING_BG = "#fef3e2"  # 今日未完成：橙底
COLOR_STATUS_PENDING_FG = "#b26a00"

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
FONT_SIZE_BODY = 10                 # 任务名
FONT_SIZE_SMALL = 11                # 说明与时间
FONT_FAMILY_LOG = "Consolas"
FONT_SIZE_LOG = 12
FONT_SIZE_RUN_BUTTON = 14
