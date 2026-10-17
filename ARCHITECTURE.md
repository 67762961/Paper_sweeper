# 项目架构与任务地图

> 本文档描述 Paper Sweeper（阴阳师纸人扫地工）当前版本的整体架构、任务编排、公共库职责与配置/日志机制。
> 修改任务流程、界面导航或 `Lib.py` 公共函数前，请先阅读本文档，确保变更不破坏 `GUI.py → main.py → Task_*` 的调用链。

## 1. 项目概述

本项目用于在 Windows + MuMu 模拟器环境下，自动化完成《阴阳师》双账号日常，主要支持：

- 按窗口标题定位账号窗口（`master` / `slaves`），未找到时尝试按 `Setting.yml` 启动命令拉起模拟器；
- OpenCV 模板匹配识别界面元素，Win32 / pyautogui / pydirectinput 完成点击与按键；
- 任务级冷却与时间窗门禁，结果写回 `Last_times.yml`；
- 日志双写（控制台 + `logs/<日期>/`），GUI 实时展示；
- 当前任务域覆盖：签到收菜、结界养成、地域鬼王、寮三十与真蛇、结界突破、狩猎战/阴界、逢魔之时。

当前代码版本：GUI 标题标注 `v1.2.0`。

## 2. 顶层架构

```mermaid
flowchart LR
    GUI["GUI.py\nPyQt6 界面\n左侧 7 张任务卡片 + 右侧控制台"] --> WT["WorkerThread\nQThread"]
    WT -->|完整运行| FO["main.Full_operation\n按 TASK_REGISTRY 顺序编排"]
    WT -->|单击卡片| SO["main.Single_operation\n只跑指定任务"]
    REG["main.TASK_REGISTRY\n任务注册表（唯一事实源）"] --> GUI
    REG --> FO
    REG --> SO
    TM["test_main.py\n开发调试入口"] --> FO
    FO --> T1["MainTask_Signin"]
    FO --> T2["MainTask_Jiejieyangcheng"]
    FO --> T3["MainTask_Digui"]
    FO --> T4["FullTask_Thirty\n含真蛇"]
    FO --> T5["FullTask_JiejieFight"]
    FO --> T6["MainTask_Shouliezhan"]
    FO --> T7["MainTask_Fengmo"]
    SO --> T1 & T2 & T3 & T4 & T5 & T6 & T7
    T1 & T2 & T3 & T4 & T5 & T6 & T7 --> LIB["Lib.py\n识别/点击/界面/配置"]
    LIB --> CFG["config/Setting.yml\nconfig/Last_times.yml"]
    LIB --> PIC["pic/**\n模板图片"]
    FO --> LOG["logs/<date>/console_output_*.log"]
    SO --> SLOG["logs/<date>/single_<key>_*.log"]
```

### 目录结构

