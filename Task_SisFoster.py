import Lib
import pyautogui
import pydirectinput
import ctypes
import win32gui
from datetime import datetime, timedelta
from Lib import Sleep_print
from Lib import Find_in_windows, Find_Click_windows, Click, Itface_Host, Itface_guild, read_config, write_config


def Work_Salary(Hwnd):
    """
    阴阳寮工资和体力
    :param Hwnd:    窗口句柄
    :return:        1正常0异常
    """
    # 领取阴阳寮奖励
    for i in range(1):
        if not Find_Click_windows(Hwnd, "./pic/Sis/Jinbigongzi.png", 0.05, "点击工资", "未检测到工资"):
            break
        Find_Click_windows(Hwnd, "./pic/Sis/Lingqu.png", 0.05, "领取工资", "领取工资异常")

        if Find_in_windows(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0):
            print("领取工资成功")
            pydirectinput.press("esc")
            print("QUIT- ccccc 按Esc退出")
            Sleep_print(0.5)
        else:
            print("工资似乎领取失败")

    for i in range(1):
        if not Find_Click_windows(Hwnd, "./pic/Sis/Tiligongzi.png", 0.05, "领取体力工资", "未检测到体力工资"):
            break

        if Find_in_windows(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0):
            print("领取体力工资成功")
            pydirectinput.press("esc")
            print("QUIT- ccccc 按Esc退出")
            Sleep_print(0.5)
        else:
            print("体力工资似乎领取失败")


