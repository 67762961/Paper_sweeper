# -*- coding: utf-8 -*-
"""寄养列表扫描与择优：一趟扫完、档内取最大、档间按优先级、封顶早停、读不出回退。

这些逻辑全都在 Task_Jiejieyangcheng 里，但它只依赖几个可替换的原语
（截图、模板匹配、读数、滚动、点击），所以可以整段替换成假的，
在纯逻辑层面验证「选谁」这件事——真机验证留给手动单跑。

重点覆盖五条容易写错的规则：
1. 一趟扫完，四档吃同一帧截图（不是四趟）；
2. 档内比数字取最大（59 输给 67）；
3. 档间按优先级取第一个有货的，**不比数字大小**（六星太鼓 67 胜过六星斗鱼 151）；
4. 本类型封顶后，本档剩余行不再点，但**其他档照常扫**；
5. 全部读不出时回退成第一个命中，而不是当作「本档没有卡」。
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
    """

    def __init__(self, screens, ended=None):
        self.screens = screens
        self.ended = ended or [False] * (len(screens) - 1) + [True]
        self.screen_index = 0
        self.clicked = []           # [(屏号, 行号)]
        self.screens_visited = []

    # ---- 截图与匹配 ----
    def screenshot(self, Hwnd):
        """按屏号给出不同画面，让指纹能分辨出真的滚动了"""
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[:, :, 0] = (self.screen_index * 23 + 5) % 255
        img[:, :, 1] = (self.screen_index * 41 + 9) % 255
        return img

    def match_one(self, Img, models, Threshold):
        """寄养列表末尾的匹配：按当前屏决定是否到底"""
        if models[0][0] != "末尾":
            return []
        return [("末尾", [[0, 0], [1, 1]], "0.000")] if self.ended[self.screen_index] else []

    def match_all(self, Img, Model_path, Threshold, max_matches=10):
        """只返回属于 Model_path 对应档位的行"""
        card_name = Model_path.rsplit("/", 1)[-1].replace(".png", "")
        rows = []
        for i, (name, _value) in enumerate(self.screens[self.screen_index]):
            if name == card_name:
                rows.append([[0, 40 * i], [100, 40 * i + 30]])
        return rows

    # ---- 交互 ----
    def scroll(self, Hwnd, length):
        if length < 0:
            self.screen_index = min(self.screen_index + 1, len(self.screens) - 1)
            self.screens_visited.append(self.screen_index)
        elif length > 0:
            self.screen_index = max(self.screen_index - 1, 0)

    def move(self, Hwnd, Loc):
        return 0

    def click(self, Hwnd, Loc, Wait):
        self.clicked.append((self.screen_index, Loc[0][1] // 40))
        return 1

    def sleep(self, seconds):
        pass

    # ---- 读数 ----
    def read_yield(self, Img):
        screen, row = self.clicked[-1]
        return self.screens[screen][row][1]


@pytest.fixture()
def fake(monkeypatch):
    """返回一个工厂：传入屏数据，得到装好假原语的环境"""

    def build(screens, ended=None):
        env = FakeList(screens, ended)
        monkeypatch.setattr(Task, "Screenshot_window", env.screenshot)
        monkeypatch.setattr(Task, "Match_models_in_image", env.match_one)
        monkeypatch.setattr(Task, "Match_models_in_image_all", env.match_all)
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
        [_card("五星太鼓", 59), _card("五星斗鱼", 151)],
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
    """全部读不出时不能当作「本档没有卡」，要回退成第一个命中（R9）"""
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
