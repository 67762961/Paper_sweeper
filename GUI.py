import os
import sys

if sys.platform == "win32":
    os.environ["QT_QPA_PLATFORM"] = "windows:dpiawareness=1"

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QScrollArea, QFrame, QLabel, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
from qt_material import apply_stylesheet
from main import (
    Full_operation,
    Single_operation,
    TASK_REGISTRY,
    completion_advanced,
    completion_snapshot,
    latest_completion,
    read_completions,
)
import config

import traceback
import logging
import sys

logging.basicConfig(filename="app_crash.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s", encoding="utf-8")


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


class WorkerThread(QThread):
    """任务执行线程：task_key 为 None 时跑完整流程，否则只跑指定任务"""

    # 实时把控制台文本推给界面
    console_output = pyqtSignal(str)
    # 任务结束后回传结果（object 以便携带字典）
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


class TaskCard(QFrame):
    """单张任务卡片：点击即单独运行对应任务"""

    clicked = pyqtSignal(str)

    # 状态 -> (背景色, 边框色, 徽章背景色, 徽章文字色, 徽章文案)
    STATE_STYLES = {
        "idle": ("#ffffff", "#e3e6ea", "#eef0f3", "#5f6368", "空闲"),
        "running": ("#e8f2ff", "#007BFF", "#007BFF", "#ffffff", "运行中"),
        "done": ("#eaf7ee", "#2e7d32", "#e6f4ea", "#1b5e20", "已完成"),
        "skipped": ("#f7f8fa", "#c5c9cf", "#f1f3f5", "#6b7280", "未更新"),
        "error": ("#fdecea", "#d93025", "#fce8e6", "#b3261e", "异常"),
    }

    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.key = entry.key
        self.title = entry.title
        self.state = "idle"
        # 高度与间距配合左侧面板可用高度，保证 7 张卡片在默认窗口下一屏可见
        self.setFixedHeight(58)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # 让样式表 :hover 生效
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.init_ui(entry)
        self.set_state("idle")

    def init_ui(self, entry):
        """卡片内部布局：标题 + 状态徽章 / 业务说明 / 上次完成时间"""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(1)

        head_layout = QHBoxLayout()
        head_layout.setSpacing(6)

        self.name_label = QLabel(self.title)
        self.name_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))

        self.state_label = QLabel("空闲")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setFixedHeight(18)

        head_layout.addWidget(self.name_label)
        head_layout.addStretch()
        head_layout.addWidget(self.state_label)
        layout.addLayout(head_layout)

        self.desc_label = QLabel(entry.desc)
        layout.addWidget(self.desc_label)

        self.time_label = QLabel("上次完成 暂无记录")
        layout.addWidget(self.time_label)

        # 文字颜色与字号显式管理：卡片启用/禁用时由 setEnabled 统一切换，
        # 避免依赖 QFrame:disabled QLabel 这类会被主题样式覆盖的选择器
        self._text_labels = (
            (self.name_label, "#1f2328", "#b8bcc2", ""),
            (self.desc_label, "#6b7280", "#b8bcc2", "font-size: 11px;"),
            (self.time_label, "#8a9099", "#b8bcc2", "font-size: 11px;"),
        )
        self._apply_text_colors(True)

        self.setLayout(layout)

    def _apply_text_colors(self, enabled):
        """按启用状态设置三个文本标签的颜色（字号随标签固定，不随启用状态变化）"""
        for label, normal_color, disabled_color, extra in self._text_labels:
            color = normal_color if enabled else disabled_color
            label.setStyleSheet(f"color: {color}; background: transparent; border: none; {extra}")

    def setEnabled(self, enabled):
        """禁用时同时灰化文字，避免禁用态文字仍为深色造成误读"""
        super().setEnabled(enabled)
        self._apply_text_colors(enabled)

    def mouseReleaseEvent(self, event):
        """左键在卡片内抬起时触发点击；禁用状态下不响应（显式判断，避免事件直投时绕过 Qt 的派发过滤）"""
        if not self.isEnabled():
            super().mouseReleaseEvent(event)
            return
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self.key)
        super().mouseReleaseEvent(event)

    def set_last_time(self, moment):
        """刷新上次完成时间，moment 为 None 表示尚无记录"""
        if moment is None:
            self.time_label.setText("上次完成 暂无记录")
        else:
            self.time_label.setText(f"上次完成 {moment.strftime('%m-%d %H:%M')}")

    def set_state(self, state):
        """切换卡片状态并重绘样式"""
        self.state = state if state in self.STATE_STYLES else "idle"
        background, border, badge_background, badge_color, badge_text = self.STATE_STYLES[self.state]

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QFrame:hover:enabled {{
                border-color: #007BFF;
            }}
            QFrame:disabled {{
                background-color: #f7f8fa;
                border-color: #e3e6ea;
            }}
        """)

        self.state_label.setText(badge_text)
        self.state_label.setStyleSheet(f"""
            background-color: {badge_background};
            color: {badge_color};
            border-radius: 10px;
            padding: 1px 8px;
            font-size: 11px;
        """)


class LeftPanel(QFrame):
    """左侧任务列表面板：7 张卡片对应 TASK_REGISTRY，单击即单独运行"""

    task_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = {}
        self.init_ui()
        self.refresh_lasttimes()

    def init_ui(self):
        # 设置左侧面板样式
        self.setFixedWidth(400)
        self.setStyleSheet("background-color: #f8f9fa;")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        # 标题
        title_label = QLabel("任务列表")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; margin: 4px;")
        layout.addWidget(title_label)

        # 任务卡片滚动区域
        layout.addWidget(self.create_scroll_area())

        # 操作提示
        hint_label = QLabel("点击卡片单独运行 · 冷却与时间窗照旧生效")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("color: #8a9099; font-size: 11px;")
        layout.addWidget(hint_label)

        self.setLayout(layout)

    def create_scroll_area(self):
        """按 TASK_REGISTRY 生成任务卡片，顺序与完整运行一致"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(4)

        for entry in TASK_REGISTRY:
            card = TaskCard(entry)
            card.clicked.connect(self.task_clicked)
            scroll_layout.addWidget(card)
            self.cards[entry.key] = card

        # 顶部对齐
        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)

        return scroll_area

    def refresh_lasttimes(self):
        """读取 Last_times.yml 刷新各卡片的最近完成时间；只读，不创建配置文件"""
        try:
            completions = read_completions()
        except Exception as error:
            logging.warning("读取任务完成时间失败: %s", error)
            completions = {}

        for entry in TASK_REGISTRY:
            card = self.cards.get(entry.key)
            if card is None:
                continue
            card.set_last_time(latest_completion(entry, completions))

    def set_busy(self, busy):
        """运行期间禁用全部卡片，避免并发抢占键鼠"""
        for card in self.cards.values():
            card.setEnabled(not busy)

    def reset_states(self, running_key=None):
        """开始新一轮运行：清空旧徽章，并把正在运行的任务标记为运行中"""
        for entry in TASK_REGISTRY:
            card = self.cards.get(entry.key)
            if card is None:
                continue
            card.set_state("running" if entry.key == running_key else "idle")

    def apply_results(self, states):
        """运行结束后按 {任务key: 状态} 回填徽章，未列出的任务保持空闲"""
        for entry in TASK_REGISTRY:
            card = self.cards.get(entry.key)
            if card is None or entry.key not in states:
                continue
            card.set_state(states[entry.key])