```
<workspace>/
├── AGENTS.md                      项目要求与协作约定
├── ARCHITECTURE.md                架构与任务说明
├── README.md                      使用说明
├── requirements.txt               Python 依赖
├── .gitignore                     忽略虚拟环境/配置/日志/打包产物/调试脚本
├── GUI.py                         PyQt6 图形入口（环境变量/日志/异常钩子 + 转出 ui 组件）
├── GUI.spec                       PyInstaller 打包配置
├── build_exe.py                   本地打包脚本（调用 GUI.spec，产物输出到根目录）
├── GUI.exe                        打包产物（默认忽略）
├── ui/                            界面层（单向依赖 theme→icons→widgets→panels→window）
│   ├── theme.py                   设计 token：颜色/间距/圆角/字号
│   ├── theme_manager.py           Fluent 主题初始化与 qconfig 持久化
│   ├── icons.py                   今日状态图标与齿轮/运行按钮（QPainter 绘制）
│   ├── widgets.py                 整跑开关、任务行
│   ├── panels.py                  左侧任务列表、右侧日志控制台
│   └── window.py                  主窗口与任务线程
├── main.py                        任务注册表 + 完整/单任务运行编排 + Tee 日志
├── Lib.py                         公共自动化库（识别/点击/界面/配置/编队）
├── Task_SignIn.py                 登录收菜：邮件/签到/福袋/纸人/礼包/友情点
├── Task_Jiejieyangcheng.py        结界养成：工资/寄养/结界卡/育成/食盒酒壶
├── Task_Digui.py                  地域鬼王
├── Task_Thirty.py                 寮三十（御魂协作）与真蛇
├── Task_JiejieFight.py            结界突破
├── Task_Shouliezhan.py            狩猎战（麒麟）与阴界之门
├── Task_Fengmo.py                 逢魔之时
├── test.py / test_main.py         开发调试入口（已忽略，不参与交付）
├── config/                        运行配置（默认忽略）
│   ├── Setting.yml                启动项、结界突破、寮三十副本表
│   ├── Last_times.yml             各账号各任务上次完成时间
│   ├── Gui_state.yml              GUI 任务开关（是否参与完整运行，缺失默认全开）
│   └── gui.json                   界面偏好（主题等，qconfig 管理）
├── pic/                           界面模板图
│   ├── Main/                      庭院/弹窗/协作/返回等通用元素
│   ├── Sign/                      签到与收菜
│   ├── Mail/                      邮件
│   ├── Sis/                       阴阳寮与结界
│   ├── Team/                      编组与队伍预设
│   ├── Thr/                       御魂副本与真蛇
│   ├── Digui/                     地域鬼王
│   ├── Fengmo/                    逢魔
│   ├── JiejieFight/               结界突破
│   └── Shouliezhan/               狩猎战/阴界
├── logs/<YYYY-MM-DD>/             运行日志（console_output_*.log / single_<key>_*.log）
└── build/ __pycache__/ .venv/     构建与环境产物（GUI.exe 直接生成在根目录）
```

## 4. 数据 / 控制流向

主处理链路如下：

```
GUI.py 点击「完整运行」/ 单击左侧某张任务卡片
        ↓
config.stop_thread = False
        ↓
WorkerThread(task_key).run()        # task_key=None 表示完整运行
        ↓
task_key is None → main.Full_operation(console_signal)
否则            → main.Single_operation(task_key, console_signal)
        ↓
Tee 重定向 stdout → 控制台 + logs/<date>/<日志前缀>_*.log + GUI 信号
        ↓
依次调用 MainTask_* / FullTask_*（完整运行按 TASK_REGISTRY 顺序，单任务只调用一项）
        ↓
每个任务：
  1) read_config(Last_times.yml) 遍历账号（master/slaves）
  2) check_lasttime 判断冷却 / 时间窗 / 星期
  3) Find_windows(Account) 获取句柄，必要时 Log_in 启动
  4) 状态机 + 模板匹配执行业务
  5) 成功则 write_config 更新 Last_times.yml
        ↓
流程结束，恢复 stdout；GUI 对比运行前后的完成时间并刷新行内时间与今日状态
```

`Full_operation` 与 `Single_operation` 都通过 `main._log_stream` 统一安装/恢复日志流，区别只在日志文件名前缀（`console_output_` / `single_<key>_`）。

`Full_operation` 在开始时读取 `config/Gui_state.yml` 的任务开关，关闭的任务打印 `SKIP- ----- 任务 <标题> 已在左侧关闭 跳过` 后跳过。

## 5. 入口函数说明

### 5.1 `GUI.py` 与 `ui/` 包

`GUI.py` 只作为入口：设置 Windows DPI（`QT_QPA_PLATFORM=windows:dpiawareness=1`）、安装全局异常钩子（写入 `app_crash.log`）、创建 `QApplication` 并应用主题，最后转出 `ui/` 中的组件供脚本/测试使用。

界面实现位于 `ui/` 包，依赖方向固定为 `theme → icons → widgets → panels → window`，禁止反向引用：

