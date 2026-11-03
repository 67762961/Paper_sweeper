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
    jiejie_yield_cap,
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

# 滚完列表后等多久再截图。滚轮翻页之后游戏会重绘整列列表，
# 同一行的结界卡有可能被刷新成另一种（太鼓 ↔ 斗鱼）。
#
# 这里只等「滚轮生效」的时间，不等重绘完成：重绘慢的时候干等太拖时间
# （整趟下来要白等好几秒）。正确性改由「点开之后、读右侧数字之前
# 在原地复核一次类型」来保证（见 Jiyang_row_type）——重绘没完就把
# 这一屏重新识别一遍，比闷头等更准，也更快。
JIEJIE_SCROLL_WAIT = 0.2

# 点开一行之后、读右侧数字之前，在原地复核卡面类型时的裁切外扩像素。
# 稍外扩一点，容忍点击时列表的轻微位移。
JIEJIE_RECHECK_MARGIN = 12

# 同一屏最多重新识别几次。复核不一致说明这一屏还没刷完，
# 重新识别一遍即可；但要有上限，否则一直不一致就会卡在同一屏。
JIEJIE_RECHECK_TRIES = 2

# 点开列表里的一行要连点几次。
#
# 滚轮翻页后游戏会重绘整列列表，重绘那一瞬点下去会被吞掉，而落空不会报错：
# 左侧列表没选中任何行、右侧详情面板还停在上张卡上，于是收益被记到这一行名下。
# 复核类型只能兜住「类型变了」，兜不住「压根没点中」——这行刷新后若仍是
# 同一类型，复核也会判「一致」。第二次点击时重绘已经结束，一定点得中，
# 这就是改动前连点两次的原因。
JIEJIE_CLICK_TIMES = 2

# 两次点击之间的间隔（秒）。改动前的 1 秒偏长，而重绘基本在 0.3~0.5 秒内
# 结束，留 0.5 秒既够第二次点中，也不至于白等。
JIEJIE_CLICK_WAIT = 0.5


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
    """本档是否已经读到该档的上限（读到就不必再点这一档剩下的行）

    上限按**档位**取，不是按类型：六星斗鱼能到 151，五星斗鱼最高只到 134。
    按类型记的话，五星斗鱼读到 134 也够不到斗鱼的 151，这一档的剩余行
    会被白点一遍。
    """
    Cap = jiejie_yield_cap(card_name)
    Found = Best.get(card_name)
    if Cap is None or Found is None or Found["value"] is None:
        return False
    return Found["value"] >= Cap


def Jiyang_outranked(Best, card_name, priority_cards):
    """本档是否已被同类型的更高档压住（压住了就不必再点本档的行）

    判据是「更高档的数值 >= 本档上限」，不是「更高档有没有数字」：
    六星斗鱼最低 118，而五星斗鱼最高能到 134，所以 118 压不住五星，
    要 134 才压得住。太鼓那边六星最低 67 = 五星上限 67，相接也算压住
    （同值按优先级取靠前的六星），于是「有六星太鼓就不点五星太鼓」
    天然成立。

    跨类型不适用：勾玉与体力单位不同，六星太鼓有货并不影响六星斗鱼。

    :param Best:          已读到的档位 -> 最优记录
    :param card_name:     当前档位名（六星太鼓 / 五星太鼓 / ...）
    :param priority_cards: 全部档位，用来判断谁排在谁前面
    :return:              True 表示本档已被更高档压住
    """
    Type = jiejie_card_type(card_name)
    Cap = jiejie_yield_cap(card_name)
    if not Type or Cap is None:
        return False
    for Other, _Other_pic in priority_cards:
        if Other == card_name:
            break           # 只往前看：排在后面的档位压不住本档
        if jiejie_card_type(Other) != Type:
            continue        # 跨类型不比
        Found = Best.get(Other)
        if Found is not None and Found["value"] is not None and Found["value"] >= Cap:
            return True
    return False


def Jiyang_top_capped(Best, priority_cards):
    """首选档位是否已经读到封顶值（读到了就整表收工，不必再往下翻）

    首选档位排在所有档位最前面，所以它一旦拿到本类型的封顶值，
    后面无论扫出什么都不可能比它更优先——「六星太鼓 76」已经是
    六星太鼓的最高收益，比它更靠后的档位按优先级也赢不了。
    这时继续往下翻纯属浪费。

    注意只对**首选档位**成立。第二、三、四位读到封顶不能收工：
    首选档位可能还在后面的屏里没出现。

    :return: True 表示可以收工
    """
    if not priority_cards:
        return False
    First, _First_pic = priority_cards[0]
    return Jiyang_at_cap(Best, First)


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


