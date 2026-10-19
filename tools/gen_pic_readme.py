# -*- coding: utf-8 -*-
"""生成 pic/README.md 索引

内容：每个目录的业务说明、图片清单（中文名）、引用模块、用途。
"""
import ast
import os
import re
import collections

PROJ = r"D:\WORKS\Python\Paper_sweeper"
PIC = os.path.join(PROJ, "pic")
FILES = ["Lib.py", "Task_SignIn.py", "Task_Fengmo.py", "Task_Digui.py",
         "Task_Jiejieyangcheng.py", "Task_JiejieFight.py",
         "Task_Shouliezhan.py", "Task_Thirty.py"]

# 目录说明
DIR_DESC = {
    "common": "公用元素：跨多个任务使用的通用界面元素（确定、关闭、获得奖励等）",
    "courtyard": "庭院：主界面本身与庭院上的功能入口（逢魔、麒麟、宴会等）",
    "signin": "登录收菜：邮件、每日一签、福袋、纸人、免费礼包、友情点",
    "guild": "结界养成：阴阳寮工资、寄养、结界卡、式神育成、食盒酒壶",
    "breakthrough": "结界突破",
    "digui": "地域鬼王",
    "fengmo": "逢魔之时",
    "hunt": "狩猎战：麒麟、阴界之门",
    "thirty": "寮三十：御魂协作刷本与真蛇",
    "team": "编队：预设编组与编队（部分由 Team_Preset 动态拼接）",
}

# 目录排序
DIR_ORDER = ["common", "courtyard", "signin", "guild", "breakthrough",
             "digui", "fengmo", "hunt", "thirty", "team"]

# 用途说明（按文件名关键字，用于自动补充）
USAGE_HINTS = {
    "确定": "确认按钮",
    "关闭": "关闭按钮（×）",
    "获得奖励": "奖励获得弹窗",
    "拒绝协作": "拒绝协作邀请",
    "适龄提示标": "适龄提示",
    "一键返回庭院": "一键返回庭院",
    "退出标志": "界面退出标志",
    "前往": "前往按钮",
    "主界面": "庭院主界面",
    "入口": "庭院功能入口",
    "式神录": "式神录入口",
    "阴阳术": "阴阳术入口",
    "御神": "御神入口",
    "退出游戏": "退出游戏确认",
    "取消退出": "取消退出",
    "邮件": "邮件入口",
    "邮箱": "邮箱界面",
    "全部领取": "全部领取",
    "消息邮件": "消息邮件",
    "每日一签": "每日签到",
    "小纸人": "小纸人领取",
    "商店": "商店入口",
    "礼包屋": "礼包屋入口",
    "日常": "日常分类",
    "免费礼包": "免费礼包",
    "好友": "好友界面",
    "吉闻": "吉闻界面",
    "祝福": "祝福",
    "收取": "一键收取",
    "友情点": "友情点切换",
    "万华牌": "万华牌跳过",
    "结界卡": "结界卡",
    "寄养": "寄养",
    "体力工资": "体力工资",
    "体力食盒": "体力食盒",
    "经验酒壶": "经验酒壶",
    "金币工资": "金币工资",
    "领取": "领取按钮",
    "取出": "取出按钮",
    "提取": "提取按钮",
    "达摩": "达摩素材",
    "放入式神": "放入式神",
    "式神育成": "式神育成",
    "素材": "素材列表",
    "全部": "全部列表",
    "育成列表框": "育成列表框",
    "跨区": "跨区",
    "进入结界": "进入结界",
    "激活": "激活",
    "邀请": "邀请",
    "斗鱼列表": "斗鱼列表",
    "太鼓列表": "太鼓列表",
    "星级降序": "星级降序",
    "首张结界卡": "首张结界卡",
    "关闭弹窗": "关闭弹窗",
    "阴阳寮": "阴阳寮",
    "有寄养位": "有寄养位",
    "太鼓": "太鼓结界卡",
    "斗鱼": "斗鱼结界卡",
    "地鬼图标": "地域鬼王入口",
    "今日挑战": "今日挑战",
    "热门": "热门排序",
    "筛选": "筛选",
    "胜利": "胜利结算",
    "挑战": "挑战按钮",
    "未选择": "未选择状态",
    "战斗奖励": "战斗奖励",
    "准备": "准备按钮",
    "最新": "最新排序",
    "第一个": "第一个目标",
    "第二个": "第二个目标",
    "第三个": "第三个目标",
    "定位": "定位按钮",
    "逢魔次数": "逢魔次数",
    "逢魔极": "逢魔-极",
    "逢魔奖励": "逢魔奖励",
    "逢魔图标": "逢魔图标",
    "集结": "集结",
    "首领": "首领",
    "现世逢魔": "现世逢魔",
    "阵容预设": "阵容预设",
    "出战": "出战按钮",
    "编组": "预设编组",
    "编队": "预设编队",
    "预设登陆": "预设入口",
    "预设选项": "预设选项",
    "应用御魂预设": "应用御魂预设",
}


