# -*- coding: utf-8 -*-
"""「结界养成设置」弹窗：真实控件的布局、四级互斥与落盘（不真的点保存）。

守住五件事：

1. 每个账号一张卡片，卡片数 = 「启动项」的账号数，标题带「（主）」/「（副）」；
2. 卡片里恰好 1 个放置下拉（只有太鼓/斗鱼两项，没有第三态）+ 4 个优先级下拉；
3. 四级互斥是**单向**的：第 N 级只灰掉第 1..N-1 级的当前值，所以第 4 级只剩自己；
4. 撞车时自动改派（走与任务层同一个 ``Lib.normalize_jiejie_priority``），
   四个下拉永远是 4 个不同的卡名；
5. 账号之间互不影响；``validate()`` 成功写盘、失败返回 False（弹窗不关）。

用法与 ``test_thirty_dialog.py`` 一致：``MessageBoxBase`` 必须传非 None 的 parent。
"""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")
pytest.importorskip("qfluentwidgets")

from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

_APP = QApplication.instance() or QApplication(sys.argv)

SETTING = """启动项:
  "master":
    启动命令: "a.exe -v 0"
  "slaves":
    启动命令: "a.exe -v 1"

寮三十:
  主账号: "master"
  副账号: "slaves"
  副本: ["魂虚", "魂虚", "魂虚", "魂虚", "魂虚", "魂海", "日蚀"]
  次数: [30, 30, 30, 30, 30, 30, 30]

结界养成:
  "master":
    优先结界卡: "太鼓"
    寄养优先级: [六星太鼓, 六星斗鱼, 五星太鼓, 五星斗鱼]
  "slaves":
    优先结界卡: "斗鱼"
    寄养优先级: [六星斗鱼, 六星太鼓, 五星斗鱼, 五星太鼓]
"""


def _write_setting(text=SETTING):
    import paths

    os.makedirs(paths.CONFIG_DIR, exist_ok=True)
    with open(paths.SETTING, "w", encoding="utf-8") as handle:
        handle.write(text)


def _make_dialog():
    from ui.jiejie_dialog import JiejieSettingsDialog

    host = QWidget()
    widget = JiejieSettingsDialog(host)
    return widget, host


def _drop(widget, host):
    widget.setParent(None)
    widget.deleteLater()
    host.setParent(None)
    host.deleteLater()
    _APP.processEvents()


@pytest.fixture()
def dialog(tmp_config_dir):
    """真实构造的 JiejieSettingsDialog；工作目录已由夹具切到临时目录"""
    _write_setting()
    widget, host = _make_dialog()
    yield widget
    _drop(widget, host)


def _enabled_texts(combo):
    """下拉里当前**可选**的项（setItemEnabled(False) 的会被滤掉）

    qfluentwidgets 的 ComboBox 不是 QComboBox 的薄包装：每一项是 ``combo.items[i]``
    （ComboItem），启用状态是**属性** ``isEnabled`` 而不是 Qt 那套 ``model().item(i).isEnabled()``。
    真机上禁用的项在弹出菜单里是 disabled 的 QAction，点不动。
    """
    return [combo.itemText(i) for i in range(combo.count()) if combo.items[i].isEnabled]


def _texts(combo):
    return [combo.currentText() for combo in combo]


# ------------------------------------------------------------ 布局


def test_每个账号一张卡片(dialog):
    assert [card.account for card in dialog.cards] == ["master", "slaves"]


def test_卡片标题带主副角色(dialog):
    titles = [card.headerLabel.text() for card in dialog.cards]

    assert titles[0] == "master（主）"
    assert titles[1] == "slaves（副）"


def test_没有寮三十段时标题只有账号名(tmp_config_dir):
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n')

    widget, host = _make_dialog()
    try:
        assert widget.cards[0].headerLabel.text() == "master"
    finally:
        _drop(widget, host)


def test_每张卡片一个放置下拉加四个优先级下拉(dialog):
    for card in dialog.cards:
        assert card.card_combo is not None
        assert len(card.priority_combos) == 4


def test_四个优先级下拉横排一行且标签在上方(dialog):
    """布局契约：四个下拉同一行、标签各自在下拉框正上方

    用户改过两次布局（先是「标签在左」、再是「两行两列」），最终定为横排一行 +
    标签在上。这里锁住**布局结构**而不是像素位置——离屏下不 show() 时控件
    几何还没算出来（全是默认 QRect），断言几何会假失败。
    """
    from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout

    from ui import jiejie_settings as js

    card = dialog.cards[0]
    header_layout = card.header.viewLayout
    content = header_layout.itemAt(0).layout()
    assert isinstance(content, QVBoxLayout)

    # 找那一行：横排布局，前 4 项各是一个竖排单元（第 5 项是 addStretch 占位）
    row = None
    for index in range(content.count()):
        item = content.itemAt(index).layout()
        if isinstance(item, QHBoxLayout) and item.count() >= 4:
            cells = [item.itemAt(i).layout() for i in range(4)]
            if all(isinstance(cell, QVBoxLayout) for cell in cells):
                row = item
                break
    assert row is not None, "四个优先级下拉必须放在一个横排布局里"

    for index, cell in enumerate(row.itemAt(i).layout() for i in range(4)):
        assert isinstance(cell, QVBoxLayout), "每格是竖排：标签在上、下拉在下"
        assert cell.count() == 2
        label_widget = cell.itemAt(0).widget()
        combo_widget = cell.itemAt(1).widget()
        # 第 0 项是标签、第 1 项是下拉 —— 顺序即「标签在上」
        assert label_widget.text() == js.PRIORITY_LABELS[index]
        assert combo_widget is card.priority_combos[index]

    assert [label.text() for label in card.priority_labels] == list(js.PRIORITY_LABELS)


