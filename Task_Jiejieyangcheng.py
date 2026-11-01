from datetime import datetime, timedelta
from Lib import (
    Find_windows,
    Find_in_windows_Matchs,
    Find_Click_windows,
    Itface_Host,
    Itface_guild,
    read_config,
    write_config,
    check_lasttime,
    Scroll_print,
    Esc_print,
    Sleep_print,
    Sleep_quiet,
    Move_to_range,
    Click,
    Screenshot_window,
    Match_models_in_image,
    Match_models_in_image_all,
    Match_models_rows,
    jiejie_read_yield,
    run_accounts_task,
    ready_after,
    load_jiejie_settings,
    jiejie_card_order,
    jiejie_priority_cards,
    JIEJIE_CARD_LIST_PICS,
    JIEJIE_YIELD_CAP,
    jiejie_card_type,
)


def MainTask_Jiejieyangcheng():
    """
    结界养成主任务
    """
    run_accounts_task(
        "结界养成",
        ready_after(6),
        work=lambda Account: Jiejieyangcheng("庭院界面", Find_windows(Account), Account),
    )


# 寄养列表每次滚动的档位（Scroll_print 的单位是「滚轮格」，一屏约 4 行）。
# 取 6 而不是 3：3 格时相邻两屏有较大重叠，同一行会被反复匹配、重复点开，
# 既慢又浪费。6 格能保证每行都完整经过一次视窗，重叠又比 5 格少。
JIEJIE_SCROLL_STEP = 6


def Jiejieyangcheng(current_state, Hwnd, Account=None):
    """
    结界养成主流程
    :param current_state:   起始界面状态
    :param Hwnd:            窗口句柄
    :param Account:         账号名，用于读取该账号的结界养成配置；
                            None 表示不区分账号，直接按默认值执行
    """
    # 配置在这里读一次往下传：本函数里 Jiejieka / Yucheng 各被调用两次，
    # 让子函数各读一遍不仅浪费，还会在用户中途改配置时前后不一致。
    settings = load_jiejie_settings(Account)
    for warning in settings["warnings"]:
        print("        INFO- ----- 结界养成配置", warning)
    card_order = jiejie_card_order(settings["card"])
    priority_cards = jiejie_priority_cards(settings["priority"])
    print(
        "        INFO- ----- 结界卡放置顺序",
        " → ".join(card_order),
    )
    print(
        "        INFO- ----- 寄养优先级",
        " → ".join(name for name, _ in priority_cards),
    )

    # 重置结束标记
    Finish = 0
    print("        STEP- vvvvv 从{First_state}开始".format(First_state=current_state))
    for step in range(30):
        match current_state:
            case "庭院界面":
                # 先进入阴阳寮界面
                print("        INFO- ----- 尝试前往寮界面")
                Itface_guild(Hwnd)
                for Wait in range(3):
                    Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/结界.png", 0.05, 0)
                    if Find:
                        print("        INFO-", Matchs, "检测到结界入口 已经进入寮界面")
                        print("        STEP- vvvvv 跳转寮界面")
                        current_state = "寮界面"
                        break
                    else:
                        print("        INFO-", Matchs, "未检测到结界入口")
                        print("        WAIT- wwwww 等待进入寮界面 已等待 {waittime} 秒".format(waittime=Wait))
                        Sleep_print(1)
                if not Find:
                    Find = Find_Click_windows(Hwnd, "./pic/guild/关闭弹窗.png", 0.05, "点击关闭弹窗", "未检测到弹窗")
                    if Find:
                        Sleep_print(1)
                        print("        STEP- vvvvv 跳转寮界面")
                        current_state = "寮界面"
                    else:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"

            case "寮界面":
                for i in range(5):
                    Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/结界.png", 0.05, 0)
                    if Find:
                        print("        INFO-", Matchs, "检测到结界入口")
                        Work_Salary(Hwnd)
                        Find = Find_Click_windows(Hwnd, "./pic/guild/结界.png", 0.05, "点击进入结界", "未检测到结界图标")
                        if Find:
                            print("        STEP- vvvvv 跳转结界界面")
                            Sleep_print(3)
                            current_state = "结界界面"
                            break
                        else:
                            print("        STEP- vvvvv 跳转异常退出界面")
                            current_state = "异常退出"
                            break
                    else:
                        Find = Find_Click_windows(Hwnd, "./pic/guild/关闭弹窗.png", 0.05, "点击关闭弹窗", "未检测到弹窗")
                        if Find:
                            Sleep_print(1)
                            print("        STEP- vvvvv 跳转寮界面")
                            current_state = "寮界面"
                            break
                        else:
                            print("        STEP- vvvvv 跳转异常退出界面")
                            current_state = "异常退出"
                            break

            case "结界界面":
                # 领取寄养
                Jiyangjiangli(Hwnd)

                # 领取结界卡奖励 领取后育成
                flag_Jiejieka = Jiejiekajiangli(Hwnd)

                flag_yucheng = Yucheng("结界界面", Hwnd, priority_cards)

                # 领取体力食盒
                Tilishihe(Hwnd)

                # 经验酒壶 领取后育成
                if Jinyanjiuhu(Hwnd):
                    flag_yucheng = Yucheng("结界界面", Hwnd, priority_cards)

                # 领取体力食盒
                Tilishihe(Hwnd)

                if flag_Jiejieka:
                    flag_Jiejieka = Jiejieka(Hwnd, card_order)
                else:
                    # 新增结界卡运行判据 防止一直不填结界卡
                    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/结界卡运行中.png", 0.05, 0)
                    if Range:
                        print("        INFO-", Matchs, "结界卡依旧生效")
                    else:
                        print("        INFO-", Matchs, "结界卡似乎已耗尽")
                        flag_Jiejieka = Jiejieka(Hwnd, card_order)

                Finish = flag_yucheng and flag_Jiejieka
                if Finish:
                    print("        STEP- vvvvv 跳转结束")
                    current_state = "结束"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "结束":
                Itface_Host(Hwnd)
                return 1

            case "异常退出":
                Esc_print(Hwnd)
                Sleep_print(2)
                for i in range(5):
                    Find = Find_Click_windows(Hwnd, "./pic/common/退出标志2.png", 0.05, "点击退出寮界面", "未检测到寮退出图标")
                    if Find:
                        Sleep_print(1)
                        break
                    else:
                        Sleep_print(3)
                        if i > 3:
                            Esc_print(Hwnd)
                Itface_Host(Hwnd)
                return 0


