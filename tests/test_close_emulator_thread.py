# -*- coding: utf-8 -*-
"""关闭模拟器必须跑在后台线程（用真实 QThread 验证）。

为什么单独一个文件：`MuMuManager control ... shutdown` 会同步阻塞到虚拟机真正
关机才返回（本机实测约 4 秒）。放在主线程里界面会完全冻住，连倒计时弹窗的
100ms 淡出动画都停在中间帧，表现为「半透明虚影 + 卡一下」。

这里的用例不碰真实模拟器：把 `Lib.close_emulators` 换成「故意睡一会儿」的假实现，
验证主线程在等待期间仍然能处理事件。
"""

import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")
pytest.importorskip("qfluentwidgets")

from PyQt6.QtCore import QEventLoop, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

_APP = QApplication.instance() or QApplication(sys.argv)


def _pump(ms):
    """用 QEventLoop 推进事件循环 ms 毫秒"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


@pytest.fixture()
def closer(monkeypatch):
    """一个只跑 run() 的 CloseEmulatorThread，Lib.close_emulators 换成假实现"""
    from ui import window as window_module

    def fake_close():
        time.sleep(0.4)          # 模拟 MuMuManager 的阻塞
        return {"closed": ["master"], "missing": [], "stuck": []}

    monkeypatch.setattr(window_module.Lib, "close_emulators", fake_close)
    return window_module.CloseEmulatorThread


# ------------------------------------------------------------ 线程本身


def test_关闭在后台线程跑完会发出结果(closer):
    received = []
    thread = closer()
    thread.close_finished.connect(received.append)

    thread.start()
    # 不能用 thread.wait()：它会阻塞调用线程的事件循环，
    # 跨线程排队的信号就永远送不到（槽在接收者所在线程执行）
    _pump(1500)
    thread.wait(3000)

    assert received, "后台线程没有发出结果"
    assert received[0]["error"] is None
    assert received[0]["result"]["closed"] == ["master"]


def test_线程异常不会静默退出(closer, monkeypatch):
    from ui import window as window_module

    def boom():
        raise OSError("MuMuManager 不见了")

    monkeypatch.setattr(window_module.Lib, "close_emulators", boom)
    received = []
    thread = closer()
    thread.close_finished.connect(received.append)

    thread.start()
    _pump(1500)
    thread.wait(3000)

    assert received[0]["error"] == "MuMuManager 不见了"
    assert received[0]["result"] is None


def test_信号名不与QThread自带finished冲突():
    """QThread 自己已有 finished 信号，重名会覆盖基类的线程结束通知"""
    from ui import window as window_module

    assert hasattr(window_module.CloseEmulatorThread, "close_finished")
    assert window_module.CloseEmulatorThread.close_finished is not getattr(
        window_module.QThread, "finished", None
    )


# ------------------------------------------------------------ 界面不被阻塞（核心）


def test_主线程在关闭期间仍能处理事件(closer):
    """核心回归：关闭模拟器时主线程不能被占死

    如果实现是同步的（直接调 Lib.close_emulators），这 0.4 秒里
    主线程什么都做不了，tick 计数会是 0。
    """
    thread = closer()
    ticks = []

    # 20ms 一次的心跳，跑在事件循环里
    heartbeat = QTimer()
    heartbeat.setInterval(20)
    heartbeat.timeout.connect(lambda: ticks.append(time.monotonic()))
    heartbeat.start()

    try:
        thread.start()
        _pump(300)          # 线程还在睡的那段时间里推进事件循环
        assert thread.isRunning() is True, "线程应该还在跑"
        mid_count = len(ticks)
    finally:
        heartbeat.stop()
        thread.wait(3000)

    # 0.3 秒 / 20ms ≈ 15 次，放宽到 5 次即可证明主线程没被冻住
    assert mid_count >= 5, f"主线程被阻塞了，300ms 内只跑了 {mid_count} 次心跳"


def test_同步实现会让心跳停摆(closer, monkeypatch):
    """反证：把同一个假实现同步跑一遍，心跳会明显变少

    这条用例保证上一条的断言不是「怎么都能过」——如果实现退化成同步的，
    心跳数会掉下来。
    """
    from ui import window as window_module

    ticks = []
    heartbeat = QTimer()
    heartbeat.setInterval(20)
    heartbeat.timeout.connect(lambda: ticks.append(time.monotonic()))
    heartbeat.start()

    try:
        window_module.Lib.close_emulators()   # 同步调用，阻塞 0.4 秒
        mid_count = len(ticks)
    finally:
        heartbeat.stop()

    # 同步阻塞期间 Qt 根本跑不了定时器
    assert mid_count == 0, f"同步调用期间居然跑了 {mid_count} 次心跳，用例前提不成立"
