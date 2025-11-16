import pyautogui
import pydirectinput
import ctypes
import win32gui
from datetime import datetime, timedelta
from Lib import Find_windows, Find_in_windows_Matchs, Find_Click_windows, Itface_Host, Itface_guild, read_config, write_config, check_lasttime, Scroll_print, Esc_print, Sleep_print


def MainTask_Jiejieyangcheng():
    """
    结界养成主任务
    """
    print("        ")
    current_time = datetime.now()
    print("TASK- ----- 开始执行结界养成任务")
    config_data = read_config("./config/Last_times.json")
    headers = list(config_data.keys())
    for Account in headers:
        print("    切换到 ", Account, " 账号")
        print("        TIME- ----- 读取上次账号", Account, "完成结界养成任务时间")
        Times_jiejieyangcheng = check_lasttime(Account, "结界养成")
        current_time = datetime.now()
        if abs(current_time - Times_jiejieyangcheng) >= timedelta(hours=6):
            Hwnd = Find_windows(Account)
            if Jiejieyangcheng("庭院界面", Hwnd):
                # 更新配置 写入当前时间
                config = read_config("./config/Last_times.json")
                Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                config[Account]["结界养成"] = Now
                write_config("./config/Last_times.json", config)
                print("        TIME- ----- 本次结界养成完成时间")
                print("        TIME- ----- ", Now)
                print("        TASK- ----- 结界养成任务完成 --------------------------------")
            else:
                print("        TASK- ----- 结界养成任务执行过程中出现错误 中断任务 --------------------------------")
        else:
            print("        SKIP- ----- 结界养成任务时间间隔未满六小时 跳过 --------------------------------")


def Jiejieyangcheng(current_state, Hwnd):
    # 重置结束标记
    Finish = 0
    print("        STEP- vvvvv 从{First_state}开始".format(First_state=current_state))
    for step in range(30):
        match current_state:
            case "庭院界面":
                # 先进入阴阳寮界面
                print("        INFO------ 尝试前往寮界面")
                Itface_guild(Hwnd)
                for Wait in range(3):
                    Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Jiejie.png", 0.05, 0)
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
                    Find = Find_Click_windows(Hwnd, "./pic/Sis/Tuichu3.png", 0.05, "点击关闭弹窗", "未检测到弹窗")
                    if Find:
                        Sleep_print(1)
                        print("        STEP- vvvvv 跳转寮界面")
                        current_state = "寮界面"
                    else:
                        print("        STEP- vvvvv 跳转异常退出界面")
                        current_state = "异常退出"

            case "寮界面":
                for i in range(5):
                    Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Jiejie.png", 0.05, 0)
                    if Find:
                        print("        INFO-", Matchs, "检测到结界入口")
                        Work_Salary(Hwnd)
                        Find = Find_Click_windows(Hwnd, "./pic/Sis/Jiejie.png", 0.05, "点击进入结界", "未检测到结界图标")
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
                        Find = Find_Click_windows(Hwnd, "./pic/Sis/Tuichu3.png", 0.05, "点击关闭弹窗", "未检测到弹窗")
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

                flag_yucheng = Yucheng("结界界面", Hwnd)

                # 领取体力食盒
                Tilishihe(Hwnd)

                # 经验酒壶 领取后育成
                if Jinyanjiuhu(Hwnd):
                    flag_yucheng = Yucheng("结界界面", Hwnd)

                # 领取体力食盒
                Tilishihe(Hwnd)

                if flag_Jiejieka:
                    flag_Jiejieka = Jiejieka(Hwnd)
                else:
                    # 新增结界卡运行判据 防止一直不填结界卡
                    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Jiejiekayunxing.png", 0.05, 0)
                    if Range:
                        print("        INFO-", Matchs, "结界卡依旧生效")
                    else:
                        print("        INFO-", Matchs, "结界卡似乎已耗尽")
                        flag_Jiejieka = Jiejieka(Hwnd)

                Finish = flag_yucheng and flag_Jiejieka
                if Finish:
                    print("        STEP- vvvvv 跳转结束")
                    current_state = "结束"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    current_state = "异常退出"

            case "结束":
                Esc_print(Hwnd)
                Sleep_print(2)
                for i in range(5):
                    Find = Find_Click_windows(Hwnd, "./pic/Sis/Tuichu.png", 0.05, "点击退出寮界面", "未检测到寮退出图标")
                    if Find:
                        Sleep_print(1)
                        break
                    else:
                        Sleep_print(3)
                        Esc_print(Hwnd)
                Itface_Host(Hwnd)
                return 1

            case "异常退出":
                Esc_print(Hwnd)
                Sleep_print(2)
                for i in range(5):
                    Find = Find_Click_windows(Hwnd, "./pic/Sis/Tuichu.png", 0.05, "点击退出寮界面", "未检测到寮退出图标")
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
    if Find_Click_windows(Hwnd, "./pic/Sis/Jinbigongzi.png", 0.05, "点击工资", "未检测到工资"):

        if Find_Click_windows(Hwnd, "./pic/Sis/Lingqu.png", 0.05, "领取工资", "领取工资异常"):
            Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
            if Find:
                print("        INFO-", Matchs, "领取体力工资成功")
                Esc_print(Hwnd)
                Sleep_print(1)

    if Find_Click_windows(Hwnd, "./pic/Sis/Tiligongzi.png", 0.05, "领取体力工资", "未检测到体力工资"):
        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
        if Find:
            print("        INFO-", Matchs, "领取体力工资成功")
            Esc_print(Hwnd)
            Sleep_print(1)

    Sleep_print(1)


