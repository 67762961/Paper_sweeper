import sys
import os
import datetime
import contextlib
from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal
# 中断相关的 request_stop / reset_stop / stop_requested 在此重新导出，
# 供 GUI 层只依赖 main 而不必直接 import Lib
from Lib import (
    Find_windows,
    TaskStopped,
    check_stop,
    read_config,
    reset_stop,
    stop_requested,
    request_stop,
    write_config,
)
from Task_SignIn import MainTask_Signin
from Task_Fengmo import MainTask_Fengmo
from Task_Digui import MainTask_Digui
from Task_Jiejieyangcheng import MainTask_Jiejieyangcheng
from Task_Thirty import FullTask_Thirty
from Task_JiejieFight import MainTask_JiejieFight, FullTask_JiejieFight
from Task_Shouliezhan import MainTask_Shouliezhan


# 创建了一个 Tee 类，用于同时将输出写入文件和控制台
class Tee(QObject):
    text_written = pyqtSignal(str)

    def __init__(self, *files, text_signal=None):
        super().__init__()
        # 过滤空流：打包版 GUI.exe（console=False 或 pythonw）下 sys.stdout 可能为 None
        self.files = tuple(file for file in files if file is not None)
        self.text_signal = text_signal
        self.buffer = ""  # 添加缓冲区处理不完整的行

    def write(self, text):
        # 写入所有文件
        for file in self.files:
            try:
                file.write(text)
                file.flush()
            except Exception:
                # 单个流写失败（如控制台已关闭）不应中断任务
                pass

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
            try:
                file.flush()
            except Exception:
                pass


@dataclass(frozen=True)
class TaskEntry:
    """单个可运行任务条目：左侧卡片、整跑顺序与状态键的唯一事实源"""

    key: str                         # 内部标识，用于卡片点击与单任务日志命名
    title: str                       # 卡片主标题
    desc: str                        # 卡片副标题，说明该任务覆盖的业务
    entry: Callable[[], None]        # 任务入口函数（与整跑一致）
    lasttime_keys: tuple             # Last_times.yml 中对应的完成时间键（取最新值展示）
    today_keys: tuple = ()           # 判定「今日是否已完成」的键；为空表示与 lasttime_keys 相同

    @property
    def label(self):
        return f"{self.key}({self.title})"

    @property
    def check_keys(self):
        """参与今日完成判定的状态键"""
        return self.today_keys or self.lasttime_keys


# 顺序即「完整运行」的执行顺序，新增任务必须登记到这里
TASK_REGISTRY = (
    TaskEntry(
        "signin",
        "登录收菜",
        "邮件·每日一签·福袋·纸人·礼包·友情点",
        MainTask_Signin,
        ("邮件领取", "每日一签", "福袋纸人", "免费礼包", "送友情点"),
    ),
    TaskEntry(
        "jiejieyangcheng",
        "结界养成",
        "工资体力·寄养·结界卡·育成·食盒酒壶",
        MainTask_Jiejieyangcheng,
        ("结界养成",),
    ),
    TaskEntry(
        "digui",
        "地域鬼王",
        "探索→六道→地鬼挑战",
        MainTask_Digui,
        ("地域鬼王",),
    ),
    TaskEntry(
        "thirty",
        "寮三十 / 真蛇",
        "双账号协作刷本 + 非周末真蛇",
        FullTask_Thirty,
        ("寮三十", "真蛇"),
        # 真蛇是周更，不参与「今日已完成」判定，只看寮三十
        ("寮三十",),
    ),
    TaskEntry(
        "jiejiefight",
        "结界突破",
        "按勋章阈值开打·支持退出次数",
        FullTask_JiejieFight,
        ("结界突破",),
    ),
    TaskEntry(
        "shouliezhan",
        "狩猎战 / 阴界",
        "周一至周四麒麟·周五至周日阴界之门",
        MainTask_Shouliezhan,
        ("狩猎战",),
    ),
    TaskEntry(
        "fengmo",
        "逢魔之时",
        "庭院日常入口进入逢魔",
        MainTask_Fengmo,
        ("逢魔之时",),
    ),
)


