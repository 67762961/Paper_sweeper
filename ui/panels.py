# -*- coding: utf-8 -*-
"""面板：左侧任务列表与右侧日志控制台（Fluent 控件）。

配色统一从 ``ui/theme.py`` 取：文字类控件用 Fluent 标签（浅色 / 深色两套文字色
由库自动切换），轮廓按钮与日志行着色显式给出深浅两套取值。
"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FluentIcon,
    IndeterminateProgressBar,
    PushButton,
    StrongBodyLabel,
    TextEdit,
    TransparentToolButton,
)
from qfluentwidgets.common import setCustomStyleSheet

from main import TASK_REGISTRY, entry_done_today, latest_completion, read_completions, read_task_switches
from . import prefs as ui_prefs
from . import theme
from .widgets import TaskRow, ToggleSwitch

# 日志行首关键字 → 颜色 token（深浅两套取值由 theme 提供）
LOG_LINE_COLORS = (
    ("ERROR", "COLOR_LOG_ERROR"),
    ("错误", "COLOR_LOG_ERROR"),
    ("SKIP-", "COLOR_LOG_SKIP"),
    ("TASK-", "COLOR_LOG_TASK"),
    ("MAIN-", "COLOR_LOG_TASK"),
)


def run_button_qss(dark):
    """「完整运行」轮廓按钮样式：主色描边 + 主色文字，悬停/按下用同色系浅底"""
    accent = theme.dark_color("COLOR_ACCENT") if dark else theme.light_color("COLOR_ACCENT")
    hover = theme.dark_color("COLOR_ACCENT_HOVER_BG") if dark else theme.light_color("COLOR_ACCENT_HOVER_BG")
    pressed = (
        theme.dark_color("COLOR_ACCENT_PRESSED_BG")
        if dark
        else theme.light_color("COLOR_ACCENT_PRESSED_BG")
    )
    disabled = theme.dark_color("COLOR_TEXT_DISABLED") if dark else theme.light_color("COLOR_TEXT_DISABLED")
    border = theme.dark_color("COLOR_ROW_BORDER") if dark else theme.light_color("COLOR_ROW_BORDER")
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {accent};
            border: 1px solid {accent};
            border-radius: {theme.RADIUS_CARD}px;
            font-size: {theme.FONT_SIZE_RUN_BUTTON}px;
            font-weight: bold;
            padding: 0 {theme.SPACE_XXL}px;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:pressed {{
            background-color: {pressed};
        }}
        QPushButton:disabled {{
            color: {disabled};
            border-color: {border};
        }}
    """


def interrupt_button_qss(dark):
    """「中断运行」轮廓按钮样式：次要色描边，与主色的完整运行按钮拉开层次"""
    text = theme.dark_color("COLOR_TEXT_SECONDARY") if dark else theme.light_color("COLOR_TEXT_SECONDARY")
    border = theme.dark_color("COLOR_ROW_BORDER") if dark else theme.light_color("COLOR_ROW_BORDER")
    hover = theme.dark_color("COLOR_HOVER_BG") if dark else theme.light_color("COLOR_HOVER_BG")
    pressed = theme.dark_color("COLOR_PRESSED_BG") if dark else theme.light_color("COLOR_PRESSED_BG")
    disabled = theme.dark_color("COLOR_TEXT_DISABLED") if dark else theme.light_color("COLOR_TEXT_DISABLED")
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {text};
            border: 1px solid {border};
            border-radius: {theme.RADIUS_CARD}px;
            font-size: {theme.FONT_SIZE_RUN_BUTTON}px;
            padding: 0 {theme.SPACE_XL}px;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:pressed {{
            background-color: {pressed};
        }}
        QPushButton:disabled {{
            color: {disabled};
            border-color: {border};
        }}
    """


def danger_button_qss(dark):
    """「关闭模拟器」危险色轮廓按钮：红色描边 + 红色文字，悬停/按下用同色系浅底

    与「中断运行」的次要色刻意拉开层次：中断只是停下，关模拟器会结束虚拟机、
    未保存的进度可能丢失，用红色提示这个差别。
    """
    text = theme.dark_color("COLOR_DANGER") if dark else theme.light_color("COLOR_DANGER")
    hover = (
        theme.dark_color("COLOR_DANGER_HOVER_BG")
        if dark
        else theme.light_color("COLOR_DANGER_HOVER_BG")
    )
    pressed = (
        theme.dark_color("COLOR_DANGER_PRESSED_BG")
        if dark
        else theme.light_color("COLOR_DANGER_PRESSED_BG")
    )
    disabled = theme.dark_color("COLOR_TEXT_DISABLED") if dark else theme.light_color("COLOR_TEXT_DISABLED")
    border = theme.dark_color("COLOR_ROW_BORDER") if dark else theme.light_color("COLOR_ROW_BORDER")
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {text};
            border: 1px solid {text};
            border-radius: {theme.RADIUS_CARD}px;
            font-size: {theme.FONT_SIZE_RUN_BUTTON}px;
            padding: 0 {theme.SPACE_XL}px;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:pressed {{
            background-color: {pressed};
        }}
        QPushButton:disabled {{
            color: {disabled};
            border-color: {border};
        }}
    """


