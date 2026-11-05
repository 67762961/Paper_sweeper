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


def Sleep_quiet(Wait_time):
    """可中断的静默等待

    扫描循环里每点一次都要等面板刷新，用 Sleep_print 会把真正的信息淹没掉，
    所以这里只等不打日志。
    """
    _sleep_with_stop(Wait_time)


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


# ---- 系统睡眠（GUI「完整运行完成后让电脑睡眠」）----
# 只用 ctypes 调 powrprof，不依赖第三方包，也不用 rundll32：
# `rundll32 powrprof.dll,SetSuspendState 0,1,0` 在开启了休眠的机器上
# 会变成「休眠」而不是「睡眠」，而且返回值不可检测。

_SE_SHUTDOWN_NAME = "SeShutdownPrivilege"
_TOKEN_ADJUST_PRIVILEGES = 0x0020
_TOKEN_QUERY = 0x0008
_ERROR_NOT_ALL_ASSIGNED = 1300


class _LUID(ctypes.Structure):
    _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]


class _LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", _LUID), ("Attributes", ctypes.c_ulong)]


class _TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [
        ("PrivilegeCount", ctypes.c_ulong),
        ("Privileges", _LUID_AND_ATTRIBUTES * 1),
    ]


def _enable_shutdown_privilege():
    """启用 SeShutdownPrivilege（普通用户默认未启用，不启用 SetSuspendState 会静默失败）

    :return: 成功返回 True；拿不到权限返回 False（调用方据此给出明确错误）
    """
    try:
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32

        # 必须显式声明签名：GetCurrentProcess 的默认返回类型是 c_int，
        # 伪句柄 -1 会被截断成 0x00000000FFFFFFFF，传给 OpenProcessToken
        # 就变成无效句柄（GetLastError 返回 6）
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        advapi32.OpenProcessToken.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        advapi32.OpenProcessToken.restype = ctypes.c_int

        token = ctypes.c_void_p()
        if not advapi32.OpenProcessToken(
            kernel32.GetCurrentProcess(),
            _TOKEN_ADJUST_PRIVILEGES | _TOKEN_QUERY,
            ctypes.byref(token),
        ):
            print("        WAIT- ----- 打开进程令牌失败:", kernel32.GetLastError())
            return False

        try:
            luid = _LUID()
            if not advapi32.LookupPrivilegeValueW(None, _SE_SHUTDOWN_NAME, ctypes.byref(luid)):
                print("        WAIT- ----- 查询关机特权失败:", kernel32.GetLastError())
                return False

            privileges = _TOKEN_PRIVILEGES()
            privileges.PrivilegeCount = 1
            privileges.Privileges[0].Luid = luid
            privileges.Privileges[0].Attributes = 0x0002  # SE_PRIVILEGE_ENABLED

            if not advapi32.AdjustTokenPrivileges(
                token, False, ctypes.byref(privileges), 0, None, None
            ):
                print("        WAIT- ----- 启用关机特权失败:", kernel32.GetLastError())
                return False

            # AdjustTokenPrivileges 成功但没拿到权限时只置 ERROR_NOT_ALL_ASSIGNED，
            # 必须单独检查，否则会误以为成功
            error = kernel32.GetLastError()
            if error == _ERROR_NOT_ALL_ASSIGNED:
                print("        WAIT- ----- 关机特权未被授予 当前账户可能无权睡眠")
                return False
            return True
        finally:
            kernel32.CloseHandle(ctypes.c_void_p(token.value))
    except Exception as error:
        print("        WAIT- ----- 启用关机特权时异常:", error)
        return False


def sleep_system():
    """让电脑进入睡眠（S3）。返回是否调用成功

    False 的常见原因：当前账户没有关机特权、或被组策略禁用。
    调用方应据此给出可操作的提示，而不是静默什么都不发生。
    """
    if not _enable_shutdown_privilege():
        return False

    try:
        # 参数依次为：Hibernate=False（睡眠而非休眠）、ForceCritical=False、
        # DisableWakeEvent=False
        result = ctypes.windll.powrprof.SetSuspendState(False, False, False)
    except Exception as error:
        print("        WAIT- ----- 调用 SetSuspendState 异常:", error)
        return False

    if not result:
        print("        WAIT- ----- 睡眠请求被拒绝:", ctypes.windll.kernel32.GetLastError())
        return False
    print("        INFO- ----- 已请求系统进入睡眠")
    return True


# ExitWindowsEx 标志位：0x0 = 注销，0x8 = 关机（后者才真正切断电源）
_EWX_LOGOFF = 0x00000000
_EWX_POWEROFF = 0x00000008

POWER_ACTIONS = ("logoff", "sleep", "shutdown")


def power_action(action):
    """执行电源动作：logoff / sleep / shutdown。返回是否调用成功

    **注销与关机会结束本进程**，调用后不要指望还能执行任何代码。
    睡眠走 SetSuspendState，其余走 ExitWindowsEx —— 两者都需要
    SeShutdownPrivilege，统一在这里启用。

    不加 EWX_FORCE / EWX_FORCEIFHUNG：强制标志会杀掉所有未保存的工作
    （包括用户开着的文档）。此时模拟器已关，正常不会有阻拦者；
    万一有程序阻拦，系统会弹确认框，让用户自己决定。

    注销与睡眠的关键差别：注销**不挂起内核**，Session 0 的服务
    （如远程控制软件）继续运行，因此注销后仍可远程接管。
    """
    if action not in POWER_ACTIONS:
        print("        WAIT- ----- 未知的电源动作:", action)
        return False

    if not _enable_shutdown_privilege():
        return False

    try:
        if action == "sleep":
            # 参数依次为：Hibernate=False（睡眠而非休眠）、ForceCritical=False、
            # DisableWakeEvent=False
            result = ctypes.windll.powrprof.SetSuspendState(False, False, False)
        else:
            flag = _EWX_LOGOFF if action == "logoff" else _EWX_POWEROFF
            result = ctypes.windll.user32.ExitWindowsEx(flag, 0)
    except Exception as error:
        print("        WAIT- ----- 执行电源动作异常:", action, error)
        return False

    if not result:
        print("        WAIT- ----- 电源动作被拒绝:", action, ctypes.windll.kernel32.GetLastError())
        return False
    print("        INFO- ----- 已请求电源动作:", action)
    return True


