### 项目概况与技术栈
- 本项目是《阴阳师》桌面端（MuMu 模拟器）每日任务自动化助手，项目名 Paper Sweeper（纸人扫地工）。
- 基于 Python 3.11 + OpenCV 模板匹配 + Win32 窗口句柄控制，不修改任何游戏文件，仅通过截图识别与鼠标键盘操作完成日常流程。
- GUI 使用 PyQt6 + PyQt6-Fluent-Widgets（Fluent 组件库）；配置与任务冷却使用 YAML（ruamel.yaml / PyYAML）。
- 依赖见 `requirements.txt`；打包入口为 PyInstaller（`GUI.spec`），本地一键打包用 `python build_exe.py`。

### 核心命令
- 先思考再编码；如有歧义，先确认需求再修改。
- 简单优先，不增加无关功能与重构。
- 精确修改，只改和任务相关的代码、注释和文档。
- 代码注释和说明文档统一使用中文。
- 代码与 .md 文件用 UTF-8 编码；必要时保持 CRLF 格式。
- 修改任务流程、界面导航或公共库函数前，必须先阅读 ARCHITECTURE.md，理解入口编排、状态机与 Lib 调用链。
- 修改后要同步检查 .gitignore、ARCHITECTURE.md、AGENTS.md 和 README.md 中的目录/功能说明。
- 运行 GUI：`python GUI.py`；完整流程入口：`main.Full_operation()`。本地调试脚本放 `dev/`（如 `dev/test.py` / `dev/test_main.py`，见 `dev/README.md`），不入库、不作为交付入口。

### 根目录白名单

**根目录只允许放三类东西**，其它一律归到子目录或写进 `.gitignore`：

| 类别 | 允许的条目 |
|---|---|
| 源码 | `Lib.py`、`main.py`、`GUI.py`、`Task_*.py`（7 个） |
| 子目录 | `ui/`、`tools/`、`tests/`、`pic/`、`dev/`、`config/`、`state/` |
| 工程配置与文档 | `pyproject.toml`、`requirements.txt`、`requirements-dev.txt`、`GUI.spec`、`build_exe.py`、`.gitignore`、`.gitattributes`、`README.md`、`AGENTS.md`、`ARCHITECTURE.md` |

**运行期产物不得落在根目录**（均已忽略，且已迁到子目录）：

| 产物 | 现在的位置 | 生成者 |
|---|---|---|
| 运行日志 | `logs/<YYYY-MM>/<YYYY-MM-DD>/` | `main._log_stream` |
| 崩溃日志 | `logs/app_crash.log` | `GUI.py` |
| 打包中间产物 | `.dsh-scratch/build-tmp/pyinstaller/` | `build_exe.py --workpath` |
| 打包产物 | 根目录 `GUI.exe` | `build_exe.py`（**唯一允许留在根目录的产物**，必须与 `pic/`、`config/` 同级才能运行） |
| 静态配置 | `config/Setting.yml` | 用户手改 |
| 运行期状态 | `state/`（Last_times.yml / Gui_state.yml / gui.json） | 程序读写 |
| 运行期开关模块 | `runtime.py` | 用户自备 / `build_exe.py` 自动生成 |
| 调试脚本 | `dev/` | 本地编写，不入库 |

新增文件前先问「它属于上面哪一类」。都不属于，就说明该放子目录或写进 `.gitignore`。

日志清理：`python tools/clean_logs.py`（默认只预览，加 `--apply` 才删除，默认保留最近 6 个月）。

### 编码规范
- 任务模块统一 `Task_*.py` 前缀，主入口函数命名为 `MainTask_*`；完整流程变体可用 `FullTask_*`。
- **单账号任务入口必须用 `Lib.run_accounts_task`**，双账号协作任务（寮三十）用 `Lib.run_shared_task`；不要在任务模块里手写「分隔线 → 时间窗 → 遍历账号 → 冷却判断 → 写回时间」这套控制流，也不要在任务模块里逐条 `print` 开始/结束/读取时间/成功/失败/SKIP 日志——这些文案由任务名与时间窗自动生成。
  - 签名：`run_accounts_task(name, ready, work, window=None, write_back=True)`
  - `name` 同时是 `Last_times.yml` 的任务键
  - `ready` 用 `ready_daily` / `ready_weekly` / `ready_after(hours)`；传 `None` 表示硬跑（跳过冷却与时间窗）
  - 不写回时间的任务（如纸人奖励）传 `write_back=False`
  - 分隔线统一为 84 字符（`Lib.TASK_LINE_WIDTH`），不要手写破折号数量
