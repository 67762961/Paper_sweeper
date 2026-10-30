# -*- coding: utf-8 -*-
"""CountdownDialog 的倒计时行为（用真实 QTimer，不用替身）。

这个文件的存在理由：`tests/test_after_run_actions.py` 用 FakeDialog 替身
验证「窗口侧的分支逻辑」，但替身把对话框自己的倒计时整个跳过了。
结果就是 start() 从未被调用、倒计时根本不会走这个 bug 溜进了 PR。

教训：**替身能验证调用方，验证不了被替身的东西本身。**
这里用真的 CountdownDialog + 真的 QTimer，跑一小段事件循环，
断言倒计时会递减、归零会自己关闭。
"""

import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")
pytest.importorskip("qfluentwidgets")

from PyQt6.QtCore import QEventLoop, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

_APP = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def host():
    """MessageBoxBase 需要一个父窗口才能算尺寸"""
    widget = QWidget()
    widget.resize(900, 600)
    yield widget
    widget.setParent(None)
    widget.deleteLater()
    _APP.processEvents()


def _pump(ms):
    """用 QEventLoop + 单次定时器推进 ms 毫秒

    不用 processEvents() 空转：offscreen 平台下裸 processEvents 遇到
    其它测试残留的控件容易触发 Qt 访问违例；QEventLoop 的退出条件明确，
    跑完就返回，不会把无关事件卷进来。
    """
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


@pytest.fixture()
def dialog(host):
    from ui.widgets import CountdownDialog

    widget = CountdownDialog(host, seconds=3, action_text="测试动作")
    yield widget
    widget.stop()
    widget.setParent(None)
    widget.deleteLater()
    _APP.processEvents()


# ------------------------------------------------------------ 构造状态


def test_构造后定时器未启动(dialog):
    """还没 exec()，倒计时不该开始跑"""
    assert dialog._timer.isActive() is False


def test_构造后显示初始秒数(dialog):
    assert dialog.remaining == 3
    assert "3 秒后将测试动作" in dialog.countdown_label.text()


def test_按钮文案(dialog):
    assert dialog.yesButton.text() == "立即执行"
    assert dialog.cancelButton.text() == "取消"


# ------------------------------------------------------------ 倒计时真的会走


def test_exec_会启动定时器(dialog):
    """核心回归：exec() 必须自己启动倒计时，不能依赖一个没人调用的 start()

    这里不调 exec()（在 offscreen 平台下，前面若有其它控件存活，
    嵌套事件循环会触发 Qt 访问违例），而是直接验证 exec() 里的关键动作：
    定时器被启动、退出时被停止。
    """
    # 未调用前：静止
    assert dialog._timer.isActive() is False

    # 模拟 exec() 的入口/出口行为（与 exec() 内部完全一致的顺序）
    dialog._timer.start()
    try:
        assert dialog._timer.isActive() is True
        _pump(1200)
        # 定时器真的在跑：3 秒起步，1.2 秒后应该递减到 2
        assert dialog.remaining < 3, "倒计时没有递减，定时器可能没启动"
    finally:
        dialog._timer.stop()

    assert dialog._timer.isActive() is False


def test_归零自动关闭(host):
    """1 秒倒计时：跑完事件循环后对话框应该自己接受，不需要人点"""
    from ui.widgets import CountdownDialog

    widget = CountdownDialog(host, seconds=1, action_text="测试")
    accepted = []
    widget.accepted.connect(lambda: accepted.append(True))

    widget._timer.start()
    try:
        _pump(1500)
    finally:
        widget.stop()
        widget.deleteLater()

    assert accepted, "倒计时归零后没有自动 accept"


def test_归零后定时器停止(dialog):
    dialog._timer.start()
    _pump(200)
    dialog.remaining = 1
    dialog._tick()

    assert dialog._timer.isActive() is False


def test_每秒递减一次(dialog):
    dialog._timer.start()
    try:
        _pump(2100)
    finally:
        dialog.stop()

    # 2 秒应该走掉 2 格（允许 1 格误差，避免 CI 上定时器抖动导致偶发失败）
    assert 0 <= dialog.remaining <= 1, f"递减不符合预期: {dialog.remaining}"


def test_归零时调用accept(dialog, monkeypatch):
    """核心：倒计时归零必须调 accept()，否则弹窗永远关不掉

    MaskDialogBase 重写了 accept()，信号/result 的行为与原生 QDialog 不同，
    所以直接监听「有没有被调用」，这是这里唯一要守住的契约。
    """
    called = []
    monkeypatch.setattr(dialog, "accept", lambda: called.append(True))

    dialog.remaining = 1
    dialog._tick()

    assert called == [True]


def test_未归零时不调用accept(dialog, monkeypatch):
    called = []
    monkeypatch.setattr(dialog, "accept", lambda: called.append(True))

    dialog._tick()   # 3 -> 2

    assert called == []
    assert dialog.remaining == 2


def test_exec_的finally会停表():
    """exec() 用 try/finally 包住定时器，无论怎么退出都不会留下在跑的定时器

    这里只做源码级断言：真正调 exec() 在 offscreen 下会触发 Qt 访问违例。
    """
    import inspect

    from ui.widgets import CountdownDialog

    source = inspect.getsource(CountdownDialog.exec)

    assert "self._timer.start()" in source
    assert "finally" in source
    assert "self._timer.stop()" in source


# ------------------------------------------------------------ 倒计时文案


def test_文案随剩余秒数变化(dialog):
    dialog.remaining = 7
    dialog._refresh_text()

    assert "7 秒后将测试动作" in dialog.countdown_label.text()


def test_未传动作文案时有兜底(dialog, host):
    from ui.widgets import CountdownDialog

    widget = CountdownDialog(host, seconds=5)

    assert "执行后续动作" in widget.countdown_label.text()
    widget.deleteLater()


# ------------------------------------------------------------ 调用方


def test_window_用的是exec而不是已删除的start():
    """回归保护：window.py 必须调 dialog.exec()

    之前 window.py 调 exec()、而倒计时写在 start() 里，start() 从没被调用，
    弹窗就永远停在 10 秒。这条断言防止有人把调用改回一个不存在的入口。
    """
    source = open("ui/window.py", "r", encoding="utf-8").read()

    assert "dialog.exec()" in source
    assert "dialog.start()" not in source


def test_CountdownDialog_不再暴露start方法():
    """start() 已合并进 exec()，不该再有这个容易漏调的入口"""
    from ui.widgets import CountdownDialog

    assert not hasattr(CountdownDialog, "start")
