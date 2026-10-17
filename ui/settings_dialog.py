# -*- coding: utf-8 -*-
"""设置弹窗：主题、日志偏好与日志目录入口。"""

import logging
import os

from PyQt6.QtWidgets import QHBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    FluentIcon,
    MessageBoxBase,
    PushButton,
    SubtitleLabel,
)

from . import prefs
from .theme_manager import THEME_LABELS
from .widgets import ToggleSwitch

APP_VERSION = "1.3.0"
LOGS_DIR = "logs"

THEME_ORDER = ("light", "dark", "auto")


def open_path(path):
    """打开目录或文件（独立函数，便于测试时替换）"""
    if hasattr(os, "startfile"):
        os.startfile(path)  # noqa: S606 - Windows 下打开资源管理器
    else:
        logging.warning("当前平台不支持直接打开路径: %s", path)


class SettingsDialog(MessageBoxBase):
    """设置对话框；确定后由调用方读取 values() 并落盘"""

    def __init__(self, parent=None):
        super().__init__(parent)
        current = prefs.load_prefs()

        self.titleLabel = SubtitleLabel("设置", self)
        self.viewLayout.addWidget(self.titleLabel)

        # 主题
        theme_row = QHBoxLayout()
        theme_row.addWidget(BodyLabel("主题", self))
        theme_row.addStretch()
        self.theme_combo = ComboBox(self)
        self.theme_combo.addItems([THEME_LABELS[mode] for mode in THEME_ORDER])
        self.theme_combo.setCurrentIndex(THEME_ORDER.index(current["theme"]))
        theme_row.addWidget(self.theme_combo)
        self.viewLayout.addLayout(theme_row)

        # 日志自动滚动
        scroll_row = QHBoxLayout()
        scroll_row.addWidget(BodyLabel("日志自动滚动", self))
        scroll_row.addStretch()
        self.auto_scroll_switch = ToggleSwitch(self)
        self.auto_scroll_switch.setOnText("")
        self.auto_scroll_switch.setOffText("")
        self.auto_scroll_switch.setChecked(current["log_auto_scroll"])
        scroll_row.addWidget(self.auto_scroll_switch)
        self.viewLayout.addLayout(scroll_row)

        # 日志字号
        font_row = QHBoxLayout()
        font_row.addWidget(BodyLabel("日志字号", self))
        font_row.addStretch()
        self.font_combo = ComboBox(self)
        self.font_combo.addItems([f"{size} pt" for size in prefs.VALID_LOG_SIZES])
        self.font_combo.setCurrentIndex(list(prefs.VALID_LOG_SIZES).index(current["log_font_size"]))
        font_row.addWidget(self.font_combo)
        self.viewLayout.addLayout(font_row)

        # 打开日志目录
        self.open_logs_button = PushButton("打开日志目录", self, FluentIcon.FOLDER)
        self.open_logs_button.clicked.connect(self.open_logs_dir)
        self.viewLayout.addWidget(self.open_logs_button)

        self.version_label = CaptionLabel(f"Paper Sweeper v{APP_VERSION}", self)
        self.viewLayout.addWidget(self.version_label)

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(460)

    def open_logs_dir(self):
        """确保日志目录存在后打开（便于用户排查问题）"""
        os.makedirs(LOGS_DIR, exist_ok=True)
        open_path(os.path.abspath(LOGS_DIR))

    def values(self):
        """当前对话框中的偏好值"""
        return {
            "theme": THEME_ORDER[self.theme_combo.currentIndex()],
            "log_auto_scroll": self.auto_scroll_switch.isChecked(),
            "log_font_size": prefs.VALID_LOG_SIZES[self.font_combo.currentIndex()],
        }