def guess_usage(filename):
    """根据文件名猜用途"""
    stem = os.path.splitext(filename)[0]
    for key, desc in USAGE_HINTS.items():
        if key in stem:
            return desc
    return ""


def collect_refs():
    """{图片相对路径: set(引用模块)}"""
    refs = collections.defaultdict(set)
    for f in FILES:
        src = open(os.path.join(PROJ, f), encoding="utf-8").read()
        mod = os.path.splitext(f)[0]
        for m in re.finditer(r'"(\./pic/[^"]+)"', src):
            refs[m.group(1)].add(mod)
    return refs


def main():
    refs = collect_refs()

    lines = [
        "# 模板图目录索引",
        "",
        "> 本文件由 `tools/gen_pic_readme.py` 自动生成，列出每个目录的用途与图片清单。",
        "> 修改图片后请运行 `python tools/check_pics.py` 校验引用，并重新生成本文件。",
        "",
        "## 目录结构",
        "",
        "```",
        "pic/",
    ]
    for d in DIR_ORDER:
        dp = os.path.join(PIC, d)
        if not os.path.isdir(dp):
            continue
        n = len([f for f in os.listdir(dp) if f.lower().endswith(".png")])
        lines.append(f"├── {d}/" + " " * max(1, 18 - len(d)) + f"# {DIR_DESC.get(d, '')}（{n} 张）")
    lines.append("```")
    lines.append("")

    total = 0
    for d in DIR_ORDER:
        dp = os.path.join(PIC, d)
        if not os.path.isdir(dp):
            continue
        files = sorted(f for f in os.listdir(dp) if f.lower().endswith(".png"))
        total += len(files)
        lines.append(f"## `{d}/`（{len(files)} 张）")
        lines.append("")
        lines.append(f"{DIR_DESC.get(d, '')}")
        lines.append("")
        lines.append("| 图片 | 用途 | 引用模块 |")
        lines.append("| ---- | ---- | ---- |")
        for fn in files:
            rel = f"./pic/{d}/{fn}"
            mods = sorted(refs.get(rel, []))
            mod_str = "、".join(f"`{m}`" for m in mods) if mods else "（动态拼接）"
            usage = guess_usage(fn)
            lines.append(f"| `{fn}` | {usage} | {mod_str} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"**共 {total} 张模板图，{len(DIR_ORDER)} 个目录。**")
    lines.append("")
    lines.append("## 维护说明")
    lines.append("")
    lines.append("- **新增图片**：放进对应业务目录，文件名用中文；在代码里引用后运行 `python tools/check_pics.py`。")
    lines.append("- **改名/移动**：用 `git mv` 保留历史，同步修改代码引用，再跑 `check_pics.py`。")
    lines.append("- **动态拼接**：`team/` 目录下的编队图由 `Lib.Team_Preset()` 用 f-string 拼接，")
    lines.append("  路径形如 `./pic/team/{Preset_name}.png`，`check_pics.py` 会跳过该目录的死图判定。")
    lines.append("- **中文文件名**：读取走 `Lib.Img_read_ch()`（`np.frombuffer` + `cv2.imdecode`），支持任意编码路径。")
    lines.append("")

    out = os.path.join(PIC, "README.md")
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))
    print(f"已生成 {out}")
    print(f"  {total} 张图，{len(DIR_ORDER)} 个目录，{len(lines)} 行")


if __name__ == "__main__":
    main()
