from datetime import datetime, time
from Lib import Find_windows, Find_in_windows_Matchs, Find_Click_windows, Itface_daily, read_config, write_config, check_lasttime, Esc_print, Sleep_print, Team_Preset, Itface_Host


def MainTask_Shouliezhan():
    """
    狩猎战主任务
    """
    print("        ")
    print("TASK- ----- 开始狩猎战任务 ----------------------------------------------------------------")
    current_time = datetime.now()
    today = datetime.now()
    week_day = today.weekday()
    week_list = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    if week_day >= 5:
        print("TASK- ----- 今天是", week_list[week_day], "进行阴界之门任务")
        MainTask_Yingjiezhimen()
    else:
        print("TASK- ----- 今天是", week_list[week_day], "进行麒麟狩猎战任务")
        MainTask_Qilin()


def MainTask_Qilin():
    return 0


def MainTask_Yingjiezhimen():
    current_time = datetime.now()
    if time(17, 0) <= current_time.time() <= time(23, 00):
        print("TASK- ----- 当前时间在17:00-23:00之间 开始执行阴界之门任务")
        config_data = read_config("./config/Last_times.yml")
        headers = list(config_data.keys())
        for Account in headers:
            print("    切换到 ", Account, " 账号")
            print("        TIME- ----- 读取上次账号", Account, "完成狩猎战任务时间")
            Times_shouliezhan = check_lasttime(Account, "狩猎战")
            current_time = datetime.now()
            if Times_shouliezhan.date() != current_time.date():
                Hwnd = Find_windows(Account)
                if Task_Yingjiezhimen(Hwnd, Account):
                    # 更新配置，写入当前时间
                    config = read_config("./config/Last_times.yml")
                    Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    config[Account]["狩猎战"] = Now
                    write_config("./config/Last_times.yml", config)
                    print("        TIME- ----- 本次狩猎战完成时间")
                    print("        TIME- ----- ", Now)
                    print("        TASK- ----- 结界狩猎战任务完成")
                else:
                    print("        TASK- ----- 狩猎战任务执行过程中出现错误 中断任务")
            else:
                print("        SKIP- ----- 今日已完成狩猎战任务 跳过")
    else:
        print("TASK- ----- 当前时间不在17:00-21:50之间 跳过")
    print("TASK- ----- 狩猎战任务结束 ----------------------------------------------------------------")


def Task_Yingjiezhimen(Hwnd, Account):
    current_state = "御魂装配"
    for step in range(120):
        Sleep_print(1)
        match current_state:
            case "御魂装配":
                print("        INFO- ----- 装配结界编队")
                Team_Preset(Hwnd, "日常编组", "阴界编队")
                print("        STEP- vvvvv 跳转庭院界面")
                current_state = "庭院界面"

            case "庭院界面":
                print("        INFO- ----- 前往阴界之门界面")
                Itface_daily(Hwnd)
                Find = Find_Click_windows(Hwnd, "./pic/Shouliezhan/阴界之门图标.png", 0.05, "点击阴界之门图标", "未检测到阴界之门图标")
                if Find:
                    Find_Click_windows(Hwnd, "./pic/Shouliezhan/前往.png", 0.05, "点击前往图标", "未检测到前往图标")
                    print("        STEP- vvvvv 跳转阴界之门界面")
                    current_state = "阴界之门界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "阴界之门界面":
                Find_Click_windows(Hwnd, "./pic/Shouliezhan/攻打阴界之门.png", 0.05, "点击攻打阴界之门", "未检测到攻打阴界之门图标")
                Sleep_print(2)
                Find_Click_windows(Hwnd, "./pic/Shouliezhan/挑战.png", 0.05, "点击挑战图标", "未检测到挑战图标")
                Sleep_print(2)
                Find_Click_windows(Hwnd, "./pic/Thr/真蛇确定.png", 0.05, "点击确定图标", "未检测到确定图标")
                Sleep_print(2)
                print("        STEP- vvvvv 跳转组队界面")
                current_state = "组队界面"

            case "组队界面":
                Find = Find_Click_windows(Hwnd, "./pic/Shouliezhan/组队界面挑战图标.png", 0.05, "点击挑战", "未检测到挑战图标")
                if Find:
                    print("        STEP- vvvvv 跳转战斗界面")
                    current_state = "战斗界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "战斗界面":
                Find = Find_Click_windows(Hwnd, "./pic/Digui/Zhunbei.png", 0.05, "点击准备", "未检测到准备图标")
                if Find:
                    print("        STEP- vvvvv 跳转战斗界面")
                    current_state = "等待结束"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "等待结束":
                Waiting = 100
                print("        INFO- 等待", Waiting, "秒后开始检测结束")
                Sleep_print(Waiting)
                for Wait in range(120):
                    Range, Match = Find_in_windows_Matchs(Hwnd, "./pic/Shouliezhan/胜利太鼓.png", 0.05, 0)
                    if Range:
                        print("        STEP- vvvvv 跳转结束界面")
                        current_state = "结束界面"
                        break
                    else:
                        print("        INFO-", Match, "未检测到结束")
                        print("        WAIT- wwwww 等待准备 已等待 {waittime} 秒".format(waittime=Waiting + Wait * 5))
                        Sleep_print(5)
                    if Wait == 119:
                        print("        INFO- 等待轮耗尽 尝试再次进入等待轮")
                        current_state = "等待结束"

            case "结束界面":
                print("        TASK- ----- 阴界之门狩猎战完成")
                Find = Find_Click_windows(Hwnd, "./pic/Shouliezhan/胜利太鼓.png", 0.05, "点击胜利太鼓图标", "未检测到胜利太鼓图标")
                Sleep_print(1)
                Itface_Host(Hwnd)
                return 1

            case "异常退出":
                Itface_Host(Hwnd)
                return 0

    print("        STEP- vvvvv 状态机轮次耗尽")
    return 0
