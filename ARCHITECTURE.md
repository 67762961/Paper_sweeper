# 项目架构与任务地图

> 本文档描述 Paper Sweeper（阴阳师纸人扫地工）当前版本的整体架构、任务编排、公共库职责与配置/日志机制。
> 修改任务流程、界面导航或 `Lib.py` 公共函数前，请先阅读本文档，确保变更不破坏 `GUI.py → main.py → Task_*` 的调用链。

## 1. 项目概述

本项目用于在 Windows + MuMu 模拟器环境下，自动化完成《阴阳师》双账号日常，主要支持：

- 按窗口标题定位账号窗口（`master` / `slaves`），未找到时尝试按 `Setting.yml` 启动命令拉起模拟器；
- OpenCV 模板匹配识别界面元素，Win32 / pyautogui / pydirectinput 完成点击与按键；
- 任务级冷却与时间窗门禁，结果写回 `Last_times.yml`；
- 日志双写（控制台 + `logs/<年-月>/<日期>/`），GUI 实时展示；
- 当前任务域覆盖：签到收菜、结界养成、地域鬼王、寮三十与真蛇、结界突破、狩猎战/阴界、逢魔之时。

当前代码版本：GUI 标题标注 `v1.3.0`。

## 2. 顶层架构

```mermaid
flowchart LR
    GUI["GUI.py\nPyQt6 界面\n左侧 7 张任务卡片 + 右侧控制台"] --> WT["WorkerThread\nQThread"]
    WT -->|完整运行| FO["main.Full_operation\n按 TASK_REGISTRY 顺序编排"]
    WT -->|单击卡片| SO["main.Single_operation\n只跑指定任务"]
    WT -->|中断运行| STOP["Lib.request_stop\n置位停止请求"]
    STOP -.检查点抛 TaskStopped.-> FO
    STOP -.检查点抛 TaskStopped.-> SO
    REG["main.TASK_REGISTRY\n任务注册表（唯一事实源）"] --> GUI
    REG --> FO
    REG --> SO
    TM["dev/test_main.py\n开发调试入口（不入库）"] --> FO
    FO --> T1["MainTask_Signin"]
    FO --> T2["MainTask_Jiejieyangcheng"]
    FO --> T3["MainTask_Digui"]
    FO --> T4["FullTask_Thirty\n含真蛇"]
    FO --> T5["MainTask_JiejieFight"]
    FO --> T6["MainTask_Shouliezhan"]
    FO --> T7["MainTask_Fengmo"]
    SO --> T1 & T2 & T3 & T4 & T5 & T6 & T7
    T1 & T2 & T3 & T4 & T5 & T6 & T7 --> LIB["Lib.py\n识别/点击/界面/配置\nrun_accounts_task 统一流程"]
    LIB --> CFG["config/Setting.yml\nstate/Last_times.yml"]
    LIB --> PIC["pic/**\n模板图片"]
    FO --> LOG["logs/<YYYY-MM>/<YYYY-MM-DD>/console_output_*.log"]
    SO --> SLOG["logs/<YYYY-MM>/<YYYY-MM-DD>/single_<key>_*.log"]
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
│   ├── theme_manager.py           Fluent 主题初始化与深浅色切换
│   ├── prefs.py                   界面偏好读写（state/gui.json）
│   ├── settings_dialog.py         设置弹窗（主题 / 日志偏好 / 日志目录 / 调试截图）
│   ├── after_run_dialog.py        完整运行设置弹窗（关闭模拟器 / 电源动作）
│   ├── thirty_settings.py         寮三十配置读写层（纯逻辑，不依赖 Qt）
│   ├── thirty_dialog.py           寮三十设置弹窗（副本 / 次数 / 主副账号）
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
├── dev/                            本地调试脚本（已忽略，不参与交付）
│   ├── test.py                     单点验证模板 / 界面动作
│   ├── test_main.py                单独跑某个 MainTask_* 入口
│   └── README.md                   说明与注意事项（唯一入库的文件）
├── tools/                         开发辅助脚本（不参与打包）
│   ├── check_pics.py              模板图引用检查：失效引用 / 大小写不一致 / 死图
│   ├── clean_logs.py              旧日志清理（按年月分层，默认预览）
│   └── gen_pic_readme.py          生成 pic/README.md 索引
├── config/                        静态配置（默认忽略）
│   └── Setting.yml                启动项、结界突破、寮三十副本表
├── state/                         运行期状态（默认忽略，删除即恢复初始状态）
│   ├── Last_times.yml             各账号各任务上次完成时间
│   ├── Gui_state.yml              GUI 任务开关（是否参与完整运行，缺失默认全开）
│   └── gui.json                   界面偏好（主题 / 日志 / 完成动作）
├── pic/                           界面模板图（目录英文、文件名中文，详见 pic/README.md）
│   ├── common/                    公用元素（确定/关闭/获得奖励/退出标志等）
│   ├── courtyard/                 庭院主界面与功能入口
│   ├── signin/                    登录收菜（邮件/签到/福袋/纸人/礼包/友情点）
│   ├── guild/                     结界养成（寮工资/寄养/结界卡/育成/食盒酒壶）
│   ├── breakthrough/              结界突破
│   ├── digui/                     地域鬼王
│   ├── fengmo/                    逢魔之时
│   ├── hunt/                      狩猎战（麒麟/阴界之门）
│   ├── thirty/                    寮三十与真蛇
│   └── team/                      编队预设（部分由 Team_Preset 动态拼接）
├── tools/                         开发辅助脚本（不参与打包）
│   ├── check_pics.py              模板图引用检查
│   └── gen_pic_readme.py          生成 pic/README.md 索引
├── tests/                         pytest 用例（329 个，纯逻辑不碰窗口）
├── logs/<YYYY-MM>/<YYYY-MM-DD>/   运行日志（console_output_*.log / single_<key>_*.log）
├── logs/app_crash.log             崩溃日志（随 exe 目录）
└── __pycache__/ .venv/            环境产物
```

> 打包中间产物不再落在源码树：`build_exe.py` 用 `--workpath` 把它写到
> `.dsh-scratch/build-tmp/pyinstaller/`（已忽略，可随时整体删除）。
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
Tee 重定向 stdout → 控制台 + logs/<YYYY-MM>/<YYYY-MM-DD>/<日志前缀>_*.log + GUI 信号
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

`Full_operation` 在开始时读取 `state/Gui_state.yml` 的任务开关，关闭的任务打印 `SKIP- ----- 任务 <标题> 已在左侧关闭 跳过` 后跳过。

## 5. 入口函数说明

### 5.1 `GUI.py` 与 `ui/` 包

`GUI.py` 只作为入口：设置 Windows DPI（`QT_QPA_PLATFORM=windows:dpiawareness=1`）、安装全局异常钩子（写入 `logs/app_crash.log`）、创建 `QApplication` 并应用主题，最后转出 `ui/` 中的组件供脚本/测试使用。

> 崩溃日志的基目录按运行形态取：源码运行时是项目根，PyInstaller 打包后是 `GUI.exe` 所在目录
> （打包后 `__file__` 指向临时解压目录，进程退出即被清理，不能用来定位日志）。

界面实现位于 `ui/` 包，依赖方向固定为 `theme → icons → widgets → panels → window`，禁止反向引用：

| 模块 | 职责 |
| ---- | ---- |
| `ui/theme.py` | 设计 token：颜色、间距、圆角、字号；`COLOR_*` 为浅色取值、深色覆盖在 `_DARK_COLORS`，组件用 `theme.color()` / `light_color()` / `dark_color()` 取色 |
| `ui/icons.py` | `StatusIcon`（QPainter 绘制对勾/感叹号/播放三角）、`IconButton`（FluentIcon 图标按钮） |
| `ui/widgets.py` | `ToggleSwitch`（Fluent `SwitchButton` 包装）、`TaskRow`（Fluent `SimpleCardWidget`）、`CountdownDialog`（可取消的倒计时确认框） |
| `ui/panels.py` | `LeftPanel`（任务列表）、`RightPanel`（Fluent `TextEdit` 日志 + 进度条 + 「关闭模拟器 / 中断运行 / 完整运行 / 设置齿轮」按钮组） |
| `ui/theme_manager.py` | Fluent 主题初始化与深浅色切换（主题偏好存 `state/gui.json`） |
| `ui/prefs.py` | 界面偏好读写（`state/gui.json`：主题 / 日志自动滚动 / 日志字号 / 调试截图档位 / 两个完成动作开关） |
| `ui/settings_dialog.py` | 日志设置弹窗：主题、日志偏好、「打开日志目录」与调试截图档位下拉（日志区齿轮进入） |
| `ui/after_run_dialog.py` | 完整运行设置弹窗：只有「关闭模拟器」「让电脑睡眠」两个开关（按钮区齿轮进入） |
| `ui/thirty_settings.py` | 寮三十配置的**纯逻辑**读写：常量、7 项归一化、非法值回落、账号校验、YAML 保真写回。不依赖 Qt，可被 pytest 直接测 |
| `ui/thirty_dialog.py` | 「寮三十设置」弹窗：主副账号（单向约束，副账号自动跟随）+ 一周七天横排的副本/次数下拉（`thirty` 行齿轮进入） |
| `ui/jiejie_settings.py` | 结界养成配置的**纯逻辑**读写：按账号读 `优先结界卡` / `寄养优先级`、校验、YAML 保真写回；枚举与归一化复用 `Lib.JIEJIE_*`。不依赖 Qt |
| `ui/jiejie_dialog.py` | 「结界养成设置」弹窗：每个账号一张卡片（1 个放置下拉 + 横排一行的四个优先级下拉，单向互斥）（`jiejieyangcheng` 行齿轮进入） |
| `ui/window.py` | `WorkerThread`、`MainWindow`（Fluent 外壳 + 组装 + 线程调度 + 中断入口 + 完成动作触发 + `InfoBar` 结果提示） |

窗口外壳：`MainWindow` 继承 `qfluentwidgets.MSFluentWindow`，把双栏内容作为唯一子界面
`mainPage` 加入后**隐藏左侧导航**，因此保留参考项目的 Fluent 观感与无边框窗口，
信息架构仍然是「左侧任务列表 + 右侧日志控制台」两栏。

主体职责：

