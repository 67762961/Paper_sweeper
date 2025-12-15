from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QScrollArea, QFrame, QLabel
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from qt_material import apply_stylesheet
from main import Full_operation
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
    print(f"发生致命错误，详情请查看日志文件: app_crash.log")


sys.excepthook = handle_exception


class WorkerThread(QThread):
    finished = pyqtSignal(str)
    # 添加一个用于实时更新UI的信号
    console_output = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        # 执行长时间运行的操作，传递信号用于实时更新UI
        result = Full_operation(self.console_output)
        self.finished.emit(result)


class TaskCard(QFrame):
    """任务卡片组件"""

    def __init__(self, task_name, last_run_time):
        super().__init__()
        self.task_name = task_name
        self.last_run_time = last_run_time
        self.init_ui()

    def init_ui(self):
        # 设置卡片样式
        self.setFixedHeight(80)
        self.setStyleSheet(
            """
            QFrame {
                background-color: white;
                margin: 2px;
            }
        """
        )

        # 创建卡片布局
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)

        # 任务名称
        name_label = QLabel(self.task_name)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        layout.addWidget(name_label)

        # 上次运行时间
        time_label = QLabel(f"上次运行 {self.last_run_time}")
        time_label.setStyleSheet("color: #666; font-size: 12px;")

        layout.addWidget(time_label)

        self.setLayout(layout)


class LeftPanel(QFrame):
    """左侧任务列表面板[1](@ref)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # 设置左侧面板样式
        self.setFixedWidth(400)
        self.setStyleSheet("background-color: #f8f9fa;")

        # 创建主布局[4](@ref)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # 标题
        title_label = QLabel("任务列表")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        # 创建滚动区域[6](@ref)
        scroll_area = self.create_scroll_area()
        layout.addWidget(scroll_area)

        self.setLayout(layout)

    def create_scroll_area(self):
        """创建滚动区域和任务卡片[6](@ref)"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 滚动区域内容widget
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)

        # 任务数据[8](@ref)
        task_list = [
            ("邮件", "12-10 12:00"),
            ("兑换码", "12-10 12:00"),
            ("录像店营业", "12-10 12:01"),
            ("刮刮卡", "12-10 12:02"),
            ("咖啡店", "12-10 12:03"),
            ("体力刷本", "12-10 12:07"),
            ("活跃度奖励", "12-10 12:07"),
            ("丽都周纪 (领奖励)", "12-10 12:07"),
            ("丽都城募", "12-10 12:08"),
            ("驱动盘拆解", "12-10 12:08"),
            ("枯萎之都", "12-10 12:20"),
        ]

        # 添加任务卡片[7](@ref)
        for task_name, last_run_time in task_list:
            card = TaskCard(task_name, last_run_time)
            scroll_layout.addWidget(card)

        # 添加伸缩项使卡片顶部对齐[5](@ref)
        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)

        return scroll_area


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
        self.textbox.setStyleSheet(
            """
            QTextEdit {
                background-color: white;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                border: 1px solid #007BFF;
                border-radius: 4px;
            }
        """
        )
        parent_layout.addWidget(self.textbox, 1)  # 添加拉伸因子1，使文本框占据更多空间

    def create_button_area(self, parent_layout):
        """创建按钮区域"""
        # 创建运行按钮
        self.run_button = QPushButton("完整运行")
        self.run_button.setFixedHeight(40)
        self.run_button.setStyleSheet(
            """
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
        """
        )

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
    """主窗口类，负责组装左右面板[1](@ref)"""

    def __init__(self):
        super().__init__()
        self.left_panel = None
        self.right_panel = None
        self.thread = None
        self.init_ui()

    def init_ui(self):
        version = "1.0.0"
        self.setWindowTitle(f"Paper Sweeper - v{version}")
        self.setFixedSize(1200, 600)

        # 创建主水平布局[3](@ref)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 初始化左侧面板[1](@ref)
        self.left_panel = LeftPanel()
        main_layout.addWidget(self.left_panel)

        # 初始化右侧面板[2](@ref)
        self.right_panel = RightPanel()
        main_layout.addWidget(self.right_panel, 1)

        self.setLayout(main_layout)

        # 连接右侧面板的信号[9](@ref)
        self.right_panel.run_button_clicked.connect(self.run_button_clicked)

    def run_button_clicked(self):
        """运行按钮点击事件处理[2](@ref)"""
        config.stop_thread = False

        # 创建并启动工作线程[2](@ref)
        self.thread = WorkerThread()
        self.thread.finished.connect(self.on_operation_finished)
        self.thread.console_output.connect(self.right_panel.update_console)
        self.thread.start()

    def on_operation_finished(self, result):
        """操作完成回调[2](@ref)"""


if __name__ == "__main__":
    app = QApplication([])
    apply_stylesheet(app, theme="light_blue.xml")
    window = MainWindow()
    window.resize(800, 500)
    window.show()
    app.exec()
