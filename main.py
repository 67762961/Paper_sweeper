import sys
import os
import datetime
from PyQt6.QtCore import QObject, pyqtSignal
from Lib import Find_windows, read_config
from Task_SignIn import MainTask_Signin
from Task_Fengmo import MainTask_Fengmo
from Task_Digui import MainTask_Digui
from Task_Jiejieyangcheng import MainTask_Jiejieyangcheng
from Task_Thirty import MainTask_Thirty, FullTask_Thirty
from Task_JiejieFight import MainTask_JiejieFight, FullTask_JiejieFight
from Task_Shouliezhan import MainTask_Shouliezhan


# 创建了一个 Tee 类，用于同时将输出写入文件和控制台
import sys
from PyQt6.QtCore import QObject, pyqtSignal


class Tee(QObject):
    text_written = pyqtSignal(str)

    def __init__(self, *files, text_signal=None):
        super().__init__()
        self.files = files
        self.text_signal = text_signal
        self.buffer = ""  # 添加缓冲区处理不完整的行

    def write(self, text):
        # 写入所有文件
        for file in self.files:
            if file is not None:
                file.write(text)
                file.flush()

        # 处理文本并发送到UI
        if self.text_signal:
            # 将文本添加到缓冲区
            self.buffer += text

            # 按行分割处理
            lines = self.buffer.split("\n")

            # 最后一部分可能是不完整的行，保留在缓冲区
            if text.endswith("\n"):
                # 如果以换行符结束，处理所有行并清空缓冲区
                for line in lines[:-1]:  # 最后一个是空字符串
                    if line:  # 只发送非空行
                        self.text_signal.emit(line + "\n")
                self.buffer = ""
            else:
                # 如果不以换行符结束，处理除了最后一行的所有行
                for line in lines[:-1]:
                    if line:
                        self.text_signal.emit(line + "\n")
                self.buffer = lines[-1]  # 最后一行保留在缓冲区

    def flush(self):
        # 刷新时发送缓冲区中剩余的内容
        if self.buffer and self.text_signal:
            self.text_signal.emit(self.buffer + "\n")
            self.buffer = ""

        for file in self.files:
            file.flush()


def Full_operation(console_signal=None):
    # 获取当前日期和时间，用于生成唯一的文件名
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = os.path.join("logs", now.strftime("%Y-%m-%d"))

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file_path = os.path.join(log_dir, f"console_output_{timestamp}.log")

    # 打开日志文件
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        # 使用修改后的Tee类重定向输出
        original_stdout = sys.stdout
        # 创建Tee实例，传递信号用于UI更新
        sys.stdout = Tee(original_stdout, log_file, text_signal=console_signal)

        try:
            print("        ")
            print("MAIN- ===== 完整运行流程开始 ================================================================")
            MainTask_Signin()
            MainTask_Jiejieyangcheng()
            MainTask_Digui()
            FullTask_Thirty()
            FullTask_JiejieFight()
            MainTask_Shouliezhan()
            MainTask_Fengmo()
            print("        ")
            print("MAIN- ===== 完整运行流程结束 ================================================================")

        finally:
            sys.stdout = original_stdout