- 左侧 7 行任务（由 `main.TASK_REGISTRY` 驱动，与完整运行同顺序），右侧控制台与「关闭模拟器 + 中断运行 + 完整运行」按钮组；
- `WorkerThread` 持有 `task_key`：`None` 时调用 `main.Full_operation`，否则调用 `main.Single_operation`；返回值里的 `stopped` 会带进 `task_finished` 的 payload；
- 运行期间所有行的交互控件与「完整运行」「关闭模拟器」按钮一起禁用（`MainWindow.busy` 互斥），仅「中断运行」可用，并显示不确定进度条；
- 点「中断运行」→ `request_stop()` + 按钮变「中断中…」→ 线程在检查点退出 → `on_job_finished` 按 `stopped` 走「已中断」收尾（不报错、不统计完成数），界面回到待机；
- 点「关闭模拟器」→ `Lib.close_emulators()` 关闭受控模拟器窗口（详见 §5.6），控制台输出 `closed/missing/stuck` 摘要并用 `InfoBar` 提示；
- 结束后刷新行内「上次运行」时间与今日状态图标，并用 `InfoBar` 提示本次结果；
- 顶栏右侧提供深浅色主题快捷切换按钮，右侧日志区提供「清空 / 自动滚动 / 设置」工具条；
- 设置弹窗可调整主题（浅色 / 深色 / 跟随系统）、日志自动滚动与字号、调试截图档位，并提供「打开日志目录」入口；
  写盘失败时弹「保存失败」提示并**不**应用改动（不切主题、不同步日志区），避免界面与磁盘状态对不上；
- 界面偏好写入 `state/gui.json`（`ui/prefs.py` 自管），任务参数与任务开关仍分别写在 `config/Setting.yml` / `state/Gui_state.yml`；
- 深浅色主题各有独立配色：文字类控件用 Fluent 标签（浅色 / 深色两套文字色由库自动切换），
  自绘状态图标、日志行着色与轮廓按钮在切换后按当前主题重新取色；主强调色是比原 `#007BFF`
  深一档的蓝（浅色 `#0d6bc2`，深色 `#3d8bd6`），避免浅色下过艳、深色下发灰看不清；
  危险色（`COLOR_DANGER` 系列）浅色 `#c42b1c`、深色柔和浅红 `#ff8b82`，与 `COLOR_LOG_ERROR` 同取值。

单行结构（从左到右）：

| 区域 | 控件 | 说明 |
| ---- | ---- | ---- |
| 今日状态 | `StatusIcon` | 今日已完成 → 绿色对勾；今日未完成 → 橙色 `!`；运行中 → 蓝色播放三角（均为 QPainter 绘制，无底色圆圈；深色主题下自动换成更亮的绿 / 橙 / 蓝） |
| 任务信息 | 名称 + 「上次运行 MM-DD HH:MM」 | 时间取该任务所有账号、所有状态键中的最新值 |
| 配置 | `IconButton(kind="gear")` | `FluentIcon.SETTING`；**按任务区分**：`thirty` 行打开「寮三十设置」弹窗（§5.8）、`jiejieyangcheng` 行打开「结界养成设置」弹窗（§5.9），其余 5 行仍是占位（弹「配置功能暂未开放」，不写盘）。提示语由 `ui/widgets.config_tooltip()` 按任务给出（映射表 `CONFIG_TOOLTIPS`） |
| 单跑 | `IconButton(kind="play")` | `FluentIcon.PLAY`；点击只运行该任务（等价于 `Single_operation`） |
| 开关 | `ToggleSwitch` | Fluent `SwitchButton`（不显示 On/Off 文案）；开 → 参与「完整运行」；关 → 完整运行时跳过、整行半透明，并写入 `state/Gui_state.yml` |

图标：齿轮与运行按钮使用 `FluentIcon`；今日状态（对勾/感叹号/播放三角）用 `QPainter` 绘制，保证任意 DPI 下清晰。右上「完整运行」为**主色**轮廓按钮（主色描边 + 主色文字，悬停同色系浅底），其左侧「中断运行」为**次要色**轮廓按钮（带 `FluentIcon.PAUSE`），再左侧「关闭模拟器」为**危险色**轮廓按钮（红色描边 + 红色文字，带 `FluentIcon.POWER_BUTTON`），都不使用实心主色块；轮廓按钮用 Fluent 的「浅色 / 深色两套自定义样式」注册，主题切换后不会退回默认实心按钮。

按钮区从左到右：**关闭模拟器 / 中断运行 / 完整运行 / 设置齿轮**。前三个按钮样式刻意拉开层次——完整运行是主色（主动作），关闭模拟器是危险色红（破坏性），中断运行是次要色灰（常规停止）。红色取值 `COLOR_DANGER` 浅色为 `#c42b1c`、深色为柔和浅红 `#ff8b82`，与 `COLOR_LOG_ERROR` 保持一致，避免深色下刺眼。末尾齿轮与日志区顶部那个同款（默认尺寸，不放大），但**走独立信号**：日志齿轮进「设置」（主题 / 日志），按钮区齿轮进「完整运行设置」（两个完成动作），两个弹窗不混放无关项，进错了页面一眼能看出。

交互约定：

| 操作 | 行为 |
| ---- | ---- |
| 点击行内 ▶ | 只运行该行对应的顶层任务（对 `Last_times.yml` 全部账号），冷却与时间窗照旧生效 |
| 点击行内齿轮 | `thirty` 行打开「寮三十设置」（§5.8）、`jiejieyangcheng` 行打开「结界养成设置」（§5.9），保存后写 `config/Setting.yml` 并在控制台打 `INFO-`；其余 5 行弹占位提示，不写任何配置 |
| 拨动行内开关 | 写入 `state/Gui_state.yml`；关闭时该行灰化，且在「完整运行」中被跳过 |
| 点击「完整运行」 | 按 `TASK_REGISTRY` 顺序执行**开关开启**的任务 |
| 点击「中断运行」 | 立即置位停止请求；任务在下一个检查点抛 `TaskStopped` 退出，界面回到待机。**不做断点续跑**，下次运行即新的一轮 |
| 点击「关闭模拟器」 | 关闭 `Setting.yml.启动项` 里登记账号对应的模拟器窗口（详见 §5.6）。**不弹二次确认**，关闭后控制台输出摘要并用 `InfoBar` 提示 |
| 点击按钮区齿轮 | 打开「完整运行设置」：只有两个完成动作开关（详见 §5.7）。写盘失败会明确提示 |
| 点击日志区齿轮 | 打开「设置」：主题、日志自动滚动、日志字号、打开日志目录（与按钮区齿轮各管一摊） |
| 运行中再次点击 | 被 `busy` 互斥拒绝，不会启动第二个线程 |
| 运行中关闭窗口 | 弹确认框；确认后同样走 `request_stop()` 并等待线程收尾 |

「中断运行」按钮位于「完整运行」左侧，为次要色轮廓按钮，**仅运行中可点**；点击后按钮变「中断中…」并禁用，防止连点。中断不处理游戏内状态（不拉回庭院、不做收尾操作），任务停在哪就是哪。

「关闭模拟器」按钮位于「中断运行」左侧，为危险色轮廓按钮，**仅空闲时可点**（运行中禁用）——正在抢占键鼠时关窗口会让任务在半途失去目标，后续每一步都必然失败。它不复用 `Find_windows`（那个函数找不到窗口会去启动游戏），改用只读枚举，详见 §5.6。

注意：`ui/window.py` 与 `Lib.py` 会在运行时 `import runtime`（`GUI.py` 本身不直接引入）。该文件属于运行期本地模块，**已被 `.gitignore` 忽略、不在版本库中**；本地运行前需在项目根目录自备，至少包含：

```python
stop_thread = False
```

### 5.2 `main.py`

调用形式：

```python
Full_operation(console_signal=None)              # 完整运行（按开关跳过已关闭任务）
Single_operation(task_key, console_signal=None)  # 单任务运行

# 返回值（PR5 起）
# Full_operation  → {"stopped": bool, "executed": int, "skipped": int}
# Single_operation → {"key": str, "ok": bool, "reason": str|None, "stopped": bool}
# 被中断时 stopped 为 True；单任务的 ok 随之为 False（这是正常收尾，不是异常）
```

职责：

- 维护 `TASK_REGISTRY`：`TaskEntry(key, title, desc, entry, lasttime_keys, today_keys)`，是「左侧行列表 / 完整运行顺序 / GUI 状态键」的唯一事实源；
- 创建日志文件：完整运行为 `logs/<YYYY-MM>/<YYYY-MM-DD>/console_output_<时间戳>.log`，单任务为 `logs/<YYYY-MM>/<YYYY-MM-DD>/single_<key>_<时间戳>.log`；
- 用 `Tee` 把 stdout 同时写到原控制台、日志文件和 GUI 信号；
- 完整运行按注册表顺序编排并按任务开关跳过，单任务运行只调用一项且**不看开关**；
- 捕获 `TaskStopped` 统一收尾（打印 `QUIT-` 与中断结束行），任务之间也会 `check_stop()`，因此上一步结束后按下的中断同样生效；
- `_log_stream` 在 `finally` 中先恢复 `sys.stdout` 再尽力冲刷，避免无控制台环境（打包版 `GUI.exe` / `pythonw`）下 `sys.stdout is None` 造成收尾异常。

中断相关名称从 `main` 重新导出（`TaskStopped` / `request_stop` / `reset_stop` / `stop_requested` / `check_stop`），GUI 层只依赖 `main`。

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
| `read_task_switches()` | 读取 `state/Gui_state.yml` 的任务开关，缺失默认全开，只读不建文件 |
| `is_task_enabled(key, switches=None)` / `enabled_task_keys(switches=None)` | 判断/列出参与完整运行的任务 |
| `set_task_switch(key, enabled)` | 写入单个任务开关，成功返回 `True` |

### 5.3 任务模块入口

完整流程 `Full_operation` 当前顺序（即 `TASK_REGISTRY` 顺序；单任务运行复用同一入口）：

