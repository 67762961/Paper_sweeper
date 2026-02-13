import win32gui
import ctypes
import cv2
import pyautogui
import pydirectinput
import time
import numpy as np
import random
from datetime import datetime
import os
import ruamel.yaml
import subprocess
import yaml


def Sleep_print(Wait_time):
    time.sleep(Wait_time)
    print("        WAIT- sssss 等待{Time}秒钟".format(Time=Wait_time))


def Scroll_print(Hwnd, length):
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    time.sleep(0.1)
    for i in range(abs(length)):
        pyautogui.scroll(int(length / abs(length)))
        time.sleep(0.01)
    print("        MOVE- mmmmm 滚轮滚动{Length}".format(Length=length))


def Esc_print(Hwnd):
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    time.sleep(0.1)
    pydirectinput.press("esc")
    time.sleep(0.1)
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

    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    if hwnds:
        return hwnds[0]
    else:
        print("        INFO- ----- 未检测到窗口", title, "正在尝试启动游戏")
        Log_in(title)
        return Find_windows(title)


def Log_in(title):
    with open("./config/Setting.yml", "r", encoding="utf-8") as f:
        config = read_config("./config/Setting.yml")
        launch_cmd = config["启动项"][title]["启动命令"]
    subprocess.Popen(launch_cmd, shell=True)
    print("        INFO- -----", title, "正在启动")
    time.sleep(20)
    Hwnd = Find_windows(title)

    for Wait in range(100):
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/适龄提示标.png", 0.03, 0)
        if Range:
            Sleep_print(1)
            print("        INFO-", Matchs, "检测到适龄提示界面 点击进入游戏")
            Click(Hwnd, [(830, 940), (1085, 1010)], 7)
            return 1
        else:
            print("        INFO-", Matchs, "未检测到适龄提示界面")
            print("        WAIT- wwwww 等待准备 已等待 {waittime} 秒".format(waittime=Wait * 1 + 20))
            Sleep_print(1)


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
        time.sleep(Wait)
        return 1


def Find_Click_windows(Hwnd, Model_path, Threshold, message_F, message_C):
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
    # 截取屏幕
    Screenshot = pyautogui.screenshot()

    # 转换为OpenCV格式
    Img = cv2.cvtColor(np.array(Screenshot), cv2.COLOR_RGB2BGR)

    # 调用内部模板匹配函数
    return Match_model(Img, Img_model_path, Threshold, Flag_show)


def Find_Click_screen(Model_path, Threshold, message_F, message_C):
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
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


def read_config(FILE_PATH):
    """
    读取YAML配置文件
    """
    yaml = ruamel.yaml.YAML()
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            return yaml.load(f)
    else:
        return {}


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


def check_lasttime(Account, Times_name):
    """
    检测上次运行的时间 如果文件或配置不存在则自动创建
    使用ruamel.yaml处理YAML格式配置文件
    """
    file_path = "./config/Last_times.yml"  # 改为YAML文件扩展名

    # 初始化ruamel.yaml
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    CommentedMap = ruamel.yaml.comments.CommentedMap

    # 确保配置目录存在
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
        except Exception as e:
            print("读取配置文件失败: ", e)
            # 尝试使用更宽松的方式重新读取
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    config = yaml.load(file) or CommentedMap()
            except:
                print("配置文件格式错误 将重置")
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