def get_task(task_key):
    """按 key 查找任务条目，未登记时返回 None"""
    for task in TASK_REGISTRY:
        if task.key == task_key:
            return task
    return None


def _parse_time(value):
    """把 Last_times.yml 中的时间字符串转为 datetime，无法解析时返回 None"""
    if not value:
        return None
    try:
        return datetime.datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def read_completions():
    """一次读取 Last_times.yml，返回 {账号: {任务键: datetime}}；只读，不创建也不写盘"""
    config_data = read_config("./config/Last_times.yml") or {}
    completions = {}
    for account, account_data in config_data.items():
        if not isinstance(account_data, dict):
            continue
        completions[account] = {}
        for key, value in account_data.items():
            moment = _parse_time(value)
            if moment is not None:
                completions[account][key] = moment
    return completions


def latest_completion(entry, completions=None):
    """取该任务在所有账号、所有状态键中的最新完成时间，没有记录时返回 None"""
    completions = read_completions() if completions is None else completions
    latest = None
    for account_data in completions.values():
        for key in entry.lasttime_keys:
            moment = account_data.get(key)
            if moment is not None and (latest is None or moment > latest):
                latest = moment
    return latest


def completion_snapshot(entries=None):
    """记录各任务当前最新完成时间，用于运行后判断是否真正推进"""
    completions = read_completions()
    entries = TASK_REGISTRY if entries is None else entries
    return {entry.key: latest_completion(entry, completions) for entry in entries}


def completion_advanced(before, after):
    """对比快照，返回 {任务key: 是否比运行前更新}（无法判断时按未更新处理）"""
    advanced = {}
    for key, moment in after.items():
        previous = before.get(key)
        advanced[key] = moment is not None and (previous is None or moment > previous)
    return advanced


def entry_done_today(entry, completions=None, today=None):
    """该任务参与今日判定的状态键，是否在所有账号上都已有今天的完成记录"""
    completions = read_completions() if completions is None else completions
    today = today or datetime.date.today()
    keys = entry.check_keys
    if not keys or not completions:
        return False

    for key in keys:
        # 每个状态键都必须在每个账号上都有今天的记录，缺一个即视为今日未完成
        for account_data in completions.values():
            moment = account_data.get(key)
            if moment is None or moment.date() != today:
                return False
    return True


# ---- 任务开关（左侧行最右的开关，决定该任务是否参与「完整运行」）----

GUI_STATE_PATH = "./config/Gui_state.yml"
TASK_SWITCH_SECTION = "任务开关"


def read_task_switches():
    """读取任务开关；文件或键缺失时默认全部开启（只读，不创建文件）"""
    config_data = read_config(GUI_STATE_PATH) or {}
    section = config_data.get(TASK_SWITCH_SECTION)
    if not isinstance(section, dict):
        section = {}
    return {task.key: bool(section.get(task.key, True)) for task in TASK_REGISTRY}


def is_task_enabled(task_key, switches=None):
    """判断某个任务是否参与「完整运行」"""
    switches = read_task_switches() if switches is None else switches
    return switches.get(task_key, True)


def enabled_task_keys(switches=None):
    """参与「完整运行」的任务 key，顺序与注册表一致"""
    switches = read_task_switches() if switches is None else switches
    return [task.key for task in TASK_REGISTRY if switches.get(task.key, True)]


def set_task_switch(task_key, enabled):
    """把单个任务开关写入 config/Gui_state.yml，写入成功返回 True"""
    if get_task(task_key) is None:
        return False
    try:
        os.makedirs(os.path.dirname(GUI_STATE_PATH), exist_ok=True)
        config_data = read_config(GUI_STATE_PATH) or {}
        section = config_data.get(TASK_SWITCH_SECTION)
        if not isinstance(section, dict):
            config_data[TASK_SWITCH_SECTION] = {}
            section = config_data[TASK_SWITCH_SECTION]
        section[task_key] = bool(enabled)
        write_config(GUI_STATE_PATH, config_data)
        return True
    except Exception as error:
        print("TASK- ----- 保存任务开关失败:", error)
        return False


