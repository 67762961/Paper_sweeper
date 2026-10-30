import win32gui
import win32con
import ctypes
import cv2
import pyautogui
import pydirectinput
import time
import numpy as np
import random
import re
import json
from datetime import datetime, timedelta
import os
import paths
import ruamel.yaml
import shutil
import subprocess
import threading
import yaml

# ---- 中断机制（GUI「中断运行」按钮）----
# 任务层不允许捕获 TaskStopped，让它一路抛到 main.py 统一收尾。
# 检查点放在本文件的公共原语里，因此所有 Task_*.py 无需改动。


class TaskStopped(Exception):
    """任务被用户中断：由 check_stop() 抛出，只允许在 main.py 收尾"""


_stop_event = threading.Event()
_STOP_SLICE = 0.2  # 长睡眠的切片长度，决定暂停的响应延迟上限


def request_stop():
    """请求中断当前任务（GUI 中断按钮 / 关闭窗口时调用）"""
    _stop_event.set()


def reset_stop():
    """清除中断请求（每次开始执行任务前调用）"""
    _stop_event.clear()


def stop_requested():
    """是否已请求中断：本模块的标志或项目级 runtime.stop_thread 任一为真"""
    if _stop_event.is_set():
        return True
    # 延迟导入避免与 GUI 入口循环依赖；runtime 缺失时按未请求处理
    try:
        import runtime

        return bool(getattr(runtime, "stop_thread", False))
    except Exception:
        return False


def check_stop():
    """检查点：已请求中断则抛 TaskStopped，否则立即返回"""
    if stop_requested():
        raise TaskStopped("用户中断运行")


def _sleep_with_stop(seconds):
    """可中断睡眠：按 _STOP_SLICE 切片，避免长等待把暂停卡住"""
    remaining = float(seconds)
    while remaining > 0:
        check_stop()
        chunk = _STOP_SLICE if remaining > _STOP_SLICE else remaining
        time.sleep(chunk)
        remaining -= chunk
    # 最后一个切片期间收到的中断也要生效
    check_stop()


def Sleep_print(Wait_time):
    if Wait_time <= 1:
        print("        WAIT- sssss 等待{Time}秒钟".format(Time=Wait_time))
        _sleep_with_stop(Wait_time)
    else:
        Sleep_print_long(Wait_time)


def Scroll_print(Hwnd, length):
    check_stop()
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    _sleep_with_stop(0.1)
    for i in range(abs(length)):
        check_stop()
        pyautogui.scroll(int(length / abs(length)))
        _sleep_with_stop(0.01)
    print("        MOVE- mmmmm 滚轮滚动{Length}".format(Length=length))


def Esc_print(Hwnd):
    check_stop()
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    _sleep_with_stop(0.1)
    pydirectinput.press("esc")
    _sleep_with_stop(0.1)
    print("        QUIT- ccccc 按Esc退出")
    return Itface_Quit(Hwnd)


def Find_windows(title):
    """
    寻找与标题相符的句柄
    :param title:   窗口标题
    :return:        返回符合的窗口列表
    """

    # 枚举窗口
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and title in win32gui.GetWindowText(hwnd):
            hwnds.append(hwnd)
        return True

    check_stop()
    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    if hwnds:
        return hwnds[0]
    else:
        print("        INFO- ----- 未检测到窗口", title, "正在尝试启动游戏")
        Log_in(title)
        return Find_windows(title)


def Log_in(title):
    check_stop()
    config = read_config(paths.SETTING)
    launch_cmd = config["启动项"][title]["启动命令"]
    subprocess.Popen(launch_cmd, shell=True)
    print("        INFO- -----", title, "正在启动")
    _sleep_with_stop(25)
    Hwnd = Find_windows(title)

    for Wait in range(100):
        check_stop()
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/适龄提示标.png", 0.03, 0)
        if Range:
            Sleep_print(1)
            print("        INFO-", Matchs, "检测到适龄提示界面 点击进入游戏")
            Click(Hwnd, [(830, 940), (1085, 1010)], 1)
            Sleep_print(1)
            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/适龄提示标.png", 0.03, 0)
            if not Range:
                print("        INFO-", Matchs, "未检测到适龄提示界面 已经进入游戏")
                Sleep_print(5)
                return 1
        else:
            print("        INFO-", Matchs, "未检测到适龄提示界面")
            print("        WAIT- wwwww 等待准备 已等待 {waittime} 秒".format(waittime=Wait * 1 + 20))
            Sleep_print(1)


# ---- 系统动作（GUI「关闭模拟器」按钮）----
# 与任务流程完全解耦：这些函数不在任务线程里跑，也不依赖中断机制。
# 关键约束：**只读枚举窗口，绝不调用 Find_windows**——那个函数找不到窗口时会去
# 启动游戏（Log_in），"关闭"场景一旦复用它就变成"先启动再关闭"，还会卡 25 秒以上。


def find_windows_silent(title):
    """按标题子串只读枚举可见窗口，找不到返回 None

    与 Find_windows 的唯一区别：**不启动游戏**。关闭模拟器只能用它。
    """
    hwnds = []

    def callback(hwnd, collected):
        if win32gui.IsWindowVisible(hwnd) and title in win32gui.GetWindowText(hwnd):
            collected.append(hwnd)
        return True

    win32gui.EnumWindows(callback, hwnds)
    return hwnds[0] if hwnds else None


def controlled_accounts(config=None):
    """受程序管理的账号名列表（即 Setting.yml 里 启动项 的 key）

    这是"受程序掌握"的唯一判定依据：只有登记过的账号窗口才会被关闭，
    用户手动开的、标题不匹配的窗口一律不碰。
    """
    config = read_config(paths.SETTING) if config is None else config
    launch_items = (config or {}).get("启动项") or {}
    if not isinstance(launch_items, dict):
        return []
    return [account for account in launch_items.keys()]


def _launch_commands(config=None):
    """返回 {账号: 启动命令字符串}；缺失或格式异常时跳过该账号"""
    config = read_config(paths.SETTING) if config is None else config
    launch_items = (config or {}).get("启动项") or {}
    if not isinstance(launch_items, dict):
        return {}
    commands = {}
    for account, item in launch_items.items():
        if isinstance(item, dict):
            command = item.get("启动命令")
            if isinstance(command, str) and command.strip():
                commands[account] = command.strip()
    return commands


