# -*- coding: utf-8 -*-
"""调试截图档位的偏好读写用例（不碰 GUI、不真的截图）。

守住三件事：
1. 默认 `off`——不改变老用户行为，升级后不会突然往磁盘里写几千张图；
2. 非法值一律回落默认（字符串拼错、数字、布尔、null、列表都不能生效）；
3. 与已有的主题 / 日志 / 完成动作那几组键互不干扰。

档位含义与 `miss` 的坑见 `ARCHITECTURE.md` §8.1。
"""

import json
import os

import pytest

from ui import prefs


def _write_prefs(payload):
    """把 payload 写进 state/gui.json（tmp_config_dir 夹具已切好工作目录）"""
    os.makedirs("state", exist_ok=True)
    with open(prefs.PREFS_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    return prefs.PREFS_PATH


# ------------------------------------------------------------ 默认值


def test_默认档位是关闭(tmp_config_dir):
    """升级后不主动开：没有这个键时必须回落 off，而不是 miss/all"""
    assert prefs.load_prefs()["debug_shots"] == "off"


def test_默认值里包含该键(tmp_config_dir):
    assert "debug_shots" in prefs.DEFAULT_PREFS


# ------------------------------------------------------------ 三档往返


@pytest.mark.parametrize("mode", ["off", "miss", "all"])
def test_三个档位都能存能读(tmp_config_dir, mode):
    _write_prefs({"debug_shots": mode})

    assert prefs.load_prefs()["debug_shots"] == mode


@pytest.mark.parametrize("mode", ["off", "miss", "all"])
def test_保存后能原样读回(tmp_config_dir, mode):
    merged = prefs.load_prefs()
    merged["debug_shots"] = mode

    assert prefs.save_prefs(merged) is True
    assert prefs.load_prefs()["debug_shots"] == mode


# ------------------------------------------------------------ 非法值


@pytest.mark.parametrize(
    "bad_value",
    ["ALL", "True", "on", "", "none", "全部", 1, 0, True, False, None, ["all"], {"mode": "all"}],
)
def test_非法档位回落默认(tmp_config_dir, bad_value):
    """手改 gui.json 写出非法值时回落 off，不能静默变成「全部保存」"""
    _write_prefs({"debug_shots": bad_value})

    assert prefs.load_prefs()["debug_shots"] == "off"


def test_合法档位列表只有三个(tmp_config_dir):
    assert prefs.VALID_SHOT_MODES == ("off", "miss", "all")


def test_每个档位都有界面标签(tmp_config_dir):
    """弹窗按这个表填下拉框，漏一个就会 IndexError"""
    assert set(prefs.SHOT_MODE_LABELS) == set(prefs.VALID_SHOT_MODES)


# ------------------------------------------------------------ 互不干扰


def test_不影响其它键(tmp_config_dir):
    _write_prefs(
        {
            "theme": "dark",
            "log_auto_scroll": False,
            "log_font_size": 14,
            "after_run_sleep": True,
            "debug_shots": "all",
        }
    )

    loaded = prefs.load_prefs()

    assert loaded["theme"] == "dark"
    assert loaded["log_auto_scroll"] is False
    assert loaded["log_font_size"] == 14
    assert loaded["after_run_sleep"] is True
    assert loaded["debug_shots"] == "all"


def test_改档位不会清掉完成动作(tmp_config_dir):
    """设置弹窗只提交自己那几项，合并写盘时不能把别的键冲掉"""
    _write_prefs({"after_run_sleep": True, "after_run_power": "logoff"})
    merged = prefs.load_prefs()
    merged["debug_shots"] = "miss"

    assert prefs.save_prefs(merged) is True

    loaded = prefs.load_prefs()
    assert loaded["debug_shots"] == "miss"
    assert loaded["after_run_sleep"] is True
    assert loaded["after_run_power"] == "logoff"


def test_老配置文件缺该键也能读(tmp_config_dir):
    """老用户的 gui.json 只有主题三项，读出来必须是 off 而不是 KeyError"""
    _write_prefs({"theme": "light", "log_auto_scroll": True, "log_font_size": 12})

    assert prefs.load_prefs()["debug_shots"] == "off"