def test_优先级下拉固定宽度不随窗口拉伸(dialog):
    """宽度固定 132：四个等宽下拉，不会因为窗口拉宽而变形"""
    from ui.jiejie_dialog import COMBO_WIDTH

    card = dialog.cards[0]
    assert COMBO_WIDTH == 132
    for combo in card.priority_combos:
        assert combo.width() == COMBO_WIDTH
        assert combo.minimumWidth() == COMBO_WIDTH
        assert combo.maximumWidth() == COMBO_WIDTH


def test_放置下拉只有太鼓与斗鱼(dialog):
    from ui.jiejie_settings import CARD_OPTIONS

    combo = dialog.cards[0].card_combo
    texts = [combo.itemText(i) for i in range(combo.count())]

    assert texts == list(CARD_OPTIONS)
    assert texts == ["太鼓", "斗鱼"], "需求只要两项，不能多出「不放置」"


def test_优先级下拉选项是四张卡(dialog):
    from ui.jiejie_settings import PRIORITY_OPTIONS

    combo = dialog.cards[0].priority_combos[0]
    texts = [combo.itemText(i) for i in range(combo.count())]

    assert texts == list(PRIORITY_OPTIONS)


def test_打开时按配置回填(dialog):
    master, slaves = dialog.cards

    assert master.card_combo.currentText() == "太鼓"
    assert _texts(master.priority_combos) == ["六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼"]
    assert slaves.card_combo.currentText() == "斗鱼"
    assert _texts(slaves.priority_combos) == ["六星斗鱼", "六星太鼓", "五星斗鱼", "五星太鼓"]


# ------------------------------------------------------------ 四级互斥


def test_第N级灰掉前N减1级的当前值(dialog):
    combos = dialog.cards[0].priority_combos

    assert _enabled_texts(combos[0]) == ["六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼"]
    assert _enabled_texts(combos[1]) == ["六星斗鱼", "五星太鼓", "五星斗鱼"]
    assert _enabled_texts(combos[2]) == ["五星太鼓", "五星斗鱼"]
    assert _enabled_texts(combos[3]) == ["五星斗鱼"]


def test_第四级天然锁定(dialog):
    """第 4 级就是「剩下的那个」，只剩自己一个值"""
    combo = dialog.cards[0].priority_combos[3]

    assert _enabled_texts(combo) == [combo.currentText()]


def test_改第一级时后级自动换走(dialog):
    """第 1 级抢了第 3 级的值 → 第 3 级让位给此刻唯一空闲的值"""
    combos = dialog.cards[0].priority_combos
    combos[0].setCurrentText("五星太鼓")

    assert _texts(combos) == ["五星太鼓", "六星斗鱼", "六星太鼓", "五星斗鱼"]
    assert len(set(_texts(combos))) == 4


def test_后级主动选前级的值会被弹回(dialog):
    combos = dialog.cards[0].priority_combos
    combos[2].setCurrentText("六星太鼓")      # 与第 1 级撞车

    assert len(set(_texts(combos))) == 4, "撞车后必须仍是四个不同的卡名"
    assert _texts(combos)[0] == "六星太鼓", "先出现者保留：第 1 级不动"


def test_反复切换始终是合法排列(dialog):
    """防 _syncing 死循环 / 残留非法状态"""
    combos = dialog.cards[0].priority_combos
    values = ["六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼"]

    for round_index in range(10):
        for index, combo in enumerate(combos):
            combo.setCurrentText(values[(index + round_index) % 4])
        current = _texts(combos)
        assert len(set(current)) == 4, f"第 {round_index} 轮出现重复: {current}"
        assert set(current) == set(values)


def test_切换后可选集跟着变(dialog):
    combos = dialog.cards[0].priority_combos
    combos[0].setCurrentText("五星斗鱼")
    # 归一化结果：五星斗鱼 → 六星斗鱼 → 五星太鼓 → 六星太鼓（原第 4 级让位）
    assert _texts(combos) == ["五星斗鱼", "六星斗鱼", "五星太鼓", "六星太鼓"]

    assert _enabled_texts(combos[1]) == ["六星太鼓", "六星斗鱼", "五星太鼓"]
    assert _enabled_texts(combos[3]) == ["六星太鼓"]


# ------------------------------------------------------------ 账号独立


def test_改一个账号不影响另一个(dialog):
    master, slaves = dialog.cards
    slaves_before = _texts(slaves.priority_combos)

    master.priority_combos[0].setCurrentText("五星斗鱼")

    assert _texts(slaves.priority_combos) == slaves_before
    assert slaves.card_combo.currentText() == "斗鱼"