def parse_instance_number(launch_cmd):
    """从启动命令里取出 MuMu 实例号（-v N 的 N），解析失败返回 None

    形如 "...MuMuNxMain.exe -p com.xxx -v 1" -> 1
    """
    if not launch_cmd:
        return None
    match = re.search(r"-v\s+(\d+)", launch_cmd)
    return match.group(1) if match else None


def _launch_exe_dir(launch_cmd):
    """从启动命令里取出主程序所在目录，解析失败返回 None

    不写死任何安装路径：MuMu 装在哪、换盘符、升级换目录都从
    Setting.yml 的启动命令推导，那里已经是权威来源。
    """
    if not launch_cmd:
        return None
    match = re.search(r'"?([A-Za-z]:[^"]*?\.exe)"?', launch_cmd, re.IGNORECASE)
    if not match:
        return None
    return os.path.dirname(match.group(1).replace("\\", os.sep).replace("/", os.sep))


def find_mumu_manager(launch_cmd, config=None):
    """定位 MuMuManager.exe，找不到返回 None

    优先级：
    1. Setting.yml 的 模拟器.MuMuManager（可选键，用户想显式指定时的逃生口）
    2. 从启动命令推导出的主程序目录 → 同目录 / 上一级 / shell 子目录
    3. 都找不到 → None（调用方降级为关窗口）
    """
    explicit = (read_config(paths.SETTING) if config is None else config) or {}
    simulator = explicit.get("模拟器") or {}
    if isinstance(simulator, dict):
        manual = simulator.get("MuMuManager")
        if isinstance(manual, str) and manual.strip() and os.path.isfile(manual.strip()):
            return manual.strip()

    exe_dir = _launch_exe_dir(launch_cmd)
    if not exe_dir:
        return None

    parent = os.path.dirname(exe_dir)
    candidates = (
        os.path.join(exe_dir, "MuMuManager.exe"),
        os.path.join(parent, "MuMuManager.exe"),
        os.path.join(parent, "shell", "MuMuManager.exe"),
    )
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def _run_manager(manager_path, args, timeout=15):
    """调用 MuMuManager 并解析其 JSON 输出，成功返回 True

    MuMuManager 的约定是输出 {"errcode": 0, "errmsg": ""}，errcode 为 0 表示成功。
    进程起不来、超时、输出不是 JSON 都按失败处理，由调用方降级。
    """
    try:
        completed = subprocess.run(
            [manager_path] + list(args),
            capture_output=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as error:
        print("        WAIT- ----- MuMuManager 调用失败:", error)
        return False

    output = (completed.stdout or b"").decode("utf-8", errors="replace").strip()
    if not output:
        return False
    try:
        payload = json.loads(output)
    except ValueError:
        # 老版本可能直接输出纯文本，返回码为 0 也认
        return completed.returncode == 0
    if isinstance(payload, dict):
        return payload.get("errcode", 0) == 0
    return completed.returncode == 0


def shutdown_via_manager(manager_path, indexes):
    """按实例号关机；两种子命令顺序都试，任一成功即返回 True

    不同 MuMu 大版本的参数位置不同（control -v N shutdown / control shutdown -v N），
    这里不猜版本，两种都试一遍，都失败再由调用方降级为关窗口。
    """
    index_arg = ",".join(str(index) for index in indexes)
    attempts = (
        ["control", "-v", index_arg, "shutdown"],
        ["control", "shutdown", "-v", index_arg],
    )
    for args in attempts:
        if _run_manager(manager_path, args):
            print("        INFO- ----- 已通过 MuMuManager 请求关机 实例:", index_arg)
            return True
        print("        INFO- ----- MuMuManager 关机命令未成功 尝试下一种写法:", " ".join(args))
    return False


def close_emulators(wait_seconds=2):
    """关闭所有受程序管理的模拟器窗口

    流程：MuMuManager 按实例号关机（最干净）→ 等待 → 复查
          仍在的窗口逐个发 WM_CLOSE（兜底）

    :return: {"closed": [账号...], "missing": [...], "stuck": [...]}
             closed  本次确认已关闭的账号
             missing 本来就没在运行的账号
             stuck   发了 WM_CLOSE 但窗口仍在的账号
    """
    result = {"closed": [], "missing": [], "stuck": []}

    config = read_config(paths.SETTING) or {}
    commands = _launch_commands(config)
    accounts = controlled_accounts(config)
    if not accounts:
        print("        INFO- ----- Setting.yml 未登记任何启动项 无可关闭的模拟器")
        return result

    # 关闭前先记录哪些账号本来就在跑，用来区分 closed 与 missing
    running_before = {account: find_windows_silent(account) for account in accounts}
    alive = [account for account, hwnd in running_before.items() if hwnd]

    if not alive:
        print("        INFO- ----- 未发现正在运行的受控模拟器窗口")
        result["missing"] = list(accounts)
        return result

    # 第一级：MuMuManager 按实例号关机（虚拟机正常退出，最干净）
    manager_path = None
    for account in alive:
        manager_path = find_mumu_manager(commands.get(account), config)
        if manager_path:
            break

    if manager_path:
        print("        INFO- ----- 使用 MuMuManager:", manager_path)
        indexes = [parse_instance_number(commands.get(account)) for account in alive]
        indexes = [index for index in indexes if index is not None]
        if indexes:
            shutdown_via_manager(manager_path, indexes)
            try:
                _sleep_with_stop(wait_seconds)
            except TaskStopped:
                print("        QUIT- ----- 关闭模拟器收到中断请求 已停止")
                return result
    else:
        print("        INFO- ----- 未找到 MuMuManager 降级为关窗口")

    # 第二级：仍在的窗口逐个发 WM_CLOSE（只关窗口，虚拟机由 MuMu 自己回收）
    for account in alive:
        hwnd = find_windows_silent(account)
        if hwnd is None:
            continue
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            print("        INFO- ----- 已向窗口发送关闭消息:", account)
        except Exception as error:
            print("        WAIT- ----- 发送关闭消息失败:", account, error)

    # 复查：关掉的算 closed，仍在的算 stuck，原本没开的算 missing
    for account in accounts:
        if account not in alive:
            result["missing"].append(account)
            continue
        if find_windows_silent(account) is None:
            result["closed"].append(account)
        else:
            result["stuck"].append(account)

    print(
        "        INFO- ----- 关闭模拟器完成 已关闭 {closed} 个 未运行 {missing} 个 仍残留 {stuck} 个".format(
            closed=len(result["closed"]),
            missing=len(result["missing"]),
            stuck=len(result["stuck"]),
        )
    )
    return result


def Img_read_ch(file_path):
    """读取包含中文路径的图片"""
    # 使用numpy从二进制数据读取
    with open(file_path, "rb") as f:
        img_data = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
    return img


def Match_model(Img, Img_model_path, Threshold, Flag_show, search_range=None, is_window_match=False):
    """
    内部模板匹配函数
    :param Img: 输入图像
    :param Img_model_path: 模板图片路径
    :param Threshold: 匹配阈值
    :param Flag_show: 是否显示结果
    :param search_range: 搜索区域，格式为[Left_up, Right_down]（相对于输入图像）
    :param is_window_match: 是否为窗口匹配（用于控制是否显示内部点击区域）
    :return: 匹配结果和匹配得分
    """
    check_stop()
    # 加载图像模板
    Img_model = Img_read_ch(Img_model_path)
    if Img_model is None:
        raise ValueError(f"无法找到文件: {Img_model_path}")

    Img_model_height, Img_model_width = Img_model.shape[0:2]

    # 确保数据类型为 np.uint8
    Img = np.uint8(Img)
    Img_model = np.uint8(Img_model)

    # 如果指定了搜索区域，则在区域内进行匹配
    if search_range is not None:
        # 提取区域坐标
        range_left_up, range_right_down = search_range

        # 确保区域在图像范围内
        height, width = Img.shape[0:2]
        x1 = max(0, range_left_up[0])
        y1 = max(0, range_left_up[1])
        x2 = min(width, range_right_down[0])
        y2 = min(height, range_right_down[1])

        # 截取指定区域
        Img_region = Img[y1:y2, x1:x2]
    else:
        # 如果没有指定区域，使用整个图像
        Img_region = Img
        x1, y1 = 0, 0  # 区域相对于原图像的偏移量

    # 进行模板匹配
    Result = cv2.matchTemplate(Img_region, Img_model, cv2.TM_SQDIFF_NORMED)

    # 获取匹配结果
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(Result)

    # 计算匹配区域在原图像中的位置
    match_x = min_loc[0] + x1
    match_y = min_loc[1] + y1

    # 确定识别到的区域
    Left_up = (match_x, match_y)
    Right_down = (match_x + Img_model_width, match_y + Img_model_height)

    # 显示结果
    if Flag_show:
        # 深拷贝原始图像以避免修改
        Img_display = Img.copy()

        # 如果指定了搜索区域，用蓝框标定
        if search_range is not None:
            cv2.rectangle(Img_display, search_range[0], search_range[1], (255, 0, 0), 2)

        # 用红框标定匹配区域
        cv2.rectangle(Img_display, Left_up, Right_down, (0, 0, 255), 2)

        # 计算点击区域（与Click函数中的计算一致）
        Width = Right_down[0] - Left_up[0]
        Height = Right_down[1] - Left_up[1]
        click_Left_up = (int(Left_up[0] + Width / 4), int(Left_up[1] + Height / 4))
        click_Right_down = (int(Left_up[0] + 3 * Width / 4), int(Left_up[1] + 3 * Height / 4))

        # 如果是窗口匹配，显示点击区域
        if is_window_match:
            cv2.rectangle(Img_display, click_Left_up, click_Right_down, (0, 255, 0), 2)

        window_title = "Window Match" if is_window_match else "Screen Match"
        if search_range is not None:
            window_title += " with Range"

        cv2.imshow(window_title, Img_display)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # 返回结果
    return2 = f"{min_val:.3f}"

    if min_val > Threshold:
        return1 = None
    else:
        return1 = [Left_up, Right_down]

    return return1, return2


def Find_in_windows_Matchs(Hwnd, Model_path, Threshold, Flag_show):
    """
    窗口内截图并找到与模板匹配的图片区域
    """
    check_stop()
    # 获取窗口位置和大小
    window_rect = win32gui.GetWindowRect(Hwnd)
    left, top, right, bottom = window_rect

    # 直接在全屏截图中截取窗口区域
    Screenshot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))

    # 转换为OpenCV格式
    Img = cv2.cvtColor(np.array(Screenshot), cv2.COLOR_RGB2BGR)

    # 调用内部模板匹配函数，标记为窗口匹配
    return Match_model(Img, Model_path, Threshold, Flag_show, is_window_match=True)