| 顺序 | 注册表 key | 行标题 | 入口 | 模块 | 今日判定键（`today_keys`） | 说明 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| 1 | `signin` | 登录收菜 | `MainTask_Signin()` | `Task_SignIn.py` | 邮件领取 / 每日一签 / 福袋纸人 / 免费礼包 / 送友情点（全部） | 邮件、每日一签、福袋、纸人、免费礼包、友情点 |
| 2 | `jiejieyangcheng` | 结界养成 | `MainTask_Jiejieyangcheng()` | `Task_Jiejieyangcheng.py` | 结界养成 | 寮界面：工资/体力、寄养、结界卡、白达摩育成、食盒酒壶；放置顺序与寄养优先级**按账号**读 `Setting.yml`（§5.9） |
| 3 | `digui` | 地域鬼王 | `MainTask_Digui()` | `Task_Digui.py` | 地域鬼王 | 经探索→六道进入地鬼，时间窗 12:00–23:50，当日冷却 |
| 4 | `thirty` | 寮三十 / 真蛇 | `FullTask_Thirty()` | `Task_Thirty.py` | 寮三十（真蛇为周更，不参与今日判定） | 寮三十协作刷本 + 非周末真蛇（周冷却） |
| 5 | `jiejiefight` | 结界突破 | `MainTask_JiejieFight()` | `Task_JiejieFight.py` | 结界突破 | 结界突破，时间窗 7:00–23:00，1 小时冷却 |
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
| 编排 | `run_accounts_task` | **单账号任务固定流程**：分隔线 → 时间窗 → 遍历账号 → 取上次时间 → 准入判断 → 执行业务 → 写回时间。参数 `(name, ready, work, window=None, write_back=True)`；`ready=None` 表示硬跑（不读上次时间、不判断冷却与时间窗） |
| 编排 | `run_shared_task` | **双账号协作任务固定流程**：两账号一起判定（任一未完成即执行），业务只执行一次，成功后主副账号双写。参数 `(name, pair, work, window=None)` |
| 编排 | `ready_daily` / `ready_weekly` / `ready_after(hours)` | 准入策略：当日冷却 / 周冷却 / 距上次满 N 小时 |
| 编排 | `skip_text` | 按准入策略生成 SKIP 日志文案 |
| 编排 | `write_task_time` / `write_task_time_pair` | 写回单个账号 / 双账号的完成时间 |
| 中断 | `TaskStopped` / `request_stop` / `reset_stop` / `stop_requested` / `check_stop` / `_sleep_with_stop` | 中断信号与检查点：`check_stop` 在已请求时抛 `TaskStopped`；`_sleep_with_stop` 按 0.2s 切片睡眠 |
| 系统动作 | `find_windows_silent` | **只读**枚举可见窗口，找不到返回 `None`。与 `Find_windows` 的唯一区别是**不启动游戏**，关闭模拟器只能用这个 |
| 系统动作 | `controlled_accounts` / `_launch_commands` | 受控账号 = `Setting.yml.启动项` 的 key；同时取出各账号的启动命令 |
| 系统动作 | `parse_instance_number` | 从启动命令解析 `-v N` 的实例号，解析失败返回 `None` |
| 系统动作 | `find_mumu_manager` | 定位 `MuMuManager.exe`：`模拟器.MuMuManager` 显式指定 → 从启动命令推导目录后探测「同目录 / 上一级 / `shell/`」→ 都没有返回 `None`。**不写死任何安装路径** |
| 系统动作 | `shutdown_via_manager` / `_run_manager` | 按实例号关机；两种 `control` 子命令顺序都试（`control -v N shutdown` / `control shutdown -v N`），解析 JSON 的 `errcode` 判断成功 |
| 系统动作 | `close_emulators` | 关闭受控模拟器：MuMuManager 关机 → 等待 → 复查 → 仍在的逐个 `WM_CLOSE`。返回 `{"closed", "missing", "stuck"}` 三分类 |

#### 任务入口编写约定（PR2 起）

单账号任务的入口只需声明「这个任务是什么」，不再手写控制流与日志：

```python
def MainTask_Fengmo():
    run_accounts_task(
        "逢魔之时", ready_daily,
        work=lambda Account: Task_Fengmo(Find_windows(Account), Account),
        window=(time(17, 0), time(21, 50)),
    )
```

- 任务名同时是 `Last_times.yml` 的任务键
- 日志文案（开始/结束分隔线、读取上次时间、成功/失败/SKIP）全部由任务名与时间窗自动生成
- 需要「硬跑」（跳过冷却与时间窗）时传 `ready=None`
- 不写回时间的任务（如纸人奖励）传 `write_back=False`
- 双账号协作任务用 `run_shared_task`
- 分隔线统一为 84 字符（`Lib.TASK_LINE_WIDTH`）

### 5.5 中断机制（协作式）

GUI 的「中断运行」走**协作式中断**，不用 `QThread.terminate()`（会留下键鼠、焦点和半写配置文件的状态）：

1. `MainWindow.interrupt_job()` 调 `Lib.request_stop()`，同时置 `config.stop_thread = True`；
2. `Lib` 在公共原语的固定检查点调 `check_stop()`，已请求则抛 `TaskStopped`；
3. 异常一路上抛（**任务层禁止捕获 `TaskStopped`**），由 `main.Full_operation` / `main.Single_operation` 统一收尾；
4. 收尾打印 `QUIT-` 与「完整运行被中断 / 单任务运行被中断」结束行，返回值带 `stopped=True`；
5. `WorkerThread` 把 `stopped` 带进 `task_finished` payload，GUI 按「已中断」复位到待机。

检查点分布（`Lib.py` 内，因此 8 个 `Task_*.py` 无需改动）：

| 位置 | 作用 |
| ---- | ---- |
| `_sleep_with_stop` | 所有等待/点击后延时的睡眠改走它，最长每 0.2 s 一次检查，暂停响应上限约 0.2 s |
| `Match_model` / `Find_in_windows_Matchs` / `Find_in_windows_Range` / `Find_multiple_in_windows_Matchs` / `Find_in_screen_Matchs` / `Find_Click_windows` | 截图匹配前后检查，避免大图匹配期间不可中断 |
| `Move_to_range`（点击前）/ `Click` | 中断后不再多移动或多点一下 |
| `Itface_Host` 状态机循环 / `Itface_Quit` / `Itface_scroll` / `Itface_guild` / `Itface_explore` / `Team_Preset` | 界面跳转循环每轮检查 |
| `Log_in` | 25 s 启动等待与 100 轮适龄提示循环改走切片睡眠 |

约定：**`Lib.py` 内除 `_sleep_with_stop` 外不应再出现裸 `time.sleep`**；长等待一律走 `_sleep_with_stop`，否则会卡住中断响应。

中断**不做**断点续跑：下次「完整运行」就是新的一轮，已完成任务靠 `Last_times.yml` 冷却/时间窗自动跳过，被中断的任务会重跑。中断也不处理游戏内状态（不拉回庭院）。

模板匹配阈值约定：`Match_model` 使用 `cv2.TM_SQDIFF_NORMED`，**数值越小越相似**；`min_val > Threshold` 视为未命中。任务代码中的阈值多在 `0.01～0.07`。

点击坐标约定：匹配框 `[(Left_up), (Right_down)]` 的中心 1/4～3/4 区域内随机点；全局坐标特例见 `Itface_scroll`（卷轴约 `((1780, 970), (1910, 1120))`）。

### 5.6 关闭模拟器（破坏性动作）

GUI「关闭模拟器」按钮走 `Lib.close_emulators()`，与任务流程**完全解耦**：不在任务线程里跑、不依赖中断机制、不参与 `Full_operation` 编排。

**受控范围**：只关 `config/Setting.yml` 里 `启动项` 登记账号（当前 `master` / `slaves`）对应标题的窗口。用户手动开的、标题不匹配任何账号的窗口**一律不碰**。这条边界是「受程序掌握」的唯一判定依据。

**为什么必须另写枚举**：`Find_windows` 找不到窗口时会调 `Log_in` 启动游戏再递归重找。关闭场景一旦复用它，"关一个本来没开的模拟器" 就变成 "先启动、等 25 秒、再关闭"。因此新增 `find_windows_silent`——同样的标题子串匹配，但**只读**，找不到返回 `None`。

**关闭手段（两级降级）**：

| 级别 | 手段 | 条件 |
| ---- | ---- | ---- |
| ① | `MuMuManager.exe control -v <实例号> shutdown` | 能找到 `MuMuManager.exe` 且实例号可解析 |
| ② | `PostMessage(hwnd, WM_CLOSE, 0, 0)` | ①不可用或失败 |

**`MuMuManager.exe` 不写死路径**——它是第三方软件，装在哪、换盘符、升级换目录都可能变，而且 `Setting.yml.启动项` 里已经是权威来源，再存一份就是两个事实源。定位规则：

1. `Setting.yml` 的 `模拟器.MuMuManager`（**可选键**，用户想显式指定时的逃生口）；
2. 否则从启动命令里的 `.exe` 路径取所在目录，依次探测：**同目录** → 上一级 → `shell/` 子目录；
3. 都不存在 → 跳过 ①，直接走 ②（功能不失效）。

实例号取自同一条启动命令的 `-v N`。不同 MuMu 大版本的 `control` 子命令顺序不同，代码里**两种顺序都试**（`control -v N shutdown` / `control shutdown -v N`），看 `errcode` 判断，都失败才降级。

**流程**：关闭前先枚举记录哪些账号在跑 → MuMuManager 关机 → 等 2 秒 → 复查 → 仍在的逐个发 `WM_CLOSE` → 再复查分类。返回 `{"closed": [...], "missing": [...], "stuck": [...]}`，GUI 据此拼控制台摘要与 `InfoBar` 提示。

**约束**：

- 按钮**仅空闲时可点**，运行中禁用（正在抢占键鼠时关窗口会让任务在半途失去目标）；
- 点击**不弹二次确认**，直接执行（ToolTip 里写明「未保存的进度会丢失」）；
- 关闭过程中的等待走 `_sleep_with_stop`，不写裸 `time.sleep`；
- 关闭失败不抛异常到 GUI，返回分类结果由 `InfoBar` 提示。

### 5.7 完整运行完成后的动作

按钮区的设置齿轮打开 `ui/after_run_dialog.py` 的 `AfterRunDialog`，里面是一个开关 + 一个下拉框，都存在 `state/gui.json`：

| 键 | 默认 | 含义 |
| ---- | ---- | ---- |
| `after_run_close_emulator` | `False` | 完整运行结束后关闭受控模拟器窗口 |
| `after_run_sleep` | `False` | **是否启用**结束后的电源动作 |
| `after_run_power` | `"sleep"` | 启用时执行哪个：`logoff` / `sleep` / `shutdown` |

**为什么是两个键而不是一个**：开关表达「要不要」，下拉框表达「要哪个」。这样老配置（只有 `after_run_sleep`）升级后新键缺失回落 `"sleep"`，**行为零变化、无需迁移**；而且「不执行」这个状态由开关表达，`after_run_power` 就不必塞一个 `"none"`。

界面行为：开关关闭时下拉框 `setEnabled(False)` 灰化（`checkedChanged` 直接连 `setEnabled`），直观表达「这个动作不启用」。标签是「电源动作」而不是「让电脑睡眠」——后者在选到注销/关机时会自相矛盾。

**三种动作的差别**（决定了它们各自适合什么场景）：

| 动作 | 实现 | 程序状态 | 内核 | 远程接管 |
| ---- | ---- | ---- | ---- | ---- |
| 注销 `logoff` | `ExitWindowsEx(EWX_LOGOFF)` | 本进程结束 | **继续运行** | ✅ 可以 |
| 睡眠 `sleep` | `powrprof.SetSuspendState(False, ...)` | 保留在内存 | 挂起 | ❌ 不行 |
| 关机 `shutdown` | `ExitWindowsEx(EWX_POWEROFF)` | 全部结束 | 停止 | ❌ 不行 |

