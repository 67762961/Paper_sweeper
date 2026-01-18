from datetime import datetime, time
from Lib import (
    Find_windows,
    Find_in_windows_Matchs,
    Find_Click_windows,
    Itface_Host,
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
    Itface_explore,
)


def FullTask_Thirty():
    """
    寮三十主任务
    """
    print("        ")
    print("TASK- ----- 开始执行寮三十任务 --------------------------------------------------------------")
    current_time = datetime.now()
    if time(9, 0) <= current_time.time() <= time(23, 00):
        print("TASK- ----- 当前时间在9:00-23:00之间 可以执行寮三十任务")
        config_data = read_config("./config/Last_times.yml")
        Account = list(config_data.keys())
        Flag = {}
        for i in range(2):
            print("        TIME- ----- 读取上次账号", Account[i], "完成寮三十任务时间")
            Times_liaosanshi = check_lasttime(Account[i], "寮三十")
            Flag[i] = current_time.date() == Times_liaosanshi.date()
        # 如果两个账号都未做寮三十 则进行寮三十任务
        Hwnd = {}
        if not (Flag[0] and Flag[1]):
            if MainTask_Thirty():
                today = datetime.now()
                week_day = today.weekday()
                if week_day == 0:
                    print("        INFO- ----- 今天是星期一 开始执行真蛇任务")
                    MainTask_Real_Snake()
        else:
            for i in range(2):
                print("        SKIP- ----- 今日账号", Account[i], "已完成寮三十任务 跳过")
    else:
        print("TASK- ----- 时间不在9:00-23:00之间 跳过")
    print("TASK- ----- 寮三十任务已完成 ----------------------------------------------------------------")


def MainTask_Real_Snake():
    config_data = read_config("./config/Last_times.yml")
    Accounts = list(config_data.keys())
    Account1 = Accounts[0]
    Account2 = Accounts[1]
    Hwnd1 = Find_windows(Accounts[0])
    Hwnd2 = Find_windows(Accounts[1])
    Hwnd = [Hwnd1, Hwnd2]
    for Account in Accounts:
        print("    切换到 ", Account, " 账号")
        print("        TIME- ----- 读取上次账号", Account, "完成真蛇时间")
        Times_zhenshe = check_lasttime(Account, "真蛇")
        current_time = datetime.now()
        if Times_zhenshe.date() != current_time.date():
            if Real_Snake("御魂装配", Hwnd, Accounts):
                # 更新配置 写入当前时间
                config = read_config("./config/Last_times.yml")
                Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                config[Account]["真蛇"] = Now
                write_config("./config/Last_times.yml", config)
                print("        TIME- ----- 本次真蛇完成时间")
                print("        TIME- ----- ", Now)
                print("        TASK- ----- 真蛇任务完成")
            else:
                print("        TASK- ----- 真蛇任务执行过程中出现错误 中断任务")
        else:
            print("        SKIP- ----- 今日已完成真蛇任务 跳过")

        Hwnd = [Hwnd2, Hwnd1]
        Accounts = [Account2, Account1]


def MainTask_Thirty():
    config_data = read_config("./config/Last_times.yml")
    config = read_config("./config/Setting.yml")
    Account = {}
    Account[0] = config["寮三十"]["主账号"]
    Account[1] = config["寮三十"]["副账号"]

    print("        TASK- ----- 开始执行寮三十任务")
    Hwnd = {}
    Hwnd[0] = Find_windows(Account[0])
    Hwnd[1] = Find_windows(Account[1])
    if Task_Liao_30(Hwnd[0], Hwnd[1], Account):
        # 更新配置 写入当前时间
        config = read_config("./config/Last_times.yml")
        Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config[Account[0]]["寮三十"] = Now
        config[Account[1]]["寮三十"] = Now
        write_config("./config/Last_times.yml", config)
        print("        TIME- ----- 本次寮三十完成时间")
        print("        TIME- ----- ", Now)
        print("        TASK- ----- 寮三十任务完成")
        return 1
    else:
        print("        TASK- ----- 寮三十任务执行过程中出现错误 中断任务")
        return 0


def Task_Liao_30(Hwnd1, Hwnd2, Account):
    """
    挑战寮三十
    """
    config = read_config("./config/Setting.yml")
    today = datetime.now()
    week_day = today.weekday()
    week_list = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    print("        TIME- ----- 今天是", week_list[week_day])
    Fuben = config["寮三十"]["副本"][week_day]
    Times = config["寮三十"]["次数"][week_day]
    if Times == 0:
        print("        INFO- ----- 副本次数为 0 次 无需执行寮三十任务")
        return 0

    Return = Yuhun(Hwnd1, Hwnd2, Account, Fuben, Times)

    return Return