| 模块 | 职责 |
| ---- | ---- |
| `ui/theme.py` | 设计 token：颜色、间距、圆角、字号；所有界面取值统一来自这里 |
| `ui/icons.py` | `StatusIcon`（QPainter 绘制对勾/感叹号/播放三角）、`IconButton`（FluentIcon 图标按钮） |
| `ui/widgets.py` | `ToggleSwitch`（Fluent `SwitchButton` 包装）、`TaskRow`（Fluent `SimpleCardWidget`） |
| `ui/panels.py` | `LeftPanel`（任务列表）、`RightPanel`（Fluent `TextEdit` 日志 + 进度条 + 主按钮） |
| `ui/theme_manager.py` | Fluent 主题初始化、`qconfig` 持久化（`config/gui.json`） |
| `ui/window.py` | `WorkerThread`、`MainWindow`（Fluent 外壳 + 组装 + 线程调度 + `InfoBar` 结果提示） |

窗口外壳：`MainWindow` 继承 `qfluentwidgets.MSFluentWindow`，把双栏内容作为唯一子界面
`mainPage` 加入后**隐藏左侧导航**，因此保留参考项目的 Fluent 观感与无边框窗口，
信息架构仍然是「左侧任务列表 + 右侧日志控制台」两栏。

主体职责：

- 左侧 7 行任务（由 `main.TASK_REGISTRY` 驱动，与完整运行同顺序），右侧控制台与「完整运行」按钮；
- `WorkerThread` 持有 `task_key`：`None` 时调用 `main.Full_operation`，否则调用 `main.Single_operation`；
- 运行期间所有行的交互控件与「完整运行」按钮一起禁用（`MainWindow.busy` 互斥），并显示不确定进度条；
- 结束后刷新行内「上次运行」时间与今日状态图标，并用 `InfoBar` 提示本次结果。

单行结构（从左到右）：

| 区域 | 控件 | 说明 |
| ---- | ---- | ---- |
| 今日状态 | `StatusIcon` | 今日已完成 → 绿色对勾；今日未完成 → 橙色 `!`；运行中 → 蓝色播放三角（均为 QPainter 绘制，无底色圆圈） |
| 任务信息 | 名称 + 「上次运行 MM-DD HH:MM」 | 时间取该任务所有账号、所有状态键中的最新值 |
| 配置 | `IconButton(kind="gear")` | `FluentIcon.SETTING`；本期为**占位**：弹「配置功能暂未开放」，不写盘 |
| 单跑 | `IconButton(kind="play")` | `FluentIcon.PLAY`；点击只运行该任务（等价于 `Single_operation`） |
| 开关 | `ToggleSwitch` | Fluent `SwitchButton`（不显示 On/Off 文案）；开 → 参与「完整运行」；关 → 完整运行时跳过、整行半透明，并写入 `config/Gui_state.yml` |

图标：齿轮与运行按钮使用 `FluentIcon`；今日状态（对勾/感叹号/播放三角）用 `QPainter` 绘制，保证任意 DPI 下清晰。右上「完整运行」为轮廓按钮（主色描边 + 主色文字，悬停浅蓝底），不使用实心主色块。

交互约定：

| 操作 | 行为 |
| ---- | ---- |
| 点击行内 ▶ | 只运行该行对应的顶层任务（对 `Last_times.yml` 全部账号），冷却与时间窗照旧生效 |
| 点击行内齿轮 | 弹出占位提示，不写任何配置 |
| 拨动行内开关 | 写入 `config/Gui_state.yml`；关闭时该行灰化，且在「完整运行」中被跳过 |
| 点击「完整运行」 | 按 `TASK_REGISTRY` 顺序执行**开关开启**的任务 |
| 运行中再次点击 | 被 `busy` 互斥拒绝，不会启动第二个线程 |
| 运行中关闭窗口 | 弹确认框；确认后置位 `config.stop_thread` 并短暂等待线程 |

注意：`GUI.py` / `test_main.py` 会 `import config`。仓库中当前没有 `config.py` 源文件；本地运行前需在项目根目录自备，至少包含：

```python
stop_thread = False
```

### 5.2 `main.py`

调用形式：

