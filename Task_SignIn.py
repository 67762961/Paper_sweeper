from datetime import datetime, timedelta
from Lib import Find_in_windows_Matchs, Find_windows, Find_Click_windows, Click, Itface_Host, read_config, write_config, Itface_scroll, check_lasttime, Sleep_print, Esc_print, run_accounts_task, ready_daily, ready_after


def MainTask_Signin():
    """
    完成每日登录所有领取项
    @param Hwnd:    窗口句柄
    """

    MainTask_Mail()

    MainTask_Qiandao()

    MainTask_Fudai()

    MainTask_Zhiren()

    MainTask_mianfeilibao()

    MainTask_youqingdain()


def MainTask_Mail():
    """
    邮件主任务
    """
    run_accounts_task(
        "邮件领取", ready_after(1),
        work=lambda Account: Work_Mail(Find_windows(Account), Account),
    )


def Work_Mail(Hwnd, Account):
    """
    领取邮件奖励
    :param Hwnd:    窗口句柄
    :return:        1为正常 0为异常
    """
    Itface_Host(Hwnd)

    Find_Click_windows(Hwnd, "./pic/signin/Youjian.png", 0.05, "点击邮件", "未识别到邮件入口")

    # 检测邮箱界面
    if not Find_Click_windows(Hwnd, "./pic/signin/Youxiang.png", 0.1, "检测到进入邮箱", "进入邮箱异常"):
        Itface_Host(Hwnd)
        return 0

    # 检测是否有奖励未领取
    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/signin/Quanbulingqu.png", 0.05, 0)

    # 没有奖励未领取 检测消息邮件 然后返回
    if not Range:
        print("        INFO-", Matchs, "没有奖励未领取")
        # 检测消息邮件
        while 1:
            if not Find_Click_windows(Hwnd, "./pic/signin/Xiaoxiyoujian.png", 0.05, "发现消息邮件", "未发现消息邮件"):
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
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/signin/Quanbulingqujiemian.png", 0.05, 0)
        if Range:
            print("        INFO-", Matchs, "检测到进入领取界面")
        else:
            print("        INFO-", Matchs, "未正常领取")
            Sleep_print(1)
            Itface_Host(Hwnd)
            return 0

        # 点击确定
        Find_Click_windows(Hwnd, "./pic/common/确定.png", 0.05, "点击确定", "未正常领取确认")
        Sleep_print(2)
        # 检测领取
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
        if Range:
            print("        INFO-", Matchs, "领取成功")
            # 按下esc退出
            Esc_print(Hwnd)
            Sleep_print(2)

            # 检测万华牌
            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/signin/万华牌跳过.png", 0.05, 0)
            if Range:
                Click(Hwnd, Range, 1)
                print("        INFO-", Matchs, "领取万华牌")
                Find_Click_windows(Hwnd, "./pic/common/关闭.png", 0.05, "点击关闭", "未正常关闭万华牌")
            else:
                print("        INFO-", Matchs, "未检测到万华牌")

            # 检测消息邮件
            for i in range(10):
                Find = Find_Click_windows(Hwnd, "./pic/signin/Xiaoxiyoujian.png", 0.05, "点击消息邮件", "未发现消息邮件")
                if not Find:
                    break

            Esc_print(Hwnd)
            Itface_Host(Hwnd)
            return 1

        Itface_Host(Hwnd)
        return 0


def MainTask_Fudai():
    """
    福袋主任务
    """
    run_accounts_task(
        "福袋纸人", ready_daily,
        work=lambda Account: Fudai(Find_windows(Account), Account),
    )


def Fudai(Hwnd, Account):
    """
    每日福袋
    """
    Itface_Host(Hwnd)
    # 检测福袋小纸人
    if Find_Click_windows(Hwnd, "./pic/signin/Fudaixiaozhiren.png", 0.05, "检测到福袋小纸人", "未检测到福袋小纸人"):
        # 点击福袋小人后检测领取状态
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
        if Range:
            print("        INFO-", Matchs, "福袋领取成功")
            Esc_print(Hwnd)
            Sleep_print(0.5)
            return 1
        else:
            print("        INFO-", Matchs, "福袋似乎未领取成功")
            return 0
    else:
        return 0


