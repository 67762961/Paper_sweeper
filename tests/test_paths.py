# -*- coding: utf-8 -*-
"""配置 / 状态分层的路径定义与旧布局迁移。

PR7 把「用户手改的静态配置」与「程序读写的运行期状态」分开：

    config/Setting.yml       静态配置，用户手改
    state/Last_times.yml     任务完成时间，程序写
    state/Gui_state.yml      任务开关，程序写
    state/gui.json           界面偏好，程序写

本文件守住三件事：
1. 路径常量集中在 paths.py，没有模块自己拼字符串；
2. ensure_state_dir() 会把旧布局（都在 config/ 下）的文件搬到 state/；
3. 迁移是幂等的，且「两边都有」时不覆盖新文件。
"""

import os

import pytest

import Lib
import main
import paths
from ui import prefs


# ------------------------------------------------------------ 路径常量


def test_paths_point_to_expected_locations():
    assert paths.SETTING == os.path.join("config", "Setting.yml")
    assert paths.LAST_TIMES == os.path.join("state", "Last_times.yml")
    assert paths.GUI_STATE == os.path.join("state", "Gui_state.yml")
    assert paths.PREFS == os.path.join("state", "gui.json")


def test_state_files_are_all_under_state_dir():
    """状态类文件必须全部在 state/ 下，不能再有落在 config/ 的"""
    for path in (paths.LAST_TIMES, paths.GUI_STATE, paths.PREFS):
        assert path.startswith(paths.STATE_DIR + os.sep), path


def test_setting_stays_in_config_dir():
    """Setting.yml 是用户手改的静态配置，留在 config/"""
    assert paths.SETTING.startswith(paths.CONFIG_DIR + os.sep)


def test_callers_use_path_constants():
    """main / prefs 必须引用常量，而不是自己拼字符串"""
    assert main.GUI_STATE_PATH == paths.GUI_STATE
    assert prefs.PREFS_PATH == paths.PREFS


# ------------------------------------------------------------ 目录创建


def test_ensure_state_dir_creates_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert not os.path.isdir("state")
    paths.ensure_state_dir()
    assert os.path.isdir("state")


def test_ensure_state_dir_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert paths.ensure_state_dir() == 0
    assert paths.ensure_state_dir() == 0


# ------------------------------------------------------------ 旧布局迁移


def test_migrates_legacy_last_times(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("config")
    with open(os.path.join("config", "Last_times.yml"), "w", encoding="utf-8") as f:
        f.write("master:\n  邮件领取: 2026-10-19 08:00:00\n")

    assert paths.ensure_state_dir() == 1

    assert os.path.exists(os.path.join("state", "Last_times.yml"))
    assert not os.path.exists(os.path.join("config", "Last_times.yml")), "旧文件应被移走"
    content = open(os.path.join("state", "Last_times.yml"), encoding="utf-8").read()
    assert "邮件领取" in content, "迁移不能丢内容"


def test_migrates_all_three_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("config")
    for name, content in (
        ("Last_times.yml", "master:\n  邮件领取: 2026-10-19 08:00:00\n"),
        ("Gui_state.yml", "任务开关:\n  digui: false\n"),
        ("gui.json", '{"theme": "dark"}'),
    ):
        with open(os.path.join("config", name), "w", encoding="utf-8") as f:
            f.write(content)

    assert paths.ensure_state_dir() == 3

    for name in ("Last_times.yml", "Gui_state.yml", "gui.json"):
        assert os.path.exists(os.path.join("state", name)), name
        assert not os.path.exists(os.path.join("config", name)), name


def test_does_not_overwrite_existing_state_file(tmp_path, monkeypatch):
    """两边都有时不覆盖：新文件是当前真相，旧文件只是残留"""
    monkeypatch.chdir(tmp_path)
    os.makedirs("config")
    os.makedirs("state")
    with open(os.path.join("config", "Last_times.yml"), "w", encoding="utf-8") as f:
        f.write("旧内容: 1\n")
    with open(os.path.join("state", "Last_times.yml"), "w", encoding="utf-8") as f:
        f.write("新内容: 1\n")

    assert paths.ensure_state_dir() == 0

    content = open(os.path.join("state", "Last_times.yml"), encoding="utf-8").read()
    assert "新内容" in content and "旧内容" not in content


def test_no_legacy_files_means_no_move(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("config")
    assert paths.ensure_state_dir() == 0


# ------------------------------------------- 迁移后各模块能读到旧数据


def test_check_lasttime_reads_migrated_history(tmp_path, monkeypatch):
    """迁移后 check_lasttime 应读到旧的历史时间，而不是初始化成 2000"""
    monkeypatch.chdir(tmp_path)
    os.makedirs("config")
    # 用 write_config 造旧文件，与真实写盘格式一致（时间值带引号，读回来是字符串）
    Lib.write_config(
        os.path.join("config", "Last_times.yml"),
        {"master": {"邮件领取": "2026-10-19 08:30:00"}},
    )

    moment = Lib.check_lasttime("master", "邮件领取")

    assert moment.strftime("%Y-%m-%d %H:%M:%S") == "2026-10-19 08:30:00"


def test_read_completions_reads_migrated_history(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("config")
    Lib.write_config(
        os.path.join("config", "Last_times.yml"),
        {"master": {"邮件领取": "2026-10-19 09:15:00"}},
    )

    completions = main.read_completions()

    assert completions["master"]["邮件领取"].hour == 9


def test_read_task_switches_reads_migrated_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("config")
    with open(os.path.join("config", "Gui_state.yml"), "w", encoding="utf-8") as f:
        f.write("任务开关:\n  digui: false\n")

    # 不显式调用 ensure_state_dir：读取本身就该触发迁移
    assert main.read_task_switches()["digui"] is False
    assert os.path.exists(os.path.join("state", "Gui_state.yml"))


def test_load_prefs_reads_migrated_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("config")
    with open(os.path.join("config", "gui.json"), "w", encoding="utf-8") as f:
        f.write('{"theme": "dark"}')

    # 不显式调用 ensure_state_dir：读取本身就该触发迁移
    assert prefs.load_prefs()["theme"] == "dark"
    assert os.path.exists(os.path.join("state", "gui.json"))


def test_read_paths_do_not_leave_legacy_file_behind(tmp_path, monkeypatch):
    """三个读取入口都应把旧文件搬走，而不是复制一份留着"""
    monkeypatch.chdir(tmp_path)
    os.makedirs("config")
    for name, content in (
        ("Last_times.yml", "master:\n  邮件领取: '2026-10-19 08:00:00'\n"),
        ("Gui_state.yml", "任务开关:\n  digui: false\n"),
        ("gui.json", '{"theme": "dark"}'),
    ):
        with open(os.path.join("config", name), "w", encoding="utf-8") as f:
            f.write(content)

    main.read_completions()
    main.read_task_switches()
    prefs.load_prefs()

    for name in ("Last_times.yml", "Gui_state.yml", "gui.json"):
        assert os.path.exists(os.path.join("state", name)), name
        assert not os.path.exists(os.path.join("config", name)), f"{name} 应已搬走"


def test_save_prefs_creates_state_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert prefs.save_prefs({"theme": "dark"}) is True
    assert os.path.exists(os.path.join("state", "gui.json"))