def Jiyang_after_scroll(Hwnd):
    """滚完之后等一小会儿再截图，等滚轮生效

    滚轮翻页之后游戏会重绘整列列表，同一行有可能被刷新成另一种卡面
    （太鼓 ↔ 斗鱼）。这里**不等重绘做完**——重绘慢的时候干等太拖时间
    （整趟下来白等好几秒）。正确性交给「点开之后、读数字之前
    在原地复核一次类型」（见 Jiyang_row_type）：重绘没完就把这一屏
    重新识别一遍，比闷头等更准，也更快。

    :return: 滚动之后的整窗截图（调用方直接用它，不必再截一次）
    """
    Sleep_quiet(JIEJIE_SCROLL_WAIT)
    return Screenshot_window(Hwnd)


def Jiyang_row_type(Img, row, priority_cards):
    """在原来那一行原地重新判一次卡面类型

    只裁这一行附近（外扩 `JIEJIE_RECHECK_MARGIN` 像素），四张模板一起送进
    `Match_models_rows` 做行内裁决，与扫描时用的是同一把尺子。
    裁得窄有两个好处：一是快，二是不会把右侧详情面板里那张放大卡面
    也当成列表里的一行。

    :param row: 扫描时记下的匹配框 [[左上x, 左上y], [右下x, 右下y]]
    :return:    这一带的卡面类型；那一带已经认不出卡时返回 None
    """
    Margin = JIEJIE_RECHECK_MARGIN
    X0 = max(0, row[0][0] - Margin)
    Y0 = max(0, row[0][1] - Margin)
    X1 = min(Img.shape[1], row[1][0] + Margin)
    Y1 = min(Img.shape[0], row[1][1] + Margin)
    if X1 - X0 < 8 or Y1 - Y0 < 8:
        return None

    Models = [(card_name, card_pic) for card_name, card_pic in priority_cards]
    Found = Match_models_rows(Img[Y0:Y1, X0:X1], Models, 0.05, max_matches=8)
    if not Found:
        return None

    # 裁切后的坐标是相对裁切块的，先加回偏移再跟原行比纵向中心。
    # 取离原行最近的那一条，避免裁切块边缘带进来的邻行冒充。
    Target = (row[0][1] + row[1][1]) / 2.0
    Near_name, Near_gap = None, None
    for name, box, _score in Found:
        Center = ((box[0][1] + Y0) + (box[1][1] + Y0)) / 2.0
        Gap = abs(Center - Target)
        if Near_gap is None or Gap < Near_gap:
            Near_name, Near_gap = name, Gap
    # 偏离超过一行高，说明这一行已经不在原处（列表滚了或整屏换了内容）
    if Near_gap > (row[1][1] - row[0][1]):
        return None
    return Near_name