def MainTask_Qiandao():
    """
    签到主任务
    """
    run_accounts_task(
        "每日一签", ready_daily,
        work=lambda Account: Qiandao(Find_windows(Account), Account),
    )


def Qiandao(Hwnd, Account):
    """
    每日签到
    """
    Itface_Host(Hwnd)
    Wait = 0
    for i in range(5):
        # 检测签小纸人
        if Find_Click_windows(Hwnd, "./pic/signin/Qiandaoxiaozhiren.png", 0.07, "检测到签到小纸人", "未检测到签到小纸人"):
            # 点击签到小人后
            Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/signin/Meiriyiqian.png", 0.05, 0)
            if Find:
                print("        INFO-", Matchs, "每日一签")
                Click(Hwnd, Find, 1)
                for i in range(2):
                    Sleep_print(0.5)
                    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/signin/Jieqianxiaozhiren.png", 0.05, 0)
                    if Range:
                        print("        INFO-", Matchs, "检测到解签小纸人 每日一签成功")
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                        return 1
                    else:
                        print("        INFO-", Matchs, "未检测到解签小纸人")
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/signin/Jieqianxiaozhiren.png", 0.05, 0)
                        if Range:
                            print("        INFO-", Matchs, "检测到解签小纸人 每日一签成功")
                            Esc_print(Hwnd)
                            Sleep_print(0.5)
                            return 1
            else:
                print("        INFO-", Matchs, "未检测到每日一签界面")
                Itface_Host(Hwnd)
                return 0
        else:
            Sleep_print(0.1)
    return 0


def MainTask_Zhiren():
    """
    纸人奖励主任务
    """
    # 纸人奖励不写回时间，因此 ready=None（硬跑）+ write_back=False
    run_accounts_task(
        "纸人奖励", None,
        work=lambda Account: zhirenjiangli(Find_windows(Account)),
        write_back=False,
    )


def zhirenjiangli(Hwnd):
    """
    体力小纸人 勾玉小纸人 buff小纸人
    """
    Itface_Host(Hwnd)

    # 检测体力小纸人
    if Find_Click_windows(Hwnd, "./pic/signin/Tilixiaozhire.png", 0.07, "检测到体力小纸人", "未检测到体力小纸人"):
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
        print("        INFO-", Matchs, "体力纸人领取成功")

        Esc_print(Hwnd)
        Sleep_print(0.5)

    # 检测勾玉小纸人
    if Find_Click_windows(Hwnd, "./pic/signin/Gouyuxiaozhiren.png", 0.07, "检测到勾玉小纸人", "未检测到勾玉小纸人"):
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
        print("        INFO-", Matchs, "勾玉纸人领取成功")

        Esc_print(Hwnd)
        Sleep_print(0.5)

    # 检测buff小纸人
    if Find_Click_windows(Hwnd, "./pic/signin/BUFFxiaozhiren.png", 0.07, "检测到BUFF小纸人", "未检测到BUFF小纸人"):
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
        print("        INFO-", Matchs, "BUFF纸人领取成功")

        Esc_print(Hwnd)
        Sleep_print(0.5)

    return 1


def MainTask_mianfeilibao():
    """
    商店免费礼包主任务
    """
    run_accounts_task(
        "免费礼包", ready_daily,
        work=lambda Account: mianfeilibao(Find_windows(Account), Account),
    )


def mianfeilibao(Hwnd, Account):
    """
    商店免费礼包
    """
    Itface_Host(Hwnd)
    # 开卷轴
    Itface_scroll(Hwnd)
    for i in range(1):
        if not Find_Click_windows(Hwnd, "./pic/signin/Shangdian.png", 0.05, "进入商店", "未检测到商店"):
            break
        if not Find_Click_windows(Hwnd, "./pic/signin/Libaowu.png", 0.05, "进入礼包屋", "未检测到礼包屋"):
            if not Find_Click_windows(Hwnd, "./pic/signin/Libaowu1.png", 0.05, "进入礼包屋", "未检测到礼包屋"):
                break

        # 此步骤有时候可跳过
        Find_Click_windows(Hwnd, "./pic/signin/Richang.png", 0.05, "进入日常项", "未检测到日常项")

        if Find_Click_windows(Hwnd, "./pic/signin/Mianfei.png", 0.05, "领取免费礼包", "未检测到免费礼包"):
            # 检测领取状态
            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
            if Range:
                print("        INFO-", Matchs, "免费礼包领取成功")
                Esc_print(Hwnd)
                Sleep_print(0.5)
                # 返回庭院
                Esc_print(Hwnd)
                Sleep_print(0.5)
                Esc_print(Hwnd)
                Sleep_print(0.5)
                Itface_Host(Hwnd)
                return 1
            else:
                print("        INFO-", Matchs, "免费礼包似乎未领取成功")
                Esc_print(Hwnd)
                Sleep_print(0.5)
                # 返回庭院
                Esc_print(Hwnd)
                Sleep_print(0.5)
                Esc_print(Hwnd)
                Sleep_print(0.5)
                return 0
    return 0


