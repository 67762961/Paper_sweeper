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
import ruamel.yaml

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


def test_结界卡池页签覆盖全部放置选项():
    """放置结界卡时要按顺序点开对应页签，漏一项就会 IndexError / KeyError"""
    assert set(Lib.JIEJIE_CARD_LIST_PICS) == set(Lib.JIEJIE_CARD_OPTIONS)
    for card, pic in Lib.JIEJIE_CARD_LIST_PICS.items():
        assert pic == f"./pic/guild/{card}列表.png"


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


# ------------------------------------------------------------ 界面读写层（ui/jiejie_settings.py）
# 与 Lib 层分开断言：Lib 保证「任务层拿到的东西是对的」，这里保证
# 「弹窗读到的与任务层一致」且「写回不伤及配置里的其它段」。

from ui import jiejie_settings as js  # noqa: E402  （放这里是为了让上面 Lib 部分先跑）

UI_SAMPLE = """# 用户手写的说明，不能被抹掉
启动项:
  "master":            # 主账号
    启动命令: "a.exe -v 0"
  "slaves":
    启动命令: "a.exe -v 1"

结界突破:
  "master":
    退出次数: 3
    开打勋章: 15

寮三十:
  主账号: "master"
  副账号: "slaves"
  副本: ["魂虚", "魂虚", "魂虚", "魂虚", "魂虚", "魂海", "日蚀"]
  次数: [30, 30, 30, 30, 30, 30, 30]

结界养成:
  "master":
    优先结界卡: "斗鱼"
    寄养优先级: [六星斗鱼, 六星太鼓, 五星斗鱼, 五星太鼓]
  "slaves":
    优先结界卡: "太鼓"
    寄养优先级: [五星太鼓, 五星斗鱼, 六星太鼓, 六星斗鱼]
"""


def _read_raw_yaml(path=None):
    """用与实现相同的 YAML 设置读回，便于断言引号等格式信息"""
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    with open(path or paths.SETTING, "r", encoding="utf-8") as handle:
        return yaml.load(handle)


def _read_text(path=None):
    with open(path or paths.SETTING, "r", encoding="utf-8") as handle:
        return handle.read()


def test_界面层枚举与Lib一致():
    """弹窗能选出来的必须正好是任务层能接受的，不能各写一份"""
    assert js.CARD_OPTIONS == Lib.JIEJIE_CARD_OPTIONS
    assert js.PRIORITY_OPTIONS == Lib.JIEJIE_PRIORITY_OPTIONS
    assert js.PRIORITY_COUNT == Lib.JIEJIE_PRIORITY_COUNT
    assert js.DEFAULT_CARD == Lib.JIEJIE_DEFAULT_CARD
    assert js.DEFAULT_PRIORITY == list(Lib.JIEJIE_DEFAULT_PRIORITY)
    assert len(js.PRIORITY_LABELS) == Lib.JIEJIE_PRIORITY_COUNT


def test_界面读取与任务层读取一致(tmp_config_dir):
    _write_setting(UI_SAMPLE)

    ui_data = js.load_jiejie_settings()

    for account in ui_data["accounts"]:
        assert ui_data["settings"][account] == {
            key: value
            for key, value in Lib.load_jiejie_settings(account).items()
            if key != "warnings"
        }


def test_账号列表来自启动项且保持顺序(tmp_config_dir):
    _write_setting(UI_SAMPLE)

    data = js.load_jiejie_settings()

    assert data["accounts"] == ["master", "slaves"]
    assert set(data["settings"]) == {"master", "slaves"}


def test_主副角色只作装饰且不落盘(tmp_config_dir):
    _write_setting(UI_SAMPLE)

    data = js.load_jiejie_settings()

    assert data["roles"] == {"master": "主", "slaves": "副"}


def test_没有寮三十段时角色为空(tmp_config_dir):
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n')

    data = js.load_jiejie_settings()

    assert data["roles"] == {}