def Work_Salary(Hwnd):
    """
    阴阳寮工资和体力
    :param Hwnd:    窗口句柄
    """
    # 领取工资奖励
    if Find_Click_windows(Hwnd, "./pic/guild/金币工资.png", 0.05, "点击工资", "未检测到工资"):

        if Find_Click_windows(Hwnd, "./pic/guild/领取.png", 0.05, "领取工资", "领取工资异常"):
            Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
            if Find:
                print("        INFO-", Matchs, "领取体力工资成功")
                Esc_print(Hwnd)
                Sleep_print(1)

    if Find_Click_windows(Hwnd, "./pic/guild/体力工资.png", 0.05, "领取体力工资", "未检测到体力工资"):
        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
        if Find:
            print("        INFO-", Matchs, "领取体力工资成功")
            Esc_print(Hwnd)
            Sleep_print(1)

    Sleep_print(1)


def Jiyangjiangli(Hwnd):
    # 检测寄养奖励
    for i in range(1):
        if not Find_Click_windows(Hwnd, "./pic/guild/寄养经验.png", 0.05, "检测到寄养奖励", "未检测到寄养奖励"):
            break
        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
        if Find:
            print("        INFO-", Matchs, "寄养奖励领取成功")
            Sleep_print(1)
            Esc_print(Hwnd)
            Sleep_print(1)
        else:
            print("        INFO-", Matchs, "寄养奖励领取失败")


def Tilishihe(Hwnd):
    Sleep_print(0.5)
    # 检测体力食盒
    for i in range(1):
        if not Find_Click_windows(Hwnd, "./pic/guild/体力食盒.png", 0.05, "检测到体力食盒", "未检测到体力食盒溢出"):
            break

        Find_Click_windows(Hwnd, "./pic/guild/取出.png", 0.05, "取出体力食盒", "取出体力食盒异常")
        Sleep_print(1)
        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
        if Find:
            print("        INFO-", Matchs, "体力食盒领取成功")
            Esc_print(Hwnd)
            Sleep_print(1)
            Esc_print(Hwnd)
            Sleep_print(1)
            return 1
        else:
            print("        INFO-", Matchs, "体力食盒领取失败")
            Esc_print(Hwnd)
            Sleep_print(1)
            return 0


