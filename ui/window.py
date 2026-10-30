# -*- coding: utf-8 -*-
"""主窗口与任务线程。"""

import logging

from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMessageBox, QWidget
from qfluentwidgets import (
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    MSFluentWindow,
    NavigationItemPosition,
    TransparentToolButton,
    qconfig,
)

import runtime
import Lib
from main import (
    Full_operation,
    Single_operation,
    TASK_REGISTRY,
    TaskStopped,
    completion_advanced,
    completion_snapshot,
    read_task_switches,
    request_stop,
    reset_stop,
    set_task_switch,
)
from . import prefs as ui_prefs
from . import theme_manager
from . import theme
from .panels import LeftPanel, RightPanel
from .settings_dialog import SettingsDialog
from .after_run_dialog import AfterRunDialog
from .widgets import CountdownDialog


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
                result = Full_operation(self.console_output)
            else:
                result = Single_operation(self.task_key, self.console_output)
            stopped = bool((result or {}).get("stopped"))
            self.task_finished.emit({"key": self.task_key, "ok": True, "error": None, "stopped": stopped})
        except TaskStopped:
            # 兜底：中断异常正常应在 main 层收尾，漏到这里也按「已中断」而非异常处理
            self.task_finished.emit({"key": self.task_key, "ok": True, "error": None, "stopped": True})
        except Exception as error:
            logging.critical("任务线程异常:", exc_info=True)
            try:
                print(f"TASK- ----- 任务执行出现未捕获异常: {error}")
            except Exception:
                pass
            self.task_finished.emit({"key": self.task_key, "ok": False, "error": str(error), "stopped": False})


class CloseEmulatorThread(QThread):
    """后台关闭模拟器

    **为什么必须用线程**：`MuMuManager control ... shutdown` 会同步阻塞到虚拟机
    真正关机才返回，本机实测约 4 秒（`info` 只要 0.1 秒，说明是 shutdown 本身在等）。
    放在主线程里界面会完全冻住——连倒计时弹窗的 100ms 淡出动画都停在中间帧，
    看起来就是一层半透明虚影，等几秒才「啪」地消失。
    """

    # 不能叫 finished：QThread 自己已有同名信号，重名会覆盖基类的线程结束通知
    close_finished = pyqtSignal(object)

    def run(self):
        # 异常必须在线程内捕获，否则 Qt 线程静默退出、界面一直停在「正在关闭」
        try:
            result = Lib.close_emulators()
            self.close_finished.emit({"result": result, "error": None})
        except Exception as error:
            logging.warning("关闭模拟器失败: %s", error)
            self.close_finished.emit({"result": None, "error": str(error)})


