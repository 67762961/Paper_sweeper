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
    Move_to_range,
    Click,
    run_accounts_task,
    ready_after,
    load_jiejie_settings,
    jiejie_card_order,
    jiejie_priority_cards,
    JIEJIE_CARD_LIST_PICS,
)


def MainTask_Jiejieyangcheng():
    """
    结界养成主任务
    """
    run_accounts_task(
        "结界养成", ready_after(6),
        work=lambda Account: Jiejieyangcheng("庭院界面", Find_windows(Account), Account),
    )


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
        "        INFO- ----- 结界卡放置顺序", " → ".join(card_order),
        "寄养优先级", " → ".join(name for name, _ in priority_cards),
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
                    # 按配置的寄养优先级逐个尝试，顺序由 Lib.jiejie_priority_cards
                    # 归一化后给出（恒为 4 张卡的一个排列，不会重复）。
                    Finish = 0
                    for card_name, card_pic in priority_cards:
                        Finish = Jiyang("寄养列表", Hwnd, card_pic, card_name)
                        if Finish:
                            break

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


def Jiyang(current_state, Hwnd, Jiejieka_Model_path, string):
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
                # 刷新好友结界卡列表
                Sleep_print(2)
                Find_Click_windows(Hwnd, "./pic/guild/跨区.png", 0.05, "点击跨区", "点击跨区异常")
                Sleep_print(2)
                Find_Click_windows(Hwnd, "./pic/guild/好友.png", 0.05, "点击好友", "点击好友异常")
                # 寻找对应结界卡
                for times in range(100):
                    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/寄养列表.png", 0.05, 0)
                    print("        INFO-", Matchs, "移动到寄养列表")
                    Move_to_range(Hwnd, Range)
                    Str1 = "点击" + string
                    Str2 = "无法点击" + string
                    Find = Find_Click_windows(Hwnd, Jiejieka_Model_path, 0.05, Str1, Str2)
                    Str1 = "再次点击" + string
                    Str2 = "无法点击" + string
                    Find = Find_Click_windows(Hwnd, Jiejieka_Model_path, 0.05, Str1, Str2)
                    if Find:
                        if Find_Click_windows(Hwnd, "./pic/guild/进入结界.png", 0.05, "点击进入结界", "点击进入结界异常"):
                            Sleep_print(2)
                            break
                    else:
                        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/guild/寄养列表末尾.png", 0.001, 0)
                        if Find:
                            print("        INFO-", Matchs, "已经到寄养列表末尾")
                            return 0
                        else:
                            print("        INFO-", Matchs, "未到寄养列表末尾")
                            Scroll_print(Hwnd, -3)

                if Find:
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
                    return Jiyang("结界界面", Hwnd, Jiejieka_Model_path, string)
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
                            return Jiyang("结界界面", Hwnd, Jiejieka_Model_path, string)