def Jiyangjiangli(Hwnd):
    # 检测寄养奖励
    for i in range(1):
        if not Find_Click_windows(Hwnd, "./pic/Sis/Jiyangjingyan.png", 0.05, "检测到寄养奖励", "未检测到寄养奖励"):
            break
        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
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
        if not Find_Click_windows(Hwnd, "./pic/Sis/Tilingshihe.png", 0.05, "检测到体力食盒", "未检测到体力食盒溢出"):
            break

        Find_Click_windows(Hwnd, "./pic/Sis/Quchu.png", 0.05, "取出体力食盒", "取出体力食盒异常")
        Sleep_print(1)
        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
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
            Find_Click_windows(Hwnd, "./pic/Sis/Queding.png", 0.05, "育成有满级式神 强行提取", "经验酒壶提取成功")
            return 1

    Sleep_print(1)
    # 满经验酒壶情况
    if Find_Click_windows(Hwnd, "./pic/Sis/Jingyanjiuhu.png", 0.05, "检测到经验酒壶满", "经验酒壶未满"):
        Find_Click_windows(Hwnd, "./pic/Sis/Tiqu.png", 0.05, "提取满的经验酒壶", "提取满的经验酒壶失败")
        Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Tiqu.png", 0.05, 0)
        return Tiqu(Range, Matchs)
    else:
        # 不满经验酒壶情况
        if Find_Click_windows(Hwnd, "./pic/Sis/Jinyanjiuhu0.png", 0.05, "检测到有经验酒壶", "未检测到经验酒壶"):
            Find_Click_windows(Hwnd, "./pic/Sis/Tiqu.png", 0.05, "提取经验酒壶", "提取经验酒壶失败")
            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Tiqu.png", 0.05, 0)
            return Tiqu(Range, Matchs)
        else:
            return 0


def Jiejiekajiangli(Hwnd):
    Sleep_print(1)
    # 检测结界卡奖励
    for i in range(1):
        if Find_Click_windows(Hwnd, "./pic/Sis/Jiejiekajiangli.png", 0.05, "检测到结界卡奖励 点击领取", "未检测到结界卡结束奖励"):
            Sleep_print(0.5)
            Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0)
            if Find:
                print("        INFO-", Matchs, "结界卡奖励领取成功")
            else:
                print("        INFO-", Matchs, "结界卡奖励领取失败")
            return 0
        else:
            Find_Click_windows(Hwnd, "./pic/Sis/Jiejiekayunxing.png", 0.05, "检测到结界卡依旧运行 点击领取", "未检测到结界卡依旧运行")
            return 1


