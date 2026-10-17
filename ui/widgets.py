# -*- coding: utf-8 -*-
"""基础组件：整跑开关与任务行（均已 Fluent 化）。"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QLabel, QVBoxLayout
from qfluentwidgets import SimpleCardWidget, SwitchButton

from . import theme
from .icons import IconButton, StatusIcon


class ToggleSwitch(SwitchButton):
    """Fluent 开关包装：补齐 isCheckable()/click()，与旧代码的按钮语义保持一致"""

    def isCheckable(self):
        return True

    def click(self):
        self.setChecked(not self.isChecked())


class TaskRow(SimpleCardWidget):
    """单行任务：今日状态 + 名称/上次运行时间 + 齿轮 + 运行 + 开关"""

    run_clicked = pyqtSignal(str)
    config_clicked = pyqtSignal(str)
    switch_toggled = pyqtSignal(str, bool)

    def __init__(self, entry, switch_on=True, parent=None):
        super().__init__(parent)
        self.key = entry.key
        self.title = entry.title
        self.entry = entry
        self.switch_on = switch_on
        self.running = False
        self.today_done = False
        self.setObjectName("TaskRow")
        self.setFixedHeight(theme.HEIGHT_TASK_ROW)
        self.setBorderRadius(theme.RADIUS_CARD)
        self.init_ui()
        self.set_switch(switch_on)
        self._apply_row_style()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_XL, theme.SPACE_SM, theme.SPACE_XL, theme.SPACE_SM)
        layout.setSpacing(theme.SPACE_MD)

        # 最左：今日状态
        self.status_icon = StatusIcon()
        layout.addWidget(self.status_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        # 中间：任务名 + 上次运行时间
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        self.name_label = QLabel(self.title)
        self.name_label.setFont(
            QFont(theme.FONT_FAMILY_UI, theme.FONT_SIZE_BODY, QFont.Weight.Bold)
        )

        self.time_label = QLabel("上次运行 暂无记录")
        self.time_label.setFont(QFont(theme.FONT_FAMILY_UI, theme.FONT_SIZE_SMALL))

        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.time_label)
        layout.addLayout(text_layout, 1)

        # 右侧：齿轮 / 运行 / 开关
        self.config_button = IconButton("gear", "配置该任务（暂未开放）")
        self.run_button = IconButton("play", "单独运行该任务")
        self.switch = ToggleSwitch()
        self.switch.setToolTip("开启后参与「完整运行」，关闭则完整运行时跳过")

        layout.addWidget(self.config_button)
        layout.addWidget(self.run_button)
        layout.addWidget(self.switch)

        self.config_button.clicked.connect(lambda: self.config_clicked.emit(self.key))
        self.run_button.clicked.connect(lambda: self.run_clicked.emit(self.key))
        self.switch.checkedChanged.connect(self.on_switch_toggled)

    # ---- 状态 ----

    def set_today_done(self, done):
        """刷新今日完成状态图标（运行中时保持运行图标）"""
        self.today_done = bool(done)
        if not self.running:
            self.status_icon.set_state("done" if self.today_done else "pending")

    def set_running(self, running):
        """切换运行中状态"""
        self.running = bool(running)
        if self.running:
            self.status_icon.set_state("running")
        else:
            self.status_icon.set_state("done" if self.today_done else "pending")
        self._apply_row_style()

    def set_last_time(self, moment):
        """刷新上次运行时间，moment 为 None 表示尚无记录"""
        if moment is None:
            self.time_label.setText("上次运行 暂无记录")
        else:
            self.time_label.setText(f"上次运行 {moment.strftime('%m-%d %H:%M')}")

    def set_busy(self, busy):
        """运行期间禁用该行的交互控件，状态与文字保持只读展示"""
        self.config_button.setEnabled(not busy)
        self.run_button.setEnabled(not busy)
        self.switch.setEnabled(not busy)

    # ---- 开关 ----

    def set_switch(self, on):
        """程序化设置开关状态（不触发写盘信号）"""
        self.switch.blockSignals(True)
        self.switch.setChecked(bool(on))
        self.switch.blockSignals(False)
        self.switch_on = bool(on)
        self._apply_row_style()

    def on_switch_toggled(self, checked):
        """用户拨动开关：更新外观并通知外部持久化"""
        self.switch_on = bool(checked)
        self._apply_row_style()
        self.switch_toggled.emit(self.key, self.switch_on)

    # ---- 外观 ----

    def _apply_row_style(self):
        """关闭「完整运行」的任务整行半透明，直观表达不参与整跑"""
        if not hasattr(self, "_opacity_effect"):
            self._opacity_effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0 if (self.switch_on or self.running) else 0.55)

    def visual_opacity(self):
        """当前行透明度（供测试断言使用）"""
        return self._opacity_effect.opacity() if hasattr(self, "_opacity_effect") else 1.0
