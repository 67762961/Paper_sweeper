from datetime import datetime, time
from Lib import Find_windows, Find_in_windows_Matchs, Find_Click_windows, Itface_Host, Itface_explore, read_config, write_config, check_lasttime, Esc_print, Sleep_print, Team_Preset, run_accounts_task, ready_daily


def MainTask_Digui():
    """
    地域鬼王主任务
    """
    run_accounts_task(
        "地域鬼王", ready_daily,
        work=lambda Account: Diyuguiwang("探索界面", Find_windows(Account)),
        window=(time(12, 0), time(23, 50)),
    )


def Diyuguiwang(current_state, Hwnd):
    """
    挑战地域鬼王
    """
    print("        INFO- ----- 装配结界编队")
    Team_Preset(Hwnd, "日常编组", "结界编队")

    print("        INFO- ----- 前往地鬼界面")
    Itface_explore(Hwnd)

    # 地鬼计数器
    flag_digui = 1
    print("        STEP- vvvvv 从{First_state}开始".format(First_state=current_state))
    for step in range(30):
        Sleep_print(1)
        match current_state:
            case "探索界面":
                Find = Find_Click_windows(Hwnd, "./pic/digui/Diguitubiao.png", 0.05, "进入地鬼界面", "未检测到地鬼图标")
                if Find:
                    print("        STEP- vvvvv 跳转地鬼界面")
                    current_state = "地鬼界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "地鬼界面":
                if flag_digui <= 3:
                    Find = Find_Click_windows(Hwnd, "./pic/digui/Shaixuan.png", 0.05, "点击筛选", "未检测到筛选图标 似乎已经在筛选中")
                    if Find:
                        print("        STEP- vvvvv 跳转筛选界面")
                        current_state = "筛选界面"
                    else:
                        print("        STEP- vvvvv 跳转筛选界面")
                        current_state = "筛选界面"
                else:
                    print("        STEP- vvvvv 跳转结束状态")
                    current_state = "结束"

            case "筛选界面":
                Find_Click_windows(Hwnd, "./pic/digui/Remen.png", 0.01, "点击热门", "似乎已经在热门选项中")
                Sleep_print(1)
                match flag_digui:
                    case 1:
                        Find = Find_Click_windows(Hwnd, "./pic/digui/1st.png", 0.05, "点击第一个", "似乎无法挑战第一热门鬼王")
                    case 2:
                        Find = Find_Click_windows(Hwnd, "./pic/digui/2nd.png", 0.05, "点击第二个", "似乎无法挑战第二热门鬼王")
                    case 3:
                        Find = Find_Click_windows(Hwnd, "./pic/digui/3rd.png", 0.05, "点击第三个", "似乎无法挑战第三热门鬼王")

                Sleep_print(1)
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/digui/Zuixin.png", 0.01, 0)
                if Range:
                    print("        INFO-", Matchs, "检测到最新栏 似乎无法挑战热门")
                    Find_Click_windows(Hwnd, "./pic/digui/Zuixin.png", 0.01, "点击最新", "点击最新失败")
                    Find = Find_Click_windows(Hwnd, "./pic/digui/Zuixintiaozhan.png", 0.03, "点击最新挑战", "未检测到最新挑战图标")
                    if Find:
                        print("        STEP- vvvvv 跳转挑战界面")
                        current_state = "挑战界面"
                    else:
                        print("        STEP- vvvvv 似乎已经无挑战次数 跳转结束")
                        Sleep_print(1)
                        Esc_print(Hwnd)
                        Sleep_print(1)
                        current_state = "结束"
                else:
                    print("        INFO-", Matchs, "未检测到最新栏 似乎可以挑战热门")
                    if Find:
                        print("        STEP- vvvvv 跳转挑战界面")
                        current_state = "挑战界面"
                    else:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"

            case "挑战界面":
                Find = Find_Click_windows(Hwnd, "./pic/digui/Tiaozhan.png", 0.05, "点击开始挑战", "未检测到挑战图标")
                if Find:
                    print("        STEP- vvvvv 预设阵容界面")
                    current_state = "预设阵容界面"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "预设阵容界面":
                for i in range(1):
                    Sleep_print(1)
                    if not Find_Click_windows(Hwnd, "./pic/team/Yushedenglong.png", 0.05, "点击预设", "未检测预设图标"):
                        if not Find_Click_windows(Hwnd, "./pic/team/Yushedenglong1.png", 0.05, "再次尝试点击预设", "依旧未检测预设图标"):
                            print("        STEP- vvvvv 跳转异常退出界面")
                            current_state = "异常退出"
                            break

                    Find_Click_windows(Hwnd, "./pic/team/Richangbianzu.png", 0.05, "点击日常编组", "似乎已经在日常编组中")

                    if not Find_Click_windows(Hwnd, "./pic/team/结界队出战.png", 0.05, "点结界队", "未检测到结界队图标"):
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"
                        break

                    if Find_Click_windows(Hwnd, "./pic/team/Chuzhan.png", 0.05, "点击出战", "未检测到出战图标"):
                        print("        STEP- vvvvv 跳转战斗准备阶段")
                        current_state = "战斗准备阶段"

                    else:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"

            case "战斗准备阶段":
                for Wait in range(10):
                    Find = Find_Click_windows(Hwnd, "./pic/digui/Zhunbei.png", 0.07, "点击准备", "未检测到准备图标")
                    if Find:
                        Sleep_print(1)
                        Find_Click_windows(Hwnd, "./pic/digui/Zhunbei.png", 0.07, "再次点击准备", "未检测到准备图标")
                        print("        STEP- vvvvv 跳转战斗阶段")
                        current_state = "战斗阶段"
                        break
                    else:
                        print("        WAIT- wwwww 等待准备 已等待 {waittime} 秒".format(waittime=Wait + 1))
                        Sleep_print(1)
                if not Find:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "战斗阶段":
                Sleep_print(10)
                for Wait in range(60):
                    if Find_Click_windows(Hwnd, "./pic/digui/Shengli.png", 0.05, "点击胜利", "似乎战斗未结束"):
                        Sleep_print(1)
                        Find = Find_Click_windows(Hwnd, "./pic/digui/Zhandoujiangli.png", 0.05, "点击战斗奖励", "未检测到战斗奖励图标")
                        if Find:
                            flag_digui += 1
                            Sleep_print(2)
                            Esc_print(Hwnd)
                            print("        STEP- vvvvv 跳转地鬼界面")
                            current_state = "地鬼界面"
                        else:
                            print("        STEP- vvvvv 跳转异常退出界面")
                            current_state = "异常退出"
                        break
                    else:
                        print("        WAIT- wwwww 等待战斗 已等待 {waittime} 秒".format(waittime=Wait * 5 + 10))
                        Sleep_print(5)

            case "结束":
                Find_Click_windows(Hwnd, "./pic/digui/Jinritioazhan.png", 0.05, "点击今日挑战", "未检测到今日挑战图标")
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/digui/Weixuanze.png", 0.05, 0)
                if Range:
                    print("        INFO-", Matchs, "发现仍然有鬼王挑战次数 继续讨伐地域鬼王")
                    return Diyuguiwang("地鬼界面", Hwnd)
                else:
                    print("        INFO-", Matchs, "似乎已无地域鬼王讨伐次数 任务结束")
                    # 任务结束
                    Itface_Host(Hwnd)
                    return 1

            case "异常退出":
                # 错误结束
                Itface_Host(Hwnd)
                return 0