- `FullTask_*` 仅用于**编排多个任务**（目前只有 `FullTask_Thirty`：先跑寮三十、再按星期跑真蛇），不要用它表达"另一种冷却策略"——那种差异用 `ready` 参数表达。
- 公共能力集中在 `Lib.py`：识别、点击、界面状态机、配置读写、队伍预设等；任务模块只编排业务，不重复实现底层匹配。
- 界面跳转优先写状态机（`current_state` + `match case`），轮次上限约 30，异常路径统一 `Itface_Host` 回庭院。
- 控制台日志使用固定前缀：`TASK-` / `STEP-` / `INFO-` / `WAIT-` / `SKIP-` / `TIME-` / `MOVE-` / `QUIT-` / `MAIN-`。
- 任务冷却写入 `./state/Last_times.yml`；静态配置写在 `./config/Setting.yml`；任务开关写 `./state/Gui_state.yml`；界面偏好（主题 / 日志自动滚动 / 日志字号）由 `ui/prefs.py` 写入 `./state/gui.json`。四者不要混用，配置目录默认不入库。
- 模板图片按业务分子目录放在 `./pic/`：**目录名用英文**（`common` / `courtyard` / `signin` / `guild` / `breakthrough` / `digui` / `fengmo` / `hunt` / `thirty` / `team`），**文件名用中文**（如 `确定.png`、`寄养入口.png`）。完整清单见 `pic/README.md`。阈值与搜索逻辑写在任务代码中，不散落魔法值到无关模块。
- 改动 `pic/` 下的图片，或改动任务代码里的模板路径后，**必须运行 `python tools/check_pics.py`** 确认无失效引用；新增图片也应跑一次，避免出现"引用了不存在的图"或"死图"。工具报"错误"必须修，"提示"（未被引用）需人工确认。新增/改名图片后，再运行 `python tools/gen_pic_readme.py` 刷新 `pic/README.md` 索引。
- 点击优先在识别框中心 1/4～3/4 区域内随机落点；全局替代硬编码坐标仅保留极少数界面（如卷轴）。
- 项目级 `runtime.py` 是**运行期本地模块**（已被 `.gitignore` 忽略，不在版本库中）：`ui/window.py` 与 `Lib.py` 在运行时 `import runtime` 读取 `stop_thread`；本地跑 GUI 前需自备，最小内容 `stop_thread = False`，执行 `python build_exe.py` 时若缺失会自动生成。
- 注释统一使用中文；修改任务流程后，按实际改动同步 ARCHITECTURE.md 中的入口顺序、冷却策略或目录说明。
- GUI 左侧 7 行任务与「完整运行」顺序都由 `main.TASK_REGISTRY` 驱动：新增/改名顶层任务入口时，必须同步登记注册表（key / 标题 / 说明 / 入口 / `lasttime_keys` / `today_keys`），不要另写一份任务列表。
- 左侧行结构固定为「今日状态图标 + 名称/上次运行时间 + 齿轮 + ▶ 单跑 + 整跑开关」；不要恢复整行点击运行，也不要加三点菜单。齿轮**按任务区分**：`thirty` 行打开「寮三十设置」弹窗，其余 6 行仍是占位提示（提示语由 `ui/widgets.config_tooltip()` 统一给出，接入新任务时记得把 key 加进 `CONFIG_READY_KEYS`）。
- 界面代码只放 `ui/` 包，单向依赖 `theme → icons → widgets → panels → window`；`GUI.py` 仅保留入口（环境变量、日志、异常钩子）并转出组件，不要在入口里写界面逻辑。
- 今日状态由 `main.entry_done_today` 判定（`check_keys` 全部为今天才 ✓）；它只读 `Last_times.yml`，因此「被冷却/时间窗跳过」的任务仍显示 `!`。
- 行内状态图标（对勾 / 感叹号 / 播放三角）用 `QPainter` 绘制，保证任意 DPI 清晰；齿轮与运行按钮使用 `FluentIcon`；不要往 `pic/` 塞 UI 素材。
- 界面组件使用 Fluent 控件（`SimpleCardWidget`、`SwitchButton`、`TextEdit`、`PushButton`、`IndeterminateProgressBar`、`InfoBar` 等），不要在 `ui/` 里重复实现库中已有的控件；「完整运行」用轮廓按钮，不要实心主色块。
- 右侧按钮区顺序固定为「关闭模拟器 / 中断运行 / 完整运行 / 设置齿轮」，三者样式按语义分层：完整运行用主色（`run_button_qss`）、关闭模拟器用危险色（`danger_button_qss`，红）、中断运行用次要色（`interrupt_button_qss`，灰）。「关闭模拟器」是破坏性动作，**仅空闲时可点**（运行中禁用），点击**不弹二次确认**；它只关 `Setting.yml.启动项` 登记账号的窗口，且**必须用 `Lib.find_windows_silent`**，禁止复用会启动游戏的 `Find_windows`。
- 两个设置齿轮**各进各的弹窗**，不要合并：日志区齿轮 → `ui/settings_dialog.py`（主题 / 日志偏好 / 打开日志目录），按钮区齿轮 → `ui/after_run_dialog.py`（只有完成动作：关闭模拟器开关 + 电源动作开关与下拉框）。弹窗里不混放无关项，进错了页面要能一眼看出；按钮区齿轮走独立信号 `after_run_settings_clicked`，不要复用 `settings_clicked`。加上左侧行内齿轮，一共**三个**配置入口，各管一摊，都不得复用对方的信号。
- 给某个任务接入配置界面：弹窗放 `ui/`，**读写与归一化单独一层且不依赖 Qt**（照 `ui/thirty_settings.py`），否则 `MessageBoxBase` 没有 parent 会崩、逻辑没法测；在 `ui/window.CONFIG_DIALOGS` 登记 key → 弹窗类（不要另写任务列表）；写 `Setting.yml` 时**不要直接复用 `Lib.read_config` / `Lib.write_config`**——前者不设 `preserve_quotes`（引号会在读的时候丢），后者不设 `width`（长命令会被折成两行），列表还要**原地切片**才保得住 `[...]` 单行写法。详见 ARCHITECTURE.md §5.8。
- `MuMuManager.exe` 的路径**不要写死**：从 `Setting.yml.启动项.<账号>.启动命令` 里的 exe 推导目录（同目录 → 上一级 → `shell/`），找不到就降级为发 `WM_CLOSE`；用户可用可选键 `模拟器.MuMuManager` 显式覆盖。
- 「完整运行完成后的动作」（关模拟器 / 注销 / 睡眠 / 关机）的触发条件严格为 `task_key is None` + `ok` + `not stopped`，**单跑、中断、异常一律不触发**。执行时机必须是 `QThread.finished`（`on_thread_finished`），不能是 `task_finished`——后者发出时 `main._log_stream` 的日志文件还没关，此时睡眠会截断日志。
- 电源动作是**开关 + 下拉框两个键**：`after_run_sleep`（bool，是否启用）+ `after_run_power`（`logoff` / `sleep` / `shutdown`，启用时用哪个）。**不要合并成一个四值枚举**——分开后老配置升级零迁移，「不执行」由开关表达，下拉框不必塞 `"none"`。开关关闭时下拉框 `setEnabled(False)` 灰化。
- 注销与睡眠的**关键差别**（决定各自适用场景）：注销只结束用户会话，**内核继续运行**，Session 0 的服务（远程控制软件如 UU 远程的 `GameViewerService`）仍在，所以**注销后可以远程接管**；睡眠/关机时内核挂起或停止，服务不存在，远程连不上。
- 电源动作统一走 `Lib.power_action(action)`（`logoff` → `ExitWindowsEx(EWX_LOGOFF)`、`sleep` → `SetSuspendState(False, ...)`、`shutdown` → `ExitWindowsEx(EWX_POWEROFF)`），共用 `_enable_shutdown_privilege()`。**不要**用 `rundll32 powrprof.dll,SetSuspendState 0,1,0`（开了休眠的机器会变成休眠）；**不要**加 `EWX_FORCE` / `EWX_FORCEIFHUNG`（会杀掉用户未保存的工作）。ctypes 调 Win32 时必须显式声明 `restype` / `argtypes`，否则伪句柄会被截断（`GetCurrentProcess` 的 `-1` 变成 `0xFFFFFFFF`，`OpenProcessToken` 报错误 6）。
- 注销/关机**会立刻结束本进程**，调用前必须 `QApplication.processEvents()` 把日志刷到屏幕上，否则用户永远看不到「正在请求注销」那一行。
- **关模拟器必须跑在后台线程**（`CloseEmulatorThread`）：`MuMuManager control ... shutdown` 同步阻塞约 4 秒，放主线程会让界面冻住，并让倒计时弹窗的 100ms 淡出动画停在中间帧（半透明虚影）。`dialog.exec()` 返回后先 `processEvents()` 让动画走完再启线程。QThread 子类的结果信号**不要叫 `finished`**（会覆盖基类的线程结束通知），本项目用 `close_finished`。
- 配色统一从 `ui/theme.py` 取：`COLOR_*` 是浅色取值、深色覆盖在 `_DARK_COLORS`；组件取色用 `theme.color()` / `light_color()` / `dark_color()`，不要在组件里写死十六进制。
- 会随主题变化的元素不要用裸 `QLabel` 承载文字（深色下会变黑看不清）：文字用 Fluent 标签并 `setTextColor(浅色, 深色)`；轮廓按钮用 `setCustomStyleSheet(light_qss, dark_qss)` 注册；自绘控件连接 `qconfig.themeChangedFinished` 后重绘。
- `Full_operation` 与 `Single_operation` 共用 `main._log_stream`；日志收尾必须先恢复 `sys.stdout` 再冲刷，避免打包版（`console=False`，`sys.stdout` 为 `None`）下抛出异常导致 GUI 卡在「运行中」。
- 中断是协作式的：GUI「中断运行」→ `Lib.request_stop()` → 各检查点 `check_stop()` 抛 `TaskStopped` → `main` 统一收尾 → 返回 `stopped=True` → GUI 回待机。**任务层禁止捕获 `TaskStopped`**，让它一路抛到 `main.py`。
- `Lib.py` 里除 `_sleep_with_stop` 之外不要写裸 `time.sleep`；长等待一律走 `_sleep_with_stop`（0.2 s 切片），否则会卡住中断响应。新增耗时的公共原语时，入口加 `check_stop()`、循环体每轮加一次。