class MainWindow(MSFluentWindow):
    """主窗口：Fluent 外壳 + 双栏内容（左侧任务列表 / 右侧日志控制台）"""

    def __init__(self):
        super().__init__()
        self.left_panel = None
        self.right_panel = None
        self.thread = None
        self.busy = False
        self.before_snapshot = {}
        # 完整运行成功后暂存，等线程真正退出（QThread.finished）再执行完成动作：
        # task_finished 发出时 _log_stream 的日志文件还没关，此时睡眠会截断最后几行
        self._pending_after_run = False
        # 后台关闭模拟器的线程与「关完要做什么」的回调
        self._close_thread = None
        self._close_then_sleep = False
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
        self.right_panel.interrupt_clicked.connect(self.interrupt_job)
        self.right_panel.close_emulator_clicked.connect(self.close_emulators)
        self.right_panel.settings_clicked.connect(self.open_settings)
        self.right_panel.after_run_settings_clicked.connect(self.open_after_run_settings)

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

    def open_after_run_settings(self):
        """打开「完整运行设置」：只有两个完成动作开关，不改主题与日志偏好"""
        dialog = AfterRunDialog(self)
        if not dialog.exec():
            return

        merged = ui_prefs.load_prefs()
        merged.update(dialog.values())
        # 写盘失败必须显式提示：用户改的是「会不会把电脑睡过去」，
        # 静默失败会让人以为设置已生效
        if ui_prefs.save_prefs(merged):
            InfoBar.success(
                "设置已保存",
                "完整运行完成后的动作已更新",
                parent=self,
                duration=2000,
                position=InfoBarPosition.TOP_RIGHT,
            )
        else:
            InfoBar.error(
                "保存失败",
                "无法写入 state/gui.json，请检查目录是否可写",
                parent=self,
                duration=4000,
                position=InfoBarPosition.TOP_RIGHT,
            )

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
        runtime.stop_thread = False
        reset_stop()  # 清除上一次的中断请求，避免新任务刚开始就被停掉
        self._pending_after_run = False  # 每次启动都清掉上一轮的完成动作标记

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
        # 日志文件此时已由 _log_stream 关好，可以安全地关模拟器或睡眠
        self._run_after_actions()

    # ---- 完整运行完成后的动作 ----

    def _run_after_actions(self):
        """按设置执行完成动作；只有「完整运行成功且未中断」才会走到这里"""
        if not self._pending_after_run:
            return
        self._pending_after_run = False

        try:
            prefs = ui_prefs.load_prefs()
        except Exception as error:
            logging.warning("读取完成动作设置失败: %s", error)
            return

        close_emulator = bool(prefs.get("after_run_close_emulator"))
        sleep = bool(prefs.get("after_run_sleep"))
        if not close_emulator and not sleep:
            return

        actions = []
        if close_emulator:
            actions.append("关闭模拟器")
        if sleep:
            actions.append("让电脑进入睡眠")
        action_text = "并".join(actions)

        # 给一段可取消的缓冲期：这两个动作一个会丢进度、一个会黑屏
        dialog = CountdownDialog(self, seconds=10, action_text=action_text)
        if not dialog.exec():
            self.right_panel.append_separator("完成动作：已取消")
            return

        # 让弹窗的 100ms 淡出动画走完再干活：紧接着的关模拟器虽然已挪到后台线程，
        # 但这里同步做的那点事（写日志、建线程）也会打断动画，留下半透明残影
        QApplication.processEvents()

        self._do_after_actions(close_emulator, sleep)

    def _do_after_actions(self, close_emulator, sleep):
        """真正执行完成动作：先关模拟器，等 3 秒，再睡眠"""
        if close_emulator:
            # 关模拟器放到后台线程：MuMuManager 关机要等虚拟机真正退出（实测约 4 秒），
            # 同步跑会把界面冻住
            self._close_then_sleep = bool(sleep)
            self._start_close_emulators()
            return

        if not sleep:
            return

        self._sleep_system()

    def _start_close_emulators(self, silent=True):
        """在后台线程里关闭模拟器；关完后按 _close_then_sleep 决定是否接着睡眠"""
        if self._close_thread is not None and self._close_thread.isRunning():
            return

        self.right_panel.append_separator("关闭模拟器：正在关闭受控模拟器窗口")
        self._close_silent = bool(silent)
        self._close_thread = CloseEmulatorThread()
        self._close_thread.close_finished.connect(self._on_close_emulators_finished)
        # 线程对象在真正退出后再释放，避免 run() 尚未返回就被回收
        self._close_thread.finished.connect(self._on_close_thread_finished)
        self._close_thread.start()

    def _on_close_emulators_finished(self, payload):
        """后台关闭完成：写日志、按需提示、必要时接着睡眠"""
        error = payload.get("error")
        if error:
            self.right_panel.append_separator(f"关闭模拟器：失败 - {error}")
            if not self._close_silent:
                InfoBar.error(
                    "关闭模拟器失败",
                    error,
                    parent=self,
                    duration=5000,
                    position=InfoBarPosition.TOP_RIGHT,
                )
        else:
            self._report_close_result(payload.get("result") or {}, self._close_silent)

        if not self._close_then_sleep:
            return
        self._close_then_sleep = False
        # 给 MuMu 一点时间回收虚拟机：它持有唤醒请求时系统睡不下去
        QTimer.singleShot(3000, self._sleep_system)

    def _on_close_thread_finished(self):
        """后台线程真正退出后再断开引用"""
        thread = self.sender()
        if thread is self._close_thread:
            self._close_thread = None
        if thread is not None:
            thread.deleteLater()

    def _sleep_system(self):
        """让电脑进入睡眠；失败时明确提示，不要静默什么都不发生"""
        self.right_panel.append_separator("完成动作：正在请求系统睡眠")
        if Lib.sleep_system():
            return
        self.right_panel.append_separator("完成动作：睡眠请求失败")
        InfoBar.error(
            "睡眠失败",
            "系统拒绝了睡眠请求，请检查电源设置或当前账户权限",
            parent=self,
            duration=6000,
            position=InfoBarPosition.TOP_RIGHT,
        )

    def interrupt_job(self):
        """「中断运行」：请求中断当前任务，任务在下一个检查点退出后回到待机"""
        if not self.busy:
            return

        # 置位停止请求（同时保留 runtime.stop_thread，关闭窗口那条路径语义一致）
        request_stop()
        runtime.stop_thread = True

        self.right_panel.append_separator("中断：已请求停止，正在结束当前任务")
        self.right_panel.set_interrupting()
        InfoBar.warning(
            "正在中断",
            "已请求中断当前任务，稍候自动回到待机",
            parent=self,
            duration=2500,
            position=InfoBarPosition.TOP_RIGHT,
        )

    def close_emulators(self, silent=False):
        """「关闭模拟器」按钮入口：在后台线程关闭受控模拟器窗口

        :param silent: 由完成动作内部调用时为 True——不弹 InfoBar，
                       因为紧接着要睡眠，弹窗来不及看，日志留痕就够了
        """
        if self.busy:
            return
        self._close_then_sleep = False   # 手动点按钮不联动睡眠
        self._start_close_emulators(silent=silent)

    def _report_close_result(self, result, silent=False):
        """把关闭结果写成控制台摘要，并按需弹提示"""
        closed = result.get("closed") or []
        missing = result.get("missing") or []
        stuck = result.get("stuck") or []

        parts = [f"已关闭 {len(closed)} 个"]
        if missing:
            parts.append(f"未运行 {len(missing)} 个")
        if stuck:
            parts.append(f"仍残留 {len(stuck)} 个")
        summary = "关闭模拟器：" + "，".join(parts)
        if closed:
            summary += f"（{'、'.join(closed)}）"
        self.right_panel.append_separator(summary)

        if silent:
            return

        if stuck:
            InfoBar.warning(
                "部分模拟器未关闭",
                f"{'、'.join(stuck)} 仍在运行，可能需要手动关闭",
                parent=self,
                duration=5000,
                position=InfoBarPosition.TOP_RIGHT,
            )
        elif closed:
            InfoBar.success(
                "模拟器已关闭",
                f"已关闭 {len(closed)} 个模拟器窗口",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP_RIGHT,
            )
        else:
            InfoBar.info(
                "没有需要关闭的模拟器",
                "未发现正在运行的受控模拟器窗口",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP_RIGHT,
            )

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

        # 用户主动中断：正常收尾，不报错也不统计完成数
        if payload.get("stopped"):
            title = "完整运行" if task_key is None else self._task_title(task_key)
            self.right_panel.append_separator(f"结束：已中断（{title}）")
            InfoBar.warning(
                "已中断运行",
                "当前任务已停止，界面回到待机",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP_RIGHT,
            )
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
            # 只有完整运行成功且未中断才标记完成动作；单跑一律不触发。
            # 这里只打标记，真正执行在 on_thread_finished——那时日志文件已关好
            self._pending_after_run = True
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

        # 置位停止请求并短暂等待线程收尾；检查点按 0.2 秒切片，通常很快退出
        request_stop()
        runtime.stop_thread = True
        if self.thread is not None and self.thread.isRunning():
            self.thread.wait(3000)
        event.accept()
