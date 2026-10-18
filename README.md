# Paper Sweeper

**阴阳师 · 纸人扫地工** —— 基于 OpenCV 图像识别的 Windows 日常自动化小助手。

面向工作繁忙、只希望把重复日常交给脚本的阴阳师玩家。脚本通过模拟器窗口截图识别与鼠标键盘操作完成领取、结界、协作本等流程，**不修改任何游戏文件**。

> 本项目一边学习一边维护，以学习交流为目的。**不接受功能需求**；出现 Bug 会视情况调整。  
> **仅供学习交流，严禁倒卖。**

---

## 功能概览

完整运行（GUI「完整运行」或 `main.Full_operation()`）会按下列顺序依次尝试各任务，任务层会检查时间窗与冷却，未到条件会自动跳过。

| 模块 | 内容 | 典型门禁 |
| ---- | ---- | ---- |
| 登录收菜 | 邮件、每日一签、福袋、体力/勾玉/BUFF 纸人、商店免费礼包、友情点 | 部分项 1 小时 / 当日 |
| 结界养成 | 寮工资与寮体力、寄养与寄养奖励、结界卡领取/放置、白达摩育成、体力食盒与经验酒壶 | 约 6 小时一轮 |
| 地域鬼王 | 经探索 → 六道 → 地鬼入口挑战 | 12:00–23:50，当日一次 |
| 寮三十 / 真蛇 | 双账号协作刷当日配置的御魂副本；非周末尝试真蛇 | 寮三十 9:00–23:00；真蛇按周 |
| 结界突破 | 按勋章阈值开打，支持配置退出次数 | 7:00–23:00，约 1 小时冷却 |
| 狩猎战 | 周五～周日阴界之门；周一～周四麒麟狩猎战 | 当日一次 |
| 逢魔之时 | 庭院日常入口进入逢魔 | 17:00–21:50，当日一次 |

结界卡、寄养等周边逻辑的默认倾向（如太古/斗鱼优先级、白达摩满级替换）写在 `Task_Jiejieyangcheng.py` 中，可通过改代码或模板图调整。

---

## 运行环境

| 项目 | 要求 |
| ---- | ---- |
| 系统 | Windows（依赖 `pywin32`、`ctypes`、鼠标钩子） |
| Python | 3.11+（开发环境为 CPython 3.11） |
| 模拟器 | MuMu 多开（或其他能把游戏窗口标题设为账号名的多开器） |
| 游戏 | 阴阳师桌面端 / 模拟器内安装的客户端 |
| 识别 | 模板图按当前窗口布局采集；分辨率或缩放不一致时需重采 `pic/` |

依赖安装：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

主要依赖：`opencv-python`、`numpy`、`pywin32`、`PyAutoGUI`、`PyDirectInput`、`PyQt6`、`PyQt6-Fluent-Widgets`、`ruamel.yaml`、`PyYAML`。完整列表见 `requirements.txt`。

### 必需的本地文件

仓库默认忽略运行配置与调试文件，克隆后请自行准备：

1. **`config/Setting.yml`** —— 启动命令与任务参数（示例结构见下）。
2. **`config/Last_times.yml`** —— 可为空；首次运行会按账号/任务自动初始化。
3. **`config.py`（项目根目录）** —— 运行期停止标志模块，**已被 `.gitignore` 忽略、不在版本库中**；由 `ui/window.py` 与 `Lib.py` 在运行时 `import config`。最小内容：

   ```python
   stop_thread = False
   ```

   执行 `python build_exe.py` 时若缺失会自动生成。

4. **`pic/`** —— 界面模板图目录，须与你的窗口分辨率/皮肤一致；缺失模板会导致对应步骤识别失败。

`Setting.yml` 示例：

```yaml
启动项:
  "master":
    启动命令: "你的MuMu主程序路径 -p 你的渠道包 -v 0"
  "slaves":
    启动命令: "你的MuMu主程序路径 -p 你的渠道包 -v 1"

结界突破:
  "master":
    退出次数: 3
    开打勋章: 15
  "slaves":
    退出次数: 3
    开打勋章: 15

寮三十:
  主账号: "master"
  副账号: "slaves"
  副本: ["魂虚","魂虚","魂虚","魂虚","魂虚","魂海","日蚀"]
  次数: [30,30,30,30,30,30,30]
```