def Jiyang_click_row(Hwnd, row):
    """点开列表里的一行：连点 `JIEJIE_CLICK_TIMES` 次，间隔 `JIEJIE_CLICK_WAIT`

    为什么要点两次：滚轮翻页后游戏会重绘整列列表，重绘那一瞬点下去会被
    吞掉，而落空**不会报错**——左侧没选中任何行、右侧详情面板还停在
    上一张卡上，于是 `Jiyang_read_panel` 读到的是上一张卡的收益。
    第二次点击时重绘已经结束，一定点得中。

    `Click` 内部自己会 `Move_to_range`，这里不必再移一次鼠标。

    扫描与回滚（`Jiyang_goto`）共用这一个原语：两条路径都会落空，
    而回滚落空的后果更重——它返回 True 之后紧接着就是点「进入结界」，
    把上一张卡的数字误认成目标行就等于寄养错卡。
    """
    for _ in range(JIEJIE_CLICK_TIMES):
        Click(Hwnd, row, JIEJIE_CLICK_WAIT)


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
    # 滚完之后的那一帧由 Jiyang_after_scroll 交回来，下一屏直接用它，
    # 省掉一次重复截图。
    Img = None

    # 100 次是兜底，不是「预计要扫 100 屏」：万一到底判定失效，
    # 也不会变成死循环。与改动前的轮次上限一致。
    for screen in range(100):
        if Img is None:
            Img = Screenshot_window(Hwnd)

        Clicked_here = False
        Redone = 0
        # 复核发现这一屏的卡面在点开时还在变，就把这一屏重新识别一遍。
        # 正常情况下这里只会跑一轮。
        while True:
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

            Redo = False
            for _y, card_name, card_pic, row in Rows:
                # 本档已封顶、或已被同类型更高档压住：这一档剩下的行不必再点。
                # Rows 是本屏一次性收集的，收集时还没发生，所以要在点击前再判一次。
                if Jiyang_at_cap(Best, card_name) or Jiyang_outranked(Best, card_name, priority_cards):
                    continue

                # 连点两次：重绘那一瞬的点击会被吞掉，而且落空不报错
                # （右侧面板还停在上张卡上），第二次点击时重绘已结束。
                Jiyang_click_row(Hwnd, row)
                Clicked_here = True

                # 点开之后、读右侧数字之前，在原地再认一次这一行是什么卡。
                # 滚轮翻页会让游戏重绘整列列表，同一行的结界卡可能被刷新成
                # 另一种（太鼓 ↔ 斗鱼）；扫描用的那一帧若是重绘中间态，
                # 类型就记错了。这里用点开之后的实时画面复核，比干等重绘更快。
                Now = Jiyang_row_type(Screenshot_window(Hwnd), row, priority_cards)
                if Now != card_name:
                    if Redone < JIEJIE_RECHECK_TRIES:
                        print("        INFO- ----- 第 {n} 屏 {old} 复核成 {new}，这一屏重新识别".format(
                            n=screen + 1, old=card_name, new=Now or "认不出"))
                        Redo = True
                        break
                    # 复核次数用完还不一致：按复核到的类型继续，
                    # 总比把这张卡整行丢掉强。认不出卡就跳过这一行。
                    print("        INFO- ----- 第 {n} 屏 {old} 复核成 {new}，按复核结果记".format(
                        n=screen + 1, old=card_name, new=Now or "认不出"))
                    if Now is None:
                        continue
                    card_name = Now
                    card_pic = Pic_of.get(Now, card_pic)

                # 兜底记录放在复核之后：万一这张卡的数字读不出，
                # 至少还知道「这一档在这个位置有一张」，可以回滚过来点它。
                Fallback.setdefault(
                    card_name,
                    {"name": card_name, "value": None, "scrolls": Scrolls, "row": row, "pic": card_pic},
                )

                Value = Jiyang_read_panel(Hwnd)
                if Value is None:
                    print("        INFO- ----- 第 {n} 屏 {name} 收益读不出，跳过".format(
                        n=screen + 1, name=card_name))
                    continue

                # 收益相同时记住后发现的这一张：扫完要往回翻到目标行，
                # 后发现的离列表底部更近，回滚的步数更少。
                # 用 >= 而不是 >，就是为了让后来者顶掉同分的前者。
                if card_name not in Best or Value >= Best[card_name]["value"]:
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
                    # 首选档位封顶会紧接着报一次「收工」，这里就不重复报了
                    if not Jiyang_top_capped(Best, priority_cards):
                        print("        INFO- ----- {name} 已达封顶 {v}，本档剩余行跳过".format(
                            name=card_name, v=Value))

            if not Redo:
                break
            # 这一屏还在刷，重新截一张再认一遍。重识别期间点过的行会重新匹配，
            # 但 Best / Fallback 里已经记下的结果不受影响（同分取后发现的）。
            Redone += 1
            Img = Screenshot_window(Hwnd)

        # 首选档位已经拿到封顶值，整表收工：它排在所有档位最前面，
        # 后面扫出什么都不可能比它更优先，继续往下翻纯属浪费。
        # 放在处理完本屏候选之后，这样同一屏里排在它后面的行不会被漏掉
        # （虽然那些行按优先级也赢不了，但少一次误判的余地）。
        if Jiyang_top_capped(Best, priority_cards):
            First = priority_cards[0][0]
            print("        INFO- ----- {name} 已到封顶 {v}，首选档位拿满，收工".format(
                name=First, v=Best[First]["value"]))
            break

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
        # 滚完只等一下滚轮生效，不等列表重绘：重绘慢时干等太拖时间。
        # 重绘途中若把某一行换了卡面，点开之后的原地复核会把它纠回来。
        # 交回来的那一帧就是下一屏要用的画面，不必再截一次。
        Img = Jiyang_after_scroll(Hwnd)
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


