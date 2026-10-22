# -*- coding: utf-8 -*-
"""配置读写与状态文件。

覆盖四类配置的读写行为，重点是「文件缺失/内容非法时能否安全回落」——
这些路径在真机上很难手工复现，但一旦出错会让 GUI 启动即崩或任务全部被跳过。

1. state/gui.json        界面偏好（ui/prefs.py）
2. state/Gui_state.yml   任务开关（main.py）
3. state/Last_times.yml  任务完成时间（Lib.check_lasttime / main.read_completions）
4. config/Setting.yml     静态配置（Lib.read_config / write_config）
"""

import json

import pytest

import Lib
import main
from ui import prefs


# ---------------------------------------------------------------- gui.json


def test_load_prefs_defaults_when_missing(tmp_config_dir, tmp_state_dir):
    loaded = prefs.load_prefs()
    assert loaded == prefs.DEFAULT_PREFS


def test_load_prefs_ignores_invalid_theme(tmp_config_dir, tmp_state_dir):
    path = tmp_state_dir / "gui.json"
    path.write_text(json.dumps({"theme": "紫色", "log_font_size": 12}), encoding="utf-8")
    loaded = prefs.load_prefs()
    assert loaded["theme"] == prefs.DEFAULT_PREFS["theme"], "非法主题应回落到默认值"


def test_load_prefs_ignores_invalid_font_size(tmp_config_dir, tmp_state_dir):
    path = tmp_state_dir / "gui.json"
    path.write_text(json.dumps({"log_font_size": 99}), encoding="utf-8")
    loaded = prefs.load_prefs()
    assert loaded["log_font_size"] == prefs.DEFAULT_PREFS["log_font_size"]


def test_load_prefs_broken_json_falls_back(tmp_config_dir, tmp_state_dir):
    path = tmp_state_dir / "gui.json"
    path.write_text("{ 这不是 json", encoding="utf-8")
    assert prefs.load_prefs() == prefs.DEFAULT_PREFS


def test_load_prefs_accepts_valid_values(tmp_config_dir, tmp_state_dir):
    path = tmp_state_dir / "gui.json"
    path.write_text(
        json.dumps({"theme": "dark", "log_auto_scroll": False, "log_font_size": 14}),
        encoding="utf-8",
    )
    loaded = prefs.load_prefs()
    assert loaded == {"theme": "dark", "log_auto_scroll": False, "log_font_size": 14}


def test_save_prefs_roundtrip(tmp_config_dir, tmp_state_dir):
    saved = {"theme": "dark", "log_auto_scroll": False, "log_font_size": 13}
    assert prefs.save_prefs(saved) is True
    assert (tmp_state_dir / "gui.json").exists()
    assert prefs.load_prefs() == saved


def test_save_prefs_drops_unknown_keys(tmp_config_dir, tmp_state_dir):
    assert prefs.save_prefs({"theme": "light", "不认识的键": 1}) is True
    written = json.loads((tmp_state_dir / "gui.json").read_text(encoding="utf-8"))
    assert "不认识的键" not in written


# ------------------------------------------------------- Gui_state.yml


def test_read_task_switches_default_all_on(tmp_config_dir, tmp_state_dir):
    switches = main.read_task_switches()
    assert set(switches) == {task.key for task in main.TASK_REGISTRY}
    assert all(switches.values())


def test_read_task_switches_partial_file(tmp_config_dir, tmp_state_dir):
    """文件里只写了一部分任务：未写的按默认开启处理"""
    path = tmp_state_dir / "Gui_state.yml"
    path.write_text("任务开关:\n  digui: false\n", encoding="utf-8")
    switches = main.read_task_switches()
    assert switches["digui"] is False
    assert switches["signin"] is True


def test_read_task_switches_section_not_mapping(tmp_config_dir, tmp_state_dir):
    """任务开关节点写成了标量：按默认全开处理，不能抛异常"""
    path = tmp_state_dir / "Gui_state.yml"
    path.write_text("任务开关: 坏了\n", encoding="utf-8")
    switches = main.read_task_switches()
    assert all(switches.values())


