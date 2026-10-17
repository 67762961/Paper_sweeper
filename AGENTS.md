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
- 运行 GUI：`python GUI.py`；完整流程入口：`main.Full_operation()`。调试脚本 `test.py` / `test_main.py` 已忽略，不作为交付入口。

### 编码规范
- 任务模块统一 `Task_*.py` 前缀，主入口函数命名为 `MainTask_*`；完整流程变体可用 `FullTask_*`。
- 公共能力集中在 `Lib.py`：识别、点击、界面状态机、配置读写、队伍预设等；任务模块只编排业务，不重复实现底层匹配。
- 界面跳转优先写状态机（`current_state` + `match case`），轮次上限约 30，异常路径统一 `Itface_Host` 回庭院。
- 控制台日志使用固定前缀：`TASK-` / `STEP-` / `INFO-` / `WAIT-` / `SKIP-` / `TIME-` / `MOVE-` / `QUIT-` / `MAIN-`。
- 任务冷却写入 `./config/Last_times.yml`；静态配置写在 `./config/Setting.yml`；GUI 偏好（左侧任务开关）写 `./config/Gui_state.yml`，三者不要混用。配置目录默认不入库。
- 模板图片按业务分子目录放在 `./pic/`（Main / Sign / Sis / Team / Thr / Mail / Digui / Fengmo / JiejieFight / Shouliezhan）。阈值与搜索逻辑写在任务代码中，不散落魔法值到无关模块。
- 点击优先在识别框中心 1/4～3/4 区域内随机落点；全局替代硬编码坐标仅保留极少数界面（如卷轴）。
- `import config` 所需的项目级 `config.py` 当前不在源码树中；若要本地跑 GUI，需自备 `config.py`，至少提供 `stop_thread = False`。
- 注释统一使用中文；修改任务流程后，按实际改动同步 ARCHITECTURE.md 中的入口顺序、冷却策略或目录说明。
- GUI 左侧 7 行任务与「完整运行」顺序都由 `main.TASK_REGISTRY` 驱动：新增/改名顶层任务入口时，必须同步登记注册表（key / 标题 / 说明 / 入口 / `lasttime_keys` / `today_keys`），不要另写一份任务列表。
- 左侧行结构固定为「今日状态图标 + 名称/上次运行时间 + 齿轮（占位） + ▶ 单跑 + 整跑开关」；不要恢复整行点击运行，也不要加三点菜单。
- 界面代码只放 `ui/` 包，单向依赖 `theme → icons → widgets → panels → window`；`GUI.py` 仅保留入口（环境变量、日志、异常钩子）并转出组件，不要在入口里写界面逻辑。
- 今日状态由 `main.entry_done_today` 判定（`check_keys` 全部为今天才 ✓）；它只读 `Last_times.yml`，因此「被冷却/时间窗跳过」的任务仍显示 `!`。
- 行内状态图标（对勾 / 感叹号 / 播放三角）用 `QPainter` 绘制，保证任意 DPI 清晰；齿轮与运行按钮使用 `FluentIcon`；不要往 `pic/` 塞 UI 素材。
- 界面组件使用 Fluent 控件（`SimpleCardWidget`、`SwitchButton`、`TextEdit`、`PushButton`、`IndeterminateProgressBar`、`InfoBar` 等），不要在 `ui/` 里重复实现库中已有的控件；「完整运行」用轮廓按钮，不要实心主色块。
- `Full_operation` 与 `Single_operation` 共用 `main._log_stream`；日志收尾必须先恢复 `sys.stdout` 再冲刷，避免打包版（`console=False`，`sys.stdout` 为 `None`）下抛出异常导致 GUI 卡在「运行中」。
