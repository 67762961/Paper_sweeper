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
)


def FullTask_Thirty():
    """
    寮三十主任务
    """
    print("        ")
    print("TASK- ----- 开始执行寮三十任务 --------------------------------------------------------------")
    current_time = datetime.now()
    ######## 时间设定上暂时避开逢魔任务
    if not (time(16, 50) <= current_time.time() <= time(21, 50)):
        print("TASK- ----- 当前时间不在16:50-21:50之间 可以执行寮三十任务")
        config_data = read_config("./config/Last_times.json")
        Account = list(config_data.keys())
        Flag = {}
        for i in range(2):
            print("        TIME- ----- 读取上次账号", Account[i], "完成寮三十任务时间")
            Times_liaosanshi = check_lasttime(Account[i], "寮三十")
            Flag[i] = current_time.date() == Times_liaosanshi.date()
        # 如果两个账号都未做寮三十 则进行寮三十任务
        Hwnd = {}
        if not (Flag[0] and Flag[1]):
            MainTask_Thirty()
        else:
            for i in range(2):
                print("        SKIP- ----- 今日账号", Account[i], "已完成寮三十任务 跳过")
    else:
        print("TASK- ----- 时间在16:50-21:50之间 跳过")
    print("TASK- ----- 寮三十任务已完成 ----------------------------------------------------------------")


def MainTask_Thirty():
    config_data = read_config("./config/Last_times.json")
    Account = list(config_data.keys())
    print("        TASK- ----- 开始执行寮三十任务")
    Hwnd = {}
    Hwnd[0] = Find_windows(Account[0])
    Hwnd[1] = Find_windows(Account[1])
    if Task_Liao_30(Hwnd[0], Hwnd[1], Account):
        # 更新配置 写入当前时间
        config = read_config("./config/Last_times.json")
        Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config[Account[0]]["寮三十"] = Now
        config[Account[1]]["寮三十"] = Now
        write_config("./config/Last_times.json", config)
        print("        TIME- ----- 本次寮三十完成时间")
        print("        TIME- ----- ", Now)
        print("        TASK- ----- 寮三十任务完成")
    else:
        print("        TASK- ----- 寮三十任务执行过程中出现错误 中断任务")


def Task_Liao_30(Hwnd1, Hwnd2, Account):
    """
    挑战寮三十
    """
    return Yuhun(Hwnd1, Hwnd2, Account, "魂王", 30)


