# -*- coding: utf-8 -*-
"""基础组件：整跑开关与任务行。"""

from PyQt6.QtCore import Qt, QSize, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from . import theme
from .icons import IconButton, StatusIcon


class ToggleSwitch(QAbstractButton):
    """自绘开关：开启为蓝底白钮，关闭为灰底白钮（不引入图片资源）"""

    WIDTH = theme.SIZE_TOGGLE_WIDTH
    HEIGHT = theme.SIZE_TOGGLE_HEIGHT

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

    def sizeHint(self):
        return QSize(self.WIDTH, self.HEIGHT)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        if not self.isEnabled():
            track = QColor(theme.COLOR_TRACK_DISABLED)
        elif self.isChecked():
            track = QColor(theme.COLOR_ACCENT)
        else:
            track = QColor(theme.COLOR_TRACK_OFF)

        track_top = 3
        track_height = self.HEIGHT - 6
        painter.setBrush(track)
        painter.drawRoundedRect(
            QRectF(0, track_top, self.WIDTH, track_height),
            track_height / 2,
            track_height / 2,
        )

        knob_diameter = 16
        knob_x = self.WIDTH - knob_diameter - 4 if self.isChecked() else 4
        painter.setBrush(QColor(theme.COLOR_KNOB))
        painter.drawEllipse(
            QRectF(knob_x, (self.HEIGHT - knob_diameter) / 2, knob_diameter, knob_diameter)
        )
        painter.end()


class TaskRow(QFrame):
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
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.init_ui()
        self.set_switch(switch_on)
        self._apply_row_style()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_LG, theme.SPACE_SM, theme.SPACE_LG, theme.SPACE_SM)
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
        self.switch.toggled.connect(self.on_switch_toggled)

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
        if self.running:
            background, border = theme.COLOR_ROW_BG_RUNNING, theme.COLOR_ACCENT
        elif self.switch_on:
            background, border = theme.COLOR_CARD_BG, theme.COLOR_ROW_BORDER
        else:
            background, border = theme.COLOR_ROW_BG_OFF, theme.COLOR_ROW_BORDER_OFF

        self.setStyleSheet(f"""
            QFrame#TaskRow {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: {theme.RADIUS_CARD}px;
            }}
            QFrame#TaskRow:hover {{
                border-color: {theme.COLOR_ACCENT};
            }}
        """)

        # 关闭的任务整行文字变浅，明确表达「不参与完整运行」
        name_color = theme.COLOR_TEXT_PRIMARY if self.switch_on else theme.COLOR_TEXT_MUTED
        time_color = theme.COLOR_TEXT_TERTIARY if self.switch_on else theme.COLOR_TEXT_DISABLED
        self.name_label.setStyleSheet(
            f"color: {name_color}; background: transparent; border: none;"
        )
        self.time_label.setStyleSheet(
            f"color: {time_color}; background: transparent; border: none; "
            f"font-size: {theme.FONT_SIZE_SMALL}px;"
        )
