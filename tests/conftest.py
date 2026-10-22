# -*- coding: utf-8 -*-
"""pytest 公共夹具与路径设置。

项目源码直接放在仓库根目录（不是可安装的包），因此这里把根目录加入 sys.path，
让 tests/ 下的用例可以 `import main` / `import Lib`。
"""

import os
import sys

import pytest

# 仓库根目录：tests/ 的上一级
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture()
def project_root():
    """仓库根目录的绝对路径"""
    return PROJECT_ROOT


@pytest.fixture()
def tmp_config_dir(tmp_path, monkeypatch):
    """把工作目录切到临时目录，避免用例碰到真实的 config/ 与 state/

    用例里所有相对路径（./config/xxx、./state/xxx）都会落到 tmp_path 下。
    两个目录都建好：config/ 放静态配置，state/ 放程序读写的状态文件。
    """
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    return config_dir


@pytest.fixture()
def tmp_state_dir(tmp_config_dir, tmp_path):
    """在 tmp_config_dir 基础上，额外返回 state/ 目录（需要同时造两份文件时用）"""
    return tmp_path / "state"
