# -*- coding: utf-8 -*-
"""结界养成配置：枚举、归一化与按账号读取（纯逻辑，不依赖 Qt）。

守住的都是「写错了会静默跑错顺序」的地方：

1. 老配置没有「结界养成」段时，行为与改动前**完全一致**（默认优先太鼓、
   寄养按 六星太鼓 → 六星斗鱼 → 五星太鼓 → 五星斗鱼）；
2. 「优先结界卡」只有太鼓 / 斗鱼两项，没有「不放置」这个第三态；
3. 寄养优先级永远是那 4 个卡名的排列——重复项换成未占用的值，
   非法值按池序补，绝不出现两项相同或长度不是 4；
4. 两个账号互不影响，账号不存在时回落默认值而不是抛异常。
"""

import os

import pytest

import Lib
import paths

SAMPLE = """启动项:
  "master":
    启动命令: "a.exe -v 0"
  "slaves":
    启动命令: "a.exe -v 1"

结界养成:
  "master":
    优先结界卡: "斗鱼"
    寄养优先级: [六星斗鱼, 六星太鼓, 五星斗鱼, 五星太鼓]
  "slaves":
    优先结界卡: "太鼓"
    寄养优先级: [五星太鼓, 五星斗鱼, 六星太鼓, 六星斗鱼]
"""


def _write_setting(text=SAMPLE):
    """把配置写到当前工作目录的 config/Setting.yml（用例已 chdir 到临时目录）"""
    os.makedirs(paths.CONFIG_DIR, exist_ok=True)
    with open(paths.SETTING, "w", encoding="utf-8") as handle:
        handle.write(text)
    return paths.SETTING


# ------------------------------------------------------------ 常量


def test_枚举与模板图一一对应():
    """配置值就是 pic/guild/ 下的模板文件名，映射表不能有缺项"""
    assert Lib.JIEJIE_CARD_OPTIONS == ("太鼓", "斗鱼")
    assert Lib.JIEJIE_PRIORITY_OPTIONS == ("六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼")
    assert Lib.JIEJIE_PRIORITY_COUNT == 4
    assert set(Lib.JIEJIE_PRIORITY_PICS) == set(Lib.JIEJIE_PRIORITY_OPTIONS)
    for name, pic in Lib.JIEJIE_PRIORITY_PICS.items():
        assert pic == f"./pic/guild/{name}.png"


def test_默认值等于改动前的写死行为():
    """默认值必须是「优先太鼓 + 原寄养顺序」，否则老配置会悄悄改变行为"""
    assert Lib.JIEJIE_DEFAULT_CARD == "太鼓"
    assert tuple(Lib.JIEJIE_DEFAULT_PRIORITY) == (
        "六星太鼓",
        "六星斗鱼",
        "五星太鼓",
        "五星斗鱼",
    )


# ------------------------------------------------------------ 优先结界卡


def test_优先结界卡只认太鼓和斗鱼():
    assert Lib.normalize_jiejie_card("太鼓") == "太鼓"
    assert Lib.normalize_jiejie_card("斗鱼") == "斗鱼"


@pytest.mark.parametrize("value", ["不放置", "六星太鼓", "", None, 3, ["太鼓"]])
def test_优先结界卡非法值回落太鼓并给提示(value):
    warnings = []
    assert Lib.normalize_jiejie_card(value, warnings) == "太鼓"
    if value is not None:
        assert warnings, "非法取值必须留下回落原因，不能静默改配置"


def test_优先结界卡为None时不产生噪音提示():
    """缺键是最常见的情况，不该在弹窗里刷一条「取值 None 不受支持」"""
    warnings = []
    assert Lib.normalize_jiejie_card(None, warnings) == "太鼓"
    assert warnings == []


# ------------------------------------------------------------ 卡序


def test_卡序按优先级调换():
    assert Lib.jiejie_card_order("太鼓") == ("太鼓", "斗鱼")
    assert Lib.jiejie_card_order("斗鱼") == ("斗鱼", "太鼓")


def test_卡序遇到非法值按太鼓优先():
    assert Lib.jiejie_card_order("六星太鼓") == ("太鼓", "斗鱼")


# ------------------------------------------------------------ 寄养优先级归一化


def test_合法排列原样保留():
    values = ["六星斗鱼", "六星太鼓", "五星斗鱼", "五星太鼓"]
    assert Lib.normalize_jiejie_priority(values) == values


def test_缺省时用默认排列():
    assert Lib.normalize_jiejie_priority(None) == list(Lib.JIEJIE_DEFAULT_PRIORITY)


def test_长度不足按池序补齐():
    """只给了 2 项：前两项保留，后两项按枚举顺序补未占用的"""
    result = Lib.normalize_jiejie_priority(["六星斗鱼", "六星太鼓"])
    assert result == ["六星斗鱼", "六星太鼓", "五星太鼓", "五星斗鱼"]


def test_长度超出截断为四项():
    result = Lib.normalize_jiejie_priority(
        ["六星斗鱼", "六星太鼓", "五星斗鱼", "五星太鼓", "六星太鼓"]
    )
    assert result == ["六星斗鱼", "六星太鼓", "五星斗鱼", "五星太鼓"]


def test_重复项换成未被占用的值():
    """需求里的「后面的让位」：先出现者保留，后者换成池中第一个空闲值"""
    result = Lib.normalize_jiejie_priority(
        ["六星太鼓", "六星太鼓", "五星太鼓", "五星斗鱼"]
    )
    assert result == ["六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼"]