def Jiyang_goto(Hwnd, Target, priority_cards=None):
    """从列表底部向上滚回目标那一屏，复核类型与数字后再确认

    扫描时从顶部一路向下滚，滚到目标那一屏时记下了当时滚了几次（scrolls）。
    扫完停在底部，所以要向上滚「总次数 - 目标次数」次才能回到目标屏。
    落点不靠绝对坐标，靠模板重新定位。

    :param priority_cards: 四档模板。复核类型时四张一起参与裁决，
                           少送几张的话，别的卡可能在目标模板上蒙混过关。
                           传 None 时退化成只用目标自己那张（仅供测试用）。
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
        # 回滚也是滚动，同样会重绘。这里只等滚轮生效，落点对不对
        # 交给下面点开后的复核——与扫描时同一套判据。
        Img = Jiyang_after_scroll(Hwnd)
    else:
        Img = Screenshot_window(Hwnd)

    Hits = Match_models_in_image_all(Img, Target["pic"], 0.05, 8)
    if not Hits:
        Hits = [Target["row"]]

    for row in Hits:
        # 与扫描同一条点击路径，同样会落空，所以同样连点两次。
        # 这里比扫描更不能容忍落空：下面一旦返回 True，紧接着就是点
        # 「进入结界」——把上一张卡的数字误认成目标行就等于寄养错卡。
        Jiyang_click_row(Hwnd, row)
        # 重绘没做完时，定位到的这一行可能已经不是目标卡了。
        # 点开之后先认一次类型，类型对不上就不必再读数字，
        # 继续试下一个候选行（不直接放弃：候选可能不止一行）。
        Models = list(priority_cards) if priority_cards else [(Target["name"], Target["pic"])]
        Now = Jiyang_row_type(Screenshot_window(Hwnd), row, Models)
        if Now != Target["name"]:
            continue
        Value = Jiyang_read_panel(Hwnd)
        if Value is None:
            continue
        if Target["value"] is None or Value == Target["value"]:
            print("        INFO- ----- 回滚复核通过 收益 {v}".format(v=Value))
            return True

    print("        INFO- ----- 回滚复核未通过")
    return False


def Jiyang_refresh(Hwnd):
    """点「跨区」→「好友」刷新寄养列表，顺带把列表带回顶部

    只在「回滚复核失败、要重扫」这一条路上用。复核失败说明列表在扫描
    期间被好友改动过（撤卡 / 新加卡），此时列表停在底部，直接重扫等于
    从半中间开始。点这两下既刷新内容，也把列表带回顶部。

    正常流程不刷新：整个流程只进一次列表，进来时本来就在顶部，
    少点两次也就少一次「刷新导致位置对不上」的机会。

    :return: True 表示两步都点到了
    """
    if not Find_Click_windows(Hwnd, "./pic/guild/跨区.png", 0.05, "点击跨区", "点击跨区异常"):
        return False
    Sleep_quiet(2)
    if not Find_Click_windows(Hwnd, "./pic/guild/好友.png", 0.05, "点击好友", "点击好友异常"):
        return False
    Sleep_quiet(1)
    return True


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

                # 回滚到选中那一行并进入。回滚后必须复核类型与数字，
                # 因为扫描期间列表可能被好友改动（撤掉结界卡 / 新加入）。
                if not Jiyang_goto(Hwnd, Selected, priority_cards):
                    # 复核失败说明列表在扫描期间被改动过，而扫描已经停在底部。
                    # 直接重扫等于从半中间开始，所以先点「跨区」→「好友」：
                    # 既刷新内容，也把列表带回顶部，重扫才有意义。
                    print("        INFO- ----- 回滚复核失败，刷新列表后重扫一次")
                    if not Jiyang_refresh(Hwnd):
                        print("        INFO- ----- 刷新列表失败，放弃本次寄养")
                        return 0
                    Selected = Jiyang_scan_list(Hwnd, priority_cards)
                    if Selected is None:
                        print("        INFO- ----- 重扫后仍没有可用结界卡")
                        return 0
                    if not Jiyang_goto(Hwnd, Selected, priority_cards):
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