def Yuhun(Hwnd1, Hwnd2, Account, Fuben, Times):
    """
    御魂副本寮三十
    """
    Hwnd = [Hwnd1, Hwnd2]
    current_state = "结束界面"
    match Fuben:
        case "魂虚":
            print("        INFO- ----- 选择魂虚副本", Times, "次")
            Preset_Group, Preset_name = "副本编组", "魂虚编队"
            Fuben_Name = "虚无"
            Fuben_Group_Name = "御魂"
            Fuben_Group = "./pic/Thr/御魂副本组别.png"
            Fuben_Group_card = "./pic/Thr/御魂组别选项.png"
            Fuben_Img0 = "./pic/Thr/虚无副本图标0.png"
            Fuben_Img1 = "./pic/Thr/虚无副本图标1.png"
            Tuichutubiao = "./pic/Thr/退出0.png"
            Zidongzhandoutubiao = "./pic/Thr/自动战斗图标.png"
            Buff = 1
        case "魂王":
            print("        INFO- ----- 选择神罚副本", Times, "次")
            Preset_Group, Preset_name = "副本编组", "魂王编队"
            Fuben_Name = "神罚"
            Fuben_Group_Name = "御魂"
            Fuben_Group = "./pic/Thr/御魂副本组别.png"
            Fuben_Group_card = "./pic/Thr/御魂组别选项.png"
            Fuben_Img0 = "./pic/Thr/神罚副本图标0.png"
            Fuben_Img1 = "./pic/Thr/神罚副本图标1.png"
            Tuichutubiao = "./pic/Thr/退出0.png"
            Zidongzhandoutubiao = "./pic/Thr/自动战斗图标.png"
            Buff = 1
        case "魂海":
            print("        INFO- ----- 选择魂海四副本", Times, "次")
            Preset_Group, Preset_name = "副本编组", "魂海编队"
            Fuben_Name = "魂海"
            Fuben_Group_Name = "永生之海"
            Fuben_Group = "./pic/Thr/永生之海组别.png"
            Fuben_Group_card = "./pic/Thr/永生之海组别选项.png"
            Fuben_Img0 = "./pic/Thr/永生之海四副本图标0.png"
            Fuben_Img1 = "./pic/Thr/永生之海四副本图标1.png"
            Tuichutubiao = "./pic/Thr/退出00.png"
            Zidongzhandoutubiao = "./pic/Thr/自动战斗图标魂海.png"
            Buff = 0
        case "日蚀":
            print("        INFO- ----- 选择日轮副本", Times, "次")
            Preset_Group, Preset_name = "副本编组", "日轮编队"
            Fuben_Name = "日蚀"
            Fuben_Group_Name = "日轮之陨"
            Fuben_Group = "./pic/Thr/日轮副本组别.png"
            Fuben_Group_card = "./pic/Thr/日轮之陨组别选项.png"
            Fuben_Img0 = "./pic/Thr/日蚀副本图标0.png"
            Fuben_Img1 = "./pic/Thr/日蚀副本图标1.png"
            Tuichutubiao = "./pic/Thr/退出0.png"
            Zidongzhandoutubiao = "./pic/Thr/自动战斗图标.png"
            Buff = 0
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
                        Massage1 = "点击" + Fuben_Group_Name + "组别选项"
                        Massage2 = "未找到" + Fuben_Group_Name + "组别选项"
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
                        Massage1 = "点击" + Fuben_Name + "副本图标"
                        Massage2 = "未找到" + Fuben_Name + "副本图标"
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
                Range, Matchs = Find_in_windows_Matchs(Hwnd[1], "./pic/Thr/邀请好友和寮成员.png", 0.01, 0)
                if Range:
                    Click(Hwnd[1], Range, 1)
                    print("        INFO-", Matchs, "选择邀请好友和寮成员")
                else:
                    print("        INFO-", Matchs, "已经选择邀请好友和寮成员")
                if Find:
                    Find_Click_windows(Hwnd[1], "./pic/Thr/创建.png", 0.01, "点击创建", "未找到创建图标")
                    print("        STEP- vvvvv 跳转加入队伍")
                    current_state = "加入队伍"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "加入队伍":
                print("    切换到 ", Account[0], " 账号")
                Find = Find_Click_windows(Hwnd[0], "./pic/Thr/点击加入.png", 0.03, "点击加入队伍", "未找到点击加入")
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
                        case 1:
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数1.png", 0.01, "点击小纸人计数1", "未找到小纸人计数1图标")
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数确定.png", 0.01, "点击小纸人计数确定", "未找到小纸人计数确定图标")
                        case 30:
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数3.png", 0.01, "点击小纸人计数3", "未找到小纸人计数3图标")
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数0.png", 0.01, "点击小纸人计数0", "未找到小纸人计数0图标")
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数确定.png", 0.01, "点击小纸人计数确定", "未找到小纸人计数确定图标")
                        case 50:
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数5.png", 0.01, "点击小纸人计数5", "未找到小纸人计数5图标")
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数0.png", 0.01, "点击小纸人计数0", "未找到小纸人计数0图标")
                            Find_Click_windows(Hwnd[i], "./pic/Thr/小纸人计数确定.png", 0.01, "点击小纸人计数确定", "未找到小纸人计数确定图标")
                    Find = Find_Click_windows(Hwnd[i], Tuichutubiao, 0.05, "点击退出", "未找到退出图标")
                    if Find:
                        print("        STEP- vvvvv 跳转自动挑战")
                        current_state = "自动挑战"
                    else:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"
            case "自动挑战":
                for i in range(2):
                    print("    切换到 ", Account[i], " 账号")
                    Find = Find_Click_windows(Hwnd[i], Zidongzhandoutubiao, 0.05, "点击自动战斗", "未找到自动战斗图标")
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
                Sleep_print(7)
                Find_Click_windows(Hwnd[0], "./pic/Thr/收起频道框.png", 0.05, "点击收起频道框", "未找到收起频道框图标")
                print("        INFO-", Matchs, "开始等待战斗结束")
                Sleep_print(30)
                for Wait in range(120):
                    Range, Match = Find_in_windows_Matchs(Hwnd[0], "./pic/Thr/取消图标.png", 0.05, 0)
                    if Range:
                        print("        INFO-", Match, "检测到结束")
                        for i in range(2):
                            print("    切换到 ", Account[i], " 账号")
                            Find_Click_windows(Hwnd[i], "./pic/Thr/取消图标.png", 0.05, "点击取消继续", "未找到取消图标")
                        print("        STEP- vvvvv 跳转结束界面")
                        current_state = "结束界面"
                        break
                    else:
                        print("        INFO-", Match, "未检测到结束")
                        print("        WAIT- wwwww 等待准备 已等待 {waittime} 分钟".format(waittime=(Wait + 1) * 0.5))
                        Sleep_print(30)
                    print("        INFO- 等待轮耗尽 尝试再次进入等待轮")
                    current_state = "结束界面"
            case "结束界面":
                print("    切换到 ", Account[1], " 账号")
                Find_Click_windows(Hwnd[1], "./pic/Thr/取消图标.png", 0.05, "点击取消继续邀请", "未找到取消图标")
                Sleep_print(1)
                for i in range(2):
                    print("    切换到 ", Account[i], " 账号")
                    Itface_Host(Hwnd[i])
                    if Buff:
                        Find_Click_windows(Hwnd[i], "./pic/Thr/庭院加成.png", 0.05, "点击加成", "未找到加成图标")
                        Find_Click_windows(Hwnd[i], "./pic/Thr/关闭加成.png", 0.05, "点击关闭加成", "未找到关闭加成")
                        Esc_print(Hwnd[i])
                        Itface_Host(Hwnd[i])
                return 1
            case "异常退出":
                Itface_Host(Hwnd[0])
                Itface_Host(Hwnd[1])
                return 0
    print("        STEP- vvvvv 状态机轮次耗尽")
    return 0


