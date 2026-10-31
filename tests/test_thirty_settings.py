# -*- coding: utf-8 -*-
"""寮三十配置读写层：归一化、回落与 YAML 保真（纯逻辑，不依赖 Qt）。

守住的都是「写错了会静默出错」的地方：

1. 配置缺失 / 损坏 / 长度不对时界面仍能打开（回落默认值，不抛异常）；
2. **次数 0 必须保留为 0**——它是最容易被 `if not value` 写成假值回落的点；
3. 保存只覆盖寮三十的四个键，`启动项` / `结界突破` 与注释逐字不变；
4. flow 列表（`副本: [...]`）与引号（`"master"`）写回后保持原样。
"""

import os

import pytest
import ruamel.yaml

import paths
from ui import thirty_settings as ts

# 一份贴近真实用法的最小配置：有注释、有引号、列表是 flow 风格
SAMPLE = """# 用户手写的说明，不能被抹掉
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
  # 周一到周日
  副本: ["魂虚", "魂虚", "魂虚", "魂虚", "魂虚", "魂海", "日蚀"]
  次数: [30, 30, 30, 30, 30, 30, 30]
"""


def _write_setting(text=SAMPLE):
    """把配置写到当前工作目录的 config/Setting.yml（用例已 chdir 到临时目录）"""
    os.makedirs(paths.CONFIG_DIR, exist_ok=True)
    with open(paths.SETTING, "w", encoding="utf-8") as handle:
        handle.write(text)
    return paths.SETTING


def _read_raw(path=None):
    """用与实现相同的 YAML 设置读回，便于断言引号等格式信息"""
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    with open(path or paths.SETTING, "r", encoding="utf-8") as handle:
        return yaml.load(handle)


def _read_text(path=None):
    with open(path or paths.SETTING, "r", encoding="utf-8") as handle:
        return handle.read()


# ------------------------------------------------------------ 常量


def test_选项与任务代码一致():
    """下拉选项必须是 Task_Thirty.py 的 match 分支，不能凭空加"""
    assert ts.FUBEN_OPTIONS == ("魂虚", "魂王", "魂海", "日蚀")
    assert ts.TIMES_OPTIONS == (0, 1, 30, 50)
    assert ts.WEEK_COUNT == 7


# ------------------------------------------------------------ 读取与回落


def test_配置缺失时返回默认值(tmp_config_dir):
    settings = ts.load_thirty_settings()

    assert settings["primary"] == "master"
    assert settings["secondary"] == "slaves"
    assert settings["fuben"] == [ts.DEFAULT_FUBEN] * 7
    assert settings["times"] == [ts.DEFAULT_TIMES] * 7


def test_配置损坏时不抛异常(tmp_config_dir):
    _write_setting("寮三十: [这不是: 合法\n  - yaml")

    settings = ts.load_thirty_settings()

    assert settings["fuben"] == [ts.DEFAULT_FUBEN] * 7
    assert settings["times"] == [ts.DEFAULT_TIMES] * 7


def test_能读回真实配置(tmp_config_dir):
    _write_setting()

    settings = ts.load_thirty_settings()

    assert settings["primary"] == "master"
    assert settings["secondary"] == "slaves"
    assert settings["fuben"] == ["魂虚", "魂虚", "魂虚", "魂虚", "魂虚", "魂海", "日蚀"]
    assert settings["times"] == [30] * 7
    assert settings["accounts"] == ["master", "slaves"]


def test_副本长度不足补默认值(tmp_config_dir):
    _write_setting(
        SAMPLE.replace(
            '副本: ["魂虚", "魂虚", "魂虚", "魂虚", "魂虚", "魂海", "日蚀"]',
            "副本: [魂海, 日蚀]",
        )
    )

    settings = ts.load_thirty_settings()

    assert len(settings["fuben"]) == 7
    assert settings["fuben"][:2] == ["魂海", "日蚀"]
    assert settings["fuben"][2:] == [ts.DEFAULT_FUBEN] * 5


