# -*- coding: utf-8 -*-
"""调试截图保存的测试。

这一版的重点是「每次匹配判定都出一张图」这条主线的几个硬约束：

1. 默认档位（off）完全零开销，不建目录、不写盘；
2. `miss` 只存未命中，`all` 逐张全存，同一帧连调 5 次就是 5 张图（不做去重）；
3. 图片明细只落 `index.tsv`，控制台一条 `SHOT- #` 都不许有；
4. 写盘出错不影响匹配结果，但连续失败 3 次要熔断；
5. `TaskStopped` 不能被 `_record_shot` 的兜底 except 吃掉。

全部用合成图，不碰游戏窗口，也不依赖真实截图。
"""

import os

import numpy as np
import pytest

import Lib


@pytest.fixture(autouse=True)
def _reset_shot_state(monkeypatch):
    """每个用例前后都把截图状态清干净，避免用例之间互相影响"""
    monkeypatch.delenv("PAPER_SHOTS", raising=False)
    monkeypatch.delenv("PAPER_SHOTS_ALL", raising=False)
    Lib._SHOT_MODE = "off"
    Lib._SHOT_DIR = None
    Lib._SHOT_SEQ = 0
    Lib._SHOT_SAVED = 0
    Lib._SHOT_BYTES = 0
    Lib._SHOT_FAILS = 0
    Lib._SHOT_INDEX = None
    Lib._SHOT_LIMIT = 8000
    Lib._SHOT_SKIP_TEMPLATES = ()
    Lib._SHOT_SKIP_ALL = False
    yield
    if Lib._SHOT_INDEX is not None:
        Lib._SHOT_INDEX.close()
        Lib._SHOT_INDEX = None
    Lib._SHOT_MODE = "off"


def _frame(width=160, height=120):
    """造一张有纹理的三通道图，避免纯色被 JPEG 压成同样大小的文件"""
    rng = np.random.default_rng(7)
    return rng.integers(0, 255, size=(height, width, 3), dtype=np.uint8)


def _log_path(tmp_path):
    """造一个形如 <prefix>_<YYYY-MM-DD_HH-MM-SS>.log 的假日志路径"""
    return str(tmp_path / "console_output_2026-11-05_10-30-00.log")


def _start(tmp_path, mode, log_path=None):
    Lib.begin_shots(log_path or _log_path(tmp_path), mode=mode)
    return Lib._SHOT_DIR


# --------------------------------------------------------------- 档位开关


def test_默认档位不产生目录(tmp_path):
    """mode 缺省且没有环境变量、没有 gui.json 时，应保持 off 且不建任何目录"""
    Lib.begin_shots(_log_path(tmp_path))
    assert Lib._SHOT_MODE == "off"
    assert Lib._SHOT_DIR is None
    assert os.listdir(tmp_path) == []


def test_非法档位一律回落off(tmp_path):
    _start(tmp_path, "随便写的值")
    assert Lib._SHOT_MODE == "off"
    assert Lib._SHOT_DIR is None


def test_off档调用record_shot不写盘(tmp_path):
    frame = _frame()
    Lib.begin_shots(_log_path(tmp_path))  # 不传 mode ⇒ off
    Lib._record_shot(frame, "match_model", "./pic/common/确定.png", 0.3, 0.05, True,
                     Left_up=(10, 10), Right_down=(50, 50))
    assert Lib._SHOT_SAVED == 0
    assert os.listdir(tmp_path) == []


def test_环境变量可以开档(tmp_path, monkeypatch):
    """begin_shots 不传 mode 时，PAPER_SHOTS 应生效"""
    monkeypatch.setenv("PAPER_SHOTS", "all")
    Lib.begin_shots(_log_path(tmp_path))
    assert Lib._SHOT_MODE == "all"
    assert os.path.isdir(Lib._SHOT_DIR)


def test_显式参数优先于环境变量(tmp_path, monkeypatch):
    monkeypatch.setenv("PAPER_SHOTS", "all")
    Lib.begin_shots(_log_path(tmp_path), mode="off")
    assert Lib._SHOT_MODE == "off"


# ----------------------------------------------------------- miss / all 语义


