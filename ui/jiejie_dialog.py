# -*- coding: utf-8 -*-
"""「结界养成设置」弹窗：按账号配置结界卡放置顺序与寄养优先级。

与 ``settings_dialog`` / ``after_run_dialog`` / ``thirty_dialog`` 刻意分开：
那三个分别管界面偏好、完成动作与寮三十任务参数，这个只管结界养成一个任务。
四个配置入口各进各的弹窗，弹窗里也不混放无关项——进错了页面一眼就能看出来。

读写与归一化全在 ``ui/jiejie_settings.py``（不依赖 Qt），这里只负责摆放控件与联动。
"""

from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    HeaderCardWidget,
    MessageBoxBase,
    SubtitleLabel,
)

import Lib

from . import jiejie_settings as js
from . import theme

# 控件尺寸：四个优先级下拉按「两行两列」摆放，两列合计约 500px，
# 加上卡片左右各 24px 内边距，680px 的弹窗宽度刚好不挤。
COMBO_WIDTH = 132
CARD_LABEL_WIDTH = 108
PRIORITY_LABEL_WIDTH = 76


class _AccountCard(QWidget):
    """单个账号的配置卡片：一个放置下拉 + 四个优先级下拉

    **为什么用组合而不是继承 ``HeaderCardWidget``**：那个类的 ``__init__`` 挂了
    ``@__init__.register`` 重载分发，子类一旦改了构造签名，``super().__init__(title, parent)``
    会被分派回子类自己的 ``__init__(parent)``，直接 TypeError。组合一层最稳。

    **为什么每张卡片各自持有一份 ``_syncing``**：两个账号的配置互相独立，
    共用一份标志会让「改 master」顺带压掉「改 slaves」期间的信号处理。
    """

    def __init__(self, account, role, settings, parent=None):
        super().__init__(parent)
        self.account = account
        self._syncing = False
        self._warnings = []

        title = f"{account}（{role}）" if role else account
        self.header = HeaderCardWidget(title, self)
        # 便于测试与外部读取卡片标题（与 HeaderCardWidget 的属性同名）
        self.headerLabel = self.header.headerLabel

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.header)

        content = QVBoxLayout()
        content.setSpacing(theme.SPACE_LG)

        # ---- 第一行：优先放置结界卡 ----
        card_row = QHBoxLayout()
        card_row.setSpacing(theme.SPACE_MD)
        card_label = BodyLabel("优先放置结界卡", self)
        card_label.setFixedWidth(CARD_LABEL_WIDTH)
        card_row.addWidget(card_label)

        self.card_combo = ComboBox(self)
        self.card_combo.addItems(list(js.CARD_OPTIONS))
        self.card_combo.setCurrentText(settings["card"])
        self.card_combo.setFixedWidth(COMBO_WIDTH)
        card_row.addWidget(self.card_combo)
        card_row.addStretch()
        content.addLayout(card_row)

        # ---- 第二、三行：四级寄养优先级（两行两列，标签写全） ----
        hint = CaptionLabel("寄养优先（越靠前越优先，同一张卡不会出现在两级）", self)
        hint.setTextColor(
            theme.light_color("COLOR_TEXT_TERTIARY"), theme.dark_color("COLOR_TEXT_TERTIARY")
        )
        content.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(theme.SPACE_XL)
        grid.setVerticalSpacing(theme.SPACE_MD)
        self.priority_combos = []
        for index, label in enumerate(js.PRIORITY_LABELS):
            cell = QHBoxLayout()
            cell.setSpacing(theme.SPACE_SM)
            item = BodyLabel(label, self)
            item.setFixedWidth(PRIORITY_LABEL_WIDTH)
            cell.addWidget(item)

            combo = ComboBox(self)
            combo.addItems(list(js.PRIORITY_OPTIONS))
            combo.setCurrentText(settings["priority"][index])
            combo.setFixedWidth(COMBO_WIDTH)
            cell.addWidget(combo)

            grid.addLayout(cell, index // 2, index % 2)
            self.priority_combos.append(combo)

        content.addLayout(grid)
        self.header.viewLayout.addLayout(content)

        self.card_combo.currentIndexChanged.connect(lambda _: self._on_priority_changed())
        for combo in self.priority_combos:
            combo.currentIndexChanged.connect(lambda _: self._on_priority_changed())

        self._refresh_priority_enabled()

    # ---- 联动 ----

    def _on_priority_changed(self):
        """任一级变化后：归一化 → 回填四个下拉 → 重算每级的可选项

        归一化与任务层共用 ``Lib.normalize_jiejie_priority``：先出现者保留，
        撞车的那个让位给池中第一个空闲值。界面与运行时的规则完全一致，
        所以「界面上能摆出来的」必然「程序能接受」。
        """
        if self._syncing:          # 程序化 setCurrentText 会再次触发信号
            return
        self._syncing = True
        try:
            current = [combo.currentText() for combo in self.priority_combos]
            normalized = Lib.normalize_jiejie_priority(current, self._warnings)
            for combo, value in zip(self.priority_combos, normalized):
                if combo.currentText() != value:
                    combo.setCurrentText(value)
            self._refresh_priority_enabled()
        finally:
            self._syncing = False

    def _refresh_priority_enabled(self):
        """第 N 级灰掉第 1..N-1 级的当前值

        单向是刻意的（与寮三十弹窗同一教训的反面）：双向互斥在只有 2 个选项时
        会把两个下拉各自锁死。这里第 N 级永远还剩自己的值 + 后面各级的值，
        改得动；第 4 级天然只剩一个值，正好表达「就是剩下的那个」。
        """
        taken = []
        for combo in self.priority_combos:
            chosen = combo.currentText()
            for item_index in range(combo.count()):
                combo.setItemEnabled(item_index, combo.itemText(item_index) not in taken)
            taken.append(chosen)

    # ---- 取值 ----

    def values(self):
        return {
            "card": self.card_combo.currentText(),
            "priority": [combo.currentText() for combo in self.priority_combos],
        }


class JiejieSettingsDialog(MessageBoxBase):
    """结界养成配置弹窗；确定后由 ``validate()`` 直接落盘"""

    # 保存成功后主窗口用它写一行控制台反馈，不再写死寮三十文案
    SAVED_MESSAGE = "结界养成设置已保存到 config/Setting.yml"

    def __init__(self, parent=None):
        super().__init__(parent)

        current = js.load_jiejie_settings()

        self.titleLabel = SubtitleLabel("结界养成设置", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.hint_label = CaptionLabel(
            "按账号分别配置；保存后写入 config/Setting.yml，任务运行时按当前账号读取。", self
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.setTextColor(
            theme.light_color("COLOR_TEXT_TERTIARY"), theme.dark_color("COLOR_TEXT_TERTIARY")
        )
        self.viewLayout.addWidget(self.hint_label)

        # 一个账号一张卡片，竖排；账号只有两个时正好一屏看完，
        # 账号变多只是变高（用户已确认先不考虑多账号场景）。
        self.cards = []
        for account in current["accounts"]:
            card = _AccountCard(
                account,
                current["roles"].get(account),
                current["settings"][account],
                self,
            )
            self.viewLayout.addWidget(card)
            self.cards.append(card)

        # 打开时若有回落，直接告诉用户改了什么，避免「我明明设过」的困惑
        if current["warnings"]:
            self.warning_label = CaptionLabel("；".join(current["warnings"]), self)
            self.warning_label.setWordWrap(True)
            self.warning_label.setTextColor(
                theme.light_color("COLOR_LOG_SKIP"), theme.dark_color("COLOR_LOG_SKIP")
            )
            self.viewLayout.addWidget(self.warning_label)

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(680)

    def values(self):
        """当前弹窗里全部账号的配置，结构直接喂给 ``save_jiejie_settings``"""
        return {card.account: card.values() for card in self.cards}

    def validate(self):
        """点「保存」时调用；写盘失败就弹提示并保持弹窗打开，方便重试"""
        if js.save_jiejie_settings(self.values()):
            return True

        QMessageBox.warning(
            self,
            "保存失败",
            "无法写入 config/Setting.yml。\n\n"
            "请检查文件是否被设为只读、目录是否可写；"
            "若配置文件已损坏，请先手动修复再保存。",
        )
        return False
