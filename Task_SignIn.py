import pyautogui
import pydirectinput
import ctypes
import win32gui
from datetime import datetime, timedelta
from Lib import Find_in_windows_Matchs, Find_windows, Find_Click_windows, Click, Itface_Host, read_config, write_config, Itface_scroll, check_lasttime, Sleep_print, Esc_print


def MainTask_Mail():
    """
    邮件主任务
    """
    print("        ")
    current_time = datetime.now()
    print("TASK- ----- 开始执行邮件任务")
    config_data = read_config("./config/Last_times.json")
    headers = list(config_data.keys())
    for Account in headers:
        print("    切换到 ", Account, " 账号")
        print("        TIME- ----- 读取上次账号", Account, "完成邮件时间")
        Times_youjian = check_lasttime(Account, "邮件领取")
        current_time = datetime.now()
        if abs(current_time - Times_youjian) >= timedelta(hours=6):
            Hwnd = Find_windows(Account)
            Work_Mail(Hwnd, Account)
        else:
            print("        SKIP- ----- 邮件查看时间间隔未满六小时 跳过")


def Work_Mail(Hwnd, Account):
    """
    领取邮件奖励
    :param Hwnd:    窗口句柄
    :return:        1为正常 0为异常
    """
    Itface_Host(Hwnd)

    Find_Click_windows(Hwnd, "./pic/Mail/Youjian.png", 0.05, "点击邮件", "未识别到邮件入口")

    # 检测邮箱界面
    if not Find_Click_windows(Hwnd, "./pic/Mail/Youxiang.png", 0.1, "检测到进入邮箱", "进入邮箱异常"):
        Itface_Host(Hwnd)
        return 0

    # 检测是否有奖励未领取
    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Mail/Quanbulingqu.png", 0.05, 0)

    # 没有奖励未领取 检测消息邮件 然后返回
    if not Range:
        print("        INFO-", Matchs, "没有奖励未领取")
        # 检测消息邮件
        while 1:
            if not Find_Click_windows(Hwnd, "./pic/Mail/Xiaoxiyoujian.png", 0.05, "发现消息邮件", "未发现消息邮件"):
                break

        Esc_print(Hwnd)
        Sleep_print(1)
        Itface_Host(Hwnd)
        return 1

    # 有奖励未领取
    else:
        print("        INFO-", Matchs, "有奖励未领取")
        # 点击全部领取
        Click(Hwnd, Range, 1)

        # 检测全部领取界面
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Mail/Quanbulingqujiemian.png", 0.05, 0)
        if Range:
            print("        INFO-", Matchs, "检测到进入领取界面")
        else:
            print("        INFO-", Matchs, "未正常领取")
            Sleep_print(1)
            Itface_Host(Hwnd)
            return 0

        # 点击确定
        Find_Click_windows(Hwnd, "./pic/Main/Queding.png", 0.05, "点击确定", "未正常领取确认")
        Sleep_print(1)
        # 检测领取
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
        if Range:
            print("        INFO-", Matchs, "领取成功")
            # 按下esc退出
            Esc_print(Hwnd)
            Sleep_print(1)
            # 检测消息邮件
            while 1:
                if not Find_Click_windows(Hwnd, "./pic/Mail/Xiaoxiyoujian.png", 0.05, "点击消息邮件", "未发现消息邮件"):
                    break

            Esc_print(Hwnd)

            # 更新配置 写入当前时间

            config = read_config("./config/Last_times.json")
            Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            config[Account]["邮件领取"] = Now
            write_config("./config/Last_times.json", config)
            print("        TIME- ----- 本次邮件领取时间")
            print("        TIME- ----- ", Now)
            print("        TASK- ----- 邮件领取完成 --------------------------------")
            Itface_Host(Hwnd)
            return 1


def MainTask_QiandaoFudai():
    """
    签到福袋主任务
    """
    print("        ")
    current_time = datetime.now()
    print("TASK- ----- 开始签到福袋任务")
    config_data = read_config("./config/Last_times.json")
    headers = list(config_data.keys())

    for Account in headers:
        print("    切换到 ", Account, " 账号")
        print("        TIME- ----- 读取上次账号", Account, "领取福袋时间")
        Times_fudai = check_lasttime(Account, "福袋纸人")
        current_time = datetime.now()
        if Times_fudai.date() != current_time.date():
            Hwnd = Find_windows(Account)
            Fudai(Hwnd, Account)
        else:
            print("        SKIP- ----- 今天已经领取过福袋纸人 跳过")

        Times_qiandao = check_lasttime(Account, "每日一签")
        if Times_qiandao.date() != current_time.date():
            Hwnd = Find_windows(Account)
            Qiandao(Hwnd, Account)
        else:
            print("        SKIP- ----- 今天已经完成每日一签 跳过")