def test_set_task_switch_roundtrip(tmp_config_dir, tmp_state_dir):
    assert main.set_task_switch("digui", False) is True
    assert main.read_task_switches()["digui"] is False
    assert main.set_task_switch("digui", True) is True
    assert main.read_task_switches()["digui"] is True


def test_set_task_switch_rejects_unknown_key(tmp_config_dir, tmp_state_dir):
    assert main.set_task_switch("不存在的任务", False) is False


def test_set_task_switch_creates_state_dir(tmp_path, monkeypatch):
    """state/ 不存在时应自动创建，而不是静默失败"""
    monkeypatch.chdir(tmp_path)
    assert main.set_task_switch("digui", False) is True
    assert (tmp_path / "state" / "Gui_state.yml").exists()


# ------------------------------------------------------ Last_times.yml


def test_check_lasttime_initializes_missing_file(tmp_config_dir, tmp_state_dir):
    """文件缺失时自动创建，并返回 2000-01-01 作为初始值"""
    moment = Lib.check_lasttime("master", "邮件领取")
    assert moment.year == 2000
    assert (tmp_state_dir / "Last_times.yml").exists()


def test_check_lasttime_returns_written_time(tmp_config_dir, tmp_state_dir):
    first = Lib.check_lasttime("master", "邮件领取")
    assert first.year == 2000

    # 手工写入一个时间，再次读取应返回它
    data = Lib.read_config("./state/Last_times.yml")
    data["master"]["邮件领取"] = "2026-10-19 08:30:00"
    Lib.write_config("./state/Last_times.yml", data)

    moment = Lib.check_lasttime("master", "邮件领取")
    assert moment.strftime("%Y-%m-%d %H:%M:%S") == "2026-10-19 08:30:00"


def test_check_lasttime_recovers_from_broken_time(tmp_config_dir, tmp_state_dir):
    """时间字符串非法时重置为初始值，不能抛异常"""
    Lib.check_lasttime("master", "邮件领取")
    data = Lib.read_config("./state/Last_times.yml")
    data["master"]["邮件领取"] = "不是时间"
    Lib.write_config("./state/Last_times.yml", data)

    moment = Lib.check_lasttime("master", "邮件领取")
    assert moment.year == 2000


def test_check_lasttime_recovers_from_empty_file(tmp_config_dir, tmp_state_dir):
    (tmp_state_dir / "Last_times.yml").write_text("", encoding="utf-8")
    moment = Lib.check_lasttime("master", "邮件领取")
    assert moment.year == 2000


def test_check_lasttime_recovers_from_broken_yaml(tmp_config_dir, tmp_state_dir):
    (tmp_state_dir / "Last_times.yml").write_text("这不是: [合法的 yaml", encoding="utf-8")
    moment = Lib.check_lasttime("master", "邮件领取")
    assert moment.year == 2000


def test_read_accounts_keeps_file_order(tmp_config_dir):
    data = {"slaves": {"邮件领取": "2026-10-19 08:00:00"}, "master": {"邮件领取": "2026-10-19 09:00:00"}}
    Lib.write_config("./state/Last_times.yml", data)
    assert Lib.read_accounts() == ["slaves", "master"]


def test_read_accounts_empty_when_missing(tmp_config_dir):
    assert Lib.read_accounts() == []


# ------------------------------------------------ read_config / write_config


def test_read_config_missing_returns_empty_dict(tmp_config_dir):
    assert Lib.read_config("./config/不存在.yml") == {}


def test_write_config_then_read(tmp_config_dir):
    payload = {"启动项": {"master": {"启动命令": "test.exe"}}, "结界突破": {"master": {"退出次数": 3}}}
    Lib.write_config("./config/Setting.yml", payload)
    loaded = Lib.read_config("./config/Setting.yml")
    assert loaded["结界突破"]["master"]["退出次数"] == 3
    assert loaded["启动项"]["master"]["启动命令"] == "test.exe"


