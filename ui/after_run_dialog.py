# -*- coding: utf-8 -*-
"""「完整运行设置」弹窗：完整运行成功结束后的动作。

与 ``settings_dialog.SettingsDialog`` 刻意分开：那个管主题与日志偏好，
这个只管两个完成动作。两个齿轮各进各的弹窗，弹窗里也不混放无关项——
进错了页面一眼就能看出来。

依赖方向与 ``settings_dialog`` 同级：只 import ``prefs`` 与 ``widgets``，
不反向依赖 ``panels`` / ``window``。
"""

from PyQt6.QtWidgets import QHBoxLayout
from qfluentwidgets import BodyLabel, CaptionLabel, MessageBoxBase, SubtitleLabel

from . import prefs
from . import theme
from .widgets import ToggleSwitch


class AfterRunDialog(MessageBoxBase):
    """完整运行完成后的动作设置；确定后由调用方读取 values() 并落盘"""

    def __init__(self, parent=None):
        super().__init__(parent)
        current = prefs.load_prefs()

        self.titleLabel = SubtitleLabel("完整运行设置", self)
        self.viewLayout.addWidget(self.titleLabel)

        # 说明文字很重要：用户勾了睡眠却去点单跑，发现没睡会以为是 bug
        self.hint_label = CaptionLabel(
            "这些动作只在「完整运行」成功结束后生效，单独运行与中断都不会触发。", self
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.setTextColor(
            theme.light_color("COLOR_TEXT_TERTIARY"), theme.dark_color("COLOR_TEXT_TERTIARY")
        )
        self.viewLayout.addWidget(self.hint_label)

        # 关闭模拟器
        close_row = QHBoxLayout()
        close_row.addWidget(BodyLabel("关闭模拟器", self))
        close_row.addStretch()
        self.close_emulator_switch = ToggleSwitch(self)
        self.close_emulator_switch.setOnText("")
        self.close_emulator_switch.setOffText("")
        self.close_emulator_switch.setToolTip("关闭所有由本程序管理的模拟器窗口，未保存的进度会丢失")
        self.close_emulator_switch.setChecked(current["after_run_close_emulator"])
        close_row.addWidget(self.close_emulator_switch)
        self.viewLayout.addLayout(close_row)

        # 让电脑睡眠
        sleep_row = QHBoxLayout()
        sleep_row.addWidget(BodyLabel("让电脑睡眠", self))
        sleep_row.addStretch()
        self.sleep_switch = ToggleSwitch(self)
        self.sleep_switch.setOnText("")
        self.sleep_switch.setOffText("")
        self.sleep_switch.setToolTip("睡眠（S3），不是休眠；睡眠失败请检查电源设置")
        self.sleep_switch.setChecked(current["after_run_sleep"])
        sleep_row.addWidget(self.sleep_switch)
        self.viewLayout.addLayout(sleep_row)

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(420)

    def values(self):
        """当前对话框中的两个动作开关"""
        return {
            "after_run_close_emulator": self.close_emulator_switch.isChecked(),
            "after_run_sleep": self.sleep_switch.isChecked(),
        }