def Jiejieka(Hwnd):
    Sleep_print(1)
    # 进入结界卡界面
    for Wait in range(10):
        Find = Find_Click_windows(Hwnd, "./pic/Sis/Jiejieka.png", 0.07, "进入结界卡界面", "未进入结界卡界面")
        if Find:
            break
        else:
            print("        WAIT- wwwww 等待进入结界卡界面 已等待 {waittime} 秒".format(waittime=Wait + 1))
            Sleep_print(1)

    Sleep_print(1)
    # 放置结界卡
    for i in range(1):
        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Jiejiekacao.png", 0.05, 0)
        if not Find:
            print("        INFO-", Matchs, "结界卡未耗尽")
            Esc_print(Hwnd)
            Sleep_print(0.5)
            return 1
        else:
            print("        INFO-", Matchs, "结界卡已经耗尽")

            for i in range(1):
                if not Find_Click_windows(Hwnd, "./pic/Sis/Jiejiekaliebiao.png", 0.05, "打开结界卡列表", "打开结界卡列表异常"):
                    break
                if not Find_Click_windows(Hwnd, "./pic/Sis/Taiguliebiao.png", 0.05, "点击太鼓列表", "点击太鼓列表异常"):
                    break
                if not Find_Click_windows(Hwnd, "./pic/Sis/Xingjijiangxu.png", 0.05, "点击星级降序", "点击星级降序异常"):
                    break
                if not Find_Click_windows(Hwnd, "./pic/Sis/Shouzhangjiejieka.png", 0.05, "点击首张结界卡", "点击首张结界卡异常"):
                    if not Find_Click_windows(Hwnd, "./pic/Sis/Jiejiekaliebiao.png", 0.05, "打开结界卡列表", "打开结界卡列表异常"):
                        break
                    if not Find_Click_windows(Hwnd, "./pic/Sis/Douyuliebiao.png", 0.05, "点击斗鱼列表", "点击斗鱼列表异常"):
                        break
                    if not Find_Click_windows(Hwnd, "./pic/Sis/Shouzhangjiejieka.png", 0.05, "点击首张结界卡", "点击首张结界卡异常"):
                        break
                if not Find_Click_windows(Hwnd, "./pic/Sis/Jihuo.png", 0.05, "点击激活", "点击激活异常"):
                    break
                Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Yaoqing.png", 0.05, 0)
                if Range:
                    print("        INFO-", Matchs, "结界卡激活成功")
                    Sleep_print(1)
                    Esc_print(Hwnd)
                    Sleep_print(0.5)
                    return 1
                else:
                    print("        INFO-", Matchs, "结界卡激活失败")
                    return 0