def Jinyanjiuhu(Hwnd):
    # 提取函数
    def Tiqu(Range, Matchs):
        if Range:
            Esc_print(Hwnd)
            Sleep_print(1)
            print("        INFO-", Matchs, "经验酒壶提取上限")
            return 0
        else:
            print("        INFO-", Matchs, "经验酒壶提取未到上限")
            Find_Click_windows(Hwnd, "./pic/guild/确定.png", 0.05, "育成有满级式神 强行提取", "经验酒壶提取成功")
            return 1

    Sleep_print(1)
    # 满经验酒壶情况
    if Find_Click_windows(Hwnd, "./pic/guild/经验酒壶满.png", 0.05, "检测到经验酒壶满", "经验酒壶未满"):
        Find_Click_windows(Hwnd, "./pic/guild/提取.png", 0.05, "提取满的经验酒壶", "提取满的经验酒壶失败")
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/提取.png", 0.05, 0)
        return Tiqu(Range, Matchs)
    else:
        # 不满经验酒壶情况
        if Find_Click_windows(Hwnd, "./pic/guild/经验酒壶.png", 0.05, "检测到有经验酒壶", "未检测到经验酒壶"):
            Find_Click_windows(Hwnd, "./pic/guild/提取.png", 0.05, "提取经验酒壶", "提取经验酒壶失败")
            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/提取.png", 0.05, 0)
            return Tiqu(Range, Matchs)
        else:
            return 0


def Jiejiekajiangli(Hwnd):
    Sleep_print(1)
    # 检测结界卡奖励
    for i in range(1):
        if Find_Click_windows(Hwnd, "./pic/guild/结界卡奖励.png", 0.05, "检测到结界卡奖励 点击领取", "未检测到结界卡结束奖励"):
            Sleep_print(0.5)
            Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/common/获得奖励.png", 0.05, 0)
            if Find:
                print("        INFO-", Matchs, "结界卡奖励领取成功")
            else:
                print("        INFO-", Matchs, "结界卡奖励领取失败")
            return 0
        else:
            Find_Click_windows(Hwnd, "./pic/guild/结界卡运行中.png", 0.05, "检测到结界卡依旧运行 点击领取", "未检测到结界卡依旧运行")
            return 1


def Jiejieka(Hwnd, card_order=("太鼓", "斗鱼")):
    """
    放置结界卡
    :param Hwnd:        窗口句柄
    :param card_order:  结界卡的尝试顺序，来自配置「优先结界卡」，
                        默认值与改动前一致（优先太鼓，耗尽再斗鱼）
    """
    Sleep_print(1)
    # 进入结界卡界面
    for Wait in range(10):
        Find = Find_Click_windows(Hwnd, "./pic/guild/结界卡.png", 0.07, "进入结界卡界面", "未进入结界卡界面")
        if Find:
            break
        else:
            print("        WAIT- wwwww 等待进入结界卡界面 已等待 {waittime} 秒".format(waittime=Wait + 1))
            Sleep_print(1)

    Sleep_print(1)
    # 放置结界卡
    for i in range(1):
        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/结界卡槽.png", 0.05, 0)
        if not Find:
            print("        INFO-", Matchs, "结界卡未耗尽")
            Esc_print(Hwnd)
            Sleep_print(0.5)
            return 1
        else:
            print("        INFO-", Matchs, "结界卡已经耗尽")

            # 按配置的顺序逐张尝试：前一张没库存就换下一张，
            # 顺序由 Lib.jiejie_card_order 决定，这里不再写死太鼓在前。
            placed = 0
            sorted_once = False
            for card in card_order:
                if not Find_Click_windows(Hwnd, "./pic/guild/结界卡列表.png", 0.05, "打开结界卡列表", "打开结界卡列表异常"):
                    break
                if not Find_Click_windows(Hwnd, JIEJIE_CARD_LIST_PICS[card], 0.05, "点击" + card + "列表", "点击" + card + "列表异常"):
                    print("        INFO- ----- 未找到" + card + "页签 尝试下一张")
                    continue
                # 星级降序只需点一次：切家族不会重置排序（已确认真机行为），
                # 而重复点击是切换型按钮，第二次会把降序翻回升序拿到低星卡。
                if not sorted_once:
                    if not Find_Click_windows(Hwnd, "./pic/guild/星级降序.png", 0.05, "点击星级降序", "点击星级降序异常"):
                        break
                    sorted_once = True
                if not Find_Click_windows(Hwnd, "./pic/guild/首张结界卡.png", 0.05, "点击首张结界卡", "点击首张结界卡异常"):
                    print("        INFO- ----- 没有可用的" + card + "结界卡 尝试下一张")
                    continue
                placed = 1
                break

            if not placed:
                print("        INFO- ----- 配置的结界卡都没有库存 放弃放置")
                return 0

            if not Find_Click_windows(Hwnd, "./pic/guild/激活.png", 0.05, "点击激活", "点击激活异常"):
                return 0
            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/邀请.png", 0.05, 0)
            if Range:
                print("        INFO-", Matchs, "结界卡激活成功")
                Sleep_print(1)
                Esc_print(Hwnd)
                Sleep_print(0.5)
                return 1
            else:
                print("        INFO-", Matchs, "结界卡激活失败")
                return 0


