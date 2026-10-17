# -*- coding: utf-8 -*-
"""build_exe.py —— 使用 PyInstaller 把 GUI.py 打包为单文件 GUI.exe

产物直接输出到项目根目录（不经过 dist/），与 pic/、config/ 同级，打包完即可运行。

用法（在任意目录执行均可，脚本会自动切到项目根目录）：
    python build_exe.py            # 打包，产物输出到项目根目录 GUI.exe
    python build_exe.py --fresh    # 先删除 build/ 与残留 dist/，做全新构建

说明：
- 打包配置来自项目根目录的 GUI.spec（onefile、无控制台窗口），通过 --distpath 指定输出位置。
- pic/ 与 config/ 属于运行期外部资源，不打进 exe；exe 需要和它们放在同一目录下运行。
- GUI.py 会 import config，因此打包前若缺少 config.py 会自动生成最小版本（stop_thread = False）。
- 若根目录 GUI.exe 正在运行会被系统锁定，脚本会在打包前直接报错提示，避免打包到一半失败。
"""

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time

# 项目根目录（本脚本所在目录），也是 exe 的最终输出位置
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SPEC_FILE = "GUI.spec"  # PyInstaller 打包配置
ENTRY_FILE = "GUI.py"  # 打包入口
APP_NAME = "GUI"  # 产物名，与 GUI.spec 中的 name 保持一致
MIN_PYTHON = (3, 11)  # 项目要求 Python 3.11+
CONFIG_PY = "config.py"

# 缺少 config.py 时自动生成的最小内容（GUI.py 只依赖 stop_thread）
DEFAULT_CONFIG_PY = '''# -*- coding: utf-8 -*-
"""项目级运行时开关（由 build_exe.py 自动生成的最小内容）。

GUI.py 通过 config.stop_thread 控制任务线程，后续需要额外开关时在此文件追加。
"""

stop_thread = False
'''


def log(message):
    """统一格式的构建日志"""
    print(f"BUILD- {message}", flush=True)


def fail(message):
    """打印错误并退出"""
    print(f"BUILD- 失败: {message}", flush=True)
    sys.exit(1)


def target_exe():
    """打包产物路径：项目根目录下的 GUI.exe"""
    return os.path.join(PROJECT_ROOT, f"{APP_NAME}.exe")


def check_environment():
    """检查 Python 版本、平台与 PyInstaller 是否可用"""
    log("STEP 1/4 检查构建环境")

    if os.name != "nt":
        fail("本项目依赖 Win32 窗口控制，只能在 Windows 上打包")

    if sys.version_info[:2] < MIN_PYTHON:
        fail(
            f"需要 Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+，"
            f"当前为 {sys.version_info.major}.{sys.version_info.minor}"
        )

    for name in (SPEC_FILE, ENTRY_FILE):
        if not os.path.exists(os.path.join(PROJECT_ROOT, name)):
            fail(f"缺少 {name}，请确认脚本位于项目根目录")

    if importlib.util.find_spec("PyInstaller") is None:
        fail("未安装 PyInstaller，请先执行: pip install -r requirements.txt")

    if os.path.basename(sys.executable).lower() == "pythonw.exe":
        log("提示: 当前用 pythonw.exe 运行，构建输出不可见，建议改用 python.exe")

    log(f"INFO- Python {sys.version.split()[0]} | {sys.executable}")


def ensure_config_py():
    """确保存在 config.py：缺失时生成最小版本，否则打包出的 exe 启动即报 ModuleNotFoundError"""
    log("STEP 2/4 检查本地运行时配置 config.py")
    config_path = os.path.join(PROJECT_ROOT, CONFIG_PY)
    if os.path.exists(config_path):
        log(f"INFO- 已存在 {CONFIG_PY}，保持不变")
        return

    with open(config_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(DEFAULT_CONFIG_PY)
    log(f"INFO- 未找到 {CONFIG_PY}，已自动生成最小版本（stop_thread = False）")

    for directory in ("pic", "config"):
        if not os.path.isdir(os.path.join(PROJECT_ROOT, directory)):
            log(f"WAIT- 缺少 {directory}/ 目录：exe 运行时需要与它同目录，请自行准备")


def check_target_writable():
    """输出位置预检：已存在的 GUI.exe 若正在运行会被锁定，提前报错而不是等打包到最后才失败"""
    exe_path = target_exe()
    if not os.path.exists(exe_path):
        return

    try:
        with open(exe_path, "r+b"):
            pass
    except PermissionError:
        fail(
            f"根目录 {APP_NAME}.exe 正被占用（可能程序还在运行），请先关闭它再重新打包。\n"
            f"       目标文件: {exe_path}"
        )
    except OSError as error:
        fail(f"无法写入目标文件 {exe_path}: {error}")

    log(f"INFO- 输出位置可用: {exe_path}")


def clean_outputs():
    """可选：删除 build/ 与历史遗留的 dist/，保证全新构建"""
    for name in ("build", "dist"):
        path = os.path.join(PROJECT_ROOT, name)
        if os.path.isdir(path):
            log(f"INFO- 删除旧目录 {name}/")
            shutil.rmtree(path, ignore_errors=True)


def run_pyinstaller():
    """调用 PyInstaller 依据 GUI.spec 打包，产物直接写入项目根目录"""
    log("STEP 3/4 调用 PyInstaller 打包（首次构建耗时较长，请耐心等待）")
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",              # 覆盖旧产物时不询问
        "--clean",                  # 清理 PyInstaller 缓存，避免旧依赖残留
        "--distpath",
        PROJECT_ROOT,               # 关键：产物输出目录改为项目根目录
        SPEC_FILE,
    ]
    log("INFO- " + " ".join(command))

    started = time.time()
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    elapsed = time.time() - started

    if result.returncode != 0:
        fail(f"PyInstaller 返回码 {result.returncode}，打包失败；请查看上方日志")
    log(f"INFO- 打包完成，耗时 {elapsed:.1f} 秒")


def report():
    """校验产物并输出提示"""
    log("STEP 4/4 构建结束")
    exe_path = target_exe()
    if not os.path.exists(exe_path):
        fail(f"未找到打包产物 {exe_path}")

    size_mb = os.path.getsize(exe_path) / 1024 / 1024
    log(f"INFO- 产物: {exe_path}（{size_mb:.1f} MB）")
    log("INFO- exe 已与 pic/、config/ 同级，可直接在本目录运行")


def main():
    parser = argparse.ArgumentParser(description="打包 Paper Sweeper 为单文件 GUI.exe（输出到项目根目录）")
    parser.add_argument("--fresh", action="store_true", help="先删除 build/ 与残留 dist/，做全新构建")
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)

    try:
        check_environment()
        ensure_config_py()
        check_target_writable()
        if args.fresh:
            clean_outputs()
        run_pyinstaller()
        report()
    except KeyboardInterrupt:
        print("BUILD- 已取消", flush=True)
        sys.exit(130)


if __name__ == "__main__":
    main()
