# -*- coding: utf-8 -*-
"""主窗口与任务线程。"""

import logging

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QMessageBox, QWidget
from qfluentwidgets import (
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    MSFluentWindow,
    NavigationItemPosition,
    TransparentToolButton,
    qconfig,
)

import config
from main import (
    Full_operation,
    Single_operation,
    TASK_REGISTRY,
    completion_advanced,
    completion_snapshot,
    read_task_switches,
    set_task_switch,
)
from . import prefs as ui_prefs
from . import theme_manager
from . import theme
from .panels import LeftPanel, RightPanel
from .settings_dialog import SettingsDialog


class WorkerThread(QThread):
    """任务执行线程：task_key 为 None 时跑完整流程，否则只跑指定任务"""

    console_output = pyqtSignal(str)
    task_finished = pyqtSignal(object)

    def __init__(self, task_key=None, parent=None):
        super().__init__(parent)
        self.task_key = task_key

    def run(self):
        # 异常必须在线程内捕获，否则 Qt 线程静默退出且界面一直停留在运行中
        try:
            if self.task_key is None:
                Full_operation(self.console_output)
            else:
                Single_operation(self.task_key, self.console_output)
            self.task_finished.emit({"key": self.task_key, "ok": True, "error": None})
        except Exception as error:
            logging.critical("任务线程异常:", exc_info=True)
            try:
                print(f"TASK- ----- 任务执行出现未捕获异常: {error}")
            except Exception:
                pass
            self.task_finished.emit({"key": self.task_key, "ok": False, "error": str(error)})


