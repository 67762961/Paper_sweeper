# -*- coding: utf-8 -*-
"""界面偏好读写（state/gui.json）。

只保存界面相关选项，与任务参数（config/Setting.yml）、任务开关（state/Gui_state.yml）隔离。
文件缺失或内容非法时回落到默认值，不阻塞界面启动。
"""

import json
import logging
import os

import paths

PREFS_PATH = paths.PREFS

DEFAULT_PREFS = {
    "theme": "light",                    # light / dark / auto
    "log_auto_scroll": True,             # 日志自动滚动到底部
    "log_font_size": 12,                 # 日志字号（pt）
    # 完整运行成功结束后的动作；只对「完整运行」生效，单跑与中断都不触发
    "after_run_close_emulator": False,   # 关闭受控模拟器窗口
    "after_run_sleep": False,            # 是否启用结束后的电源动作
    "after_run_power": "sleep",          # 启用时执行哪个：logoff / sleep / shutdown
}

VALID_THEMES = ("light", "dark", "auto")
VALID_LOG_SIZES = (11, 12, 13, 14)
# 电源动作的合法取值；「不执行」由 after_run_sleep 开关表达，不在这里
VALID_POWER_ACTIONS = ("logoff", "sleep", "shutdown")

# 布尔类偏好：统一按「是 bool 才采纳，否则回落默认」处理
BOOL_PREF_KEYS = ("log_auto_scroll", "after_run_close_emulator", "after_run_sleep")


def load_prefs(path=None):
    """读取界面偏好；缺失或非法字段回落到默认值"""
    path = path or PREFS_PATH
    data = {}
    try:
        # 首次读取时把旧布局 config/gui.json 迁到 state/ 下
        if path == PREFS_PATH:
            paths.ensure_state_dir()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                data = loaded
    except Exception as error:
        logging.warning("读取界面偏好失败，使用默认值: %s", error)

    prefs = dict(DEFAULT_PREFS)
    if data.get("theme") in VALID_THEMES:
        prefs["theme"] = data["theme"]
    for key in BOOL_PREF_KEYS:
        # 只认真正的布尔值：字符串 "false"、数字 0 都回落默认，
        # 避免手改 gui.json 时写出 "false" 被当成真值
        if isinstance(data.get(key), bool):
            prefs[key] = data[key]
    if data.get("after_run_power") in VALID_POWER_ACTIONS:
        prefs["after_run_power"] = data["after_run_power"]
    try:
        size = int(data.get("log_font_size", DEFAULT_PREFS["log_font_size"]))
        if size in VALID_LOG_SIZES:
            prefs["log_font_size"] = size
    except (TypeError, ValueError):
        pass
    return prefs


def save_prefs(prefs, path=None):
    """保存界面偏好；返回是否写盘成功"""
    path = path or PREFS_PATH
    merged = dict(DEFAULT_PREFS)
    merged.update({key: prefs[key] for key in DEFAULT_PREFS if key in prefs})
    try:
        # 首次保存时把旧布局 config/gui.json 迁到 state/ 下
        if path == PREFS_PATH:
            paths.ensure_state_dir()
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temp_path = f"{path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(merged, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_path, path)
        return True
    except Exception as error:
        logging.warning("保存界面偏好失败: %s", error)
        return False