class RightPanel(QFrame):
    """右侧控制台面板"""

    # 定义信号
    run_button_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #f8f9fa;")
        self.textbox = None
        self.run_button = None
        self.init_ui()

    def init_ui(self):
        """初始化右侧面板主布局"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 创建控制台输出区域
        self.create_console_area(layout)

        # 创建按钮区域
        self.create_button_area(layout)

        self.setLayout(layout)

    def create_console_area(self, parent_layout):
        """创建控制台输出文本框区域"""
        self.textbox = QTextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setStyleSheet("""
            QTextEdit {
                background-color: white;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                border: 1px solid #007BFF;
                border-radius: 4px;
            }
        """)
        parent_layout.addWidget(self.textbox, 1)  # 添加拉伸因子1，使文本框占据更多空间

    def create_button_area(self, parent_layout):
        """创建按钮区域"""
        # 创建运行按钮
        self.run_button = QPushButton("完整运行")
        self.run_button.setFixedHeight(40)
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #007acc;
                border-color: #007BFF;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E6F2FF;
            }
            QPushButton:pressed {
                background-color: #B8DAFF;
            }
        """)

        # 创建按钮容器，使按钮右对齐
        button_container = QFrame()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 5, 5, 5)
        button_layout.addStretch()  # 添加左侧伸缩
        button_layout.addWidget(self.run_button)
        button_container.setLayout(button_layout)

        parent_layout.addWidget(button_container)

        # 连接信号
        self.run_button.clicked.connect(self.run_button_clicked)

    def set_running(self, running):
        """运行期间禁用完整运行按钮并提示状态"""
        self.run_button.setEnabled(not running)
        self.run_button.setText("运行中…" if running else "完整运行")

    def append_separator(self, text):
        """在控制台插入一段分隔说明，便于区分多次运行"""
        self.update_console(f"\n{'=' * 78}\n{text}\n{'=' * 78}\n\n")

    def update_console(self, message):
        """更新控制台显示"""
        cursor = self.textbox.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(message)
        self.textbox.setTextCursor(cursor)
        self.textbox.ensureCursorVisible()

        # 自动滚动到底部
        scrollbar = self.textbox.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class MainWindow(QWidget):
    """主窗口类，负责组装左右面板并统一调度任务线程"""

    def __init__(self):
        super().__init__()
        self.left_panel = None
        self.right_panel = None
        self.thread = None
        self.busy = False
        self.before_snapshot = {}
        self.init_ui()

    def init_ui(self):
        version = "1.1.0"
        self.setWindowTitle(f"Paper Sweeper - v{version}")
        self.setFixedSize(1200, 600)

        # 创建主水平布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 初始化左侧面板
        self.left_panel = LeftPanel()
        main_layout.addWidget(self.left_panel)

        # 初始化右侧面板
        self.right_panel = RightPanel()
        main_layout.addWidget(self.right_panel, 1)

        self.setLayout(main_layout)

        # 连接面板信号：卡片单击跑单个任务，按钮跑完整流程
        self.left_panel.task_clicked.connect(self.on_card_clicked)
        self.right_panel.run_button_clicked.connect(self.run_button_clicked)

    def on_card_clicked(self, task_key):
        """左侧卡片点击：单独运行该任务"""
        self.start_job(task_key)

    def run_button_clicked(self):
        """完整运行按钮点击：按注册表顺序依次执行全部任务"""
        self.start_job(None)

    def start_job(self, task_key):
        """启动一次任务；同一时间只允许一个任务线程运行"""
        if self.busy:
            return

        self.busy = True
        config.stop_thread = False

        # 运行前快照，结束后用它判断任务是否真正推进了完成时间
        self.before_snapshot = completion_snapshot()

        self.left_panel.refresh_lasttimes()
        self.left_panel.reset_states(task_key)
        self.left_panel.set_busy(True)
        self.right_panel.set_running(True)

        if task_key is None:
            self.right_panel.append_separator("开始：完整运行")
        else:
            title = next((task.title for task in TASK_REGISTRY if task.key == task_key), task_key)
            self.right_panel.append_separator(f"开始：单独运行 - {title}")

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
        """任务结束：恢复界面、刷新时间、按完成时间变化回填徽章"""
        self.busy = False

        try:
            after_snapshot = completion_snapshot()
            advanced = completion_advanced(self.before_snapshot, after_snapshot)
        except Exception as error:
            logging.warning("任务完成后刷新状态失败: %s", error)
            advanced = {}

        self.left_panel.refresh_lasttimes()
        self.left_panel.set_busy(False)
        self.right_panel.set_running(False)

        task_key = payload.get("key")

        if not payload.get("ok", True):
            states = {task_key: "error"} if task_key else {}
            self.left_panel.apply_results(states)
            self.right_panel.append_separator(f"结束：异常 - {payload.get('error')}")
            return

        if task_key is None:
            # 完整运行：所有任务按完成时间是否推进回填
            states = {key: ("done" if value else "skipped") for key, value in advanced.items()}
        else:
            states = {task_key: ("done" if advanced.get(task_key) else "skipped")}

        self.left_panel.apply_results(states)
        finished = sum(1 for value in states.values() if value == "done")
        self.right_panel.append_separator(f"结束：完成 {finished} 项 / 共 {len(states)} 项（未更新详见控制台日志）")

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


if __name__ == "__main__":
    app = QApplication([])
    apply_stylesheet(app, theme="light_blue.xml")
    window = MainWindow()
    window.resize(800, 500)
    window.show()
    app.exec()
