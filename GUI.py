# -*- coding: utf-8 -*-
"""Paper Sweeper 图形界面入口。

界面实现位于 ``ui/`` 包，本文件只负责：

1. Windows 高 DPI 环境变量；
2. 日志与未捕获异常钩子；
3. 创建 QApplication、应用主题并显示主窗口；
4. 为兼容旧脚本/测试而转出主要界面类。
"""

import os
import sys

if sys.platform == "win32":
    os.environ["QT_QPA_PLATFORM"] = "windows:dpiawareness=1"

import logging

from PyQt6.QtWidgets import QApplication, QMessageBox
from qt_material import apply_stylesheet

from ui.icons import IconButton, StatusIcon
from ui.panels import LeftPanel, RightPanel
from ui.widgets import TaskRow, ToggleSwitch
from ui.window import MainWindow, WorkerThread

logging.basicConfig(
    filename="app_crash.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)


def handle_exception(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))
    # 打包版（console=False）或 pythonw 下 sys.stdout 可能为 None，打印需兜底
    try:
        print("发生致命错误，详情请查看日志文件: app_crash.log")
    except Exception:
        pass


sys.excepthook = handle_exception


if __name__ == "__main__":
    app = QApplication([])
    apply_stylesheet(app, theme="light_blue.xml")
    window = MainWindow()
    window.resize(800, 500)
    window.show()
    app.exec()
