# -*- coding: utf-8 -*-
"""寄养列表扫描与择优：一趟扫完、档内取最大、档间按优先级、封顶早停、读不出回退。

这些逻辑全都在 Task_Jiejieyangcheng 里，但它只依赖几个可替换的原语
（截图、模板匹配、读数、滚动、点击），所以可以整段替换成假的，
在纯逻辑层面验证「选谁」这件事——真机验证留给手动单跑。

重点覆盖六条容易写错的规则：
1. 一趟扫完，四档吃同一帧截图（不是四趟）；
2. 档内比数字取最大（59 输给 67）；
3. 档间按优先级取第一个有货的，**不比数字大小**（六星太鼓 67 胜过六星斗鱼 151）；
4. 本类型封顶后，本档剩余行不再点，但**其他档照常扫**；
5. 全部读不出时回退成第一个命中，而不是当作「本档没有卡」；
6. 滚动前必须把鼠标放回列表上——滚轮作用在鼠标位置，鼠标不在列表上就滚不动。
"""
import numpy as np
import pytest

import Lib
import Task_Jiejieyangcheng as Task


# ---------------------------------------------------------------- 假环境


class FakeList:
    """模拟寄养列表：每屏若干行，每行标注它属于哪个档位、收益是多少

    :param screens: 每屏一个列表，元素是 ``(档位名, 收益值)``；
                    收益为 None 表示这张卡的数字读不出
    :param ended:   每一屏是否已经到底（末尾露出空白格）
    :param flip:    模拟「点开之后卡面被刷新成另一种」：键是 ``(屏号, 行号)``，
                    值是依次要变过去的档位名列表，每点一次前进一格。
                    列表只有一个元素时就是「一直变回同一种」。

    另外模拟一个真机上的关键行为：**滚轮只作用于鼠标位置**。
    鼠标不在列表上时 scroll 什么也不做——这正是「滚不动」被误判成
    「列表到头」的成因，所以假环境必须能复现它。
    """

    # 列表模板在画面里的位置（假坐标）。各行都落在这个区域内：
    # 点过左边某一行之后，鼠标本来就在列表上，可以直接滚。
    LIST_BOX = [[0, 0], [300, 200]]

    # 假画面尺寸。必须比最长的一行坐标（40 * 行数 + 30）加复核外扩还大，
    # 否则 Jiyang_row_type 裁出来的块会小于 8 像素而一律返回 None。
    SHAPE = (300, 400, 3)

    def __init__(self, screens, ended=None, flip=None):
        self.screens = screens
        self.ended = ended or [False] * (len(screens) - 1) + [True]
        self.flip = flip or {}
        self.flip_step = {}         # (屏号, 行号) -> 已经变到第几个
        self.screen_index = 0
        self.clicked = []           # [(屏号, 行号)]
        self.screens_visited = []
        # 初始鼠标停在列表外（真机上停「好友」页签就是这么个状态）
        self.mouse = (500, 500)
        self.scroll_attempts = 0    # 尝试滚动了几次（含滚不动的）
        self.dead_scrolls = 0       # 其中「鼠标不在列表上」而空转的次数
        self.list_looks = 0         # 「找列表位置」的匹配次数
        self.sleeps = []            # 每次静默等待的秒数
        self.trace = []             # 动作顺序：('scroll', 屏号) / ('sleep', 秒) / ('shot', 屏号)

    # ---- 截图与匹配 ----
    def screenshot(self, Hwnd):
        """按屏号给出不同画面"""
        self.trace.append(("shot", self.screen_index))
        img = np.zeros(self.SHAPE, dtype=np.uint8)
        img[:, :, 0] = (self.screen_index * 23 + 5) % 255
        img[:, :, 1] = (self.screen_index * 41 + 9) % 255
        return img

    def match_one(self, Img, models, Threshold):
        """一次匹配一个位置：末尾空白格 / 寄养列表本身"""
        name = models[0][0]
        if name == "末尾":
            return [("末尾", [[0, 0], [1, 1]], "0.000")] if self.ended[self.screen_index] else []
        if name == "列表":
            self.list_looks += 1
            return [("列表", self.LIST_BOX, "0.000")]
        return []

    def match_all(self, Img, Model_path, Threshold, max_matches=10):
        """只返回属于 Model_path 对应档位的行（回滚定位用）"""
        card_name = Model_path.rsplit("/", 1)[-1].replace(".png", "")
        rows = []
        for i, (name, _value) in enumerate(self.screens[self.screen_index]):
            if name == card_name:
                rows.append([[0, 40 * i], [100, 40 * i + 30]])
        return rows

    def match_rows(self, Img, Models, Threshold, max_matches=8):
        """本屏每一行只报一次，类型由行内比分数决出

        真机上四张模板共用托盘与星点，逐张模板各找各的会把同一行报两次；
        Match_models_rows 的职责就是聚行后在行内裁决。这里模拟它的结果：
        每行只出一条，类型是该行的真实类型。
        """
        card_names = {name for name, _pic in Models}
        rows = []
        for i, (name, _value) in enumerate(self.screens[self.screen_index]):
            if name in card_names:
                rows.append((name, [[0, 40 * i], [100, 40 * i + 30]], "0.010"))
        return rows

    def recheck(self, Img, row, priority_cards):
        """替身版的 Jiyang_row_type：按 flip 表返回点开之后看到的类型

        真机上这一行会在滚轮翻页后被游戏重绘成另一种卡面，这里用
        ``flip`` 表按「点了几次」逐次推进来复现。
        """
        index = row[0][1] // 40
        key = (self.screen_index, index)
        if key not in self.flip:
            return self.screens[self.screen_index][index][0]
        seq = self.flip[key]
        step = self.flip_step.get(key, 0)
        self.flip_step[key] = step + 1
        return seq[min(step, len(seq) - 1)]

    # ---- 交互 ----
    def _in_list(self):
        """鼠标是否落在列表区域内"""
        (x0, y0), (x1, y1) = self.LIST_BOX
        x, y = self.mouse
        return x0 <= x <= x1 and y0 <= y <= y1

    def scroll(self, Hwnd, length):
        self.scroll_attempts += 1
        self.trace.append(("scroll", self.screen_index))
        if not self._in_list():
            # 真机就是这个行为：鼠标不在列表上，滚轮落在别处，列表纹丝不动
            self.dead_scrolls += 1
            return
        if length < 0:
            self.screen_index = min(self.screen_index + 1, len(self.screens) - 1)
            self.screens_visited.append(self.screen_index)
        elif length > 0:
            self.screen_index = max(self.screen_index - 1, 0)

    def move(self, Hwnd, Loc):
        """把鼠标移到框中心"""
        cx = (Loc[0][0] + Loc[1][0]) // 2
        cy = (Loc[0][1] + Loc[1][1]) // 2
        self.mouse = (cx, cy)
        return self.mouse

    def click(self, Hwnd, Loc, Wait):
        self.clicked.append((self.screen_index, Loc[0][1] // 40))
        return 1

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.trace.append(("sleep", seconds))

    # ---- 读数 ----
    def read_yield(self, Img):
        screen, row = self.clicked[-1]
        return self.screens[screen][row][1]


@pytest.fixture()
def fake(monkeypatch):
    """返回一个工厂：传入屏数据，得到装好假原语的环境"""

    def build(screens, ended=None, flip=None):
        env = FakeList(screens, ended, flip)
        monkeypatch.setattr(Task, "Screenshot_window", env.screenshot)
        monkeypatch.setattr(Task, "Match_models_in_image", env.match_one)
        monkeypatch.setattr(Task, "Match_models_in_image_all", env.match_all)
        monkeypatch.setattr(Task, "Match_models_rows", env.match_rows)
        monkeypatch.setattr(Task, "Jiyang_row_type", env.recheck)
        monkeypatch.setattr(Task, "jiejie_read_yield", env.read_yield)
        monkeypatch.setattr(Task, "Scroll_print", env.scroll)
        monkeypatch.setattr(Task, "Move_to_range", env.move)
        monkeypatch.setattr(Task, "Click", env.click)
        monkeypatch.setattr(Task, "Sleep_quiet", env.sleep)
        return env

    return build


PRIORITY = (
    ("六星太鼓", "./pic/guild/六星太鼓.png"),
    ("六星斗鱼", "./pic/guild/六星斗鱼.png"),
    ("五星太鼓", "./pic/guild/五星太鼓.png"),
    ("五星斗鱼", "./pic/guild/五星斗鱼.png"),
)


def _card(name, value):
    """一行：(档位名, 收益)"""
    return (name, value)


# ------------------------------------------------------------ 档内取最大


def test_picks_highest_value_within_tier(fake):
    """同一档里扫到 67 和 59，必须选 67"""
    env = fake(screens=[[_card("六星太鼓", 67), _card("六星太鼓", 59)]])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["name"] == "六星太鼓"
    assert found["value"] == 67


def test_scans_all_screens_before_deciding(fake):
    """最优值可能在后一屏，不能在第一屏就收工"""
    env = fake(screens=[[_card("六星太鼓", 59)], [_card("六星太鼓", 76)]])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["value"] == 76


def test_keeps_low_value_when_it_is_the_best(fake):
    """只有四星 42 时也要选 42，不能因为「太低」就当没有"""
    env = fake(screens=[[_card("五星太鼓", 42)]])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["value"] == 42


# ------------------------------------------------------------ 单趟扫描


def test_all_tiers_scanned_in_one_pass(fake):
    """四档必须吃同一趟滚动：滚过的屏数应等于列表长度，而不是四倍"""
    env = fake(screens=[
        [_card("六星太鼓", 67), _card("六星斗鱼", 118)],
        [_card("六星太鼓", 59), _card("六星斗鱼", 151)],
    ])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert env.screens_visited == [1], "只有一屏可翻，只能滚一次"
    assert len(env.clicked) == 4, "四张卡各点一次，不多不少"


def test_each_card_clicked_once(fake):
    """同一行不能被重复点开（四档模板共用一帧，不能重复处理同一行）"""
    env = fake(screens=[[_card("六星太鼓", 67), _card("六星斗鱼", 118)]])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert len(env.clicked) == 2
    assert len(set(env.clicked)) == 2


# ------------------------------------------- 同类型更高档已有数字就不读本档


def test_six_star_taiko_skips_five_star_taiko(fake):
    """读到六星太鼓后，五星太鼓不必再点：同类型内高星必然不更差"""
    env = fake(screens=[[_card("六星太鼓", 67), _card("五星太鼓", 59)]])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert len(env.clicked) == 1, "五星太鼓被六星太鼓压住，不该再点开"
    assert env.clicked == [(0, 0)]


def test_six_star_douyu_skips_five_star_douyu(fake):
    """斗鱼同理：六星斗鱼读到数字后，五星斗鱼不必再读"""
    env = fake(screens=[[_card("六星斗鱼", 118), _card("五星斗鱼", 151)]])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert len(env.clicked) == 1, "五星斗鱼被六星斗鱼压住"
    assert env.clicked == [(0, 0)]


def test_lower_tier_still_read_when_higher_tier_absent(fake):
    """没有六星时，五星照常要读——压制的前提是「更高档已经读到数字」"""
    env = fake(screens=[[_card("五星太鼓", 59)]])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert len(env.clicked) == 1
    assert found["name"] == "五星太鼓"
    assert found["value"] == 59


def test_taiko_does_not_suppress_douyu(fake):
    """跨类型不压制：六星太鼓有数字，不代表六星斗鱼不用读"""
    env = fake(screens=[[_card("六星太鼓", 67), _card("六星斗鱼", 118)]])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert len(env.clicked) == 2, "太鼓与斗鱼互不压制"


def test_suppression_applies_on_later_screens(fake):
    """六星在后面的屏、五星在前面的屏时，读到六星后也要停下"""
    env = fake(screens=[
        [_card("五星太鼓", 59)],
        [_card("六星太鼓", 67)],
        [_card("五星太鼓", 42)],
    ])

    Task.Jiyang_scan_list(env, PRIORITY)

    # 第一屏只有五星（此时还没读到六星，必须读）→ 第二屏读到六星
    # → 第三屏的五星被压住，不该再点
    assert len(env.clicked) == 2, "读到六星后，后面的五星不再点开"


def test_six_star_equal_value_still_suppresses(fake):
    """67 对 67 这种相接情况也算压制：更高档排在前面，读不读本档结果一样"""
    env = fake(screens=[[_card("六星太鼓", 67), _card("五星太鼓", 67)]])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert len(env.clicked) == 1
    assert found["name"] == "六星太鼓", "同值时按优先级取靠前的六星"


def test_outranked_ignores_tiers_behind(fake):
    """排在后面的档位压不住前面的：优先级顺序才是裁决者"""
    # 把五星放最前，六星放最后
    custom = (
        ("五星太鼓", "./pic/guild/五星太鼓.png"),
        ("六星太鼓", "./pic/guild/六星太鼓.png"),
    )
    env = fake(screens=[[_card("五星太鼓", 59), _card("六星太鼓", 67)]])

    found = Task.Jiyang_scan_list(env, custom)

    assert found["name"] == "五星太鼓", "五星排第一就选五星，不被后面的六星压住"
    assert len(env.clicked) == 1


# ------------------------------------------- 滚动前只在必要时把鼠标归位


def test_no_list_lookup_when_card_was_clicked(fake):
    """本屏点过卡，鼠标就在列表里，不必再找一次列表位置

    点卡时 Move_to_range 已经把鼠标落在列表的某一行上，
    再匹配一次「寄养列表」纯属浪费——一屏一次，全表扫下来是可观的开销。
    """
    env = fake(screens=[[_card("六星太鼓", 67)], [_card("六星太鼓", 59)]])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert env.list_looks == 0, "点过卡就不该再找列表位置"
    assert env.dead_scrolls == 0, "鼠标本来就在列表上，不该有空滚"


def test_list_lookup_when_nothing_clicked(fake):
    """整屏一张卡都没点，鼠标位置不可信，必须先把鼠标放回列表

    这是真机上暴露过的 bug：只有「找到卡」时才 Move_to_range，
    某屏一张卡都没匹配上时鼠标还停在页签上，滚轮滚不动列表，
    两帧相同就被误判成「列表到头」，扫描提前结束。
    """
    env = fake(screens=[
        [],
        [_card("六星太鼓", 67)],
    ])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert env.list_looks >= 1, "没点过卡时必须找一次列表位置"
    assert env.dead_scrolls == 0, "归位之后滚轮必须真的作用到列表"
    assert env.screens_visited == [1], "空白屏也必须能滚下去"


def test_list_lookup_when_all_rows_skipped(fake):
    """本屏的行全被压住没点，同样要归位鼠标

    「有行但没点」与「没有行」在鼠标位置上是一回事：
    上一屏点完卡之后鼠标停在那一行，这一屏的卡可能已经滚出视窗。
    """
    env = fake(screens=[
        [_card("六星太鼓", 67)],
        [_card("五星太鼓", 59)],        # 被六星太鼓压住，不会点
        [_card("六星太鼓", 76)],
    ])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert env.list_looks >= 1, "整屏都没点卡，要归位鼠标"
    assert env.dead_scrolls == 0


def test_scroll_actually_moves_when_no_card_on_screen(fake):
    """整屏一张卡都匹配不上时，仍要真的滚动，不能原地打转"""
    env = fake(screens=[
        [],
        [_card("六星太鼓", 67)],
    ])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert env.screens_visited == [1], "空白屏也必须能滚下去"


# ------------------------------------------------------------ 封顶早停


def test_cap_skips_rest_of_that_tier(fake):
    """读到本类型封顶（太鼓 76）后，本档剩余行不再点"""
    env = fake(screens=[[_card("六星太鼓", 76), _card("六星太鼓", 59)]])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert len(env.clicked) == 1, "封顶后不应再点同一档的其他行"


def test_cap_does_not_stop_other_tiers(fake):
    """太鼓封顶不能影响斗鱼的扫描：勾玉与体力不互比"""
    env = fake(screens=[[_card("六星太鼓", 76), _card("六星斗鱼", 118)]])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert len(env.clicked) == 2, "斗鱼那一行仍要点开"


def test_cap_differs_per_card_type(fake):
    """斗鱼封顶是 151，读到 118 不能提前停"""
    env = fake(screens=[[_card("六星斗鱼", 118), _card("六星斗鱼", 134)]])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["value"] == 134, "118 没到斗鱼封顶，必须继续扫"


def test_cap_table_matches_known_yields():
    """封顶值必须与收益表一致，否则早停会漏掉更好的卡"""
    assert Lib.JIEJIE_YIELD_CAP["太鼓"] == 76
    assert Lib.JIEJIE_YIELD_CAP["斗鱼"] == 151


def test_card_type_extracted_from_priority_name():
    """封顶表按类型索引，而档位名带星级，必须先取出类型"""
    assert Lib.jiejie_card_type("六星太鼓") == "太鼓"
    assert Lib.jiejie_card_type("五星太鼓") == "太鼓"
    assert Lib.jiejie_card_type("六星斗鱼") == "斗鱼"
    assert Lib.jiejie_card_type("五星斗鱼") == "斗鱼"
    assert Lib.jiejie_card_type("未知档位") == ""


# ------------------------------------------------------- 档间按优先级


def test_returns_first_tier_with_result(fake):
    """六星太鼓有货就选它，哪怕六星斗鱼数值更大（勾玉与体力不互比）"""
    env = fake(screens=[[_card("六星太鼓", 67), _card("六星斗鱼", 151)]])

    selected = Task.Jiyang_scan_list(env, PRIORITY)

    assert selected["name"] == "六星太鼓"
    assert selected["value"] == 67, "优先级在前者胜出，不比数字大小"


def test_skips_empty_tiers(fake):
    """前面档位没货时往后找，取第一个有货的档位"""
    env = fake(screens=[[_card("五星太鼓", 59), _card("五星斗鱼", 151)]])

    selected = Task.Jiyang_scan_list(env, PRIORITY)

    assert selected["name"] == "五星太鼓"
    assert selected["value"] == 59


def test_returns_none_when_all_empty(fake):
    """四档全空返回 None，调用方据此返回 0"""
    env = fake(screens=[[]])

    assert Task.Jiyang_scan_list(env, PRIORITY) is None


# ------------------------------------------------------- 读不出时的兜底


def test_falls_back_to_first_hit_when_all_unreadable(fake):
    """全部读不出时不能当作「本档没有卡」，要回退成第一个命中"""
    env = fake(screens=[[_card("六星太鼓", None), _card("六星太鼓", None)]])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found is not None, "读不出不等于没有卡"
    assert found["value"] is None
    assert found["name"] == "六星太鼓"


def test_skips_unreadable_but_keeps_readable(fake):
    """部分读不出时，读得出的那个照常参与比较"""
    env = fake(screens=[[_card("六星太鼓", None), _card("六星太鼓", 59)]])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["value"] == 59


def test_fallback_tier_still_selectable(fake):
    """兜底结果也算「有货」，否则全读不出时会误返回 0"""
    env = fake(screens=[[_card("六星太鼓", None)]])

    selected = Task.Jiyang_scan_list(env, PRIORITY)

    assert selected is not None
    assert selected["name"] == "六星太鼓"


# ---------------------------------------------------- 到底只能由空白格判定


def test_stops_when_blank_slot_found(fake):
    """到底的唯一判据是空白格模板命中，命中即停"""
    env = fake(screens=[
        [_card("六星太鼓", 59)],
        [_card("六星太鼓", 67)],
    ], ended=[False, True])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["value"] == 67, "最后一屏的卡也要参与比较"
    assert env.screens_visited == [1], "命中空白格后不再往下滚"


def test_does_not_stop_on_unchanged_screen(fake):
    """画面不再变化**不能**当成到底：那是「滚不动」的间接现象，不是语义

    这里让滚动完全无效（屏幕数固定为 1），但空白格永不命中——
    扫描必须一直跑到轮次上限，而不是提前 break 成「列表到头」。
    """
    env = fake(screens=[[_card("六星太鼓", 59)]], ended=[False])
    env.scroll = lambda Hwnd, length: None      # 滚轮彻底失效

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found is not None and found["value"] == 59


# ------------------------------------------------------------ 日志可读性


def test_logs_current_best_of_same_type(fake, capsys):
    """每读一个数字都要报「目前最高」，且只跟同类型比

    勾玉与体力单位不同，混在一起报没有意义：斗鱼的 151 不该出现在
    太鼓那一行里，否则会让人以为 76 落后了。
    """
    env = fake(screens=[
        [_card("六星太鼓", 67)],
        [_card("六星太鼓", 59)],
        [_card("六星斗鱼", 118)],
    ])

    Task.Jiyang_scan_list(env, PRIORITY)
    out = capsys.readouterr().out

    assert "六星太鼓 收益 59 目前最高67" in out, "后读到的低收益要报出同类型最高"
    assert "六星斗鱼 收益 118 目前最高118" in out, "斗鱼自成一体，不拿太鼓的 67 来比"


def test_logs_selected_card_after_reaching_end(fake, capsys):
    """扫到列表末尾后要紧接着报出最终选中了哪张、收益多少"""
    env = fake(screens=[[_card("六星太鼓", 67), _card("六星斗鱼", 151)]])

    Task.Jiyang_scan_list(env, PRIORITY)
    out = capsys.readouterr().out

    assert "扫完 当前选中 六星太鼓 收益 67" in out, "跨类型不互比，取优先级靠前的太鼓"


def test_logs_selected_card_when_value_unreadable(fake, capsys):
    """兜底选中时也要报，且要说清收益读不出，不能显示 None"""
    env = fake(screens=[[_card("六星太鼓", None)]])

    Task.Jiyang_scan_list(env, PRIORITY)
    out = capsys.readouterr().out

    assert "扫完 当前选中 六星太鼓 收益读不出" in out


# ------------------------------------------------------------ 回滚复核


def test_goto_accepts_matching_value(fake):
    """回滚后读到同样的数字，就算复核通过"""
    env = fake(screens=[[_card("六星太鼓", 67)]])
    target = {"name": "六星太鼓", "value": 67, "scrolls": 0, "back": 0,
              "row": [[0, 0], [100, 30]], "pic": "./pic/guild/六星太鼓.png"}

    assert Task.Jiyang_goto(env, target) is True


def test_goto_rejects_changed_value(fake):
    """回滚后数字变了（列表被改动）就必须返回 False，交给调用方重扫"""
    env = fake(screens=[[_card("六星太鼓", 59)]])
    target = {"name": "六星太鼓", "value": 67, "scrolls": 0, "back": 0,
              "row": [[0, 0], [100, 30]], "pic": "./pic/guild/六星太鼓.png"}

    assert Task.Jiyang_goto(env, target) is False


def test_goto_accepts_fallback_target_with_unknown_value(fake):
    """兜底目标的数字本来就是 None，只要点中就算通过"""
    env = fake(screens=[[_card("六星太鼓", 42)]])
    target = {"name": "六星太鼓", "value": None, "scrolls": 0, "back": 0,
              "row": [[0, 0], [100, 30]], "pic": "./pic/guild/六星太鼓.png"}

    assert Task.Jiyang_goto(env, target) is True


def test_goto_no_scroll_when_target_on_current_screen(fake):
    """目标就在当前屏时不需要滚动"""
    env = fake(screens=[[_card("六星太鼓", 59)], [_card("六星太鼓", 67)]])
    env.screen_index = 1        # 扫完停在最后一屏，目标也在这屏
    target = {"name": "六星太鼓", "value": 67, "scrolls": 1, "back": 0,
              "row": [[0, 0], [100, 30]], "pic": "./pic/guild/六星太鼓.png"}

    assert Task.Jiyang_goto(env, target) is True
    assert env.screen_index == 1, "目标就在当前屏，不需要滚动"


def test_goto_rolls_back_from_bottom(fake):
    """目标在第一屏、扫完停在第三屏时，要向上滚两屏才回到目标"""
    env = fake(screens=[
        [_card("六星太鼓", 67)],
        [_card("六星太鼓", 59)],
        [_card("六星太鼓", 42)],
    ])
    env.screen_index = 2        # 扫完停在最后一屏
    target = {"name": "六星太鼓", "value": 67, "scrolls": 0, "back": 2,
              "row": [[0, 0], [100, 30]], "pic": "./pic/guild/六星太鼓.png"}

    assert Task.Jiyang_goto(env, target) is True
    assert env.screen_index == 0, "向上滚两次应该回到第一屏"


def test_scan_list_computes_back_steps(fake):
    """回滚次数 = 扫描总次数 - 目标那一屏的次数，由扫描自己算好"""
    env = fake(screens=[
        [_card("六星太鼓", 67)],
        [_card("六星太鼓", 59)],
        [_card("六星太鼓", 42)],
    ])

    selected = Task.Jiyang_scan_list(env, PRIORITY)

    assert selected["value"] == 67
    assert selected["scrolls"] == 0
    assert selected["back"] == 2, "扫完停在底部，回第一屏要向上滚两次"


# ------------------------------------------------------ 首选档位封顶即收工


def test_stops_when_first_priority_hits_cap(fake):
    """首选是六星太鼓，读到 76 就直接收工，不再往下翻"""
    env = fake(screens=[
        [_card("六星太鼓", 76)],
        [_card("六星太鼓", 59)],
        [_card("六星太鼓", 42)],
    ])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["value"] == 76
    assert env.screens_visited == [], "第一屏就拿到封顶，一次都不该滚"


def test_stops_when_first_priority_douyu_hits_cap(fake):
    """首选换成六星斗鱼时，读到 151 收工"""
    priority = (
        ("六星斗鱼", "./pic/guild/六星斗鱼.png"),
        ("六星太鼓", "./pic/guild/六星太鼓.png"),
        ("五星斗鱼", "./pic/guild/五星斗鱼.png"),
        ("五星太鼓", "./pic/guild/五星太鼓.png"),
    )
    env = fake(screens=[
        [_card("六星斗鱼", 151)],
        [_card("六星斗鱼", 118)],
    ])

    found = Task.Jiyang_scan_list(env, priority)

    assert found["name"] == "六星斗鱼"
    assert found["value"] == 151
    assert env.screens_visited == []


def test_does_not_stop_when_lower_tier_hits_cap(fake):
    """封顶的是第二优先级，不能收工：首选档位可能还在后面没出现"""
    env = fake(screens=[
        [_card("六星斗鱼", 151)],
        [_card("六星太鼓", 76)],
    ])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["name"] == "六星太鼓", "首选档位排在前面，压过六星斗鱼"
    assert found["value"] == 76
    assert env.screens_visited == [1], "第二档封顶不能让整表收工"


def test_stops_after_scanning_whole_screen(fake):
    """同一屏里封顶行后面的行仍要处理完，再收工"""
    env = fake(screens=[
        [_card("六星太鼓", 76), _card("六星斗鱼", 118)],
        [_card("六星斗鱼", 151)],
    ])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert len(env.clicked) == 2, "本屏两行都要点，收工发生在处理完本屏之后"
    assert env.screens_visited == []


# --------------------------------------------------- 同收益记住后发现的


def test_equal_value_prefers_later_one(fake):
    """两个 67 时记住后发现的：它离底部更近，回滚步数更少"""
    env = fake(screens=[
        [_card("六星太鼓", 67)],
        [_card("六星太鼓", 67)],
        [],
    ])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["value"] == 67
    assert found["scrolls"] == 1, "应该记住第二屏那张，而不是第一屏那张"
    assert found["back"] == 1, "回滚两步变一步"


def test_higher_value_still_wins_over_later_one(fake):
    """后来的数字更小，仍然保留前面那个大的"""
    env = fake(screens=[
        [_card("六星太鼓", 76)],
        [_card("六星太鼓", 67)],
    ])

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["value"] == 76
    assert found["scrolls"] == 0


# ------------------------------------------------- 滚动后只等滚轮生效


def test_waits_for_scroll_after_scrolling(fake):
    """滚完只等一下滚轮生效，不再硬等重绘：重绘慢时干等太拖时间"""
    env = fake(screens=[[_card("六星太鼓", 67)], [_card("六星太鼓", 59)]])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert env.trace[0] == ("shot", 0)
    for i, event in enumerate(env.trace):
        if event[0] != "scroll":
            continue
        nxt = env.trace[i + 1:i + 3]
        assert ("sleep", Task.JIEJIE_SCROLL_WAIT) in nxt, \
            "滚动之后必须先等一下滚轮生效，不能立刻截图"


def test_scroll_wait_is_short():
    """只等滚轮生效，不等重绘：0.5 秒硬等实测太慢，改回 0.2 秒"""
    assert Task.JIEJIE_SCROLL_WAIT == 0.2


def test_after_scroll_waits_once_then_shoots(fake):
    """滚完的做法是「等一次、截一张」，不连拍比对指纹"""
    env = fake(screens=[[_card("六星太鼓", 67)]])
    before = len(env.trace)

    Task.Jiyang_after_scroll(env)

    after = env.trace[before:]
    assert after == [("sleep", Task.JIEJIE_SCROLL_WAIT), ("shot", 0)], \
        "只该等一次再截一张，不该反复探测"


def test_after_scroll_frame_reused_by_next_screen(fake):
    """滚完那一帧直接给下一屏用，不要再多截一次"""
    env = fake(screens=[[], []])

    Task.Jiyang_scan_list(env, PRIORITY)

    shots = [e for e in env.trace if e[0] == "shot"]
    assert len(shots) == 2, "首屏 1 张 + 滚动后 1 张，第二屏不再单独截图"


# ------------------------------------------------ 点开后原地复核类型


def test_recheck_mismatch_redoes_screen(fake):
    """点开后类型变了：这一屏重新识别，最后按复核到的类型记账

    滚轮翻页会让游戏重绘整列列表，扫描用的那一帧若是重绘中间态，
    类型就会记错。复核到不一致时必须把这一屏重来，而不是照着错的记。
    """
    env = fake(
        screens=[[_card("六星太鼓", 67)]],
        flip={(0, 0): ["六星斗鱼"]},      # 一直变不回来
    )

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["name"] == "六星斗鱼", "复核一直说是斗鱼，就按斗鱼记"
    assert found["value"] == 67
    assert len(env.clicked) == 3, "两次重识别 + 第三次按复核结果记账"


def test_recheck_settles_then_records_original(fake):
    """重识别之后卡面恢复原样，就照原类型正常记账"""
    env = fake(
        screens=[[_card("六星太鼓", 67)]],
        flip={(0, 0): ["六星斗鱼", "六星太鼓"]},   # 第一次复核是中间态，之后稳定
    )

    found = Task.Jiyang_scan_list(env, PRIORITY)

    assert found["name"] == "六星太鼓"
    assert found["value"] == 67
    assert len(env.clicked) == 2, "重识别一次就够了"


def test_recheck_consistent_clicks_once(fake):
    """复核一致时不能白重来：每张卡只点一次"""
    env = fake(screens=[[_card("六星太鼓", 67), _card("六星斗鱼", 151)]])

    Task.Jiyang_scan_list(env, PRIORITY)

    assert len(env.clicked) == 2, "两张卡各点一次，复核没发现异常就不重来"


def test_recheck_logs_redo(fake, capsys):
    """重识别要在日志里留一行，方便对不上时回看"""
    env = fake(
        screens=[[_card("六星太鼓", 67)]],
        flip={(0, 0): ["六星斗鱼", "六星太鼓"]},
    )

    Task.Jiyang_scan_list(env, PRIORITY)
    out = capsys.readouterr().out

    assert "六星太鼓 复核成 六星斗鱼，这一屏重新识别" in out


def test_recheck_gives_up_after_limit(fake, capsys):
    """复核次数用完后不能再无限重来，要按复核结果往下走"""
    env = fake(
        screens=[[_card("六星太鼓", 67)]],
        flip={(0, 0): ["六星斗鱼"]},
    )

    Task.Jiyang_scan_list(env, PRIORITY)
    out = capsys.readouterr().out

    assert "按复核结果记" in out
    assert len(env.clicked) == Task.JIEJIE_RECHECK_TRIES + 1, \
        "重识别次数 + 最后按复核结果记的那一次"


def test_row_type_crops_around_row(monkeypatch):
    """复核只裁这一行附近，并且把裁切偏移加回去再比纵向中心"""
    seen = {}

    def fake_rows(Img, Models, Threshold, max_matches=8):
        seen["shape"] = Img.shape
        # 裁切块里的坐标是相对的：这一行在裁切块里 y 约 12（原图 40，裁切从 28 开始）
        return [("六星太鼓", [[0, 12], [100, 42]], "0.010")]

    monkeypatch.setattr(Task, "Match_models_rows", fake_rows)
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    row = [[10, 40], [110, 70]]

    got = Task.Jiyang_row_type(img, row, PRIORITY)

    assert got == "六星太鼓"
    assert seen["shape"][0] == (70 - 40) + 2 * Task.JIEJIE_RECHECK_MARGIN, "纵向按外扩裁切"


def test_row_type_returns_none_when_no_match(monkeypatch):
    """那一带已经认不出卡时返回 None，调用方据此跳过这一行"""
    monkeypatch.setattr(Task, "Match_models_rows", lambda *a, **k: [])
    img = np.zeros((300, 400, 3), dtype=np.uint8)

    assert Task.Jiyang_row_type(img, [[10, 40], [110, 70]], PRIORITY) is None


def test_row_type_rejects_far_row(monkeypatch):
    """裁切块边缘带进来的邻行不能冒充原行：偏离超过一行高就当认不出"""
    monkeypatch.setattr(Task, "Match_models_rows",
                        lambda *a, **k: [("六星太鼓", [[0, 60], [100, 90]], "0.010")])
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    row = [[10, 40], [110, 70]]      # 原行中心 y=55，裁切后邻行中心 28+75=103

    assert Task.Jiyang_row_type(img, row, PRIORITY) is None


# ------------------------------------------------ 复核失败时刷新列表


def _stub_find_click(monkeypatch, found):
    """替掉 Find_Click_windows，记录点了哪些模板"""
    calls = []

    def fake_click(Hwnd, Model_path, Threshold, message_F, message_C):
        calls.append(Model_path)
        return found.get(Model_path, False)

    monkeypatch.setattr(Task, "Find_Click_windows", fake_click)
    return calls


def test_refresh_clicks_cross_area_then_friend(monkeypatch):
    """刷新 = 先点跨区再点好友，两步都点到了才算成功"""
    calls = _stub_find_click(monkeypatch, {
        "./pic/guild/跨区.png": True,
        "./pic/guild/好友.png": True,
    })

    assert Task.Jiyang_refresh("Hwnd") is True
    assert calls == ["./pic/guild/跨区.png", "./pic/guild/好友.png"]


def test_refresh_stops_when_cross_area_missing(monkeypatch):
    """跨区都点不到就不要去点好友了"""
    calls = _stub_find_click(monkeypatch, {"./pic/guild/跨区.png": False})

    assert Task.Jiyang_refresh("Hwnd") is False
    assert calls == ["./pic/guild/跨区.png"]


def test_refresh_stops_when_friend_missing(monkeypatch):
    """跨区点到了但好友点不到，同样算刷新失败"""
    calls = _stub_find_click(monkeypatch, {
        "./pic/guild/跨区.png": True,
        "./pic/guild/好友.png": False,
    })

    assert Task.Jiyang_refresh("Hwnd") is False
    assert calls == ["./pic/guild/跨区.png", "./pic/guild/好友.png"]
