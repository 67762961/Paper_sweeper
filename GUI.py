import os
import sys

if sys.platform == "win32":
    os.environ["QT_QPA_PLATFORM"] = "windows:dpiawareness=1"

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QScrollArea,
    QFrame,
    QLabel,
    QMessageBox,
    QAbstractButton,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSize, QRectF, QPointF
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QPolygonF
from qt_material import apply_stylesheet
from main import (
    Full_operation,
    Single_operation,
    TASK_REGISTRY,
    completion_advanced,
    completion_snapshot,
    entry_done_today,
    latest_completion,
    read_completions,
    read_task_switches,
    set_task_switch,
)
import config

import logging

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


class StatusIcon(QWidget):
    """行首的今日状态图标：已完成 ✓ / 今日未完成 ! / 运行中 ▶

    图标用 QPainter 矢量绘制，不依赖任何字体，避免换机器或打包后缺字形变成方块。
    """

    STATE_STYLES = {
        "done": ("#e6f4ea", "#1b5e20", "check", "今日已完成"),
        "pending": ("#fef3e2", "#b26a00", "alert", "今日尚未完成"),
        "running": ("#007BFF", "#ffffff", "play", "正在运行"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "pending"
        self.setFixedSize(22, 22)
        self.set_state("pending")

    def set_state(self, state):
        self.state = state if state in self.STATE_STYLES else "pending"
        _, _, _, tooltip = self.STATE_STYLES[self.state]
        self.setToolTip(tooltip)
        self.update()

    def paintEvent(self, event):
        background, color, glyph, _ = self.STATE_STYLES[self.state]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(background))
        painter.drawEllipse(QRectF(0, 0, 22, 22))

        pen = QPen(QColor(color))
        pen.setWidthF(2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QColor(color))

        if glyph == "check":
            painter.drawLine(QPointF(6.2, 11.4), QPointF(9.8, 15.0))
            painter.drawLine(QPointF(9.8, 15.0), QPointF(15.8, 7.4))
        elif glyph == "alert":
            painter.drawLine(QPointF(11, 5.8), QPointF(11, 12.4))
            painter.drawEllipse(QRectF(9.9, 14.6, 2.2, 2.2))
        else:  # play
            painter.setBrush(QColor(color))
            painter.drawPolygon(
                QPolygonF([QPointF(8.4, 6.2), QPointF(8.4, 15.8), QPointF(15.6, 11.0)])
            )
        painter.end()


class IconButton(QAbstractButton):
    """行内圆形图标按钮（齿轮 / 运行），图形同样用 QPainter 绘制，不依赖字体与图片"""

    def __init__(self, kind, tooltip, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(26, 26)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        hovered = self.underMouse() and self.isEnabled()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#e9ecef"))
            painter.drawEllipse(QRectF(1, 1, 24, 24))

        color = QColor("#1f2328") if hovered else QColor("#6b7280")
        if not self.isEnabled():
            color = QColor("#c8ccd2")

        if self.kind == "gear":
            self._paint_gear(painter, color)
        else:
            self._paint_play(painter, color)
        painter.end()

    @staticmethod
    def _paint_play(painter, color):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(
            QPolygonF([QPointF(9.6, 7.2), QPointF(9.6, 18.8), QPointF(18.4, 13.0)])
        )

    @staticmethod
    def _paint_gear(painter, color):
        """齿轮：环形 + 8 个轮齿 + 中心孔"""
        center = QPointF(13, 13)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        for index in range(8):
            painter.save()
            painter.translate(center)
            painter.rotate(index * 45)
            painter.drawRoundedRect(QRectF(-1.9, -10.4, 3.8, 4.4), 1.0, 1.0)
            painter.restore()

        ring_pen = QPen(color)
        ring_pen.setWidthF(3.4)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, 6.2, 6.2)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(center, 2.2, 2.2)


class ToggleSwitch(QAbstractButton):
    """自绘开关：开启为蓝底白钮，关闭为灰底白钮（不引入图片资源）"""

    WIDTH = 44
    HEIGHT = 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

    def sizeHint(self):
        return QSize(self.WIDTH, self.HEIGHT)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        if not self.isEnabled():
            track = QColor("#d8dbe0")
        elif self.isChecked():
            track = QColor("#007BFF")
        else:
            track = QColor("#c9ced6")

        track_top = 3
        track_height = self.HEIGHT - 6
        painter.setBrush(track)
        painter.drawRoundedRect(
            QRectF(0, track_top, self.WIDTH, track_height),
            track_height / 2,
            track_height / 2,
        )

        knob_diameter = 16
        knob_x = self.WIDTH - knob_diameter - 4 if self.isChecked() else 4
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(
            QRectF(knob_x, (self.HEIGHT - knob_diameter) / 2, knob_diameter, knob_diameter)
        )
        painter.end()


class TaskRow(QFrame):
    """单行任务：今日状态 + 名称/上次运行时间 + 齿轮 + 运行 + 开关"""

    run_clicked = pyqtSignal(str)
    config_clicked = pyqtSignal(str)
    switch_toggled = pyqtSignal(str, bool)

    def __init__(self, entry, switch_on=True, parent=None):
        super().__init__(parent)
        self.key = entry.key
        self.title = entry.title
        self.entry = entry
        self.switch_on = switch_on
        self.running = False
        self.today_done = False
        self.setObjectName("TaskRow")
        self.setFixedHeight(62)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.init_ui()
        self.set_switch(switch_on)
        self._apply_row_style()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # 最左：今日状态
        self.status_icon = StatusIcon()
        layout.addWidget(self.status_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        # 中间：任务名 + 上次运行时间
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        self.name_label = QLabel(self.title)
        self.name_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))

        self.time_label = QLabel("上次运行 暂无记录")

        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.time_label)
        layout.addLayout(text_layout, 1)

        # 右侧：齿轮 / 运行 / 开关
        self.config_button = IconButton("gear", "配置该任务（暂未开放）")
        self.run_button = IconButton("play", "单独运行该任务")
        self.switch = ToggleSwitch()
        self.switch.setToolTip("开启后参与「完整运行」，关闭则完整运行时跳过")

        layout.addWidget(self.config_button)
        layout.addWidget(self.run_button)
        layout.addWidget(self.switch)

        self.config_button.clicked.connect(lambda: self.config_clicked.emit(self.key))
        self.run_button.clicked.connect(lambda: self.run_clicked.emit(self.key))
        self.switch.toggled.connect(self.on_switch_toggled)

    # ---- 状态 ----

    def set_today_done(self, done):
        """刷新今日完成状态图标（运行中时保持运行图标）"""
        self.today_done = bool(done)
        if not self.running:
            self.status_icon.set_state("done" if self.today_done else "pending")

    def set_running(self, running):
        """切换运行中状态"""
        self.running = bool(running)
        if self.running:
            self.status_icon.set_state("running")
        else:
            self.status_icon.set_state("done" if self.today_done else "pending")
        self._apply_row_style()

    def set_last_time(self, moment):
        """刷新上次运行时间，moment 为 None 表示尚无记录"""
        if moment is None:
            self.time_label.setText("上次运行 暂无记录")
        else:
            self.time_label.setText(f"上次运行 {moment.strftime('%m-%d %H:%M')}")

    def set_busy(self, busy):
        """运行期间禁用该行的交互控件，状态与文字保持只读展示"""
        self.config_button.setEnabled(not busy)
        self.run_button.setEnabled(not busy)
        self.switch.setEnabled(not busy)

    # ---- 开关 ----

    def set_switch(self, on):
        """程序化设置开关状态（不触发写盘信号）"""
        self.switch.blockSignals(True)
        self.switch.setChecked(bool(on))
        self.switch.blockSignals(False)
        self.switch_on = bool(on)
        self._apply_row_style()

    def on_switch_toggled(self, checked):
        """用户拨动开关：更新外观并通知外部持久化"""
        self.switch_on = bool(checked)
        self._apply_row_style()
        self.switch_toggled.emit(self.key, self.switch_on)

    # ---- 外观 ----

    def _apply_row_style(self):
        if self.running:
            background, border = "#e8f2ff", "#007BFF"
        elif self.switch_on:
            background, border = "#ffffff", "#e3e6ea"
        else:
            background, border = "#f7f8fa", "#eceef1"

        self.setStyleSheet(f"""
            QFrame#TaskRow {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QFrame#TaskRow:hover {{
                border-color: #007BFF;
            }}
        """)

        # 关闭的任务整行文字变浅，明确表达「不参与完整运行」
        name_color = "#1f2328" if self.switch_on else "#9aa0a6"
        time_color = "#8a9099" if self.switch_on else "#b8bcc2"
        self.name_label.setStyleSheet(
            f"color: {name_color}; background: transparent; border: none;"
        )
        self.time_label.setStyleSheet(
            f"color: {time_color}; background: transparent; border: none; font-size: 11px;"
        )


