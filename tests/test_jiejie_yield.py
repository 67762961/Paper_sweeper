# -*- coding: utf-8 -*-
"""寄养收益数字识别：jiejie_read_yield。

测试的重点不是「字形比对准不准」（那是阈值与模板的事，已用真实截图验证过），
而是整条管线的行为约定：

1. 空白画面 / 结构不对时返回 None，绝不猜一个数；
2. 两行数字时只读下面那行（收益行），不会把「式神经验」读成收益；
3. 数字右对齐，左边混进来的汉字碎片与 `+` 号会被丢掉；
4. 认不出的字形返回 None，而不是硬套一个最像的数字。

为了让用例不依赖真实截图（那是运行期素材，不入库），
这里用 pic/guild/收益数字*.png 这 10 张原型本身拼出「看起来像面板」的图：
把原型缩放贴到画布上，字形尺寸与间距都按真实截图的实测比例来。
"""
import cv2
import numpy as np
import pytest

import Lib


# ---------------------------------------------------------------- 拼图工具

# 真实截图实测：字高 24 像素、数字间距 3~5 像素、行距约 41 像素
GLYPH_H = 24
DIGIT_GAP = 4
LINE_GAP = 17
LEFT_LABEL = 20      # 左侧「式神经验」「勾玉」等汉字碎片占位宽度
PLUS_W = 19          # `+` 号宽度，宽/高≈0.90，必须被过滤掉


@pytest.fixture(autouse=True)
def _reset_caches():
    Lib.clear_template_cache()
    Lib.clear_digit_cache()
    yield
    Lib.clear_template_cache()
    Lib.clear_digit_cache()


def _digit_image(digit):
    """取原型灰度图（32x28，0~1），裁成只有笔画的最小外接块"""
    Lib._digit_prototypes()      # 先载入，保证缓存里有
    proto = Lib._DIGIT_PROTOTYPES[digit]
    # 原型是平均后的灰度画布，笔画处接近 1；阈值取 0.4 保住细笔画（比如 1）
    ink = (proto > 0.4).astype(np.uint8) * 255
    cols = np.nonzero(ink.any(axis=0))[0]
    rows = np.nonzero(ink.any(axis=1))[0]
    assert cols.size and rows.size, "原型里必须有笔画"
    return ink[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]


def _draw_digits(canvas, y, x_right, text):
    """把 text 里的数字按右对齐画到 canvas 上，返回最左端 x

    注意按**高度等比**缩放：真实字形是 15x25（宽/高≈0.6），
    如果把宽度原样保留、只把高度压到 GLYPH_H，宽高比会变成 0.79，
    正好被「宽 ≤ 高×0.78」那条过滤规则误杀——那是用来滤 `+` 号的。
    """
    x = x_right
    for ch in reversed(text):
        glyph = _digit_image(int(ch))
        h, w = glyph.shape
        new_w = max(1, int(round(w * GLYPH_H / h)))
        scaled = cv2.resize(glyph, (new_w, GLYPH_H), interpolation=cv2.INTER_NEAREST)
        x -= scaled.shape[1]
        region = canvas[y:y + GLYPH_H, x:x + scaled.shape[1]]
        region[scaled > 128] = 60
        x -= DIGIT_GAP
    return x + DIGIT_GAP


def _make_panel(exp_value, yield_value, width=600, height=400):
    """拼一张「右侧面板」：米色底 + 两行数字（上行经验、下行收益）"""
    canvas = np.full((height, width, 3), (182, 192, 200), dtype=np.uint8)

    base_y = int(height * 0.55)
    right = width - 40

    # 第一行：式神经验 +NNNNN
    x_left = _draw_digits(canvas, base_y, right, str(exp_value))
    # `+` 号：19x21 的十字，宽/高 0.90，必须被宽高比过滤掉
    plus_y = base_y + 2
    canvas[plus_y + 8:plus_y + 13, x_left - PLUS_W - 8:x_left - 8] = 60
    canvas[plus_y:plus_y + 21, x_left - PLUS_W + 2:x_left - 8 + 2] = 60

    # 第二行：勾玉 +NN（收益行）
    y2 = base_y + GLYPH_H + LINE_GAP
    _draw_digits(canvas, y2, right, str(yield_value))

    return canvas


# ------------------------------------------------------------ 正常读数