def Fudai(Hwnd, Account):
    """
    每日福袋
    """
    # 检测福袋小纸人
    if Find_Click_windows(Hwnd, "./pic/Sign/Fudaixiaozhiren.png", 0.05, "检测到福袋小纸人", "未检测到福袋小纸人"):
        # 点击福袋小人后检测领取状态
        Range, Match = Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
        if Range:
            print("        INFO-", Matchs, "福袋领取成功")
            Esc_print(Hwnd)
            Sleep_print(0.5)
            # 更新配置 写入当前时间
            config = read_config("./config/Last_times.json")
            Now = current_time.strftime("%Y-%m-%d %H:%M:%S")
            config[Account]["福袋纸人"] = Now
            write_config("./config/Last_times.json", config)
            print("        TIME- ----- 本次福袋小纸人领取时间: ")
            print("        TIME- ----- ", Now)
            print("        TASK- ----- 福袋小纸人领取成功 --------------------------------")
            return 1
        else:
            print("        INFO-", Matchs, "福袋似乎未领取成功")
            return 0
    else:
        return 0


def Qiandao(Hwnd, Account):
    """
    每日签到
    """
    Wait = 0
    for i in range(5):
        # 检测签小纸人
        if Find_Click_windows(Hwnd, "./pic/Sign/Qiandaoxiaozhiren.png", 0.07, "检测到签到小纸人", "未检测到签到小纸人"):
            # 点击签到小人后
            if Find_Click_windows(Hwnd, "./pic/Sign/Meiriyiqian.png", 0.05, "每日一签", "签到异常"):
                for i in range(2):
                    Sleep_print(0.5)
                    Range, Match = Find_in_windows_Matchs(Hwnd, "./pic/Sign/Jieqianxiaozhiren.png", 0.05, 0)
                    if Range:
                        print("        INFO-", Matchs, "检测到解签小纸人 每日一签成功")
                        # 更新配置 写入当前时间
                        config = read_config("./config/Last_times.json")
                        Now = current_time.strftime("%Y-%m-%d %H:%M:%S")
                        config[Account]["每日一签"] = Now
                        write_config("./config/Last_times.json", config)
                        print("        TIME- ----- 本次每日一签时间: ")
                        print("        TIME- ----- ", Now)
                        print("        TASK- ----- 每日一签成功 --------------------------------")
                    else:
                        print("        INFO-", Matchs, "未检测到解签小纸人")
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                Esc_print(Hwnd)
                Sleep_print(0.5)
                break
        else:
            Sleep_print(0.1)


def zhirenjiangli(Hwnd):
    """
    体力小纸人 勾玉小纸人 buff小纸人
    """
    # 检测体力小纸人
    if Find_Click_windows(Hwnd, "./pic/Sign/Tilixiaozhire.png", 0.07, "检测到体力小纸人", "未检测到体力小纸人"):
        Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
        print("体力领取成功")

        Esc_print(Hwnd)
        Sleep_print(0.5)

    # 检测勾玉小纸人
    if Find_Click_windows(Hwnd, "./pic/Sign/Gouyuxiaozhiren.png", 0.07, "检测到勾玉小纸人", "未检测到勾玉小纸人"):
        Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
        print("勾玉领取成功")

        Esc_print(Hwnd)
        Sleep_print(0.5)

    # 检测buff小纸人
    if Find_Click_windows(Hwnd, "./pic/Sign/BUFFxiaozhiren.png", 0.07, "检测到BUFF小纸人", "未检测到BUFF小纸人"):
        Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
        print("BUFF领取成功")

        Esc_print(Hwnd)
        Sleep_print(0.5)


def mianfeilibao(Hwnd, Account):
    """
    商店免费礼包
    """
    # 读取上次免费礼包
    print("TIME- ----- 读取上次免费礼包时间")
    Times_mianfeilibao = check_lasttime(Account, "免费礼包")

    current_time = datetime.now()

    if Times_mianfeilibao.date() != current_time.date():
        # 开卷轴
        Itface_scroll(Hwnd)
        for i in range(1):
            if not Find_Click_windows(Hwnd, "./pic/Sign/Shangdian.png", 0.05, "进入商店", "未检测到商店"):
                break
            if not Find_Click_windows(Hwnd, "./pic/Sign/Libaowu.png", 0.05, "进入礼包屋", "未检测到礼包屋"):
                if not Find_Click_windows(Hwnd, "./pic/Sign/Libaowu1.png", 0.05, "进入礼包屋", "未检测到礼包屋"):
                    break

            # 此步骤有时候可跳过
            Find_Click_windows(Hwnd, "./pic/Sign/Richang.png", 0.05, "进入日常项", "未检测到日常项")

            if Find_Click_windows(Hwnd, "./pic/Sign/Mianfei.png", 0.05, "领取免费礼包", "未检测到免费礼包"):
                # 检测领取状态
                Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
                print("免费礼包领取成功")
                Esc_print(Hwnd)
                Sleep_print(0.5)
                # 更新配置，写入当前时间
                config = read_config("./config/Last_times.json")
                Now = current_time.strftime("%Y-%m-%d %H:%M:%S")
                config[Account]["免费礼包"] = Now
                write_config("./config/Last_times.json", config)
                print("TIME- ----- 本次免费礼包领取时间")
                print("TIME- ----- ", Now)

                # 返回庭院
                Esc_print(Hwnd)
                Sleep_print(0.5)
                Esc_print(Hwnd)
                Sleep_print(0.5)
                Itface_Host(Hwnd)
                return 1
        Itface_Host(Hwnd)
        return 0
    else:
        print("SKIP- ----- 跳过商店免费礼包")


