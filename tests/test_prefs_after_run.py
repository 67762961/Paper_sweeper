# -*- coding: utf-8 -*-
"""「完整运行完成后」两个开关的偏好读写用例（不碰 GUI、不真的睡眠）。

守住三件事：
1. 两个新键默认关闭——不改变老用户的行为；
2. 非法值（字符串、数字、null）一律回落默认，不能因为手改 gui.json 就把电脑睡过去；
3. 与已有的三个键互不干扰。
"""

import json
import os

import pytest

from ui import prefs


def _write_prefs(tmp_config_dir, payload):
    """把 payload 写进 state/gui.json（tmp_config_dir 夹具已切好工作目录）"""
    os.makedirs("state", exist_ok=True)
    with open(prefs.PREFS_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    return prefs.PREFS_PATH


# ------------------------------------------------------------ 默认值


def test_两个新开关默认都是关闭(tmp_config_dir):
    loaded = prefs.load_prefs()

    assert loaded["after_run_close_emulator"] is False
    assert loaded["after_run_sleep"] is False


def test_默认值里包含两个新键(tmp_config_dir):
    assert "after_run_close_emulator" in prefs.DEFAULT_PREFS
    assert "after_run_sleep" in prefs.DEFAULT_PREFS


def test_文件不存在时不创建文件(tmp_config_dir):
    prefs.load_prefs()

    assert not os.path.exists(prefs.PREFS_PATH)


# ------------------------------------------------------------ 读取


def test_能读回开启状态(tmp_config_dir):
    _write_prefs(
        tmp_config_dir,
        {"after_run_close_emulator": True, "after_run_sleep": True},
    )

    loaded = prefs.load_prefs()

    assert loaded["after_run_close_emulator"] is True
    assert loaded["after_run_sleep"] is True


def test_能读回一开一关(tmp_config_dir):
    _write_prefs(tmp_config_dir, {"after_run_close_emulator": True, "after_run_sleep": False})

    loaded = prefs.load_prefs()

    assert loaded["after_run_close_emulator"] is True
    assert loaded["after_run_sleep"] is False


@pytest.mark.parametrize(
    "bad_value",
    [
        "false",   # 字符串：truthy，若不做类型校验会被当成开启
        "true",
        "0",
        "1",
        0,
        1,
        None,
        [],
        {},
    ],
)
def test_非法值回落到默认(tmp_config_dir, bad_value):
    """手改 gui.json 写出字符串或数字时，必须回落为关闭，不能误触发睡眠"""
    _write_prefs(tmp_config_dir, {"after_run_sleep": bad_value})

    assert prefs.load_prefs()["after_run_sleep"] is False


def test_布尔值之外的键被忽略(tmp_config_dir):
    _write_prefs(tmp_config_dir, {"after_run_sleep": True, "未知键": "随便写"})

    loaded = prefs.load_prefs()

    assert "未知键" not in loaded
    assert loaded["after_run_sleep"] is True


# ------------------------------------------------------------ 保存


def test_保存后能读回(tmp_config_dir):
    merged = prefs.load_prefs()
    merged["after_run_close_emulator"] = True
    merged["after_run_sleep"] = True

    assert prefs.save_prefs(merged) is True

    loaded = prefs.load_prefs()
    assert loaded["after_run_close_emulator"] is True
    assert loaded["after_run_sleep"] is True


def test_保存不会丢掉已有键(tmp_config_dir):
    merged = prefs.load_prefs()
    merged["theme"] = "dark"
    merged["after_run_sleep"] = True

    prefs.save_prefs(merged)

    loaded = prefs.load_prefs()
    assert loaded["theme"] == "dark"
    assert loaded["after_run_sleep"] is True
    assert loaded["log_font_size"] == 12


def test_保存时未知键不写盘(tmp_config_dir):
    merged = prefs.load_prefs()
    merged["随便写的键"] = "值"

    prefs.save_prefs(merged)

    with open(prefs.PREFS_PATH, "r", encoding="utf-8") as handle:
        on_disk = json.load(handle)
    assert "随便写的键" not in on_disk


def test_保存失败返回False而不是抛异常(tmp_config_dir, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("磁盘只读")

    monkeypatch.setattr(prefs.os, "replace", boom)

    assert prefs.save_prefs(prefs.load_prefs()) is False


# ------------------------------------------------------------ 互不干扰


def test_原有三个键的行为不变(tmp_config_dir):
    _write_prefs(
        tmp_config_dir,
        {
            "theme": "dark",
            "log_auto_scroll": False,
            "log_font_size": 14,
            "after_run_sleep": True,
        },
    )

    loaded = prefs.load_prefs()

    assert loaded["theme"] == "dark"
    assert loaded["log_auto_scroll"] is False
    assert loaded["log_font_size"] == 14
    assert loaded["after_run_sleep"] is True


def test_只有两个新键的旧文件也能读(tmp_config_dir):
    """老用户的 gui.json 里没有这两个键，读出来必须是关闭而不是 KeyError"""
    _write_prefs(tmp_config_dir, {"theme": "light", "log_auto_scroll": True, "log_font_size": 12})

    loaded = prefs.load_prefs()

    assert loaded["after_run_close_emulator"] is False
    assert loaded["after_run_sleep"] is False
