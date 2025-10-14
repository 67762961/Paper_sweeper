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
from Task_Digui import Task_Digui
from Task_SisFoster import MainTask_Sisfoster
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


def Init():
    """
    初始化 获取窗口句柄
    """
    global hwnds
    user32 = ctypes.windll.user32

    print("INIT- +++++ 程序初始化进行中 ++++++++++++++++++++++++++++++++")

    # 首先获取游戏窗口句柄列表
    try:
        hwnds = Find_windows("阴阳师-网易游戏")
        if len(hwnds) == 2:
            print("INIT- ----- 已捕获到两个窗口 --------------------------------")
        else:
            wait = 0
            while True:
                try:
                    process1 = subprocess.Popen([config.exe_path], start_new_session=True)
                    process2 = subprocess.Popen([config.exe_path], start_new_session=True)
                    # 等待进程启动
                    process1.wait()
                    process2.wait()
                    hwnds = Find_windows("阴阳师-网易游戏")
                    if len(hwnds) == 2:
                        print("INIT- ----- 启动并捕获阴阳师 --------------------------------")
                        break
                    else:
                        process1.kill()
                        process2.kill()
                        process1 = subprocess.Popen([config.exe_path], start_new_session=True)
                        process2 = subprocess.Popen([config.exe_path], start_new_session=True)
                        process1.wait()
                        process2.wait()
                        hwnds = Find_windows("阴阳师-网易游戏")
                        wait += 1
                        time.sleep(5)
                        if len(hwnds) == 2:
                            print("INIT- ----- 启动并捕获阴阳师 --------------------------------")
                            break
                    if wait >= 3:
                        print("EROR- XXXXX 启动双开程序失败 XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
                        break
                except Exception as e:
                    print(f"启动进程或获取窗口句柄时发生异常: {e}")
    except:
        print(f"获取窗口句柄时发生异常: {e}")

    return hwnds


def Init_MuMu():
    global hwnds
    hwnds = []
    config = read_config("./config/Last_times.json")
    headers = list(config.keys())

    for header in headers:
        hwnd = Find_windows(header)
        print(hwnd)
        hwnds.append(hwnd)
        config[header]["HWND"] = hwnd

    write_config("./config/Last_times.json", config)
    print(hwnds)
    return hwnds


def Main_Login_2():
    """
    双账号登录
    """
    while not config.stop_thread:
        try:
            print("TASK- +++++ 主账号 开始登录 ++++++++++++++++++++++++++++++++")
            ctypes.windll.user32.SetForegroundWindow(hwnds[0])
            time.sleep(1)
            LogIn("master", hwnds[0])
            print("TASK- ----- 主账号已登录成功 --------------------------------")
        except:
            config.stop_thread = True
        break

    while not config.stop_thread:
        ctypes.windll.user32.SetForegroundWindow(hwnds[0])
        pyautogui.hotkey("win", "right")
        time.sleep(0.5)
        ctypes.windll.user32.SetForegroundWindow(hwnds[0])
        pyautogui.hotkey("win", "left")
        print("TASK- ----- 主窗口位置已修改 --------------------------------")
        break

    while not config.stop_thread:
        try:
            print("TASK- +++++ 从账号 开始登录 ++++++++++++++++++++++++++++++++")
            ctypes.windll.user32.SetForegroundWindow(hwnds[1])
            time.sleep(1)
            LogIn("slaves", hwnds[1])
            print("TASK- ----- 从账号已登录成功 --------------------------------")
        except:
            config.stop_thread = True
        break

    while not config.stop_thread:
        ctypes.windll.user32.SetForegroundWindow(hwnds[1])
        pyautogui.hotkey("win", "right")
        time.sleep(0.5)
        ctypes.windll.user32.SetForegroundWindow(hwnds[1])
        pyautogui.hotkey("win", "right")
        print("TASK- ----- 从窗口位置已修改 --------------------------------")

        break


def Sign_In():
    """
    邮箱奖励与庭院收菜
    """
    while not config.stop_thread:
        print()
        print("SHIF- ^^^^^ 切换游戏账号窗口 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        ctypes.windll.user32.SetForegroundWindow(hwnds[0])
        MainTask_Signin(hwnds[0], "master")

        print()
        print("SHIF- ^^^^^ 切换游戏账号窗口 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        ctypes.windll.user32.SetForegroundWindow(hwnds[1])
        MainTask_Signin(hwnds[1], "slaves")

        break


def Sis_Foster():
    """
    结界收菜种菜
    """
    while not config.stop_thread:
        print()
        print("SHIF- ^^^^^ 切换游戏账号窗口 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        ctypes.windll.user32.SetForegroundWindow(hwnds[0])
        MainTask_Sisfoster(hwnds[0], "master")

        print()
        print("SHIF- ^^^^^ 切换游戏账号窗口 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        ctypes.windll.user32.SetForegroundWindow(hwnds[1])
        MainTask_Sisfoster(hwnds[1], "slaves")

        break


def Jiejie_yangcheng():
    """
    结界收菜种菜
    """
    while not config.stop_thread:
        print()
        print("SHIF- ^^^^^ 切换游戏账号窗口 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        ctypes.windll.user32.SetForegroundWindow(hwnds[0])
        MainTask_Jiejieyangcheng(hwnds[0], "master")

        print()
        print("SHIF- ^^^^^ 切换游戏账号窗口 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        ctypes.windll.user32.SetForegroundWindow(hwnds[1])
        MainTask_Jiejieyangcheng(hwnds[1], "slaves")

        break


def Fengmo_zhishi():
    """
    逢魔之时
    """
    while not config.stop_thread:
        print()
        print("SHIF- ^^^^^ 切换游戏账号窗口 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        ctypes.windll.user32.SetForegroundWindow(hwnds[0])
        MainTask_Fengmo(hwnds[0], "master")

        print()
        print("SHIF- ^^^^^ 切换游戏账号窗口 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        ctypes.windll.user32.SetForegroundWindow(hwnds[1])
        MainTask_Fengmo(hwnds[1], "slaves")

        break


def Diyu_guiwang():
    """
    地域鬼王
    """
    while not config.stop_thread:
        print()
        print("SHIF- ^^^^^ 切换游戏账号窗口 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        ctypes.windll.user32.SetForegroundWindow(hwnds[0])
        Task_Digui(hwnds[0], "master")

        print()
        print("SHIF- ^^^^^ 切换游戏账号窗口 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        ctypes.windll.user32.SetForegroundWindow(hwnds[1])
        Task_Digui(hwnds[1], "slaves")

        break


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
            print()
            print("MAIN- ~~~~ 完整运行流程开始 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            # Main_Login_2()
            Sign_In()
            Jiejie_yangcheng()
            Diyu_guiwang()
            Fengmo_zhishi()
            print("MAIN- ~~~~ 完整运行流程结束 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

        finally:
            sys.stdout = original_stdout  # 恢复原始 stdout
