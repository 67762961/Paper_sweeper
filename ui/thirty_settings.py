# -*- coding: utf-8 -*-
"""寮三十配置读写层（不依赖 Qt）。

职责：把 ``config/Setting.yml`` 里「寮三十」这一段的四个键
（主账号 / 副账号 / 副本 / 次数）读成界面友好的结构，并把界面的选择写回去。

**为什么单独一层**：弹窗继承 ``MessageBoxBase``，没有 parent 会崩
（``parent.width()`` AttributeError），没法在无 GUI 环境里直接测。把读写与归一化
放在这里，pytest 就能脱离 Qt 覆盖「长度不对 / 值非法 / 0 不能当假值」这些最容易写错的地方。

**为什么不复用 ``Lib.read_config`` / ``Lib.write_config``**（本模块唯一的「绕开公共函数」）：

1. 引号是在**读**的时候丢的——``Lib.read_config`` 没设 ``preserve_quotes``，
   用户手写的 ``"master"`` 读进来就变成 ``master``，写回后多出一堆无意义的 diff；
2. 长命令折行是**写**造成的——``Lib.write_config`` 没设 ``width``（默认 80），
   ``启动项`` 里的 MuMu 启动命令会被折成两行；
3. 列表变块状与用哪个 writer **无关**，只跟是否原地切片有关：用
   ``sec["副本"][:] = [...]`` 原地赋值时 flow 风格保持；一旦整体替换
   ``sec["副本"] = [...]``，无论哪个 writer 都会变成每项一行的块状。

所以这里自建一个 YAML 实例（``preserve_quotes`` + ``width=4096`` + 固定缩进），
读写都走它，并且写回列表时**必须原地切片**。
"""

import os

import ruamel.yaml
from ruamel.yaml.comments import CommentedMap, CommentedSeq

import paths

# 段名与键名（与 config/Setting.yml 一致）
SECTION = "寮三十"
KEY_PRIMARY = "主账号"
KEY_SECONDARY = "副账号"
KEY_FUBEN = "副本"
KEY_TIMES = "次数"

# 与 Task_Thirty.py 的 match Fuben 分支一一对应（只有这 4 个分支）
FUBEN_OPTIONS = ("魂虚", "魂王", "魂海", "日蚀")
# 与 Task_Thirty.py 的小纸人计数 match 对应：0 提前返回、1/30/50 三种计数
TIMES_OPTIONS = (0, 1, 30, 50)

DEFAULT_FUBEN = "魂虚"
DEFAULT_TIMES = 30
DEFAULT_ACCOUNTS = ("master", "slaves")

WEEK_LABELS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
WEEK_COUNT = len(WEEK_LABELS)


def _new_yaml():
    """读写共用的 YAML 实例：保引号、不折行、固定缩进"""
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096
    return yaml


def _load_raw(path):
    """读原始 YAML；返回 (数据, 是否可安全写回)

    文件不存在 → 空 CommentedMap + True（可以新建）
    文件存在但解析失败 → 空 CommentedMap + False（**不能**写回，否则覆盖用户原内容）
    """
    if not os.path.exists(path):
        return CommentedMap(), True

    try:
        yaml = _new_yaml()
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.load(handle)
    except (OSError, UnicodeDecodeError, ruamel.yaml.YAMLError) as error:
        reason = str(error).splitlines()[0] if str(error) else type(error).__name__
        print("        INFO- ----- 寮三十配置无法解析，按默认值显示:", path)
        print("        INFO- -----", reason)
        return CommentedMap(), False

    return (data if isinstance(data, dict) else CommentedMap()), True


def _account_names(data):
    """``启动项`` 的 key 列表（保持文件顺序）；读不到时回落默认两个账号"""
    launch = data.get("启动项") if isinstance(data, dict) else None
    if isinstance(launch, dict):
        names = [str(key) for key in launch.keys()]
        if names:
            return names
    return list(DEFAULT_ACCOUNTS)


def _coerce_fuben(value):
    """合法副本名原样返回；其它一律返回 None（由调用方回落默认值）"""
    if isinstance(value, str) and value in FUBEN_OPTIONS:
        return value
    return None