def Yucheng(current_state, Hwnd):
    Sleep_print(1)
    # 进入结界育成
    print("        STEP- vvvvv 从{First_state}开始育成任务".format(First_state=current_state))
    for step in range(30):
        match current_state:
            case "结界界面":
                for Wait in range(10):
                    Find = Find_Click_windows(Hwnd, "./pic/Sis/Shishenyucheng.png", 0.05, "检测到进入结界育成界面", "未检测到进入结界育成界面")
                    if Find:
                        print("        STEP- vvvvv 跳转育成界面")
                        Sleep_print(1)
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
                # 放出满级式神
                for i in range(10):
                    if Find_Click_windows(Hwnd, "./pic/Sis/Manjidamo.png", 0.07, "检测到有满级式神", "未检测到有满级式神"):
                        Sleep_print(0.5)
                    else:
                        break
                        Sleep_print(0.5)

                Find = Find_Click_windows(Hwnd, "./pic/Sis/Fangrushishen.png", 0.05, "检测到有空位", "育成池已经放满")
                if Find:
                    # 进入素材列表
                    if Find_Click_windows(Hwnd, "./pic/Sis/Quanbu.png", 0.05, "进入全部式神列表", "正处在素材列表中"):
                        Sleep_print(0.5)
                        Find_Click_windows(Hwnd, "./pic/Sis/Sucai.png", 0.05, "选择素材列表", "选择素材列表异常")

                    for j in range(10):
                        Sleep_print(0.5)
                        if not Find_Click_windows(Hwnd, "./pic/Sis/Fengweidamo.png", 0.07, "放上去一个奉为达摩", "未检测到达摩素材"):
                            Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Yuchengliebioakuang.png", 0.05, 0)
                            print("        INFO-", Matchs, "进入翻页区域")
                            rect = win32gui.GetWindowRect(Hwnd)
                            x = (Range[0][0] + Range[1][0]) // 2 + rect[0]
                            y = (Range[0][1] + Range[1][1]) // 2 + rect[1]
                            pyautogui.moveTo(x, y)
                            Scroll_print(Hwnd, -5)
                        else:
                            break
                else:
                    print("        STEP- vvvvv 跳转寄养任务")
                    Sleep_print(1)
                    current_state = "寄养任务"

            case "寄养任务":
                Find = Find_Click_windows(Hwnd, "./pic/Sis/Jiyangrukou.png", 0.05, "检测到寄养空位", "已经有寄养")
                if Find:
                    card_handlers = {
                        "六星太鼓": lambda: Jiyang("寄养列表", Hwnd, "./pic/Sis/6xingtaigu.png", card),
                        "六星斗鱼": lambda: Jiyang("寄养列表", Hwnd, "./pic/Sis/6xingdouyu.png", card),
                        "五星太鼓": lambda: Jiyang("寄养列表", Hwnd, "./pic/Sis/5xingtaigu.png", card),
                        "五星斗鱼": lambda: Jiyang("寄养列表", Hwnd, "./pic/Sis/5xingdouyu.png", card),
                    }

                    for card in card_handlers:
                        Finish = card_handlers[card]()
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
                    Find = Find_Click_windows(Hwnd, "./pic/Sis/Shishenyucheng.png", 0.05, "检测到进入结界育成界面", "未检测到进入结界育成界面")
                    if Find:
                        print("        STEP- vvvvv 跳转育成界面")
                        Sleep_print(1)
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
                Find = Find_Click_windows(Hwnd, "./pic/Sis/Jiyangrukou.png", 0.05, "检测到寄养空位", "已经有寄养")
                if Find:
                    print("        STEP- vvvvv 跳转寄养列表")
                    Sleep_print(1)
                    current_state = "寄养列表"
                else:
                    print("        STEP- vvvvv 寄养任务完成")
                    return 1

            case "寄养列表":
                # 刷新好友结界卡列表
                Sleep_print(2)
                Find_Click_windows(Hwnd, "./pic/Sis/Kuaqu.png", 0.05, "点击跨区", "点击跨区异常")
                Sleep_print(2)
                Find_Click_windows(Hwnd, "./pic/Sis/Haoyou.png", 0.05, "点击好友", "点击好友异常")
                # 寻找对应结界卡
                for times in range(100):
                    Range, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Jiyangliebiao.png", 0.05, 0)
                    print("        INFO-", Matchs, "移动到寄养列表")
                    rect = win32gui.GetWindowRect(Hwnd)
                    x = (Range[0][0] + Range[1][0]) // 2 + rect[0]
                    y = (Range[0][1] + Range[1][1]) // 2 + rect[1]
                    pyautogui.moveTo(x, y)

                    Str1 = "检测到" + string
                    Str2 = "未检测到" + string
                    Find = Find_Click_windows(Hwnd, Jiejieka_Model_path, 0.05, Str1, Str2)
                    if Find_Click_windows(Hwnd, Jiejieka_Model_path, 0.05, Str1, Str2):
                        if Find_Click_windows(Hwnd, "./pic/Sis/Jinrujiejie.png", 0.05, "点击进入结界", "点击进入结界异常"):
                            Sleep_print(2)
                            break
                    else:
                        Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Jiyangliebiaomowei.png", 0.001, 0)
                        if Find:
                            print("        INFO-", Matchs, "已经到寄养列表末尾")
                            return 0
                        else:
                            print("        INFO-", Matchs, "未到寄养列表末尾")
                            Scroll_print(Hwnd, -5)

                if Find:
                    print("        STEP- vvvvv 跳转寄养结界")
                    Sleep_print(1)
                    current_state = "寄养结界"
                else:
                    print("        STEP- vvvvv 跳转异常退出界面")
                    Sleep_print(1)
                    return 0

            case "寄养结界":
                Find = Find_Click_windows(Hwnd, "./pic/Sis/youjiyangwei.png", 0.05, "有寄养位", "结界已被占用")
                if not Find:
                    Esc_print(Hwnd)
                    Sleep_print(0.5)
                    Esc_print(Hwnd)
                    Sleep_print(2)
                    return Jiyang("结界界面", Hwnd, Jiejieka_Model_path, string)
                else:
                    # 进入素材列表
                    if Find_Click_windows(Hwnd, "./pic/Sis/Quanbu.png", 0.05, "进入全部式神列表", "正处在素材列表中"):
                        Sleep_print(0.5)
                        Find_Click_windows(Hwnd, "./pic/Sis/Sucai.png", 0.05, "选择素材列表", "选择素材列表异常")

                    for j in range(10):
                        if not Find_Click_windows(Hwnd, "./pic/Sis/Fengweidamo.png", 0.07, "放上去一个奉为达摩", "未检测到达摩素材"):
                            Find, Matchs = Find_in_windows_Matchs(Hwnd, "./pic/Sis/Yuchengliebioakuang.png", 0.05, 0)
                            print("        INFO-", Matchs, "进入翻页区域")
                            rect = win32gui.GetWindowRect(Hwnd)
                            x = (Find[0][0] + Find[1][0]) // 2 + rect[0]
                            y = (Find[0][1] + Find[1][1]) // 2 + rect[1]
                            pyautogui.moveTo(x, y)
                            Scroll_print(Hwnd, -5)
                        else:
                            Find_Click_windows(Hwnd, "./pic/Sis/Queding.png", 0.05, "点击确定", "点击确定异常")
                            Esc_print(Hwnd)
                            Sleep_print(2)
                            Esc_print(Hwnd)
                            Sleep_print(2)
                            return Jiyang("结界界面", Hwnd, Jiejieka_Model_path, string)