def test_配置缺失时每个账号都给默认值(tmp_config_dir):
    data = js.load_jiejie_settings()

    assert data["accounts"] == ["master", "slaves"]
    for account in data["accounts"]:
        assert data["settings"][account]["card"] == js.DEFAULT_CARD
        assert data["settings"][account]["priority"] == js.DEFAULT_PRIORITY


def test_配置损坏时不抛异常(tmp_config_dir):
    _write_setting("结界养成: [这不是: 合法\n  - yaml")

    data = js.load_jiejie_settings()

    assert data["settings"]["master"]["card"] == js.DEFAULT_CARD


def test_保存只改结界养成段(tmp_config_dir):
    _write_setting(UI_SAMPLE)
    before = _read_raw_yaml()

    per_account = {
        "master": {"card": "太鼓", "priority": ["六星太鼓", "六星斗鱼", "五星太鼓", "五星斗鱼"]},
        "slaves": {"card": "斗鱼", "priority": ["五星斗鱼", "五星太鼓", "六星斗鱼", "六星太鼓"]},
    }
    assert js.save_jiejie_settings(per_account) is True

    after = _read_raw_yaml()
    assert dict(after["启动项"]) == dict(before["启动项"])
    assert dict(after["结界突破"]) == dict(before["结界突破"])
    assert dict(after["寮三十"]) == dict(before["寮三十"])
    assert after["结界养成"]["master"]["优先结界卡"] == "太鼓"
    assert after["结界养成"]["slaves"]["寄养优先级"] == ["五星斗鱼", "五星太鼓", "六星斗鱼", "六星太鼓"]


def test_保存后能读回(tmp_config_dir):
    _write_setting(UI_SAMPLE)

    per_account = {
        "master": {"card": "太鼓", "priority": ["五星斗鱼", "五星太鼓", "六星斗鱼", "六星太鼓"]},
        "slaves": {"card": "斗鱼", "priority": ["六星斗鱼", "六星太鼓", "五星斗鱼", "五星太鼓"]},
    }
    js.save_jiejie_settings(per_account)
    data = js.load_jiejie_settings()

    assert data["settings"]["master"]["card"] == "太鼓"
    assert data["settings"]["master"]["priority"] == ["五星斗鱼", "五星太鼓", "六星斗鱼", "六星太鼓"]
    assert data["settings"]["slaves"]["priority"] == ["六星斗鱼", "六星太鼓", "五星斗鱼", "五星太鼓"]


def test_段缺失时能新建(tmp_config_dir):
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n  "slaves":\n    启动命令: "a.exe -v 1"\n')

    per_account = {
        "master": {"card": "太鼓", "priority": js.DEFAULT_PRIORITY},
        "slaves": {"card": "斗鱼", "priority": js.DEFAULT_PRIORITY},
    }
    assert js.save_jiejie_settings(per_account) is True

    after = _read_raw_yaml()
    assert after["结界养成"]["master"]["优先结界卡"] == "太鼓"
    assert "启动项" in after


def test_新建的优先级列表也是单行flow(tmp_config_dir):
    """段缺失时塞普通 list 会被写成块状多行，必须显式 flow"""
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n')

    js.save_jiejie_settings({"master": {"card": "太鼓", "priority": js.DEFAULT_PRIORITY}})
    text = _read_text()

    assert "寄养优先级: [六星太鼓, 六星斗鱼, 五星太鼓, 五星斗鱼]" in text
    assert "    - 六星太鼓" not in text


def test_新建段与上一段之间空一行(tmp_config_dir):
    """手写的 Setting.yml 段与段之间空一行，新建段不能紧贴上去"""
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n\n寮三十:\n  主账号: "master"\n')

    js.save_jiejie_settings({"master": {"card": "太鼓", "priority": js.DEFAULT_PRIORITY}})
    text = _read_text()

    assert '\n\n结界养成:\n  "master":\n' in text


