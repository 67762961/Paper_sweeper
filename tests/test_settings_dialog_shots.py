# -*- coding: utf-8 -*-
"""设置弹窗里的「调试截图」下拉框：真实控件、真实落盘（不真的点保存按钮）。

守住四件事：

1. 下拉框的三项与 `prefs.VALID_SHOT_MODES` 一一对应，顺序不能错位
   ——`values()` 是按索引取值的，顺序一错就会把「全部保存」存成「只存未命中」；
2. 打开弹窗时回显当前档位，而不是永远显示第一项；
3. `values()` 返回的档位能真的写进 `state/gui.json`，且不冲掉别的键；
4. 默认档位是 `off`，老用户打开弹窗看到的必须是「关闭」。

用法与 `test_thirty_dialog.py` 一致：`MessageBoxBase` 必须传非 None 的 parent。
"""

import json
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")
pytest.importorskip("qfluentwidgets")

from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

from ui import prefs  # noqa: E402

_APP = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def dialog(tmp_config_dir):
    """真实构造的 SettingsDialog；工作目录已由夹具切到临时目录"""
    from ui.settings_dialog import SettingsDialog

    host = QWidget()
    widget = SettingsDialog(host)
    yield widget
    widget.setParent(None)
    widget.deleteLater()
    host.setParent(None)
    host.deleteLater()
    _APP.processEvents()


def _settings_dialog():
    from ui.settings_dialog import SettingsDialog

    return SettingsDialog


# ------------------------------------------------------------ 下拉框内容


def test_下拉框有三项(dialog):
    assert dialog.shot_combo.count() == 3


def test_下拉框顺序与合法档位一致(dialog):
    """values() 按下标取 VALID_SHOT_MODES，顺序必须完全一致"""
    labels = [dialog.shot_combo.itemText(i) for i in range(dialog.shot_combo.count())]
    expected = [prefs.SHOT_MODE_LABELS[mode] for mode in prefs.VALID_SHOT_MODES]

    assert labels == expected


def test_下拉框文案是中文且不含英文档位名(dialog):
    """给普通用户看的，不该出现 off/miss/all"""
    labels = [dialog.shot_combo.itemText(i) for i in range(dialog.shot_combo.count())]

    for mode in prefs.VALID_SHOT_MODES:
        assert mode not in labels


# ------------------------------------------------------------ 回显与取值


def test_默认回显关闭(dialog):
    """老配置里没有 debug_shots，打开弹窗必须显示「关闭」"""
    assert prefs.VALID_SHOT_MODES[dialog.shot_combo.currentIndex()] == "off"


@pytest.mark.parametrize("mode", ["off", "miss", "all"])
def test_打开时回显已保存的档位(tmp_config_dir, mode):
    """先写盘再构造弹窗，验证不是永远回显第一项"""
    os.makedirs("state", exist_ok=True)
    with open(prefs.PREFS_PATH, "w", encoding="utf-8") as handle:
        json.dump({"debug_shots": mode}, handle)

    from ui.settings_dialog import SettingsDialog

    host = QWidget()
    widget = SettingsDialog(host)
    try:
        assert widget.values()["debug_shots"] == mode
    finally:
        widget.setParent(None)
        widget.deleteLater()
        host.setParent(None)
        host.deleteLater()
        _APP.processEvents()


@pytest.mark.parametrize("index,expected", [(0, "off"), (1, "miss"), (2, "all")])
def test_选中第几项就返回第几个档位(dialog, index, expected):
    dialog.shot_combo.setCurrentIndex(index)

    assert dialog.values()["debug_shots"] == expected


def test_values仍返回主题与日志三项(dialog):
    """加了下拉框不能把原来那三项弄丢"""
    values = dialog.values()

    assert set(values) == {"theme", "log_auto_scroll", "log_font_size", "debug_shots"}


# ------------------------------------------------------------ 落盘


def test_选中全部保存后能写进gui_json(dialog):
    dialog.shot_combo.setCurrentIndex(2)
    values = dialog.values()

    merged = prefs.load_prefs()
    merged.update(values)
    assert prefs.save_prefs(merged) is True

    with open(prefs.PREFS_PATH, "r", encoding="utf-8") as handle:
        on_disk = json.load(handle)
    assert on_disk["debug_shots"] == "all"


def test_保存档位不冲掉完成动作(dialog):
    """设置弹窗只提交自己那几项，合并时不能把 after_run_* 抹掉"""
    os.makedirs("state", exist_ok=True)
    with open(prefs.PREFS_PATH, "w", encoding="utf-8") as handle:
        json.dump({"after_run_sleep": True, "after_run_power": "logoff"}, handle)

    dialog.shot_combo.setCurrentIndex(1)
    merged = prefs.load_prefs()
    merged.update(dialog.values())
    assert prefs.save_prefs(merged) is True

    loaded = prefs.load_prefs()
    assert loaded["debug_shots"] == "miss"
    assert loaded["after_run_sleep"] is True
    assert loaded["after_run_power"] == "logoff"


# ------------------------------------------------------------ 界面提示


def test_三个档位各有一句说明(dialog):
    """只存未命中的坑必须在界面上说清楚，三个档位各说一句「会怎么样」"""
    text = dialog.shot_hint.text()

    assert "关闭" in text
    assert "只存未命中" in text
    assert "全部保存" in text
    assert "未命中" in text
