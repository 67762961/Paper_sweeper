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
2. **`state/Last_times.yml`** —— 可为空；首次运行会按账号/任务自动初始化。
3. **`runtime.py`（项目根目录）** —— 运行期停止标志模块，**已被 `.gitignore` 忽略、不在版本库中**；由 `ui/window.py` 与 `Lib.py` 在运行时 `import runtime`。最小内容：

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
  这四项（含 `主账号` / `副账号`）也可以不手改：点左侧「寮三十 / 真蛇」行的**齿轮**，在弹窗里选完保存即可。
  副本只支持 `魂虚` / `魂王` / `魂海` / `日蚀`，次数只支持 `0` / `1` / `30` / `50`——填其它数字会让「小纸人计数」那一步静默跳过、流程失效。

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
   - **齿轮**：「寮三十 / 真蛇」这一行点开是**配置弹窗**（副本 / 次数 / 主副账号），其余 6 行暂未开放、点击只弹提示；
   - **▶ 运行**：单击只运行这一项（不绕过任务自身的时间窗与冷却，条件不满足会打印 `SKIP-`）；
   - **开关**：开启时参与「完整运行」，关闭时「完整运行」直接跳过该任务（配置存 `state/Gui_state.yml`，缺失默认全开）。
3. **运行全套日常**：点击右侧 **「完整运行」**，按行顺序依次执行**开关开启**的任务；已关闭的任务会在日志里打印 `SKIP- ... 已在左侧关闭 跳过`。
4. 运行期间所有行的按钮、齿轮与开关会一起禁用，避免并发抢占键鼠；结束后自动刷新「上次运行」时间与今日状态。
5. **中断运行**：运行中「完整运行」左侧的 **「中断运行」** 按钮会变为可点。点击后立即停止当前任务并回到待机状态
   （日志打印 `QUIT- ----- 收到中断指令 已停止当前任务 回到待机`，按钮区复位、行内控件恢复）。
   中断**不做断点续跑**，也**不处理游戏内状态**（不会把角色拉回庭院）；再次点「完整运行」就是新的一轮，
   已完成的任务会按冷却/时间窗自动跳过，被中断的任务会重跑。中断响应通常在 0.2 秒内。
6. **关闭模拟器**：按钮区最左的 **红色「关闭模拟器」** 按钮（`中断运行` 左边），空闲时可点，**运行中禁用**。
   点击后直接关闭 `Setting.yml.启动项` 里登记账号（`master` / `slaves`）对应的模拟器窗口，**不弹二次确认**，
   关闭后控制台输出摘要（已关闭 / 未运行 / 仍残留 3 类）并用提示条告知结果。
   手动开的、标题不匹配任何账号的窗口**不会被碰**。优先走 `MuMuManager` 按实例号正常关机，
   找不到 `MuMuManager` 时降级为向窗口发关闭消息。
   > ⚠️ 关模拟器等于结束虚拟机，**游戏内未保存的进度会丢失**；它不会先把角色拉回庭院。
7. **完整运行完成后的动作**：点按钮区最右的**设置齿轮**（「完整运行」右边）打开「完整运行设置」，
   里面是**关闭模拟器**开关 + **电源动作**（开关 + 下拉框），默认都不启用，存在 `state/gui.json`。
   电源动作可选 **注销 / 睡眠 / 关机**；开关关闭时下拉框是灰的，表示不执行。
   启用后，**完整运行成功结束**时会先弹一个 10 秒倒计时（可取消、可提前执行），归零后按顺序执行：
   关模拟器 → 等 3 秒 → 电源动作（3 秒是给 MuMu 回收虚拟机的时间，它持有唤醒请求时系统睡不下去）。
   只有「完整运行 + 成功 + 未中断」才触发；**单跑、中断、异常都不会**动你的电脑。

   | 选项 | 效果 | 远程还能连吗 |
   | ---- | ---- | ---- |
   | **注销** | 结束当前用户会话，程序关闭 | ✅ **能**，服务继续运行，输密码即可接管 |
   | **睡眠** | S3，CPU 断电、内存供电，唤醒 1～3 秒 | ❌ 不能 |
   | **关机** | 全部断电 | ❌ 不能 |

   > 想随时远程接管就选**注销**：它只结束用户会话，Session 0 的服务（如 UU 远程）照常运行；
   > 睡眠和关机时系统内核挂起/停止，远程连不上。
   > 日志区顶部的齿轮是另一个弹窗（主题 / 日志字号 / 打开日志目录），两个齿轮各管一摊，别点混。