def test_首尾重复时后者让位():
    result = Lib.normalize_jiejie_priority(
        ["五星斗鱼", "六星太鼓", "六星斗鱼", "五星斗鱼"]
    )
    assert result == ["五星斗鱼", "六星太鼓", "六星斗鱼", "五星太鼓"]


def test_非法值按池序补位():
    warnings = []
    result = Lib.normalize_jiejie_priority(
        ["六星白达摩", "六星斗鱼", "五星太鼓", "五星斗鱼"], warnings
    )
    assert result == ["六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼"]
    assert any("不受支持" in item for item in warnings)


def test_非列表按默认值处理并提示():
    warnings = []
    result = Lib.normalize_jiejie_priority("六星太鼓", warnings)
    assert result == list(Lib.JIEJIE_DEFAULT_PRIORITY)
    assert warnings


def test_归一化输出永远是四个互不相同的合法值():
    """穷举一批脏输入，输出必须始终是那 4 个卡名的排列"""
    pool = set(Lib.JIEJIE_PRIORITY_OPTIONS)
    cases = [
        [],
        [None] * 4,
        ["六星太鼓"] * 4,
        ["六星太鼓", "六星斗鱼", "六星太鼓", "六星斗鱼"],
        ["x", "y", "z", "w"],
        [1, 2, 3, 4],
        ["五星斗鱼", "五星斗鱼", "五星斗鱼", "五星斗鱼"],
    ]
    for case in cases:
        result = Lib.normalize_jiejie_priority(case)
        assert len(result) == 4, case
        assert len(set(result)) == 4, case
        assert set(result) == pool, case


# ------------------------------------------------------------ 卡名 → 模板路径


def test_寄养卡片按优先级给出模板路径():
    cards = Lib.jiejie_priority_cards(["五星斗鱼", "六星太鼓", "六星斗鱼", "五星太鼓"])
    assert [name for name, _ in cards] == ["五星斗鱼", "六星太鼓", "六星斗鱼", "五星太鼓"]
    assert cards[0][1] == "./pic/guild/五星斗鱼.png"
    assert cards[3][1] == "./pic/guild/五星太鼓.png"


def test_寄养卡片遇到脏配置也能给出四条路径():
    cards = Lib.jiejie_priority_cards(["六星太鼓", "六星太鼓", "六星太鼓", "六星太鼓"])
    assert len(cards) == 4
    assert len({name for name, _ in cards}) == 4


# ------------------------------------------------------------ 按账号读取


def test_配置缺失时返回默认值(tmp_config_dir):
    settings = Lib.load_jiejie_settings("master")

    assert settings["card"] == Lib.JIEJIE_DEFAULT_CARD
    assert settings["priority"] == list(Lib.JIEJIE_DEFAULT_PRIORITY)
    assert settings["warnings"] == []


def test_能按账号读回各自的配置(tmp_config_dir):
    _write_setting()

    master = Lib.load_jiejie_settings("master")
    slaves = Lib.load_jiejie_settings("slaves")

    assert master["card"] == "斗鱼"
    assert master["priority"] == ["六星斗鱼", "六星太鼓", "五星斗鱼", "五星太鼓"]
    assert slaves["card"] == "太鼓"
    assert slaves["priority"] == ["五星太鼓", "五星斗鱼", "六星太鼓", "六星斗鱼"]


def test_账号不在配置里时回落默认值(tmp_config_dir):
    _write_setting()

    settings = Lib.load_jiejie_settings("第三账号")

    assert settings["card"] == Lib.JIEJIE_DEFAULT_CARD
    assert settings["priority"] == list(Lib.JIEJIE_DEFAULT_PRIORITY)


def test_账号为None时不取子键直接给默认值(tmp_config_dir):
    _write_setting()

    settings = Lib.load_jiejie_settings(None)

    assert settings["card"] == Lib.JIEJIE_DEFAULT_CARD


def test_配置损坏时不抛异常(tmp_config_dir):
    _write_setting("结界养成: [这不是: 合法\n  - yaml")

    settings = Lib.load_jiejie_settings("master")

    assert settings["card"] == Lib.JIEJIE_DEFAULT_CARD
    assert settings["priority"] == list(Lib.JIEJIE_DEFAULT_PRIORITY)


def test_段存在但不是映射时回落默认值(tmp_config_dir):
    _write_setting("结界养成: 太鼓\n")

    settings = Lib.load_jiejie_settings("master")

    assert settings["card"] == Lib.JIEJIE_DEFAULT_CARD


def test_脏配置能读出四条可用路径(tmp_config_dir):
    """真实运行时的兜底：不管配置多脏，都要能给出 4 条模板路径去扫"""
    _write_setting(
        "结界养成:\n"
        '  "master":\n'
        "    优先结界卡: 不放置\n"
        "    寄养优先级: [六星太鼓, 六星太鼓, 六星白达摩]\n"
    )

    settings = Lib.load_jiejie_settings("master")
    cards = Lib.jiejie_priority_cards(settings["priority"])

    assert settings["card"] == Lib.JIEJIE_DEFAULT_CARD
    assert len(cards) == 4
    assert all(os.path.basename(pic) for _, pic in cards)
    assert settings["warnings"], "回落必须留下提示，便于用户发现配置写错了"
