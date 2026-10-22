# -*- coding: utf-8 -*-
"""Paper Sweeper 图形界面入口。

界面实现位于 ``ui/`` 包，本文件只负责：

1. 日志与未捕获异常钩子；
2. 创建 QApplication、初始化 Fluent 主题并显示主窗口；
3. 为兼容旧脚本/测试而转出主要界面类。
"""

import logging
import os
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from ui.icons import IconButton, StatusIcon
from ui.panels import LeftPanel, RightPanel
from ui.theme_manager import apply_theme, init_theme, toggle_theme
from ui.widgets import TaskRow, ToggleSwitch
from ui.window import MainWindow, WorkerThread

# 崩溃日志统一放 logs/（与运行日志同处），不再散落在项目根目录。
# 注意取基目录的方式：
# - 源码运行时用 __file__ 所在目录（项目根）；
# - PyInstaller 打包后 __file__ 指向临时解压目录（_MEIPASS），会被清理，
#   必须改用 sys.executable 所在目录（即 GUI.exe 旁边）。
def _base_dir():
    """返回"程序所在目录"：源码运行时是项目根，打包后是 exe 所在目录"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


LOG_DIR = os.path.join(_base_dir(), "logs")
CRASH_LOG_PATH = os.path.join(LOG_DIR, "app_crash.log")

try:
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=CRASH_LOG_PATH,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
    )
except OSError:
    # 目录不可写时退回不写文件，至少别让界面起不来
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


def handle_exception(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))
    # 打包版（console=False）或 pythonw 下 sys.stdout 可能为 None，打印需兜底
    try:
        print(f"发生致命错误，详情请查看日志文件: {CRASH_LOG_PATH}")
    except Exception:
        pass


def main():
    """创建应用、初始化主题并显示主窗口"""
    sys.excepthook = handle_exception

    app = QApplication(sys.argv)
    init_theme()

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