class LeftPanel(QFrame):
    """左侧任务列表面板：7 行对应 TASK_REGISTRY，行内提供单跑与整跑开关"""

    task_run_clicked = pyqtSignal(str)
    task_config_clicked = pyqtSignal(str)
    task_toggled = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        self.rows = {}
        self.init_ui()
        self.refresh()

    def init_ui(self):
        self.setFixedWidth(theme.WIDTH_LEFT_PANEL)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_XS)

        # 文字用 Fluent 标签，深度主题下自动变白；裸 QLabel 在暗底上会变成黑字
        self.title_label = StrongBodyLabel("任务列表", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont(theme.FONT_FAMILY_UI, 12, QFont.Weight.Bold))
        self.title_label.setTextColor(
            theme.light_color("COLOR_TEXT_PRIMARY"), theme.dark_color("COLOR_TEXT_PRIMARY")
        )
        layout.addWidget(self.title_label)

        layout.addWidget(self.create_scroll_area())

        self.hint_label = CaptionLabel(
            "运行按钮单独执行 · 齿轮为配置入口（寮三十已支持）· 开关决定是否参与完整运行", self
        )
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setFont(QFont(theme.FONT_FAMILY_UI, 9))
        self.hint_label.setWordWrap(True)
        self.hint_label.setTextColor(
            theme.light_color("COLOR_TEXT_TERTIARY"), theme.dark_color("COLOR_TEXT_TERTIARY")
        )
        layout.addWidget(self.hint_label)

        self.setLayout(layout)

    def create_scroll_area(self):
        """按 TASK_REGISTRY 生成任务行，顺序与完整运行一致"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(theme.SPACE_XS)

        try:
            switches = read_task_switches()
        except Exception as error:
            logging.warning("读取任务开关失败，按全部开启处理: %s", error)
            switches = {}

        for entry in TASK_REGISTRY:
            row = TaskRow(entry, switch_on=switches.get(entry.key, True))
            row.run_clicked.connect(self.task_run_clicked)
            row.config_clicked.connect(self.task_config_clicked)
            row.switch_toggled.connect(self.task_toggled)
            scroll_layout.addWidget(row)
            self.rows[entry.key] = row

        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)

        return scroll_area

    def refresh(self):
        """刷新上次运行时间与今日状态；只读 Last_times.yml，不创建配置文件"""
        try:
            completions = read_completions()
        except Exception as error:
            logging.warning("读取任务完成时间失败: %s", error)
            completions = {}

        for entry in TASK_REGISTRY:
            row = self.rows.get(entry.key)
            if row is None:
                continue
            row.set_last_time(latest_completion(entry, completions))
            try:
                row.set_today_done(entry_done_today(entry, completions))
            except Exception as error:
                logging.warning("判定任务 %s 今日状态失败: %s", entry.key, error)
                row.set_today_done(False)

    def set_busy(self, busy):
        """运行期间禁用全部行的交互控件，避免并发抢占键鼠或中途改开关"""
        for row in self.rows.values():
            row.set_busy(busy)

    def set_running(self, task_key):
        """把指定任务行标记为运行中"""
        for key, row in self.rows.items():
            row.set_running(key == task_key)

    def clear_running(self):
        """清除所有行的运行中标记"""
        for row in self.rows.values():
            row.set_running(False)

    def set_switch_state(self, task_key, on):
        """外部回写开关状态（写盘失败时用于回滚界面）"""
        row = self.rows.get(task_key)
        if row is not None:
            row.set_switch(on)


class RightPanel(QFrame):
    """右侧日志控制台面板"""

    run_button_clicked = pyqtSignal()
    interrupt_clicked = pyqtSignal()
    close_emulator_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    after_run_settings_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        self.prefs = ui_prefs.load_prefs()
        self.auto_scroll = self.prefs["log_auto_scroll"]
        self.textbox = None
        self.run_button = None
        self.interrupt_button = None
        self.close_emulator_button = None
        self.button_settings_button = None
        self.progress = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_LG)

        self.create_header(layout)
        self.create_console_area(layout)
        self.create_progress(layout)
        self.create_button_area(layout)

        self.setLayout(layout)

    def create_header(self, parent_layout):
        """日志区顶部工具条：标题 / 清空 / 自动滚动 / 设置"""
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(theme.SPACE_SM)

        header.addWidget(BodyLabel("运行日志", self))
        header.addStretch()

        self.clear_button = TransparentToolButton(FluentIcon.BROOM, self)
        self.clear_button.setToolTip("清空日志")
        self.clear_button.clicked.connect(self.clear_log)
        header.addWidget(self.clear_button)

        self.auto_scroll_switch = ToggleSwitch(self)
        self.auto_scroll_switch.setOnText("")
        self.auto_scroll_switch.setOffText("")
        self.auto_scroll_switch.setToolTip("新日志自动滚动到底部")
        self.auto_scroll_switch.setChecked(self.auto_scroll)
        self.auto_scroll_switch.checkedChanged.connect(self.on_auto_scroll_changed)
        header.addWidget(self.auto_scroll_switch)

        self.settings_button = TransparentToolButton(FluentIcon.SETTING, self)
        self.settings_button.setToolTip("设置")
        self.settings_button.clicked.connect(self.settings_clicked)
        header.addWidget(self.settings_button)

        parent_layout.addLayout(header)

    def create_console_area(self, parent_layout):
        """创建控制台输出区域"""
        self.textbox = TextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setFont(QFont(theme.FONT_FAMILY_LOG, self.prefs["log_font_size"]))
        self.textbox.setPlaceholderText("运行日志会显示在这里")
        parent_layout.addWidget(self.textbox, 1)

    def create_progress(self, parent_layout):
        """运行中的不确定进度条，默认隐藏"""
        self.progress = IndeterminateProgressBar(self)
        self.progress.setVisible(False)
        parent_layout.addWidget(self.progress)

    def create_button_area(self, parent_layout):
        """创建主操作按钮：左起「关闭模拟器」「中断运行」「完整运行」，末尾是设置齿轮"""
        self.run_button = PushButton("完整运行")
        self.run_button.setFixedHeight(theme.SIZE_RUN_BUTTON_HEIGHT)
        # 用 Fluent 的「浅色 / 深色两套自定义样式」而不是一次性 setStyleSheet：
        # 后者会在主题切换时被样式管理器覆盖，按钮会退回 Fluent 默认实心样式
        setCustomStyleSheet(
            self.run_button,
            run_button_qss(dark=False),
            run_button_qss(dark=True),
        )

        self.interrupt_button = PushButton("中断运行", self, FluentIcon.PAUSE)
        self.interrupt_button.setFixedHeight(theme.SIZE_RUN_BUTTON_HEIGHT)
        self.interrupt_button.setToolTip("立即中断当前任务并回到待机（不会从断点继续）")
        self.interrupt_button.setEnabled(False)  # 仅运行中可点
        setCustomStyleSheet(
            self.interrupt_button,
            interrupt_button_qss(dark=False),
            interrupt_button_qss(dark=True),
        )

        # 危险动作：红色轮廓，与灰色的「中断运行」拉开层次
        self.close_emulator_button = PushButton("关闭模拟器", self, FluentIcon.POWER_BUTTON)
        self.close_emulator_button.setFixedHeight(theme.SIZE_RUN_BUTTON_HEIGHT)
        self.close_emulator_button.setToolTip(
            "关闭所有由本程序管理的模拟器窗口（master / slaves），未保存的进度会丢失"
        )
        self.close_emulator_button.setEnabled(True)  # 仅空闲时可点
        setCustomStyleSheet(
            self.close_emulator_button,
            danger_button_qss(dark=False),
            danger_button_qss(dark=True),
        )

        # 完整运行设置的入口：与日志区顶部齿轮同款（默认尺寸，不放大）。
        # 走独立信号，与日志齿轮各进各的弹窗
        self.button_settings_button = TransparentToolButton(FluentIcon.SETTING, self)
        self.button_settings_button.setToolTip("完整运行完成后的动作")
        self.button_settings_button.clicked.connect(self.after_run_settings_clicked)

        button_container = QFrame()
        button_container.setStyleSheet("background: transparent;")
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, theme.SPACE_MD, 0, 0)
        button_layout.setSpacing(theme.SPACE_SM)
        # 左侧 stretch 吃掉剩余空间，整组右对齐；末尾追加齿轮后
        # 前面三个按钮会被自然向左推，不需要额外调整
        button_layout.addStretch()
        button_layout.addWidget(self.close_emulator_button)
        button_layout.addWidget(self.interrupt_button)
        button_layout.addWidget(self.run_button)
        button_layout.addSpacing(theme.SPACE_MD)
        button_layout.addWidget(self.button_settings_button)
        button_container.setLayout(button_layout)

        parent_layout.addWidget(button_container)

        self.run_button.clicked.connect(self.run_button_clicked)
        self.interrupt_button.clicked.connect(self.interrupt_clicked)
        self.close_emulator_button.clicked.connect(self.close_emulator_clicked)

    def set_running(self, running):
        """运行期间禁用完整运行按钮、启用中断按钮、显示进度条"""
        self.run_button.setEnabled(not running)
        self.run_button.setText("运行中…" if running else "完整运行")
        self.interrupt_button.setEnabled(running)
        self.interrupt_button.setText("中断运行")
        # 关闭模拟器是破坏性动作，运行中一律禁用：正在抢占键鼠时关窗口
        # 会让任务在半途失去目标，后续每一步都必然失败
        self.close_emulator_button.setEnabled(not running)
        if running:
            self.progress.setVisible(True)
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.setVisible(False)

    def set_interrupting(self):
        """已发出中断请求：禁用中断按钮防连点，等线程收尾后由 set_running(False) 复位"""
        self.interrupt_button.setEnabled(False)
        self.interrupt_button.setText("中断中…")

    def clear_log(self):
        """清空日志区"""
        self.textbox.clear()

    def on_auto_scroll_changed(self, checked):
        """自动滚动开关变化：立即生效并持久化"""
        self.auto_scroll = bool(checked)
        current = ui_prefs.load_prefs()
        current["log_auto_scroll"] = self.auto_scroll
        ui_prefs.save_prefs(current)

    def set_log_font_size(self, size):
        """更新日志字号"""
        self.prefs["log_font_size"] = size
        self.textbox.setFont(QFont(theme.FONT_FAMILY_LOG, size))

    def apply_prefs(self, values):
        """设置对话框保存后统一应用界面偏好"""
        self.prefs.update(values)
        self.auto_scroll = bool(values["log_auto_scroll"])
        self.auto_scroll_switch.blockSignals(True)
        self.auto_scroll_switch.setChecked(self.auto_scroll)
        self.auto_scroll_switch.blockSignals(False)
        self.set_log_font_size(values["log_font_size"])

    def apply_theme(self):
        """主题切换后重新着色已有日志（已插入的文本不会自动跟随主题）"""
        text = self.textbox.toPlainText()
        if not text:
            return
        scrollbar = self.textbox.verticalScrollBar()
        position = scrollbar.value()
        self.textbox.clear()
        self.update_console(text)
        if not self.auto_scroll:
            scrollbar.setValue(min(position, scrollbar.maximum()))

    def append_separator(self, text):
        """在控制台插入一段分隔说明，便于区分多次运行"""
        self.update_console(f"\n{'=' * 60}\n{text}\n{'=' * 60}\n\n")

    @staticmethod
    def color_for(line):
        """按日志前缀返回当前主题下的着色，返回 None 表示使用正文颜色"""
        for keyword, token in LOG_LINE_COLORS:
            if keyword in line:
                return theme.color(token)
        return None

    def update_console(self, message):
        """更新控制台显示：逐行着色并自动滚动到底部"""
        cursor = self.textbox.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        # 无前缀的正文也显式给颜色：不依赖控件调色板，深浅色下都保证可读
        default_color = QColor(theme.color("COLOR_LOG_TEXT"))

        for line in message.splitlines(keepends=True):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(self.color_for(line) or default_color))
            cursor.insertText(line, fmt)

        self.textbox.setTextCursor(cursor)
        if self.auto_scroll:
            self.textbox.ensureCursorVisible()
            scrollbar = self.textbox.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
