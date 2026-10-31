# -*- coding: utf-8 -*-
"""「寮三十设置」弹窗：主副账号 + 一周七天的副本与次数。

与 ``settings_dialog`` / ``after_run_dialog`` 刻意分开：那两个管界面偏好与完成动作，
这个只管寮三十这一个任务的任务参数。三个入口各进各的弹窗，弹窗里也不混放无关项——
进错了页面一眼就能看出来。

读写与归一化全在 ``ui/thirty_settings.py``（不依赖 Qt），这里只负责摆放控件与互斥联动。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QMessageBox
from qfluentwidgets import BodyLabel, CaptionLabel, ComboBox, MessageBoxBase, SubtitleLabel

from . import theme
from . import thirty_settings as ts

# 一列下拉的固定宽度；7 列 + 左侧标签恰好落在 800px 弹窗里
COMBO_WIDTH = 96
LABEL_WIDTH = 40


class ThirtySettingsDialog(MessageBoxBase):
    """寮三十配置弹窗；确定后由 ``validate()`` 直接落盘"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._syncing = False

        current = ts.load_thirty_settings()
        self.accounts = current["accounts"]

        self.titleLabel = SubtitleLabel("寮三十设置", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.hint_label = CaptionLabel(
            "按星期配置副本与次数；次数 0 表示当天不刷。保存后写入 config/Setting.yml。", self
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.setTextColor(
            theme.light_color("COLOR_TEXT_TERTIARY"), theme.dark_color("COLOR_TEXT_TERTIARY")
        )
        self.viewLayout.addWidget(self.hint_label)

        self._build_account_row(current)
        self._build_week_table(current)

        # 打开时若有回落，直接告诉用户改了什么，避免"我明明设过"的困惑
        if current["warnings"]:
            self.warning_label = CaptionLabel("；".join(current["warnings"]), self)
            self.warning_label.setWordWrap(True)
            self.warning_label.setTextColor(
                theme.light_color("COLOR_LOG_SKIP"), theme.dark_color("COLOR_LOG_SKIP")
            )
            self.viewLayout.addWidget(self.warning_label)

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(800)

    # ---- 构建 ----

    def _build_account_row(self, current):
        """主副账号：两个下拉，选项都来自 Setting.yml 的启动项"""
        row = QHBoxLayout()
        row.setSpacing(theme.SPACE_MD)

        row.addWidget(BodyLabel("主账号", self))
        self.primary_combo = ComboBox(self)
        self.primary_combo.addItems(self.accounts)
        self.primary_combo.setCurrentText(current["primary"])
        self.primary_combo.setFixedWidth(120)
        row.addWidget(self.primary_combo)

        row.addSpacing(theme.SPACE_XXL)
        row.addWidget(BodyLabel("副账号", self))
        self.secondary_combo = ComboBox(self)
        self.secondary_combo.addItems(self.accounts)
        self.secondary_combo.setCurrentText(current["secondary"])
        self.secondary_combo.setFixedWidth(120)
        row.addWidget(self.secondary_combo)

        row.addStretch()
        self.viewLayout.addLayout(row)

        self.primary_combo.currentIndexChanged.connect(
            lambda _: self._on_account_changed(self.primary_combo, self.secondary_combo)
        )
        self.secondary_combo.currentIndexChanged.connect(
            lambda _: self._on_account_changed(self.secondary_combo, self.primary_combo)
        )
        self._refresh_account_enabled()

    def _build_week_table(self, current):
        """横着铺：表头 7 个星期，下面两行分别是副本与次数"""
        head = QHBoxLayout()
        head.setSpacing(theme.SPACE_MD)
        head.addSpacing(LABEL_WIDTH + theme.SPACE_MD)
        for label in ts.WEEK_LABELS:
            item = BodyLabel(label, self)
            item.setFixedWidth(COMBO_WIDTH)
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            head.addWidget(item)
        head.addStretch()
        self.viewLayout.addLayout(head)

        self.fuben_combos = self._build_row("副本", list(ts.FUBEN_OPTIONS), current["fuben"])
        self.times_combos = self._build_row("次数", list(ts.TIMES_OPTIONS), current["times"])

    def _build_row(self, title, options, values):
        """一行：左侧标签 + 7 个下拉（下拉里一律显示纯文本，取值时再按需转换）"""
        row = QHBoxLayout()
        row.setSpacing(theme.SPACE_MD)

        label = BodyLabel(title, self)
        label.setFixedWidth(LABEL_WIDTH)
        row.addWidget(label)

        texts = [str(option) for option in options]
        combos = []
        for value in values:
            combo = ComboBox(self)
            combo.addItems(texts)
            combo.setCurrentText(str(value))
            combo.setFixedWidth(COMBO_WIDTH)
            row.addWidget(combo)
            combos.append(combo)
        row.addStretch()

        self.viewLayout.addLayout(row)
        return combos

    # ---- 主副账号互斥 ----

    def _on_account_changed(self, changed, other):
        """一方改选后：对方若撞车则自动切走，然后刷新两边的灰化"""
        if self._syncing:      # 程序化 setCurrentIndex 会再次触发信号
            return
        self._syncing = True
        try:
            if other.currentText() == changed.currentText():
                for index in range(other.count()):
                    if other.itemText(index) != changed.currentText():
                        other.setCurrentIndex(index)
                        break
            self._refresh_account_enabled()
        finally:
            self._syncing = False

    def _refresh_account_enabled(self):
        """两个框各自禁用「对方当前选中」的项"""
        for me, other in ((self.primary_combo, self.secondary_combo),
                          (self.secondary_combo, self.primary_combo)):
            chosen = other.currentText()
            for index in range(me.count()):
                me.setItemEnabled(index, me.itemText(index) != chosen)

    # ---- 取值与落盘 ----

    def values(self):
        """当前弹窗里的四项配置（下标与 WEEK_LABELS 一一对应）"""
        return {
            "primary": self.primary_combo.currentText(),
            "secondary": self.secondary_combo.currentText(),
            "fuben": [combo.currentText() for combo in self.fuben_combos],
            "times": [int(combo.currentText()) for combo in self.times_combos],
        }

    def validate(self):
        """点「保存」时调用；写盘失败就弹提示并保持弹窗打开，方便重试"""
        values = self.values()
        if ts.save_thirty_settings(
            values["primary"], values["secondary"], values["fuben"], values["times"]
        ):
            return True

        QMessageBox.warning(
            self,
            "保存失败",
            "无法写入 config/Setting.yml。\n\n"
            "请检查文件是否被设为只读、目录是否可写；"
            "若配置文件已损坏，请先手动修复再保存。",
        )
        return False
