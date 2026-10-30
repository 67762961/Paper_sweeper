# -*- coding: utf-8 -*-
"""「关闭模拟器」能力的纯逻辑用例（不碰真实窗口、不真的关模拟器）。

守住四件事：
1. 受控账号只来自 Setting.yml 的 启动项，不多关用户手动开的窗口；
2. 实例号能从启动命令里解析出来，解析不了不崩；
3. MuMuManager 路径**从启动命令推导**，不写死任何安装路径；
4. 找不到 MuMuManager 时降级为关窗口，功能不失效。
"""

import os

import pytest

import Lib
import paths


# ------------------------------------------------------------ 受控账号


def test_controlled_accounts_只取启动项里登记的账号(tmp_config_dir):
    Lib.write_config(
        paths.SETTING,
        {"启动项": {"master": {"启动命令": "a.exe -v 0"}, "slaves": {"启动命令": "b.exe -v 1"}}},
    )

    assert Lib.controlled_accounts() == ["master", "slaves"]


def test_controlled_accounts_没有启动项时返回空列表(tmp_config_dir):
    Lib.write_config(paths.SETTING, {"结界突破": {"master": {"退出次数": 3}}})

    assert Lib.controlled_accounts() == []


def test_controlled_accounts_文件缺失时返回空列表(tmp_config_dir):
    """Setting.yml 不存在时不能抛异常，GUI 要能正常启动"""
    assert Lib.controlled_accounts() == []


def test_controlled_accounts_启动项格式异常时返回空列表(tmp_config_dir):
    Lib.write_config(paths.SETTING, {"启动项": "这不是字典"})

    assert Lib.controlled_accounts() == []


def test_launch_commands_跳过缺少启动命令的账号(tmp_config_dir):
    Lib.write_config(
        paths.SETTING,
        {"启动项": {"master": {"启动命令": "a.exe -v 0"}, "broken": {"其它键": 1}}},
    )

    commands = Lib._launch_commands()

    assert list(commands) == ["master"]
    assert commands["master"] == "a.exe -v 0"


# ------------------------------------------------------------ 实例号解析