- **窗口标题必须能包含账号名**（如标题含 `master` / `slaves`），脚本用标题子串找窗口。
- **双开**：先启动两个游戏窗口，再点「完整运行」。多开器可自选，能改窗口标题即可。
- **寮三十** 的 `副本` / `次数` 为周一～周日共 7 项；次数 `0` 表示当天不刷该项。

---

## 快速开始

### 方式一：图形界面

```powershell
# 在项目根目录执行，保证相对路径 ./pic、./config 可用
python GUI.py
```

1. 确认两个游戏窗口已打开，且窗口标题匹配 `Setting.yml` 中的账号名。
2. 左侧列表面板按任务顺序显示 7 行，每行包含：
   - 最左**今日状态**：绿底 ✓ = 今天已完成；橙底 `!` = 今天还没完成（状态取自 `Last_times.yml`，所以「点了但被冷却/时间窗跳过」仍显示 `!`）；
   - **任务名 + 上次运行时间**（多账号取最新一条）；
   - **齿轮**：该任务的配置入口，当前版本**暂未开放**，点击只弹提示；
   - **▶ 运行**：单击只运行这一项（不绕过任务自身的时间窗与冷却，条件不满足会打印 `SKIP-`）；
   - **开关**：开启时参与「完整运行」，关闭时「完整运行」直接跳过该任务（配置存 `config/Gui_state.yml`，缺失默认全开）。
3. **运行全套日常**：点击右侧 **「完整运行」**，按行顺序依次执行**开关开启**的任务；已关闭的任务会在日志里打印 `SKIP- ... 已在左侧关闭 跳过`。
4. 运行期间所有行的按钮、齿轮与开关会一起禁用，避免并发抢占键鼠；结束后自动刷新「上次运行」时间与今日状态。
5. **中断运行**：运行中「完整运行」左侧的 **「中断运行」** 按钮会变为可点。点击后立即停止当前任务并回到待机状态
   （日志打印 `QUIT- ----- 收到中断指令 已停止当前任务 回到待机`，按钮区复位、行内控件恢复）。
   中断**不做断点续跑**，也**不处理游戏内状态**（不会把角色拉回庭院）；再次点「完整运行」就是新的一轮，
   已完成的任务会按冷却/时间窗自动跳过，被中断的任务会重跑。中断响应通常在 0.2 秒内。
6. 右侧控制台会实时打印识别与任务日志；同一份日志也会写入 `logs/<日期>/`
   （完整运行为 `console_output_*.log`，单任务为 `single_<key>_*.log`）。

7. 右侧日志区顶部可一键**清空日志**、切换**自动滚动**；点击齿轮打开**设置**（主题、日志字号、打开日志目录）。
   顶栏标题旁的亮度按钮可快速切换**浅色 / 深色**主题。

打包版可使用同目录下的 `GUI.exe`（若存在），行为与 `python GUI.py` 一致。

### 方式二：代码入口

```python
from main import Full_operation, Single_operation

Full_operation()                  # 完整运行：控制台 + logs/ 文件
Single_operation("fengmo")        # 只跑「逢魔之时」，日志写 logs/<日期>/single_fengmo_*.log
```

`Single_operation` 的 key 与左侧任务行一一对应：`signin` / `jiejieyangcheng` / `digui` /
`thirty` / `jiejiefight` / `shouliezhan` / `fengmo`（完整列表见 `main.TASK_REGISTRY`）。
`Full_operation` / `Single_operation` 都会遵守冷却与时间窗；其中 `Full_operation` 还会读取
`config/Gui_state.yml` 的任务开关，跳过被关闭的任务。

脚本里也可以主动中断（等价于 GUI 的「中断运行」）：

```python
from main import Full_operation, request_stop
import threading

threading.Timer(30, request_stop).start()   # 30 秒后中断
result = Full_operation()                   # 被中断时 result["stopped"] 为 True
```

### 方式三：单任务调试

在项目根目录的交互式 Python 中直接调用某一 `MainTask_*`，例如：

```python
from Task_SignIn import MainTask_Signin
MainTask_Signin()
```