def test_副本长度超出截断(tmp_config_dir):
    nine = ["魂虚"] * 7 + ["魂海", "日蚀"]
    _write_setting(
        SAMPLE.replace(
            '副本: ["魂虚", "魂虚", "魂虚", "魂虚", "魂虚", "魂海", "日蚀"]',
            "副本: [" + ", ".join(nine) + "]",
        )
    )

    settings = ts.load_thirty_settings()

    assert len(settings["fuben"]) == 7
    assert "魂海" not in settings["fuben"]


def test_非法副本回落且不影响其它项(tmp_config_dir):
    _write_setting(
        SAMPLE.replace(
            '副本: ["魂虚", "魂虚", "魂虚", "魂虚", "魂虚", "魂海", "日蚀"]',
            '副本: ["不存在的副本", "魂王", "魂海", "日蚀", "魂虚", "魂虚", "魂虚"]',
        )
    )

    settings = ts.load_thirty_settings()

    assert settings["fuben"][0] == ts.DEFAULT_FUBEN
    assert settings["fuben"][1:4] == ["魂王", "魂海", "日蚀"]
    assert any("不存在的副本" in text for text in settings["warnings"])


def test_次数0必须保留为0(tmp_config_dir):
    """最容易被写成假值回落的点：0 是合法取值，不是「空」"""
    _write_setting(SAMPLE.replace("次数: [30, 30, 30, 30, 30, 30, 30]", "次数: [0, 1, 30, 50, 0, 30, 50]"))

    settings = ts.load_thirty_settings()

    assert settings["times"] == [0, 1, 30, 50, 0, 30, 50]


@pytest.mark.parametrize("bad", ['"abc"', "7", "true", "3.5", "null"])
def test_非法次数回落30(tmp_config_dir, bad):
    _write_setting(
        SAMPLE.replace("次数: [30, 30, 30, 30, 30, 30, 30]", f"次数: [{bad}, 1, 30, 50, 30, 30, 30]")
    )

    settings = ts.load_thirty_settings()

    assert settings["times"][0] == ts.DEFAULT_TIMES
    assert settings["times"][1:] == [1, 30, 50, 30, 30, 30]


def test_主副账号相同会被纠正(tmp_config_dir):
    _write_setting(SAMPLE.replace('副账号: "slaves"', '副账号: "master"'))

    settings = ts.load_thirty_settings()

    assert settings["primary"] != settings["secondary"]


def test_账号不在启动项里会回落(tmp_config_dir):
    _write_setting(SAMPLE.replace('主账号: "master"', '主账号: "不存在"'))

    settings = ts.load_thirty_settings()

    assert settings["primary"] == "master"
    assert any("不存在" in text for text in settings["warnings"])


# ------------------------------------------------------------ 保存


def test_保存只改四个键(tmp_config_dir):
    _write_setting()
    before = _read_raw()

    assert ts.save_thirty_settings("slaves", "master", ["魂王"] * 7, [50] * 7) is True

    after = _read_raw()
    assert dict(after["启动项"]) == dict(before["启动项"])
    assert dict(after["结界突破"]) == dict(before["结界突破"])
    assert after["寮三十"]["主账号"] == "slaves"
    assert after["寮三十"]["副账号"] == "master"
    assert after["寮三十"]["副本"] == ["魂王"] * 7
    assert after["寮三十"]["次数"] == [50] * 7


def test_保存后能读回(tmp_config_dir):
    _write_setting()

    ts.save_thirty_settings("master", "slaves", ["日蚀", "魂海"] + ["魂虚"] * 5, [1, 30] + [50] * 5)
    settings = ts.load_thirty_settings()

    assert settings["fuben"] == ["日蚀", "魂海"] + ["魂虚"] * 5
    assert settings["times"] == [1, 30] + [50] * 5


def test_寮三十段缺失时能新建(tmp_config_dir):
    _write_setting(
        """启动项:
  "master":
    启动命令: "a.exe -v 0"
  "slaves":
    启动命令: "a.exe -v 1"
"""
    )

    assert ts.save_thirty_settings("master", "slaves", ["魂虚"] * 7, [30] * 7) is True

    after = _read_raw()
    assert after["寮三十"]["主账号"] == "master"
    assert after["寮三十"]["次数"] == [30] * 7
    assert "启动项" in after