**注销为什么能远程接管**：注销只结束当前用户的会话（Session 1+），Session 0 的系统服务继续运行。远程控制软件（如 UU 远程的 `GameViewerService`）以服务形式常驻，所以注销后仍能接受连接，输入密码即可回到桌面。睡眠/关机时整个内核挂起或停止，服务自然不存在。

**触发条件（严格）**：`task_key is None` **且** `payload["ok"]` **且** `not payload["stopped"]`。即只有「完整运行 + 成功 + 未中断」才触发；**单跑、中断、异常一律不触发**。全部任务被冷却 SKIP 也算成功完成，**仍会触发**——语义是「完整运行这一轮走完了」，而不是「至少干成了一件事」。

**执行时机**：`QThread.finished` → `on_thread_finished()`，**不是** `task_finished`。因为 `task_finished` 在 `WorkerThread.run()` 内部就发出，此时 `main._log_stream` 的 `finally` 还没执行，日志文件未关；在那个时点睡眠会把最后几行日志截掉。

**执行顺序**：

```
on_job_finished（成功分支）→ 打 _pending_after_run 标记
  ↓
QThread.finished → on_thread_finished → _run_after_actions()
  ↓ 读 gui.json：after_run_close_emulator + after_run_sleep
  ↓ 开关关闭时 power 记为 "none"
  ├ 都关 → 直接返回，行为与没有该功能时完全一致
  └ 至少一个开 → CountdownDialog（10 秒，可取消）
        ↓ 取消 → 日志记「完成动作：已取消」
        ↓ 确认/倒计时归零 → processEvents() 让弹窗淡出动画走完
              ↓ 关模拟器（CloseEmulatorThread 后台跑，silent=True 不弹 InfoBar）
              ↓ 后台完成回调 → QTimer 3 秒
              ↓ 电源动作（Lib.power_action：logoff / sleep / shutdown）
```

3 秒间隔是给 MuMu 回收虚拟机的时间：它持有系统唤醒请求时系统睡不下去，所以顺序必须是**先关模拟器再睡眠**。关模拟器失败**不阻断**电源动作——用户要的是「跑完就睡」，失败只写日志。

**注销/关机前必须 `processEvents()`**：这两个动作会立刻结束本进程，如果日志行还堆在事件队列里没渲染，用户就永远看不到「完成动作：正在请求注销」这一行。

**关闭模拟器必须跑在后台线程**（`CloseEmulatorThread`）：`MuMuManager control ... shutdown` 会同步阻塞到虚拟机真正关机才返回，本机实测约 **4.1 秒**（对照：`info` 只要 0.1 秒，说明是 shutdown 本身在等）。放在主线程会引发两个可见问题：

1. 界面完全冻住，日志不刷新；
2. 倒计时弹窗留下**半透明虚影**——`MaskDialogBase.done()` 不是立即关闭，而是先跑 100ms 的透明度淡出动画、动画 `finished` 才调 `QDialog.done()`。弹窗刚淡出第一帧主线程就被 `subprocess.run` 占死，Qt 无法重绘，窗口停在约 0.9 透明度的中间帧；等 4 秒后线程解放，动画补完才真正消失。

因此 `dialog.exec()` 返回后要补一次 `QApplication.processEvents()` 让淡出动画走完，再启动后台线程。

> 信号名用 `close_finished` 而不是 `finished`：`QThread` 自己已有同名信号，重名会覆盖基类的线程结束通知，导致线程对象无法正确释放。

**电源动作实现**：三种动作统一走 `Lib.power_action(action)`，共用 `_enable_shutdown_privilege()`：

- `logoff` → `user32.ExitWindowsEx(EWX_LOGOFF, 0)`；
- `sleep` → `powrprof.SetSuspendState(False, False, False)`，第一个参数 `False` 表示**睡眠（S3）而非休眠（S4）**；
- `shutdown` → `user32.ExitWindowsEx(EWX_POWEROFF, 0)`。用 `EWX_POWEROFF` 而不是 `EWX_SHUTDOWN`：前者真正切断电源（配合 ATX 电源），后者只做到「可以安全断电」的状态。

`Lib.sleep_system()` 保留（早期只有睡眠一种动作，现有测试仍在引用），逻辑与 `power_action("sleep")` 等价。

- **不加 `EWX_FORCE` / `EWX_FORCEIFHUNG`**：强制标志会杀掉所有未保存的工作（包括用户开着的文档）。此时模拟器已关，正常不会有阻拦者；万一有程序阻拦，系统会弹确认框让用户自己决定；
- **不用** `rundll32 powrprof.dll,SetSuspendState 0,1,0`：第二个参数为 1 时，开了休眠的机器会变成休眠而不是睡眠，且返回值不可检测；
- 调用前必须 `Lib._enable_shutdown_privilege()` 启用 `SeShutdownPrivilege`，否则静默失败（返回 0 无异常）；
- **坑**：`GetCurrentProcess` / `OpenProcessToken` 必须显式声明 `restype` / `argtypes`，否则伪句柄 `-1` 被截断成 `0xFFFFFFFF`，`OpenProcessToken` 报错误 6（无效句柄）；
- `AdjustTokenPrivileges` 成功但未授予权限时只置 `ERROR_NOT_ALL_ASSIGNED`，必须单独检查；
- 动作失败时用 `InfoBar.error` 明确提示（按动作名区分「注销失败」/「睡眠失败」/「关机失败」），不静默什么都不发生。

**倒计时对话框**：`ui/widgets.py` 的 `CountdownDialog(MessageBoxBase)`，每秒刷新剩余秒数，归零自动 `accept()`。为什么不用 `InfoBar`：它没有「倒计时结束回调 + 可取消」的组合能力，关闭 InfoBar 也无法可靠地通知调用方。

### 5.8 寮三十配置弹窗（行内齿轮）

`thirty` 这一行的齿轮打开「寮三十设置」弹窗（另一个已接入配置界面的是 `jiejieyangcheng` 行，见 §5.9），其余 5 行仍是占位提示。入口链路：

```
TaskRow.config_button（ui/widgets.py）
  → config_clicked(str) → LeftPanel.task_config_clicked → MainWindow.on_task_config(task_key)
      → CONFIG_DIALOGS["thirty"] → ThirtySettingsDialog(self).exec()
```

`CONFIG_DIALOGS` 是 `ui/window.py` 里的一张两行小表，只登记「哪个任务有配置界面」，**不复制 `TASK_REGISTRY`**（任务列表仍然只有一个事实源）。

保存成功后主窗口写的那行控制台提示也**不再写死**：从弹窗类的 `SAVED_MESSAGE` 取（`getattr(dialog_class, "SAVED_MESSAGE", 兜底文案)`），否则接入第二个任务后仍会报「寮三十设置已保存」。

**只管一件事**：`config/Setting.yml` 的 `寮三十.主账号` / `副账号` / `副本` / `次数`。界面偏好（`state/gui.json`）与任务开关（`state/Gui_state.yml`）都不在这里，四个入口（行内齿轮 / 日志区齿轮 / 按钮区齿轮 / 行内开关）各管一摊。

| 维度 | 可选值 | 依据 |
| ---- | ---- | ---- |
| 副本 | `魂虚` / `魂王` / `魂海` / `日蚀` | `Task_Thirty.py` 的 `match Fuben` 只有这 4 个分支 |
| 次数 | `0` / `1` / `30` / `50` | `Times == 0` 提前返回；`match Times` 只认 1 / 30 / 50 |
| 主副账号 | `启动项` 的 key | `Lib.Log_in` 用 `config["启动项"][title]` 取启动命令，用不存在的名字会 KeyError |

**其它数字为什么不给**：`match Times` 没有默认分支，填 `7` 会静默跳过「小纸人计数」这一步，流程随后失效——所以只做枚举下拉，不做自由输入。

**布局**：主副账号一行（两个 `ComboBox` + 右侧角色提示）+ 表头周一～周日 7 列 + 「副本」「次数」两行各 7 个下拉。弹窗自然尺寸约 836×366（`widget.setMinimumWidth(800)`）。

**主副账号约束是单向的**：主账号可任意选，副账号只避开「主账号当前值」；撞车时**只让副账号**自动换成「列表里第一个不是主账号的账号」，主账号不动。副账号右侧有一句 `主账号作为打手，副账号作为司机`（`CaptionLabel` + 深浅两套文字色）——两个账号在游戏里分工确实不同：副账号开房（选副本 / 创建队伍 / 邀请），主账号进队开打（加入队伍 / 开加成 / 自动战斗），对着 `Task_Thirty.py` 的状态机核过。

> **为什么不能双向灰化**：双向是「每个下拉都禁用对方当前选中项」。只有两个账号时，主框只剩自己、副框只剩自己，两边都被锁死——**主副互换这个最常见的操作反而做不了**。早期版本就是这么写的，用例只守住了「不会撞车」，没守住「能互换」，所以漏了。现在 `tests/test_thirty_dialog.py` 里有 `test_主账号下拉全部可选` 和 `test_两个账号能互换主副` 两条直接守住它。

`_syncing` 标志防递归（程序化 `setCurrentText` 会再次触发 `currentIndexChanged`）。`启动项` 只有一个账号时无处可让，主副相同、弹窗照常可保存（`save_thirty_settings` 对单账号已放行）。

**落盘在 `validate()` 里**：`MessageBoxBase.__onYesButtonClicked` 是 `if self.validate(): self.accept()`，所以写盘失败只需返回 `False`，弹窗自然不关闭，用户可以重试或去修文件。

**读写层单独成模块**（`ui/thirty_settings.py`，不依赖 Qt）：`MessageBoxBase` 没有 parent 会崩（`parent.width()` AttributeError），纯逻辑留在弹窗里就没法脱离 GUI 测试。

**YAML 保真（三个坑，都必须绕开 `Lib.read_config` / `Lib.write_config`）**：

| 现象 | 真正的原因 | 对策 |
| ---- | ---- | ---- |
| `"master"` 的引号没了 | `Lib.read_config` 不设 `preserve_quotes`，**读**的时候就丢了 | 自建 `YAML()`，`preserve_quotes=True` |
| 长启动命令被折成两行 | `Lib.write_config` 不设 `width`（默认 80） | 自建 `YAML()`，`width=4096` |
| `副本: [...]` 变成每项一行 | **整体替换列表对象**（与哪个 writer 无关） | 写回时**原地切片** `sec["副本"][:] = [...]` |

新建 `寮三十` 段时没有可复用的列表对象，要显式 flow：`CommentedSeq(values)` + `.fa.set_flow_style()`，否则会写成块状多行。

**容错**：配置缺失 / 损坏 / 长度不是 7 / 单项取值非法 / 账号名不在 `启动项` 里，一律回落默认值并让弹窗照常打开，同时把回落原因用小字列在弹窗里（不静默改用户配置）。**配置解析失败时拒绝写入**——写回等于把用户原内容抹掉。