8. 右侧控制台会实时打印识别与任务日志；同一份日志也会写入 `logs/<年-月>/<日期>/`
   （完整运行为 `console_output_*.log`，单任务为 `single_<key>_*.log`）。

9. 右侧日志区顶部可一键**清空日志**、切换**自动滚动**；点击齿轮打开**设置**（主题、日志字号、打开日志目录）。
   顶栏标题旁的亮度按钮可快速切换**浅色 / 深色**主题。

打包版可使用同目录下的 `GUI.exe`（若存在），行为与 `python GUI.py` 一致。

### 方式二：代码入口

```python
from main import Full_operation, Single_operation

Full_operation()                  # 完整运行：控制台 + logs/ 文件
Single_operation("fengmo")        # 只跑「逢魔之时」，日志写 logs/<年-月>/<日期>/single_fengmo_*.log
```

`Single_operation` 的 key 与左侧任务行一一对应：`signin` / `jiejieyangcheng` / `digui` /
`thirty` / `jiejiefight` / `shouliezhan` / `fengmo`（完整列表见 `main.TASK_REGISTRY`）。
`Full_operation` / `Single_operation` 都会遵守冷却与时间窗；其中 `Full_operation` 还会读取
`state/Gui_state.yml` 的任务开关，跳过被关闭的任务。

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

开发用脚本放在 `dev/`（如 `dev/test.py` / `dev/test_main.py`），不在版本库跟踪范围，可按需在本地改写，
用于验证单张模板或单个状态机。详见 [dev/README.md](./dev/README.md)。

### 方式四：打包为 exe

项目自带打包脚本 `build_exe.py`，基于 `GUI.spec`（PyInstaller，单文件、无控制台窗口）。
产物**直接输出到项目根目录**，与 `pic/`、`config/` 同级，打包完即可双击运行：

```powershell
python build_exe.py            # 打包，产物为项目根目录的 GUI.exe
python build_exe.py --fresh    # 先清空构建缓存与历史遗留的 build/、dist/，做全新构建
```

PyInstaller 的中间产物写在 `.dsh-scratch/build-tmp/pyinstaller/`（已被忽略），
不会在源码树里生成 `build/`。

脚本会依次检查 Python 版本（需 3.11+）与 PyInstaller 是否安装、核对 `GUI.spec` 与 `GUI.py`，
并在缺少 `runtime.py` 时自动生成最小版本（`stop_thread = False`）。单次构建约 30～60 秒。

> 注意：`pic/`、`config/`、`state/` 是运行期外部资源，**不会**打进 exe。请把 `GUI.exe` 与这些目录放在同一目录下运行，
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

## 开发与自检

面向要改代码的人。只想跑日常的话，上面的「快速开始」就够了。

### 依赖分两份

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt            # 只跑日常：图像识别 + 界面
pip install -r requirements-dev.txt        # 改代码：pytest / 静态检查 / 打包
```

- `requirements.txt` —— 运行期依赖，**只列代码真正 import 的包**（精确版本，便于复现）
- `requirements-dev.txt` —— 测试、静态检查、打包工具
- `pyproject.toml` —— 工具配置（pytest 路径、ruff 规则）与项目元信息；本项目**不是**要 `pip install` 的库，源码直接放在根目录运行

### 自检三件套

改完代码按这个顺序过一遍，从便宜到贵：

```powershell
# 1. 语法检查（秒级）
python -m compileall -q Lib.py main.py GUI.py build_exe.py paths.py Task_*.py ui tools tests