```python
Full_operation(console_signal=None)              # 完整运行（按开关跳过已关闭任务）
Single_operation(task_key, console_signal=None)  # 单任务运行，返回 {key, ok, reason}
```

职责：

- 维护 `TASK_REGISTRY`：`TaskEntry(key, title, desc, entry, lasttime_keys, today_keys)`，是「左侧行列表 / 完整运行顺序 / GUI 状态键」的唯一事实源；
- 创建日志文件：完整运行为 `logs/<YYYY-MM-DD>/console_output_<时间戳>.log`，单任务为 `logs/<YYYY-MM-DD>/single_<key>_<时间戳>.log`；
- 用 `Tee` 把 stdout 同时写到原控制台、日志文件和 GUI 信号；
- 完整运行按注册表顺序编排并按任务开关跳过，单任务运行只调用一项且**不看开关**；
- `_log_stream` 在 `finally` 中先恢复 `sys.stdout` 再尽力冲刷，避免无控制台环境（打包版 `GUI.exe` / `pythonw`）下 `sys.stdout is None` 造成收尾异常。

`main.py` 同时定义 `Tee`：按行缓冲，保证 GUI 控制台按完整行更新；`files` 会过滤空流，写入/冲刷失败不中断任务。

辅助函数：

| 函数 | 职责 |
| ---- | ---- |
| `get_task(key)` | 按 key 查注册表条目，未登记返回 `None` |
| `read_completions()` | 一次性只读 `Last_times.yml`，返回 `{账号: {任务键: datetime}}`；不创建文件、不写盘 |
| `latest_completion(entry, completions=None)` | 取该任务在所有账号、所有状态键中的最新完成时间（行内「上次运行」） |
| `completion_snapshot(entries=None)` | 记录各任务当前完成时间快照 |
| `completion_advanced(before, after)` | 对比快照，返回 `{key: 是否推进}`，用于运行结果摘要 |
| `entry_done_today(entry, completions=None, today=None)` | 判定「今日已完成」：`check_keys` 中的每个键在所有账号上都要有今天的记录 |
| `read_task_switches()` | 读取 `config/Gui_state.yml` 的任务开关，缺失默认全开，只读不建文件 |
| `is_task_enabled(key, switches=None)` / `enabled_task_keys(switches=None)` | 判断/列出参与完整运行的任务 |
| `set_task_switch(key, enabled)` | 写入单个任务开关，成功返回 `True` |

### 5.3 任务模块入口

完整流程 `Full_operation` 当前顺序（即 `TASK_REGISTRY` 顺序；单任务运行复用同一入口）：

| 顺序 | 注册表 key | 行标题 | 入口 | 模块 | 今日判定键（`today_keys`） | 说明 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| 1 | `signin` | 登录收菜 | `MainTask_Signin()` | `Task_SignIn.py` | 邮件领取 / 每日一签 / 福袋纸人 / 免费礼包 / 送友情点（全部） | 邮件、每日一签、福袋、纸人、免费礼包、友情点 |
| 2 | `jiejieyangcheng` | 结界养成 | `MainTask_Jiejieyangcheng()` | `Task_Jiejieyangcheng.py` | 结界养成 | 寮界面：工资/体力、寄养、结界卡、白达摩育成、食盒酒壶 |
| 3 | `digui` | 地域鬼王 | `MainTask_Digui()` | `Task_Digui.py` | 地域鬼王 | 经探索→六道进入地鬼，时间窗 12:00–23:50，当日冷却 |
| 4 | `thirty` | 寮三十 / 真蛇 | `FullTask_Thirty()` | `Task_Thirty.py` | 寮三十（真蛇为周更，不参与今日判定） | 寮三十协作刷本 + 非周末真蛇（周冷却） |
| 5 | `jiejiefight` | 结界突破 | `FullTask_JiejieFight()` | `Task_JiejieFight.py` | 结界突破 | 结界突破，时间窗 7:00–23:00，1 小时冷却 |
| 6 | `shouliezhan` | 狩猎战 / 阴界 | `MainTask_Shouliezhan()` | `Task_Shouliezhan.py` | 狩猎战 | 周四–周日阴界之门；其余日麒麟狩猎战（当日冷却） |
| 7 | `fengmo` | 逢魔之时 | `MainTask_Fengmo()` | `Task_Fengmo.py` | 逢魔之时 | 逢魔之时，时间窗 17:00–21:50，当日冷却 |

