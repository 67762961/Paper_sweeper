# -*- coding: utf-8 -*-
"""结界养成配置读写层（不依赖 Qt）。

职责：把 ``config/Setting.yml`` 里「结界养成」这一段按账号读成界面友好的结构，
并把弹窗里的选择写回去。段内每个账号两个键：

```yaml
结界养成:
  "master":
    优先结界卡: "太鼓"                                     # 太鼓 / 斗鱼
    寄养优先级: [六星太鼓, 六星斗鱼, 五星太鼓, 五星斗鱼]      # 4 项，越左越优先
```

**为什么单独一层**：弹窗继承 ``MessageBoxBase``，没有 parent 会崩
（``parent.width()`` AttributeError），没法在无 GUI 环境里直接测。

**为什么复用 ``Lib`` 的枚举与归一化**：任务层运行时读的是 ``Lib.load_jiejie_settings``，
弹窗必须与它用同一套规则，否则会出现「界面能选出来、程序却当非法值回落」的错位。
任务层不能 import ``ui/``（``ui`` → ``main`` → 任务模块会成环），但反向是安全的。

**为什么不复用 ``Lib.read_config`` / ``Lib.write_config``**：与
``ui/thirty_settings.py`` 同一组原因——前者没设 ``preserve_quotes``（引号在**读**的
时候就丢了），后者没设 ``width``（``启动项`` 里的长命令会被折成两行），
而列表要保住 ``[...]`` 单行写法必须**原地切片**。详见 ARCHITECTURE.md §5.8。
"""

import os

import ruamel.yaml
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

import Lib
import paths

SECTION = Lib.JIEJIE_SECTION
KEY_CARD = Lib.JIEJIE_KEY_CARD
KEY_PRIORITY = Lib.JIEJIE_KEY_PRIORITY

CARD_OPTIONS = Lib.JIEJIE_CARD_OPTIONS
PRIORITY_OPTIONS = Lib.JIEJIE_PRIORITY_OPTIONS
PRIORITY_COUNT = Lib.JIEJIE_PRIORITY_COUNT

DEFAULT_ACCOUNTS = ("master", "slaves")
DEFAULT_CARD = Lib.JIEJIE_DEFAULT_CARD
DEFAULT_PRIORITY = list(Lib.JIEJIE_DEFAULT_PRIORITY)

# 四级优先级的完整标签（弹窗用；短标签含义不清，宽度也够）
PRIORITY_LABELS = ("第一优先级", "第二优先级", "第三优先级", "第四优先级")


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
        print("        INFO- ----- 结界养成配置无法解析，按默认值显示:", path)
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


def _account_roles(data):
    """账号 → 「主」/「副」，只用于卡片标题的装饰，不参与落盘

    取自「寮三十」段的主副账号；没有该段或账号未被指派时返回空字典。
    """
    section = data.get("寮三十") if isinstance(data, dict) else None
    if not isinstance(section, dict):
        return {}
    roles = {}
    primary = section.get("主账号")
    secondary = section.get("副账号")
    if isinstance(primary, str) and primary:
        roles[primary] = "主"
    if isinstance(secondary, str) and secondary and secondary != primary:
        roles[secondary] = "副"
    return roles


def load_jiejie_settings(path=None):
    """读取全部账号的结界养成配置；任何异常都降级为默认值，不抛到界面层

    :return: ``{"accounts", "roles", "settings", "warnings"}``
             ``settings`` 形如 ``{"master": {"card": "太鼓", "priority": [...]}}``
    """
    path = path or paths.SETTING
    data, _ = _load_raw(path)
    accounts = _account_names(data)

    section = data.get(SECTION)
    if not isinstance(section, dict):
        section = {}

    warnings = []
    settings = {}
    for account in accounts:
        raw = section.get(account)
        if not isinstance(raw, dict):
            raw = {}
        settings[account] = {
            "card": Lib.normalize_jiejie_card(raw.get(KEY_CARD), warnings),
            "priority": Lib.normalize_jiejie_priority(raw.get(KEY_PRIORITY), warnings),
        }

    return {
        "accounts": accounts,
        "roles": _account_roles(data),
        "settings": settings,
        "warnings": warnings,
    }