def test_单账号时退化不崩(tmp_config_dir):
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n')

    widget, host = _make_dialog()
    try:
        assert len(widget.cards) == 1
        assert len(widget.cards[0].priority_combos) == 4
        assert widget.values() == {
            "master": {
                "card": "太鼓",
                "priority": ["六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼"],
            }
        }
    finally:
        _drop(widget, host)


def test_配置损坏时弹窗仍能打开(tmp_config_dir):
    """打开时读取失败只降级为默认值，不抛异常"""
    _write_setting("结界养成: [这不是: 合法\n  - yaml")

    widget, host = _make_dialog()
    try:
        values = widget.values()
        assert len(values) == 2
        assert values["master"]["card"] == "太鼓"
    finally:
        _drop(widget, host)


# ------------------------------------------------------------ 取值与落盘


def test_values结构与读写层一致(dialog):
    values = dialog.values()

    assert set(values) == {"master", "slaves"}
    assert values["master"] == {
        "card": "太鼓",
        "priority": ["六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼"],
    }


def test_validate成功时写盘(dialog):
    dialog.cards[0].card_combo.setCurrentText("斗鱼")
    dialog.cards[0].priority_combos[0].setCurrentText("五星斗鱼")

    assert dialog.validate() is True

    import paths

    with open(paths.SETTING, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert "优先结界卡: \"斗鱼\"" in text
    assert "寄养优先级: [五星斗鱼" in text


def test_保存后其它段不变(dialog):
    import paths
    import ruamel.yaml

    with open(paths.SETTING, "r", encoding="utf-8") as handle:
        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        before = yaml.load(handle)

    dialog.cards[1].card_combo.setCurrentText("太鼓")
    assert dialog.validate() is True

    with open(paths.SETTING, "r", encoding="utf-8") as handle:
        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        after = yaml.load(handle)

    assert dict(after["启动项"]) == dict(before["启动项"])
    assert dict(after["寮三十"]) == dict(before["寮三十"])
    assert after["结界养成"]["slaves"]["优先结界卡"] == "太鼓"


def test_validate失败时返回False(dialog, monkeypatch):
    """写盘失败不能让弹窗关闭，否则用户以为保存成功了"""
    from ui import jiejie_settings

    monkeypatch.setattr(jiejie_settings, "save_jiejie_settings", lambda *a, **k: False)
    monkeypatch.setattr("ui.jiejie_dialog.QMessageBox.warning", lambda *a, **k: None)

    assert dialog.validate() is False


def test_保存提示由弹窗自己给出():
    """主窗口不再写死寮三十文案，改从弹窗类取"""
    from ui.jiejie_dialog import JiejieSettingsDialog

    assert "结界养成" in JiejieSettingsDialog.SAVED_MESSAGE
    assert "寮三十" not in JiejieSettingsDialog.SAVED_MESSAGE


def test_每个已登记弹窗都有自己的保存提示():
    """漏写 SAVED_MESSAGE 会静默退化成通用文案（寮三十那次就漏了）"""
    from ui.window import CONFIG_DIALOGS

    for key, dialog_class in CONFIG_DIALOGS.items():
        message = getattr(dialog_class, "SAVED_MESSAGE", None)
        assert message, f"{key} 的弹窗没有 SAVED_MESSAGE"
        # 不能串台：别的任务的提示里不该出现本任务的专有词
        for other_key, other_class in CONFIG_DIALOGS.items():
            if other_key == key:
                continue
            other_word = getattr(other_class, "SAVED_MESSAGE", "").split("设置")[0]
            assert other_word not in message, f"{key} 的提示串到了 {other_key}"


def test_寮三十的保存提示没被改坏():
    from ui.thirty_dialog import ThirtySettingsDialog

    assert "寮三十" in ThirtySettingsDialog.SAVED_MESSAGE
    assert "结界" not in ThirtySettingsDialog.SAVED_MESSAGE


# ------------------------------------------------------------ 齿轮登记


def test_齿轮已登记到弹窗表():
    from ui.jiejie_dialog import JiejieSettingsDialog
    from ui.window import CONFIG_DIALOGS

    assert CONFIG_DIALOGS.get("jiejieyangcheng") is JiejieSettingsDialog


def test_齿轮提示语按任务区分():
    """接入新任务后提示语不能再一律说成寮三十，也不能还写「暂未开放」"""
    from ui.widgets import CONFIG_READY_KEYS, config_tooltip

    assert "jiejieyangcheng" in CONFIG_READY_KEYS
    text = config_tooltip("jiejieyangcheng")
    assert "结界" in text
    assert "寮三十" not in text
    assert "暂未开放" not in text
    # 已有任务的话术不受影响
    assert config_tooltip("thirty") == "配置寮三十副本/次数与主副账号"
    assert "暂未开放" in config_tooltip("signin")


def test_提示语表覆盖全部就绪任务():
    from ui.widgets import CONFIG_READY_KEYS, CONFIG_TOOLTIPS

    assert set(CONFIG_TOOLTIPS) == set(CONFIG_READY_KEYS)