def youqingdain(Hwnd, Account):
    """
    每日友情点以及吉闻祝福
    """
    # 读取上次友情点时间
    print("TIME- ----- 读取上次友情点时间")
    Times_youqingdian = check_lasttime(Account, "送友情点")
    current_time = datetime.now()

    # 今日运行过则跳过
    if Times_youqingdian.date() == current_time.date():
        print("SKIP- ----- 跳过友情点任务")
    # 运行友情点任务
    else:
        # 开卷轴
        Itface_scroll(Hwnd)

        current_state = "庭院"
        flag_jiwen = 0
        flag_youqingdian = 0
        for i in range(10):
            match current_state:
                case "庭院":
                    Find = Find_Click_windows(Hwnd, "./pic/Sign/Haoyou.png", 0.05, "进入好友界面", "未检测到好友界面")
                    if Find:
                        current_state = "好友界面"
                        Sleep_print(2)
                    else:
                        current_state = "end"
                case "好友界面":
                    if not flag_jiwen:
                        Find = Find_Click_windows(Hwnd, "./pic/Sign/Jiwen.png", 0.05, "进入吉闻界面", "未检测到吉闻界面")
                        if Find:
                            current_state = "吉闻界面"
                        else:
                            current_state = "好友界面"
                    else:
                        Find = Find_Click_windows(Hwnd, "./pic/Sign/Youqingdianqiehuan.png", 0.05, "进入友情点界面", "未检测到友情点界面")
                        if Find:
                            current_state = "友情点界面"
                        else:
                            current_state = "好友界面"
                case "吉闻界面":
                    Find = Find_Click_windows(Hwnd, "./pic/Sign/Yijianzhufu.png", 0.05, "一键祝福", "未检测到一键祝福")
                    if Find:
                        current_state = "祝福界面"
                    else:
                        current_state = "好友界面"
                        flag_jiwen = 1
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                case "祝福界面":
                    Find_Click_windows(Hwnd, "./pic/Sign/Zhufu.png", 0.05, "祝福", "未检测到祝福")
                    Sleep_print(1)
                    if Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0):
                        print("一键祝福成功")
                        flag_jiwen = 1
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                    else:
                        print("一键祝福似乎未成功")
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                        Find = Find_in_windows_Matchs(Hwnd, "./pic/Sign/Jiwen.png", 0.05, 0)
                        if not Find:
                            print("退出吉闻界面异常")
                            Esc_print(Hwnd)
                            Sleep_print(0.5)
                        else:
                            print("已正常退出吉闻界面")
                    current_state = "好友界面"
                case "友情点界面":
                    Find = Find_Click_windows(Hwnd, "./pic/Sign/Yijianshouqu.png", 0.05, "一键收取", "未检测到一键收取")
                    if Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0):
                        print("一键收取成功")
                        flag_youqingdian = 1
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                        current_state = "end"
                    else:
                        print("一键收取似乎未成功")
                case "end":
                    if flag_youqingdian and flag_jiwen:
                        # 更新配置，写入当前时间
                        config = read_config("./config/Last_times.json")
                        Now = current_time.strftime("%Y-%m-%d %H:%M:%S")
                        config[Account]["送友情点"] = Now
                        print("TIME- ----- 本次友情点任务时间")
                        print("TIME- ----- ", Now)
                        write_config("./config/Last_times.json", config)
                        # 退至庭院
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                        Itface_Host(Hwnd)
                        return 1

        Itface_Host(Hwnd)
        return 0


def Work_Sign(Hwnd, Account):
    """
    签到 福袋 纸人奖励
    @param Hwnd:    窗口句柄
    """
    Itface_Host(Hwnd)

    # 纸人奖励
    zhirenjiangli(Hwnd)

    # 商店免费礼包
    mianfeilibao(Hwnd, Account)

    # 每日友情点
    youqingdain(Hwnd, Account)


def MainTask_Signin(Hwnd, Account):
    """
    完成每日登录所有领取项
    @param Hwnd:    窗口句柄
    """

    # 检测是否位于庭院主界面
    Itface_Host(Hwnd)

    # 开始每日签到以及福袋领取
    print("TASK- +++++ 开始领取签到奖励 ++++++++++++++++++++++++++++++++")
    Work_Sign(Hwnd, Account)
    print("TASK- ----- 领取签到奖励成功 --------------------------------")