def Real_Snake(current_state, Hwnd, Account):
    """
    真蛇
    """
    for step in range(30):
        Sleep_print(1)
        match current_state:
            case "御魂装配":
                for i in range(2):
                    print("    切换到 ", Account[i], " 账号")
                    print("        INFO- -----", Account[i], "装配", "真蛇编队")
                    Team_Preset(Hwnd[i], "日常编组", "真蛇编队")
                    Itface_scroll(Hwnd[i])
                print("        STEP- vvvvv 跳转探索界面")
                current_state = "探索界面"
            case "探索界面":
                print("    切换到 ", Account[0], " 账号")
                Itface_explore(Hwnd[0])
                Range, Match = Find_in_windows_Matchs(Hwnd[0], "./pic/Thr/真蛇图标.png", 0.05, 0)
                if Range:
                    print("        INFO-", Match, "检测到真蛇副本图标")
                    Click(Hwnd[0], Range, 1)
                    print("        STEP- vvvvv 跳转阴阳寮频道")
                    current_state = "阴阳寮频道"
                else:
                    print("        INFO-", Match, "未检测到真蛇副本图标 跳过真蛇任务")
                    return 0
            case "阴阳寮频道":
                print("    切换到 ", Account[1], " 账号")
                Itface_Host(Hwnd[1])
                Find = Find_Click_windows(Hwnd[1], "./pic/Thr/频道.png", 0.05, "点击频道图标", "未找到频道图标")
                if Find:
                    Find = Find_Click_windows(Hwnd[1], "./pic/Thr/阴阳寮频道.png", 0.05, "选择阴阳寮频道", "未找到阴阳寮频道选项 似乎已在其中")
                    print("        STEP- vvvvv 跳转创建队伍")
                    current_state = "创建队伍"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "创建队伍":
                print("    切换到 ", Account[0], " 账号")
                Find_Click_windows(Hwnd[0], "./pic/Thr/真蛇挑战图标.png", 0.05, "点击真蛇挑战图标", "未找到真蛇挑战图标")
                Find_Click_windows(Hwnd[0], "./pic/Main/Queding.png", 0.03, "点击确定", "未找到确定图标")
                Sleep_print(0.5)
                Range, Matchs = Find_in_windows_Matchs(Hwnd[0], "./pic/Thr/邀请好友和寮成员.png", 0.03, 0)
                if Range:
                    Click(Hwnd[1], Range, 1)
                    print("        INFO-", Matchs, "选择邀请好友和寮成员")
                else:
                    print("        INFO-", Matchs, "已经选择邀请好友和寮成员")
                Find_Click_windows(Hwnd[0], "./pic/Thr/真蛇队伍创建图标.png", 0.01, "点击创建队伍", "未找到创建队伍图标")
                print("        STEP- vvvvv 跳转加入队伍")
                current_state = "加入队伍"
            case "加入队伍":
                print("    切换到 ", Account[1], " 账号")
                Find = Find_Click_windows(Hwnd[1], "./pic/Thr/点击加入.png", 0.01, "点击加入队伍", "未找到点击加入")
                if Find:
                    Find_Click_windows(Hwnd[1], "./pic/Main/Queding.png", 0.03, "点击确定", "未找到确定图标")
                    print("        STEP- vvvvv 跳转准备挑战")
                    current_state = "准备挑战"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"
            case "准备挑战":
                print("    切换到 ", Account[0], " 账号")
                Find_Click_windows(Hwnd[0], "./pic/Thr/真蛇挑战.png", 0.03, "点击挑战", "未找到挑战图标")
                Sleep_print(2)
                print("    切换到 ", Account[1], " 账号")
                Find_Click_windows(Hwnd[1], "./pic/Thr/收起频道框.png", 0.05, "点击收起频道框", "未找到收起频道框图标")
                for i in range(2):
                    print("    切换到 ", Account[i], " 账号")
                    Find_Click_windows(Hwnd[i], "./pic/Thr/真蛇准备.png", 0.03, "点击准备", "未找到准备图标")
                Sleep_print(1)
                print("        STEP- vvvvv 跳转战斗阶段")
                current_state = "战斗阶段"
            case "战斗阶段":
                for i in range(2):
                    print("    切换到 ", Account[i], " 账号")
                    Find_Click_windows(Hwnd[i], "./pic/Thr/真蛇自动准备.png", 0.03, "点击自动准备", "未找到自动准备图标")
                print("        INFO- ----- 开始等待战斗")
                Sleep_print(100)
                for Wait in range(10):
                    Range, Match = Find_in_windows_Matchs(Hwnd[0], "./pic/Digui/Zhandoujiangli.png", 0.05, 0)
                    if not Range:
                        Range, Match = Find_in_windows_Matchs(Hwnd[0], "./pic/Thr/真蛇确定.png", 0.05, 0)
                    if Range:
                        print("        INFO-", Match, "检测到战斗奖励")
                        for i in range(2):
                            print("    切换到 ", Account[i], " 账号")
                            Find = Find_Click_windows(Hwnd[i], "./pic/Digui/Zhandoujiangli.png", 0.05, "点击战斗奖励", "未检测到战斗奖励图标")
                            if not Find:
                                Find_Click_windows(Hwnd[i], "./pic/Thr/真蛇确定.png", 0.05, "点击确定", "未检测到确定图标")
                                Sleep_print(1)
                                Find_Click_windows(Hwnd[i], "./pic/Digui/Zhandoujiangli.png", 0.05, "点击战斗奖励", "未检测到战斗奖励图标")
                        print("        STEP- vvvvv 跳转结束界面")
                        current_state = "结束界面"
                        break
                    else:
                        print("        INFO-", Match, "未检测到结束")
                        print("        WAIT- wwwww 等待准备 已等待 {waittime} 秒".format(waittime=(Wait * 10 + 100)))
                        Sleep_print(10)
            case "结束界面":
                for i in range(2):
                    print("    切换到 ", Account[i], " 账号")
                    Itface_Host(Hwnd[i])
                return 1
    print("        STEP- vvvvv 状态机轮次耗尽")
    return 0