def _coerce_times(value):
    """合法次数原样返回；其它返回 None

    注意 ``bool`` 是 ``int`` 的子类：``True in (0, 1, 30, 50)`` 会命中 1，
    所以必须先把布尔值挡掉，否则 YAML 里手写个 ``true`` 会被当成 1 次。
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value in TIMES_OPTIONS:
        return value
    return None


def _normalize_list(raw, coerce, default, label, warnings):
    """把 ``副本`` / ``次数`` 归一化成恰好 7 项

    - 缺失 / 非列表 → 全默认值；
    - 长度不足 → 补默认值；超出 → 截断；
    - 单项非法 → 该项回落默认值，并记一条提示（不静默改配置）。
    """
    if raw is None:
        values = []
    elif isinstance(raw, (list, tuple)):
        values = list(raw)
    else:
        warnings.append(f"「{label}」不是列表，已按默认值显示")
        values = []

    if values and len(values) != WEEK_COUNT:
        warnings.append(f"「{label}」应为 {WEEK_COUNT} 项，实际 {len(values)} 项，已按 {WEEK_COUNT} 项显示")

    result = []
    for index in range(WEEK_COUNT):
        if index < len(values):
            value = coerce(values[index])
            if value is None:
                warnings.append(
                    f"{WEEK_LABELS[index]}的「{label}」取值 {values[index]!r} 不受支持，已按默认值显示"
                )
                value = default
        else:
            value = default
        result.append(value)
    return result


def _normalize_accounts(section, accounts, warnings):
    """主副账号回落：必须都在 ``启动项`` 里，且不能相同"""
    primary = section.get(KEY_PRIMARY)
    if primary not in accounts:
        if primary is not None:
            warnings.append(f"主账号 {primary!r} 不在「启动项」里，已回落为 {accounts[0]!r}")
        primary = accounts[0]

    secondary = section.get(KEY_SECONDARY)
    if secondary not in accounts:
        if secondary is not None:
            warnings.append(f"副账号 {secondary!r} 不在「启动项」里，已自动回落")
        secondary = next((name for name in accounts if name != primary), primary)

    if secondary == primary:
        alternative = next((name for name in accounts if name != primary), None)
        if alternative is None:
            warnings.append("「启动项」里只有一个账号，主副账号无法区分，将按同一窗口执行")
        else:
            warnings.append(f"主副账号不能相同，副账号已自动改为 {alternative!r}")
            secondary = alternative

    return primary, secondary


def load_account_names(path=None):
    """账号下拉的选项来源：``启动项`` 的 key（保持文件顺序）"""
    data, _ = _load_raw(path or paths.SETTING)
    return _account_names(data)


def load_thirty_settings(path=None):
    """读取寮三十配置；任何异常都降级为默认值，不抛到界面层

    :return: ``{"accounts", "primary", "secondary", "fuben", "times", "warnings"}``
    """
    data, _ = _load_raw(path or paths.SETTING)
    accounts = _account_names(data)

    section = data.get(SECTION)
    if not isinstance(section, dict):
        section = {}

    warnings = []
    primary, secondary = _normalize_accounts(section, accounts, warnings)
    fuben = _normalize_list(section.get(KEY_FUBEN), _coerce_fuben, DEFAULT_FUBEN, "副本", warnings)
    times = _normalize_list(section.get(KEY_TIMES), _coerce_times, DEFAULT_TIMES, "次数", warnings)

    return {
        "accounts": accounts,
        "primary": primary,
        "secondary": secondary,
        "fuben": fuben,
        "times": times,
        "warnings": warnings,
    }


def _validate(primary, secondary, fuben_list, times_list, accounts):
    """保存前的防御性校验；返回问题描述，通过时返回 None"""
    if primary not in accounts:
        return f"主账号 {primary!r} 不在「启动项」里"
    if secondary not in accounts:
        return f"副账号 {secondary!r} 不在「启动项」里"
    # 只有一个账号时无法互斥，界面已提示，这里放行；两个以上必须不同
    if primary == secondary and len(accounts) > 1:
        return "主账号与副账号不能相同"

    if len(fuben_list) != WEEK_COUNT:
        return f"副本需要 {WEEK_COUNT} 项，实际 {len(fuben_list)} 项"
    for index, value in enumerate(fuben_list):
        if value not in FUBEN_OPTIONS:
            return f"{WEEK_LABELS[index]}的副本 {value!r} 不受支持"

    if len(times_list) != WEEK_COUNT:
        return f"次数需要 {WEEK_COUNT} 项，实际 {len(times_list)} 项"
    for index, value in enumerate(times_list):
        if _coerce_times(value) is None:
            return f"{WEEK_LABELS[index]}的次数 {value!r} 不受支持"
    return None


def _write_list(section, key, values):
    """把列表写进 section；已有列表**原地切片**以保住 flow 风格

    整体替换 ``section[key] = list(values)`` 会让 ruamel 丢掉 flow 标记，
    输出变成每项一行的块状，与用户手写的 ``副本: ["魂虚", ...]`` 不一致。
    """
    existing = section.get(key)
    if isinstance(existing, list):
        existing[:] = list(values)
        return

    seq = CommentedSeq(list(values))
    seq.fa.set_flow_style()
    section[key] = seq


def save_thirty_settings(primary, secondary, fuben_list, times_list, path=None):
    """把界面选择写回 ``config/Setting.yml``，只覆盖寮三十的四个键

    :return: True 表示写盘成功；False 表示校验失败、配置损坏或写入异常
    """
    path = path or paths.SETTING

    data, writable = _load_raw(path)
    if not writable:
        # 文件存在但解析不了：写回等于把用户原内容抹掉，宁可失败
        print("        TASK- ----- 寮三十设置保存失败：配置文件无法解析，已放弃写入")
        return False

    accounts = _account_names(data)
    problem = _validate(primary, secondary, fuben_list, times_list, accounts)
    if problem:
        print("        TASK- ----- 寮三十设置保存失败：", problem)
        return False

    section = data.get(SECTION)
    if not isinstance(section, dict):
        section = CommentedMap()
        data[SECTION] = section

    section[KEY_PRIMARY] = primary
    section[KEY_SECONDARY] = secondary
    _write_list(section, KEY_FUBEN, fuben_list)
    _write_list(section, KEY_TIMES, times_list)

    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        yaml = _new_yaml()
        with open(path, "w", encoding="utf-8") as handle:
            yaml.dump(data, handle)
    except (OSError, ruamel.yaml.YAMLError) as error:
        print("        TASK- ----- 寮三十设置保存失败：", error)
        return False

    return True
