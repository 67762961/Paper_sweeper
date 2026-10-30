# -*- coding: utf-8 -*-
"""右侧按钮区的组装顺序与两个齿轮的分工（不碰真实窗口）。

守住三件事：
1. 按钮区从左到右是「关闭模拟器 / 中断运行 / 完整运行 / 设置齿轮」；
2. 两个齿轮走不同信号，各进各的弹窗——日志齿轮是 settings_clicked，
   按钮区齿轮是 after_run_settings_clicked；
3. 齿轮与日志区顶部那个是同款控件、同尺寸（不放大）。
"""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")
pytest.importorskip("qfluentwidgets")

from PyQt6.QtWidgets import QApplication  # noqa: E402

# 用例间共享一个 QApplication，重复创建会崩
_APP = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def panel(tmp_config_dir):
    """每个用例一个干净的 RightPanel（tmp_config_dir 已切好工作目录）"""
    from ui.panels import RightPanel

    widget = RightPanel()
    yield widget
    widget.deleteLater()


def _button_layout(panel):
    """取出按钮区那个 QHBoxLayout"""
    return panel.close_emulator_button.parentWidget().layout()


def _widget_texts(layout):
    """按顺序列出布局里每个控件的文字；stretch / spacing 记为占位符"""
    texts = []
    for index in range(layout.count()):
        item = layout.itemAt(index)
        widget = item.widget()
        if widget is None:
            # spacerItem：addStretch / addSpacing 都是 None 的 widget
            texts.append("<spacer>")
        else:
            texts.append(widget.text())
    return texts


# ------------------------------------------------------------ 顺序


def test_按钮区顺序(panel):
    texts = _widget_texts(_button_layout(panel))

    assert texts == ["<spacer>", "关闭模拟器", "中断运行", "完整运行", "<spacer>", ""]


def test_齿轮在最右边(panel):
    layout = _button_layout(panel)

    last_widget = layout.itemAt(layout.count() - 1).widget()
    assert last_widget is panel.button_settings_button


def test_三个文字按钮都在齿轮左边(panel):
    layout = _button_layout(panel)
    order = [
        layout.itemAt(index).widget()
        for index in range(layout.count())
        if layout.itemAt(index).widget() is not None
    ]

    assert order.index(panel.close_emulator_button) < order.index(panel.interrupt_button)
    assert order.index(panel.interrupt_button) < order.index(panel.run_button)
    assert order.index(panel.run_button) < order.index(panel.button_settings_button)


# ------------------------------------------------------------ 两个齿轮的分工


def test_按钮区齿轮走独立信号(panel):
    """两个齿轮不能共用同一个信号，否则以后想分开就改不动了"""
    fired = []
    panel.after_run_settings_clicked.connect(lambda: fired.append("after_run"))
    panel.settings_clicked.connect(lambda: fired.append("settings"))

    panel.button_settings_button.click()

    assert fired == ["after_run"]


def test_日志齿轮仍走原有信号(panel):
    fired = []
    panel.after_run_settings_clicked.connect(lambda: fired.append("after_run"))
    panel.settings_clicked.connect(lambda: fired.append("settings"))

    panel.settings_button.click()

    assert fired == ["settings"]


def test_两个齿轮不是同一个控件(panel):
    assert panel.settings_button is not panel.button_settings_button


# ------------------------------------------------------------ 齿轮外观


def test_齿轮与日志齿轮同尺寸(panel):
    """不放大：默认尺寸放进 40px 高的按钮行里由布局垂直居中"""
    assert panel.button_settings_button.size() == panel.settings_button.size()


def test_齿轮未设置固定尺寸(panel):
    """确认没有调过 setFixedSize（放大就与日志齿轮不一致了）"""
    assert not panel.button_settings_button.minimumSize() == panel.button_settings_button.maximumSize()


def test_齿轮提示文案区分于日志齿轮(panel):
    assert panel.button_settings_button.toolTip() != panel.settings_button.toolTip()
    assert "完整运行" in panel.button_settings_button.toolTip()


# ------------------------------------------------------------ 禁用逻辑


def test_空闲时只有关闭模拟器与完整运行可点(panel):
    assert panel.close_emulator_button.isEnabled() is True
    assert panel.run_button.isEnabled() is True
    assert panel.interrupt_button.isEnabled() is False


def test_运行中只有中断可点(panel):
    panel.set_running(True)

    assert panel.close_emulator_button.isEnabled() is False
    assert panel.run_button.isEnabled() is False
    assert panel.interrupt_button.isEnabled() is True


def test_齿轮在运行中仍可点(panel):
    """设置弹窗任何时候都能打开，改完对本次收尾立即生效"""
    panel.set_running(True)

    assert panel.button_settings_button.isEnabled() is True


def test_结束后复位(panel):
    panel.set_running(True)
    panel.set_running(False)

    assert panel.close_emulator_button.isEnabled() is True
    assert panel.run_button.isEnabled() is True
    assert panel.interrupt_button.isEnabled() is False
