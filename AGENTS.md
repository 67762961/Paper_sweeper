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
- 左侧行结构固定为「今日状态图标 + 名称/上次运行时间 + 齿轮（占位） + ▶ 单跑 + 整跑开关」；不要恢复整行点击运行，也不要加三点菜单。
- 界面代码只放 `ui/` 包，单向依赖 `theme → icons → widgets → panels → window`；`GUI.py` 仅保留入口（环境变量、日志、异常钩子）并转出组件，不要在入口里写界面逻辑。
- 今日状态由 `main.entry_done_today` 判定（`check_keys` 全部为今天才 ✓）；它只读 `Last_times.yml`，因此「被冷却/时间窗跳过」的任务仍显示 `!`。
- 行内状态图标（对勾 / 感叹号 / 播放三角）用 `QPainter` 绘制，保证任意 DPI 清晰；齿轮与运行按钮使用 `FluentIcon`；不要往 `pic/` 塞 UI 素材。
- 界面组件使用 Fluent 控件（`SimpleCardWidget`、`SwitchButton`、`TextEdit`、`PushButton`、`IndeterminateProgressBar`、`InfoBar` 等），不要在 `ui/` 里重复实现库中已有的控件；「完整运行」用轮廓按钮，不要实心主色块。
- 配色统一从 `ui/theme.py` 取：`COLOR_*` 是浅色取值、深色覆盖在 `_DARK_COLORS`；组件取色用 `theme.color()` / `light_color()` / `dark_color()`，不要在组件里写死十六进制。
- 会随主题变化的元素不要用裸 `QLabel` 承载文字（深色下会变黑看不清）：文字用 Fluent 标签并 `setTextColor(浅色, 深色)`；轮廓按钮用 `setCustomStyleSheet(light_qss, dark_qss)` 注册；自绘控件连接 `qconfig.themeChangedFinished` 后重绘。
- `Full_operation` 与 `Single_operation` 共用 `main._log_stream`；日志收尾必须先恢复 `sys.stdout` 再冲刷，避免打包版（`console=False`，`sys.stdout` 为 `None`）下抛出异常导致 GUI 卡在「运行中」。
- 中断是协作式的：GUI「中断运行」→ `Lib.request_stop()` → 各检查点 `check_stop()` 抛 `TaskStopped` → `main` 统一收尾 → 返回 `stopped=True` → GUI 回待机。**任务层禁止捕获 `TaskStopped`**，让它一路抛到 `main.py`。
- `Lib.py` 里除 `_sleep_with_stop` 之外不要写裸 `time.sleep`；长等待一律走 `_sleep_with_stop`（0.2 s 切片），否则会卡住中断响应。新增耗时的公共原语时，入口加 `check_stop()`、循环体每轮加一次。
