# -*- coding: utf-8 -*-
"""完整运行完成动作的触发条件（不真的关模拟器、不真的睡眠）。

这是整个 PR 最需要守住的地方：一次误触发就会把电脑睡过去，
所以条件必须严格是「完整运行 + 成功 + 未中断」，且必须在
线程真正退出（日志文件已关）之后才执行。

不构造 MainWindow（那会拉起整个 Fluent 外壳），而是用桩对象
直接调 _run_after_actions / _do_after_actions 验证分支。
"""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")
pytest.importorskip("qfluentwidgets")

from PyQt6.QtWidgets import QApplication  # noqa: E402

_APP = QApplication.instance() or QApplication(sys.argv)


class FakePanel:
    """替身：记录日志行，不碰真实控件"""

    def __init__(self):
        self.lines = []

    def append_separator(self, text):
        self.lines.append(text)


class FakeWindow:
    """只保留完成动作需要的那部分 MainWindow 行为"""

    def __init__(self):
        self.right_panel = FakePanel()
        self._pending_after_run = False
        self.dialog_result = 1        # QDialog.exec()：1 = Accepted（确认），0 = Rejected（取消）
        self.dialog_calls = []
        self.close_calls = []         # 记录「启动了后台关闭」
        self.sleep_calls = []
        self.scheduled = []
        self._close_then_sleep = False
        self._close_silent = True

    # 从 MainWindow 借来的方法（逻辑原样，避免重复实现）
    _run_after_actions = None
    _do_after_actions = None
    _sleep_system = None


@pytest.fixture()
def window(monkeypatch, tmp_config_dir):
    """构造一个真实调用 MainWindow 完成动作逻辑的替身"""
    from ui import window as window_module

    fake = FakeWindow()

    class FakeDialog:
        def __init__(self, parent, seconds, action_text):
            fake.dialog_calls.append((seconds, action_text))

        def exec(self):
            # 与 QDialog.exec 一致：1 = Accepted，0 = Rejected
            return fake.dialog_result

    monkeypatch.setattr(window_module, "CountdownDialog", FakeDialog)

    # 关模拟器现在是异步的：替身只记录「有没有启动」，不真的开线程
    def fake_start_close(silent=True):
        fake.close_calls.append(silent)
        fake._close_silent = silent

    fake._start_close_emulators = fake_start_close
    fake._sleep_system = lambda: fake.sleep_calls.append(True)

    # 绑定真实的完成动作逻辑
    fake._run_after_actions = window_module.MainWindow._run_after_actions.__get__(fake)
    fake._do_after_actions = window_module.MainWindow._do_after_actions.__get__(fake)
    fake._on_close_emulators_finished = (
        window_module.MainWindow._on_close_emulators_finished.__get__(fake)
    )
    # 结果摘要用的是真实实现，但 InfoBar 在测试里没有父窗口，用记录代替
    fake._report_close_result = lambda result, silent=False: fake.right_panel.append_separator(
        "关闭模拟器：摘要"
    )

    # QTimer.singleShot 换成记录，避免用例里真的等 3 秒
    monkeypatch.setattr(
        window_module.QTimer, "singleShot", lambda ms, func: fake.scheduled.append((ms, func))
    )
    return fake


def _set_prefs(**values):
    from ui import prefs

    merged = prefs.load_prefs()
    merged.update(values)
    prefs.save_prefs(merged)


# ------------------------------------------------------------ 不触发的情况


def test_没有标记时什么都不做(window):
    window._pending_after_run = False

    window._run_after_actions()

    assert window.dialog_calls == []
    assert window.close_calls == []
    assert window.sleep_calls == []


def test_两个开关都关时不弹倒计时(window):
    _set_prefs(after_run_close_emulator=False, after_run_sleep=False)
    window._pending_after_run = True

    window._run_after_actions()

    assert window.dialog_calls == []
    assert window.close_calls == []
    assert window.sleep_calls == []


# ------------------------------------------------------------ 触发的情况


def test_只开关闭模拟器(window):
    _set_prefs(after_run_close_emulator=True, after_run_sleep=False)
    window._pending_after_run = True

    window._run_after_actions()

    assert len(window.dialog_calls) == 1
    assert window.close_calls == [True]   # silent=True：紧接着可能睡眠
    assert window.sleep_calls == []


def test_只开睡眠(window):
    _set_prefs(after_run_close_emulator=False, after_run_sleep=True)
    window._pending_after_run = True

    window._run_after_actions()

    assert window.close_calls == []
    assert window.sleep_calls == [True]


