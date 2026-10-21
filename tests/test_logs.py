# -*- coding: utf-8 -*-
"""日志目录结构与清理工具的测试。

覆盖 PR6 改动的两处：
1. main._log_stream 的日志目录改为 logs/<YYYY-MM>/<YYYY-MM-DD>/；
2. tools/clean_logs.py 的按月/按天清理计划（只碰形如 YYYY-MM / YYYY-MM-DD 的目录）。
"""

import datetime
import importlib.util
import os
import sys

import pytest

import main

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(PROJECT_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import clean_logs  # noqa: E402


# ------------------------------------------------------- 日志目录分层


def test_log_stream_uses_year_month_day_dirs(tmp_path, monkeypatch):
    """日志应落在 logs/<YYYY-MM>/<YYYY-MM-DD>/ 下，而不是直接 logs/<YYYY-MM-DD>/"""
    monkeypatch.chdir(tmp_path)

    with main._log_stream(None, "console_output") as log_path:
        print("hello")

    today = datetime.date.today()
    expected_dir = os.path.join(
        "logs", today.strftime("%Y-%m"), today.strftime("%Y-%m-%d")
    )
    assert os.path.dirname(log_path) == expected_dir
    assert os.path.exists(log_path)


def test_log_stream_creates_nested_dirs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with main._log_stream(None, "single_digui") as log_path:
        print("x")
    assert os.path.isdir(os.path.dirname(log_path))


def test_log_stream_filename_contains_prefix_and_timestamp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with main._log_stream(None, "console_output") as log_path:
        print("x")
    name = os.path.basename(log_path)
    assert name.startswith("console_output_")
    assert name.endswith(".log")
    # 形如 console_output_2026-10-21_21-30-00.log
    assert name.count("_") >= 3


def test_log_stream_writes_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with main._log_stream(None, "console_output") as log_path:
        print("TASK- ----- 测试输出")
    content = open(log_path, encoding="utf-8").read()
    assert "TASK- ----- 测试输出" in content


def test_log_stream_restores_stdout_on_error(tmp_path, monkeypatch):
    """任务抛异常时也必须恢复 sys.stdout，否则后续 print 会写进已关闭的文件"""
    monkeypatch.chdir(tmp_path)
    original = sys.stdout

    with pytest.raises(RuntimeError):
        with main._log_stream(None, "console_output"):
            raise RuntimeError("boom")

    assert sys.stdout is original


# --------------------------------------------------------- 清理工具


@pytest.fixture()
def fake_logs(tmp_path):
    """造一个假 logs/ 目录：8 个月份 + 1 个非月份目录 + app_crash.log"""
    logs = tmp_path / "logs"
    logs.mkdir()
    for month in ("2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"):
        day_dir = logs / month / "2026-10-21"
        day_dir.mkdir(parents=True)
        (day_dir / "x.log").write_text("log", encoding="utf-8")
    (logs / "not-a-month").mkdir()
    (logs / "app_crash.log").write_text("crash", encoding="utf-8")
    return logs


def test_iter_month_dirs_sorted_and_filtered(fake_logs, monkeypatch):
    monkeypatch.setattr(clean_logs, "LOGS_DIR", str(fake_logs))
    names = [name for name, _path in clean_logs.iter_month_dirs()]
    assert names == ["2026-03", "2026-04", "2026-05", "2026-06",
                     "2026-07", "2026-08", "2026-09", "2026-10"]
    assert "not-a-month" not in names, "非 YYYY-MM 目录不应被当作月份"


def test_plan_month_cleanup_keeps_recent(fake_logs, monkeypatch):
    monkeypatch.setattr(clean_logs, "LOGS_DIR", str(fake_logs))
    to_delete, kept = clean_logs.plan_month_cleanup(6)
    assert [os.path.basename(p) for p in to_delete] == ["2026-03", "2026-04"]
    assert [name for name, _p in kept] == [
        "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"
    ]


def test_plan_month_cleanup_keep_more_than_exist(fake_logs, monkeypatch):
    monkeypatch.setattr(clean_logs, "LOGS_DIR", str(fake_logs))
    to_delete, kept = clean_logs.plan_month_cleanup(99)
    assert to_delete == []
    assert len(kept) == 8


def test_plan_month_cleanup_keep_zero_deletes_all(fake_logs, monkeypatch):
    monkeypatch.setattr(clean_logs, "LOGS_DIR", str(fake_logs))
    to_delete, kept = clean_logs.plan_month_cleanup(0)
    assert len(to_delete) == 8
    assert kept == []


def test_plan_day_cleanup_removes_old_days(fake_logs, monkeypatch):
    monkeypatch.setattr(clean_logs, "LOGS_DIR", str(fake_logs))
    month_dir = fake_logs / "2026-10"
    old_day = month_dir / "2020-01-01"
    old_day.mkdir()
    _to_delete, kept = clean_logs.plan_month_cleanup(6)

    stale = clean_logs.plan_day_cleanup(kept, 30)
    names = [os.path.basename(p) for p in stale]
    assert "2020-01-01" in names
    assert "2026-10-21" not in names, "最近日期不应被删"


def test_plan_day_cleanup_disabled_by_zero(fake_logs, monkeypatch):
    monkeypatch.setattr(clean_logs, "LOGS_DIR", str(fake_logs))
    _to_delete, kept = clean_logs.plan_month_cleanup(6)
    assert clean_logs.plan_day_cleanup(kept, 0) == []


def test_missing_logs_dir_is_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(clean_logs, "LOGS_DIR", str(tmp_path / "不存在"))
    assert clean_logs.iter_month_dirs() == []
    to_delete, kept = clean_logs.plan_month_cleanup(6)
    assert to_delete == [] and kept == []


def test_dir_size_and_human_size(fake_logs):
    size = clean_logs.dir_size(str(fake_logs / "2026-03"))
    assert size > 0
    assert "B" in clean_logs.human_size(size)