def Yucheng(current_state, Hwnd, priority_cards=None):
    """
    结界育成
    :param current_state:   起始界面状态
    :param Hwnd:            窗口句柄
    :param priority_cards:  寄养优先级，``((卡名, 模板路径), ...)``，
                            来自配置「寄养优先级」；None 表示用默认顺序
    """
    if priority_cards is None:
        priority_cards = jiejie_priority_cards(None)
    Sleep_print(1)
    # 进入结界育成
    print("        STEP- vvvvv 从{First_state}开始育成任务".format(First_state=current_state))
    for step in range(30):
        match current_state:
            case "结界界面":
                for Wait in range(10):
                    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/式神育成.png", 0.05, 0)
                    if Range:
                        print("        INFO-", Matchs, "检测到结界育成界面")
                        Move_to_range(Hwnd, Range)
                        Click(Hwnd, Range, 1)
                        print("        STEP- vvvvv 跳转育成界面")
                        current_state = "育成界面"
                        break
                    else:
                        print("        WAIT- wwwww 等待育成界面检测 已等待 {waittime} 秒".format(waittime=Wait + 1))
                        Sleep_print(1)
                if not Range:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    Sleep_print(1)
                    return 0

            case "育成界面":
                # 放出满级式神
                for i in range(10):
                    if Find_Click_windows(Hwnd, "./pic/guild/满级达摩.png", 0.07, "检测到有满级式神", "未检测到有满级式神"):
                        Sleep_print(0.5)
                    else:
                        break
                        Sleep_print(0.5)

                Find = Find_Click_windows(Hwnd, "./pic/guild/放入式神.png", 0.05, "检测到有空位", "育成池已经放满")
                if Find:
                    # 进入素材列表
                    if Find_Click_windows(Hwnd, "./pic/guild/全部.png", 0.05, "进入全部式神列表", "正处在素材列表中"):
                        Sleep_print(0.5)
                        Find_Click_windows(Hwnd, "./pic/guild/素材.png", 0.05, "选择素材列表", "选择素材列表异常")

                    for j in range(10):
                        Sleep_print(0.5)
                        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/奉为达摩.png", 0.07, 0)
                        if Range:
                            print("        INFO-", Matchs, "放上去一个奉为达摩")
                            Move_to_range(Hwnd, Range)
                            Click(Hwnd, Range, 1)
                            break
                        else:
                            print("        INFO-", Matchs, "未找到奉为达摩")
                            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/育成列表框.png", 0.05, 0)
                            print("        INFO-", Matchs, "进入翻页区域")
                            Move_to_range(Hwnd, Range)
                            Scroll_print(Hwnd, -3)
                else:
                    print("        STEP- vvvvv 跳转寄养任务")
                    current_state = "寄养任务"

            case "寄养任务":
                Find = Find_Click_windows(Hwnd, "./pic/guild/寄养入口.png", 0.05, "检测到寄养空位", "已经有寄养")
                if Find:
                    # 四档优先级在 Jiyang 内部一趟扫完再统一裁决，
                    # 所以这里只调一次，不再按优先级逐个重扫全表。
                    Finish = Jiyang("寄养列表", Hwnd, priority_cards)

                    if Finish:
                        print("        STEP- vvvvv 结束育成")
                        Sleep_print(1)
                        Esc_print(Hwnd)
                        Sleep_print(1)
                        return 1
                    else:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        Sleep_print(1)
                        return 0
                else:
                    print("        STEP- vvvvv 结束育成")
                    Sleep_print(1)
                    Esc_print(Hwnd)
                    Sleep_print(1)
                    return 1