def Find_in_windows_Range(Hwnd, Range, Model_path, Threshold, Flag_show):
    """
    在窗口内的指定区域内进行模板匹配
    """
    check_stop()
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    # 获取窗口位置和大小
    window_rect = win32gui.GetWindowRect(Hwnd)
    left, top, right, bottom = window_rect

    # 截取整个窗口
    Screenshot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
    Img = cv2.cvtColor(np.array(Screenshot), cv2.COLOR_RGB2BGR)

    # 调用Match_model函数，传入搜索区域
    return1, return2 = Match_model(Img, Model_path, Threshold, Flag_show, search_range=Range, is_window_match=True)

    # 如果匹配成功，返回窗口坐标
    if return1 is not None:
        return1_window = return1
    else:
        return1_window = None

    return return1_window, return2


def Find_multiple_in_windows_Matchs(Hwnd, Model_path, Threshold, Flag_show, max_matches=10):
    """
    窗口内截图并找到多个与模板匹配的图片区域
    通过重复调用Match_model实现 每次找到后蒙版盖住再找下一个
    """
    check_stop()
    # 获取窗口位置和大小
    window_rect = win32gui.GetWindowRect(Hwnd)
    left, top, right, bottom = window_rect

    # 直接在全屏截图中截取窗口区域
    Screenshot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))

    # 转换为OpenCV格式
    Img_original = cv2.cvtColor(np.array(Screenshot), cv2.COLOR_RGB2BGR)

    # 创建用于匹配的图像副本
    Img_working = Img_original.copy()

    positions = []  # 存储匹配位置 [(Left_up, Right_down), ...]
    scores = []  # 存储匹配得分

    # 循环查找多个匹配
    for i in range(max_matches):
        check_stop()
        # 调用现有的Match_model函数
        return1, return2 = Match_model(Img_working, Model_path, Threshold, False, None, True)

        # 将匹配度字符串转换为浮点数
        try:
            match_score = float(return2)
        except ValueError:
            match_score = 1.0  # 如果转换失败，设为最差值

        # 如果没有找到匹配或匹配度超过阈值，停止搜索
        if return1 is None or match_score > Threshold:
            break

        # 获取匹配位置
        Left_up, Right_down = return1

        # 记录匹配结果
        positions.append((Left_up, Right_down))
        scores.append(match_score)

        # 用蒙版盖住已匹配区域（避免重复检测）
        cv2.rectangle(Img_working, Left_up, Right_down, (0, 0, 0), -1)

        _sleep_with_stop(0.05)

    # 显示结果（如果启用）
    if Flag_show and positions:
        # 深拷贝原始图像以避免修改
        Img_display = Img_original.copy()

        # 每个匹配位置都显示红色框和绿色点击区域框
        for Left_up, Right_down in positions:
            # 用红框标定匹配区域
            cv2.rectangle(Img_display, Left_up, Right_down, (0, 0, 255), 2)

            # 计算点击区域（与Click函数中的计算一致）
            Width = Right_down[0] - Left_up[0]
            Height = Right_down[1] - Left_up[1]
            click_Left_up = (int(Left_up[0] + Width / 4), int(Left_up[1] + Height / 4))
            click_Right_down = (int(Left_up[0] + 3 * Width / 4), int(Left_up[1] + 3 * Height / 4))

            # 显示点击区域（绿色框）
            cv2.rectangle(Img_display, click_Left_up, click_Right_down, (0, 255, 0), 2)

        cv2.imshow("Multiple Window Matches", Img_display)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # 返回结果：数量, 位置列表, 匹配度列表
    return len(positions), positions, scores


