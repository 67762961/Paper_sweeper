# -*- coding: utf-8 -*-
"""TASK_REGISTRY 注册表一致性。

左侧 7 行任务与「完整运行」顺序都由 main.TASK_REGISTRY 驱动，
注册表出错会同时影响界面、冷却键与今日状态判定，因此单独守住几条不变量：
1. key 唯一（界面用它做任务标识与配置键）
2. entry 可调用（能被 GUI 线程直接调用）
3. lasttime_keys 非空且为字符串元组（Last_times.yml 的键）
4. today_keys 为空或为 lasttime_keys 的子集（今日判定不能看别的任务的键）
5. 每个任务在默认开关下都参与完整运行（新任务忘记登记会在这里暴露）
"""

import pytest

import main


def test_registry_not_empty():
    assert len(main.TASK_REGISTRY) == 7, "左侧固定 7 行任务，增删任务需同步界面"


def test_keys_unique():
    keys = [task.key for task in main.TASK_REGISTRY]
    assert len(keys) == len(set(keys)), f"任务 key 重复: {keys}"


def test_titles_and_descs_filled():
    for task in main.TASK_REGISTRY:
        assert task.title.strip(), f"{task.key} 缺少标题"
        assert task.desc.strip(), f"{task.key} 缺少说明"


def test_entry_callable():
    for task in main.TASK_REGISTRY:
        assert callable(task.entry), f"{task.key} 的入口不可调用"


def test_lasttime_keys_valid():
    for task in main.TASK_REGISTRY:
        assert isinstance(task.lasttime_keys, tuple), f"{task.key} 的 lasttime_keys 应为 tuple"
        assert task.lasttime_keys, f"{task.key} 缺少 lasttime_keys"
        for key in task.lasttime_keys:
            assert isinstance(key, str) and key.strip(), f"{task.key} 的状态键非法: {key!r}"


def test_today_keys_subset_of_lasttime_keys():
    for task in main.TASK_REGISTRY:
        if not task.today_keys:
            continue
        extra = set(task.today_keys) - set(task.lasttime_keys)
        assert not extra, f"{task.key} 的 today_keys 含 lasttime_keys 之外的键: {extra}"


def test_check_keys_falls_back_to_lasttime_keys():
    for task in main.TASK_REGISTRY:
        expected = task.today_keys or task.lasttime_keys
        assert task.check_keys == expected, f"{task.key} 的 check_keys 回落逻辑不对"


def test_thirty_only_checks_liao_thirty_today():
    """寮三十 / 真蛇：真蛇是周更，不参与今日判定，只看寮三十"""
    task = main.get_task("thirty")
    assert task is not None
    assert "真蛇" in task.lasttime_keys
    assert task.check_keys == ("寮三十",)


def test_label_format():
    for task in main.TASK_REGISTRY:
        assert task.label == f"{task.key}({task.title})"


def test_get_task_known_and_unknown():
    for task in main.TASK_REGISTRY:
        assert main.get_task(task.key) is task
    assert main.get_task("不存在的任务") is None


def test_all_tasks_enabled_by_default(tmp_config_dir):
    """config/Gui_state.yml 缺失时默认全开"""
    switches = main.read_task_switches()
    assert set(switches) == {task.key for task in main.TASK_REGISTRY}
    assert all(switches.values()), "缺失配置时应默认全部开启"

    enabled = main.enabled_task_keys()
    assert enabled == [task.key for task in main.TASK_REGISTRY], "默认顺序应与注册表一致"


def test_enabled_task_keys_respects_switches():
    keys = [task.key for task in main.TASK_REGISTRY]
    switches = {key: (index % 2 == 0) for index, key in enumerate(keys)}
    enabled = main.enabled_task_keys(switches)
    assert enabled == [key for key in keys if switches[key]]


def test_is_task_enabled_default_true():
    assert main.is_task_enabled("不存在的任务", {}) is True


@pytest.mark.parametrize("key", [task.key for task in main.TASK_REGISTRY])
def test_each_registry_entry_lookup(key):
    task = main.get_task(key)
    assert task is not None and task.key == key