@pytest.mark.parametrize(
    "command, expected",
    [
        ("G:/MuMu/nx_main/MuMuNxMain.exe -p com.netease -v 0", "0"),
        ("G:/MuMu/nx_main/MuMuNxMain.exe -p com.netease -v 1", "1"),
        ("MuMuNxMain.exe -v 12", "12"),
        ("MuMuNxMain.exe  -v   3", "3"),
        ("MuMuNxMain.exe -p com.netease", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_instance_number(command, expected):
    assert Lib.parse_instance_number(command) == expected


# ------------------------------------------------------------ 路径推导


def test_launch_exe_dir_从启动命令取目录():
    command = 'G:/GAMES/Platform/MuMuPlayer/nx_main/MuMuNxMain.exe -p com.netease -v 0'

    directory = Lib._launch_exe_dir(command)

    assert directory is not None
    assert directory.replace("\\", "/").endswith("MuMuPlayer/nx_main")


def test_launch_exe_dir_带引号的路径也能解析():
    command = '"D:/Emu/MuMu/MuMuNxMain.exe" -p com.netease -v 0'

    directory = Lib._launch_exe_dir(command)

    assert directory is not None
    assert directory.replace("\\", "/").endswith("Emu/MuMu")


def test_launch_exe_dir_没有exe时返回None():
    assert Lib._launch_exe_dir("start notepad") is None
    assert Lib._launch_exe_dir("") is None


def test_find_mumu_manager_优先用同目录的候选(tmp_path, tmp_config_dir):
    """同 MuMuNxMain.exe 一个目录是首选——这也是实际安装的布局"""
    nx_dir = tmp_path / "nx_main"
    nx_dir.mkdir()
    manager = nx_dir / "MuMuManager.exe"
    manager.write_bytes(b"")
    command = f'"{nx_dir / "MuMuNxMain.exe"}" -p com.netease -v 0'

    found = Lib.find_mumu_manager(command)

    assert found == str(manager)


def test_find_mumu_manager_同目录没有时回退到上一级(tmp_path, tmp_config_dir):
    nx_dir = tmp_path / "nx_main"
    nx_dir.mkdir()
    manager = tmp_path / "MuMuManager.exe"
    manager.write_bytes(b"")
    command = f'"{nx_dir / "MuMuNxMain.exe"}" -p com.netease -v 0'

    assert Lib.find_mumu_manager(command) == str(manager)


def test_find_mumu_manager_再回退到shell子目录(tmp_path, tmp_config_dir):
    nx_dir = tmp_path / "nx_main"
    nx_dir.mkdir()
    shell_dir = tmp_path / "shell"
    shell_dir.mkdir()
    manager = shell_dir / "MuMuManager.exe"
    manager.write_bytes(b"")
    command = f'"{nx_dir / "MuMuNxMain.exe"}" -p com.netease -v 0'

    assert Lib.find_mumu_manager(command) == str(manager)


def test_find_mumu_manager_都不存在时返回None(tmp_path, tmp_config_dir):
    """找不到就必须返回 None，调用方据此降级——绝不能抛异常"""
    nx_dir = tmp_path / "nx_main"
    nx_dir.mkdir()
    command = f'"{nx_dir / "MuMuNxMain.exe"}" -p com.netease -v 0'

    assert Lib.find_mumu_manager(command) is None


def test_find_mumu_manager_支持配置里显式指定(tmp_path, tmp_config_dir):
    """Setting.yml 的 模拟器.MuMuManager 是逃生口，优先级最高"""
    nx_dir = tmp_path / "nx_main"
    nx_dir.mkdir()
    auto = nx_dir / "MuMuManager.exe"
    auto.write_bytes(b"")
    manual = tmp_path / "别处的MuMuManager.exe"
    manual.write_bytes(b"")
    Lib.write_config(
        paths.SETTING,
        {
            "启动项": {"master": {"启动命令": f'"{nx_dir / "MuMuNxMain.exe"}" -v 0'}},
            "模拟器": {"MuMuManager": str(manual)},
        },
    )

    assert Lib.find_mumu_manager(f'"{nx_dir / "MuMuNxMain.exe"}" -v 0') == str(manual)


def test_find_mumu_manager_显式指定但文件不存在时回落推导(tmp_path, tmp_config_dir):
    nx_dir = tmp_path / "nx_main"
    nx_dir.mkdir()
    auto = nx_dir / "MuMuManager.exe"
    auto.write_bytes(b"")
    Lib.write_config(
        paths.SETTING,
        {
            "启动项": {"master": {"启动命令": f'"{nx_dir / "MuMuNxMain.exe"}" -v 0'}},
            "模拟器": {"MuMuManager": str(tmp_path / "不存在.exe")},
        },
    )

    assert Lib.find_mumu_manager(f'"{nx_dir / "MuMuNxMain.exe"}" -v 0') == str(auto)


def test_没有硬编码MuMu安装路径():
    """回归保护：源码里不允许出现写死的 MuMu 安装路径"""
    source = open("Lib.py", "r", encoding="utf-8").read()

    assert "MuMuPlayer/nx_main" not in source
    assert "MuMuPlayer\\nx_main" not in source
    assert "G:/GAMES" not in source
    assert "G:\\GAMES" not in source


# ------------------------------------------------------------ 关机命令降级


def test_shutdown_via_manager_第一种写法成功就不试第二种(monkeypatch):
    calls = []

    def fake_run(manager_path, args, timeout=15):
        calls.append(args)
        return True

    monkeypatch.setattr(Lib, "_run_manager", fake_run)

    assert Lib.shutdown_via_manager("MuMuManager.exe", ["0", "1"]) is True
    assert calls == [["control", "-v", "0,1", "shutdown"]]


def test_shutdown_via_manager_第一种失败会试第二种(monkeypatch):
    calls = []

    def fake_run(manager_path, args, timeout=15):
        calls.append(args)
        return args[1] == "shutdown"

    monkeypatch.setattr(Lib, "_run_manager", fake_run)

    assert Lib.shutdown_via_manager("MuMuManager.exe", ["0"]) is True
    assert calls == [
        ["control", "-v", "0", "shutdown"],
        ["control", "shutdown", "-v", "0"],
    ]


def test_shutdown_via_manager_两种都失败返回False(monkeypatch):
    monkeypatch.setattr(Lib, "_run_manager", lambda *a, **k: False)

    assert Lib.shutdown_via_manager("MuMuManager.exe", ["0"]) is False


def test_run_manager_errcode非0视为失败(monkeypatch):
    class FakeCompleted:
        returncode = 0
        stdout = b'{"errcode": 1, "errmsg": "boom"}'

    monkeypatch.setattr(Lib.subprocess, "run", lambda *a, **k: FakeCompleted())

    assert Lib._run_manager("MuMuManager.exe", ["control", "-v", "0", "shutdown"]) is False


def test_run_manager_errcode为0视为成功(monkeypatch):
    class FakeCompleted:
        returncode = 0
        stdout = b'{"errcode": 0, "errmsg": ""}'

    monkeypatch.setattr(Lib.subprocess, "run", lambda *a, **k: FakeCompleted())

    assert Lib._run_manager("MuMuManager.exe", ["control", "-v", "0", "shutdown"]) is True


def test_run_manager_进程起不来时返回False(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("找不到文件")

    monkeypatch.setattr(Lib.subprocess, "run", boom)

    assert Lib._run_manager("不存在的.exe", ["control"]) is False


# ------------------------------------------------------------ 关闭流程


def test_close_emulators_一个都没开时只报missing(monkeypatch, tmp_config_dir):
    Lib.write_config(
        paths.SETTING,
        {"启动项": {"master": {"启动命令": "a.exe -v 0"}, "slaves": {"启动命令": "b.exe -v 1"}}},
    )
    monkeypatch.setattr(Lib, "find_windows_silent", lambda account: None)

    result = Lib.close_emulators()

    assert result["closed"] == []
    assert result["missing"] == ["master", "slaves"]
    assert result["stuck"] == []


def test_close_emulators_没有受控账号时不做事(monkeypatch, tmp_config_dir):
    Lib.write_config(paths.SETTING, {})
    monkeypatch.setattr(
        Lib, "find_windows_silent", lambda account: pytest.fail("不该枚举窗口")
    )

    result = Lib.close_emulators()

    assert result == {"closed": [], "missing": [], "stuck": []}


def test_close_emulators_窗口被关掉后记为closed(monkeypatch, tmp_config_dir):
    Lib.write_config(paths.SETTING, {"启动项": {"master": {"启动命令": "a.exe -v 0"}}})

    # 调用顺序：①关闭前枚举（在跑）→ ②发 WM_CLOSE 前枚举（还在）→ ③复查（已关）
    state = {"calls": 0}

    def fake_find(account):
        state["calls"] += 1
        return 1234 if state["calls"] <= 2 else None

    monkeypatch.setattr(Lib, "find_windows_silent", fake_find)
    monkeypatch.setattr(Lib, "find_mumu_manager", lambda *a, **k: None)
    monkeypatch.setattr(Lib.win32gui, "PostMessage", lambda *a: None)

    result = Lib.close_emulators(wait_seconds=0)

    assert result["closed"] == ["master"]
    assert result["stuck"] == []


def test_close_emulators_窗口仍在时记为stuck(monkeypatch, tmp_config_dir):
    Lib.write_config(paths.SETTING, {"启动项": {"master": {"启动命令": "a.exe -v 0"}}})
    monkeypatch.setattr(Lib, "find_windows_silent", lambda account: 1234)
    monkeypatch.setattr(Lib, "find_mumu_manager", lambda *a, **k: None)
    monkeypatch.setattr(Lib.win32gui, "PostMessage", lambda *a: None)

    result = Lib.close_emulators(wait_seconds=0)

    assert result["stuck"] == ["master"]
    assert result["closed"] == []


def test_close_emulators_找不到MuMuManager时仍然发WM_CLOSE(monkeypatch, tmp_config_dir):
    """降级路径：没有 MuMuManager 也必须能关掉窗口"""
    Lib.write_config(paths.SETTING, {"启动项": {"master": {"启动命令": "a.exe -v 0"}}})
    posted = []
    state = {"calls": 0}

    def fake_find(account):
        state["calls"] += 1
        return 1234 if state["calls"] <= 2 else None

    monkeypatch.setattr(Lib, "find_windows_silent", fake_find)
    monkeypatch.setattr(Lib, "find_mumu_manager", lambda *a, **k: None)
    monkeypatch.setattr(Lib.win32gui, "PostMessage", lambda hwnd, msg, w, l: posted.append(hwnd))

    result = Lib.close_emulators(wait_seconds=0)

    assert posted == [1234]
    assert result["closed"] == ["master"]


def test_close_emulators_有关闭模拟器能力时不会去启动游戏(monkeypatch, tmp_config_dir):
    """回归保护：关闭流程绝不能走到 Find_windows（它会启动游戏）"""
    Lib.write_config(paths.SETTING, {"启动项": {"master": {"启动命令": "a.exe -v 0"}}})
    monkeypatch.setattr(Lib, "find_windows_silent", lambda account: None)

    def forbidden(*args, **kwargs):
        pytest.fail("关闭模拟器时不该调用 Find_windows / Log_in")

    monkeypatch.setattr(Lib, "Find_windows", forbidden)
    monkeypatch.setattr(Lib, "Log_in", forbidden)

    Lib.close_emulators()


def test_close_emulators_不关未登记的窗口(monkeypatch, tmp_config_dir):
    """只登记了 master，即使系统里有别的窗口也不该被碰"""
    Lib.write_config(paths.SETTING, {"启动项": {"master": {"启动命令": "a.exe -v 0"}}})
    queried = []

    def fake_find(account):
        queried.append(account)
        return None

    monkeypatch.setattr(Lib, "find_windows_silent", fake_find)

    Lib.close_emulators()

    assert set(queried) == {"master"}


# ------------------------------------------------------------ 电源动作
# 与「关闭模拟器」同属系统动作，放同一个文件。
# 全部 mock ctypes，绝不真的注销/关机。


@pytest.fixture()
def fake_power(monkeypatch):
    """把 ctypes 的三个入口换成记录器，避免真的动电脑"""

    class Recorder:
        def __init__(self):
            self.suspend_calls = []
            self.exit_calls = []
            self.suspend_result = True
            self.exit_result = True

    rec = Recorder()

    class FakePowrProf:
        @staticmethod
        def SetSuspendState(*args):
            rec.suspend_calls.append(args)
            return rec.suspend_result

    class FakeUser32:
        @staticmethod
        def ExitWindowsEx(*args):
            rec.exit_calls.append(args)
            return rec.exit_result

    class FakeKernel32:
        @staticmethod
        def GetLastError():
            return 0

    class FakeWindll:
        powrprof = FakePowrProf()
        user32 = FakeUser32()
        kernel32 = FakeKernel32()

    monkeypatch.setattr(Lib.ctypes, "windll", FakeWindll())
    monkeypatch.setattr(Lib, "_enable_shutdown_privilege", lambda: True)
    return rec


def test_power_action_睡眠走SetSuspendState(fake_power):
    assert Lib.power_action("sleep") is True

    assert fake_power.suspend_calls == [(False, False, False)]
    assert fake_power.exit_calls == []


def test_power_action_睡眠不是休眠(fake_power):
    """第一个参数必须是 False，True 会变成休眠"""
    Lib.power_action("sleep")

    assert fake_power.suspend_calls[0][0] is False


def test_power_action_注销走ExitWindowsEx_logoff(fake_power):
    assert Lib.power_action("logoff") is True

    assert fake_power.exit_calls == [(Lib._EWX_LOGOFF, 0)]
    assert fake_power.suspend_calls == []


def test_power_action_关机走ExitWindowsEx_poweroff(fake_power):
    assert Lib.power_action("shutdown") is True

    assert fake_power.exit_calls == [(Lib._EWX_POWEROFF, 0)]


def test_power_action_关机标志不是注销标志():
    """EWX_POWEROFF 才是真正切断电源；EWX_SHUTDOWN 只做到「可安全断电」"""
    assert Lib._EWX_POWEROFF == 0x00000008
    assert Lib._EWX_LOGOFF == 0x00000000


def test_power_action_不加强制标志(fake_power):
    """按用户要求不加 EWX_FORCEIFHUNG，避免杀掉未保存的工作"""
    Lib.power_action("shutdown")

    flag, reserved = fake_power.exit_calls[0]
    assert flag & 0x10 == 0    # EWX_FORCE
    assert flag & 0x20 == 0    # EWX_FORCEIFHUNG
    assert reserved == 0


def test_power_action_未知动作直接返回False(fake_power):
    assert Lib.power_action("hibernate") is False
    assert Lib.power_action("") is False
    assert fake_power.suspend_calls == []
    assert fake_power.exit_calls == []


def test_power_action_特权启用失败时不调用API(fake_power, monkeypatch):
    monkeypatch.setattr(Lib, "_enable_shutdown_privilege", lambda: False)

    assert Lib.power_action("sleep") is False
    assert fake_power.suspend_calls == []
    assert fake_power.exit_calls == []


def test_power_action_API返回0视为失败(fake_power):
    fake_power.suspend_result = False

    assert Lib.power_action("sleep") is False


def test_power_action_调用抛异常时返回False(monkeypatch):
    def boom(*args):
        raise OSError("接口不可用")

    class FakeWindll:
        powrprof = type("P", (), {"SetSuspendState": staticmethod(boom)})()
        user32 = type("U", (), {"ExitWindowsEx": staticmethod(boom)})()
        kernel32 = type("K", (), {"GetLastError": staticmethod(lambda: 0)})()

    monkeypatch.setattr(Lib.ctypes, "windll", FakeWindll())
    monkeypatch.setattr(Lib, "_enable_shutdown_privilege", lambda: True)

    assert Lib.power_action("sleep") is False
    assert Lib.power_action("logoff") is False


def test_power_action_常量表完整():
    assert Lib.POWER_ACTIONS == ("logoff", "sleep", "shutdown")

