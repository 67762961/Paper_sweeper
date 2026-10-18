from datetime import datetime, time
from Lib import Find_windows, Find_in_windows_Matchs, Find_Click_windows, Itface_daily, read_config, write_config, check_lasttime, Esc_print, Sleep_print, run_accounts_task, ready_daily


def MainTask_Fengmo():
    """
    逢魔之时主任务
    """
    run_accounts_task(
        "逢魔之时", ready_daily,
        work=lambda Account: Task_Fengmo(Find_windows(Account), Account),
        window=(time(17, 0), time(21, 50)),
    )


def Task_Fengmo(Hwnd, Account):
    """
    有关逢魔之时相关任务
    :param Hwnd:    窗口句柄
    :param Account: 账号
    """
    print("        INFO- ----- 前往逢魔界面")
    Itface_daily(Hwnd)
    Range = Find_Click_windows(Hwnd, "./pic/fengmo/逢魔图标.png", 0.05, "点击逢魔图标", "未检测到逢魔图标")
    Range = Find_Click_windows(Hwnd, "./pic/courtyard/前往.png", 0.05, "点击前往", "未检测到前往图标")
    if Range:
        Sleep_print(3)
        # 先点封魔再打boss
        meirifengmo(Hwnd)
        if fengmoboss(Hwnd):
            return 1
        ######################################################################################################################
        # 此处进入了打boss场景 应添加后续战斗完成的处理


def meirifengmo(Hwnd):
    for i in range(3):
        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/fengmo/定位.png", 0.06, 0)
        if Find:
            print("        INFO-", Matchs, "已进入逢魔地图界面")
            break
        else:
            print("        INFO-", Matchs, "未进入逢魔地图界面 等待10s")
            Sleep_print(10)

    # 点四下逢魔
    while True:
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/fengmo/逢魔次数.png", 0.03, 0)
        if Range:
            print("        INFO-", Matchs, "还有逢魔次数")
            Find_Click_windows(Hwnd, "./pic/fengmo/现世逢魔.png", 0.07, "点击现世逢魔", "未检测到现世逢魔图标")
            Sleep_print(2.5)
        else:
            print("        INFO-", Matchs, "逢魔次数耗尽")
            break

    # 领取逢魔奖励
    for i in range(3):
        flag = Find_Click_windows(Hwnd, "./pic/fengmo/逢魔奖励.png", 0.05, "点击逢魔奖励", "未检测到现世逢魔奖励")
        if flag:
            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
            if Range:
                print("        INFO-", Matchs, "逢魔奖励领取成功")
                Sleep_print(2)
                Esc_print(Hwnd)
                break
            else:
                print("        INFO-", Matchs, "逢魔奖励领取失败")
        else:
            for j in range(10):
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/fengmo/逢魔奖励已领取.png", 0.05, 0)
                if Range:
                    print("        INFO-", Matchs, "逢魔奖励已经被领取")
                    break
                else:
                    print("        INFO-", Matchs, "逢魔奖励未正确领取")
                    Sleep_print(0.5)
            break


def fengmoboss(Hwnd):
    """
    封魔打boss
    """
    # 初始化
    Sleep_print(1)
    flag_boss = 1
    flag_Ji = True
    found_battle_scene = False
    Find_Click_windows(Hwnd, "./pic/fengmo/定位.png", 0.05, "点击定位", "未检测到定位图标")

    # 找boss循环
    for p in range(4):
        for i in range(2):
            # 优先打逢魔-极
            if flag_Ji:
                Range = Find_Click_windows(Hwnd, "./pic/fengmo/逢魔极.png", 0.05, "点击逢魔-极", "未检测到逢魔-极图标")
                if Range:
                    flag_boss = 1
                    Sleep_print(1)
                    break
            else:
                # 封魔-极检索失败则转为打首领
                if Find_Click_windows(Hwnd, "./pic/fengmo/首领.png", 0.05, "点击首领", "未检测到首领图标"):
                    flag_boss = 0
                    Sleep_print(1)
                    break

        # 集结 简化为只识别一次
        for i in range(1):
            if flag_boss:
                Range = Find_Click_windows(Hwnd, "./pic/fengmo/集结.png", 0.05, "点击集结", "未检测到集结图标")
            else:
                Range = Find_Click_windows(Hwnd, "./pic/fengmo/集结0.png", 0.05, "点击集结", "未检测到集结图标")

            Sleep_print(1)

            if Range:
                if flag_boss:
                    Find_Click_windows(Hwnd, "./pic/fengmo/集结挑战.png", 0.05, "点击集结挑战", "未检测到集结挑战")
                else:
                    Find_Click_windows(Hwnd, "./pic/fengmo/集结挑战1.png", 0.05, "点击集结挑战", "未检测到集结挑战")
                Sleep_print(3)
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/fengmo/阵容预设.png", 0.05, 0)
                if Range:
                    print("        INFO-", Matchs, "已经进入备战场景")
                    found_battle_scene = True
                    return 1
                else:
                    print("        INFO-", Matchs, "未进入备战场景")
                    Esc_print(Hwnd)
                    Sleep_print(0.5)
                    p = 0

        # 两次寻找封魔-极无果就改换首领
        if p == 1:
            flag_Ji = False

    return 0
