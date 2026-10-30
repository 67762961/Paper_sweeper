# -*- coding: utf-8 -*-
"""基础组件：整跑开关、任务行与倒计时对话框（均已 Fluent 化）。"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    MessageBoxBase,
    SimpleCardWidget,
    SubtitleLabel,
    SwitchButton,
)

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

        # 用 Fluent 标签而不是裸 QLabel：文字颜色会随深浅色主题自动切换，
        # 否则深色主题下仍是黑色文字，几乎看不见
        self.name_label = BodyLabel(self.title, self)
        self.name_label.setFont(
            QFont(theme.FONT_FAMILY_UI, theme.FONT_SIZE_TASK_NAME, QFont.Weight.Bold)
        )
        self.name_label.setTextColor(
            theme.light_color("COLOR_TEXT_PRIMARY"), theme.dark_color("COLOR_TEXT_PRIMARY")
        )

        self.time_label = CaptionLabel("上次运行 暂无记录", self)
        self.time_label.setFont(QFont(theme.FONT_FAMILY_UI, theme.FONT_SIZE_TASK_TIME))
        self.time_label.setTextColor(
            theme.light_color("COLOR_TEXT_TERTIARY"), theme.dark_color("COLOR_TEXT_TERTIARY")
        )

        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.time_label)
        layout.addLayout(text_layout, 1)

        # 右侧：齿轮 / 运行 / 开关
        self.config_button = IconButton("gear", "配置该任务（暂未开放）")
        self.run_button = IconButton("play", "单独运行该任务")
        self.switch = ToggleSwitch()
        self.switch.setOnText("")
        self.switch.setOffText("")
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


class CountdownDialog(MessageBoxBase):
    """倒计时确认框：N 秒后自动执行，期间可以取消

    用在「完整运行结束后关闭模拟器 / 睡眠」之前——那两个动作一个会丢进度、
    一个会让屏幕黑掉，直接执行容易让人措手不及。给一段可取消的缓冲期。

    为什么不用 InfoBar：InfoBar 没有「倒计时结束回调 + 可取消」的组合能力，
    关闭 InfoBar 也无法可靠地通知调用方。

    **倒计时在 exec() 里启动，不在单独的 start() 里**：调用方拿到对话框后
    按 QDialog 的惯例直接 exec()，如果定时器只在别的方法里启动，就会漏掉，
    表现为「弹窗出来了但数字一直停在 N 秒、也不会自动关闭」。
    """

    def __init__(self, parent=None, seconds=10, action_text=""):
        super().__init__(parent)
        self.remaining = int(seconds)
        self.action_text = action_text or "执行后续动作"

        self.titleLabel = SubtitleLabel("完整运行已结束", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.countdown_label = BodyLabel("", self)
        self.viewLayout.addWidget(self.countdown_label)

        self.hint_label = CaptionLabel("点击「立即执行」跳过等待，或点「取消」放弃本次动作", self)
        self.hint_label.setWordWrap(True)
        self.hint_label.setTextColor(
            theme.light_color("COLOR_TEXT_TERTIARY"), theme.dark_color("COLOR_TEXT_TERTIARY")
        )
        self.viewLayout.addWidget(self.hint_label)

        self.yesButton.setText("立即执行")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(440)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._refresh_text()

    # ---- 倒计时 ----

    def exec(self):
        """显示对话框并开始倒计时（阻塞到用户选择或倒计时归零）

        重写而不是新增一个 start()：调用方按 QDialog 惯例直接 exec()，
        把倒计时绑在这里才不会漏启动。
        """
        self._timer.start()
        try:
            return super().exec()
        finally:
            # 用户点按钮、倒计时归零、或窗口被外部关闭都要停表，
            # 否则对话框已销毁而定时器还在跑
            self._timer.stop()

    def _tick(self):
        """每秒递减；归零自动接受"""
        self.remaining -= 1
        if self.remaining <= 0:
            self._timer.stop()
            self.accept()
            return
        self._refresh_text()

    def _refresh_text(self):
        self.countdown_label.setText(f"{self.remaining} 秒后将{self.action_text}")

    def stop(self):
        """停止倒计时（窗口被外部关闭时用，避免定时器继续跑）"""
        self._timer.stop()