def _validate_one(account, card, priority):
    """保存前校验单个账号；返回问题描述，通过时返回 None"""
    if card not in CARD_OPTIONS:
        return f"{account} 的「{KEY_CARD}」取值 {card!r} 不受支持"
    if not isinstance(priority, (list, tuple)):
        return f"{account} 的「{KEY_PRIORITY}」不是列表"
    if len(priority) != PRIORITY_COUNT:
        return f"{account} 的「{KEY_PRIORITY}」需要 {PRIORITY_COUNT} 项，实际 {len(priority)} 项"
    seen = set()
    for index, value in enumerate(priority):
        if value not in PRIORITY_OPTIONS:
            return f"{account} 的第 {index + 1} 优先级 {value!r} 不受支持"
        if value in seen:
            return f"{account} 的第 {index + 1} 优先级 {value!r} 与更靠前的项重复"
        seen.add(value)
    return None


def _write_list(section, key, values):
    """把列表写进 section；已有列表**原地切片**以保住 flow 风格

    整体替换 ``section[key] = list(values)`` 会让 ruamel 丢掉 flow 标记，
    输出变成每项一行的块状，与手写的 ``寄养优先级: [...]`` 不一致。
    """
    existing = section.get(key)
    if isinstance(existing, list):
        existing[:] = list(values)
        return

    seq = CommentedSeq(list(values))
    seq.fa.set_flow_style()
    section[key] = seq


def save_jiejie_settings(per_account, path=None):
    """把界面选择写回 ``config/Setting.yml``，只覆盖「结界养成」段

    :param per_account: ``{"master": {"card": ..., "priority": [...]}, ...}``
                        ``启动项`` 里没有的账号会被忽略
    :return: True 表示写盘成功；False 表示校验失败、配置损坏或写入异常
    """
    path = path or paths.SETTING

    data, writable = _load_raw(path)
    if not writable:
        # 文件存在但解析不了：写回等于把用户原内容抹掉，宁可失败
        print("        TASK- ----- 结界养成设置保存失败：配置文件无法解析，已放弃写入")
        return False

    accounts = _account_names(data)
    if not per_account:
        print("        TASK- ----- 结界养成设置保存失败：没有可保存的账号")
        return False

    for account in accounts:
        if account not in per_account:
            continue
        item = per_account[account]
        problem = _validate_one(account, item.get("card"), item.get("priority"))
        if problem:
            print("        TASK- ----- 结界养成设置保存失败：", problem)
            return False

    section = data.get(SECTION)
    if not isinstance(section, dict):
        section = CommentedMap()
        data[SECTION] = section
        # 新建段时补一个前置空行，与手写的「段与段之间空一行」保持一致。
        # 只在新建时做：段已存在时再加一次会累积成两个空行（实测过）。
        data.yaml_set_comment_before_after_key(SECTION, before="")

    for account in accounts:
        if account not in per_account:
            continue
        item = per_account[account]
        # 每个账号一个子映射；账号名带引号，与「启动项」的写法一致
        account_section = section.get(account)
        if not isinstance(account_section, dict):
            account_section = CommentedMap()
            section[DoubleQuotedScalarString(account)] = account_section
        account_section[KEY_CARD] = item["card"]
        _write_list(account_section, KEY_PRIORITY, item["priority"])

    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        yaml = _new_yaml()
        with open(path, "w", encoding="utf-8") as handle:
            yaml.dump(data, handle)
    except (OSError, ruamel.yaml.YAMLError) as error:
        print("        TASK- ----- 结界养成设置保存失败：", error)
        return False

    return True