**一个已知的既有瑕疵（本次不改）**：某天次数设 `0` 时 `Task_Liao_30` 返回 `0`，`run_shared_task` 会判为失败、打印「执行过程中出现错误 中断任务」且不写回完成时间。日志看起来像报错，但行为本身是「当天不刷」，属于既有语义问题，单独议。

### 5.9 结界养成配置弹窗（行内齿轮）

`jiejieyangcheng` 行的齿轮打开「结界养成设置」。与 §5.8 同构（同样的 `CONFIG_DIALOGS` 登记、同样的「落盘在 `validate()` 里」、同样的读写层与 Qt 分离），差别只在于**配置是按账号分组的**，以及四级下拉的单向互斥。

**只管两件事**，都写在 `config/Setting.yml` 的 `结界养成.<账号>` 下：

| 键 | 取值 | 现状默认 |
| ---- | ---- | ---- |
| `优先结界卡` | `太鼓` / `斗鱼`（只有两项，**没有「不放置」第三态**） | `太鼓`（即改动前「优先太鼓、耗尽再斗鱼」） |
| `寄养优先级` | `六星太鼓` / `六星斗鱼` / `五星太鼓` / `五星斗鱼` 的排列，恰好 4 项，越左越优先 | `[六星太鼓, 六星斗鱼, 五星太鼓, 五星斗鱼]`（改动前写死的顺序） |

> 「高星」在代码里一直就是**五星**（模板图 `pic/guild/五星太鼓.png` / `五星斗鱼.png`），所以枚举里直接写 `五星`，不引入「高星」这个词，避免配置值与模板文件名对不上。

**为什么账号分组而不是主/副两个键**：`结界突破` 段早就是 `<账号> -> {参数}` 的形状（`Task_JiejieFight.py` 读 `config["结界突破"][Account]["退出次数"]`），结界养成照抄同一形状最省事；而「哪个账号是主、哪个是副」已经从 `寮三十.主账号/副账号` 知道了，再存一份就是第二个事实源。弹窗只在**标题**上把角色读出来做装饰（`master（主）`），不新增配置键、不参与落盘。

**运行时怎么取**：`MainTask_Jiejieyangcheng` 把 `Account` 传进业务层，`Jiejieyangcheng(current_state, Hwnd, Account)` 在入口用 `Lib.load_jiejie_settings(Account)` 读一次，把 `card_order` 与 `priority_cards` 往下传给 `Jiejieka` / `Yucheng`。**不能各子函数各读一遍**——`Jiejieka` 与 `Yucheng` 在状态机里各被调用两次，各读一遍会在用户中途改配置时前后不一致。

| 改动点 | 改动前 | 改动后 |
| ---- | ---- | ---- |
| `Jiejieka(Hwnd, card_order)` | 太鼓分支写死在前，失败再走斗鱼 | 按 `Lib.jiejie_card_order(优先结界卡)` 的顺序循环，页签路径取自 `Lib.JIEJIE_CARD_LIST_PICS` |
| `Yucheng(current_state, Hwnd, priority_cards)` | `card_handlers` 字典的字面顺序 | 按 `Lib.jiejie_priority_cards(寄养优先级)` 遍历，命中即 `break` |
| `Jiyang(current_state, Hwnd, priority_cards)` | 按优先级逐个调 `Jiyang`，每次重扫全表 | 一趟扫完，按档位记最优，再按优先级裁决（§5.9.1） |

#### 5.9.1 寄养选卡：模板只做候选探测，收益数字定胜负

模板匹配无法区分「六星太鼓 67」与「六星太鼓 76」——那是**同一张卡面**，列表小图上完全一样；同理五星与四星太鼓在整图匹配上差异极小，靠阈值分不开。所以选卡改成**两层**：

```
模板匹配  →  这一行是哪个档位的结界卡？（召回，可以宽松）
点开读数  →  是多少？（精确，数字说了算）
```

**收益表**（6 小时寄养，含 1.4 倍加成，实测）：

| 类型 | 星级 | 每小时 | 显示值 |
| ---- | ---- | ------ | ------ |
| 太鼓 | 六星 | 9 勾 | 76 |
| 太鼓 | 六星 | 8 勾 | 67 |
| 太鼓 | 五星 | 8 勾 | 67 |
| 太鼓 | 五星 | 7 勾 | 59 |
| 斗鱼 | 六星 | 18 体 | 151 |
| 斗鱼 | 六星 | 16 体 | 134 |
| 斗鱼 | 六星 | 14 体 | 118 |
| 斗鱼 | 五星 | 16 体 | 134 |
| 斗鱼 | 五星 | 15 体 | 126 |
| 斗鱼 | 五星 | 14 体 | 118 |
| 斗鱼 | 五星 | 13 体 | 109 |
| 斗鱼 | 五星 | 12 体 | 101 |

由此得到**每档的上限与下限**，这是后面所有提前停止判据的依据：

| 档位 | 上限 | 下限 |
| ---- | ---- | ---- |
| 六星太鼓 | 76 | 67 |
| 五星太鼓 | 67 | 59 |
| 六星斗鱼 | 151 | 118 |
| 五星斗鱼 | 134 | 101 |

**跨类型不互比**：勾玉与体力单位不同，无法比大小。所以 `寄养优先级` 的顺序是**唯一裁决者**——「六星太鼓 67」胜过「六星斗鱼 151」，因为前者排在前面，不是因为 151 更大。

**扫描策略是一趟，不是四趟**：四张模板可以吃同一帧截图，扫四趟等于把同样的滚动与截图做四遍。一屏内四档一起找、按 y 从上到下依次点开、读数、按档位记最优。

**一行只能出一个类型：用 `Match_models_rows` 而不是逐张模板各找各的**。四张结界卡模板共用同一个金色托盘与同一排橙色星点（太鼓是橙鼓、斗鱼是蓝鱼，但托盘与星点完全同款），尺寸又各不相同（`六星太鼓` 108×102、`六星斗鱼` 120×126、`五星太鼓` 112×114、`五星斗鱼` 110×124），滑窗位置天然不对齐。早先按「每张模板各自跑一遍 `Match_models_in_image_all`」收集候选，涂黑只在同一张模板自己的循环里生效，于是同一行可能被两张模板各报一次 → 点两次、记两次账。真机上暴露的后果是：点开的是五星斗鱼（收益 101 = 12 体/时 × 8.4），日志却写「五星太鼓 收益 101」，而 101 又大于太鼓封顶 76，误触发「已达封顶，本档剩余行跳过」。

`Lib.Match_models_rows(Img, Models, Threshold, max_matches=8)` 的做法是：每张模板只跑一次 `matchTemplate` 得到全图分数图 → 各取若干峰 → 按纵向中心聚成行 → **行内比分数取最像的那一张**，胜出者仍超过阈值则整行不算命中。实测三张真实截图 8 行，行内比分数 8/8 全对，真实类型分数 0.0095~0.0254、次优 0.0584~0.1144，**余量 6~12 倍**。

**四张模板必须一起送进裁决**，哪怕本档已封顶或被更高档压制：少送一张，行内竞争就不公平，剩下的模板可能把这张卡认成别的类型。该不该点这一行由 `Jiyang_at_cap` / `Jiyang_outranked` 判断，与类型识别分开。

**三种提前停止，前两条只作用于「本档」，第三条作用于整表**：

| 停止条件 | 判据 | 作用范围 |
| ---- | ---- | ---- |
| 本档封顶 | `Jiyang_at_cap`：读到**本档上限**（六星太鼓 76 / 五星太鼓 67 / 六星斗鱼 151 / 五星斗鱼 134） | 本档剩余行不再点 |
| 同类型更高档压住 | `Jiyang_outranked`：沿优先级往前找同类型档位，其数值 **≥ 本档上限** 就压住本档 | 本档剩余行不再点 |
| 首选档位封顶 | `Jiyang_top_capped`：`priority_cards[0]` 读到本档上限 | 整表收工，不再往下翻 |

**判据要用「当前这一档的上限」，不是「类型的上限」，也不是「有没有数字」**。封顶表 `Lib.JIEJIE_YIELD_CAP` 的键是**档位**（`六星太鼓` / `五星斗鱼`），取值用 `Lib.jiejie_yield_cap(priority_name)`。早先按类型记（太鼓 76 / 斗鱼 151），后果是：

- 五星斗鱼读到 134 也够不到斗鱼的 151 → 这一档的剩余行继续点，白点；
- `Jiyang_outranked` 只要更高档读到数字就压住，而六星斗鱼最低那档只有 118 → 可能存在的 134 五星斗鱼被整片跳过。

第二条的边界因此按类型不同：斗鱼要 **≥ 134** 才压得住五星（六星最低 118 < 五星上限 134）；太鼓六星最低 67 正好等于五星上限 67，相接即压住，所以「有六星太鼓就不点五星太鼓」天然成立。**跨类型不压制**——勾玉与体力单位不同，六星太鼓有货不代表六星斗鱼不用看。

**点开一行连点两次**：`Jiyang_click_row(Hwnd, row)` 连点 `JIEJIE_CLICK_TIMES = 2` 次、间隔 `JIEJIE_CLICK_WAIT = 0.5` 秒。滚轮翻页后游戏重绘整列列表，重绘那一瞬点下去会被吞掉，而**落空不会报错**：左侧列表没选中任何行、右侧详情面板还停在上一张卡上，于是 `Jiyang_read_panel` 读到的是上一张卡的收益。复核类型只能兜住「类型变了」，兜不住「压根没点中」——这行刷新后若仍是同一类型，复核也会判「一致」。第二次点击时重绘已经结束，一定点得中。

间隔取 0.5 秒而不是原设计的 1 秒：重绘基本在 0.3~0.5 秒内结束，0.5 秒够第二次点中，又不至于白等。

**扫描与回滚必须走同一个 `Jiyang_click_row`**：`Jiyang_scan_list` 与 `Jiyang_goto` 都会落空，而回滚落空的后果更重——`Jiyang_goto` 返回 `True` 之后紧接着就是点「进入结界」，把上一张卡的数字误认成目标行就等于**寄养错卡**。回滚里某个候选行复核类型不符时是 `continue` 继续试下一个候选（`Match_models_in_image_all` 可能定位出多行），不直接返回 `False`，否则会白触发一次「刷新 + 重扫」。

**首选档位封顶就整表收工**：上面两条只作用于本档，但首选档位（`priority_cards[0]`）拿到本档上限时还要再往下翻就是纯浪费——它排在所有档位最前面，后面扫出什么都不可能比它更优先。`Jiyang_top_capped` 只对首选成立：第二、三、四位读到封顶不能收工，因为首选档位可能还在后面的屏里没出现。判断放在**处理完本屏候选之后**，与到底判定同一位置。