def Work_Foster(Hwnd):
    """
    结界养成
    :param Hwnd:    窗口句柄
    :return:        1正常0异常
    """

    # 进入结界
    Find_Click_windows(Hwnd, "./pic/Sis/Jiejie.png", 0.05, "进入结界", "未检测到结界入口")
    Sleep_print(3)

    def Jiyang():
        # 检测寄养奖励
        for i in range(1):
            if not Find_Click_windows(Hwnd, "./pic/Sis/Jiyangjingyan.png", 0.05, "检测到寄养奖励", "未检测到寄养奖励"):
                break

            if Find_in_windows(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0):
                print("寄养奖励领取成功")
                pydirectinput.press("esc")
                print("QUIT- ccccc 按Esc退出")
                Sleep_print(0.5)
            else:
                print("寄养奖励领取失败")

    def Tilishihe():
        Sleep_print(0.5)
        # 检测体力食盒
        for i in range(1):
            if not Find_Click_windows(Hwnd, "./pic/Sis/Tilingshihe.png", 0.05, "检测到体力食盒", "未检测到体力食盒溢出"):
                break

            Find_Click_windows(Hwnd, "./pic/Sis/Quchu.png", 0.05, "取出体力食盒", "取出体力食盒异常")

            if Find_in_windows(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0):
                print("体力食盒领取成功")
                pydirectinput.press("esc")
                print("QUIT- ccccc 按Esc退出")
                Sleep_print(0.5)
                pydirectinput.press("esc")
                print("QUIT- ccccc 按Esc退出")
                Sleep_print(0.5)
                return 1
            else:
                print("体力食盒领取失败")

    def Jinyanjiuhu():
        Sleep_print(1)
        # 检测经验酒壶
        if not Find_Click_windows(Hwnd, "./pic/Sis/Jingyanjiuhu.png", 0.05, "检测到经验酒壶满", "经验酒壶未满"):
            Find_Click_windows(Hwnd, "./pic/Sis/Jinyanjiuhu0.png", 0.05, "检测到有经验酒壶", "未检测到经验酒壶")

        Find_Click_windows(Hwnd, "./pic/Sis/Tiqu.png", 0.05, "提取满的经验酒壶", "经验酒壶未满")
        Range = Find_in_windows(Hwnd, "./pic/Sis/Tiqu.png", 0.05, 0)
        if Range:
            pydirectinput.press("esc")
            print("QUIT- ccccc 按Esc退出")
            print("经验酒壶提取上限")
        else:
            print("经验酒壶提取未到上限")
            Find_Click_windows(Hwnd, "./pic/Sis/Queding.png", 0.05, "育成有满级式神 强行提取", "经验酒壶提取成功")
            return 1

    def Jiejiekajiangli():
        Sleep_print(1)
        # 检测太鼓奖励
        for i in range(1):
            if Find_Click_windows(Hwnd, "./pic/Sis/Jiejiekajiangli.png", 0.05, "检测到结界卡奖励 点击领取", "未检测到结界卡结束奖励"):
                if Find_in_windows(Hwnd, "./pic/Main/Huodejiangli.png", 0.05, 0):
                    print("结界卡奖励领取成功")
                    return 1
                else:
                    print("结界卡奖励领取失败")
                    return 0
            else:
                Find_Click_windows(Hwnd, "./pic/Sis/Jiejiekayunxing.png", 0.05, "检测到结界卡依旧运行 点击领取", "未检测到结界卡依旧运行")
                return 2

    def Jiejieka():
        Sleep_print(1)
        # 进入结界卡界面
        for i in range(3):
            if Find_Click_windows(Hwnd, "./pic/Sis/Jiejieka.png", 0.07, "进入结界卡界面", "未进入结界卡界面"):
                break

        Sleep_print(1)
        # 放置结界卡
        for i in range(1):
            if not Find_in_windows(Hwnd, "./pic/Sis/Jiejiekacao.png", 0.05, 0):
                print("结界卡未耗尽")
                pydirectinput.press("esc")
                print("QUIT- ccccc 按Esc退出")
                Sleep_print(0.5)
                break
            else:
                print("结界卡已经耗尽")

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

                    if Find_in_windows(Hwnd, "./pic/Sis/Yaoqing.png", 0.05, 0):
                        print("结界卡激活成功")
                        Sleep_print(1)
                        pydirectinput.press("esc")
                        print("QUIT- ccccc 按Esc退出")
                        Sleep_print(0.5)
                        return 1
                    else:
                        print("结界卡激活失败")
                        return 0

    def Yucheng():
        Sleep_print(1)
        # 进入结界育成

        for i in range(10):
            if Find_Click_windows(Hwnd, "./pic/Sis/Shishenyucheng.png", 0.05, "检测到进入结界育成界面", "未检测到进入结界育成界面"):
                break
            else:
                Sleep_print(1)

        # 检测是否有满级式神
        Sleep_print(0.5)

        for i in range(10):
            if Find_Click_windows(Hwnd, "./pic/Sis/Manjidamo.png", 0.07, "检测到有满级式神", "未检测到有满级式神"):
                Sleep_print(0.5)
            else:
                break
                Sleep_print(1)

        Sleep_print(0.5)
        for i in range(10):
            if not Find_Click_windows(Hwnd, "./pic/Sis/Fangrushishen.png", 0.05, "检测到有空位", "育成池已经放满"):
                Sleep_print(0.5)
                break
            else:
                Sleep_print(0.5)

                # 进入素材列表
                if Find_Click_windows(Hwnd, "./pic/Sis/Quanbu.png", 0.05, "进入全部式神列表", "正处在素材列表中"):
                    Sleep_print(0.5)
                    Find_Click_windows(Hwnd, "./pic/Sis/Sucai.png", 0.05, "选择素材列表", "选择素材列表异常")

                for j in range(10):
                    if not Find_Click_windows(Hwnd, "./pic/Sis/Fengweidamo.png", 0.03, "放上去一个奉为达摩", "未检测到达摩素材"):
                        Range = Find_in_windows(Hwnd, "./pic/Sis/Yuchengliebioakuang.png", 0.05, 0)
                        print("进入翻页区域")
                        rect = win32gui.GetWindowRect(Hwnd)
                        x = (Range[0][0] + Range[1][0]) // 2 + rect[0]
                        y = (Range[0][1] + Range[1][1]) // 2 + rect[1]
                        pyautogui.moveTo(x, y)
                        pyautogui.scroll(-500)
                    else:
                        break

        # 寄养
        if not Find_Click_windows(Hwnd, "./pic/Sis/Jiyangrukou.png", 0.05, "检测到寄养空位", "已经有寄养"):
            pydirectinput.press("esc")
            print("QUIT- ccccc 按Esc退出")
            Sleep_print(3)
            return 1

        def Jiyang(Jiejieka_Model_path, string):
            flag_jiyangqueding = 0

            Find_Click_windows(Hwnd, "./pic/Sis/Kuaqu.png", 0.05, "点击跨区", "点击跨区异常")

            Find_Click_windows(Hwnd, "./pic/Sis/Haoyou.png", 0.05, "点击好友", "点击好友异常")

            Find_Click_windows(Hwnd, "./pic/Sis/Jiyangliebiao.png", 0.05, "点击寄养列表", "点击寄养列表异常")

            for o in range(50):
                if flag_jiyangqueding:
                    break

                Sleep_print(0.5)
                Range = Find_in_windows(Hwnd, Jiejieka_Model_path, 0.05, 0)
                if Range:
                    for i in range(1):
                        Sleep_print(1)
                        Click(Hwnd, Range, 1)
                        print("检测到", end="")
                        print(string)

                        if Find_Click_windows(Hwnd, "./pic/Sis/Jinrujiejie.png", 0.05, "点击进入结界", "点击进入结界异常"):
                            Sleep_print(2)

                        if not Find_Click_windows(Hwnd, "./pic/Sis/youjiyangwei.png", 0.05, "有寄养位", "结界已被占用"):
                            pydirectinput.press("esc")
                            print("QUIT- ccccc 按Esc退出")
                            Sleep_print(0.5)
                            pydirectinput.press("esc")
                            print("QUIT- ccccc 按Esc退出")
                            Sleep_print(2)
                            break

                        # 进入素材列表
                        if Find_Click_windows(Hwnd, "./pic/Sis/Quanbu.png", 0.05, "进入全部式神列表", "正处在素材列表中"):
                            Sleep_print(0.5)
                            Find_Click_windows(Hwnd, "./pic/Sis/Sucai.png", 0.05, "选择素材列表", "选择素材列表异常")

                        for j in range(10):
                            if not Find_Click_windows(Hwnd, "./pic/Sis/Fengweidamo.png", 0.04, "放上去一个奉为达摩", "未检测到达摩素材"):
                                Range = Find_in_windows(Hwnd, "./pic/Sis/Yuchengliebioakuang.png", 0.05, 0)
                                print("进入翻页区域")
                                rect = win32gui.GetWindowRect(Hwnd)
                                x = (Range[0][0] + Range[1][0]) // 2 + rect[0]
                                y = (Range[0][1] + Range[1][1]) // 2 + rect[1]
                                pyautogui.moveTo(x, y)
                                pyautogui.scroll(-500)
                                pyautogui.scroll(-100)
                            else:
                                Find_Click_windows(Hwnd, "./pic/Sis/Queding.png", 0.05, "点击确定", "点击确定异常")
                                pydirectinput.press("esc")
                                print("QUIT- ccccc 按Esc退出")
                                Sleep_print(2)
                                pydirectinput.press("esc")
                                print("QUIT- ccccc 按Esc退出")
                                Sleep_print(2)
                                flag_jiyangqueding = 1
                                return 0
                else:
                    print("未检测到", end="")
                    print(string)
                    if Find_in_windows(Hwnd, "./pic/Sis/Jiyangliebiaomowei.png", 0.001, 0):
                        print("已经到寄养列表末尾")
                        return 1
                        break
                    else:
                        pyautogui.scroll(-400)
                        print("往下翻页")

        flag_Jiyang = Jiyang("./pic/Sis/6xingtaigu.png", "六星太鼓")
        if flag_Jiyang:
            flag_Jiyang = Jiyang("./pic/Sis/6xingdouyu.png", "六星斗鱼")
            if flag_Jiyang:
                flag_Jiyang = Jiyang("./pic/Sis/5xingtaigu.png", "五星太鼓")
                if flag_Jiyang:
                    flag_Jiyang = Jiyang("./pic/Sis/5xingdouyu.png", "五星斗鱼")
                    if flag_Jiyang:
                        return 1

    # 领取寄养
    Jiyang()

    flag_Jiejieka = 0
    flag_yucheng = 0

    # 领取结界卡奖励 领取后育成
    if 1 == Jiejiekajiangli():
        flag_Jiejieka = 1
    else:
        flag_Jiejieka = 0

    if Yucheng():
        flag_yucheng = 1

    # 领取体力食盒
    Tilishihe()

    # 经验酒壶 领取后育成
    if Jinyanjiuhu():
        if Yucheng():
            flag_yucheng = 1
    if flag_Jiejieka == 1:
        Jiejieka()
    else:
        # 新增结界卡运行判据 防止一直不填结界卡
        Range = Find_in_windows(Hwnd, "./pic/Sis/Jiejiekayunxing.png", 0.05, 0)
        if Range:
            print("结界卡依旧生效")
        else:
            print("结界卡似乎已耗尽")
            Jiejieka()

    # 回到寮界面
    pydirectinput.press("esc")
    print("QUIT- ccccc 按Esc退出")
    Sleep_print(2)

    return Find_Click_windows(Hwnd, "./pic/Sis/Tuichu.png", 0.05, "退出寮界面", "退出寮界面异常")


