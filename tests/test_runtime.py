# -*- coding: utf-8 -*-
"""运行期开关模块 runtime.py 的约定与中断链路。

PR7 把项目级开关模块从 `config.py` 改名为 `runtime.py`。原因是命名阴影：

    config.py        <- 模块
    config/          <- 目录（放 Setting.yml）

`import config` 的解析依赖「config/ 里没有 __init__.py」这一隐含前提。
一旦有人往 config/ 加个 __init__.py（或放个 config/config.py），
`import config` 就会变成包导入，`stop_thread` 静默失效——中断按钮点了没反应，
而且不报任何错。改名后彻底消除。

本文件守住三件事：
1. runtime.py 能被导入且提供 stop_thread；
2. Lib.stop_requested() 会消费 runtime.stop_thread；
3. 代码里不再出现 `import config`（避免阴影问题复现）。
"""

import ast
import importlib
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import Lib
import paths  # noqa: E402


# --------------------------------------------------------- 模块本身


def test_runtime_module_exists_and_has_stop_thread():
    module = importlib.import_module("runtime")
    assert hasattr(module, "stop_thread")
    assert isinstance(module.stop_thread, bool)


def test_config_module_is_not_shadowed_by_config_dir():
    """config/ 目录存在，但不能因此让 `config` 变成包（这正是改名的原因）"""
    config_dir = os.path.join(PROJECT_ROOT, "config")
    if os.path.isdir(config_dir):
        assert not os.path.exists(os.path.join(config_dir, "__init__.py")), (
            "config/ 里出现 __init__.py 会让 `import config` 变成包导入，"
            "与 runtime.py 的旧名字冲突"
        )


# --------------------------------------------------- 中断链路消费开关


def test_stop_requested_consumes_runtime_flag():
    """runtime.stop_thread = True 必须被 stop_requested() 识别"""
    runtime = importlib.import_module("runtime")
    original = runtime.stop_thread
    try:
        Lib.reset_stop()
        runtime.stop_thread = True
        assert Lib.stop_requested() is True

        runtime.stop_thread = False
        Lib.reset_stop()
        assert Lib.stop_requested() is False
    finally:
        runtime.stop_thread = original
        Lib.reset_stop()


def test_stop_requested_works_without_runtime_module(monkeypatch):
    """runtime 缺失时按「未请求」处理，不能抛异常"""
    Lib.reset_stop()
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def fake_import(name, *args, **kwargs):
        if name == "runtime":
            raise ImportError("模拟缺失")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    assert Lib.stop_requested() is False


# ------------------------------------------------- 源码里不应再有旧引用


def iter_source_files():
    """项目内所有 .py（跳过环境目录、收容所与本地调试脚本）

    dev/ 里是个人调试脚本（不入库），不参与这条约定检查。
    """
    skip = {".venv", ".git", "__pycache__", ".dsh-scratch", "build", "dist", "logs", "config", "state", "dev"}
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(root, name)


def test_no_module_imports_legacy_config():
    """不允许再出现 `import config` / `from config import ...`"""
    offenders = []
    for path in iter_source_files():
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if "config" in names:
                rel = os.path.relpath(path, PROJECT_ROOT)
                offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, f"仍有模块导入 config（应为 runtime）: {offenders}"


def test_gui_entry_does_not_import_legacy_config():
    source = open(os.path.join(PROJECT_ROOT, "GUI.py"), encoding="utf-8").read()
    assert "import config" not in source


def test_window_imports_runtime():
    source = open(os.path.join(PROJECT_ROOT, "ui", "window.py"), encoding="utf-8").read()
    assert "import runtime" in source
    assert "runtime.stop_thread" in source
    assert "import config" not in source


# ---------------------------------------------------- 打包脚本同步改名


def test_build_script_generates_runtime_py():
    source = open(os.path.join(PROJECT_ROOT, "build_exe.py"), encoding="utf-8").read()
    assert 'RUNTIME_PY = "runtime.py"' in source
    assert "def ensure_runtime_py" in source
    assert "stop_thread = False" in source


def test_build_script_warns_about_legacy_config():
    """旧 config.py 存在时要提示用户改名，而不是默默忽略"""
    source = open(os.path.join(PROJECT_ROOT, "build_exe.py"), encoding="utf-8").read()
    assert "LEGACY_CONFIG_PY" in source
    assert "请改名或删除" in source