def test_新建段的列表也是单行flow(tmp_config_dir):
    """段缺失时塞普通 list 会被写成块状多行，必须显式 flow"""
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n  "slaves":\n    启动命令: "a.exe -v 1"\n')

    ts.save_thirty_settings("master", "slaves", ["魂虚"] * 7, [30] * 7)
    text = _read_text()

    assert "副本: [" in text
    assert "次数: [30, 30, 30, 30, 30, 30, 30]" in text
    assert "    - 魂虚" not in text


def test_主副账号相同时拒绝保存(tmp_config_dir):
    _write_setting()
    before = _read_text()

    assert ts.save_thirty_settings("master", "master", ["魂虚"] * 7, [30] * 7) is False
    assert _read_text() == before


def test_只有一个账号时允许主副相同(tmp_config_dir):
    """单账号无法互斥：放行并靠界面的提示语说明，不阻断保存"""
    _write_setting('启动项:\n  "master":\n    启动命令: "a.exe -v 0"\n')

    assert ts.save_thirty_settings("master", "master", ["魂虚"] * 7, [30] * 7) is True
    assert _read_raw()["寮三十"]["副账号"] == "master"


def test_账号不在启动项时拒绝保存(tmp_config_dir):
    _write_setting()

    assert ts.save_thirty_settings("ghost", "slaves", ["魂虚"] * 7, [30] * 7) is False


def test_非法取值拒绝保存(tmp_config_dir):
    _write_setting()

    assert ts.save_thirty_settings("master", "slaves", ["不存在的副本"] * 7, [30] * 7) is False
    assert ts.save_thirty_settings("master", "slaves", ["魂虚"] * 7, [7] * 7) is False
    assert ts.save_thirty_settings("master", "slaves", ["魂虚"] * 6, [30] * 7) is False


def test_配置损坏时拒绝保存而不是覆盖(tmp_config_dir):
    """解析不了就不写：写回等于把用户原内容抹掉"""
    broken = "寮三十: [这不是: 合法\n  - yaml"
    _write_setting(broken)

    assert ts.save_thirty_settings("master", "slaves", ["魂虚"] * 7, [30] * 7) is False
    assert _read_text() == broken


# ------------------------------------------------------------ 格式保真


def test_副本保持单行flow(tmp_config_dir):
    _write_setting()

    ts.save_thirty_settings("master", "slaves", ["魂王", "魂虚", "魂海", "日蚀", "魂虚", "魂虚", "魂虚"], [30] * 7)
    text = _read_text()

    assert '副本: [魂王, 魂虚, 魂海, 日蚀, 魂虚, 魂虚, 魂虚]' in text
    assert "    - 魂王" not in text


def test_引号保持(tmp_config_dir):
    """Lib.read_config 不带 preserve_quotes，引号会丢；本模块必须自己保住"""
    _write_setting()

    ts.save_thirty_settings("slaves", "master", ["魂虚"] * 7, [30] * 7)
    text = _read_text()

    assert '"master"' in text
    assert '"slaves"' in text


def test_注释保持(tmp_config_dir):
    _write_setting()

    ts.save_thirty_settings("master", "slaves", ["魂虚"] * 7, [30] * 7)
    text = _read_text()

    assert "用户手写的说明" in text          # 顶部注释
    assert "# 主账号" in text                # 行尾注释
    assert "# 周一到周日" in text            # 段内注释


def test_长命令不被折行(tmp_config_dir):
    """Lib.write_config 不设 width（默认 80），会把启动命令折成两行"""
    _write_setting()

    ts.save_thirty_settings("master", "slaves", ["魂虚"] * 7, [30] * 7)
    lines = _read_text().splitlines()

    command_lines = [line for line in lines if "a.exe -v 0" in line]
    assert len(command_lines) == 1
    assert command_lines[0].strip().endswith('-v 0"')