def MainTask_youqingdain():
    """
    友情点主任务
    """
    run_accounts_task(
        "送友情点", ready_daily,
        work=lambda Account: youqingdain(Find_windows(Account), Account),
    )


def youqingdain(Hwnd, Account):
    """
    每日友情点以及吉闻祝福
    """
    Itface_Host(Hwnd)
    # 开卷轴
    Itface_scroll(Hwnd)
    current_state = "庭院"
    flag_jiwen = 0
    flag_youqingdian = 0
    for i in range(10):
        match current_state:
            case "庭院":
                Find = Find_Click_windows(Hwnd, "./pic/signin/Haoyou.png", 0.05, "进入好友界面", "未检测到好友界面")
                if Find:
                    current_state = "好友界面"
                    Sleep_print(2)
                else:
                    current_state = "end"
            case "好友界面":
                if not flag_jiwen:
                    Find = Find_Click_windows(Hwnd, "./pic/signin/Jiwen.png", 0.05, "进入吉闻界面", "未检测到吉闻界面")
                    if Find:
                        current_state = "吉闻界面"
                    else:
                        current_state = "好友界面"
                else:
                    Find = Find_Click_windows(Hwnd, "./pic/signin/Youqingdianqiehuan.png", 0.05, "进入友情点界面", "未检测到友情点界面")
                    if Find:
                        current_state = "友情点界面"
                    else:
                        current_state = "好友界面"
            case "吉闻界面":
                Find = Find_Click_windows(Hwnd, "./pic/signin/Yijianzhufu.png", 0.05, "一键祝福", "未检测到一键祝福")
                if Find:
                    current_state = "祝福界面"
                else:
                    current_state = "好友界面"
                    flag_jiwen = 1
                    Esc_print(Hwnd)
                    Sleep_print(0.5)
            case "祝福界面":
                Find_Click_windows(Hwnd, "./pic/signin/Zhufu.png", 0.05, "祝福", "未检测到祝福")
                Sleep_print(1)
                Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
                if Find:
                    print("        INFO-", Matchs, "一键祝福成功")
                    flag_jiwen = 1
                    Esc_print(Hwnd)
                    Sleep_print(0.5)
                    Esc_print(Hwnd)
                    Sleep_print(0.5)
                else:
                    print("一键祝福似乎未成功")
                    Esc_print(Hwnd)
                    Sleep_print(0.5)
                    Find = Find_in_windows_Matchs(Hwnd, "./pic/signin/Jiwen.png", 0.05, 0)
                    if not Find:
                        print("退出吉闻界面异常")
                        Esc_print(Hwnd)
                        Sleep_print(0.5)
                    else:
                        print("已正常退出吉闻界面")
                current_state = "好友界面"
            case "友情点界面":
                Find_Click_windows(Hwnd, "./pic/signin/Yijianshouqu.png", 0.05, "一键收取", "未检测到一键收取")
                Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
                if Find:
                    print("        INFO-", Matchs, "一键收取成功")
                    flag_youqingdian = 1
                    Esc_print(Hwnd)
                    Sleep_print(0.5)
                    current_state = "end"
                else:
                    print("一键收取似乎未成功")
            case "end":
                if flag_youqingdian and flag_jiwen:
                    # 退至庭院
                    Esc_print(Hwnd)
                    Sleep_print(0.5)
                    Itface_Host(Hwnd)
                    return 1
    return 0