def Jiyang_at_cap(Best, card_name):
    """本档是否已经读到该类型的封顶值（读到就不必再点这一档剩下的行）"""
    Found = Best.get(card_name)
    if Found is None or Found["value"] is None:
        return False
    return Found["value"] >= JIEJIE_YIELD_CAP.get(jiejie_card_type(card_name), 10 ** 6)


def Jiyang_outranked(Best, card_name, priority_cards):
    """本档是否已被同类型的更高档压住（压住了就不必再点本档的行）

    同类型内星级是单调的：六星太鼓 67~76，五星太鼓 59~67，
    六星斗鱼最低 118，五星斗鱼更低。所以只要同类型的更高档已经读到数字，
    本档不可能胜出——连 67 对 67 这种相接的情况也算了，因为
    档间按优先级取第一个有货的，更高档排在前面，读不读本档结果一样。

    跨类型不适用：勾玉与体力单位不同，六星太鼓有货并不影响六星斗鱼。

    :param Best:          已读到的档位 -> 最优记录
    :param card_name:     当前档位名（六星太鼓 / 五星太鼓 / ...）
    :param priority_cards: 全部档位，用来判断谁排在谁前面
    :return:              True 表示本档已被更高档压住
    """
    Type = jiejie_card_type(card_name)
    if not Type:
        return False
    for Other, _Other_pic in priority_cards:
        if Other == card_name:
            break           # 只往前看：排在后面的档位压不住本档
        if jiejie_card_type(Other) != Type:
            continue        # 跨类型不比
        Found = Best.get(Other)
        if Found is not None and Found["value"] is not None:
            return True
    return False


def Jiyang_type_best(Best, card_name):
    """同类型里已经读到的最好成绩，一个都没有则返回 None

    为什么不看全部档位：勾玉与体力单位不同，跨类型比大小没有意义。
    同类型内星级是单调的，所以「同类型目前最高」才是这张卡能不能
    胜出的真正参照。
    """
    Type = jiejie_card_type(card_name)
    Top = None
    for Other, Found in Best.items():
        if Type and jiejie_card_type(Other) != Type:
            continue
        if Found["value"] is None:
            continue
        if Top is None or Found["value"] > Top["value"]:
            Top = Found
    return Top


def Jiyang_pick(Best, Fallback, priority_cards):
    """按优先级裁决：取第一个有结果的档位

    勾玉与体力单位不同，不互比大小，所以「六星太鼓 67」胜过
    「六星斗鱼 151」——因为前者排在前面。

    :return: (选中记录 或 None, 是否走了兜底)
    """
    for card_name, _card_pic in priority_cards:
        if card_name in Best:
            return Best[card_name], False
    for card_name, _card_pic in priority_cards:
        if card_name in Fallback:
            return Fallback[card_name], True
    return None, False


def Jiyang_read_panel(Hwnd):
    """读右侧面板的收益数字，等两帧一致再返回

    数字是滚动动画，点开后立刻截图会截到中间帧。所以读两次，
    两次一致才算数；不一致再等一帧，仍不一致就当作读不出。
    """
    First = jiejie_read_yield(Screenshot_window(Hwnd))
    Sleep_quiet(0.15)
    Second = jiejie_read_yield(Screenshot_window(Hwnd))
    if First == Second:
        return First
    Sleep_quiet(0.2)
    Third = jiejie_read_yield(Screenshot_window(Hwnd))
    return Third if Third == Second else None