def Yuhun(Hwnd1, Hwnd2, Account, Fuben, Times):
    """
    御魂副本寮三十
    """
    Hwnd = [Hwnd1, Hwnd2]
    current_state = "御魂装配"
    match Fuben:
        case "魂虚":
            print("        INFO- ----- 选择魂虚副本")
            Preset_Group, Preset_name = "副本编组", "魂虚编队"
            Fuben_Name = "虚无"
            Fuben_Group_Name = "御魂"
            Fuben_Group = "./pic/Thr/御魂副本组别.png"
            Fuben_Group_card = "./pic/Thr/御魂组别选项.png"
            Fuben_Img0 = "./pic/Thr/虚无副本图标0.png"
            Fuben_Img1 = "./pic/Thr/虚无副本图标1.png"
            Buff = 1
        case "魂王":
            print("        INFO- ----- 选择神罚副本")
            Preset_Group, Preset_name = "副本编组", "魂王编队"
            Fuben_Name = "神罚"
            Fuben_Group_Name = "御魂"
            Fuben_Group = "./pic/Thr/御魂副本组别.png"
            Fuben_Group_card = "./pic/Thr/御魂组别选项.png"
            Fuben_Img0 = "./pic/Thr/神罚副本图标0.png"
            Fuben_Img1 = "./pic/Thr/神罚副本图标1.png"
            Buff = 1
    for step in range(30):
        Sleep_print(1)
        match current_state:
            case "御魂装配":
                for i in range(2):
                    print("    切换到 ", Account[i], " 账号")
                    print("        INFO- -----", Account[i], "装配", Preset_name)
                    Team_Preset(Hwnd[i], Preset_Group, Preset_name)
                    Itface_scroll(Hwnd[i])
                print("        STEP- vvvvv 跳转庭院界面")
                current_state = "庭院界面"
            case "庭院界面":
                print("    切换到 ", Account[1], " 账号")
                Find = Find_Click_windows(Hwnd[1], "./pic/Thr/组队图标.png", 0.05, "点击组队图标", "未找到组队图标")
                if Find:
                    print("        STEP- vvvvv 跳转组队界面")
                    current_state = "组队界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "组队界面":
                Range, Matchs = Find_in_windows_Matchs(Hwnd[1], Fuben_Group, 0.05, 0)
                if Range:
                    print("        INFO-", Matchs, "正在", Fuben_Group_Name, "副本组别内")
                    print("        STEP- vvvvv 跳转副本组别界面")
                    current_state = "副本组别界面"
                else:
                    print("        INFO-", Matchs, "目前不正在", Fuben_Group_Name, "副本组别内")
                    for i in range(5):
                        Massage1 = "点击", Fuben_Group_Name, "组别选项"
                        Massage2 = "未找到", Fuben_Group_Name, "组别选项"
                        Find = Find_Click_windows(Hwnd[1], Fuben_Group_card, 0.01, Massage1, Massage2)
                        Find = Find_Click_windows(Hwnd[1], Fuben_Group_card, 0.01, Massage1, Massage2)
                        if Find:
                            print("        STEP- vvvvv 跳转副本组别界面")
                            current_state = "副本组别界面"
                            break
                        else:
                            Range, Matchs = Find_in_windows_Matchs(Hwnd[1], "./pic/Thr/副本组别表头.png", 0.05, 0)
                            print("        INFO-", Matchs, "转到副本组别表头位置")
                            Move_to_range(Hwnd[1], Range)
                            Scroll_print(Hwnd[1], 1)
                    if not Find:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"
            case "副本组别界面":
                Range, Matchs = Find_in_windows_Matchs(Hwnd[1], Fuben_Img0, 0.01, 0)
                if Range:
                    print("        INFO-", Matchs, "正处在", Fuben_Name, "副本内")
                    print("        STEP- vvvvv 跳转阴阳寮频道")
                    current_state = "阴阳寮频道"
                else:
                    print("        INFO-", Matchs, "并未处在", Fuben_Name, "副本内")
                    for i in range(3):
                        Massage1 = "点击", Fuben_Name, "副本图标"
                        Massage2 = "未找到", Fuben_Name, "副本图标"
                        Find = Find_Click_windows(Hwnd[1], Fuben_Img1, 0.01, Massage1, Massage2)
                        if Find:
                            print("        STEP- vvvvv 跳转阴阳寮频道")
                            current_state = "阴阳寮频道"
                            break
                        else:
                            Range, Matchs = Find_in_windows_Matchs(Hwnd[1], "./pic/Thr/副本表头.png", 0.05, 0)
                            print("        INFO-", Matchs, "转到副本表头位置")
                            Move_to_range(Hwnd[1], Range)
                            Scroll_print(Hwnd[1], -5)
                    if not Find:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"
            case "阴阳寮频道":
                print("    切换到 ", Account[0], " 账号")
                Itface_Host(Hwnd[0])
                Find = Find_Click_windows(Hwnd[0], "./pic/Thr/频道.png", 0.05, "点击频道图标", "未找到频道图标")
                if Find:
                    Find = Find_Click_windows(Hwnd[0], "./pic/Thr/阴阳寮频道.png", 0.05, "选择阴阳寮频道", "未找到阴阳寮频道选项 似乎已在其中")
                    print("        STEP- vvvvv 跳转创建队伍")
                    current_state = "创建队伍"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "创建队伍":
                print("    切换到 ", Account[1], " 账号")
                Find = Find_Click_windows(Hwnd[1], "./pic/Thr/创建队伍.png", 0.01, "点击创建队伍", "未找到创建队伍图标")
                if Find:
                    Find_Click_windows(Hwnd[1], "./pic/Thr/创建.png", 0.01, "点击创建", "未找到创建图标")
                    print("        STEP- vvvvv 跳转加入队伍")
                    current_state = "加入队伍"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "加入队伍":
                print("    切换到 ", Account[0], " 账号")
                Find = Find_Click_windows(Hwnd[0], "./pic/Thr/点击加入.png", 0.01, "点击加入队伍", "未找到点击加入")
                if Find:
                    if Buff:
                        print("        STEP- vvvvv 跳转加成")
                        current_state = "加成"
                    else:
                        print("        STEP- vvvvv 跳转小纸人设置")
                        current_state = "小纸人设置"
                else:
                    print("        STEP- vvvvv 跳转重新创建队伍")
                    current_state = "重新创建队伍"
            case "重新创建队伍":
                Itface_Host(Hwnd[0])
                print("    切换到 ", Account[1], " 账号")
                Esc_print(Hwnd[1])
                Sleep_print(1)
                Find = Find_Click_windows(Hwnd[1], "./pic/Main/Queding.png", 0.03, "点击确定", "未找到确定图标")
                Itface_Host(Hwnd[1])
                if Find:
                    print("        STEP- vvvvv 跳转庭院界面")
                    current_state = "庭院界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "加成":
                for i in range(2):
                    print("    切换到 ", Account[i], " 账号")
                    print("        INFO- -----", Account[i], "开启加成")
                    Find_Click_windows(Hwnd[i], "./pic/Thr/加成.png", 0.05, "点击加成", "未找到加成图标")
                    Range, Matchs = Find_in_windows_Matchs(Hwnd[i], "./pic/Thr/御魂加成区域.png", 0.05, 0)
                    if Range:
                        print("        INFO-", Matchs, "识别到加成区域")
                        Find, Matchs = Find_in_windows_Range(Hwnd[i], Range, "./pic/Thr/加成开启按钮.png", 0.05, 0)
                        Click(Hwnd[i], Find, 1)
                        print("        INFO-", Matchs, "打开加成")
                        Find_Click_windows(Hwnd[i], "./pic/Thr/加成1.png", 0.05, "关闭加成面板", "关闭加成面板失败")
                    else:
                        Find_Click_windows(Hwnd[i], "./pic/Thr/加成.png", 0.05, "点击加成", "未找到加成图标")
                if Range:
                    print("        STEP- vvvvv 跳转小纸人设置")
                    current_state = "小纸人设置"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "小纸人设置":
                for i in range(2):
                    print("    切换到 ", Account[i], " 账号")
                    Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人图标.png", 0.05, "点击小纸人图标", "未找到小纸人图标")
                    Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数.png", 0.01, "点击小纸人计数", "未找到小纸人计数图标")
                    match Times:
                        case 30:
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数3.png", 0.01, "点击小纸人计数3", "未找到小纸人计数3图标")
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数0.png", 0.01, "点击小纸人计数0", "未找到小纸人计数0图标")
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数确定.png", 0.01, "点击小纸人计数确定", "未找到小纸人计数确定图标")
                    Find = Find_Click_windows(Hwnd[i], "./pic/Thr/退出0.png", 0.05, "点击退出", "未找到退出图标")
                    if Find:
                        print("        STEP- vvvvv 跳转自动挑战")
                        current_state = "自动挑战"
                    else:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"
            case "自动挑战":
                for i in range(2):
                    print("    切换到 ", Account[i], " 账号")
                    Find = Find_Click_windows(Hwnd[i], "./pic/Thr/自动战斗图标.png", 0.05, "点击自动战斗", "未找到自动战斗图标")
                    Range, Matchs = Find_in_windows_Matchs(Hwnd[i], "./pic/Thr/取消图标.png", 0.05, 0)
                    if Range:
                        print("        INFO-", Matchs, "取消继续计数")
                        Click(Hwnd[i], Range, 1)
                    else:
                        print("        INFO-", Matchs, "未检测到继续计数确认")
                if Find:
                    print("        STEP- vvvvv 跳转战斗")
                    current_state = "战斗"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "战斗":
                Sleep_print(6)
                Find_Click_windows(Hwnd[0], "./pic/Thr/收起频道框.png", 0.05, "点击收起频道框", "未找到收起频道框图标")

                ################### 理论上后续需要跑完任务后的处理
                return 1

            case "异常退出":
                Itface_Host(Hwnd[0])
                Itface_Host(Hwnd[1])
                return 0