class LeftPanel(QFrame):
    """左侧任务列表面板：7 行对应 TASK_REGISTRY，行内提供单跑与整跑开关"""

    task_run_clicked = pyqtSignal(str)
    task_config_clicked = pyqtSignal(str)
    task_toggled = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = {}
        self.init_ui()
        self.refresh()

    def init_ui(self):
        self.setFixedWidth(488)
        self.setStyleSheet("background-color: #f8f9fa;")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        title_label = QLabel("任务列表")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; margin: 4px;")
        layout.addWidget(title_label)

        layout.addWidget(self.create_scroll_area())

        hint_label = QLabel("运行按钮单独执行 · 齿轮为配置入口（暂未开放）· 开关决定是否参与完整运行")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("color: #8a9099; font-size: 11px;")
        layout.addWidget(hint_label)

        self.setLayout(layout)

    def create_scroll_area(self):
        """按 TASK_REGISTRY 生成任务行，顺序与完整运行一致"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(4)

        try:
            switches = read_task_switches()
        except Exception as error:
            logging.warning("读取任务开关失败，按全部开启处理: %s", error)
            switches = {}

        for entry in TASK_REGISTRY:
            row = TaskRow(entry, switch_on=switches.get(entry.key, True))
            row.run_clicked.connect(self.task_run_clicked)
            row.config_clicked.connect(self.task_config_clicked)
            row.switch_toggled.connect(self.task_toggled)
            scroll_layout.addWidget(row)
            self.rows[entry.key] = row

        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)

        return scroll_area

    def refresh(self):
        """刷新上次运行时间与今日状态；只读 Last_times.yml，不创建配置文件"""
        try:
            completions = read_completions()
        except Exception as error:
            logging.warning("读取任务完成时间失败: %s", error)
            completions = {}

        for entry in TASK_REGISTRY:
            row = self.rows.get(entry.key)
            if row is None:
                continue
            row.set_last_time(latest_completion(entry, completions))
            try:
                row.set_today_done(entry_done_today(entry, completions))
            except Exception as error:
                logging.warning("判定任务 %s 今日状态失败: %s", entry.key, error)
                row.set_today_done(False)

    def set_busy(self, busy):
        """运行期间禁用全部行的交互控件，避免并发抢占键鼠或中途改开关"""
        for row in self.rows.values():
            row.set_busy(busy)

    def set_running(self, task_key):
        """把指定任务行标记为运行中"""
        for key, row in self.rows.items():
            row.set_running(key == task_key)

    def clear_running(self):
        """清除所有行的运行中标记"""
        for row in self.rows.values():
            row.set_running(False)

    def set_switch_state(self, task_key, on):
        """外部回写开关状态（写盘失败时用于回滚界面）"""
        row = self.rows.get(task_key)
        if row is not None:
            row.set_switch(on)


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
        version = "1.2.0"
        self.setWindowTitle(f"Paper Sweeper - v{version}")
        self.setFixedSize(1200, 600)

        # 创建主水平布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        self.left_panel = LeftPanel()
        main_layout.addWidget(self.left_panel)

        self.right_panel = RightPanel()
        main_layout.addWidget(self.right_panel, 1)

        self.setLayout(main_layout)

        # 左侧行内交互：运行 / 配置（占位）/ 整跑开关
        self.left_panel.task_run_clicked.connect(self.on_task_run)
        self.left_panel.task_config_clicked.connect(self.on_task_config)
        self.left_panel.task_toggled.connect(self.on_task_toggled)
        self.right_panel.run_button_clicked.connect(self.run_button_clicked)

    # ---- 左侧行交互 ----

    def on_task_run(self, task_key):
        """点击行内 ▶：单独运行该任务"""
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
            self.right_panel.append_separator(f"结束：异常 - {payload.get('error')}")
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
