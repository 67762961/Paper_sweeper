from datetime import datetime, time
from Lib import (
    Find_windows,
    Find_in_windows_Matchs,
    Find_Click_windows,
    Itface_Host,
    Itface_explore,
    read_config,
    write_config,
    check_lasttime,
    Esc_print,
    Sleep_print,
    Team_Preset,
    Move_to_range,
    Scroll_print,
    Itface_scroll,
    Click,
    Find_in_windows_Range,
    Find_multiple_in_windows_Matchs,
)


def MainTask_JiejieFight():
    print("        ")
    print("TASK- ----- 开始结界突破任务 ----------------------------------------------------------------")
    config_data = read_config("./config/Last_times.json")
    headers = list(config_data.keys())
    for Account in headers:
        print("    切换到 ", Account, " 账号")
        Hwnd = Find_windows(Account)
        if JiejieFight(Hwnd):
            # 更新配置 写入当前时间
            config = read_config("./config/Last_times.json")
            Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            config[Account]["结界突破"] = Now
            write_config("./config/Last_times.json", config)
            print("        TIME- ----- 本次结界突破完成时间")
            print("        TIME- ----- ", Now)
            print("        TASK- ----- 结界突破任务完成")
        else:
            print("        TASK- ----- 结界突破任务执行过程中出现错误 中断任务")
    print("TASK- ----- 结界突破任务结束 ----------------------------------------------------------------")


def FullTask_JiejieFight():
    """
    结界突破主任务
    """
    print("        ")
    print("TASK- ----- 开始结界突破任务 ----------------------------------------------------------------")
    current_time = datetime.now()
    if time(12, 0) <= current_time.time() <= time(23, 00):
        print("TASK- ----- 当前时间在12:00-24:00之间 可以执行结界突破任务")
        config_data = read_config("./config/Last_times.json")
        headers = list(config_data.keys())
        for Account in headers:
            print("    切换到 ", Account, " 账号")
            print("        TIME- ----- 读取上次账号", Account, "完成结界突破任务时间")
            Times_jiejieFight = check_lasttime(Account, "结界突破")
            current_time = datetime.now()
            # 当天未完成结界突破任务 则执行
            if Times_jiejieFight.date() != current_time.date():
                Hwnd = Find_windows(Account)
                if JiejieFight(Hwnd):
                    # 更新配置 写入当前时间
                    config = read_config("./config/Last_times.json")
                    Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    config[Account]["结界突破"] = Now
                    write_config("./config/Last_times.json", config)
                    print("        TIME- ----- 本次结界突破完成时间")
                    print("        TIME- ----- ", Now)
                    print("        TASK- ----- 结界突破任务完成")
                else:
                    print("        TASK- ----- 结界突破任务执行过程中出现错误 中断任务")
            else:
                print("        SKIP- ----- 今日已完成结界突破任务 跳过")
    else:
        print("TASK- ----- 当前时间不在12:00-24:00之间 跳过")
    print("TASK- ----- 结界突破任务结束 ----------------------------------------------------------------")