def test_miss档只存未命中(tmp_path):
    frame = _frame()
    _start(tmp_path, "miss")
    Lib._record_shot(frame, "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                     Left_up=(10, 10), Right_down=(50, 50))
    assert Lib._SHOT_SAVED == 0, "命中不该存档"
    Lib._record_shot(frame, "match_model", "./pic/common/确定.png", 0.900, 0.05, False,
                     Left_up=(10, 10), Right_down=(50, 50))
    assert Lib._SHOT_SAVED == 1
    files = [n for n in os.listdir(Lib._SHOT_DIR) if n.endswith(".jpg")]
    assert len(files) == 1
    assert "_miss_" in files[0]


def test_all档每次匹配都出一张(tmp_path):
    """同一帧连调 5 次 ⇒ 5 个文件 + index.tsv 6 行（含表头），序号连续 1~5"""
    frame = _frame()
    _start(tmp_path, "all")
    for _ in range(5):
        Lib._record_shot(frame, "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                         Left_up=(10, 10), Right_down=(50, 50))

    assert Lib._SHOT_SAVED == 5, "不做去重，5 次调用必须留 5 张"
    jpgs = sorted(n for n in os.listdir(Lib._SHOT_DIR) if n.endswith(".jpg"))
    assert len(jpgs) == 5
    assert [n[:6] for n in jpgs] == ["000001", "000002", "000003", "000004", "000005"]

    lines = open(os.path.join(Lib._SHOT_DIR, "index.tsv"), encoding="utf-8").read().splitlines()
    assert len(lines) == 6
    assert lines[0].split("\t")[0] == "序号"
    assert [line.split("\t")[0] for line in lines[1:]] == ["1", "2", "3", "4", "5"]


def test_不留每张图的log行(tmp_path, capsys):
    """控制台不许出现逐张 SHOT- 行；收尾只有一行汇总"""
    frame = _frame()
    _start(tmp_path, "all")
    for _ in range(3):
        Lib._record_shot(frame, "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                         Left_up=(10, 10), Right_down=(50, 50))
    Lib.end_shots()

    out = capsys.readouterr().out
    assert "SHOT- #" not in out, "逐张明细行已取消，图片清单只落 index.tsv"
    shot_lines = [line for line in out.splitlines() if "SHOT-" in line]
    assert len(shot_lines) == 1, "控制台只应有一条汇总"
    assert "本次共保存 3 张" in shot_lines[0]


def test_达到上限后停止(tmp_path, monkeypatch):
    frame = _frame()
    _start(tmp_path, "all")
    Lib._SHOT_LIMIT = 3
    for _ in range(6):
        Lib._record_shot(frame, "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                         Left_up=(10, 10), Right_down=(50, 50))
    assert Lib._SHOT_SAVED == 3
    assert len([n for n in os.listdir(Lib._SHOT_DIR) if n.endswith(".jpg")]) == 3


# --------------------------------------------------------------- 命名与写盘


def test_模板名里的非法字符被替换(tmp_path):
    name = Lib._shot_name("match_model", './pic/common/寄养/入:口?*.png', 0.312, False)
    assert name.endswith("_miss_.jpg") or "_miss_" in name
    for bad in '\\/:*?"<>|':
        assert bad not in name


def test_index_tsv列数与时间格式(tmp_path):
    frame = _frame(320, 240)
    _start(tmp_path, "all")
    Lib._record_shot(frame, "models_rows", "./pic/team/确定.png", 0.123, 0.05, True,
                     Left_up=None, Offset=(100, 50))

    line = open(os.path.join(Lib._SHOT_DIR, "index.tsv"), encoding="utf-8").read().splitlines()[1]
    cols = line.split("\t")
    assert len(cols) == 10, "列数与表头必须一致"
    assert cols[0] == "1"
    assert len(cols[1]) == 12 and cols[1][2] == ":" and cols[1][5] == ":", "时间形如 HH:MM:SS.mmm"
    assert cols[2] == "hit"
    assert cols[3] == "models_rows"
    assert cols[5] == "0.123"
    assert cols[7] == "320x240"
    assert cols[8] == "100,50", "裁剪偏移要写进 index.tsv 供对坐标"
    assert cols[9].endswith(".jpg")


def test_裁剪偏移缺省写短横(tmp_path):
    _start(tmp_path, "all")
    Lib._record_shot(_frame(), "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                     Left_up=(10, 10), Right_down=(50, 50))
    line = open(os.path.join(Lib._SHOT_DIR, "index.tsv"), encoding="utf-8").read().splitlines()[1]
    assert line.split("\t")[8] == "-"


def test_不画框时原图不被修改(tmp_path):
    """Left_up=None 时直接把原图交给写盘，绝不能顺手在上面画东西"""
    frame = _frame()
    before = frame.copy()
    _start(tmp_path, "all")
    Lib._record_shot(frame, "models_rows", "./pic/team/确定.png", 0.300, 0.05, True,
                     Left_up=None, Offset=(0, 0))
    assert np.array_equal(frame, before)


def test_有框时会画在副本上(tmp_path):
    frame = _frame()
    before = frame.copy()
    _start(tmp_path, "all")
    Lib._record_shot(frame, "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                     Left_up=(10, 10), Right_down=(50, 50))
    assert np.array_equal(frame, before), "画框必须画在副本上"


def test_中文路径能真的写盘(tmp_path):
    """cv2.imwrite 遇中文路径会静默返回 False，这里验证走的是 imencode+tofile"""
    target = tmp_path / "中文目录" / "截图.jpg"
    target.parent.mkdir()
    assert Lib.Img_write_ch(str(target), _frame()) is True
    assert target.exists() and target.stat().st_size > 0


def test_写盘内容能被读回(tmp_path):
    frame = _frame(200, 100)
    _start(tmp_path, "all")
    Lib._record_shot(frame, "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                     Left_up=(10, 10), Right_down=(50, 50))
    jpg = os.path.join(Lib._SHOT_DIR, [n for n in os.listdir(Lib._SHOT_DIR) if n.endswith(".jpg")][0])
    back = Lib.Img_read_ch(jpg)
    assert back is not None
    assert back.shape == frame.shape


# ------------------------------------------------------------------- 健壮性


def test_连续写盘失败三次熔断(tmp_path, monkeypatch):
    _start(tmp_path, "all")
    monkeypatch.setattr(Lib, "Img_write_ch", lambda *a, **k: False)
    for _ in range(4):
        Lib._record_shot(_frame(), "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                         Left_up=(10, 10), Right_down=(50, 50))
    assert Lib._SHOT_MODE == "off", "连续失败 3 次后必须自关"
    assert Lib._SHOT_SAVED == 0


def test_成功一次就清零失败计数(tmp_path, monkeypatch):
    """熔断只针对「连续」失败，中间成功过一次就不该被累计"""
    _start(tmp_path, "all")
    calls = {"n": 0}
    real = Lib.Img_write_ch

    def flaky(path, img, quality=80):
        calls["n"] += 1
        if calls["n"] % 2 == 1:
            return False
        return real(path, img, quality)

    monkeypatch.setattr(Lib, "Img_write_ch", flaky)
    for _ in range(6):
        Lib._record_shot(_frame(), "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                         Left_up=(10, 10), Right_down=(50, 50))
    assert Lib._SHOT_MODE == "all", "隔次失败不该熔断"
    assert Lib._SHOT_SAVED == 3


def test_TaskStopped不被吃掉(tmp_path, monkeypatch):
    """中断必须一路抛到 main.py，不能被兜底 except 吞掉"""
    _start(tmp_path, "all")

    def boom(*a, **k):
        raise Lib.TaskStopped()

    monkeypatch.setattr(Lib, "_draw_boxes", boom)
    with pytest.raises(Lib.TaskStopped):
        Lib._record_shot(_frame(), "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                         Left_up=(10, 10), Right_down=(50, 50))


def test_普通异常不影响匹配结果(tmp_path, monkeypatch):
    _start(tmp_path, "all")

    def boom(*a, **k):
        raise RuntimeError("磁盘炸了")

    monkeypatch.setattr(Lib, "_draw_boxes", boom)
    # 不抛异常 = 匹配流程不会被截图拖垮
    Lib._record_shot(_frame(), "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                     Left_up=(10, 10), Right_down=(50, 50))
    assert Lib._SHOT_SAVED == 0
    assert Lib._SHOT_FAILS == 1


def test_排除名单默认不排除任何东西(tmp_path):
    """默认空名单：必然 miss 的探测也照存，不给自己开后门"""
    _start(tmp_path, "all")
    Lib._record_shot(_frame(), "match_model", "./pic/common/拒绝协作.png", 0.900, 0.01, False,
                     Left_up=(10, 10), Right_down=(50, 50))
    assert Lib._SHOT_SAVED == 1


def test_排除名单命中则跳过(tmp_path, monkeypatch):
    _start(tmp_path, "all")
    Lib._SHOT_SKIP_TEMPLATES = ("拒绝协作.png",)
    Lib._record_shot(_frame(), "match_model", "./pic/common/拒绝协作.png", 0.900, 0.01, False,
                     Left_up=(10, 10), Right_down=(50, 50))
    assert Lib._SHOT_SAVED == 0
    Lib._SHOT_SKIP_ALL = True
    Lib._record_shot(_frame(), "match_model", "./pic/common/拒绝协作.png", 0.900, 0.01, False,
                     Left_up=(10, 10), Right_down=(50, 50))
    assert Lib._SHOT_SAVED == 1, "_SHOT_SKIP_ALL 应能整体绕过排除名单"


# -------------------------------------------------------------- 与 log 的绑定


def test_截图目录名沿用日志时间戳(tmp_path):
    log_path = str(tmp_path / "console_output_2026-11-05_10-30-00.log")
    Lib.begin_shots(log_path, mode="all")
    assert os.path.basename(Lib._SHOT_DIR) == "shots_2026-11-05_10-30-00"
    assert os.path.dirname(Lib._SHOT_DIR) == str(tmp_path)


def test_end_shots可重复调用(tmp_path):
    _start(tmp_path, "all")
    Lib._record_shot(_frame(), "match_model", "./pic/common/确定.png", 0.300, 0.05, True,
                     Left_up=(10, 10), Right_down=(50, 50))
    Lib.end_shots()
    Lib.end_shots()  # 再调一次不该炸，也不该重复打汇总
    assert Lib._SHOT_MODE == "off"
    assert Lib._SHOT_INDEX is None


def test_目录建不出来时自关(tmp_path, monkeypatch):
    """建目录失败不能让整场运行挂掉，只需关掉截图继续跑"""
    monkeypatch.setattr(Lib.os, "makedirs", lambda *a, **k: (_ for _ in ()).throw(OSError("没权限")))
    Lib.begin_shots(_log_path(tmp_path), mode="all")
    assert Lib._SHOT_MODE == "off"