def Jiyang_scan_list(Hwnd, priority_cards):
    """一趟扫完全表：每屏同时试四张模板，点开读数，按档位记录最优

    为什么是一趟而不是四趟：四张模板可以吃同一帧截图，
    扫四趟等于把同样的滚动与截图做四遍，白白多出三倍时间，
    而且每多一趟就多一次「扫描期间列表被改动」的机会。

    :return: {"name", "value", "scrolls", "row", "pic"} 或 None
             scrolls 是从列表顶部向下滚了几次，row 是该行的匹配框
    """
    Best = {}          # 档位 -> 最优（数字读得出）
    Fallback = {}      # 档位 -> 第一个命中（数字全都读不出时的兜底）
    Scrolls = 0

    # 100 次是兜底，不是「预计要扫 100 屏」：万一到底判定失效，
    # 也不会变成死循环。与改动前的轮次上限一致。
    for screen in range(100):
        Img = Screenshot_window(Hwnd)

        # 本屏四档一起找：同一帧上把四张模板一起送进 Match_models_rows，
        # 由它按行聚类、在行内比分数裁决类型。
        #
        # 为什么不能逐张模板各找各的：四张结界卡共用同一个金色托盘与同一排橙色星点，
        # 一张斗鱼卡在太鼓模板上换个滑窗位置也可能过阈值。逐模板独立搜索时，
        # 同一行会被两张模板各报一次 → 点两次、记两次账，
        # 斗鱼的 101 记到「五星太鼓」名下，101 又大于太鼓封顶 76，误触发「已达封顶」。
        #
        # 四张模板必须一起参与裁决（哪怕本档已封顶或被压制）：
        # 少送一张，行内的竞争就不公平，剩下的模板可能把这张卡认成别的类型。
        # 该不该点这一行，由下面的 at_cap / outranked 判断，与类型识别分开。
        Models = [(card_name, card_pic) for card_name, card_pic in priority_cards]
        Pic_of = {card_name: card_pic for card_name, card_pic in Models}
        Rows = []
        for card_name, row, _score in Match_models_rows(Img, Models, 0.05, max_matches=8):
            Rows.append((row[0][1], card_name, Pic_of[card_name], row))

        # 从上到下依次点，与人的阅读顺序一致，也避免上下反复跳
        Rows.sort(key=lambda item: item[0])

        Clicked_here = False
        for _y, card_name, card_pic, row in Rows:
            # 本档已封顶、或已被同类型更高档压住：这一档剩下的行不必再点。
            # Rows 是本屏一次性收集的，收集时还没发生，所以要在点击前再判一次。
            if Jiyang_at_cap(Best, card_name) or Jiyang_outranked(Best, card_name, priority_cards):
                continue

            Fallback.setdefault(
                card_name,
                {"name": card_name, "value": None, "scrolls": Scrolls, "row": row, "pic": card_pic},
            )

            Move_to_range(Hwnd, row)
            Click(Hwnd, row, 1)
            Clicked_here = True
            Value = Jiyang_read_panel(Hwnd)
            if Value is None:
                print("        INFO- ----- 第 {n} 屏 {name} 收益读不出，跳过".format(
                    n=screen + 1, name=card_name))
                continue

            if card_name not in Best or Value > Best[card_name]["value"]:
                Best[card_name] = {
                    "name": card_name, "value": Value, "scrolls": Scrolls, "row": row, "pic": card_pic,
                }

            # 报一下同类型目前最高，方便对着日志判断这张卡有没有希望胜出。
            # 只跟同类型比：勾玉与体力单位不同，混在一起看没有意义。
            Top = Jiyang_type_best(Best, card_name)
            if Top is None:
                print("        INFO- ----- 第 {n} 屏 {name} 收益 {v}".format(
                    n=screen + 1, name=card_name, v=Value))
            else:
                print("        INFO- ----- 第 {n} 屏 {name} 收益 {v} 目前最高{top}".format(
                    n=screen + 1, name=card_name, v=Value, top=Top["value"]))

            if Jiyang_at_cap(Best, card_name):
                print("        INFO- ----- {name} 已达封顶 {v}，本档剩余行跳过".format(
                    name=card_name, v=Value))

        # 到底判定：寄养列表末尾.png 命中的是「有头像但没有结界卡图」的空白格子，
        # 与有卡行的得分差一个数量级。必须放在处理完本屏候选之后：
        # 列表不满一屏时首页就露出空白格，若先判到底，第一屏的卡会被跳过。
        End_hit = Match_models_in_image(Img, [("末尾", "./pic/guild/寄养列表末尾.png")], 0.001)
        if End_hit:
            print("        INFO-", End_hit[0][2], "已经到寄养列表末尾")
            break

        # 滚动前要保证鼠标落在列表上：pyautogui.scroll 是发给鼠标位置的，
        # 鼠标若停在页签或详情面板上，滚轮不会作用到列表，画面不动会被误当成「到底」。
        #
        # 本屏点过卡的话，鼠标刚刚就落在列表里的某一行上，直接滚就行，
        # 不必再找一次列表位置。只有整屏一张卡都没点（鼠标还停在上一屏
        # 的某处，或者停在点过的卡上但那一行已经滚出视窗）时，才把鼠标
        # 放回列表上。这既省掉一次匹配，也避免了「找不到列表就滚不动」。
        if not Clicked_here:
            List_hit = Match_models_in_image(Img, [("列表", "./pic/guild/寄养列表.png")], 0.05)
            if List_hit:
                Move_to_range(Hwnd, List_hit[0][1])

        Scroll_print(Hwnd, -JIEJIE_SCROLL_STEP)
        Sleep_quiet(0.8)
        Scrolls += 1

    # 档间按优先级取第一个有结果的档位：勾玉与体力单位不同，不互比大小，
    # 所以「六星太鼓 67」胜过「六星斗鱼 151」——因为前者排在前面。
    Selected, Fell_back = Jiyang_pick(Best, Fallback, priority_cards)
    if Selected is None:
        return None

    # 扫完之后紧接着报一次最终选择，紧跟在「已经到寄养列表末尾」下面，
    # 这样日志一眼就能看到「扫到头了，最后选的是哪张、值多少」。
    if Selected["value"] is None:
        print("        INFO- ----- 扫完 当前选中 {name} 收益读不出".format(name=Selected["name"]))
    else:
        print("        INFO- ----- 扫完 当前选中 {name} 收益 {v}".format(
            name=Selected["name"], v=Selected["value"]))
    if Fell_back:
        print("        INFO- ----- {name} 一个数字都没读出 回退成第一个命中".format(name=Selected["name"]))

    # 扫完停在底部，回滚要向上滚「总次数 - 目标那一屏的次数」次。
    # 这里算好存进去，免得 Jiyang_goto 还要知道扫描总共滚了多少。
    Selected["back"] = max(0, Scrolls - Selected["scrolls"])
    return Selected


