# -*- coding: utf-8 -*-
"""日志区齿轮的保存路径：写盘失败必须让用户看见（不碰真实弹窗、不真的写盘）。

守住四件事：

1. 保存成功：偏好落盘、主题生效、界面同步（三件事都真的发生）；
2. 保存失败：弹「保存失败」提示，**并且不再假装成功**——不切主题、不同步界面，
   否则用户会以为设置已生效（尤其把「调试截图」改成全部保存时，代价是几百 MB）；
3. 点「取消」：一次都不写盘，也不碰界面；
4. 弹窗返回值里的键原样合并进 gui.json，不冲掉完成动作那几项。

做法：把 `SettingsDialog` 换成一个返回固定 values 的假弹窗，
把 `InfoBar` / `apply_theme` / `apply_prefs` 换成记录器，逐条断言调用与顺序。
"""

import json
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")
pytest.importorskip("qfluentwidgets")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui import prefs as ui_prefs  # noqa: E402

_APP = QApplication.instance() or QApplication(sys.argv)

FAKE_VALUES = {
    "theme": "dark",
    "log_auto_scroll": False,
    "log_font_size": 14,
    "debug_shots": "all",
}


class _FakeDialog:
    """冒充 SettingsDialog：exec() 返回给定结果，values() 返回固定值"""

    accept = True

    def __init__(self, parent=None):
        self.parent = parent

    def exec(self):
        return _FakeDialog.accept

    def values(self):
        return dict(FAKE_VALUES)


class _Recorder:
    """记录 InfoBar.success / InfoBar.error 的调用"""

    def __init__(self):
        self.calls = []

    def success(self, title, content, **kwargs):
        self.calls.append(("success", title, content))

    def error(self, title, content, **kwargs):
        self.calls.append(("error", title, content))

    def titles(self, kind=None):
        return [call[1] for call in self.calls if kind is None or call[0] == kind]


@pytest.fixture()
def window(tmp_config_dir):
    """真实构造的 MainWindow（不显示）；工作目录已由夹具切到临时目录"""
    _FakeDialog.accept = True

    from ui.window import MainWindow

    widget = MainWindow()
    yield widget
    widget.setParent(None)
    widget.deleteLater()
    _APP.processEvents()


@pytest.fixture()
def spy(window, monkeypatch):
    """把弹窗、InfoBar、主题与界面同步都换成记录器"""
    recorder = _Recorder()
    events = {"apply_theme": [], "apply_prefs": []}

    monkeypatch.setattr("ui.window.SettingsDialog", _FakeDialog)
    monkeypatch.setattr("ui.window.InfoBar", recorder)
    monkeypatch.setattr(
        "ui.window.theme_manager.apply_theme",
        lambda mode: events["apply_theme"].append(mode),
    )
    monkeypatch.setattr(
        window.right_panel,
        "apply_prefs",
        lambda values: events["apply_prefs"].append(dict(values)),
    )
    return recorder, events


def _read_disk():
    with open(ui_prefs.PREFS_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


# ------------------------------------------------------------ 保存成功


def test_保存成功时落盘并应用(window, spy):
    recorder, events = spy

    window.open_settings()

    assert _read_disk()["debug_shots"] == "all"
    assert _read_disk()["theme"] == "dark"
    assert events["apply_theme"] == ["dark"]
    assert events["apply_prefs"] == [FAKE_VALUES]
    assert recorder.titles("error") == []


def test_保存成功不弹保存失败(window, spy):
    recorder, _events = spy

    window.open_settings()

    assert recorder.titles("error") == []


# ------------------------------------------------------------ 保存失败


def test_保存失败弹错误提示(window, spy, monkeypatch):
    recorder, _events = spy
    monkeypatch.setattr("ui.window.ui_prefs.save_prefs", lambda merged: False)

    window.open_settings()

    assert recorder.titles("error") == ["保存失败"]


def test_保存失败不再切主题(window, spy, monkeypatch):
    """写盘没成功就不能让界面看起来变了，否则用户以为已经生效"""
    _recorder, events = spy
    monkeypatch.setattr("ui.window.ui_prefs.save_prefs", lambda merged: False)

    window.open_settings()

    assert events["apply_theme"] == []
    assert events["apply_prefs"] == []


def test_保存失败不会留下半截文件(window, spy, monkeypatch):
    recorder, _events = spy
    monkeypatch.setattr("ui.window.ui_prefs.save_prefs", lambda merged: False)

    window.open_settings()

    assert not os.path.exists(ui_prefs.PREFS_PATH)
    assert recorder.titles("error") == ["保存失败"]


# ------------------------------------------------------------ 取消


def test_点取消时一次都不写盘(window, spy):
    _recorder, events = spy
    _FakeDialog.accept = False

    window.open_settings()

    assert events["apply_theme"] == []
    assert events["apply_prefs"] == []
    assert not os.path.exists(ui_prefs.PREFS_PATH)


def test_点取消时不弹任何提示(window, spy):
    recorder, _events = spy
    _FakeDialog.accept = False

    window.open_settings()

    assert recorder.calls == []


# ------------------------------------------------------------ 合并语义


def test_保存时合并而不是覆盖(window, spy):
    """弹窗只管主题/日志/截图，完成动作那两项必须原样留着"""
    os.makedirs("state", exist_ok=True)
    with open(ui_prefs.PREFS_PATH, "w", encoding="utf-8") as handle:
        json.dump({"after_run_sleep": True, "after_run_power": "logoff"}, handle)

    window.open_settings()

    on_disk = _read_disk()
    assert on_disk["after_run_sleep"] is True
    assert on_disk["after_run_power"] == "logoff"
    assert on_disk["debug_shots"] == "all"