# 2. 单元测试（秒级，不碰游戏窗口）
python -m pytest

# 3. 模板图引用（改了 pic/ 或模板路径才需要）
python tools/check_pics.py
```

`pytest` 只覆盖**不依赖真实游戏窗口**的纯逻辑，当前有 324 个用例：

| 文件 | 用例数 | 覆盖内容 |
|---|---|---|
| `tests/test_task_registry.py` | 20 | `TASK_REGISTRY` 一致性：key 唯一、入口可调用、状态键合法、今日判定键是状态键子集、默认开关全开、注册表顺序即整跑顺序 |
| `tests/test_config_io.py` | 33 | 四类配置的读写与**回落**：`gui.json` 非法值回默认、`Gui_state.yml` 缺文件默认全开、`Last_times.yml` 缺失/空文件/坏 YAML/坏时间都能自愈、`read_config` 缺失返回 `{}` |
| `tests/test_config_corrupt.py` | 10 | **配置文件损坏时不崩**：`read_config` 对坏 YAML / 非法 UTF-8 返回 `{}`，上层四个调用方都不抛异常 |
| `tests/test_config_backup.py` | 10 | **损坏配置先备份再重置**：重置前生成 `.corrupt-*.bak`，历史记录不被静默清空 |
| `tests/test_paths.py` | 16 | **`config/` 与 `state/` 分层**：路径常量位置、旧布局迁移（不覆盖、不复制）、迁移后四个读取入口都能读到旧数据 |
| `tests/test_runtime.py` | 9 | **`runtime.py` 命名约定**：`stop_thread` 可被消费、`config/` 里不能有 `__init__.py`、全项目禁止 `import config` |
| `tests/test_logs.py` | 13 | 日志按年月分层、`clean_logs.py` 的按月/按天清理计划（只碰 `YYYY-MM` 目录） |
| `tests/test_check_pics.py` | 15 | `tools/check_pics.py` 自身的判定逻辑（失效引用、大小写不一致、死图、动态拼接豁免） |
| `tests/test_emulator_close.py` | 46 | **关闭模拟器**：受控账号只来自 `启动项`、实例号解析、**MuMuManager 路径推导**（不写死安装路径）、两种子命令顺序的降级、找不到管理器时降级为关窗口、**关闭流程绝不调用会启动游戏的 `Find_windows`**；末尾还有**电源动作**：三种动作各走对 API、睡眠参数不是休眠、关机用 `EWX_POWEROFF`、不加强制标志位、未知动作/特权失败/返回 0/异常 |
| `tests/test_prefs_after_run.py` | 34 | **完成动作偏好的读写与回落**：两个开关默认关闭、电源动作默认睡眠、三种动作可读回、7 种非法值回落、字符串 `"false"` / 数字 / `null` 都回落默认（不做校验会误触发睡眠）、开关与动作互不影响、保存不丢已有键 |
| `tests/test_button_layout.py` | 13 | **按钮区顺序与两个齿轮的分工**：关闭模拟器 / 中断运行 / 完整运行 / 齿轮的先后、两个齿轮走不同信号、尺寸一致（不放大）、运行中只有中断可点 |
| `tests/test_after_run_dialog.py` | 15 | **「完整运行设置」弹窗**（真实控件）：下拉框三项顺序与文案、默认选中睡眠、能读回已保存选择、**开关关闭时下拉框灰化**、切换时灰化跟着变、`values()` 三个键、标签是「电源动作」、走真实保存路径后重开保持选择 |
| `tests/test_after_run_actions.py` | 20 | **完成动作的触发条件**：单跑与中断不触发、取消后什么都不做、两个都开时先关再执行（3 秒间隔）、标记只用一次、注销/关机传对 action、开关关闭时选了动作也不执行、倒计时文案区分三种动作、失败提示用对应名字 |
| `tests/test_countdown_dialog.py` | 14 | **倒计时弹窗本身**（用真实 `QTimer`，不用替身）：`exec()` 会启动定时器、结束后一定停止、归零会 `accept()`、文案随秒数变化；源码级回归保护 `window.py` 必须调 `dialog.exec()` |
| `tests/test_close_emulator_thread.py` | 5 | **关模拟器在后台线程**（用真实 `QThread`）：能发出结果、异常不静默退出、信号名不与 `QThread.finished` 冲突；核心断言「关闭期间主线程仍在处理事件」，并配一条反证用例——同样的假实现同步跑一遍心跳数必须是 0 |
| `tests/test_thirty_settings.py` | 28 | **寮三十配置读写层**（纯逻辑）：缺失/损坏/长度不是 7 都能回落、**次数 0 保留为 0**、非法值回落并给出提示、只改四个键、主副账号校验、**YAML 保真**（flow 单行、引号、注释、长命令不折行）、配置损坏时拒绝写入而不是覆盖 |
| `tests/test_thirty_dialog.py` | 13 | **「寮三十设置」弹窗**（真实控件）：7 列下拉、选项只有代码支持的那几个、**主副账号互斥**（一方改选另一方自动让开、交替切换不撞车、单账号时退化）、`values()` 次数是整数、`validate()` 成功写盘/失败返回 False 不关窗、配置损坏时仍能打开 |
| `tests/test_示例_教学用.py` | 10 | 教学示例（不计入上表的覆盖统计，但会被 `pytest` 一起跑） |

> 新增任务时，先跑 `python -m pytest tests/test_task_registry.py` —— 忘记登记注册表或状态键写错会立刻失败。

---

### 怎么写测试（从零开始）

如果你没写过测试，这一节够用了。**不需要装任何额外东西**，`requirements-dev.txt` 里的 `pytest` 就是全部。

#### 第 0 步：三条规矩

1. **文件名必须是 `test_*.py`**，放在 `tests/` 下，`pytest` 才会自动找到它
2. **函数名必须是 `test_` 开头**，否则不会被当成用例
3. **每个函数只断言一件事**，失败时一眼能看出哪里坏了

就这么简单。没有基类、没有注册、没有配置文件要改。

#### 第 1 步：最简单的用例

新建 `tests/test_我的功能.py`：

```python
# -*- coding: utf-8 -*-
"""一句话说明这个文件在测什么。"""