`today_keys` 为空表示与 `lasttime_keys` 相同（`TaskEntry.check_keys` 负责回落）。

任务模块通用约定：

- `MainTask_*`：读配置 → 判冷却 → 遍历账号 → 调用业务函数 → 写回时间；
- `Work_*` / 无前缀业务函数：在单窗口上执行具体点击流程，返回 `1` 成功 / `0` 失败；
- 复杂界面用状态机字符串推进，异常统一 `Itface_Host` 回庭院后退出。

### 5.4 `Lib.py` 公共库

| 类别 | 函数 | 职责 |
| ---- | ---- | ---- |
| 窗口 | `Find_windows` | 按标题子串枚举可见窗口；找不到则 `Log_in` 启动后再找 |
| 登录 | `Log_in` | 按 `Setting.yml.启动项` 拉起 MuMu，处理适龄提示 |
| 识别 | `Img_read_ch` / `Match_model` | 中文路径读图；`TM_SQDIFF_NORMED` 模板匹配，阈值越小越严 |
| 识别 | `Find_in_windows_Matchs` / `Find_in_windows_Range` / `Find_multiple_in_windows_Matchs` | 窗口截图匹配 / 区域匹配 / 多目标匹配（匹配后涂黑避免重复） |
| 识别 | `Find_in_screen_Matchs` / `Find_Click_screen` | 全屏匹配与点击（协作拒绝等） |
| 操作 | `Move_to_range` / `Click` / `Find_Click_windows` | 识别框内随机落点点击；「找到则点」组合 API |
| 等待 | `Sleep_print` / `Sleep_print_long` / `Scroll_print` / `Esc_print` | 带日志的等待/滚轮/Esc；长等待附带拒绝协作 |
| 界面 | `Itface_Host` | 庭院复位状态机：协作→弹窗→退出标志→Esc，上限约 30 轮 |
| 界面 | `Itface_Quit` / `Itface_scroll` / `Itface_guild` / `Itface_daily` / `Itface_explore` | 退出界面、卷轴、阴阳寮、日常外显入口、探索/六道 |
| 编队 | `Team_Preset` | 式神录→预设编组→队伍→应用御魂预设 |
| 配置 | `read_config` / `write_config` / `check_lasttime` | YAML 读写；`Last_times.yml` 时间读取与缺失初始化 |

模板匹配阈值约定：`Match_model` 使用 `cv2.TM_SQDIFF_NORMED`，**数值越小越相似**；`min_val > Threshold` 视为未命中。任务代码中的阈值多在 `0.01～0.07`。

点击坐标约定：匹配框 `[(Left_up), (Right_down)]` 的中心 1/4～3/4 区域内随机点；全局坐标特例见 `Itface_scroll`（卷轴约 `((1780, 970), (1910, 1120))`）。

## 6. 配置体系

### 6.1 `config/Setting.yml`

| 键 | 含义 |
| ---- | ---- |
| `启动项.<账号>.启动命令` | MuMu 启动命令；账号名为窗口标题关键字 |
| `结界突破.<账号>.退出次数` / `开打勋章` | 结界突破策略参数 |
| `寮三十.主账号` / `副账号` | 协作刷本的两个窗口 |
| `寮三十.副本` / `次数` | 按星期（一～日）配置的副本类型与次数 |

寮三十副本类型当前支持：`魂虚`、`魂海`、`日蚀` 等；次数填 `0` 表示当日跳过。

### 6.2 `config/Last_times.yml`

结构：`<账号> -> <任务名> -> ISO 时间字符串`。

常见任务键与冷却策略：