**同收益记住后发现的**：`Best` 的更新条件用 `>=` 而不是 `>`，所以同一档里两个 67 会记住后面那个。扫完要往回翻到目标行，后发现的离列表底部更近，回滚步数更少。

**滚动步长 `JIEJIE_SCROLL_STEP = 6`**（`Scroll_print` 的单位是滚轮格，一屏约 4 行）。取 6 而不是 3：3 格时相邻两屏重叠太多，同一行会被反复匹配、重复点开，既慢又浪费；6 格能保证每行都完整经过一次视窗，重叠又比 5 格少。

**日志要能一眼看出「这张卡有没有希望」**：每读到一个数字，紧跟一句同类型目前最高（`Jiyang_type_best`，只比同类型——勾玉与体力单位不同，混在一起报会让人误以为 76 落后于 151）。扫到列表末尾后紧接着报一次最终选择（`Jiyang_pick` 的返回值），收益读不出时明确写「收益读不出」而不是 `None`。

**滚动之后不等重绘，改成点开后原地复核类型**：滚轮翻页会让游戏重绘整列列表，**同一行的结界卡有可能被刷新成另一种（太鼓 ↔ 斗鱼）**。截到重绘中间帧时，那一行会一半像太鼓一半像斗鱼，行内比分数也可能判错类型——这是「点开是斗鱼却记成太鼓」的另一个成因，光靠 `Match_models_rows` 的行内裁决解决不了。

做法分两步。滚动这边只等滚轮生效：`Jiyang_after_scroll` 等 `JIEJIE_SCROLL_WAIT = 0.2` 秒就截图，**不等重绘做完**——重绘慢的时候干等太拖时间，整趟下来要白等好几秒。正确性交给 `Jiyang_row_type`：点开一行之后、读右侧数字之前，**在原来那一行的位置上再认一次卡面类型**（按 `row` 外扩 `JIEJIE_RECHECK_MARGIN = 12` 像素裁切，四张模板一起送进 `Match_models_rows` 做行内裁决，再把裁切偏移加回去按纵向中心取离原行最近的那条，偏离超过一行高就当认不出）。复核结果与原类型不一致时，把这一屏重新识别一遍（`Jiyang_scan_list` 里的 `while True` + `Redo`），最多 `JIEJIE_RECHECK_TRIES = 2` 次；次数用完仍不一致就按复核结果记账（认不出就跳过这一行），不能无限卡在同一屏。

裁得窄有两个理由：一是快，二是不会把右侧详情面板里那张放大卡面也当成列表里的一行。回滚（`Jiyang_goto`）也走同一套：点开后先认类型，对不上就不必再读数字。

**曾经试过的两种「猜落定」都不可靠**：① 等 0.3 秒后连拍两帧比对左侧列表指纹，一致就算落定——指纹是 32×18 灰度缩略图 + 容差 3.0，重绘途中经常连续两帧「看起来一样」，于是提前收工、仍截到半张卡；② 滚完硬等 0.5 秒——准了但太慢。**用整体统计量判断局部内容是否换完，方向就错了**：一张卡占画面不足 1/20，缩略统计天生抹掉「整列换图」的细节。

**正常流程不刷新列表，只有复核失败要重扫时才刷新**：整个流程只进一次寄养列表，进来时列表本来就是从顶部开始的。扫完停在底部，回滚次数 = 扫描总次数 − 目标那一屏的次数（`Selected["back"]`），回滚后必须重新定位并**复核类型与数字**。复核失败说明列表在扫描期间被好友改动过（撤卡 / 新加卡），而列表此刻停在底部——直接重扫等于从半中间开始。所以 `Jiyang_refresh` 先点「跨区」→「好友」：既刷新内容，也把列表带回顶部，重扫才有意义；这两步任何一步失败就放弃本次寄养，不硬重扫。

**读不出时的兜底**：任何一个字认不出，`Lib.jiejie_read_yield` 返回 `None`（不猜）。若某档全部读不出，不能当作「本档没有卡」而返回 0——要回退成该档第一个模板命中的行，与改动前的行为一致。

**数字识别不用 OCR 库**：连通域切字 + 归一化画布（28×32，按字高等比缩放居中）+ 带位移容忍的像素距离（±2 横移 / ±1 纵移）。实测四张不同分辨率截图（1910×1121 / 1784×932 / 1632×854 / 1618×900）全部读对，同一数字跨图距离 0.000~0.055、不同数字最近 0.131，阈值取 0.10。数字区不依赖固定坐标：取右半边 0.55W、下半部 0.45H 的粗区域自动定位。

**模板与路径**：10 张数字模板 `pic/guild/收益数字0.png` ~ `收益数字9.png`，从四张真实截图切字形后按数字求平均得到。`Lib.JIEJIE_DIGIT_PICS` 必须写成 10 个字面量而不是 f-string——`tools/check_pics.py` 会把 f-string 目录整体豁免死图检查，写死才能让这 10 张图被真正校验。

**到底判定沿用原样**：`寄养列表末尾.png` + `0.001` 阈值 + 100 次兜底全部保留。那张模板是一块低方差米色面板（175×162，灰度均值 193.75、标准差 15.75），命中的正是「没有卡的空白格子」，与有卡行的得分差一个数量级（0.03~0.10 vs 0.37~0.47）。**注意它必须放在处理完本屏候选之后**：列表不满一屏时首页就露出空白格，若先判到底，第一屏的卡会被直接跳过。

**滚动前保证鼠标落在列表上，但只在必要时才去找列表位置**：`Scroll_print` 只 `SetForegroundWindow` 后调 `pyautogui.scroll`，**不移动鼠标**，滚轮事件是发给鼠标当前位置的。早先版本曾用「连续两屏画面相同」判断列表到底，真机上出现过「滚了但画面没变」——原因是某屏一张卡都没匹配上时没有调用 `Move_to_range`，鼠标还停在「好友」页签上，滚轮落在页签上，列表纹丝不动。

现在的做法是：**本屏点过卡就不管**（点卡时 `Move_to_range` 已经把鼠标落在列表的某一行上，直接滚就行，省掉一屏一次的多余匹配）；**本屏一张卡都没点**（没有行，或行全被 `at_cap` / `outranked` 跳过）才 `Move_to_range` 到 `寄养列表.png` 的匹配框（三张真实截图实测落点在左栏 0.28~0.33W，可靠）。回滚时归位只需做一次——滚动不移动鼠标，第一下落在列表上，后面几轮就都还在列表上。

**不要再用「画面是否变化」判断列表到底**——它既不是正确语义，在滚轮落空时还会给出误导性结论。

**`Jiejieka` 里两个容易写错的细节**（都是本次顺手修的）：

1. **切家族失败必须 `continue` 而不是 `break`**：原代码在第一张卡的页签点不到时直接跳出循环，结果「太鼓没库存 → 连斗鱼都不试」。改成 `continue` 才真的实现「耗尽再斗鱼」。
2. **`星级降序` 只点一次**（`sorted_once` 标志），不能绑在「第一轮」上：真机确认过切家族**不会**重置排序，而重复点击是切换型按钮，第二次会把降序翻回升序，拿到的是低星卡。

**弹窗布局**：一个账号一张 `HeaderCardWidget`，卡片内三行——`优先放置结界卡` + 1 个下拉、一句小字说明、四个优先级下拉**横排一行**（标签「第一优先级」…「第四优先级」在下拉框正上方，每格一个 `QVBoxLayout`）。下拉统一**固定宽度** `COMBO_WIDTH = 132`、不随窗口拉伸；4×132 + 3×12 间距 = 564px，卡片左右各 24px 内边距，`widget.setMinimumWidth(680)` 刚好装下。账号只有两个时一屏看完。

**下拉与标签的高度必须钉死**（`setFixedSize` / `setFixedHeight`，不能只靠 `sizeHint`）：Qt 的布局在空间不够时会**突破 `minimumSizeHint` 继续压缩**。实测父窗口 560px 高时，四个下拉被压成 6px 的细条、标签被压成 6px——这就是「下拉框糊掉」的成因。钉死 `COMBO_HEIGHT = 32` / `LABEL_HEIGHT = 20` 之后，父窗口只有 420px 也保持原尺寸（`tests/test_jiejie_dialog.py` 有对应用例）。

代价是弹窗总高固定，所以纵向留白比 `MessageBoxBase` 的默认值收紧一档：`viewLayout` 上下 24 → 16、间距 12 → 8、卡片表头 48 → 40、卡片内容区上下 24 → 14、`buttonGroup` 81 → 69（按钮本身高度不变，只削多余的白）。横向留白保持 24，与库的观感一致。收紧后 `sizeHint` 从 671 降到 569，600px 出头的窗口也能一屏放下两个账号。

> `_AccountCard` 用**组合**而非继承 `HeaderCardWidget`：那个类的 `__init__` 挂了 `@__init__.register` 重载分发，子类一改构造签名，`super().__init__(title, parent)` 就会被分派回子类自己的 `__init__(parent)`，直接 `TypeError: missing required positional arguments`。

**四级下拉的互斥是单向的**：第 N 级的可选项 = 枚举池去掉「第 1..N-1 级当前值」。

- 第 1 级 4 项全开、第 2 级 3 项、第 3 级 2 项、第 4 级**天然只剩 1 项**（语义就是「剩下的那个」）；
- 撞车（前级抢了后级的值，或后级主动选了前级的值）时走**同一个** `Lib.normalize_jiejie_priority()`：先出现者保留，较后者让位给池中此刻唯一空闲的值。界面联动与落盘校验共用这一个函数，所以「界面能摆出来的」必然「运行时能接受」；
- 与 §5.8 的双向灰化**刻意不同**：那边只有 2 个选项，双向会各自只剩自己、把两个下拉锁死；这里单向，第 N 级永远还剩自己的值 + 后面各级的值，改得动；
- 每张卡片各自持有一份 `_syncing`（`setCurrentText` 会再次触发 `currentIndexChanged`），两个账号互不联动。

**容错**：段缺失 / 账号缺失 / 长度不是 4 / 取值非法 / 有重复项 → 一律回落默认值（= 改动前行为），弹窗照常打开并在底部列出回落原因；配置解析失败时**拒绝写入**。落盘只覆盖 `结界养成` 段，`启动项` / `结界突破` / `寮三十` 与注释逐字不变（YAML 保真的三个坑见 §5.8，对策完全相同）。

首次新建该段时还会补两处手写风格：段前留一个空行（`data.yaml_set_comment_before_after_key(SECTION, before="")`，**只在新建时**做——段已存在时再加一次会累积成两个空行）、账号名写成带引号的 `"master"`（`DoubleQuotedScalarString`，与 `启动项` 一致，加引号不影响读取）。

