# -*- coding: utf-8 -*-
"""「完整运行设置」弹窗：电源动作下拉框与开关的联动（不真的动电脑）。

守住三件事：
1. 下拉框有「注销 / 睡眠 / 关机」三项，顺序固定；
2. 开关关闭时下拉框灰化（setEnabled(False)），开启时恢复可点；
3. values() 返回的两个键各管一件事：after_run_sleep 是是否启用，
   after_run_power 是用哪个。
"""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")
pytest.importorskip("qfluentwidgets")

from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

_APP = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def dialog(tmp_config_dir):
    """一个真实构造的 AfterRunDialog；MessageBoxBase 需要非 None 的父窗口"""
    from ui.after_run_dialog import AfterRunDialog

    host = QWidget()
    widget = AfterRunDialog(host)
    yield widget
    widget.setParent(None)
    widget.deleteLater()
    host.setParent(None)
    host.deleteLater()
    _APP.processEvents()


def _set_prefs(**values):
    from ui import prefs

    merged = prefs.load_prefs()
    merged.update(values)
    prefs.save_prefs(merged)


# ------------------------------------------------------------ 下拉框内容


def test_下拉框有三项且顺序固定(dialog):
    from ui.after_run_dialog import POWER_LABELS, POWER_ORDER

    assert POWER_ORDER == ("logoff", "sleep", "shutdown")
    assert dialog.power_combo.count() == 3
    assert [dialog.power_combo.itemText(i) for i in range(3)] == [
        POWER_LABELS[action] for action in POWER_ORDER
    ]


def test_下拉框文案是注销睡眠关机(dialog):
    assert dialog.power_combo.itemText(0) == "注销"
    assert dialog.power_combo.itemText(1) == "睡眠"
    assert dialog.power_combo.itemText(2) == "关机"


def test_默认选中睡眠(dialog):
    """老配置没有 after_run_power，默认落在睡眠，与升级前行为一致"""
    assert dialog.power_combo.currentIndex() == 1
    assert dialog.power_combo.currentText() == "睡眠"


@pytest.mark.parametrize(
    "action,index", [("logoff", 0), ("sleep", 1), ("shutdown", 2)]
)
def test_能读回已保存的选择(dialog, action, index):
    _set_prefs(after_run_power=action)

    from ui.after_run_dialog import AfterRunDialog

    host = QWidget()
    fresh = AfterRunDialog(host)
    try:
        assert fresh.power_combo.currentIndex() == index
    finally:
        fresh.setParent(None)
        fresh.deleteLater()
        host.setParent(None)
        host.deleteLater()
        _APP.processEvents()


# ------------------------------------------------------------ 灰化联动


def test_开关关闭时下拉框灰化(dialog):
    dialog.power_switch.setChecked(False)

    assert dialog.power_combo.isEnabled() is False


def test_开关开启时下拉框可点(dialog):
    dialog.power_switch.setChecked(False)
    dialog.power_switch.setChecked(True)

    assert dialog.power_combo.isEnabled() is True


def test_开关切换时灰化状态跟着变(dialog):
    """checkedChanged 信号连到 setEnabled，不是只在构造时判一次"""
    for checked in (True, False, True, False):
        dialog.power_switch.setChecked(checked)
        assert dialog.power_combo.isEnabled() is checked


def test_开关打开时下拉框才有意义(dialog):
    """灰化不该影响取值——关掉开关时仍能读到当前选中的动作"""
    dialog.power_switch.setChecked(False)
    dialog.power_combo.setCurrentIndex(2)

    assert dialog.values()["after_run_power"] == "shutdown"


# ------------------------------------------------------------ values()


def test_values返回两个键(dialog):
    values = dialog.values()

    assert set(values) == {"after_run_close_emulator", "after_run_sleep", "after_run_power"}
    assert isinstance(values["after_run_sleep"], bool)
    assert values["after_run_power"] in ("logoff", "sleep", "shutdown")


def test_values反映当前选中项(dialog):
    dialog.power_combo.setCurrentIndex(0)

    assert dialog.values()["after_run_power"] == "logoff"


def test_values反映开关状态(dialog):
    dialog.power_switch.setChecked(True)
    assert dialog.values()["after_run_sleep"] is True

    dialog.power_switch.setChecked(False)
    assert dialog.values()["after_run_sleep"] is False


def test_标签文案是电源动作(dialog):
    """原来叫「让电脑睡眠」，现在能选注销/关机，标签必须改"""
    from qfluentwidgets import BodyLabel

    texts = [child.text() for child in dialog.findChildren(BodyLabel)]
    assert "电源动作" in texts
    assert "让电脑睡眠" not in texts


def test_保存后重新打开保持选择(tmp_config_dir):
    """走一遍真实保存路径：values() → save_prefs → 重新构造"""
    from ui import prefs
    from ui.after_run_dialog import AfterRunDialog

    host = QWidget()
    first = AfterRunDialog(host)
    first.power_switch.setChecked(True)
    first.power_combo.setCurrentIndex(0)      # 注销
    merged = prefs.load_prefs()
    merged.update(first.values())
    prefs.save_prefs(merged)
    first.setParent(None)
    first.deleteLater()

    second = AfterRunDialog(host)
    try:
        assert second.power_switch.isChecked() is True
        assert second.power_combo.currentText() == "注销"
    finally:
        second.setParent(None)
        second.deleteLater()
        host.setParent(None)
        host.deleteLater()
        _APP.processEvents()
