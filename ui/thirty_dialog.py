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

    # 保存成功后的控制台反馈，由 ui/window.on_task_config 读取（不要写死在那一边）
    SAVED_MESSAGE = "寮三十设置已保存到 config/Setting.yml"

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
        """主副账号：两个下拉，选项都来自 Setting.yml 的启动项

        约束是**单向**的：主账号可以选任意账号，副账号只避开「主账号当前值」。
        双向灰化在只有两个账号时会把两个下拉都锁死（各自只剩自己），
        所以「主副互换」这个最常见的操作反而做不了。
        """
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

        # 两个账号在游戏里分工不同，写清楚免得选反
        self.role_hint = CaptionLabel("主账号作为打手，副账号作为司机", self)
        self.role_hint.setTextColor(
            theme.light_color("COLOR_TEXT_TERTIARY"), theme.dark_color("COLOR_TEXT_TERTIARY")
        )
        row.addWidget(self.role_hint)

        row.addStretch()
        self.viewLayout.addLayout(row)

        self.primary_combo.currentIndexChanged.connect(lambda _: self._on_account_changed())
        self.secondary_combo.currentIndexChanged.connect(lambda _: self._on_account_changed())
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

    # ---- 主副账号约束（单向：只有副账号让） ----

    def _on_account_changed(self):
        """账号任一变化后：副账号让开主账号当前值，主账号不受限制"""
        if self._syncing:      # 程序化 setCurrentText 会再次触发信号
            return
        self._syncing = True
        try:
            if self.secondary_combo.currentText() == self.primary_combo.currentText():
                target = self._first_other_account(self.primary_combo.currentText())
                if target is not None:
                    self.secondary_combo.setCurrentText(target)
            self._refresh_account_enabled()
        finally:
            self._syncing = False

    def _first_other_account(self, exclude):
        """列表里第一个 != exclude 的账号；只有一个账号时返回 None"""
        return next((name for name in self.accounts if name != exclude), None)

    def _refresh_account_enabled(self):
        """主账号全放开；副账号只灰掉「主账号当前值」

        单向是刻意的：双向灰化在只有两个账号时会让两个下拉各自只剩自己，
        主副互换就再也做不到了（这正是之前那个 bug）。
        """
        for index in range(self.primary_combo.count()):
            self.primary_combo.setItemEnabled(index, True)

        chosen = self.primary_combo.currentText()
        for index in range(self.secondary_combo.count()):
            self.secondary_combo.setItemEnabled(
                index, self.secondary_combo.itemText(index) != chosen
            )

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