## 6. 配置体系

### 6.0 目录划分：config/ 与 state/

按「谁写」把文件分成两个目录，路径常量集中在 `paths.py`（唯一事实源，其它模块不要自己拼字符串）：

| 目录 | 文件 | 谁写 | 用户是否手改 |
|---|---|---|---|
| `config/` | `Setting.yml` | 用户 | ✅ 会手改 |
| `state/` | `Last_times.yml` | 程序 | ❌ 只读或删掉重来 |
| `state/` | `Gui_state.yml` | 程序（GUI 开关） | ❌ |
| `state/` | `gui.json` | 程序（界面偏好） | ❌ |
| 项目根 | `runtime.py` | 程序（运行期开关模块） | 可手写，也可由打包脚本生成 |

**为什么要分开**：混在一起时，用户手改 `Setting.yml` 容易顺手改坏 `Last_times.yml`
（那里是冷却历史，改坏就要重跑一天）；备份/同步 `config/` 时也会把「机器状态」当成配置带走。

**旧布局迁移**：PR7 之前上述三个状态文件都在 `config/` 下。`paths.ensure_state_dir()`
会在首次读取时把它们搬到 `state/`（规则：目标不存在且源存在才搬，两边都有时不覆盖）。
触发点覆盖所有读取入口：`Lib.check_lasttime`、`main.read_completions` /
`read_task_switches` / `set_task_switch`、`ui/prefs.load_prefs` / `save_prefs`。

删除 `state/` 目录即恢复初始状态（所有任务视为从未完成、开关全部开启、界面偏好回默认）。

### 6.1 `config/Setting.yml`（静态配置，用户手改）

| 键 | 含义 |
| ---- | ---- |
| `启动项.<账号>.启动命令` | MuMu 启动命令；账号名为窗口标题关键字 |
| `结界突破.<账号>.退出次数` / `开打勋章` | 结界突破策略参数 |
| `结界养成.<账号>.优先结界卡` | 结界卡放置顺序：`太鼓` / `斗鱼`（哪个先耗尽再试另一个） |
| `结界养成.<账号>.寄养优先级` | 结界寄养的 4 张卡顺序，越左越优先；取值见 §5.9 |
| `寮三十.主账号` / `副账号` | 协作刷本的两个窗口，取值必须是 `启动项` 里存在的账号 |
| `寮三十.副本` / `次数` | 按星期（一～日）配置的副本类型与次数，各 7 项 |
| `模拟器.MuMuManager`（可选） | 显式指定 `MuMuManager.exe`；不写则从启动命令推导（见 §5.6） |

寮三十这四项**已可在界面里改**：点左侧「寮三十 / 真蛇」行的齿轮，弹窗里选完保存即可（详见 §5.8），不必再手改本文件。手改也仍然有效，两种方式写的是同一份配置。

结界养成的两项同理：点「结界养成」行的齿轮，按账号各配一份（详见 §5.9）。**缺段或取值非法时一律回落默认值**，默认值就是本次改动前的写死行为，所以老配置不写这一段也能正常跑。

寮三十副本类型只支持 `魂虚`（虚无）、`魂王`（神罚）、`魂海`（永生之海）、`日蚀`（日轮之陨）四种；次数只支持 `0`（当日跳过）/ `1` / `30` / `50`。填其它值会让「小纸人计数」那一步静默跳过、流程失效。

### 6.2 `state/Last_times.yml`（运行期状态）

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

**损坏保护**：文件整体解析失败时，重置前会先备份成 `Last_times.yml.corrupt-<时间戳>.bak`
（与文件同目录），日志用 `WAIT-` 说明备份位置，避免冷却历史被静默清空。

### 6.3 `state/Gui_state.yml`（任务开关）

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

### 6.4 `state/gui.json`（界面偏好）

由 `ui/prefs.py` 自管（普通 JSON，非 qconfig 配置文件），保存界面偏好：

```json
{
  "theme": "light",
  "log_auto_scroll": true,
  "log_font_size": 12,
  "after_run_close_emulator": false,
  "after_run_sleep": false,
  "after_run_power": "sleep"
}
```

| 键 | 含义 | 由哪个弹窗写 |
| ---- | ---- | ---- |
| `theme` | `light` / `dark` / `auto`（跟随系统） | `SettingsDialog`（日志区齿轮） |
| `log_auto_scroll` | 新日志是否自动滚动到底部 | `SettingsDialog`（日志区齿轮） |
| `log_font_size` | 日志字号，取值 11 / 12 / 13 / 14 | `SettingsDialog`（日志区齿轮） |
| `after_run_close_emulator` | 完整运行结束后关闭受控模拟器窗口（详见 §5.7） | `AfterRunDialog`（按钮区齿轮） |
| `after_run_sleep` | 完整运行结束后**是否启用**电源动作 | `AfterRunDialog`（按钮区齿轮） |
| `after_run_power` | 启用时执行哪个：`logoff` / `sleep` / `shutdown` | `AfterRunDialog`（按钮区齿轮） |

约定：

- 文件缺失或字段非法时回落默认值（浅色、自动滚动、12 pt、两个完成动作都关闭、电源动作为睡眠），不阻塞启动；
- 布尔类偏好（`log_auto_scroll` / `after_run_close_emulator` / `after_run_sleep`）统一按 `BOOL_PREF_KEYS` 校验：**只认真正的布尔值**，字符串 `"false"`、数字 `0`/`1`、`null` 一律回落默认。手改 `gui.json` 写出字符串是常见错误，不做类型校验会被当成真值而误触发睡眠；
- `after_run_power` 按 `VALID_POWER_ACTIONS` 校验，非法值回落 `"sleep"`。**注意它没有 `"none"`**：「不执行」由 `after_run_sleep` 开关表达，两个键职责不重叠；
- 三个完成动作键**由 `AfterRunDialog` 写**，`SettingsDialog` 完全不碰；反过来 `AfterRunDialog` 也不碰主题与日志偏好；
- `qconfig` 只负责运行时主题状态，不再托管配置文件，避免被覆写；
- 主题切换后日志区按新主题重新着色、自绘状态图标同步重绘，Fluent 控件由库自动换肤；
- 与 `Setting.yml`（任务参数）、`Gui_state.yml`（任务开关）互不干扰。

### 6.5 项目级 `runtime.py`（运行期开关模块）

- 用途：运行期开关，目前只有 `runtime.stop_thread`（中断请求的兼容通道）。
- 状态：**被 `.gitignore` 忽略，不在版本库中**；属于运行时必需的本地模块。
- 引用方：`ui/window.py`（GUI 中断入口置位）与 `Lib.py`（`stop_requested()` 消费）；`GUI.py` 本身不直接导入。
- 最小内容：`stop_thread = False`。
- 中断语义：`stop_thread = True` 会被 `Lib.stop_requested()` 消费，与 `Lib.request_stop()` 等价；GUI 的「中断运行」与「运行中关闭窗口」两条路径都会置位。
- 生成方式：可手写，也可执行 `python build_exe.py` 时由脚本自动生成（已存在则不改动）。

> **为什么叫 runtime 而不是 config**：PR7 之前这个模块叫 `runtime.py`，与 `config/` 目录同名。
> `import config` 能工作，依赖的是「`config/` 里没有 `__init__.py`」这个隐含前提；
> 一旦有人往里加 `__init__.py`，导入就会变成包导入、`stop_thread` 静默失效，
> 表现为「中断按钮点了没反应且不报错」。改名后两者彻底解耦。
> 旧的 `runtime.py` 若仍存在，打包脚本会输出 `WAIT-` 提示改名（不自动改用户文件）。

## 7. 关键模块与算法

### 7.1 模板匹配流水线

1. `win32gui.GetWindowRect` 取窗口矩形；
2. `pyautogui.screenshot(region=...)` 截取窗口；
3. `cv2.cvtColor` 转 BGR；
4. `cv2.matchTemplate(..., TM_SQDIFF_NORMED)`；
5. `minMaxLoc` 得最小值与位置，结合模板尺寸得到 `Left_up/Right_down`；
6. 阈值判定后返回区间与得分字符串。

中文路径通过 `Img_read_ch`（`np.frombuffer` + `cv2.imdecode`）读取。

#### 7.1.1 一帧多用（`Screenshot_window` / `Match_models_in_image`）

上面那条流水线是「识别一次就截一次图」。当同一个画面上要找多个东西时（寄养列表要先定位列表、再找卡、再找按钮），重复截图就成了大头——模板匹配本身只要几十毫秒，`pyautogui.screenshot` 才是瓶颈。

三个原语把这件事拆开：

| 函数 | 作用 |
| ---- | ---- |
| `Screenshot_window(Hwnd)` | 只截窗口，返回 cv2 BGR 图像，不匹配、不点击 |
| `Match_models_in_image(Img, models, Threshold)` | 在一张**已截好**的图上依次试多个模板，返回 `[(名字, [左上, 右下], 得分), ...]`，只含命中项、按得分升序 |
| `_read_template_cached(path)` | 模板解码缓存，键带 `mtime_ns` + 文件大小，换图立刻失效 |

`Match_models_in_image` 的阈值语义与 `Match_model` 完全一致（`TM_SQDIFF_NORMED`，得分越小越像，`> Threshold` 判失败），所以两者可以互换；`tests/test_lib_match_multi.py` 有一条用例专门断言「拆开后的结果与原函数逐字段相同」。模板比待匹配图还大时直接跳过（否则 `cv2.matchTemplate` 会抛错），文件缺失则照旧抛 `ValueError` / `FileNotFoundError`。

同一帧上找**同一种**卡的多行用 `Match_models_in_image_all(Img, Model_path, Threshold, max_matches)`：蒙版法重复匹配，返回 `[[左上, 右下], ...]` 按 y 排序。

找**多种**卡（四张结界卡）时用 `Match_models_rows(Img, Models, Threshold, max_matches)`，它多了「行内竞争」这一步，理由见 §5.9.1：每张模板各自独立搜索时，涂黑只在同一张模板自己的循环里生效，同一行会被两张模板各报一次，于是重复点击、收益记到错误的类型名下。`Match_models_rows` 先把所有命中按纵向聚成行，再在行内比分数取最像的那一张。**选型口诀**：同一种卡找多行 → `_all`；多种卡一起找 → `_rows`。

#### 7.1.2 画面指纹（`Image_fingerprint` / `Fingerprint_diff` / `Fingerprint_same`）

`Image_fingerprint` 把画面缩到 32×18 的灰度小图；`Fingerprint_diff` 给两张指纹的平均灰度差，`Fingerprint_same` 用容差（默认 3.0）判「是不是同一画面」。缩小的作用是把压缩噪声与动画抖动平均掉：同一画面带噪声的差值约 1~2，真滚动则远超 10，中间有很宽的判别带。