def Move_to_range(Hwnd, Loc):
    """
    计算点击位置并移动鼠标到该位置
    :param Hwnd: 窗口句柄 如果为None则使用屏幕坐标
    :param Loc: 坐标元组 格式为[(左上x,左上y), (右下x,右下y)]
    :return: 移动到的目标坐标 (x, y) 或 0 当Loc为空时
    """
    # 移动鼠标前检查：避免用户按下中断后还多点/多移动一下
    check_stop()
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    # 检测Loc是否为空
    if not Loc or len(Loc) < 2:
        print("Loc参数非法 ", Loc, " 跳过鼠标移动操作")
        return 0

    if Hwnd:
        # 计算点击区域在窗口内的绝对坐标
        window_x, window_y, _, _ = win32gui.GetWindowRect(Hwnd)
        ctypes.windll.user32.SetForegroundWindow(Hwnd)
    else:
        window_x, window_y = 0, 0

    # 计算出识别区域长宽
    Width = Loc[1][0] - Loc[0][0]
    Height = Loc[1][1] - Loc[0][1]

    # 计算点击区域（在识别区域内部的1/4到3/4范围内随机点击）
    target_x = window_x + Loc[0][0] + Width / 4 + random.randint(0, Width) / 2
    target_y = window_y + Loc[0][1] + Height / 4 + random.randint(0, Height) / 2

    # 移动鼠标到目标位置
    pyautogui.moveTo(x=target_x, y=target_y)

    return target_x, target_y


def Click(Hwnd, Loc, Wait):
    """
    接受一个坐标元组 自动点击
    :param Hwnd: 窗口句柄 如果为None则使用屏幕坐标
    :param Loc: 坐标元组 格式为[(左上x,左上y), (右下x,右下y)]
    :param Wait: 点击后自动延时的等待时间
    :return: None
    """
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    # 先移动鼠标到目标位置
    if not Move_to_range(Hwnd, Loc):
        print("点击位置无效 跳过点击操作")
        return 0
    else:
        # 执行点击操作
        pyautogui.click(button="left")
        _sleep_with_stop(Wait)
        return 1


def Find_Click_windows(Hwnd, Model_path, Threshold, message_F, message_C):
    check_stop()
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    Range, Matchs = Find_in_windows_Matchs(Hwnd, Model_path, Threshold, 0)
    if not Matchs:
        Matchs = 0
    if Range and (len(Range) >= 2):
        Range, Matchs = Find_in_windows_Matchs(Hwnd, Model_path, Threshold, 0)
        if Click(Hwnd, Range, 1):
            print("        INFO-", Matchs, message_F)
            return 1
        else:
            print("        INFO- 点击失败", Matchs, message_C)
            return 0
    else:
        print("        INFO-", Matchs, message_C)
        return 0


def Find_in_screen_Matchs(Img_model_path, Threshold, Flag_show):
    """
    全屏截图并找到与模板匹配的图片区域
    """
    check_stop()
    # 截取屏幕
    Screenshot = pyautogui.screenshot()

    # 转换为OpenCV格式
    Img = cv2.cvtColor(np.array(Screenshot), cv2.COLOR_RGB2BGR)

    # 调用内部模板匹配函数
    return Match_model(Img, Img_model_path, Threshold, Flag_show)


def Find_Click_screen(Model_path, Threshold, message_F, message_C):
    Range, Matchs = Find_in_screen_Matchs(Model_path, Threshold, 0)
    if not Matchs:
        Matchs = 0
    if Range:
        Click(None, Range, 1)
        print("        INFO-", Matchs, message_F)
        return 1
    else:
        print("        INFO-", Matchs, message_C)
        return 0


def Sleep_print_long(Wait_time):

    print("        WAIT- sssss 等待{Time}秒钟".format(Time=Wait_time))
    _sleep_with_stop(Wait_time)

    # 拒绝协作
    if Wait_time > 1:
        Range, Matchs = Find_in_screen_Matchs("./pic/common/拒绝协作.png", 0.01, 0)
        if Range:
            Find_Click_screen("./pic/common/拒绝协作.png", 0.01, "拒绝协作", "未发现协作")


def read_config(FILE_PATH):
    """
    读取YAML配置文件

    文件不存在、内容为空或格式损坏时返回空字典，而不是抛异常。
    配置损坏不应该让 GUI 在启动时就崩掉——具体是哪个文件、什么原因，由日志暴露；
    真正依赖配置内容的调用方会在取键时失败，报错位置更准确。

    :param FILE_PATH: 配置文件路径
    :return: 解析后的配置字典；无法读取或解析时返回 {}
    """
    if not os.path.exists(FILE_PATH):
        return {}

    try:
        yaml = ruamel.yaml.YAML()
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except (OSError, UnicodeDecodeError, ruamel.yaml.YAMLError) as error:
        reason = str(error).splitlines()[0] if str(error) else type(error).__name__
        print("        INFO- ----- 配置文件无法解析，按空配置处理:", FILE_PATH)
        print("        INFO- -----", reason)
        return {}

    # 空文件解析结果是 None，统一成空字典，避免调用方对 None 取键
    return data if data is not None else {}