def test_reads_yield_from_last_line():
    """两行数字时读下面那行，不能把式神经验当成收益"""
    panel = _make_panel(exp_value=23520, yield_value=118)
    assert Lib.jiejie_read_yield(panel) == 118


@pytest.mark.parametrize("value", [42, 50, 59, 67, 76, 118, 134, 151])
def test_reads_each_known_yield_value(value):
    """收益表里出现过的值都要能读出来（含四星太鼓的 42、四星斗鱼的 50）"""
    panel = _make_panel(exp_value=23520, yield_value=value)
    assert Lib.jiejie_read_yield(panel) == value


@pytest.mark.parametrize("value", [10, 99, 100, 202, 999])
def test_reads_arbitrary_values(value):
    """逐位识别对任意数值成立，不依赖「预先知道的 7 个值」"""
    panel = _make_panel(exp_value=6720, yield_value=value)
    assert Lib.jiejie_read_yield(panel) == value


def test_long_experience_number_does_not_leak():
    """式神经验是 5 位数，不能被当成收益读出来"""
    panel = _make_panel(exp_value=13440, yield_value=42)
    assert Lib.jiejie_read_yield(panel) == 42


# ------------------------------------------------------------ 认不出时


def test_blank_image_returns_none():
    """空白画面没有任何字形，必须返回 None 而不是 0"""
    blank = np.full((400, 600, 3), (182, 192, 200), dtype=np.uint8)
    assert Lib.jiejie_read_yield(blank) is None


def test_single_line_returns_none():
    """只有一行数字时结构不对，返回 None（宁可漏也不猜）"""
    canvas = np.full((400, 600, 3), (182, 192, 200), dtype=np.uint8)
    _draw_digits(canvas, 250, 560, "118")
    assert Lib.jiejie_read_yield(canvas) is None


def test_unknown_glyph_returns_none():
    """长得不像任何数字的字形要返回 None，不能硬套最像的那个"""
    panel = _make_panel(exp_value=23520, yield_value=118)
    # 把收益行的最后一个数字涂成一个方块（既不像 0~9 任何一个）
    h, w = panel.shape[0:2]
    panel[h - 120:h - 120 + GLYPH_H, w - 60:w - 40] = 60
    assert Lib.jiejie_read_yield(panel) is None


def test_box_out_of_range_returns_none():
    """裁剪区落在画面外时不抛异常，返回 None"""
    panel = _make_panel(exp_value=23520, yield_value=118)
    assert Lib.jiejie_read_yield(panel, Box=(5000, 5000, 100, 100)) is None


# ------------------------------------------------------- 右对齐与切段


def test_rightmost_run_skips_left_fragments():
    """数字段左边的汉字碎片与 `+` 号不能混进数字里"""
    line = [
        (0, 100, 30, 33, np.zeros((33, 30), bool)),     # 汉字碎片（宽/高 0.9）
        (100, 100, 19, 21, np.zeros((21, 19), bool)),   # `+` 号
        (140, 100, 8, 23, np.ones((23, 8), bool)),      # 1
        (152, 100, 9, 24, np.ones((24, 9), bool)),      # 1
        (166, 100, 15, 25, np.ones((25, 15), bool)),    # 8
    ]
    run = Lib._digit_rightmost_run(line)
    assert [g[0] for g in run] == [140, 152, 166], "必须只取最右边连续那段"


def test_rightmost_run_returns_empty_for_single_glyph():
    """只有一个字形时不算数字段（可能是标点或 `+` 的残片）"""
    line = [(100, 100, 15, 25, np.ones((25, 15), bool))]
    assert Lib._digit_rightmost_run(line) == []


def test_rightmost_run_returns_empty_for_empty_line():
    assert Lib._digit_rightmost_run([]) == []


# ------------------------------------------------------------- 模板缓存


def test_prototypes_cover_all_ten_digits():
    """0~9 必须齐全，缺一个就会把那个数字读成别的"""
    protos = Lib._digit_prototypes()
    assert sorted(protos) == list(range(10))
    for digit, canvas in protos.items():
        assert canvas.shape == (32, 28), f"{digit} 的画布尺寸不对"


def test_digit_pics_are_literal_paths():
    """10 条路径必须是字面量，否则 check_pics.py 会把目录整体豁免"""
    for digit, path in Lib.JIEJIE_DIGIT_PICS.items():
        assert isinstance(path, str) and "{" not in path
        assert path == f"./pic/guild/收益数字{digit}.png"