**不要直接比指纹字节串**——同一画面带一点噪声时字节未必全等（早先版本量化后比字节，就栽在这里）。

用途是判断「画面是否稳定」（例如点开右侧面板后等它停止变化），**不要拿它当「列表是否到底」的判据**：列表到底的正确语义是「某一行有头像但没有结界卡图」，而画面不变只是「滚不动了」的间接现象，两者不等价。到底判定仍用 `寄养列表末尾.png`。

而且「滚不动」本身也不可靠：`pyautogui.scroll` 是把滚轮事件发给**鼠标当前位置**的。鼠标若停在页签、详情面板或窗口外，列表根本不会动，两帧当然一样。实测（三张真实截图，容差 3.0）左栏滚 6px 时整窗指纹差只有 1.7~2.1，本来就分不开小幅滚动。**任何「用画面是否变化来判断流程是否走完」的写法都要先确认滚轮真的作用在目标控件上**——寄养列表的做法是每轮滚动前先 `Move_to_range` 到 `寄养列表.png` 的匹配框。

**同理也不要用它判断「重绘是否落定」**：寄养列表滚完要等游戏重绘，早先版本用「两帧指纹一致」当落定判据，实测在重绘途中经常连续两帧「看起来一样」，于是提前收工、仍截到半张卡。缩略指纹会抹掉整列卡片换图的细节（一张卡占画面不足 1/20），这类「局部内容变了但整体统计没变」的场景它天生分不出来。现在的做法是滚完只等 `JIEJIE_SCROLL_WAIT = 0.2` 秒让滚轮生效，重绘有没有做完交给「点开后原地复核类型」（`Jiyang_row_type`）兜。目前这三个原语只在测试里用，任务代码不再依赖。

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
| `MOVE-` / `QUIT-` | 滚轮、Esc 等操作；`QUIT-` 也用于「收到中断指令」 |
| `MAIN-` | 完整流程 / 单任务运行起止；被中断时结束行改为「被中断 |
| `SHOT-` | 调试截图：只在收尾打一行汇总，以及写盘失败/熔断时告警（见 §8 产物树） |

GUI 崩溃日志：`logs/app_crash.log`（`logging` + `sys.excepthook`）。

右侧日志面板按行首关键字着色：`ERROR` / `错误` → 红，`SKIP-` → 橙，`TASK-` / `MAIN-` → 蓝，其余使用正文色；
深浅色各有一套取值，切换主题后会重新着色已有日志；
运行期间面板下方显示不确定进度条，结束后用 `InfoBar` 提示本次结果。

日志区顶部工具条提供「清空日志」按钮与「自动滚动」开关（关闭后新日志不再强制滚到底部）；
日志字号可在设置弹窗中调整为 11～14 pt，偏好保存在 `state/gui.json`。

单任务运行在 `MAIN-` 起止行中带任务标题，例如：

```
MAIN- ===== 单任务运行开始：逢魔之时 ================================================
...
MAIN- ===== 单任务运行结束：逢魔之时 ================================================
```

被「中断运行」中断时的日志形态（完整运行为例）：

```
QUIT- ----- 收到中断指令 已停止当前任务 回到待机
MAIN- ===== 完整运行被中断 已完成 2 项 ========================================
```

## 8. 输出与运行产物

```
<workspace>/
├── logs/<YYYY-MM>/<YYYY-MM-DD>/console_output_<timestamp>.log   完整运行日志
├── logs/<YYYY-MM>/<YYYY-MM-DD>/single_<key>_<timestamp>.log     单任务运行日志
├── logs/<YYYY-MM>/<YYYY-MM-DD>/shots_<timestamp>/               调试截图（开启时才有）
│   ├── 000001_miss_太鼓_0.312.jpg                                  每次匹配判定一张
│   └── index.tsv                                                   图 ↔ 日志的对齐表
├── logs/app_crash.log                                          未捕获异常
├── state/Last_times.yml                                       任务冷却状态（本地）
├── state/Gui_state.yml                                        任务开关（本地）
├── state/gui.json                                             界面偏好（本地）
├── .dsh-scratch/build-tmp/pyinstaller/                         PyInstaller 中间产物
├── GUI.exe                                                     打包产物（直接在根目录，默认忽略）
└── __pycache__/                                                字节码缓存
```

运行模式：

| 方式 | 命令/入口 | 说明 |
| ---- | ---- | ---- |
| GUI | `python GUI.py` | 单击左侧卡片跑单个任务；「完整运行」按注册表顺序跑全套；运行中点「中断运行」立即停止并回待机 |
| 脚本 | 调用 `main.Full_operation()` | 无 GUI，输出到控制台与日志 |
| 脚本 | 调用 `main.Single_operation("<key>")` | 单个任务，日志写到 `logs/<YYYY-MM>/<YYYY-MM-DD>/single_<key>_*.log` |
| 调试 | `dev/test.py` / `dev/test_main.py` | 单点验证模板/任务，已 gitignore（见 `dev/README.md`） |
| 调试 | 设置弹窗选「调试截图」档位，或 `PAPER_SHOTS=all python GUI.py` | 见下方「调试截图」（也可以在 `dev/` 脚本里设同名环境变量） |
| 检查 | `python tools/check_pics.py` | 模板图引用检查（见 §8.2） |
| 清理 | `python tools/clean_logs.py` | 旧日志清理（默认预览，`--apply` 才删） |
| 打包 | `python build_exe.py` | 调用 `GUI.spec`，产物 `GUI.exe` 直接输出到项目根目录 |

### 8.1 调试截图（排查识别问题用）

每一次模板匹配判定都留一张图，用来回看「当时屏幕长什么样、得分多少」。
默认**关闭**（`off`），热路径第一行就返回，平时零开销。

| 档位 | 存什么 | 用在哪 |
| ---- | ---- | ---- |
| `off` | 不存 | 默认 |
| `miss` | 只存未命中 | **语义有坑，暂不建议用**：流程里有大量「点完看它还在不在」的反向探测，不匹配才是正常，这种档位会把正常情况也存下来 |
| `all` | 每一次判定都存 | 排查时用这个 |

开关优先级：`begin_shots(mode=...)` > 环境变量 `PAPER_SHOTS` > `state/gui.json` 的 `debug_shots` > `off`。

产物与日志同目录同 stamp（`main._log_stream` 负责起停），清理日志时整月删除即可连带带走：

```
logs/2026-11/2026-11-05/
├── console_output_2026-11-05_10-48-54.log
└── shots_2026-11-05_10-48-54/
    ├── 000001_hit_确定_0.000.jpg
    ├── 000042_miss_太鼓_0.312.jpg     # 文件名自带 hit/miss 与得分，可直接按名筛
    └── index.tsv                      # 10 列：序号/时间/结果/来源/模板/得分/阈值/尺寸/裁剪偏移/文件
```

**控制台不出现截图明细**：几千张图只在收尾打一行 `SHOT- ----- 本次共保存 N 张 / 约 M MB -> 路径`，
明细全在 `index.tsv` 里。图文对照的渲染器 `tools/render_shots.py` 尚未提供，计划在后续 PR 补上。

日志行本身不带时间戳，所以图与日志的对应关系靠 `index.tsv` 的**序号 + 毫秒时间戳**事后切分：
第 N 张图发生在第 N-1 张之后、第 N+1 张之前，落在这段区间里的日志行就归它。

上线量级参考：一次完整运行约 2000~6000 次判定，`all` 档约 640 MB（单张 JPEG 约 160 KB），
大于 8000 张会停止保存（`_SHOT_LIMIT`）；连续写盘失败 3 次自动关闭本次截图，不影响任务本身。

### 8.2 模板图引用检查（`tools/check_pics.py`）

改动 `pic/` 或任务代码里的模板路径后运行，可自动发现三类问题：

```powershell
python tools/check_pics.py            # 完整报告
python tools/check_pics.py --quiet    # 只输出错误（适合接 CI / pre-commit）
```

| 级别 | 检查项 | 说明 |
| ---- | ---- | ---- |
| **错误** | 引用了不存在的图片 | 运行到该步骤必然失败，必须修 |
| **错误** | 路径大小写与磁盘不一致 | Windows 不敏感，但 Linux / 打包工具 / 大小写敏感文件系统会失败 |
| 提示 | 未被任何源码引用的图片 | 可能是保留素材，需人工确认后再删 |
| 信息 | 动态拼接的路径（f-string） | 无法静态校验，需人工确认 |

**注意**：`team/` 目录下的编队图由 `Team_Preset()` 动态拼接（`f"./pic/team/{Preset_name}.png"`），
工具会跳过该目录的死图判定，只列出动态拼接位置。

退出码：`0` = 无错误（提示项不阻断），`1` = 发现错误，`2` = 找不到 `pic/` 目录。

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
6. 给某个任务接入配置界面时，必须同时更新：
   - 新增弹窗模块（参考 `ui/thirty_dialog.py` / `ui/jiejie_dialog.py`）与纯逻辑读写层（参考 `ui/thirty_settings.py` / `ui/jiejie_settings.py`，不依赖 Qt 才可测）；
   - `ui/window.CONFIG_DIALOGS` 登记 key → 弹窗类（**不要**另立任务列表）；
   - `ui/widgets.CONFIG_READY_KEYS` 加上该 key、`ui/widgets.CONFIG_TOOLTIPS` 加上该任务自己的提示语（两者键集合必须一致），让齿轮 tooltip 不再写「暂未开放」；
   - 弹窗类给一个 `SAVED_MESSAGE` 类属性，否则保存后控制台仍会报上一个任务的文案；
   - 涉及写 `Setting.yml` 时按 §5.8 的「三个坑」自己读写，不要直接复用 `Lib.read_config` / `Lib.write_config`。
7. `config/`、`logs/`、`.dsh-scratch/`、`GUI.exe`、`dev/` 下的调试脚本默认不入库；需要跟踪的新源码与文档请在 `.gitignore` 中显式排除忽略。根目录只允许放源码、子目录与工程配置（见 `AGENTS.md` 的「根目录白名单」）。
7. 修改 `Lib.py` 公共匹配/点击/界面函数前，确认所有 `Task_*` 调用方语义不变，尤其是返回值 `1/0` 与 `Range/Matchs` 约定。
8. 新增界面依赖（如 Fluent 组件库）时，必须同步 `requirements.txt` 与 `GUI.spec` 的 `hiddenimports`，并用 `python build_exe.py` 验证打包产物可启动。
9. 本项目通过公开 UI 自动化交互，不修改游戏文件；文档与注释避免暗示注入、外挂或协议破解能力。
10. GUI 行内图标（✓ / ! / ▶ / 齿轮）统一用 `QPainter` 矢量绘制，不依赖字体字形，也不往 `pic/` 塞 UI 素材。