def test_两个都开时先关再睡(window):
    _set_prefs(after_run_close_emulator=True, after_run_sleep=True)
    window._pending_after_run = True

    window._run_after_actions()

    # 关模拟器现在是异步的：启动后台线程后立即返回，此时还没排睡眠
    assert window.close_calls == [True]
    assert window._close_then_sleep is True
    assert window.scheduled == []
    assert window.sleep_calls == []


def test_关闭完成后才排睡眠(window, monkeypatch):
    """关模拟器在后台线程跑完 → 回调里才排 3 秒后的睡眠"""
    from ui import window as window_module

    _set_prefs(after_run_close_emulator=True, after_run_sleep=True)
    window._pending_after_run = True
    window._run_after_actions()

    # 模拟后台线程回报结果
    report = window_module.MainWindow._on_close_emulators_finished.__get__(window)
    report({"result": {"closed": ["master"], "missing": [], "stuck": []}, "error": None})

    assert len(window.scheduled) == 1
    assert window.scheduled[0][0] == 3000
    assert window.sleep_calls == []

    window.scheduled[0][1]()
    assert window.sleep_calls == [True]


def test_只关不睡时关闭完成不排睡眠(window):
    from ui import window as window_module

    _set_prefs(after_run_close_emulator=True, after_run_sleep=False)
    window._pending_after_run = True
    window._run_after_actions()

    report = window_module.MainWindow._on_close_emulators_finished.__get__(window)
    report({"result": {"closed": ["master"], "missing": [], "stuck": []}, "error": None})

    assert window.scheduled == []
    assert window.sleep_calls == []


def test_关闭失败也照样接着睡眠(window):
    """关模拟器失败不该阻断睡眠：用户要的是「跑完就睡」"""
    from ui import window as window_module

    _set_prefs(after_run_close_emulator=True, after_run_sleep=True)
    window._pending_after_run = True
    window._run_after_actions()

    report = window_module.MainWindow._on_close_emulators_finished.__get__(window)
    report({"result": None, "error": "模拟器不肯关"})

    assert len(window.scheduled) == 1
    assert any("模拟器不肯关" in line for line in window.right_panel.lines)


def test_标记用过就清掉(window):
    """防止一次标记触发两次（比如用户连续两次完整运行）"""
    _set_prefs(after_run_close_emulator=True, after_run_sleep=False)
    window._pending_after_run = True

    window._run_after_actions()
    window._run_after_actions()

    assert len(window.close_calls) == 1


def test_取消后不执行任何动作(window):
    _set_prefs(after_run_close_emulator=True, after_run_sleep=True)
    window._pending_after_run = True
    window.dialog_result = 0   # 用户点「取消」→ Rejected

    window._run_after_actions()

    assert window.close_calls == []
    assert window.sleep_calls == []
    assert window.scheduled == []
    assert any("已取消" in line for line in window.right_panel.lines)


# ------------------------------------------------------------ 倒计时文案


def test_倒计时文案列出实际动作(window):
    _set_prefs(after_run_close_emulator=True, after_run_sleep=True)
    window._pending_after_run = True

    window._run_after_actions()

    seconds, action_text = window.dialog_calls[0]
    assert seconds == 10
    assert "关闭模拟器" in action_text
    assert "睡眠" in action_text


def test_只开睡眠时文案不含关闭模拟器(window):
    _set_prefs(after_run_close_emulator=False, after_run_sleep=True)
    window._pending_after_run = True

    window._run_after_actions()

    _, action_text = window.dialog_calls[0]
    assert "关闭模拟器" not in action_text
    assert "睡眠" in action_text


# ------------------------------------------------------------ 睡眠失败


def test_睡眠失败时给出明确提示(monkeypatch):
    """不能静默什么都不发生，否则用户以为程序卡住"""
    from ui import window as window_module

    bars = []
    monkeypatch.setattr(
        window_module.InfoBar,
        "error",
        lambda title, content, **kwargs: bars.append((title, content)),
    )
    monkeypatch.setattr(window_module.Lib, "sleep_system", lambda: False)

    fake = FakeWindow()
    fake._sleep_system = window_module.MainWindow._sleep_system.__get__(fake)

    fake._sleep_system()

    assert bars and bars[0][0] == "睡眠失败"
    assert any("失败" in line for line in fake.right_panel.lines)


def test_睡眠成功时不报错(monkeypatch):
    from ui import window as window_module

    bars = []
    monkeypatch.setattr(
        window_module.InfoBar,
        "error",
        lambda title, content, **kwargs: bars.append(title),
    )
    monkeypatch.setattr(window_module.Lib, "sleep_system", lambda: True)

    fake = FakeWindow()
    fake._sleep_system = window_module.MainWindow._sleep_system.__get__(fake)

    fake._sleep_system()

    assert bars == []
    assert any("正在请求系统睡眠" in line for line in fake.right_panel.lines)