| 任务键 | 冷却/门禁 |
| ---- | ---- |
| 邮件领取 | ≥ 1 小时 |
| 每日一签 / 福袋纸人 / 纸人奖励 | 按业务逻辑领取，部分不写时间 |
| 免费礼包 / 地域鬼王 / 逢魔之时 / 狩猎战 | 当日未完成才执行（`date` 比较） |
| 送友情点 | 业务内判断 |
| 结界养成 | ≥ 6 小时 |
| 结界突破 | ≥ 1 小时，且在 7:00–23:00 |
| 寮三十 | 两账号均已完成当日则跳过；限 9:00–23:00 |
| 真蛇 | 按 ISO 周（`isocalendar` 周序号），非周末执行 |

`check_lasttime` 在键缺失时初始化为 `2000-01-01 00:00:00`。

### 6.3 `config/Gui_state.yml`（任务开关）

结构：`任务开关 -> <注册表 key> -> true/false`，由 GUI 行内开关写入，决定该任务是否参与「完整运行」。

```yaml
任务开关:
  signin: true
  jiejieyangcheng: true
  digui: true
  thirty: true
  jiejiefight: true
  shouliezhan: true
  fengmo: true
```

约定：

- 文件不存在、或某个 key 缺失时**默认开启**（不破坏老用户配置）；
- 只有用户拨动开关才写盘；读取开关不会创建文件；
- 与 `Setting.yml`（任务参数）分离，避免 GUI 偏好混进用户手写配置；
- 单击行内 ▶ 不受该开关影响，只有「完整运行」会跳过关闭的任务。

### 6.4 `config/gui.json`（界面偏好）

由 `qfluentwidgets` 的 `qconfig` 管理，保存主题模式（浅色/深色/跟随系统）等界面偏好。
文件缺失时使用浅色主题；与 `Setting.yml`（任务参数）、`Gui_state.yml`（任务开关）互不干扰。

### 6.5 项目级 `config.py`

- 用途：GUI 线程停止标志（`config.stop_thread`）。
- 状态：源码树中不存在该文件；属于运行时必需的本地模块。
- 最小内容：`stop_thread = False`。
- 生成方式：可手写，也可执行 `python build_exe.py` 时由脚本自动生成（已存在则不改动）。

## 7. 关键模块与算法

### 7.1 模板匹配流水线

1. `win32gui.GetWindowRect` 取窗口矩形；
2. `pyautogui.screenshot(region=...)` 截取窗口；
3. `cv2.cvtColor` 转 BGR；
4. `cv2.matchTemplate(..., TM_SQDIFF_NORMED)`；
5. `minMaxLoc` 得最小值与位置，结合模板尺寸得到 `Left_up/Right_down`；
6. 阈值判定后返回区间与得分字符串。

中文路径通过 `Img_read_ch`（`np.frombuffer` + `cv2.imdecode`）读取。

### 7.2 界面状态机

典型模式：

```python
current_state = "庭院界面"
for step in range(30):
    match current_state:
        case "庭院界面":
            ...
            current_state = "寮界面"
        case "异常退出":
            Itface_Host(Hwnd)
            return 0
```

`Itface_Host` 是全局兜底：检测庭院 → 处理协作/弹窗/退出标志 → 必要时 Esc，失败返回 `0`。

### 7.3 双账号协作（寮三十 / 真蛇）

- 从 `Setting.yml` 取主/副账号与窗口句柄；
- `Team_Preset` 切换对应副本编队；
- 两窗口交替进入组队/挑战流程；
- 真蛇额外处理「御魂装配」等前置状态，成功后写周时间。

### 7.4 日志协议

`Tee` 将业务 `print` 双写。前缀语义：

| 前缀 | 含义 |
| ---- | ---- |
| `TASK-` | 任务开始/结束 |
| `STEP-` | 状态机跳转 |
| `INFO-` | 识别结果与业务信息（常带匹配得分） |
| `WAIT-` | 等待 |
| `SKIP-` | 冷却未到或时间窗外跳过 |
| `TIME-` | 上次/本次任务时间 |
| `MOVE-` / `QUIT-` | 滚轮、Esc 等操作 |
| `MAIN-` | 完整流程 / 单任务运行起止 |

