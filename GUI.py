from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QCheckBox,
    QTextEdit,
    QLabel,
    QHBoxLayout,
    QFrame,
    QSpacerItem,
    QSizePolicy,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from qt_material import apply_stylesheet
from PyQt6.QtCore import QThread, pyqtSignal
from main import Full_operation, Init_MuMu
import ctypes
import config

hwnds = []


# 创建一个自定义线程类
class WorkerThread(QThread):
    # 用于向主线程发送信号
    finished = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        # 执行长时间运行的操作
        result = Full_operation()
        # 发射信号
        self.finished.emit(result)


class MainWindow(QWidget):

    def __init__(self):
        # 初始化
        super().__init__()
        self.init_ui()

    def init_ui(self):
        version = "1.0.0"
        # 窗口标题和版本号
        self.setWindowTitle(f"Paper Sweeper - v{version}")

        # 创建垂直分布
        layout = QVBoxLayout()

        # 创建顶部的只读文本框
        self.textbox = QTextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setFixedSize(800, 300)
        layout.addWidget(self.textbox)

        # 创建一个包含按钮的框架
        button_layout = QHBoxLayout()
        button_frame = QFrame()
        button_frame.setLayout(button_layout)
        button_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.9); padding: 5px;")
        button_frame.setFixedSize(800, 60)

        # 创建描述标签
        self.description_label = QLabel("按顺序完整运行所有任务")
        button_layout.addWidget(self.description_label)

        # 添加一个间隔项，使按钮靠右对齐
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        button_layout.addItem(spacer)

        # 创建“完整运行”按钮
        self.Button0 = QPushButton("完整运行")
        self.Button0.setFixedSize(100, 30)
        self.Button0.setStyleSheet("border: 1px solid #007bff;")
        self.Button0.clicked.connect(self.Button0_clicked)
        button_layout.addWidget(self.Button0)

        # 创建菜单切换按钮
        self.toggle_button = QPushButton()
        self.toggle_button.setFixedSize(30, 30)
        self.toggle_button.setStyleSheet(" border: 1px solid #007bff;")
        self.toggle_button.setText("▼")
        self.toggle_button.clicked.connect(self.toggle_menu)
        button_layout.addWidget(self.toggle_button)

        # 创建菜单框架和滚动区域
        self.menu_frame = QFrame()
        self.menu_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.9);")
        self.menu_frame.setFixedHeight(150)
        self.menu_layout = QVBoxLayout()
        self.menu_frame.setLayout(self.menu_layout)

        # 将菜单框架添加到滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.menu_frame)

        # 将按钮框架和滚动区域添加到主布局中
        layout.addWidget(button_frame)
        layout.addWidget(self.scroll_area)

        # 创建第一个复选框
        self.checkbox1 = QCheckBox("开关 1")
        self.checkbox1.stateChanged.connect(self.checkbox_changed)
        self.menu_layout.addWidget(self.checkbox1)

        # 创建第二个复选框
        self.checkbox2 = QCheckBox("开关 2")
        self.checkbox2.stateChanged.connect(self.checkbox_changed)
        self.menu_layout.addWidget(self.checkbox2)

        self.setLayout(layout)

    # 处理“完整运行”按钮点击事件
    def Button0_clicked(self):
        self.textbox.append("开始完整运行")
        config.stop_thread = False
        hwnds = Init_MuMu()
        # 创建工作线程
        self.thread = WorkerThread()
        # 连接信号与槽
        self.thread.finished.connect(self.onOperationFinished)
        # 启动线程
        self.thread.start()

    def onOperationFinished(self, result):
        # 处理线程完成后的操作
        self.textbox.append("完整流程运行结束")

    # 切换菜单的显示和隐藏
    def toggle_menu(self):
        if self.scroll_area.isVisible():
            self.scroll_area.hide()
            self.toggle_button.setText("▼")
        else:
            self.scroll_area.show()
            self.toggle_button.setText("▲")

    # 处理复选框状态改变事件
    def checkbox_changed(self, state):
        sender = self.sender()
        state_text = "选中" if state == Qt.CheckState.Checked else "未选中"
        self.textbox.append(f"{sender.text()}: {state_text}")


if __name__ == "__main__":
    app = QApplication([])
    apply_stylesheet(app, theme="light_blue.xml")  # 应用主题样式
    window = MainWindow()
    window.resize(800, 500)
    window.show()
    app.exec()