def MainTask_Sisfoster(Hwnd, Account):
    """
    有关结界寄养相关任务
    :param Hwnd:    窗口句柄
    """
    print("TASK- +++++ 开始结界寄养任务 ++++++++++++++++++++++++++++++++")

    # 读取上次结界任务时间
    config = read_config("./config/Last_times.json")
    Times_jiejieyangcheng_str = config[Account].get("Times_jiejieyangcheng", None)
    Times_jiejieyangcheng = datetime.fromisoformat(Times_jiejieyangcheng_str) if Times_jiejieyangcheng_str else None
    current_time = datetime.now()
    if Times_jiejieyangcheng is not None:
        print("TIME- ----- 上次结界养成时间:")
        print("TIME- ----- ", Times_jiejieyangcheng.strftime("%Y-%m-%d %H:%M:%S"))
        time_diff = (current_time - Times_jiejieyangcheng).total_seconds() / 60 / 60
    else:
        print("TIME- ----- 没有记录上次结界养成时间")
        one_week_ago = current_time - timedelta(weeks=1)
        config[Account]["Times_jiejieyangcheng"] = one_week_ago.isoformat()
        write_config("./config/Last_times.json", config)
        time_diff = 7 * 24

    if time_diff > 6:
        # 先进入阴阳寮界面
        Itface_guild(Hwnd)

        # 开始领取工资任务
        Sleep_print(2)
        Work_Salary(Hwnd)

        # 开始结界寄养任务
        Sleep_print(0.5)
        if Work_Foster(Hwnd):
            Now = current_time.strftime("%Y-%m-%d %H:%M:%S")
            config[Account]["Times_jiejieyangcheng"] = Now
            print("TIME- ----- 本次结界养成时间:")
            print("TIME- ----- ", Now)
            write_config("./config/Last_times.json", config)
            print("TASK- ----- 结界寄养任务完成 --------------------------------")
            Sleep_print(2)
        else:
            print("EROR- XXXXX 结界寄养任务失败 XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    else:
        print("SKIP- ----- 跳过结界养成任务 --------------------------------")