def Itface_Quit(Hwnd):
    """
    检测是否有退出界面 有则esc解除
    :param Hwnd:    窗口句柄
    :return: None
    """
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    time.sleep(0.5)
    # 注：此处退出界面条件可以极为苛刻 一般识别取值为0.006
    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Tuichuyouxi.png", 0.01, 0)
    if Range:
        print("        INFO-", Matchs, "检测到退出界面")
        Find_Click_windows(Hwnd, "./pic/Main/Quxiaotuichu.png", 0.03, "取消退出", "取消退出失败")
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
            ctypes.windll.user32.SetForegroundWindow(Hwnd)
            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Zhujiemian.png", 0.05, 0)
            if Range:
                print("        INFO-", Matchs, "检测到进入庭院")
                return 1
            else:
                print("        INFO-", Matchs, "未检测到庭院界面")
                # 一键返回
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/一键返回庭院.png", 0.05, 0)
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
        match current_state:
            case "庭院界面":
                Check = Host_check(Hwnd, Wait)
                if Check:
                    return 1
                else:
                    current_state = "检测协作"
            case "检测协作":
                # 检测协作
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/拒绝协作.png", 0.01, 0)
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
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Cha.png", 0.01, 0)
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
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/退出标志1.png", 0.05, 0)
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
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/退出标志2.png", 0.05, 0)
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
    # 检测是否位于庭院主界面
    ctypes.windll.user32.SetForegroundWindow(Hwnd)
    Itface_Host(Hwnd)

    # 检测底部卷轴是否展开
    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Shishenlu.png", 0.05, 0)
    if not Range:
        print("        INFO-", Matchs, "检测到卷轴尚未打开 点击打开卷轴")
        # 坐标法点击展开卷轴
        Range = ((1780, 970), (1910, 1120))
        Click(Hwnd, Range, 2)

        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Shishenlu.png", 0.05, 0)
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
    # 确保卷轴打开
    Itface_scroll(Hwnd)

    # 进入阴阳寮
    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Yinyangliao.png", 0.05, 0)
    if Range:
        Click(Hwnd, Range, 1)
        print("        INFO-", Matchs, "进入阴阳寮")
        time.sleep(1)
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
        if Find_Click_windows(Hwnd, "./pic/Main/Fengmorukou.png", 0.05, "进入逢魔入口", "未检测到逢魔入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/Main/Doujirukou.png", 0.05, "进入斗技入口", "未检测到斗技入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/Shouliezhan/阴界之门入口.png", 0.05, "进入阴界之门入口", "未检测到阴界之门入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/Main/Daoguanrukou.png", 0.05, "进入道馆入口", "未检测到道馆入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/Main/Baiguiyirukou.png", 0.05, "进入百鬼弈入口", "未检测到百鬼弈入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/Main/Xiajiananyurukou.png", 0.05, "进入狭间暗域入口", "未检测到狭间暗域入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/Main/Qilinrukou.png", 0.05, "进入麒麟入口", "未检测到麒麟入口"):
            break
        if Find_Click_windows(Hwnd, "./pic/Main/Yanhuirukou.png", 0.05, "进入宴会入口", "未检测到宴会入口"):
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
        Sleep_print(1)
        match current_state:
            case "庭院界面":
                Find = Find_Click_windows(Hwnd, "./pic/Main/阴阳术.png", 0.05, "点击阴阳术图标", "未检测到阴阳术图标")
                if Find:
                    print("        STEP- vvvvv 跳转阴阳术界面")
                    current_state = "阴阳术界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "阴阳术界面":
                Find = Find_Click_windows(Hwnd, "./pic/Main/御神.png", 0.05, "点击御神按钮", "未检测到御神按钮")
                if Find:
                    print("        STEP- vvvvv 跳转御神界面")
                    current_state = "御神界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "御神界面":
                Find = Find_Click_windows(Hwnd, "./pic/Main/前往六道.png", 0.05, "点击前往六道按钮", "未检测到前往六道按钮")
                if Find:
                    print("        STEP- vvvvv 跳转六道界面")
                    current_state = "六道界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "六道界面":
                print("        INFO- -----点击退出区域")
                Range = [(20, 105), (91, 175)]
                Click(Hwnd, Range, 1)
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Digui/Diguitubiao.png", 0.05, 0)
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
        Sleep_print(1)
        match current_state:
            case "庭院卷轴界面":
                Find = Find_Click_windows(Hwnd, "./pic/Main/Shishenlu.png", 0.05, "点击式神录", "未检测到式神录")
                Sleep_print(1)
                if Find:
                    print("        STEP- vvvvv 跳转式神录界面")
                    current_state = "式神录界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "式神录界面":
                Find = Find_Click_windows(Hwnd, "./pic/Team/Yushexuanxiang.png", 0.05, "点击预设选项", "未检测到预设选项")
                if Find:
                    print("        STEP- vvvvv 跳转队伍预设")
                    current_state = "队伍预设"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "队伍预设":
                Range, Matchs = Find_in_windows_Matchs(Hwnd, f"./pic/Team/{Preset_Group}.png", 0.01, 0)
                if Range:
                    Find = Find_Click_windows(Hwnd, f"./pic/Team/{Preset_Group}.png", 0.01, f"选择预设编组 {Preset_Group}", f"未检测到预设编组 {Preset_Group}")
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
                Range, Matchs = Find_in_windows_Matchs(Hwnd, f"./pic/Team/{Preset_name}.png", 0.01, 0)
                if Range:
                    Find = Find_Click_windows(Hwnd, f"./pic/Team/{Preset_name}.png", 0.01, f"选择预设队伍 {Preset_name}", f"未检测到预设队伍 {Preset_name}")
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
                Find = Find_Click_windows(Hwnd, "./pic/Team/应用御魂预设.png", 0.03, "点击应用御魂预设", "未检测到应用御魂预设按钮")
                if Find:
                    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Queding.png", 0.05, 0)
                    if Range:
                        Click(Hwnd, Range, 0.5)
                        print("        INFO-", Matchs, "点击确认")
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
