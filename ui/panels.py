# -*- coding: utf-8 -*-
"""面板：左侧任务列表与右侧日志控制台。"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from main import TASK_REGISTRY, entry_done_today, latest_completion, read_completions, read_task_switches
from . import theme
from .widgets import TaskRow


class LeftPanel(QFrame):
    """左侧任务列表面板：7 行对应 TASK_REGISTRY，行内提供单跑与整跑开关"""

    task_run_clicked = pyqtSignal(str)
    task_config_clicked = pyqtSignal(str)
    task_toggled = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = {}
        self.init_ui()
        self.refresh()

    def init_ui(self):
        self.setFixedWidth(theme.WIDTH_LEFT_PANEL)
        self.setStyleSheet(f"background-color: {theme.COLOR_PANEL_BG};")

        layout = QVBoxLayout()
        layout.setContentsMargins(theme.SPACE_LG, theme.SPACE_SM, theme.SPACE_LG, theme.SPACE_SM)
        layout.setSpacing(theme.SPACE_XS)

        title_label = QLabel("任务列表")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            f"font-size: {theme.FONT_SIZE_TITLE}px; font-weight: bold; margin: {theme.SPACE_XS}px;"
        )
        layout.addWidget(title_label)

        layout.addWidget(self.create_scroll_area())

        hint_label = QLabel("运行按钮单独执行 · 齿轮为配置入口（暂未开放）· 开关决定是否参与完整运行")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet(
            f"color: {theme.COLOR_TEXT_TERTIARY}; font-size: {theme.FONT_SIZE_SMALL}px;"
        )
        layout.addWidget(hint_label)

        self.setLayout(layout)

    def create_scroll_area(self):
        """按 TASK_REGISTRY 生成任务行，顺序与完整运行一致"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_content = QWidget()
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
    """右侧控制台面板"""

    run_button_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {theme.COLOR_PANEL_BG};")
        self.textbox = None
        self.run_button = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(theme.SPACE_XXL, theme.SPACE_XXL, theme.SPACE_XXL, theme.SPACE_XXL)
        layout.setSpacing(15)

        self.create_console_area(layout)
        self.create_button_area(layout)

        self.setLayout(layout)

    def create_console_area(self, parent_layout):
        """创建控制台输出文本框区域"""
        self.textbox = QTextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.COLOR_CARD_BG};
                font-family: '{theme.FONT_FAMILY_LOG}', 'Monaco', monospace;
                font-size: {theme.FONT_SIZE_LOG}px;
                border: 1px solid {theme.COLOR_ACCENT};
                border-radius: {theme.RADIUS_LOG_BOX}px;
            }}
        """)
        parent_layout.addWidget(self.textbox, 1)

    def create_button_area(self, parent_layout):
        """创建按钮区域"""
        self.run_button = QPushButton("完整运行")
        self.run_button.setFixedHeight(theme.SIZE_RUN_BUTTON_HEIGHT)
        self.run_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.COLOR_CARD_BG};
                color: {theme.COLOR_ACCENT_TEXT};
                border-color: {theme.COLOR_ACCENT};
                border-radius: {theme.RADIUS_CARD}px;
                font-size: {theme.FONT_SIZE_RUN_BUTTON}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #E6F2FF;
            }}
            QPushButton:pressed {{
                background-color: #B8DAFF;
            }}
        """)

        button_container = QFrame()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 5, 5, 5)
        button_layout.addStretch()
        button_layout.addWidget(self.run_button)
        button_container.setLayout(button_layout)

        parent_layout.addWidget(button_container)

        self.run_button.clicked.connect(self.run_button_clicked)

    def set_running(self, running):
        """运行期间禁用完整运行按钮并提示状态"""
        self.run_button.setEnabled(not running)
        self.run_button.setText("运行中…" if running else "完整运行")

    def append_separator(self, text):
        """在控制台插入一段分隔说明，便于区分多次运行"""
        self.update_console(f"\n{'=' * 78}\n{text}\n{'=' * 78}\n\n")

    def update_console(self, message):
        """更新控制台显示"""
        cursor = self.textbox.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(message)
        self.textbox.setTextCursor(cursor)
        self.textbox.ensureCursorVisible()

        scrollbar = self.textbox.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