def test_重复保存不会累积空行(tmp_config_dir):
    """空行只在新建段时补一次；段已存在时再加一次会变成两个空行"""
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n\n寮三十:\n  主账号: "master"\n')
    per_account = {"master": {"card": "太鼓", "priority": js.DEFAULT_PRIORITY}}

    js.save_jiejie_settings(per_account)
    first = _read_text()
    js.save_jiejie_settings(per_account)
    second = _read_text()

    assert first == second
    assert "\n\n\n结界养成:" not in second


def test_新建段的账号名带引号(tmp_config_dir):
    """与「启动项」的写法保持一致；不带引号的话手写风格会不一致"""
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n')

    js.save_jiejie_settings({"master": {"card": "太鼓", "priority": js.DEFAULT_PRIORITY}})
    text = _read_text()

    assert '结界养成:\n  "master":\n' in text
    # 加引号不能影响读取
    assert js.load_jiejie_settings()["settings"]["master"]["card"] == "太鼓"


def test_引号与注释保持(tmp_config_dir):
    """Lib.read_config 不带 preserve_quotes，引号会丢；本模块必须自己保住"""
    _write_setting(UI_SAMPLE)

    js.save_jiejie_settings({"master": {"card": "太鼓", "priority": js.DEFAULT_PRIORITY}})
    text = _read_text()

    assert "用户手写的说明" in text
    assert "# 主账号" in text
    assert '"master"' in text
    assert '"slaves"' in text


def test_长命令不被折行(tmp_config_dir):
    """Lib.write_config 不设 width（默认 80），会把启动命令折成两行"""
    _write_setting(UI_SAMPLE)

    js.save_jiejie_settings({"master": {"card": "太鼓", "priority": js.DEFAULT_PRIORITY}})
    command_lines = [line for line in _read_text().splitlines() if "a.exe -v 0" in line]

    assert len(command_lines) == 1
    assert command_lines[0].strip().endswith('-v 0"')


def test_配置损坏时拒绝保存而不是覆盖(tmp_config_dir):
    broken = "结界养成: [这不是: 合法\n  - yaml"
    _write_setting(broken)

    assert js.save_jiejie_settings({"master": {"card": "太鼓", "priority": js.DEFAULT_PRIORITY}}) is False
    assert _read_text() == broken


def test_非法取值拒绝保存(tmp_config_dir):
    _write_setting(UI_SAMPLE)

    assert js.save_jiejie_settings({"master": {"card": "不放置", "priority": js.DEFAULT_PRIORITY}}) is False
    assert js.save_jiejie_settings({"master": {"card": "太鼓", "priority": ["六星太鼓"] * 4}}) is False
    assert js.save_jiejie_settings({"master": {"card": "太鼓", "priority": ["六星太鼓", "六星太鼓", "五星太鼓", "五星斗鱼"]}}) is False
    assert js.save_jiejie_settings({"master": {"card": "太鼓", "priority": ["六星白达摩", "六星斗鱼", "五星太鼓", "五星斗鱼"]}}) is False


def test_没有可保存的账号时拒绝(tmp_config_dir):
    _write_setting(UI_SAMPLE)
    before = _read_text()

    assert js.save_jiejie_settings({}) is False
    assert _read_text() == before


def test_启动项里没有的账号被忽略(tmp_config_dir):
    """界面不该出现这类账号，但落盘层不能因为多传就崩或写脏配置"""
    _write_setting(UI_SAMPLE)

    per_account = {
        "master": {"card": "太鼓", "priority": js.DEFAULT_PRIORITY},
        "ghost": {"card": "斗鱼", "priority": js.DEFAULT_PRIORITY},
    }
    assert js.save_jiejie_settings(per_account) is True

    after = _read_raw_yaml()
    assert "ghost" not in after["结界养成"]
    assert after["结界养成"]["master"]["优先结界卡"] == "太鼓"