class MainWindow(MSFluentWindow):
    """主窗口：Fluent 外壳 + 双栏内容（左侧任务列表 / 右侧日志控制台）"""

    def __init__(self):
        super().__init__()
        self.left_panel = None
        self.right_panel = None
        self.thread = None
        self.busy = False
        self.before_snapshot = {}
        self.init_ui()

    def init_ui(self):
        version = "1.3.0"
        self.setWindowTitle(f"Paper Sweeper - v{version}")
        self.resize(1240, 640)
        self.setMinimumSize(1100, 620)

        # 双栏内容作为唯一子界面加入 Fluent 外壳；当前版本不使用左侧导航
        page = QWidget()
        page.setObjectName("mainPage")

        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(theme.SPACE_XXL, theme.SPACE_LG, theme.SPACE_XXL, theme.SPACE_LG)
        main_layout.setSpacing(theme.SPACE_LG)

        self.left_panel = LeftPanel()
        main_layout.addWidget(self.left_panel)

        self.right_panel = RightPanel()
        main_layout.addWidget(self.right_panel, 1)

        self.addSubInterface(page, FluentIcon.HOME, "任务", NavigationItemPosition.TOP)
        self.navigationInterface.hide()

        # 顶栏快捷主题切换按钮
        self.theme_button = TransparentToolButton(FluentIcon.BRIGHTNESS, self)
        self.theme_button.setToolTip("切换深浅色主题")
        self.theme_button.clicked.connect(self.toggle_theme)
        if hasattr(self.titleBar, "hBoxLayout"):
            self.titleBar.hBoxLayout.insertWidget(4, self.theme_button)

        # 左侧行内交互：运行 / 配置（占位）/ 整跑开关
        self.left_panel.task_run_clicked.connect(self.on_task_run)
        self.left_panel.task_config_clicked.connect(self.on_task_config)
        self.left_panel.task_toggled.connect(self.on_task_toggled)
        self.right_panel.run_button_clicked.connect(self.run_button_clicked)
        self.right_panel.settings_clicked.connect(self.open_settings)

        # 主题切换后重新着色日志区已有文本；行内状态图标在 ui/icons.py 内自行重绘，
        # 文字类标签由 Fluent 自动切换浅色 / 深色两套取值
        qconfig.themeChangedFinished.connect(self.right_panel.apply_theme)

    # ---- 左侧行交互 ----

    def on_task_run(self, task_key):
        """点击行内运行图标：单独运行该任务"""
        self.start_job(task_key)

    def on_task_config(self, task_key):
        """点击行内齿轮：配置入口占位，暂不实现具体配置"""
        title = self._task_title(task_key)
        QMessageBox.information(
            self,
            "配置功能暂未开放",
            f"「{title}」的配置功能将在后续版本提供。\n\n当前可在 config/Setting.yml 中调整该任务的参数。",
        )

    def on_task_toggled(self, task_key, enabled):
        """拨动行内开关：写入 config/Gui_state.yml，决定是否参与完整运行"""
        title = self._task_title(task_key)
        if set_task_switch(task_key, enabled):
            state_text = "参与" if enabled else "不参与"
            self.right_panel.update_console(f"INFO- ----- 任务「{title}」已设置为{state_text}「完整运行」\n")
            return

        # 写盘失败：回滚界面并提示，避免界面与实际配置不一致
        self.left_panel.set_switch_state(task_key, not enabled)
        QMessageBox.warning(
            self,
            "保存失败",
            f"无法保存「{title}」的开关状态，请检查 config 目录是否可写。",
        )

    @staticmethod
    def _task_title(task_key):
        return next((task.title for task in TASK_REGISTRY if task.key == task_key), task_key)

    # ---- 主题与设置 ----

    def toggle_theme(self):
        """顶栏按钮：浅色 / 深色快速切换"""
        mode = theme_manager.toggle_theme()
        self._notify_theme(mode)

    def open_settings(self):
        """打开设置弹窗：主题、日志偏好与日志目录"""
        dialog = SettingsDialog(self)
        if not dialog.exec():
            return
        values = dialog.values()
        merged = ui_prefs.load_prefs()
        merged.update(values)
        ui_prefs.save_prefs(merged)
        theme_manager.apply_theme(values["theme"])
        self.right_panel.apply_prefs(values)
        self._notify_theme(values["theme"])

    def _notify_theme(self, mode):
        InfoBar.success("主题已切换", theme_manager.THEME_LABELS.get(mode, mode),
                        parent=self, duration=1500, position=InfoBarPosition.TOP_RIGHT)
    # ---- 任务调度 ----

    def run_button_clicked(self):
        """完整运行按钮点击：按注册表顺序依次执行已开启的任务"""
        self.start_job(None)

    def start_job(self, task_key):
        """启动一次任务；同一时间只允许一个任务线程运行"""
        if self.busy:
            return

        self.busy = True
        config.stop_thread = False

        # 运行前快照，结束后用它判断任务是否真正推进了完成时间
        self.before_snapshot = completion_snapshot()

        self.left_panel.refresh()
        if task_key is None:
            self.left_panel.clear_running()
        else:
            self.left_panel.set_running(task_key)
        self.left_panel.set_busy(True)
        self.right_panel.set_running(True)

        if task_key is None:
            try:
                switches = read_task_switches()
            except Exception:
                switches = {}
            disabled = [task.title for task in TASK_REGISTRY if not switches.get(task.key, True)]
            if disabled:
                self.right_panel.append_separator(
                    f"开始：完整运行（已关闭 {len(disabled)} 项将跳过：{'、'.join(disabled)}）"
                )
            else:
                self.right_panel.append_separator("开始：完整运行")
        else:
            self.right_panel.append_separator(f"开始：单独运行 - {self._task_title(task_key)}")

        self.thread = WorkerThread(task_key)
        self.thread.console_output.connect(self.right_panel.update_console)
        self.thread.task_finished.connect(self.on_job_finished)
        # 界面恢复在 task_finished，线程对象释放放在 QThread.finished 之后，
        # 避免在 run() 尚未返回时就把 QThread 置空回收
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()

    def on_thread_finished(self):
        """线程真正退出后再断开引用，防止 QThread 在使用中被回收"""
        thread = self.sender()
        if thread is self.thread:
            self.thread = None
        if thread is not None:
            thread.deleteLater()

    def on_job_finished(self, payload):
        """任务结束：恢复界面、刷新时间与今日状态、输出本次结果摘要"""
        self.busy = False

        try:
            after_snapshot = completion_snapshot()
            advanced = completion_advanced(self.before_snapshot, after_snapshot)
        except Exception as error:
            logging.warning("任务完成后刷新状态失败: %s", error)
            advanced = {}

        self.left_panel.clear_running()
        self.left_panel.refresh()
        self.left_panel.set_busy(False)
        self.right_panel.set_running(False)

        task_key = payload.get("key")

        if not payload.get("ok", True):
            error_text = str(payload.get("error"))
            self.right_panel.append_separator(f"结束：异常 - {error_text}")
            self.show_error_bar("任务执行异常", error_text)
            return

        try:
            switches = read_task_switches()
        except Exception:
            switches = {}
        enabled_keys = [task.key for task in TASK_REGISTRY if switches.get(task.key, True)]
        disabled_count = len(TASK_REGISTRY) - len(enabled_keys)

        if task_key is None:
            finished = sum(1 for key in enabled_keys if advanced.get(key))
            summary = f"结束：完成 {finished} 项 / 共 {len(enabled_keys)} 项"
            if disabled_count:
                summary += f"（另有 {disabled_count} 项已关闭跳过）"
        else:
            state_text = "完成" if advanced.get(task_key) else "未推进（详见控制台日志）"
            summary = f"结束：{self._task_title(task_key)} {state_text}"

        self.right_panel.append_separator(summary)

        # Fluent 结果提示：完整运行与单任务分别用不同文案
        content = summary.replace("结束：", "")
        if task_key is None:
            InfoBar.success("完整运行结束", content, parent=self, duration=4000,
                            position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.success("单任务结束", content, parent=self, duration=3000,
                            position=InfoBarPosition.TOP_RIGHT)

    def show_error_bar(self, title, content):
        """统一的错误提示（任务线程异常时使用）"""
        InfoBar.error(title, content, parent=self, duration=6000,
                      position=InfoBarPosition.TOP_RIGHT)

    def closeEvent(self, event):
        """运行中关闭窗口需要用户确认，避免中断正在抢占键鼠的任务"""
        if not self.busy:
            event.accept()
            return

        answer = QMessageBox.question(
            self,
            "任务运行中",
            "任务仍在运行，强制关闭会中断当前任务。\n确定要关闭吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            event.ignore()
            return

        # 置位停止标志（当前任务层尚未消费，保留给后续中断支持），并短暂等待线程收尾
        config.stop_thread = True
        if self.thread is not None and self.thread.isRunning():
            self.thread.wait(2000)
        event.accept()
