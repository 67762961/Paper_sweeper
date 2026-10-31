# -*- coding: utf-8 -*-
"""「寮三十设置」弹窗：真实控件的布局、互斥与落盘（不真的点保存）。

守住四件事：

1. 横着铺：表头 7 列，副本/次数各 7 个下拉，选项只有代码支持的那几个；
2. 主副账号互斥：一方改选，另一方自动让开，且下拉里对方那一项灰掉；
3. ``values()`` 的下标与 `WEEK_LABELS` 一一对应，次数按整数返回；
4. ``validate()`` 成功时返回 True 并写盘，失败时返回 False（弹窗不关）。

用法与 ``test_after_run_dialog.py`` 一致：``MessageBoxBase`` 必须传非 None 的 parent。
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
"""


def _write_setting(text=SETTING):
    import paths

    os.makedirs(paths.CONFIG_DIR, exist_ok=True)
    with open(paths.SETTING, "w", encoding="utf-8") as handle:
        handle.write(text)


@pytest.fixture()
def dialog(tmp_config_dir):
    """真实构造的 ThirtySettingsDialog；工作目录已由夹具切到临时目录"""
    _write_setting()

    from ui.thirty_dialog import ThirtySettingsDialog

    host = QWidget()
    widget = ThirtySettingsDialog(host)
    yield widget
    widget.setParent(None)
    widget.deleteLater()
    host.setParent(None)
    host.deleteLater()
    _APP.processEvents()


# ------------------------------------------------------------ 布局


def test_副本与次数各七列(dialog):
    assert len(dialog.fuben_combos) == 7
    assert len(dialog.times_combos) == 7


def test_副本下拉只有四项(dialog):
    from ui.thirty_settings import FUBEN_OPTIONS

    texts = [dialog.fuben_combos[0].itemText(i) for i in range(dialog.fuben_combos[0].count())]
    assert texts == list(FUBEN_OPTIONS)


def test_次数下拉只有四档(dialog):
    from ui.thirty_settings import TIMES_OPTIONS

    texts = [dialog.times_combos[0].itemText(i) for i in range(dialog.times_combos[0].count())]
    assert texts == [str(value) for value in TIMES_OPTIONS]


def test_默认值与配置一致(dialog):
    values = dialog.values()

    assert values["primary"] == "master"
    assert values["secondary"] == "slaves"
    assert values["fuben"] == ["魂虚", "魂虚", "魂虚", "魂虚", "魂虚", "魂海", "日蚀"]
    assert values["times"] == [30] * 7


# ------------------------------------------------------------ 主副账号互斥


def test_账号下拉来自启动项(dialog):
    texts = [dialog.primary_combo.itemText(i) for i in range(dialog.primary_combo.count())]
    assert texts == ["master", "slaves"]


def test_主账号改选后副账号自动让开(dialog):
    dialog.primary_combo.setCurrentText("slaves")

    assert dialog.primary_combo.currentText() == "slaves"
    assert dialog.secondary_combo.currentText() == "master"


def test_副账号改选后主账号自动让开(dialog):
    dialog.secondary_combo.setCurrentText("master")

    assert dialog.secondary_combo.currentText() == "master"
    assert dialog.primary_combo.currentText() == "slaves"


def test_交替切换不会撞车(dialog):
    """防递归的 _syncing 若写错，这里会死循环或两边变成同一个"""
    for _ in range(10):
        dialog.primary_combo.setCurrentText("slaves")
        dialog.secondary_combo.setCurrentText("slaves")
        assert dialog.primary_combo.currentText() != dialog.secondary_combo.currentText()


def test_只有一列账号时互斥退化(dialog):
    """启动项只有一个账号：两框都只有一项，允许相同，不崩"""
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n')

    from ui.thirty_dialog import ThirtySettingsDialog

    host = QWidget()
    single = ThirtySettingsDialog(host)
    try:
        assert single.primary_combo.count() == 1
        assert single.primary_combo.currentText() == single.secondary_combo.currentText() == "master"
    finally:
        single.setParent(None)
        single.deleteLater()
        host.setParent(None)
        host.deleteLater()
        _APP.processEvents()


# ------------------------------------------------------------ 取值与落盘


def test_values次数是整数(dialog):
    dialog.times_combos[0].setCurrentText("50")

    values = dialog.values()
    assert values["times"][0] == 50
    assert all(isinstance(value, int) for value in values["times"])


def test_validate成功时写盘(dialog):
    dialog.fuben_combos[1].setCurrentText("魂王")
    dialog.times_combos[2].setCurrentText("0")

    assert dialog.validate() is True

    import paths

    with open(paths.SETTING, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert "副本: [魂虚, 魂王, 魂虚, 魂虚, 魂虚, 魂海, 日蚀]" in text
    assert "次数: [30, 30, 0, 30, 30, 30, 30]" in text


def test_validate失败时返回False(dialog, monkeypatch):
    """写盘失败不能让弹窗关闭，否则用户以为保存成功了"""
    from ui import thirty_settings

    monkeypatch.setattr(thirty_settings, "save_thirty_settings", lambda *a, **k: False)
    monkeypatch.setattr(
        "ui.thirty_dialog.QMessageBox.warning", lambda *a, **k: None
    )

    assert dialog.validate() is False


def test_配置损坏时弹窗仍能打开(tmp_config_dir):
    """打开时读取失败只降级为默认值，不抛异常"""
    _write_setting("寮三十: [这不是: 合法\n  - yaml")

    from ui.thirty_dialog import ThirtySettingsDialog

    host = QWidget()
    widget = ThirtySettingsDialog(host)
    try:
        values = widget.values()
        assert len(values["fuben"]) == 7
        assert len(values["times"]) == 7
    finally:
        widget.setParent(None)
        widget.deleteLater()
        host.setParent(None)
        host.deleteLater()
        _APP.processEvents()
