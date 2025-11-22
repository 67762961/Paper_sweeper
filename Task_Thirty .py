import Lib
from Lib import Sleep_print


def MainTask_Thirty(Hwnd):
    """
    有关三十的相关任务
    @param Hwnd:    窗口句柄
    """
    # 先进入阴阳寮界面
    Lib.Itface_guild(Hwnd)

    # 开始领取工资任务
    print("TASK- +++++ 开始领取工资任务 ++++++++++++++++++++++++++++++++")
    Sleep_print(0.5)
    if Work_Salary(Hwnd):
        print("TASK- ----- 领取工资任务完成 --------------------------------")
    else:
        print("EROR- ***** 领取工资任务失败 ********************************")

    # 开始结界寄养任务
    print("TASK- +++++ 开始结界寄养任务 ++++++++++++++++++++++++++++++++")
    Sleep_print(0.5)
    if Work_Foster(Hwnd):
        print("TASK- ----- 结界寄养任务完成 --------------------------------")
    else:
        print("EROR- ***** 结界寄养任务失败 ********************************")