import main


def test_注册表有七个任务():
    assert len(main.TASK_REGISTRY) == 7
```

跑一下：

```powershell
python -m pytest tests/test_我的功能.py -v
```

输出：

```
tests/test_我的功能.py::test_注册表有七个任务 PASSED   [100%]
```

`assert` 就是「我断言这里应该是这样」。成立就通过，不成立就失败并打印实际值。

> 函数名可以用中文，Python 3 支持。中文名读起来更清楚，失败时一眼知道哪条规则破了。

#### 第 2 步：不要碰真实配置（`tmp_path` + `monkeypatch`）

问题：`Lib.read_config(paths.LAST_TIMES)` 里的路径是**相对路径**（`state/Last_times.yml`）。如果测试直接在项目里跑，会读到、甚至覆盖你真实的冷却历史。

解法：把工作目录临时切到一个空目录。`pytest` 自带两个工具：

- **`tmp_path`** —— 一个全新的临时目录，每个用例都不一样，用完自动清理
- **`monkeypatch.chdir()`** —— 临时切换工作目录，用例结束自动切回来

```python
import os

import Lib


def test_写进去能读出来(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)            # 工作目录 -> 临时目录
    os.makedirs("state", exist_ok=True)    # 建个空的 state/

    Lib.write_config("./state/Test.yml", {"键": "值"})

    assert Lib.read_config("./state/Test.yml")["键"] == "值"
```

关键在于：**只要函数参数里写了 `tmp_path`，pytest 就会自动传一个临时目录给你**。不用自己创建，不用自己删除。

项目里还封装了一个更省事的夹具 `tmp_config_dir`（在 `tests/conftest.py`），它把上面两步都做了：

```python
import main


def test_默认全开(tmp_config_dir):
    # tmp_config_dir 已经帮你 chdir 并建好 config/ 与 state/ 了
    switches = main.read_task_switches()
    assert all(switches.values())