GUI 崩溃日志：`app_crash.log`（`logging` + `sys.excepthook`）。

右侧日志面板按行首关键字着色：`ERROR` / `错误` → 红，`SKIP-` → 橙，`TASK-` / `MAIN-` → 蓝，其余使用主题默认文字颜色；
运行期间面板下方显示不确定进度条，结束后用 `InfoBar` 提示本次结果。

单任务运行在 `MAIN-` 起止行中带任务标题，例如：

```
MAIN- ===== 单任务运行开始：逢魔之时 ================================================
...
MAIN- ===== 单任务运行结束：逢魔之时 ================================================
```

## 8. 输出与运行产物

```
<workspace>/
├── logs/<YYYY-MM-DD>/console_output_<timestamp>.log   完整运行日志
├── logs/<YYYY-MM-DD>/single_<key>_<timestamp>.log     单任务运行日志
├── app_crash.log                                      未捕获异常
├── config/Last_times.yml                              任务冷却状态（本地）
├── config/Gui_state.yml                               任务开关（本地）
├── config/gui.json                                    界面偏好（本地）
├── build/                                             PyInstaller 中间产物
├── GUI.exe                                            打包产物（直接在根目录，默认忽略）
└── __pycache__/                                       字节码缓存
```

运行模式：

| 方式 | 命令/入口 | 说明 |
| ---- | ---- | ---- |
| GUI | `python GUI.py` | 单击左侧卡片跑单个任务；「完整运行」按注册表顺序跑全套 |
| 脚本 | 调用 `main.Full_operation()` | 无 GUI，输出到控制台与日志 |
| 脚本 | 调用 `main.Single_operation("<key>")` | 单个任务，日志写到 `logs/<日期>/single_<key>_*.log` |
| 调试 | `test.py` / `test_main.py` | 单点验证模板/任务，已 gitignore |
| 打包 | `python build_exe.py` | 调用 `GUI.spec`，产物 `GUI.exe` 直接输出到项目根目录 |

## 9. 实施约束

1. 新增任务时，必须同时更新：
   - `Task_*.py` 业务模块；
   - `main.TASK_REGISTRY`（key / 行标题 / 说明 / 入口 / `lasttime_keys` / `today_keys`），左侧行列表与完整运行顺序都由它驱动；
   - `Last_times.yml` 任务键与冷却策略；
   - `ARCHITECTURE.md` / `README.md` 中的功能与目录说明。
2. 新增模板图必须放进对应 `pic/<业务>/`，路径使用 `./pic/...` 相对当前工作目录。
3. 识别阈值、点击等待写在调用处，修改后需用真实窗口回归；调试可临时 `Flag_show=1` 弹出标注框。
4. 时间窗、星期分支写在 `MainTask_*` 入口层，不要埋进底层 `Lib` 点击函数。
5. 冷却成功写回、失败不写回；`Setting.yml` 只放用户可改的静态配置，GUI 偏好分别写 `Gui_state.yml`（任务开关）与 `gui.json`（主题），三者不要混用。
6. `config/`、`logs/`、`build/`、`dist/`、`GUI.exe`、调试脚本默认不入库；需要跟踪的新源码与文档请在 `.gitignore` 中显式排除忽略。
7. 修改 `Lib.py` 公共匹配/点击/界面函数前，确认所有 `Task_*` 调用方语义不变，尤其是返回值 `1/0` 与 `Range/Matchs` 约定。
8. 新增界面依赖（如 Fluent 组件库）时，必须同步 `requirements.txt` 与 `GUI.spec` 的 `hiddenimports`，并用 `python build_exe.py` 验证打包产物可启动。
9. 本项目通过公开 UI 自动化交互，不修改游戏文件；文档与注释避免暗示注入、外挂或协议破解能力。
10. GUI 行内图标（✓ / ! / ▶ / 齿轮）统一用 `QPainter` 矢量绘制，不依赖字体字形，也不往 `pic/` 塞 UI 素材。