def JiejieFight(Hwnd):
    current_state = "御魂装配"
    for step in range(120):
        Sleep_print(1)
        match current_state:
            case "御魂装配":
                print("        INFO- ----- 装配结界编队")
                Team_Preset(Hwnd, "日常编组", "结界编队")
                print("        STEP- vvvvv 跳转庭院界面")
                current_state = "庭院界面"

            case "庭院界面":
                print("        INFO- ----- 前往结界突破界面")
                Itface_explore(Hwnd)
                Find = Find_Click_windows(Hwnd, "./pic/JiejieFight/结界突破图标.png", 0.05, "点击结界图标", "未检测到结界图标")
                if Find:
                    print("        STEP- vvvvv 跳转结界突破界面")
                    current_state = "结界突破界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "结界突破界面":
                Num, Range, Matchs = Find_multiple_in_windows_Matchs(Hwnd, "./pic/JiejieFight/已攻破结界.png", 0.07, 0)
                if Num < 8:
                    print("        INFO- ----- 检测到", Num, "个已攻破结界 继续挑战未攻破结界")
                    if Num == 0:
                        Num, Range, Matchs = Find_multiple_in_windows_Matchs(Hwnd, "./pic/JiejieFight/勋章.png", 0.03, 0, 45)
                        print("        INFO- ----- 检测到", Num, "个勋章")
                        if Num < 20:
                            print("        INFO- ----- 勋章少于20个 暂停结界突破任务 等待人工刷新")
                            Itface_Host(Hwnd)
                            return 0
                    print("        STEP- vvvvv 跳转正常战斗界面")
                    current_state = "正常战斗界面"
                else:
                    print("        INFO- ----- 检测到", Num, "个已攻破结界 准备三退")
                    print("        STEP- vvvvv 跳转三退战斗界面")
                    current_state = "三退战斗界面"

                Sleep_print(1)

                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/JiejieFight/目标结界.png", 0.005, 0)
                if Range:
                    print("        INFO-", Matchs, "发现目标结界 准备战斗")
                    Move_to_range(Hwnd, Range)
                    Click(Hwnd, Range, 0.5)
                    Find = Find_Click_windows(Hwnd, "./pic/JiejieFight/进攻.png", 0.05, "点击进攻", "未检测到进攻图标")
                    Sleep_print(1)
                    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/JiejieFight/进攻.png", 0.05, 0)
                    if Range:
                        print("        INFO-", Matchs, "进攻按钮点击失败 似乎已经无结界挑战券")
                        print("        STEP- vvvvv 跳转结束")
                        current_state = "结束"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "正常战斗界面":
                Sleep_print(10)
                for Wait in range(60):
                    Range, Match = Find_in_windows_Matchs(Hwnd, "./pic/JiejieFight/结束奖励.png", 0.01, 0)
                    if Range:
                        print("        INFO-", Matchs, "点击结束奖励")
                        Move_to_range(Hwnd, Range)
                        Click(Hwnd, Range, 1)
                        print("        STEP- vvvvv 跳转战斗结束界面")
                        current_state = "战斗结束界面"
                        break
                    else:
                        print("        INFO-", Matchs, "未检测到结束奖励")
                        print("        WAIT- wwwww 等待准备 已等待 {waittime} 秒".format(waittime=Wait * 5 + 10))
                        Sleep_print(5)
                if not Find:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "战斗结束界面":
                Range, Match = Find_in_windows_Matchs(Hwnd, "./pic/JiejieFight/结束奖励.png", 0.01, 0)
                if Range:
                    print("        INFO-", Matchs, "点击结束奖励")
                    Move_to_range(Hwnd, Range)
                    Click(Hwnd, Range, 0.5)
                else:
                    print("        INFO-", Matchs, "未检测到结束奖励")
                    print("        STEP- vvvvv 跳转结界突破界面")
                    current_state = "结界突破界面"

            case "三退战斗界面":
                for times in range(3):
                    print("        INFO- ----- 第", times + 1, "次退出")
                    for wait in range(10):
                        Sleep_print(0.5)
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                        Find = Find_Click_windows(Hwnd, "./pic/JiejieFight/确认.png", 0.05, "点击确认", "未检测到确认按钮")
                        if Find:
                            break

                    for wait in range(10):
                        Sleep_print(3)
                        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/JiejieFight/再次挑战.png", 0.05, 0)
                        if Range:
                            print("        INFO- ----- 发现再次挑战按钮 点击")
                            Click(Hwnd, Range, 1)
                            break
                        else:
                            print("        INFO- ----- 未发现再次挑战按钮 继续等待 已等待 {waittime} 秒".format(waittime=wait + 3))

                    Sleep_print(1)
                    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Queding.png", 0.05, 0)
                    if Range:
                        print("        INFO- ----- 出现再次挑战二次确认弹框 点击确认")
                        Find_Click_windows(Hwnd, "./pic/JiejieFight/今日不再提醒.png", 0.05, "点击今日不再提醒", "未检测到今日不再提醒")
                        Find_Click_windows(Hwnd, "./pic/JiejieFight/确认.png", 0.05, "点击确认", "未检测到确认按钮")
                    else:
                        print("        INFO- ----- 未出现再次挑战二次确认弹框")
                print("        INFO- ----- 三退完成")
                print("        STEP- vvvvv 跳转正常战斗界面")
                current_state = "正常战斗界面"

            case "异常退出":
                Itface_Host(Hwnd)
                return 0

            case "结束":
                Esc_print(Hwnd)
                Sleep_print(1)
                Esc_print(Hwnd)
                Sleep_print(2)
                Itface_Host(Hwnd)
                return 1

    print("        STEP- vvvvv 状态机轮次耗尽")
    return 0
