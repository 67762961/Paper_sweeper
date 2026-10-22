# -*- coding: utf-8 -*-
"""check_lasttime 在配置损坏时的数据保护行为。

旧行为：YAML 坏了 -> 裸 except 吞掉 -> config 重置为空 -> 立刻写回文件。
后果是**用户积累的整份历史记录被静默清空**，而提示只有一行「配置文件格式错误 将重置」，
用户根本不知道数据没了、也没法找回。

新行为：重置前先把原文件备份成 .corrupt-<时间戳>.bak，并输出明确日志说明备份位置。
"""

import glob
import os

import pytest

import Lib

GOOD_CONTENT = (
    "master:\n"
    "  邮件领取: 2026-10-19 08:00:00\n"
    "  每日一签: 2026-10-19 08:01:00\n"
    "slaves:\n"
    "  邮件领取: 2026-10-19 09:00:00\n"
)

BROKEN_CONTENT = GOOD_CONTENT + "寮三十: [未闭合\n"


def test_corrupt_config_is_backed_up(tmp_config_dir, tmp_state_dir):
    """重置前必须留下 .bak，且内容与损坏前一致"""
    (tmp_state_dir / "Last_times.yml").write_text(BROKEN_CONTENT, encoding="utf-8")

    Lib.check_lasttime("master", "邮件领取")

    backups = glob.glob(str(tmp_state_dir / "Last_times.yml.corrupt-*.bak"))
    assert len(backups) == 1, "损坏配置应恰好备份一份"
    assert open(backups[0], encoding="utf-8").read() == BROKEN_CONTENT


def test_corrupt_config_backup_keeps_all_accounts(tmp_config_dir, tmp_state_dir):
    """备份里必须保有原来所有账号的记录，不能只剩被查询的那一个"""
    (tmp_state_dir / "Last_times.yml").write_text(BROKEN_CONTENT, encoding="utf-8")

    Lib.check_lasttime("master", "邮件领取")

    backup = glob.glob(str(tmp_state_dir / "Last_times.yml.corrupt-*.bak"))[0]
    content = open(backup, encoding="utf-8").read()
    assert "每日一签" in content, "master 的其它记录不能丢"
    assert "slaves" in content, "slaves 账号不能丢"


def test_corrupt_config_resets_to_initial_value(tmp_config_dir, tmp_state_dir):
    """备份归备份，本次调用仍要返回初始值让任务能继续"""
    (tmp_state_dir / "Last_times.yml").write_text(BROKEN_CONTENT, encoding="utf-8")

    moment = Lib.check_lasttime("master", "邮件领取")

    assert moment.year == 2000
    assert moment.month == 1 and moment.day == 1


def test_corrupt_config_logs_backup_path(tmp_config_dir, capsys, tmp_state_dir):
    """日志必须告诉用户备份到哪了，否则等于没备份"""
    (tmp_state_dir / "Last_times.yml").write_text(BROKEN_CONTENT, encoding="utf-8")

    Lib.check_lasttime("master", "邮件领取")

    output = capsys.readouterr().out
    assert "WAIT-" in output
    assert ".corrupt-" in output, "日志里应出现备份文件名"
    assert ".bak" in output


def test_healthy_config_is_not_backed_up(tmp_config_dir, tmp_state_dir):
    """配置正常时不应产生任何备份文件"""
    Lib.write_config("./state/Last_times.yml", {"master": {"邮件领取": "2026-10-19 08:00:00"}})

    Lib.check_lasttime("master", "邮件领取")

    assert glob.glob(str(tmp_config_dir / "*.bak")) == []


def test_empty_file_is_not_treated_as_corrupt(tmp_config_dir, tmp_state_dir):
    """空文件是正常初始状态，不该触发备份"""
    (tmp_state_dir / "Last_times.yml").write_text("", encoding="utf-8")

    moment = Lib.check_lasttime("master", "邮件领取")

    assert moment.year == 2000
    assert glob.glob(str(tmp_config_dir / "*.bak")) == [], "空文件不算损坏，无需备份"


def test_broken_time_string_is_not_treated_as_corrupt(tmp_config_dir, tmp_state_dir):
    """单个时间值写错属于「值非法」，不是「文件损坏」，不应备份整份文件"""
    Lib.write_config("./state/Last_times.yml", {"master": {"邮件领取": "不是时间"}})

    moment = Lib.check_lasttime("master", "邮件领取")

    assert moment.year == 2000
    assert glob.glob(str(tmp_config_dir / "*.bak")) == []


def test_backup_failure_still_returns_initial_value(tmp_config_dir, monkeypatch, capsys, tmp_state_dir):
    """备份本身失败时也不能中断流程，但要明确提示内容将丢失"""
    (tmp_state_dir / "Last_times.yml").write_text(BROKEN_CONTENT, encoding="utf-8")

    def 假的备份失败(path):
        return None

    monkeypatch.setattr(Lib, "_backup_corrupt_config", 假的备份失败)

    moment = Lib.check_lasttime("master", "邮件领取")

    assert moment.year == 2000
    output = capsys.readouterr().out
    assert "备份失败" in output


def test_no_bare_except_remains():
    """check_lasttime 里不允许再出现裸 except（会吞掉 KeyboardInterrupt 等）"""
    source = open(Lib.__file__, encoding="utf-8").read()
    assert "except:" not in source, "Lib.py 中仍有裸 except"


def test_config_can_be_reused_after_reset(tmp_config_dir, tmp_state_dir):
    """重置后再写入，下一次读取应正常返回新值（不能一直卡在损坏状态）"""
    (tmp_state_dir / "Last_times.yml").write_text(BROKEN_CONTENT, encoding="utf-8")
    Lib.check_lasttime("master", "邮件领取")

    data = Lib.read_config("./state/Last_times.yml")
    data["master"]["邮件领取"] = "2026-10-21 08:00:00"
    Lib.write_config("./state/Last_times.yml", data)

    moment = Lib.check_lasttime("master", "邮件领取")
    assert moment.strftime("%Y-%m-%d %H:%M:%S") == "2026-10-21 08:00:00"
