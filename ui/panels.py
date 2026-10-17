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
from qfluentwidgets import IndeterminateProgressBar, PrimaryPushButton, TextEdit

from main import TASK_REGISTRY, entry_done_today, latest_completion, read_completions, read_task_switches
from . import theme
from .widgets import TaskRow

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        self.textbox = None
        self.run_button = None
        self.progress = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.SPACE_SM)

        self.create_console_area(layout)
        self.create_progress(layout)
        self.create_button_area(layout)

        self.setLayout(layout)

    def create_console_area(self, parent_layout):
        """创建控制台输出区域"""
        self.textbox = TextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setFont(QFont(theme.FONT_FAMILY_LOG, theme.FONT_SIZE_LOG))
        self.textbox.setPlaceholderText("运行日志会显示在这里")
        parent_layout.addWidget(self.textbox, 1)

    def create_progress(self, parent_layout):
        """运行中的不确定进度条，默认隐藏"""
        self.progress = IndeterminateProgressBar(self)
        self.progress.setVisible(False)
        parent_layout.addWidget(self.progress)

    def create_button_area(self, parent_layout):
        """创建主操作按钮"""
        self.run_button = PrimaryPushButton("完整运行")
        self.run_button.setFixedHeight(theme.SIZE_RUN_BUTTON_HEIGHT)

        button_container = QFrame()
        button_container.setStyleSheet("background: transparent;")
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
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
        self.textbox.ensureCursorVisible()

        scrollbar = self.textbox.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
