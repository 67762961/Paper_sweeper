import time
import ctypes
import win32api
import win32con
import win32gui
import sys
import pyautogui
import pydirectinput
import win32process
import config
import os
import subprocess
import datetime
from Lib import Find_windows, read_config, write_config
from contextlib import redirect_stdout
from Task_LogIn import LogIn
from Task_SignIn import MainTask_Signin
from Task_Fengmo import MainTask_Fengmo
from Task_Digui import MainTask_Digui
from Task_Jiejieyangcheng import MainTask_Jiejieyangcheng


# 全局变量 窗口句柄列表
hwnds = []


# 创建了一个 Tee 类，用于同时将输出写入文件和控制台
class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, message):
        for file in self.files:
            file.write(message)
            file.flush()

    def flush(self):
        for file in self.files:
            file.flush()


def Init_MuMu():
    global hwnds
    hwnds = []
    config = read_config("./config/Last_times.json")
    headers = list(config.keys())

    for header in headers:
        hwnd = Find_windows(header)
        hwnds.append(hwnd)
    return hwnds


def Full_operation():
    # 获取当前日期和时间，用于生成唯一的文件名
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = os.path.join("logs", now.strftime("%Y-%m-%d"))

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)  # 创建文件夹

    log_file_path = os.path.join(log_dir, f"console_output_{timestamp}.log")  # 添加时间戳

    # 打开日志文件
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        # 使用 Tee 类重定向输出
        original_stdout = sys.stdout  # 保存原始 stdout
        sys.stdout = Tee(original_stdout, log_file)  # 重定向

        try:
            print("        ")
            print("MAIN- ~~~~ 完整运行流程开始 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            MainTask_Signin()
            MainTask_Jiejieyangcheng()
            MainTask_Digui()
            MainTask_Fengmo()
            print("        ")
            print("MAIN- ~~~~ 完整运行流程结束 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

        finally:
            sys.stdout = original_stdout  # 恢复原始 stdout