开发用脚本 `test.py` / `test_main.py` 不在版本库跟踪范围，可按需在本地改写，用于验证单张模板或单个状态机。

### 方式四：打包为 exe

项目自带打包脚本 `build_exe.py`，基于 `GUI.spec`（PyInstaller，单文件、无控制台窗口）。
产物**直接输出到项目根目录**，与 `pic/`、`config/` 同级，打包完即可双击运行：

```powershell
python build_exe.py            # 打包，产物为项目根目录的 GUI.exe
python build_exe.py --fresh    # 先删除 build/ 与残留 dist/，做全新构建
```

脚本会依次检查 Python 版本（需 3.11+）与 PyInstaller 是否安装、核对 `GUI.spec` 与 `GUI.py`，
并在缺少 `config.py` 时自动生成最小版本（`stop_thread = False`）。单次构建约 30～60 秒。

> 注意：`pic/` 与 `config/` 是运行期外部资源，**不会**打进 exe。请把 `GUI.exe` 与这两个目录放在同一目录下运行，
> 否则模板图与配置的相对路径会失效。根目录 `GUI.exe` 正在运行时会被锁定，打包前请先关闭程序。

### 方式五：检查模板图引用

改动 `pic/` 下的图片或任务代码里的模板路径后，运行检查工具确认没有写错：

```powershell
python tools/check_pics.py            # 完整报告
python tools/check_pics.py --quiet    # 只输出错误
```

会检查四项：引用了不存在的图片（错误）、路径大小写与磁盘不一致（错误）、
未被引用的图片（提示）、动态拼接的路径（信息）。退出码 `0` 表示无错误。

---

## 使用注意

1. **工作目录**：请在项目根目录启动脚本，否则 `./pic`、`./config` 相对路径会失效。
2. **不要抢占键鼠**：任务运行时脚本会置前游戏窗口并移动鼠标，请避免同时操作。
3. **分辨率 / 皮肤**：模板图对 UI 缩放敏感；换分辨率或界面主题后应重截对应 `pic/` 子目录。
4. **冷却状态**：成功完成会写入 `config/Last_times.yml`；若要强制重跑某任务，可删除该账号下对应键或改写时间。
5. **界面偏好**：主题、日志自动滚动与日志字号保存在 `config/gui.json`；删除该文件即恢复默认（浅色 / 自动滚动 / 12 pt）。
6. **中断运行**：中断是协作式的，任务在下一个检查点（≤0.2 秒）退出，不会强杀线程；中断后不保留进度，下次运行即新的一轮。中断瞬间鼠标键盘输入立即停止，但**不会**把角色拉回庭院。
7. **任务开关**：左侧行的开关只影响「完整运行」，点击 ▶ 始终可以单跑该任务；开关状态存于 `config/Gui_state.yml`，删除该文件即恢复「全部开启」。
8. **协作与弹窗**：脚本会尝试自动关闭协作邀请与常见弹窗；若布局变化导致误判，优先检查 `pic/Main` 中相关模板。
9. **硬编码坐标**：极少数界面（如庭院卷轴）仍使用绝对坐标，窗口位置/分辨率变化后可能失效。
10. **日志排查**：
   - 完整运行日志：`logs/<YYYY-MM-DD>/console_output_*.log`
   - 单任务运行日志：`logs/<YYYY-MM-DD>/single_<key>_*.log`
   - GUI 崩溃：`app_crash.log`
   - 控制台匹配得分（`INFO- 0.0xx ...`）可辅助判断阈值是否过严/过松。

---

## 项目结构（简）

```
Paper_sweeper/
├── GUI.py                 # 图形界面入口（环境变量 / 日志 / 异常钩子）
├── GUI.spec               # PyInstaller 打包配置
├── build_exe.py           # 一键打包脚本（调用 GUI.spec，产物输出到根目录）
├── main.py                # 任务注册表、完整/单任务运行编排、任务开关与日志 Tee
├── Lib.py                 # 识别、点击、界面状态机、配置、编队
├── ui/                    # 界面层（theme → icons → widgets → panels → window）
├── Task_SignIn.py         # 登录收菜
├── Task_Jiejieyangcheng.py# 结界养成
├── Task_Digui.py          # 地域鬼王
├── Task_Thirty.py         # 寮三十与真蛇
├── Task_JiejieFight.py    # 结界突破
├── Task_Shouliezhan.py    # 狩猎战 / 阴界
├── Task_Fengmo.py         # 逢魔之时
├── pic/                   # 界面模板图（按业务分子目录）
├── tools/                 # 开发辅助脚本（不参与打包）
│   └── check_pics.py      # 模板图引用检查
├── config/                # Setting.yml / Last_times.yml / Gui_state.yml / gui.json（本地）
├── logs/                  # 运行日志
├── requirements.txt
├── AGENTS.md              # 协作与编码约定（开发向）
└── ARCHITECTURE.md        # 架构与任务地图（开发向）
```