def write_config(FILE_PATH, data):
    """
    将配置写入文件
    """
    yaml = ruamel.yaml.YAML()
    # 设置保留引号格式和缩进
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    with open(FILE_PATH, "w", encoding="utf-8") as file:
        yaml.dump(data, file)


def _backup_corrupt_config(file_path):
    """把损坏的配置文件另存为带时间戳的 .bak，返回备份路径；失败返回 None

    check_lasttime 在配置损坏时会把文件重置为初始值，原内容若不先备份就永久丢失。
    备份文件名形如 Last_times.yml.corrupt-20261021-204700.bak，与配置同目录。
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{file_path}.corrupt-{stamp}.bak"
    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except OSError as error:
        print("        WAIT- ----- 备份损坏配置失败:", error)
        return None


def check_lasttime(Account, Times_name):
    """
    检测上次运行的时间 如果文件或配置不存在则自动创建
    使用ruamel.yaml处理YAML格式配置文件

    配置损坏时会重置为初始值，但重置前会把原文件备份成 .corrupt-*.bak，
    避免用户的历史记录被静默清空。
    """
    file_path = paths.LAST_TIMES

    # 初始化ruamel.yaml
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    CommentedMap = ruamel.yaml.comments.CommentedMap

    # 确保状态目录存在（同时把旧布局 config/Last_times.yml 迁过来）
    paths.ensure_state_dir()
    config_dir = os.path.dirname(file_path)
    if config_dir and not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir, exist_ok=True)
            print("创建配置目录: ", config_dir)
        except OSError as e:
            print("无法创建目录 ", config_dir, ":", e)
            return datetime(2000, 1, 1, 0, 0)

    # 检查文件是否存在 不存在则创建
    if not os.path.exists(file_path):
        print("配置文件不存在 创建新文件: ", file_path)
        try:
            # 创建空的CommentedMap以保留YAML结构
            config = CommentedMap()
            # 使用ruamel.yaml保存空配置
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f)
            config = CommentedMap()
        except Exception as e:
            print("创建配置文件失败: ", e)
            return datetime(2000, 1, 1, 0, 0)
    else:
        # 文件存在 正常读取
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read().strip()
                if not content:  # 处理空文件情况
                    config = CommentedMap()
                else:
                    config = yaml.load(content)
                    if config is None:  # 处理YAML文件内容为null的情况
                        config = CommentedMap()
        except (OSError, UnicodeDecodeError, ruamel.yaml.YAMLError) as error:
            print("        WAIT- ----- 读取配置文件失败:", str(error).splitlines()[0] if str(error) else type(error).__name__)
            # 尝试使用更宽松的方式重新读取
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    config = yaml.load(file) or CommentedMap()
            except (OSError, UnicodeDecodeError, ruamel.yaml.YAMLError) as retry_error:
                # 文件确实坏了：重置前先备份，否则历史记录会被静默清空
                backup_path = _backup_corrupt_config(file_path)
                print("        WAIT- ----- 配置文件格式错误，将重置为初始值")
                if backup_path:
                    print("        WAIT- ----- 原文件已备份:", backup_path)
                else:
                    print("        WAIT- ----- 备份失败，原文件内容将丢失")
                print("        WAIT- ----- 原因:", str(retry_error).splitlines()[0] if str(retry_error) else type(retry_error).__name__)
                config = CommentedMap()

    # 确保配置是CommentedMap类型
    if not isinstance(config, CommentedMap):
        config = CommentedMap(config)

    # 确保Account键存在
    if Account not in config:
        config[Account] = CommentedMap()

    # 确保Account对应的值也是CommentedMap类型
    if not isinstance(config[Account], (dict, CommentedMap)):
        config[Account] = CommentedMap({Times_name: config[Account]})

    Times_need_str = config[Account].get(Times_name, None)

    # 解析时间字符串
    if Times_need_str is not None:
        try:
            Times_need = datetime.fromisoformat(Times_need_str)
        except (ValueError, TypeError):
            print(f"时间格式错误: {Times_need_str}，将使用默认时间")
            Times_need = None
    else:
        Times_need = None

    if Times_need is not None:
        print("        TIME- ----- ", Times_need.strftime("%Y-%m-%d %H:%M:%S"))
        return Times_need
    else:
        print("        TIME- ----- 没有记录上次时间 已重置初始化值")
        Initial_time = datetime(2000, 1, 1, 0, 0)
        config[Account][Times_name] = Initial_time.isoformat()

        # 安全写入配置
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f)
            print("配置已更新并保存")
        except Exception as e:
            print("保存配置失败: ", e)

        return Initial_time


# ---- 任务准入策略（供 run_accounts_task 使用）----
# 每个策略接收 (上次完成时间, 当前时间)，返回 True 表示本次可以执行。


def read_accounts():
    """读取 Last_times.yml 中的账号列表，保持文件中的顺序"""
    config_data = read_config(paths.LAST_TIMES)
    return list(config_data.keys())


def ready_daily(last_time, now):
    """当日未完成才执行：上次完成时间不是今天"""
    return last_time.date() != now.date()


def ready_weekly(last_time, now):
    """本周未完成才执行：按 ISO 周比较"""
    return last_time.isocalendar()[1] != now.isocalendar()[1]


def ready_after(hours):
    """距上次完成满 N 小时才执行（工厂函数）

    :param hours: 冷却小时数
    :return:      准入判断函数，带 hours 属性供 skip_text 生成文案
    """

    def check(last_time, now):
        return abs(now - last_time) >= timedelta(hours=hours)

    check.hours = hours
    return check


def skip_text(name, ready):
    """按准入策略生成 SKIP 日志文案

    :param name:  任务名
    :param ready: 准入判断函数（ready_daily / ready_weekly / ready_after 的产物）
    """
    if ready is ready_daily:
        return "        SKIP- ----- 今日已完成" + name + "任务 跳过"
    if ready is ready_weekly:
        return "        SKIP- ----- 本周已完成" + name + "任务 跳过"
    hours = getattr(ready, "hours", None)
    if hours:
        hours_cn = {1: "一小时", 6: "六小时"}.get(hours, str(hours) + "小时")
        return "        SKIP- ----- " + name + "任务时间间隔未满" + hours_cn + " 跳过"
    return "        SKIP- ----- " + name + "任务未到执行时间 跳过"


def write_task_time(Account, Times_name):
    """把某账号某任务的成功时间写回 Last_times.yml

    :param Account:    账号名（Last_times.yml 的顶层键）
    :param Times_name: 任务键（如「逢魔之时」「邮件领取」）
    :return:           写入的时间字符串，便于调用方打印 TIME- 日志
    """
    config = read_config(paths.LAST_TIMES)
    Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    config[Account][Times_name] = Now
    write_config(paths.LAST_TIMES, config)
    return Now


# ---- 单账号任务的固定流程 ----

TASK_LINE_WIDTH = 84  # 任务分隔线总宽度（统一值）


def _task_line(title):
    """输出一条总宽 TASK_LINE_WIDTH 的 TASK- 分隔线"""
    print("TASK- ----- " + title + " " + "-" * (TASK_LINE_WIDTH - 12 - len(title) - 1))


def _fmt_window(window):
    """把时间窗 (time, time) 格式化为 'HH:MM-HH:MM'"""
    return window[0].strftime("%H:%M") + "-" + window[1].strftime("%H:%M")


def run_accounts_task(name, ready, work, window=None, write_back=True):
    """单账号任务的固定流程：时间窗 → 遍历账号 → 准入判断 → 执行业务 → 写回时间

    所有日志文案由任务名与时间窗自动生成，调用方只需描述"这个任务是什么"。

    :param name:       任务名（同时是 Last_times.yml 的任务键）
    :param ready:      准入判断函数 (last_time, now) -> bool；
                       None 表示硬跑：不读上次时间、不判断冷却与时间窗，直接执行
    :param work:       业务执行函数 (Account) -> 真值表示成功
    :param window:     时间窗 (begin, end)，None 表示不限；ready=None 时忽略
    :param write_back: 成功后是否写回时间（纸人奖励不写回）
    """
    _task_line("开始" + name + "任务")

    if ready is not None:
        # ---- 按需跑：时间窗 + 读上次时间 + 冷却判断 ----
        now = datetime.now()
        if window is not None:
            if not (window[0] <= now.time() <= window[1]):
                print("TASK- ----- 当前时间不在" + _fmt_window(window) + "之间 跳过")
                _task_line(name + "任务结束")
                return
            print("TASK- ----- 当前时间在" + _fmt_window(window) + "之间 开始执行" + name + "任务")

        for Account in read_accounts():
            check_stop()
            print("    切换到 ", Account, " 账号")
            print("        TIME- ----- 读取上次账号", Account, "完成" + name + "任务时间")
            last_time = check_lasttime(Account, name)
            now = datetime.now()
            if ready(last_time, now):
                if work(Account):
                    Now = write_task_time(Account, name) if write_back else None
                    if write_back:
                        print("        TIME- ----- 本次" + name + "完成时间")
                        print("        TIME- ----- ", Now)
                    else:
                        # 不写回的任务（如纸人奖励）只打印时间，不打印"本次…完成时间"
                        print("        TIME- ----- ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    print("        TASK- ----- " + name + "任务完成")
                else:
                    print("        TASK- ----- " + name + "任务执行过程中出现错误 中断任务")
            else:
                print(skip_text(name, ready))
    else:
        # ---- 硬跑：不读上次时间，直接执行 ----
        for Account in read_accounts():
            check_stop()
            print("    切换到 ", Account, " 账号")
            if work(Account):
                Now = write_task_time(Account, name) if write_back else None
                if write_back:
                    print("        TIME- ----- 本次" + name + "完成时间")
                    print("        TIME- ----- ", Now)
                else:
                    # 不写回的任务（如纸人奖励）只打印时间，不打印"本次…完成时间"
                    print("        TIME- ----- ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                print("        TASK- ----- " + name + "任务完成")
            else:
                print("        TASK- ----- " + name + "任务执行过程中出现错误 中断任务")

    _task_line(name + "任务结束")


# ---- 双账号协作任务的固定流程 ----


def write_task_time_pair(Accounts, Times_name):
    """把同一时间写回多个账号（一次读、全部写、一次存）

    :param Accounts:   账号容器，支持 Accounts[0] / Accounts[1] 索引
                       （list 或 dict 均可，与 Task_Liao_30 的参数形式保持一致）
    :param Times_name: 任务键
    :return:           写入的时间字符串
    """
    config = read_config(paths.LAST_TIMES)
    Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for i in range(len(Accounts)):
        config[Accounts[i]][Times_name] = Now
    write_config(paths.LAST_TIMES, config)
    return Now


def run_shared_task(name, pair, work, window=None):
    """双账号协作任务的固定流程：两账号一起判定，任一未完成则整体执行一次

    与 run_accounts_task 的区别：
    - 判定是「或」：任一账号未完成就执行
    - 业务只执行一次（需要两个窗口同时操作）
    - 成功时给主副账号都写回时间

    :param name:   任务名（Last_times.yml 的任务键）
    :param pair:   取主副账号的回调 () -> [主账号, 副账号]（通常来自 Setting.yml）
    :param work:   业务执行函数 (Accounts) -> 真值表示成功
    :param window: 时间窗 (begin, end)，None 表示不限
    """
    _task_line("开始" + name + "任务")

    now = datetime.now()
    if window is not None:
        if not (window[0] <= now.time() <= window[1]):
            print("TASK- ----- 时间不在" + _fmt_window(window) + "之间 跳过")
            _task_line(name + "任务结束")
            return
        print("TASK- ----- 当前时间在" + _fmt_window(window) + "之间 可以执行" + name + "任务")

    # 用 Last_times.yml 的账号判断「该不该跑」
    Accounts = read_accounts()
    Flag = {}
    for i in range(2):
        check_stop()
        print("        TIME- ----- 读取上次账号", Accounts[i], "完成" + name + "任务时间")
        last_time = check_lasttime(Accounts[i], name)
        Flag[i] = now.date() == last_time.date()

    if not (Flag[0] and Flag[1]):
        # 用 Setting.yml 的主副账号决定「谁跟谁配对跑」
        Pair = pair()
        print("        TASK- ----- 开始执行" + name + "任务")
        if work(Pair):
            Now = write_task_time_pair(Pair, name)
            print("        TIME- ----- 本次" + name + "完成时间")
            print("        TIME- ----- ", Now)
            print("        TASK- ----- " + name + "任务完成")
        else:
            print("        TASK- ----- " + name + "任务执行过程中出现错误 中断任务")
    else:
        for i in range(2):
            print("        SKIP- ----- 今日账号", Accounts[i], "已完成" + name + "任务 跳过")

    _task_line(name + "任务结束")


def Itface_Quit(Hwnd):
    """
    检测是否有退出界面 有则esc解除
    :param Hwnd:    窗口句柄
    :return: None
    """
    check_stop()
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    _sleep_with_stop(0.5)
    # 注：此处退出界面条件可以极为苛刻 一般识别取值为0.006
    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/courtyard/退出游戏.png", 0.01, 0)
    if Range:
        print("        INFO-", Matchs, "检测到退出界面")
        Find_Click_windows(Hwnd, "./pic/courtyard/取消退出.png", 0.03, "取消退出", "取消退出失败")
        return 1
    else:
        print("        INFO-", Matchs, "未检测到退出界面")
        return 0


def Itface_Host(Hwnd):
    """
    检测是否处在主界面
    :param Hwnd:    窗口句柄
    :return: 成功 1 失败 0
    """

    def Host_check(Hwnd, Wait):
        for i in range(Wait):
            check_stop()
            ctypes.windll.user32.SetForegroundWindow(Hwnd)
            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/courtyard/主界面.png", 0.05, 0)
            if Range:
                print("        INFO-", Matchs, "检测到进入庭院")
                return 1
            else:
                print("        INFO-", Matchs, "未检测到庭院界面")
                # 一键返回
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/一键返回庭院.png", 0.05, 0)
                Sleep_print(1)
                if Range:
                    Click(Hwnd, Range, 1)
                    print("        INFO-", Matchs, "一键返回庭院")
                    Sleep_print(2)
                    Check = Host_check(Hwnd, 1)
                    if Check:
                        return 1
                else:
                    print("        INFO-", Matchs, "未发现一键返回庭院图标")
                Sleep_print(1)
        return 0

    current_state = "庭院界面"
    Wait = 3
    for step in range(30):
        check_stop()
        match current_state:
            case "庭院界面":
                Check = Host_check(Hwnd, Wait)
                if Check:
                    return 1
                else:
                    current_state = "检测协作"
            case "检测协作":
                # 检测协作
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/拒绝协作.png", 0.01, 0)
                Sleep_print(1)
                if Range:
                    Click(Hwnd, Range, 1)
                    print("        INFO-", Matchs, "关闭协作")
                    Check = Host_check(Hwnd, 1)
                    if Check:
                        return 1
                    else:
                        current_state = "庭院界面"
                        Wait = 1
                else:
                    print("        INFO-", Matchs, "未发现协作")
                current_state = "检测弹窗"
            case "检测弹窗":
                # 检测弹窗
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/关闭.png", 0.01 + 0.01 * step, 0)
                Sleep_print(1)
                if Range:
                    Click(Hwnd, Range, 1)
                    print("        INFO-", Matchs, "关闭弹窗")
                    Check = Host_check(Hwnd, 1)
                    if Check:
                        return 1
                    else:
                        current_state = "庭院界面"
                        Wait = 1
                else:
                    print("        INFO-", Matchs, "未发现弹窗")
                current_state = "检测退出标志1"

            case "检测退出标志1":
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/退出标志1.png", 0.05, 0)
                Sleep_print(1)
                if Range:
                    Click(Hwnd, Range, 1)
                    print("        INFO-", Matchs, "点击退出标志1")
                    Check = Host_check(Hwnd, 1)
                    if Check:
                        return 1
                    else:
                        current_state = "庭院界面"
                        Wait = 1
                else:
                    print("        INFO-", Matchs, "未发现退出标志1")
                current_state = "检测退出标志2"

            case "检测退出标志2":
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/退出标志2.png", 0.05, 0)
                Sleep_print(1)
                if Range:
                    Click(Hwnd, Range, 1)
                    print("        INFO-", Matchs, "点击退出标志2")
                    Check = Host_check(Hwnd, 1)
                    if Check:
                        return 1
                    else:
                        current_state = "庭院界面"
                        Wait = 1
                else:
                    print("        INFO-", Matchs, "未发现退出标志2")
                current_state = "Esc退出"

            case "Esc退出":
                for i in range(3):
                    # 若Esc未触发退出界面 则再尝试
                    if not Esc_print(Hwnd):
                        Sleep_print(1)
                        Check = Host_check(Hwnd, 1)
                        if Check:
                            return 1
                    else:
                        current_state = "庭院界面"
                        break
                current_state = "庭院界面"

    print("        STEP- vvvvv 状态机轮次耗尽")
    return 0


def Itface_scroll(Hwnd):
    """
    位于庭院时 检测并确保卷轴打开
    @param Hwnd:    窗口句柄
    @return:        1正常0异常
    """
    check_stop()
    # 检测是否位于庭院主界面
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    Itface_Host(Hwnd)

    # 检测底部卷轴是否展开
    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/courtyard/式神录.png", 0.05, 0)
    if not Range:
        print("        INFO-", Matchs, "检测到卷轴尚未打开 点击打开卷轴")
        # 坐标法点击展开卷轴
        Range = ((1780, 970), (1910, 1120))
        Click(Hwnd, Range, 2)

        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/courtyard/式神录.png", 0.05, 0)
        if Range:
            print("        INFO-", Matchs, "检测到卷轴已经打开")
        else:
            print("        INFO-", Matchs, "打开卷轴失败")
            return 0
    else:
        print("        INFO-", Matchs, "检测到卷轴已经打开")
        return 1


def Itface_guild(Hwnd):
    """
    位于庭院时 进入阴阳寮界面
    @param Hwnd:    窗口句柄
    @return:        1正常0异常
    """
    check_stop()
    # 确保卷轴打开
    Itface_scroll(Hwnd)

    # 进入阴阳寮
    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/阴阳寮.png", 0.05, 0)
    if Range:
        Click(Hwnd, Range, 1)
        print("        INFO-", Matchs, "进入阴阳寮")
        _sleep_with_stop(1)
        return 1
    else:
        print("        INFO-", Matchs, "进入阴阳寮失败")
        return 0


def Itface_daily(Hwnd):
    """
    循环检测多种外显的日常入口
    """
    Itface_Host(Hwnd)
    for i in range(1):
        if Find_Click_windows(Hwnd, "./pic/courtyard/逢魔入口.png", 0.05, "进入逢魔入口", "未检测到逢魔入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/courtyard/斗技入口.png", 0.05, "进入斗技入口", "未检测到斗技入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/hunt/阴界之门入口.png", 0.05, "进入阴界之门入口", "未检测到阴界之门入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/courtyard/道馆入口.png", 0.05, "进入道馆入口", "未检测到道馆入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/courtyard/百鬼弈入口.png", 0.05, "进入百鬼弈入口", "未检测到百鬼弈入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/courtyard/狭间暗域入口.png", 0.05, "进入狭间暗域入口", "未检测到狭间暗域入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/courtyard/麒麟入口.png", 0.05, "进入麒麟入口", "未检测到麒麟入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/courtyard/宴会入口.png", 0.05, "进入宴会入口", "未检测到宴会入口"):
            break


def Itface_explore(Hwnd):
    """
    位于庭院时 进入探索界面
    param Hwnd:    窗口句柄
    """
    # 检测是否位于庭院主界面
    Itface_scroll(Hwnd)
    current_state = "庭院界面"
    for step in range(30):
        check_stop()
        Sleep_print(1)
        match current_state:
            case "庭院界面":
                Find = Find_Click_windows(Hwnd, "./pic/courtyard/阴阳术.png", 0.05, "点击阴阳术图标", "未检测到阴阳术图标")
                if Find:
                    print("        STEP- vvvvv 跳转阴阳术界面")
                    current_state = "阴阳术界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "阴阳术界面":
                Find = Find_Click_windows(Hwnd, "./pic/courtyard/御神.png", 0.05, "点击御神按钮", "未检测到御神按钮")
                if Find:
                    print("        STEP- vvvvv 跳转御神界面")
                    current_state = "御神界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "御神界面":
                Find = Find_Click_windows(Hwnd, "./pic/courtyard/前往六道.png", 0.05, "点击前往六道按钮", "未检测到前往六道按钮")
                if Find:
                    print("        STEP- vvvvv 跳转六道界面")
                    current_state = "六道界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "六道界面":
                print("        INFO- -----点击退出区域")
                Sleep_print(1)
                Range = [(20, 105), (91, 175)]
                Click(Hwnd, Range, 2)
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/digui/地鬼图标.png", 0.05, 0)
                if Range:
                    print("        INFO-", Matchs, "检测到地鬼入口 已进入探索界面")
                    return 1
                else:
                    print("        INFO-", Matchs, "未检测到地鬼入口 似乎未进入探索界面")
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "异常退出":
                Itface_Host(Hwnd)
                return 0


def Team_Preset(Hwnd, Preset_Group, Preset_name):
    """
    选择预设编组
    :param Hwnd:            窗口句柄
    :param Preset_name:     预设名称
    """
    Itface_scroll(Hwnd)
    current_state = "庭院卷轴界面"
    for step in range(30):
        check_stop()
        Sleep_print(1)
        match current_state:
            case "庭院卷轴界面":
                Find = Find_Click_windows(Hwnd, "./pic/courtyard/式神录.png", 0.05, "点击式神录", "未检测到式神录")
                Sleep_print(1)
                if Find:
                    print("        STEP- vvvvv 跳转式神录界面")
                    current_state = "式神录界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "式神录界面":
                Find = Find_Click_windows(Hwnd, "./pic/team/预设选项.png", 0.05, "点击预设选项", "未检测到预设选项")
                if Find:
                    print("        STEP- vvvvv 跳转队伍预设")
                    current_state = "队伍预设"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "队伍预设":
                Range, Matchs = Find_in_windows_Matchs(Hwnd, f"./pic/team/{Preset_Group}.png", 0.01, 0)
                if Range:
                    Find = Find_Click_windows(Hwnd, f"./pic/team/{Preset_Group}.png", 0.01, f"选择预设编组 {Preset_Group}", f"未检测到预设编组 {Preset_Group}")
                    if Find:
                        print("        STEP- vvvvv 跳转组内预设")
                        current_state = "组内预设"
                    else:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"
                else:
                    print("        INFO-", Matchs, "似乎已经在预设组", Preset_Group, "中")
                    print("        STEP- vvvvv 跳转组内预设")
                    current_state = "组内预设"
            case "组内预设":
                Range, Matchs = Find_in_windows_Matchs(Hwnd, f"./pic/team/{Preset_name}.png", 0.01, 0)
                if Range:
                    Find = Find_Click_windows(Hwnd, f"./pic/team/{Preset_name}.png", 0.01, f"选择预设队伍 {Preset_name}", f"未检测到预设队伍 {Preset_name}")
                    if Find:
                        print("        STEP- vvvvv 跳转应用预设")
                        current_state = "应用预设"
                    else:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"
                else:
                    print("        INFO-", Matchs, "似乎已经选中预设队伍", Preset_name)
                    print("        STEP- vvvvv 跳转应用预设")
                    current_state = "应用预设"
            case "应用预设":
                Find = Find_Click_windows(Hwnd, "./pic/team/应用御魂预设.png", 0.03, "点击应用御魂预设", "未检测到应用御魂预设按钮")
                if Find:
                    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/确定.png", 0.05, 0)
                    if Range:
                        Click(Hwnd, Range, 0.5)
                        print("        INFO-", Matchs, "点击确认")
                    else:
                        print("        INFO-", Matchs, "未发现二次确认按钮 似乎已经是此配置")
                    if Find:
                        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/确定.png", 0.05, 0)
                        if Range:
                            Click(Hwnd, Range, 0.5)
                            print("        INFO-", Matchs, "点击确认更换御灵")
                        else:
                            print("        INFO-", Matchs, "未发现二次确认按钮 似乎已经是此配置")
                    print("        STEP- vvvvv 跳转结束界面")
                    current_state = "结束"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "结束":
                Esc_print(Hwnd)
                print("        STEP- vvvvv 御魂预设", f"{Preset_Group}", f"{Preset_name}" " 装配完成")
                return 1
            case "异常退出":
                Itface_Host(Hwnd)
                return 0
