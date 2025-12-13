from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit
from PyQt6.QtCore import QThread, pyqtSignal
from qt_material import apply_stylesheet
from main import Full_operation
import config


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


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        version = "1.0.0"
        self.setWindowTitle(f"Paper Sweeper - v{version}")

        # 创建主布局
        layout = QVBoxLayout()

        # 创建输出文本框
        self.textbox = QTextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setFixedSize(800, 400)
        layout.addWidget(self.textbox)

        # 创建运行按钮
        self.run_button = QPushButton("完整运行")
        self.run_button.setFixedSize(100, 30)
        self.run_button.setStyleSheet("border: 1px solid #007bff;")
        self.run_button.clicked.connect(self.run_button_clicked)
        layout.addWidget(self.run_button)

        self.setLayout(layout)

    def run_button_clicked(self):
        self.textbox.append("开始完整运行...")
        config.stop_thread = False

        # 创建并启动工作线程
        self.thread = WorkerThread()
        self.thread.finished.connect(self.on_operation_finished)
        # 连接实时输出信号
        self.thread.console_output.connect(self.update_console)
        self.thread.start()

    def on_operation_finished(self, result):
        self.textbox.append("完整流程运行结束")

    def update_console(self, message):
        """更新控制台显示的槽函数"""
        # 确保文本追加操作在主线程执行
        cursor = self.textbox.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(message)
        self.textbox.setTextCursor(cursor)
        self.textbox.ensureCursorVisible()

        # 自动滚动到底部
        scrollbar = self.textbox.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


if __name__ == "__main__":
    app = QApplication([])
    apply_stylesheet(app, theme="light_blue.xml")
    window = MainWindow()
    window.resize(800, 500)
    window.show()
    app.exec()