> `config.py`、`config/`、`logs/`、`build/`、`GUI.exe`、`app_crash.log` 均为运行期产物，已被 `.gitignore` 忽略，故不列在上方结构里。

更细的调用链、状态机与实施约束见 [ARCHITECTURE.md](./ARCHITECTURE.md)；提交代码前的约定见 [AGENTS.md](./AGENTS.md)。

---

## 常见问题

**Q：点击「完整运行」后立即报 `ModuleNotFoundError: No module named 'config'`？**  
A：项目根目录缺少 `config.py`。创建该文件并写入 `stop_thread = False`（或执行 `python build_exe.py` 自动生成）。该文件已被 `.gitignore` 忽略，克隆仓库后不会自带。

**Q：一直提示「未检测到窗口」？**  
A：检查游戏是否已启动、窗口标题是否包含 `Setting.yml` 中的账号名（`master`/`slaves`）；若走自动启动，核对 `启动命令` 路径与 `-v` 实例号。

**Q：某个任务总是「未检测到 xxx」？**  
A：多为模板图与当前 UI 不符或阈值过严。用临时调试脚本对目标模板 `Flag_show=1` 查看红框是否命中，再替换 `pic/` 下对应图片。

**Q：任务全部 SKIP？**  
A：多半是冷却未到。查看 `config/Last_times.yml`，或确认当前时间是否落在任务时间窗内。点击 ▶ 单独运行同样受这些限制，不会强制重跑。

**Q：点了 ▶ 没反应 / 只有一行提示？**  
A：先看控制台是否出现 `SKIP-`。单任务运行沿用与完整运行一致的冷却和时间窗判断；若行首仍是 `!`，通常就是条件未满足或该任务本次未成功。

**Q：行首 `!` 是什么意思？和开关有关吗？**  
A：`!` 表示该任务今天还没有完成（依据 `Last_times.yml` 的当天记录；「登录收菜」要求 5 个子项全部完成才算 ✓）。它与最右侧开关无关：开关只决定是否参与「完整运行」。

**Q：我把某个任务的开关关了，为什么点 ▶ 还能跑？**  
A：这是有意设计：开关只影响「完整运行」，▶ 是你的显式单跑操作，始终允许（仍受任务自身冷却/时间窗约束）。

**Q：齿轮点了只有提示？**  
A：任务配置入口本期为占位，暂未实现具体配置界面；需要调参数请直接改 `config/Setting.yml`。

**Q：能否按分辨率自动适配？**  
A：当前版本依赖人工维护模板图与少量坐标，没有自动缩放适配层。

---

## 免责声明

本项目是一个外部工具，旨在自动化阴阳师的部分每日任务。它被设计成仅通过现有用户界面与游戏交互，并遵守相关法律法规。该软件包旨在提供简化和用户通过功能与游戏交互，并且它不打算以任何方式破坏游戏平衡或提供任何不公平的优势。该软件包不会以任何方式修改任何游戏文件或游戏代码。

This project is an external tool designed to automate some of Onmyoji's Dailies. It is designed to interact with the game only through the existing user interface and to comply with relevant laws and regulations. This package is designed to provide simplicity and user interaction with the game through features, and it is not intended to upset the balance of the game in any way or provide any unfair advantage. This package does not modify any game files or game code in any way.

本软件开源、免费，仅供学习交流使用。开发者团队拥有本项目的最终解释权。使用本软件产生的所有问题与本项目与开发者团队无关。若您遇到商家使用本软件进行代练并收费，可能是设备与时间等费用，产生的问题及后果与本软件无关。
