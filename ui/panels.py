# -*- coding: utf-8 -*-
"""面板：左侧任务列表与右侧日志控制台（Fluent 控件）。"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
    IndeterminateProgressBar,
    PushButton,
    TextEdit,
    TransparentToolButton,
)

from main import TASK_REGISTRY, entry_done_today, latest_completion, read_completions, read_task_switches
from . import prefs as ui_prefs
from . import theme
from .widgets import TaskRow, ToggleSwitch

# 日志行首关键字着色：深色/浅色主题下都保持可读
LOG_LINE_COLORS = (
    ("ERROR", "#c42b1c"),
    ("错误", "#c42b1c"),
    ("SKIP-", "#c77700"),
    ("TASK-", "#0f6cbd"),
    ("MAIN-", "#0f6cbd"),
)


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

        title_label = QLabel("任务列表")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont(theme.FONT_FAMILY_UI, 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        layout.addWidget(self.create_scroll_area())

        hint_label = QLabel("运行按钮单独执行 · 齿轮为配置入口（暂未开放）· 开关决定是否参与完整运行")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setFont(QFont(theme.FONT_FAMILY_UI, 9))
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

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
    settings_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        self.prefs = ui_prefs.load_prefs()
        self.auto_scroll = self.prefs["log_auto_scroll"]
        self.textbox = None
        self.run_button = None
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
        """创建主操作按钮"""
        self.run_button = PushButton("完整运行")
        self.run_button.setFixedHeight(theme.SIZE_RUN_BUTTON_HEIGHT)
        self.run_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.COLOR_ACCENT};
                border: 1px solid {theme.COLOR_ACCENT};
                border-radius: {theme.RADIUS_CARD}px;
                font-size: {theme.FONT_SIZE_RUN_BUTTON}px;
                font-weight: bold;
                padding: 0 {theme.SPACE_XXL}px;
            }}
            QPushButton:hover {{
                background-color: #E6F2FF;
            }}
            QPushButton:pressed {{
                background-color: #B8DAFF;
            }}
            QPushButton:disabled {{
                color: {theme.COLOR_TEXT_DISABLED};
                border-color: {theme.COLOR_ROW_BORDER};
            }}
        """)

        button_container = QFrame()
        button_container.setStyleSheet("background: transparent;")
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, theme.SPACE_MD, 0, 0)
        button_layout.addStretch()
        button_layout.addWidget(self.run_button)
        button_container.setLayout(button_layout)

        parent_layout.addWidget(button_container)

        self.run_button.clicked.connect(self.run_button_clicked)

    def set_running(self, running):
        """运行期间禁用完整运行按钮、显示进度条"""
        self.run_button.setEnabled(not running)
        self.run_button.setText("运行中…" if running else "完整运行")
        if running:
            self.progress.setVisible(True)
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.setVisible(False)

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

    def append_separator(self, text):
        """在控制台插入一段分隔说明，便于区分多次运行"""
        self.update_console(f"\n{'=' * 60}\n{text}\n{'=' * 60}\n\n")

    @staticmethod
    def color_for(line):
        """按日志前缀返回着色，返回 None 表示使用主题默认文字颜色"""
        for keyword, color in LOG_LINE_COLORS:
            if keyword in line:
                return color
        return None

    def update_console(self, message):
        """更新控制台显示：逐行着色并自动滚动到底部"""
        cursor = self.textbox.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        for line in message.splitlines(keepends=True):
            fmt = QTextCharFormat()
            color = self.color_for(line)
            if color:
                fmt.setForeground(QColor(color))
            cursor.insertText(line, fmt)

        self.textbox.setTextCursor(cursor)
        if self.auto_scroll:
            self.textbox.ensureCursorVisible()
            scrollbar = self.textbox.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