def Jiyang_goto(Hwnd, Target):
    """从列表底部向上滚回目标那一屏，复核数字后再确认

    扫描时从顶部一路向下滚，滚到目标那一屏时记下了当时滚了几次（scrolls）。
    扫完停在底部，所以要向上滚「总次数 - 目标次数」次才能回到目标屏。
    落点不靠绝对坐标，靠模板重新定位。

    :return: True 表示已经点中目标行；False 表示回滚后对不上
    """
    Steps = Target.get("back", 0)
    if Steps:
        # 与扫描时同理：滚轮作用在鼠标位置，先把它放回列表上，
        # 否则鼠标停在详情面板上，回滚是滚不动的。
        # 归位只需要做一次——滚动不会移动鼠标，只要第一下落在列表上，
        # 后面几轮就都还在列表上。
        List_hit = Match_models_in_image(Screenshot_window(Hwnd),
                                         [("列表", "./pic/guild/寄养列表.png")], 0.05)
        if List_hit:
            Move_to_range(Hwnd, List_hit[0][1])
    for _ in range(Steps):
        Scroll_print(Hwnd, JIEJIE_SCROLL_STEP)
        Sleep_quiet(0.1)
    if Steps:
        Sleep_quiet(1)

    Img = Screenshot_window(Hwnd)
    Hits = Match_models_in_image_all(Img, Target["pic"], 0.05, 8)
    if not Hits:
        Hits = [Target["row"]]

    for row in Hits:
        Move_to_range(Hwnd, row)
        Click(Hwnd, row, 1)
        Value = Jiyang_read_panel(Hwnd)
        if Value is None:
            continue
        if Target["value"] is None or Value == Target["value"]:
            print("        INFO- ----- 回滚复核通过 收益 {v}".format(v=Value))
            return True

    print("        INFO- ----- 回滚复核未通过")
    return False