@contextlib.contextmanager
def _log_stream(console_signal, log_prefix):
    """把 stdout 同时重定向到原控制台、日志文件和 GUI 信号；退出时恢复并冲刷缓冲"""
    now = datetime.datetime.now()
    log_dir = os.path.join("logs", now.strftime("%Y-%m-%d"))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = os.path.join(log_dir, f"{log_prefix}_{timestamp}.log")

    with open(log_file_path, "w", encoding="utf-8") as log_file:
        original_stdout = sys.stdout
        tee = Tee(original_stdout, log_file, text_signal=console_signal)
        sys.stdout = tee
        try:
            yield log_file_path
        finally:
            # 先无条件恢复 stdout，避免后续 print 写入已关闭的日志文件；
            # 冲刷只做尽力而为，控制台流在打包版（console=False）下可能为 None
            sys.stdout = original_stdout
            try:
                tee.flush()
            except Exception:
                pass


def Full_operation(console_signal=None):
    """完整运行：按 TASK_REGISTRY 顺序执行未被左侧开关关闭的任务

    返回 {"stopped": 是否被用户中断, "executed": 实际执行数, "skipped": 跳过数}。
    中断由 Lib 的检查点抛出 TaskStopped，这里统一收尾，任务层不感知。
    """
    result = {"stopped": False, "executed": 0, "skipped": 0}
    with _log_stream(console_signal, "console_output"):
        print("        ")
        print("MAIN- ===== 完整运行流程开始 ================================================================")
        switches = read_task_switches()
        try:
            for task in TASK_REGISTRY:
                # 任务之间也检查一次：上一步收尾后用户可能已按下中断
                check_stop()
                if not switches.get(task.key, True):
                    print("SKIP- ----- 任务", task.title, "已在左侧关闭 跳过")
                    result["skipped"] += 1
                    continue
                task.entry()
                result["executed"] += 1
        except TaskStopped:
            result["stopped"] = True
            print("QUIT- ----- 收到中断指令 已停止当前任务 回到待机")

        if result["skipped"]:
            if result["executed"] == 0 and not result["stopped"]:
                print("SKIP- ----- 所有任务均已在左侧关闭 本次完整运行没有执行任何任务")
            elif not result["stopped"]:
                print(f"INFO- ----- 本次完整运行跳过 {result['skipped']} 项已关闭任务 实际执行 {result['executed']} 项")
        print("        ")
        if result["stopped"]:
            print(f"MAIN- ===== 完整运行被中断 已完成 {result['executed']} 项 ========================================")
        else:
            print("MAIN- ===== 完整运行流程结束 ================================================================")
    return result


def Single_operation(task_key, console_signal=None):
    """单任务运行：只执行 TASK_REGISTRY 中指定的一个任务，冷却与时间窗照常生效"""
    task = get_task(task_key)
    if task is None:
        print("TASK- ----- 未登记的任务", task_key, "已忽略")
        return {"key": task_key, "ok": False, "reason": "unknown_task", "stopped": False}

    stopped = False
    with _log_stream(console_signal, f"single_{task.key}"):
        print("        ")
        print(f"MAIN- ===== 单任务运行开始：{task.title} ================================================")
        try:
            task.entry()
        except TaskStopped:
            stopped = True
            print("QUIT- ----- 收到中断指令 已停止当前任务 回到待机")
        print("        ")
        if stopped:
            print(f"MAIN- ===== 单任务运行被中断：{task.title} ================================================")
        else:
            print(f"MAIN- ===== 单任务运行结束：{task.title} ================================================")

    return {"key": task.key, "ok": not stopped, "reason": None, "stopped": stopped}