```

#### 第 3 步：一个逻辑测多种情况（`@pytest.mark.parametrize`）

比如「解析时间字符串」，正常值、边界值、坏值都要测。不用写 4 个函数：

```python
import pytest
import main


@pytest.mark.parametrize(
    "raw, expected_hour",
    [
        ("2026-10-19 08:30:00", 8),
        ("2026-10-19 23:59:59", 23),
        ("不是时间", None),
        ("", None),
    ],
)
def test_解析时间(raw, expected_hour):
    moment = main._parse_time(raw)
    if expected_hour is None:
        assert moment is None
    else:
        assert moment.hour == expected_hour
```

`parametrize` 会把它展开成 4 个独立用例。**哪个输入坏了，报告里直接写着**，不用猜。

#### 第 4 步：验证「调用了什么」（`monkeypatch.setattr`）

有些函数不好直接测结果（比如它只负责把数据交给别的函数）。这时可以**临时替换掉被调用的函数**，看它收到了什么。

```python
import main
import paths


def test_开关写进了配置文件(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []

    def 假的写配置(path, data):
        calls.append((path, data))

    # 把 main.write_config 临时换成假的（用例结束自动换回来）
    monkeypatch.setattr(main, "write_config", 假的写配置)

    main.set_task_switch("digui", False)

    assert len(calls) == 1
    path, data = calls[0]
    assert path == paths.GUI_STATE      # 用常量比对，避免硬编码分隔符
    assert data["任务开关"]["digui"] is False
```

这个手法在项目里很有用：测试**不需要真的写盘**，也不需要真的启动游戏窗口，就能验证逻辑对不对。

#### 第 5 步：测试「应该报错」（`pytest.raises`）

中断机制是个好例子：用户点「中断运行」后，下一个检查点必须抛 `TaskStopped`。

```python
import pytest
import Lib


def test_请求中断后检查点抛异常():
    Lib.reset_stop()
    Lib.request_stop()

    with pytest.raises(Lib.TaskStopped):
        Lib.check_stop()

    Lib.reset_stop()   # 清理，别影响下一个用例
```

`with pytest.raises(...)` 的意思是「这行代码**必须**抛出这个异常」。如果它没抛，用例就失败。

#### 第 6 步：跑测试的几种姿势

```powershell
python -m pytest                              # 全部
python -m pytest tests/test_config_io.py      # 单个文件
python -m pytest -k 开关                       # 名字含「开关」的用例
python -m pytest -v                           # 显示每个用例名
python -m pytest -x                           # 第一个失败就停
python -m pytest --lf                         # 只重跑上次失败的
```

#### 第 7 步（重要）：怎么确认测试真的有用

**测试通过 ≠ 测试有用。**

一个测试可能什么都没检查（比如 `assert True`），永远通过；也可能因为写法不对，被测代码坏了它也不报。

验证办法叫**变异测试**：故意把代码改坏，看测试会不会失败。

举个例子，想确认「寮三十今日判定只看寮三十」这条规则有没有被测住：

1. 打开 `main.py`，找到 `("寮三十",)`
2. 改成 `("寮三十", "真蛇")` —— 模拟手滑
3. 跑 `python -m pytest tests/test_task_registry.py`
4. **必须看到失败**。如果还是全绿，说明测试没接上线，得补用例
5. 改回去

本项目 PR4 就是这么验证的：17 个人工变异，全部被抓住。

#### 常见坑

| 现象 | 原因 | 解决 |
|---|---|---|
| `ModuleNotFoundError: No module named 'main'` | 测试跑在别的目录 | 在项目根目录跑；或确认 `tests/conftest.py` 存在（它负责把根目录加进 `sys.path`） |
| 测试改了你的真实 `config/` 或 `state/` | 忘了 `monkeypatch.chdir(tmp_path)` | 所有碰相对路径的用例都要加这个参数 |
| 用例之间互相影响 | 上一个用例留下了状态 | 每个用例自己准备数据、自己清理；别依赖执行顺序 |
| 中文函数名报编码错误 | 文件不是 UTF-8 | 文件头加 `# -*- coding: utf-8 -*-`，保存为 UTF-8 无 BOM |
| 测试通过但功能还是坏的 | 断言太弱（只测了「不报错」） | 用第 7 步的变异测试验证一下 |

#### 这个项目该测什么、不该测什么

**该测**（纯逻辑，跑得飞快，不碰游戏）：

- 注册表一致性、配置读写与回落
- 时间窗判断、冷却计算、字符串解析
- 工具脚本的判定逻辑（`check_pics` 这类）

**不该测**（要真实窗口，慢且不稳定）：

- 图像识别（依赖具体分辨率与皮肤）
- 鼠标点击、键盘输入
- 界面渲染

**不要为了凑覆盖率去测不该测的**。当前 283 个用例覆盖的都是「改错了会静默出错」的地方，这才是测试的价值所在。

---

### 改代码时的约定

- **入口编排**：单账号任务用 `Lib.run_accounts_task`，双账号协作（寮三十）用 `Lib.run_shared_task`；不要在任务模块里手写分隔线/时间窗/遍历账号/冷却判断这套流程
- **模板图**：目录用英文、文件名用中文；改动后必须跑 `tools/check_pics.py`，新增/改名后再跑 `tools/gen_pic_readme.py` 刷新索引
- **行尾**：仓库统一 CRLF（见 `.gitattributes`），用编辑器保存时注意别改成 LF，否则会产生整文件 diff
- **临时产物**：中间脚本、备份、诊断报告写到 `.dsh-scratch/`（已被 `.gitignore` 忽略），不要散落在项目根目录

更细的调用链与实施约束见 [ARCHITECTURE.md](./ARCHITECTURE.md)，提交前的完整约定见 [AGENTS.md](./AGENTS.md)。

---

## 使用注意

1. **工作目录**：请在项目根目录启动脚本，否则 `./pic`、`./config`、`./state` 这些相对路径会失效。
2. **不要抢占键鼠**：任务运行时脚本会置前游戏窗口并移动鼠标，请避免同时操作。
3. **分辨率 / 皮肤**：模板图对 UI 缩放敏感；换分辨率或界面主题后应重截对应 `pic/` 子目录。
4. **冷却状态**：成功完成会写入 `state/Last_times.yml`；若要强制重跑某任务，可删除该账号下对应键或改写时间。
5. **界面偏好**：主题、日志自动滚动、日志字号与完成动作都保存在 `state/gui.json`；删除该文件即恢复默认（浅色 / 自动滚动 / 12 pt / 完成动作都不启用 / 电源动作为睡眠）。
6. **中断运行**：中断是协作式的，任务在下一个检查点（≤0.2 秒）退出，不会强杀线程；中断后不保留进度，下次运行即新的一轮。中断瞬间鼠标键盘输入立即停止，但**不会**把角色拉回庭院。
7. **任务开关**：左侧行的开关只影响「完整运行」，点击 ▶ 始终可以单跑该任务；开关状态存于 `state/Gui_state.yml`，删除该文件即恢复「全部开启」。
8. **关闭模拟器**：红色按钮会直接结束模拟器虚拟机，**游戏内未保存的进度会丢失**，且不会先把角色拉回庭院。它只关闭 `Setting.yml.启动项` 里登记过的账号窗口，手动开的窗口不受影响。优先用 `MuMuManager` 按实例号正常关机（路径从启动命令自动推导，也可在 `Setting.yml` 里用可选的 `模拟器.MuMuManager` 显式指定）；找不到时降级为向窗口发关闭消息，此时虚拟机可能仍在后台运行。
9. **完成动作（关闭模拟器 / 注销 / 睡眠 / 关机）**：只在「完整运行成功且未中断」时触发，单跑与中断都不会动电脑。执行前有 10 秒可取消倒计时。电源动作三选一：**注销**后系统服务继续运行，可以远程接管；**睡眠**是 S3 而非休眠，唤醒 1～3 秒即可恢复，但远程连不上；**关机**后远程同样连不上。动作失败时界面会明确报错（常见原因是当前账户没有关机特权或被电源策略禁用）。
10. **协作与弹窗**：脚本会尝试自动关闭协作邀请与常见弹窗；若布局变化导致误判，优先检查 `pic/common` 或 `pic/courtyard` 中的相关模板。
11. **硬编码坐标**：极少数界面（如庭院卷轴）仍使用绝对坐标，窗口位置/分辨率变化后可能失效。
12. **日志排查**：
   - 完整运行日志：`logs/<YYYY-MM>/<YYYY-MM-DD>/console_output_*.log`
   - 单任务运行日志：`logs/<YYYY-MM>/<YYYY-MM-DD>/single_<key>_*.log`
   - GUI 崩溃：`logs/app_crash.log`
   - 控制台匹配得分（`INFO- 0.0xx ...`）可辅助判断阈值是否过严/过松。
   - 清理旧日志：`python tools/clean_logs.py`（默认只预览，`--apply` 才删除，默认保留 6 个月）。

---

## 项目结构（简）

```
Paper_sweeper/
├── GUI.py                 # 图形界面入口（环境变量 / 日志 / 异常钩子）
├── GUI.spec               # PyInstaller 打包配置
├── build_exe.py           # 一键打包脚本（调用 GUI.spec，产物输出到根目录）
├── main.py                # 任务注册表、完整/单任务运行编排、任务开关与日志 Tee
├── Lib.py                 # 识别、点击、界面状态机、配置、编队
├── paths.py               # 配置/状态文件路径常量 + 旧布局迁移
├── ui/                    # 界面层（theme → icons → widgets → panels → window）
├── Task_SignIn.py         # 登录收菜
├── Task_Jiejieyangcheng.py# 结界养成
├── Task_Digui.py          # 地域鬼王
├── Task_Thirty.py         # 寮三十与真蛇
├── Task_JiejieFight.py    # 结界突破
├── Task_Shouliezhan.py    # 狩猎战 / 阴界
├── Task_Fengmo.py         # 逢魔之时
├── pic/                   # 界面模板图（目录英文、文件名中文，详见 pic/README.md）
├── tools/                 # 开发辅助脚本（不参与打包）
│   ├── check_pics.py      # 模板图引用检查
│   ├── clean_logs.py      # 旧日志清理（按年月分层，默认预览）
│   └── gen_pic_readme.py  # 生成 pic/README.md 索引
├── tests/                 # pytest 用例（纯逻辑，不依赖游戏窗口）
├── dev/                   # 本地调试脚本（不入库，详见 dev/README.md）
├── config/                # Setting.yml（静态配置，用户手改）
├── state/                 # Last_times.yml / Gui_state.yml / gui.json（程序读写）
├── logs/                  # 运行日志（<年-月>/<日期>/，含 app_crash.log）
├── requirements.txt       # 运行期依赖（精确版本）
├── requirements-dev.txt   # 测试 / 静态检查 / 打包依赖
├── pyproject.toml         # 工具配置（pytest / ruff）与项目元信息
├── AGENTS.md              # 协作与编码约定（开发向）
└── ARCHITECTURE.md        # 架构与任务地图（开发向）
```

> `runtime.py`、`config/`、`state/`、`logs/`、`GUI.exe`、`.dsh-scratch/` 均为运行期产物或本地目录，
> 已被 `.gitignore` 忽略，故不列在上方结构里。打包中间产物已从源码树移到
> `.dsh-scratch/build-tmp/pyinstaller/`，不再产生根目录 `build/`。
>
> **`config/` 与 `state/` 的区别**：前者是**用户手改**的静态配置，后者是**程序读写**的运行期状态。
> 删除 `state/` 即恢复初始状态（所有任务视为从未完成、开关全开、偏好回默认）。

更细的调用链、状态机与实施约束见 [ARCHITECTURE.md](./ARCHITECTURE.md)；提交代码前的约定见 [AGENTS.md](./AGENTS.md)。

---

## 常见问题

**Q：点击「完整运行」后立即报 `ModuleNotFoundError: No module named 'runtime'`？**  
A：项目根目录缺少 `runtime.py`。创建该文件并写入 `stop_thread = False`（或执行 `python build_exe.py` 自动生成）。该文件已被 `.gitignore` 忽略，克隆仓库后不会自带。

**Q：一直提示「未检测到窗口」？**  
A：检查游戏是否已启动、窗口标题是否包含 `Setting.yml` 中的账号名（`master`/`slaves`）；若走自动启动，核对 `启动命令` 路径与 `-v` 实例号。

**Q：某个任务总是「未检测到 xxx」？**  
A：多为模板图与当前 UI 不符或阈值过严。用临时调试脚本对目标模板 `Flag_show=1` 查看红框是否命中，再替换 `pic/` 下对应图片。

**Q：任务全部 SKIP？**  
A：多半是冷却未到。查看 `state/Last_times.yml`，或确认当前时间是否落在任务时间窗内。点击 ▶ 单独运行同样受这些限制，不会强制重跑。

**Q：点了 ▶ 没反应 / 只有一行提示？**  
A：先看控制台是否出现 `SKIP-`。单任务运行沿用与完整运行一致的冷却和时间窗判断；若行首仍是 `!`，通常就是条件未满足或该任务本次未成功。

**Q：行首 `!` 是什么意思？和开关有关吗？**  
A：`!` 表示该任务今天还没有完成（依据 `Last_times.yml` 的当天记录；「登录收菜」要求 5 个子项全部完成才算 ✓）。它与最右侧开关无关：开关只决定是否参与「完整运行」。

**Q：我把某个任务的开关关了，为什么点 ▶ 还能跑？**  
A：这是有意设计：开关只影响「完整运行」，▶ 是你的显式单跑操作，始终允许（仍受任务自身冷却/时间窗约束）。

**Q：齿轮点了只有提示？**  
A：只有「寮三十 / 真蛇」这一行接入了配置弹窗（副本 / 次数 / 主副账号），其余 6 行仍是占位，需要调参数请直接改 `config/Setting.yml`。

**Q：寮三十的副本/次数为什么只能下拉选，不能自己填数字？**  
A：因为任务代码只实现了这几种取值：`match Fuben` 只有 4 个分支，`match Times` 只认 1 / 30 / 50（外加 `0` 表示当天不刷）。填其它数字不会报错，而是让小纸人计数那一步静默跳过、流程失效——所以界面只给合法的枚举值。

**Q：在弹窗里改了寮三十配置，会把我 `Setting.yml` 里的注释和格式弄乱吗？**  
A：不会。写回时只动 `寮三十` 这一段的四个键，`启动项` / `结界突破`、注释、引号、缩进以及 `副本: [...]` 的单行写法都保持原样。

**Q：能否按分辨率自动适配？**  
A：当前版本依赖人工维护模板图与少量坐标，没有自动缩放适配层。

---

## 免责声明

本项目是一个外部工具，旨在自动化阴阳师的部分每日任务。它被设计成仅通过现有用户界面与游戏交互，并遵守相关法律法规。该软件包旨在提供简化和用户通过功能与游戏交互，并且它不打算以任何方式破坏游戏平衡或提供任何不公平的优势。该软件包不会以任何方式修改任何游戏文件或游戏代码。

This project is an external tool designed to automate some of Onmyoji's Dailies. It is designed to interact with the game only through the existing user interface and to comply with relevant laws and regulations. This package is designed to provide simplicity and user interaction with the game through features, and it is not intended to upset the balance of the game in any way or provide any unfair advantage. This package does not modify any game files or game code in any way.

本软件开源、免费，仅供学习交流使用。开发者团队拥有本项目的最终解释权。使用本软件产生的所有问题与本项目与开发者团队无关。若您遇到商家使用本软件进行代练并收费，可能是设备与时间等费用，产生的问题及后果与本软件无关。