def Img_read_ch(file_path):
    """读取包含中文路径的图片"""
    # 使用numpy从二进制数据读取
    with open(file_path, "rb") as f:
        img_data = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
    return img


# ---- 调试截图（默认全关，热路径第一行 early return）----
_SHOT_MODE = "off"          # off / miss / all
_SHOT_DIR = None            # logs/<月>/<日>/shots_<stamp>
_SHOT_SEQ = 0               # 产出序号，等于「第几次匹配判定」
_SHOT_SAVED = 0
_SHOT_BYTES = 0             # 累计写盘字节，供 end_shots() 打汇总
_SHOT_FAILS = 0             # 连续写盘失败计数，达 3 熔断
_SHOT_INDEX = None          # index.tsv 文件句柄
_SHOT_LIMIT = 8000          # 单次运行张数上限（轮询场景会顶到数千）


def Img_write_ch(file_path, Img, quality=80):
    """中文路径写图：cv2.imwrite 遇中文路径静默返回 False，必须走 imencode + tofile"""
    try:
        Ok, Buffer = cv2.imencode(".jpg", Img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not Ok:
            return False
        Buffer.tofile(file_path)
        return True
    except Exception as error:
        print("        WAIT- ----- 截图写盘失败:", file_path, error)
        return False


def _read_shot_pref():
    """读 state/gui.json 的 debug_shots。直接用 json 读，不 import ui.prefs——
    Lib 是底层，不能反向依赖界面层（ui/__init__.py 写明了单向依赖）"""
    try:
        with open(paths.PREFS, "r", encoding="utf-8") as Handle:
            return json.load(Handle).get("debug_shots")
    except Exception:
        return None


_SHOT_BAD_CHARS = re.compile(r'[\\/:*?"<>|]')


def _shot_name(Origin, Model_path, Score, Hit):
    """000123_miss_确定_0.312.jpg。模板名走中文，必须先把 Windows 非法字符换掉"""
    name = os.path.splitext(os.path.basename(Model_path or ""))[0] or Origin
    name = _SHOT_BAD_CHARS.sub("_", name)[:40]
    try:
        score = "{0:.3f}".format(float(Score))
    except (TypeError, ValueError):
        score = str(Score)
    return f"{_SHOT_SEQ:06d}_{'hit' if Hit else 'miss'}_{name}_{score}.jpg"


def begin_shots(log_file_path, mode=None):
    """在 _log_stream 里调用：按当前档位准备截图目录与 index.tsv

    优先级：显式 mode 参数 > state/gui.json 的 debug_shots > off。
    设置弹窗写的就是 gui.json，所以界面上显示什么，这里就执行什么。
    不再读 PAPER_SHOTS 环境变量——它曾让「设置里关着、实际却在存图」，
    用户无从察觉那个变量还在进程环境里。
    """
    global _SHOT_MODE, _SHOT_DIR, _SHOT_SEQ, _SHOT_SAVED, _SHOT_BYTES, _SHOT_FAILS, _SHOT_INDEX

    _SHOT_MODE = (mode or _read_shot_pref() or "off").lower()
    _SHOT_SEQ = _SHOT_SAVED = _SHOT_BYTES = _SHOT_FAILS = 0
    if _SHOT_MODE not in ("miss", "all"):
        _SHOT_MODE = "off"
        return
    # 目录名沿用 log 的 timestamp，保证一一对应
    # log 名形如 console_output_2026-11-04_22-15-03.log，末 19 位就是 %Y-%m-%d_%H-%M-%S
    stem = os.path.splitext(os.path.basename(log_file_path))[0]
    stamp = stem[-19:] if len(stem) >= 19 else stem
    _SHOT_DIR = os.path.join(os.path.dirname(log_file_path), "shots_" + stamp)
    try:
        os.makedirs(_SHOT_DIR, exist_ok=True)
        _SHOT_INDEX = open(os.path.join(_SHOT_DIR, "index.tsv"), "w", encoding="utf-8")
        _SHOT_INDEX.write("序号\t时间\t结果\t来源\t模板\t得分\t阈值\t尺寸\t裁剪偏移\t文件\n")
    except OSError as error:
        print("        WAIT- ----- 无法创建截图目录，已关闭截图:", error)
        _SHOT_MODE = "off"


def end_shots():
    """收尾：打一行汇总并关 index.tsv（G3：控制台只出现这一行截图信息）"""
    global _SHOT_MODE, _SHOT_INDEX
    if _SHOT_INDEX is not None:
        try:
            _SHOT_INDEX.close()
        except Exception:
            pass
        _SHOT_INDEX = None
    if _SHOT_MODE != "off":
        # 汇总一行：张数 + 体积 + 路径。体积靠累加每张写盘后的 os.path.getsize，
        # 不额外扫目录（扫几千个文件要几百毫秒，收尾时没必要再付一次）
        print(f"        SHOT- ----- 本次共保存 {_SHOT_SAVED} 张 / 约 {_SHOT_BYTES / 1048576:.0f} MB"
              f" -> {_SHOT_DIR}")
    _SHOT_MODE = "off"


def _record_shot(Img, Origin, Model_path, Score, Threshold, Hit,
                 Left_up=None, Right_down=None, search_range=None, Offset=None):
    """匹配后调用的唯一截图出口。任何异常都不允许影响匹配结果。

    Img          : 要存档的原始帧（不要传涂黑过/裁剪过的内部工作图）
    Origin       : match_model / models_in_image / models_all / models_rows
    Left_up/Right_down : 要画的框；为 None 时只存原图不画框
    Offset       : 裁剪块时的 (X0, Y0)，写进 index.tsv 供对坐标
    """
    global _SHOT_MODE, _SHOT_SEQ, _SHOT_SAVED, _SHOT_BYTES, _SHOT_FAILS

    if _SHOT_MODE == "off":
        return
    if _SHOT_MODE == "miss" and Hit:
        return
    if _SHOT_SAVED >= _SHOT_LIMIT:
        return
    try:
        # ① 画框：与 Flag_show 的调试窗口完全一致
        if Left_up is None:
            Img_display = Img
        else:
            Img_display = _draw_boxes(Img, Left_up, Right_down, search_range,
                                      Origin in ("match_model", "models_all"))

        # ② 命名 + 写盘
        _SHOT_SEQ += 1
        Name = _shot_name(Origin, Model_path, Score, Hit)
        Path = os.path.join(_SHOT_DIR, Name)
        if not Img_write_ch(Path, Img_display):
            _SHOT_FAILS += 1
            if _SHOT_FAILS >= 3:
                print("        WAIT- ----- 截图连续写盘失败，本次运行已停止保存截图")
                _SHOT_MODE = "off"
            return
        _SHOT_SAVED += 1
        try:
            _SHOT_BYTES += os.path.getsize(Path)      # 供 end_shots() 打体积汇总
        except OSError:
            pass
        _SHOT_FAILS = 0                               # 成功一次就清零，熔断只针对「连续」失败

        # ③ 只写 index.tsv（图片明细的唯一权威清单）
        #    不给每张图 print —— GUI 控制台不要出现截图明细，
        #    「哪句 log 对应哪张图」靠 index.tsv 的序号 + 时间戳事后对齐
        if _SHOT_INDEX is not None:
            Height, Width = Img.shape[0:2]
            _SHOT_INDEX.write("\t".join((
                str(_SHOT_SEQ),
                datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "hit" if Hit else "miss",
                Origin,
                os.path.splitext(os.path.basename(Model_path or ""))[0] or "-",
                str(Score),
                str(Threshold),
                f"{Width}x{Height}",
                f"{Offset[0]},{Offset[1]}" if Offset else "-",
                Name,
            )) + "\n")
            _SHOT_INDEX.flush()
    except TaskStopped:
        raise                      # 中断必须一路抛到 main
    except Exception as error:
        _SHOT_FAILS += 1
        print("        WAIT- ----- 截图保存异常:", error)
        if _SHOT_FAILS >= 3:
            _SHOT_MODE = "off"


def _draw_boxes(Img, Left_up, Right_down, search_range=None, is_window_match=False):
    """
    在图像副本上画出匹配框（调试显示与截图保存共用）
    :param Img: 原始图像（三通道 BGR）
    :param Left_up: 匹配区域左上角
    :param Right_down: 匹配区域右下角
    :param search_range: 搜索区域，格式为[Left_up, Right_down]，指定时用蓝框标定
    :param is_window_match: 是否为窗口匹配，为真时用绿框标定点击区域
    :return: 画好框的图像副本（不修改传入的原图）
    """
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

    return Img_display


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
        # 画框逻辑与截图保存共用
        Img_display = _draw_boxes(Img, Left_up, Right_down, search_range, is_window_match)

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

    # 调试截图：每次匹配判定留一张图（默认档位下 _record_shot 首行即返回）
    _record_shot(Img, "match_model", Img_model_path, return2, Threshold, return1 is not None,
                 Left_up, Right_down, search_range, (x1, y1) if search_range is not None else None)

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


# ---- 一帧多用：截一次图，在同一帧上做多次识别 ----
# 寄养列表扫描里原来的写法是「每识别一次就重新截一次窗口」，
# 一屏要截 5 次（定位列表 1 次 + 两次 Find_Click_windows 内部各 2 次），
# 而模板匹配本身只要几十毫秒，截图才是大头。下面三个原语把它拆开。

_TEMPLATE_CACHE = {}  # 路径 -> (mtime_ns, size, 模板图像)


def clear_template_cache():
    """清空模板缓存（测试用；正常运行时不需要手动调用）"""
    _TEMPLATE_CACHE.clear()


def _read_template_cached(Img_model_path):
    """读取模板图并缓存，避免同一张模板在循环里被反复解码

    缓存键带 mtime 与文件大小：用户替换了模板图会立刻失效，
    不会出现「改了图但程序还在用旧图」的怪事。
    """
    try:
        stat = os.stat(Img_model_path)
        stamp = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        # 文件不存在时不做缓存，交给 Img_read_ch 统一报错
        stamp = None

    if stamp is not None:
        cached = _TEMPLATE_CACHE.get(Img_model_path)
        if cached is not None and cached[0] == stamp:
            return cached[1]

    Img_model = Img_read_ch(Img_model_path)
    if Img_model is None:
        raise ValueError(f"无法找到文件: {Img_model_path}")

    if stamp is not None:
        _TEMPLATE_CACHE[Img_model_path] = (stamp, Img_model)
    return Img_model


def Screenshot_window(Hwnd):
    """截取窗口当前画面，返回 cv2 BGR 图像

    与 Find_in_windows_Matchs 的区别：这里只截图，不做匹配、不点击。
    调用方可以拿同一帧去做多次识别，避免「识别几次就截几次」。
    """
    check_stop()
    window_rect = win32gui.GetWindowRect(Hwnd)
    left, top, right, bottom = window_rect
    Screenshot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
    return cv2.cvtColor(np.array(Screenshot), cv2.COLOR_RGB2BGR)


def Match_models_in_image(Img, models, Threshold):
    """在一张已经截好的图上依次试多个模板

    :param Img:       cv2 BGR 图像（调用方自己截，可用 Screenshot_window）
    :param models:    [(名字, 模板路径), ...]
    :param Threshold: 匹配阈值，语义与 Match_model 一致
                      （TM_SQDIFF_NORMED，得分越小越像，超过阈值判失败）
    :return:          [(名字, [左上, 右下], 得分字符串), ...]，
                      只含命中项，按得分升序（最像的在前）
    """
    check_stop()
    Img = np.uint8(Img)

    Results = []
    Best = None          # (score, name, box)：未命中时也要知道「最像的那张差多少」
    for name, Model_path in models:
        Img_model = _read_template_cached(Model_path)
        Model_height, Model_width = Img_model.shape[0:2]

        # 模板比待匹配图还大时 matchTemplate 会直接抛错，这里当作未命中跳过
        if Model_height > Img.shape[0] or Model_width > Img.shape[1]:
            continue

        Result = cv2.matchTemplate(Img, np.uint8(Img_model), cv2.TM_SQDIFF_NORMED)
        min_val, _max_val, min_loc, _max_loc = cv2.minMaxLoc(Result)

        Left_up = (min_loc[0], min_loc[1])
        Right_down = (min_loc[0] + Model_width, min_loc[1] + Model_height)
        if Best is None or min_val < Best[0]:
            Best = (float(min_val), name, [Left_up, Right_down])

        if min_val > Threshold:
            continue

        Results.append((name, [Left_up, Right_down], f"{min_val:.3f}"))

    Results.sort(key=lambda item: float(item[2]))

    # 调试截图：一次调用留一张图。命中与否按「有没有至少一个命中」判定；
    # 未命中时也记下最像那张的分数，否则「为什么没认出来」无从判断
    if Results:
        _name, _box, _score = Results[0]
        _record_shot(Img, "models_in_image", _name, _score, Threshold, True,
                     _box[0], _box[1])
    elif Best is not None:
        _record_shot(Img, "models_in_image", Best[1], f"{Best[0]:.3f}", Threshold, False)
    else:
        _record_shot(Img, "models_in_image", "-", "-", Threshold, False)

    return Results


def Match_models_in_image_all(Img, Model_path, Threshold, max_matches=10):
    """在同一帧上找出**所有**匹配位置（蒙版法重复匹配）

    Match_models_in_image 对每张模板只返回最像的那一个位置，
    而寄养列表一屏有 4 行，同一档的卡可能同时出现好几个。
    这里在匹配成功后把该区域涂黑再找下一个，就能在同一帧上拿全。

    与 Find_multiple_in_windows_Matchs 的区别：那个每次循环都重新截一次窗口，
    这个只在一张已经截好的图上重复匹配，不额外截图。

    :param Img:         cv2 BGR 图像
    :param Model_path:  模板路径
    :param Threshold:   匹配阈值，语义与 Match_model 一致
    :param max_matches: 最多返回几个
    :return:            [[左上, 右下], ...]，按从上到下排序
    """
    check_stop()
    Img_work = np.uint8(Img).copy()

    Img_model = _read_template_cached(Model_path)
    Model_height, Model_width = Img_model.shape[0:2]
    if Model_height > Img_work.shape[0] or Model_width > Img_work.shape[1]:
        # 模板比帧还大属于配置错误，但这也是一次「判定为未命中」，照 G1 留一张图
        _record_shot(Img, "models_all", Model_path, "1.000", Threshold, False)
        return []

    Positions = []
    Last_score = None      # 循环结束那一轮的分数：未命中时它就是「最像的那次差多少」
    Hit_score = None       # 第一个命中的分数（最像的那个位置）
    for _ in range(max_matches):
        Result = cv2.matchTemplate(Img_work, np.uint8(Img_model), cv2.TM_SQDIFF_NORMED)
        min_val, _max_val, min_loc, _max_loc = cv2.minMaxLoc(Result)
        Last_score = float(min_val)
        if min_val > Threshold:
            break
        if Hit_score is None:
            Hit_score = float(min_val)

        Left_up = (min_loc[0], min_loc[1])
        Right_down = (min_loc[0] + Model_width, min_loc[1] + Model_height)
        Positions.append([Left_up, Right_down])

        # 涂黑已匹配区域，避免同一行被重复找到
        cv2.rectangle(Img_work, Left_up, Right_down, (0, 0, 0), -1)

    Positions.sort(key=lambda box: box[0][1])

    # 调试截图：传原始 Img，不能传涂黑过的 Img_work（那会看不出当时屏幕什么样）
    if Positions:
        _record_shot(Img, "models_all", Model_path, f"{Hit_score:.3f}", Threshold, True,
                     Positions[0][0], Positions[0][1])
    else:
        Last = "1.000" if Last_score is None else f"{Last_score:.3f}"
        _record_shot(Img, "models_all", Model_path, Last, Threshold, False)

    return Positions


def Match_models_rows(Img, Models, Threshold, max_matches=8, origin_offset=None):
    """在一帧上找多个不同模板，并按「行」裁决：一行只出一个类型

    与 Match_models_in_image_all 的区别是**行内竞争**。那个原语是
    每张模板各自独立搜索，涂黑只在同一张模板自己的循环里生效，
    所以同一张卡可能被两张模板各报一次（四张结界卡共用金色托盘与
    橙色星点，一张斗鱼卡在太鼓模板上换个滑窗位置也可能过阈值）。
    同一行被报两次的后果是：点两次、记两次账，斗鱼的收益记到太鼓名下，
    而太鼓封顶只有 76，于是又误触发「已达封顶」。

    这里的做法是先把所有命中按纵向聚成行，再在行内比分数取最像的那一张。
    实测三张真实截图 8 行：真实类型分数 0.0095~0.0254，次优 0.0584~0.1144，
    余量 6~12 倍，比「先到先得」稳得多。

    :param Img:         cv2 BGR 图像
    :param Models:      [(名字, 模板路径), ...]
    :param Threshold:   行内胜出者的分数上限，超过则该行不算命中
    :param max_matches: 每张模板最多取几个峰
    :param origin_offset: 这张 Img 来自整屏的哪个位置 (x, y)，只用于调试截图
                        记下裁剪偏移；不传表示 Img 就是整屏
    :return:            [(名字, [左上, 右下], 得分字符串), ...]，按纵向排序
    """
    check_stop()
    Img_work = np.uint8(Img)
    Img_height, Img_width = Img_work.shape[0:2]

    # 1) 每张模板只跑一次 matchTemplate，得到全图分数图
    Maps = []
    for Name, Model_path in Models:
        Img_model = _read_template_cached(Model_path)
        Model_height, Model_width = Img_model.shape[0:2]
        if Model_height > Img_height or Model_width > Img_width:
            continue
        Maps.append({
            "name": Name,
            "map": cv2.matchTemplate(Img_work, np.uint8(Img_model), cv2.TM_SQDIFF_NORMED),
            "width": Model_width,
            "height": Model_height,
        })

    # 2) 各取若干峰（非极大抑制只压分数图，不重跑匹配）
    Peaks = []
    Best = None        # (score, name)：未命中时记下最像的那张差多少
    for Item in Maps:
        Work = Item["map"].copy()
        for _ in range(max_matches):
            min_val, _max_val, min_loc, _max_loc = cv2.minMaxLoc(Work)
            if Best is None or min_val < Best[0]:
                Best = (float(min_val), Item["name"])
            if min_val > Threshold:
                break
            Peaks.append({
                "name": Item["name"],
                "score": float(min_val),
                "x": min_loc[0],
                "y": min_loc[1],
                "width": Item["width"],
                "height": Item["height"],
            })
            # 压掉这一带，避免同一处反复取到
            Half_w = Item["width"] // 2
            Half_h = Item["height"] // 2
            cv2.rectangle(
                Work,
                (max(0, min_loc[0] - Half_w), max(0, min_loc[1] - Half_h)),
                (min(Work.shape[1], min_loc[0] + Half_w), min(Work.shape[0], min_loc[1] + Half_h)),
                1.0,
                -1,
            )

    if not Peaks:
        # 全部模板都没过阈值：这是一次判定为未命中的匹配，照 G1 留一张图。
        # 记最像那张的分数，否则「为什么没认出来」只能靠猜
        if Best is not None:
            _record_shot(Img, "models_rows", Best[1], f"{Best[0]:.3f}", Threshold, False,
                         Offset=origin_offset)
        else:
            _record_shot(Img, "models_rows", Models[0][1] if Models else None, "-",
                         Threshold, False, Offset=origin_offset)
        return []

    # 3) 按纵向中心聚成行
    Peaks.sort(key=lambda item: item["y"] + item["height"] / 2.0)
    Rows = []
    for Peak in Peaks:
        Center = Peak["y"] + Peak["height"] / 2.0
        for Row in Rows:
            if abs(Row["center"] - Center) <= max(Row["heights"]) / 2.0:
                Row["peaks"].append(Peak)
                Row["center"] = sum(p["y"] + p["height"] / 2.0 for p in Row["peaks"]) / len(Row["peaks"])
                Row["heights"].append(Peak["height"])
                break
        else:
            Rows.append({"center": Center, "peaks": [Peak], "heights": [Peak["height"]]})

    # 4) 行内比分数，取最像的那一张
    Results = []
    for Row in Rows:
        Winner = min(Row["peaks"], key=lambda item: item["score"])
        if Winner["score"] > Threshold:
            continue
        Results.append((
            Winner["name"],
            [[Winner["x"], Winner["y"]],
             [Winner["x"] + Winner["width"], Winner["y"] + Winner["height"]]],
            "{0:.3f}".format(Winner["score"]),
        ))

    Results.sort(key=lambda item: item[1][0][1])

    # 调试截图：一次调用可能有多个命中行，_draw_boxes 只认一个框，
    # 所以这里自己在副本上把所有框画完，再以 Left_up=None 交给 _record_shot。
    # Img_work 是原图别名，直接画会污染调用方的图，必须先 copy。
    if _SHOT_MODE != "off":
        Img_shot = np.uint8(Img).copy()
        for _name, _box, _score in Results:
            cv2.rectangle(Img_shot, _box[0], _box[1], (0, 0, 255), 2)
        _record_shot(Img_shot, "models_rows",
                     Results[0][0] if Results else (Models[0][0] if Models else None),
                     Results[0][2] if Results else "1.000",
                     Threshold, bool(Results), Left_up=None, Offset=origin_offset)

    return Results


def Image_fingerprint(Img, size=(32, 18)):
    """把图像压成一张小尺寸灰度指纹，用于判断「两帧是不是同一画面」

    缩小的作用是把压缩噪声与动画抖动平均掉，所以滚动到底之后
    相邻两帧的指纹几乎一模一样；而真的滚动了，内容整体位移，指纹差异很大。
    这替代了原来的 寄养列表末尾.png：那张图配 TM_SQDIFF_NORMED + 0.001
    等于要求逐像素相等，实拍图永远达不到，末尾判定形同虚设。

    注意：指纹本身是「缩略灰度」，比较时请用 Fingerprint_diff / Fingerprint_same，
    不要直接比字节串——同一画面带一点噪声时字节未必全等。

    :param Img:  cv2 BGR 图像
    :param size: 指纹尺寸 (宽, 高)，越小越不敏感
    :return:     指纹（np.uint8 二维数组，size[1] 行 size[0] 列）
    """
    check_stop()
    Gray = cv2.cvtColor(np.uint8(Img), cv2.COLOR_BGR2GRAY)
    return cv2.resize(Gray, size, interpolation=cv2.INTER_AREA)


def Fingerprint_diff(Fp_a, Fp_b):
    """两张指纹的平均灰度差（0~255，同一画面通常小于 2）"""
    a = np.asarray(Fp_a, dtype=np.int16)
    b = np.asarray(Fp_b, dtype=np.int16)
    if a.shape != b.shape:
        raise ValueError(f"指纹尺寸不一致: {a.shape} vs {b.shape}")
    return float(np.abs(a - b).mean())


def Fingerprint_same(Fp_a, Fp_b, Tolerance=3.0):
    """两张指纹是否算「同一画面」

    :param Tolerance: 平均灰度差上限。实测同一画面带噪声约 1~2，
                      真实滚动远超 10，取 3 能稳稳分开。
    """
    return Fingerprint_diff(Fp_a, Fp_b) <= Tolerance


# ---- 收益数字识别（寄养结界右侧面板的「勾玉 +NN」/「体力 +NN」）----
# 不用 OCR 库：这里的数字是固定字体、固定字号的灰黑字，笔画形状高度一致，
# 用「连通域切字 + 归一化画布 + 带位移容忍的像素距离」就足够，
# 而且能明确回答「认不出」（返回 None），不会像 OCR 那样猜一个错的。
#
# 实测（四张真实截图，1910x1121 / 1784x932 / 1632x854 / 1618x900）：
#   同一数字跨图距离 0.000~0.055，不同数字最近 5vs6 = 0.131、1vs4 = 0.148，
#   所以阈值取 0.10 —— 覆盖实测最差同类（0.055），离最近异类留 30% 缓冲。

JIEJIE_DIGIT_CANVAS = (28, 32)      # 归一化画布 (宽, 高)，按字高等比缩放后居中
JIEJIE_DIGIT_THRESHOLD = 0.10       # 像素差平方均值上限，超过判「认不出」
JIEJIE_DIGIT_LUM = 150              # 墨迹判据：亮度上限
JIEJIE_DIGIT_SAT = 60               # 墨迹判据：最大通道差上限（灰黑字饱和低）
JIEJIE_YIELD_BOX_X = 0.55           # 数字区粗定位：右半边起点（占窗口宽比例）
JIEJIE_YIELD_BOX_Y = 0.45           # 数字区粗定位：下半部起点（占窗口高比例）
JIEJIE_DIGIT_GAP_RATIO = 0.5        # 行内切段的最大字间距（占字高比例）

# 数字模板：pic/guild/收益数字0.png ~ 收益数字9.png，下标即数字本身。
# 这里刻意写成 10 个字面量而不是 f-string 拼接：tools/check_pics.py 会把
# f-string 目录整体豁免「死图」检查，写成字面量才能让这 10 张图被真正校验。
JIEJIE_DIGIT_PICS = {
    0: "./pic/guild/收益数字0.png",
    1: "./pic/guild/收益数字1.png",
    2: "./pic/guild/收益数字2.png",
    3: "./pic/guild/收益数字3.png",
    4: "./pic/guild/收益数字4.png",
    5: "./pic/guild/收益数字5.png",
    6: "./pic/guild/收益数字6.png",
    7: "./pic/guild/收益数字7.png",
    8: "./pic/guild/收益数字8.png",
    9: "./pic/guild/收益数字9.png",
}


def _digit_ink_mask(Img):
    """灰度文字的墨迹掩码：足够暗、且三通道差异小

    游戏里的数字是灰黑色，背景是米色面板（R≈200 G≈192 B≈182），
    按「亮度 < 150 且最大通道差 < 60」就能把文字与背景干净分开，
    不会把面板上的浅色纹理算进来。
    """
    Img = np.asarray(Img, dtype=np.int32)
    Blue, Green, Red = Img[:, :, 0], Img[:, :, 1], Img[:, :, 2]
    Lum = 0.299 * Red + 0.587 * Green + 0.114 * Blue
    Diff = Img.max(axis=2) - Img.min(axis=2)
    return (Lum < JIEJIE_DIGIT_LUM) & (Diff < JIEJIE_DIGIT_SAT)


def _digit_glyphs(Img, Origin_x, Origin_y):
    """在图像右下区域切出候选字形

    :return: [(x, y, w, h, mask), ...]，坐标是相对整张图的绝对坐标
    """
    Sub = Img[Origin_y:, Origin_x:]
    Mask = _digit_ink_mask(Sub)

    # cv2 的连通域比手写 DFS 快两个数量级，且返回的 stats 直接就是外接框
    Count, _Labels, Stats, _Centroids = cv2.connectedComponentsWithStats(
        Mask.astype(np.uint8), connectivity=8
    )

    Glyphs = []
    for index in range(1, Count):       # 0 是背景
        x, y, w, h, _area = Stats[index]
        # 尺寸过滤：数字高 22~25、宽 8~16（原生分辨率）
        if h < 14 or h > 44:
            continue
        if w < 3 or w > 32:
            continue
        # 宽高比过滤：把 `+` 号滤掉（它是 19x21，宽/高≈0.90；数字都 ≤0.68）
        if w > h * 0.78:
            continue
        Glyphs.append(
            (x + Origin_x, y + Origin_y, w, h, Mask[y:y + h, x:x + w].copy())
        )
    return Glyphs


def _digit_group_lines(Glyphs):
    """按垂直重叠把字形聚成行，行内按 x 排序

    :return: [[(x, y, w, h, mask), ...], ...]，按 y 从上到下
    """
    Lines = []
    for Glyph in sorted(Glyphs, key=lambda item: item[1]):
        Placed = False
        for Line in Lines:
            Line_y0 = Line[0][1]
            Line_y1 = Line[0][1] + Line[0][3]
            Glyph_y0 = Glyph[1]
            Glyph_y1 = Glyph[1] + Glyph[3]
            Overlap = min(Line_y1, Glyph_y1) - max(Line_y0, Glyph_y0)
            if Overlap > min(Line_y1 - Line_y0, Glyph_y1 - Glyph_y0) * 0.5:
                Line.append(Glyph)
                Placed = True
                break
        if not Placed:
            Lines.append([Glyph])
    return [sorted(Line, key=lambda item: item[0]) for Line in Lines]


def _digit_rightmost_run(Line):
    """行内按间距切段，取最右边那段

    数字是右对齐的，左边混进来的汉字碎片、`+` 号与数字之间有明显空隙；
    而数字与数字之间只隔 3~10 像素。按「字高的一半」作切分阈值正好分开。
    """
    if not Line:
        return []

    Heights = sorted(Glyph[3] for Glyph in Line)
    Median = Heights[len(Heights) // 2]
    Gap_max = max(6, int(round(Median * JIEJIE_DIGIT_GAP_RATIO)))

    Runs = []
    Current = [Line[0]]
    for Prev, Glyph in zip(Line, Line[1:]):
        Gap = Glyph[0] - (Prev[0] + Prev[2])
        if Gap <= Gap_max:
            Current.append(Glyph)
        else:
            Runs.append(Current)
            Current = [Glyph]
    Runs.append(Current)

    # 单字形段不算数字（可能是 `+` 剩下的碎片或标点）
    Runs = [Run for Run in Runs if len(Run) >= 2]
    return Runs[-1] if Runs else []


def _digit_canvas(Glyph):
    """把一个字形缩放居中到统一画布，返回 float32 的 0/1 数组

    按高度等比缩放（数字高度一致，宽度才携带信息：1 很窄、0 很宽），
    所以不能用「拉伸铺满」的方式归一化。
    """
    _x, _y, w, h, Mask = Glyph
    Canvas_w, Canvas_h = JIEJIE_DIGIT_CANVAS
    Scale = Canvas_h / h
    New_w = max(1, int(round(w * Scale)))
    Offset = (Canvas_w - New_w) // 2

    Canvas = np.zeros((Canvas_h, Canvas_w), dtype=np.float32)
    Source_y = np.clip(
        ((np.arange(Canvas_h) + 0.5) / Scale).astype(np.int32), 0, h - 1
    )
    Source_x = np.clip(
        ((np.arange(New_w) + 0.5) / Scale).astype(np.int32), 0, w - 1
    )
    Canvas[:, Offset:Offset + New_w] = Mask[np.ix_(Source_y, Source_x)].astype(np.float32)
    return Canvas


def _digit_distance(Canvas_a, Canvas_b):
    """两张画布的像素差平方均值，在 ±2 横移 / ±1 纵移内取最小值

    位移容忍是为了吸收「字形框起点差 1 像素」这种抖动——
    同一数字重切一次，外接框可能差一格，不放开位移会把它们判成两个数字。
    """
    Canvas_h, Canvas_w = Canvas_a.shape
    Best = float("inf")
    for dy in (-1, 0, 1):
        for dx in (-2, -1, 0, 1, 2):
            Shifted = np.zeros_like(Canvas_b)
            y0, y1 = max(0, dy), min(Canvas_h, Canvas_h + dy)
            x0, x1 = max(0, dx), min(Canvas_w, Canvas_w + dx)
            Shifted[y0:y1, x0:x1] = Canvas_b[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
            Diff = float(((Canvas_a - Shifted) ** 2).mean())
            if Diff < Best:
                Best = Diff
    return Best


def _digit_read_run(Run, Prototypes):
    """把一个数字段读成整数

    :param Run:        [(x, y, w, h, mask), ...]，同一段里的字形
    :param Prototypes: {数字: 画布}
    :return:           读到的整数；任何一个字认不出就返回 None（不猜）
    """
    Text = ""
    for Glyph in Run:
        Canvas = _digit_canvas(Glyph)
        Best_digit = -1
        Best_distance = float("inf")
        for digit, Prototype in Prototypes.items():
            distance = _digit_distance(Canvas, Prototype)
            if distance < Best_distance:
                Best_distance = distance
                Best_digit = digit
        if Best_distance > JIEJIE_DIGIT_THRESHOLD:
            return None
        Text += str(Best_digit)

    try:
        return int(Text)
    except ValueError:      # 理论上不会发生，防御一下
        return None


def jiejie_read_yield(Img, Box=None):
    """读寄养结界右侧面板的收益数字（勾玉 / 体力后面的那个数）

    面板上有两行数字：上面是「式神经验 +NNNNN」，下面是「勾玉/体力 +NN」。
    这里只读**下面那一行**，因为寄养优先级只看勾玉 / 体力。

    :param Img: cv2 BGR 图像（通常来自 Screenshot_window）
    :param Box: 数字区粗定位 (x, y, w, h)；None 表示按窗口右下区域自动取
    :return:    收益值；认不出返回 None（调用方必须把 None 当作「没有数据」）
    """
    check_stop()
    Img = np.asarray(Img)

    if Box is None:
        Height, Width = Img.shape[0:2]
        Origin_x = int(Width * JIEJIE_YIELD_BOX_X)
        Origin_y = int(Height * JIEJIE_YIELD_BOX_Y)
        Region = Img[Origin_y:, Origin_x:]
    else:
        x, y, w, h = Box
        Origin_x, Origin_y = x, y
        Region = Img[y:y + h, x:x + w]

    if Region.size == 0:
        return None

    Glyphs = _digit_glyphs(Region, 0, 0)
    Lines = _digit_group_lines(Glyphs)
    if len(Lines) < 2:
        return None

    # 只保留「字高接近最大字高」的行：真正的数字行字号统一，
    # 而界面上的小图标、标点会形成矮行，先剔掉再取最后一行。
    Heights = [sorted(g[3] for g in Line)[len(Line) // 2] for Line in Lines]
    Top = max(Heights)
    Digit_lines = [Line for Line, Med in zip(Lines, Heights) if Med >= Top * 0.85]
    if len(Digit_lines) < 2:
        return None

    # 最后一行就是收益行（上一行是「式神经验 +NNNNN」，字号相同但数值不是收益）
    Run = _digit_rightmost_run(Digit_lines[-1])
    if not Run:
        return None

    Prototypes = _digit_prototypes()
    return _digit_read_run(Run, Prototypes)


_DIGIT_PROTOTYPES = {}


def clear_digit_cache():
    """清空数字模板缓存（测试用）"""
    _DIGIT_PROTOTYPES.clear()


def _digit_prototypes():
    """载入并缓存 10 张数字原型（灰度 0~1）"""
    if _DIGIT_PROTOTYPES:
        return _DIGIT_PROTOTYPES

    for digit, path in JIEJIE_DIGIT_PICS.items():
        Img = _read_template_cached(path)
        if Img is None:
            raise ValueError(f"无法找到数字模板: {path}")
        Gray = cv2.cvtColor(Img, cv2.COLOR_BGR2GRAY)
        _DIGIT_PROTOTYPES[digit] = Gray.astype(np.float32) / 255.0
    return _DIGIT_PROTOTYPES



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


# ---- 结界养成配置（config/Setting.yml 的「结界养成」段）----
# 段名与 run_accounts_task 的任务键同名，便于日志对照；段内每个账号一组配置。
#
# **为什么放这里而不是 ui/**：任务层不能 import ui/（ui → main → 任务模块会成环），
# 根目录白名单也不允许新增顶层模块。枚举与归一化留在这里，界面层
# （ui/jiejie_settings.py）反向复用它，从而保证「弹窗能选出来的」与
# 「任务层能接受的」永远是同一套规则。

JIEJIE_SECTION = "结界养成"
JIEJIE_KEY_CARD = "优先结界卡"       # 太鼓 / 斗鱼
JIEJIE_KEY_PRIORITY = "寄养优先级"   # 4 项，越靠左越优先

JIEJIE_CARD_OPTIONS = ("太鼓", "斗鱼")
JIEJIE_PRIORITY_OPTIONS = ("六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼")
JIEJIE_PRIORITY_COUNT = 4

# 默认值 = 本次改动之前写死的行为，老配置缺段缺键时零迁移
JIEJIE_DEFAULT_CARD = "太鼓"
JIEJIE_DEFAULT_PRIORITY = ("六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼")

# 配置值就是模板文件名（pic/guild/ 下的同名图片），不另设显示名
JIEJIE_PRIORITY_PICS = {
    "六星太鼓": "./pic/guild/六星太鼓.png",
    "六星斗鱼": "./pic/guild/六星斗鱼.png",
    "五星太鼓": "./pic/guild/五星太鼓.png",
    "五星斗鱼": "./pic/guild/五星斗鱼.png",
}

# 结界卡池的列表页签（放置结界卡时按优先顺序点开）
JIEJIE_CARD_LIST_PICS = {
    "太鼓": "./pic/guild/太鼓列表.png",
    "斗鱼": "./pic/guild/斗鱼列表.png",
}

# 各档位的已知封顶收益（6 小时寄养，含 1.4 倍加成）
# 太鼓六星满时率 9 勾/时 → 76；斗鱼六星满时率 18 体/时 → 151。
# 扫到封顶值就说明本档不可能更好，可以提前结束这一档的剩余扫描。
#
# 键是「档位」（六星太鼓/五星斗鱼），不是「类型」（太鼓/斗鱼）：
# 同一类型里六星与五星的上限并不相同——六星斗鱼能到 151，五星斗鱼最高
# 只到 134；太鼓这边六星 67~76、五星 59~67。若按类型记，「五星斗鱼读到
# 134」永远够不到斗鱼的 151，这一档的剩余行会被白点一遍。
JIEJIE_YIELD_CAP = {
    "六星太鼓": 76,
    "五星太鼓": 67,
    "六星斗鱼": 151,
    "五星斗鱼": 134,
}


def jiejie_yield_cap(priority_name):
    """取某个档位的收益上限：``六星太鼓`` → 76

    :param priority_name: ``寄养优先级`` 的一项（六星太鼓 / 六星斗鱼 / 五星太鼓 / 五星斗鱼）
    :return:              上限值；无法识别时返回 None（调用方按「没有上限」处理）
    """
    return JIEJIE_YIELD_CAP.get(str(priority_name))


def jiejie_card_type(priority_name):
    """从档位名取出类型：``六星太鼓`` → ``太鼓``

    :param priority_name: ``寄养优先级`` 的一项（六星太鼓 / 六星斗鱼 / 五星太鼓 / 五星斗鱼）
    :return:              类型名；无法识别时返回空串（调用方按「没有封顶」处理）
    """
    for name in JIEJIE_CARD_OPTIONS:
        if name in str(priority_name):
            return name
    return ""


def normalize_jiejie_card(value, warnings=None):
    """把「优先结界卡」修成太鼓或斗鱼

    只有两项，没有「不放置」这个第三态：「今天不放卡」是「结界卡未耗尽」这条
    既有判据自己得出的结果，不需要用户配置。

    :param value:    配置里的原始值
    :param warnings: 可选列表，非法取值会追加一条回落原因
    :return:         ``太鼓`` 或 ``斗鱼``
    """
    if isinstance(value, str) and value in JIEJIE_CARD_OPTIONS:
        return value
    if value is not None and warnings is not None:
        warnings.append(
            f"「{JIEJIE_KEY_CARD}」取值 {value!r} 不受支持，已按 {JIEJIE_DEFAULT_CARD!r} 执行"
        )
    return JIEJIE_DEFAULT_CARD


def normalize_jiejie_priority(values, warnings=None):
    """把「寄养优先级」修成恰好 4 项、互不相同、都在枚举内

    规则：**先出现者保留**——后出现的重复项换成池中第一个还没被占用的值；
    非法值视同缺位，同样按 ``JIEJIE_PRIORITY_OPTIONS`` 的顺序补。
    输出永远是那 4 个卡名的一个排列。

    弹窗的「撞车自动改派」也走这个函数：第 N 级抢了第 M 级（M > N）的值时，
    第 M 级作为较后者被改派，效果正好是需求里的「后面的让位」。

    :param values:   配置里的原始值（列表 / 元组 / 其它任意值）
    :param warnings: 可选列表，回落原因会追加进去
    :return:         长度恒为 4 的新列表
    """
    if values is None:
        items = []
    elif isinstance(values, (list, tuple)):
        items = list(values)
    else:
        if warnings is not None:
            warnings.append(
                f"「{JIEJIE_KEY_PRIORITY}」不是列表，已按默认值执行"
            )
        items = []

    if items and len(items) != JIEJIE_PRIORITY_COUNT and warnings is not None:
        warnings.append(
            f"「{JIEJIE_KEY_PRIORITY}」应为 {JIEJIE_PRIORITY_COUNT} 项，"
            f"实际 {len(items)} 项，已按 {JIEJIE_PRIORITY_COUNT} 项执行"
        )

    result = [None] * JIEJIE_PRIORITY_COUNT
    taken = set()
    for index in range(JIEJIE_PRIORITY_COUNT):
        if index >= len(items):
            continue
        value = items[index]
        if not isinstance(value, str) or value not in JIEJIE_PRIORITY_OPTIONS:
            if warnings is not None:
                warnings.append(
                    f"寄养优先级第 {index + 1} 项 {value!r} 不受支持，已按顺序补默认值"
                )
            continue
        if value in taken:
            if warnings is not None:
                warnings.append(
                    f"寄养优先级第 {index + 1} 项 {value!r} 与更靠前的项重复，已换成一个未占用的值"
                )
            continue
        result[index] = value
        taken.add(value)

    # 空位按池序补齐：空位数恒等于池中剩余项数（4 个选项、4 个位置）
    pool = [option for option in JIEJIE_PRIORITY_OPTIONS if option not in taken]
    for index in range(JIEJIE_PRIORITY_COUNT):
        if result[index] is None:
            result[index] = pool.pop(0)
    return result


def jiejie_card_order(card):
    """两张结界卡的尝试顺序：优先的那张在前

    :param card: ``太鼓`` 或 ``斗鱼``（非法值按默认的太鼓处理）
    :return:     二元组，如 ``("太鼓", "斗鱼")``
    """
    first = normalize_jiejie_card(card)
    rest = [option for option in JIEJIE_CARD_OPTIONS if option != first]
    return (first, rest[0])


def jiejie_priority_cards(priority):
    """把寄养优先级转成 ((卡名, 模板路径), ...)，顺序即尝试顺序

    :param priority: 4 项配置值（会被归一化，非法/重复自动修正）
    :return:         元组，每项 ``(卡名, "./pic/guild/<卡名>.png")``
    """
    return tuple(
        (name, JIEJIE_PRIORITY_PICS[name])
        for name in normalize_jiejie_priority(priority)
    )


def load_jiejie_settings(Account=None, path=None):
    """读取某账号的结界养成配置；任何异常都回落默认值，绝不抛

    默认值就是本次改动之前写死的行为，所以老配置（没有「结界养成」段）
    跑起来与以前完全一致。

    :param Account: 账号名（「结界养成」段的子键，与「启动项」同名）；
                    None 表示不区分账号，直接取默认值
    :param path:    配置文件路径，默认 ``config/Setting.yml``
    :return:        ``{"card": str, "priority": list[str], "warnings": [str]}``
    """
    warnings = []
    try:
        config = read_config(path or paths.SETTING)
    except Exception as error:      # read_config 已兜住常见异常，这里只是不信任
        config = {}
        warnings.append(f"读取结界养成配置失败：{error}")

    section = config.get(JIEJIE_SECTION) if isinstance(config, dict) else None
    account_config = None
    if isinstance(section, dict) and Account is not None:
        account_config = section.get(Account)
    if not isinstance(account_config, dict):
        account_config = {}

    return {
        "card": normalize_jiejie_card(account_config.get(JIEJIE_KEY_CARD), warnings),
        "priority": normalize_jiejie_priority(
            account_config.get(JIEJIE_KEY_PRIORITY), warnings
        ),
        "warnings": warnings,
    }


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
