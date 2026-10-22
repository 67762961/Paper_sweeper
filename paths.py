# -*- coding: utf-8 -*-
"""配置与状态文件的路径定义，以及旧布局的一次性迁移。

**为什么分两个目录**

`config/` 与 `state/` 的区别是「谁写」：

| 目录 | 内容 | 谁写 | 用户是否手改 |
|---|---|---|---|
| `config/` | `Setting.yml` | 用户 | ✅ 会手改 |
| `state/` | `Last_times.yml`、`Gui_state.yml`、`gui.json` | 程序 | ❌ 只读或删掉重来 |

混在一起的问题：用户手改 `Setting.yml` 时，容易顺手把程序写的
`Last_times.yml` / `Gui_state.yml` 一起改坏；备份/同步 `config/` 时也会
把「机器状态」当成配置带走。分开之后语义清楚，删除 `state/` 就等于恢复初始状态。

**本模块的职责**

1. 定义所有路径常量（唯一事实源，其它模块不要自己拼字符串）；
2. `ensure_state_dir()`：确保 `state/` 存在，并把旧布局（都在 `config/` 里）的文件搬过来。
   这是幂等的，重复调用安全。
"""

import os
import shutil

# ---- 目录 ----
CONFIG_DIR = "config"   # 静态配置，用户手改
STATE_DIR = "state"     # 运行期状态，程序读写

# ---- 文件（唯一事实源）----
SETTING = os.path.join(CONFIG_DIR, "Setting.yml")          # 启动项 / 结界突破 / 寮三十参数
LAST_TIMES = os.path.join(STATE_DIR, "Last_times.yml")     # 各账号各任务上次完成时间
GUI_STATE = os.path.join(STATE_DIR, "Gui_state.yml")       # 任务开关
PREFS = os.path.join(STATE_DIR, "gui.json")                # 界面偏好（主题 / 日志）

# 旧布局 -> 新布局：PR7 之前这三个文件都在 config/ 下
LEGACY_MOVES = (
    (os.path.join(CONFIG_DIR, "Last_times.yml"), LAST_TIMES),
    (os.path.join(CONFIG_DIR, "Gui_state.yml"), GUI_STATE),
    (os.path.join(CONFIG_DIR, "gui.json"), PREFS),
)


def ensure_state_dir():
    """确保 state/ 存在，并把旧布局的文件搬过来（幂等）

    迁移规则：**目标不存在、源存在**时才搬。两边都存在时不覆盖——
    那说明用户已经在新布局下跑过，旧文件只是残留，留着让用户自己决定删不删。

    :return: 实际迁移的文件对数
    """
    os.makedirs(STATE_DIR, exist_ok=True)

    moved = 0
    for old_path, new_path in LEGACY_MOVES:
        if not os.path.exists(old_path) or os.path.exists(new_path):
            continue
        try:
            shutil.move(old_path, new_path)
            print("        MOVE- ----- 状态文件迁移:", old_path, "->", new_path)
            moved += 1
        except OSError as error:
            # 迁移失败不阻塞启动：程序会在新位置重新初始化，
            # 但要把原路径打出来，方便用户手动搬
            print("        WAIT- ----- 状态文件迁移失败:", old_path, "->", new_path, ":", error)
    return moved
