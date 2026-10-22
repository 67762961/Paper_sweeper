# -*- coding: utf-8 -*-
"""配置文件损坏时的容错行为。

配置是用户可以手改的普通文本，写盘中断、编辑器崩溃、手动编辑出错都会留下坏 YAML。
这些路径在真机上很难复现，但一旦踩到，旧行为是「GUI 启动即崩」或「历史记录被静默清空」。

本文件守住两条底线：
1. 读配置失败不能抛异常（read_config 返回 {}，GUI 仍能启动）；
2. 重置损坏配置前必须备份原文件（不能静默清空用户的历史）。
"""

import os

import pytest

import Lib
import main


# --------------------------------------------------------- read_config 容错

BROKEN_YAML = "master:\n  邮件领取: [未闭合\n"


def test_read_config_missing_file_returns_empty(tmp_config_dir):
    assert Lib.read_config("./config/不存在.yml") == {}


def test_read_config_broken_yaml_returns_empty(tmp_config_dir):
    """坏 YAML 不能让 GUI 启动崩溃，应返回空字典"""
    (tmp_config_dir / "Setting.yml").write_text(BROKEN_YAML, encoding="utf-8")
    assert Lib.read_config("./config/Setting.yml") == {}


def test_read_config_empty_file_returns_empty(tmp_config_dir):
    """空文件解析结果是 None，必须归一成 {}，否则 read_accounts 会对 None 取键"""
    (tmp_config_dir / "Last_times.yml").write_text("", encoding="utf-8")
    assert Lib.read_config("./state/Last_times.yml") == {}


def test_read_config_invalid_utf8_returns_empty(tmp_config_dir):
    """非法 UTF-8 字节（比如被别的编码覆盖）也不能抛异常"""
    (tmp_config_dir / "Setting.yml").write_bytes(b"\xff\xfe\x00broken")
    assert Lib.read_config("./config/Setting.yml") == {}


def test_read_config_valid_content_still_works(tmp_config_dir):
    Lib.write_config("./config/Setting.yml", {"键": {"子键": 1}})
    assert Lib.read_config("./config/Setting.yml")["键"]["子键"] == 1


def test_read_config_logs_reason(tmp_config_dir, capsys):
    """失败时必须留下可追溯的日志，而不是悄悄返回空字典"""
    (tmp_config_dir / "Setting.yml").write_text(BROKEN_YAML, encoding="utf-8")
    Lib.read_config("./config/Setting.yml")
    output = capsys.readouterr().out
    assert "INFO-" in output
    assert "Setting.yml" in output


# ------------------------------------------- 上层调用方不再因坏配置崩溃


def test_read_completions_survives_broken_config(tmp_config_dir):
    """GUI 启动会调它来渲染左侧状态；坏配置不能让它抛异常"""
    (tmp_config_dir / "Last_times.yml").write_text(BROKEN_YAML, encoding="utf-8")
    assert main.read_completions() == {}


def test_read_task_switches_survives_broken_config(tmp_config_dir):
    (tmp_config_dir / "Gui_state.yml").write_text("任务开关: [坏\n", encoding="utf-8")
    switches = main.read_task_switches()
    assert set(switches) == {task.key for task in main.TASK_REGISTRY}
    assert all(switches.values()), "坏配置应按默认全开处理"


def test_read_accounts_survives_broken_config(tmp_config_dir):
    (tmp_config_dir / "Last_times.yml").write_text(BROKEN_YAML, encoding="utf-8")
    assert Lib.read_accounts() == []


def test_entry_done_today_survives_broken_config(tmp_config_dir):
    (tmp_config_dir / "Last_times.yml").write_text(BROKEN_YAML, encoding="utf-8")
    assert main.entry_done_today(main.get_task("digui")) is False