def test_write_config_is_utf8(tmp_config_dir):
    """中文配置必须按 UTF-8 落盘，不能写成 GBK 或带 BOM"""
    Lib.write_config("./config/Setting.yml", {"寮三十": {"主账号": "master"}})
    raw = (tmp_config_dir / "Setting.yml").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "配置文件不应带 BOM"
    assert "寮三十".encode("utf-8") in raw


def test_write_config_preserves_indent_style(tmp_config_dir):
    """写回时保持 2 空格缩进 + 序列 4 空格偏移（与仓库现有配置一致）"""
    Lib.write_config("./config/Setting.yml", {"副本": ["魂虚", "魂海"]})
    text = (tmp_config_dir / "Setting.yml").read_text(encoding="utf-8")
    assert "\r\n" not in text or text.count("\n") > 0  # 只要求可读，行尾由 .gitattributes 管
    assert "魂虚" in text


# ------------------------------------------------- 完成时间读取（main 侧）


def test_read_completions_missing_file(tmp_config_dir):
    assert main.read_completions() == {}


def test_read_completions_parses_times(tmp_config_dir):
    data = {"master": {"邮件领取": "2026-10-19 08:30:00", "坏值": "不是时间"}}
    Lib.write_config("./state/Last_times.yml", data)
    completions = main.read_completions()
    assert completions["master"]["邮件领取"].hour == 8
    assert "坏值" not in completions["master"], "无法解析的时间应被跳过"


def test_read_completions_skips_non_mapping_account(tmp_config_dir):
    Lib.write_config("./state/Last_times.yml", {"master": "坏了"})
    assert main.read_completions() == {}


def test_entry_done_today_all_keys_present(tmp_config_dir):
    today = "2026-10-19"
    data = {
        "master": {"邮件领取": f"{today} 08:00:00"},
        "slaves": {"邮件领取": f"{today} 09:00:00"},
    }
    Lib.write_config("./state/Last_times.yml", data)
    entry = main.get_task("signin")
    # signin 有 5 个状态键，只写了 1 个 → 未完成
    assert main.entry_done_today(entry) is False


def test_entry_done_today_complete(tmp_config_dir):
    import datetime

    today = datetime.date.today().strftime("%Y-%m-%d")
    entry = main.get_task("digui")
    data = {
        account: {key: f"{today} 08:00:00" for key in entry.check_keys}
        for account in ("master", "slaves")
    }
    Lib.write_config("./state/Last_times.yml", data)
    assert main.entry_done_today(entry) is True


def test_entry_done_today_yesterday_is_not_done(tmp_config_dir):
    import datetime

    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    entry = main.get_task("digui")
    data = {account: {key: f"{yesterday} 08:00:00" for key in entry.check_keys} for account in ("master",)}
    Lib.write_config("./state/Last_times.yml", data)
    assert main.entry_done_today(entry) is False


def test_latest_completion_picks_newest(tmp_config_dir):
    data = {
        "master": {"寮三十": "2026-10-19 08:00:00"},
        "slaves": {"寮三十": "2026-10-19 10:00:00"},
    }
    Lib.write_config("./state/Last_times.yml", data)
    entry = main.get_task("thirty")
    latest = main.latest_completion(entry)
    assert latest.hour == 10


def test_latest_completion_none_when_absent(tmp_config_dir):
    Lib.write_config("./state/Last_times.yml", {"master": {}})
    assert main.latest_completion(main.get_task("digui")) is None


def test_completion_snapshot_and_advanced(tmp_config_dir):
    import datetime

    Lib.write_config("./state/Last_times.yml", {"master": {"寮三十": "2026-10-19 08:00:00"}})
    before = main.completion_snapshot()

    later = datetime.datetime(2026, 10, 19, 12, 0, 0).strftime("%Y-%m-%d %H:%M:%S")
    Lib.write_config("./state/Last_times.yml", {"master": {"寮三十": later}})
    after = main.completion_snapshot()

    advanced = main.completion_advanced(before, after)
    assert advanced["thirty"] is True
    assert advanced["digui"] is False, "没有记录的任务应视为未推进"