def Jiyang(current_state, Hwnd, priority_cards):
    print("        STEP- vvvvv 从{First_state}开始寄养任务".format(First_state=current_state))
    for step in range(30):
        Sleep_print(1)
        match current_state:
            case "结界界面":
                for Wait in range(10):
                    Find = Find_Click_windows(Hwnd, "./pic/guild/式神育成.png", 0.05, "检测到进入结界育成界面", "未检测到进入结界育成界面")
                    if Find:
                        print("        STEP- vvvvv 跳转育成界面")
                        current_state = "育成界面"
                        break
                    else:
                        print("        WAIT- wwwww 等待育成界面检测 已等待 {waittime} 秒".format(waittime=Wait + 1))
                        Sleep_print(1)
                if not Find:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    Sleep_print(1)
                    return 0

            case "育成界面":
                Find = Find_Click_windows(Hwnd, "./pic/guild/寄养入口.png", 0.05, "检测到寄养空位", "已经有寄养")
                if Find:
                    print("        STEP- vvvvv 跳转寄养列表")
                    current_state = "寄养列表"
                else:
                    print("        STEP- vvvvv 寄养任务完成")
                    return 1

            case "寄养列表":
                # 整个流程只进一次列表，进来时列表本来就是从顶部开始的，
                # 所以不需要再点「跨区」→「好友」刷新一次：那一步只是为了
                # 让列表回到顶部，而这里没有「回到顶部」的需求。
                # 少点两次，也就少一次「刷新导致列表内容变化、扫描位置对不上」的机会。
                Selected = Jiyang_scan_list(Hwnd, priority_cards)
                if Selected is None:
                    print("        INFO- ----- 四个优先级都没有可用结界卡")
                    return 0

                # 回滚到选中那一行并进入。回滚后必须复核数字，
                # 因为扫描期间列表可能被好友改动（撤掉结界卡 / 新加入）。
                if not Jiyang_goto(Hwnd, Selected):
                    print("        INFO- ----- 回滚复核失败，重扫一次")
                    Selected = Jiyang_scan_list(Hwnd, priority_cards)
                    if Selected is None:
                        print("        INFO- ----- 重扫后仍没有可用结界卡")
                        return 0
                    if not Jiyang_goto(Hwnd, Selected):
                        print("        INFO- ----- 重扫后仍无法定位，放弃本次寄养")
                        return 0

                print(
                    "        INFO- ----- 选中 {name} 收益 {value}".format(
                        name=Selected["name"], value=Selected["value"]
                    )
                )
                if Find_Click_windows(Hwnd, "./pic/guild/进入结界.png", 0.05, "点击进入结界", "点击进入结界异常"):
                    Sleep_print(2)
                    print("        STEP- vvvvv 跳转寄养结界")
                    current_state = "寄养结界"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    Sleep_print(1)
                    return 0

            case "寄养结界":
                Find = Find_Click_windows(Hwnd, "./pic/guild/有寄养位.png", 0.05, "有寄养位", "结界已被占用")
                if not Find:
                    Esc_print(Hwnd)
                    Sleep_print(0.5)
                    Esc_print(Hwnd)
                    Sleep_print(2)
                    return Jiyang("结界界面", Hwnd, priority_cards)
                else:
                    # 进入素材列表
                    if Find_Click_windows(Hwnd, "./pic/guild/全部.png", 0.05, "进入全部式神列表", "正处在素材列表中"):
                        Sleep_print(0.5)
                        Find_Click_windows(Hwnd, "./pic/guild/素材.png", 0.05, "选择素材列表", "选择素材列表异常")

                    for j in range(10):
                        if not Find_Click_windows(Hwnd, "./pic/guild/奉为达摩.png", 0.07, "放上去一个奉为达摩", "未检测到达摩素材"):
                            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/育成列表框.png", 0.05, 0)
                            print("        INFO-", Matchs, "进入翻页区域")
                            Move_to_range(Hwnd, Range)
                            Scroll_print(Hwnd, -3)
                        else:
                            Find_Click_windows(Hwnd, "./pic/guild/确定.png", 0.05, "点击确定", "点击确定异常")
                            Esc_print(Hwnd)
                            Sleep_print(2)
                            Esc_print(Hwnd)
                            Sleep_print(2)
                            return Jiyang("结界界面", Hwnd, priority_cards)
