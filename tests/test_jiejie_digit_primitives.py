# -*- coding: utf-8 -*-
"""收益数字识别底层原语：墨迹掩码、连通域切字、行聚类、右对齐切段、画布归一化。

这些原语是 jiejie_read_yield 的地基，单独测它们的好处是：
读数出错时能立刻定位是「切字切错了」还是「比对比错了」，
而不是只能看到一个整体的 None。

全部用合成图，不依赖真实截图（那是运行期素材，不入库）。
"""
import numpy as np
import pytest

import Lib


# ---------------------------------------------------------------- 造字工具


def _draw_digit_mask(mask, x, y, pattern):
    """在 bool 掩码上画一个由字符串描述的字形

    pattern 每行一个字符串，'#' 是墨迹、'.' 是空白。
    """
    for dy, row in enumerate(pattern):
        for dx, ch in enumerate(row):
            if ch == "#":
                mask[y + dy, x + dx] = True


# 一个 8x24 的假数字：宽/高 0.33，能通过「宽 <= 高*0.78」的过滤
NARROW = ["..#..#.."] * 24
# 一个 15x24 的假数字：宽/高 0.63，也能通过
WIDE = ["#########" + "######"] * 24
# `+` 号：19x21，宽/高 0.90，必须被宽高比过滤掉
PLUS = ["#########"] + ["#########"] * 0 + ["#########"]


def _glyph(x, y, w, h, fill=True):
    """直接造一个字形元组 (x, y, w, h, mask)"""
    return (x, y, w, h, np.ones((h, w), dtype=bool) if fill else np.zeros((h, w), dtype=bool))


# ------------------------------------------------------------ 墨迹掩码


def test_ink_mask_picks_dark_low_saturation():
    """灰黑字算墨迹，米色面板与彩色不算"""
    img = np.full((20, 30, 3), (182, 192, 200), dtype=np.uint8)   # 米色面板
    img[5:10, 5:10] = (60, 60, 60)                                # 灰黑字
    img[12:17, 5:10] = (30, 200, 30)                              # 高饱和绿色

    mask = Lib._digit_ink_mask(img)

    assert mask[7, 7], "灰黑字必须是墨迹"
    assert not mask[14, 7], "高饱和彩色不是墨迹"
    assert not mask[0, 0], "米色面板不是墨迹"


def test_ink_mask_threshold_is_on_luminance():
    """亮度 150 是分界：149 算墨迹，151 不算"""
    img = np.full((4, 4, 3), 200, dtype=np.uint8)
    img[0:2, :] = 149
    img[2:4, :] = 151

    mask = Lib._digit_ink_mask(img)

    assert mask[0, 0] and mask[1, 0]
    assert not mask[2, 0] and not mask[3, 0]


# ------------------------------------------------------------ 连通域切字


def test_glyphs_filters_by_size_and_aspect():
    """尺寸过滤 + 宽高比过滤：`+` 号（宽/高 0.90）必须被丢掉"""
    img = np.full((200, 200, 3), (182, 192, 200), dtype=np.uint8)

    # 合格：15x24，宽/高 0.63
    img[50:74, 20:35] = 60
    # 不合格：19x21，宽/高 0.90（`+` 号）
    img[50:71, 60:79] = 60
    # 不合格：太矮（8x10）
    img[100:110, 20:28] = 60

    glyphs = Lib._digit_glyphs(img, 0, 0)
    sizes = sorted((g[2], g[3]) for g in glyphs)

    assert (15, 24) in sizes, "合格字形必须留下"
    assert (19, 21) not in sizes, "`+` 号必须被宽高比过滤掉"
    assert (8, 10) not in sizes, "过矮的字形必须被滤掉"


def test_glyphs_returns_absolute_coordinates():
    """传了原点偏移时，返回的坐标要加回偏移量"""
    img = np.full((200, 200, 3), (182, 192, 200), dtype=np.uint8)
    img[50:74, 20:35] = 60

    glyphs = Lib._digit_glyphs(img, 10, 30)

    assert len(glyphs) == 1
    x, y, _w, _h, _mask = glyphs[0]
    assert (x, y) == (20, 50), "坐标必须是相对整张图的绝对坐标"


def test_glyphs_carries_bitmask():
    """每个字形要带自己的局部二值掩码，后面归一化画布要用"""
    img = np.full((100, 100, 3), (182, 192, 200), dtype=np.uint8)
    img[50:74, 20:35] = 60

    glyphs = Lib._digit_glyphs(img, 0, 0)

    x, y, w, h, mask = glyphs[0]
    assert mask.shape == (h, w)
    assert mask.all(), "整块涂黑的字形，掩码里应该全是墨迹"


# ------------------------------------------------------------ 行聚类


def test_group_lines_splits_by_vertical_overlap():
    """纵向不重叠的字形要分成两行"""
    glyphs = [_glyph(10, 10, 15, 24), _glyph(30, 10, 15, 24), _glyph(10, 60, 15, 24)]

    lines = Lib._digit_group_lines(glyphs)

    assert len(lines) == 2
    assert len(lines[0]) == 2 and len(lines[1]) == 1


def test_group_lines_sorts_by_x():
    """行内要按 x 排序，否则右对齐取段会取错"""
    glyphs = [_glyph(50, 10, 15, 24), _glyph(10, 10, 15, 24), _glyph(30, 10, 15, 24)]

    lines = Lib._digit_group_lines(glyphs)

    assert [g[0] for g in lines[0]] == [10, 30, 50]


def test_group_lines_tolerates_small_vertical_jitter():
    """上下差几个像素仍算同一行（同一行数字不会绝对对齐）"""
    glyphs = [_glyph(10, 10, 15, 24), _glyph(30, 13, 15, 24)]

    lines = Lib._digit_group_lines(glyphs)

    assert len(lines) == 1


# ------------------------------------------------------- 右对齐切段


def test_rightmost_run_skips_left_fragments():
    """数字段左边的汉字碎片与 `+` 号不能混进数字里"""
    line = [
        _glyph(0, 100, 30, 33),      # 汉字碎片
        _glyph(100, 100, 19, 21),    # `+` 号
        _glyph(140, 100, 8, 23),     # 1
        _glyph(152, 100, 9, 24),     # 1
        _glyph(166, 100, 15, 25),    # 8
    ]

    run = Lib._digit_rightmost_run(line)

    assert [g[0] for g in run] == [140, 152, 166], "必须只取最右边连续那段"


def test_rightmost_run_returns_empty_for_single_glyph():
    """只有一个字形时不算数字段（可能是标点或 `+` 的残片）"""
    assert Lib._digit_rightmost_run([_glyph(100, 100, 15, 25)]) == []


def test_rightmost_run_returns_empty_for_empty_line():
    assert Lib._digit_rightmost_run([]) == []


def test_rightmost_run_gap_threshold_scales_with_height():
    """切段阈值跟着字高走：字越大，允许的字间距越大"""
    # 字高 24，阈值 = max(6, 12) = 12，间距 10 仍算同一段
    line = [_glyph(0, 0, 15, 24), _glyph(25, 0, 15, 24)]
    assert len(Lib._digit_rightmost_run(line)) == 2

    # 同样间距 10，但字高只有 10 时阈值 = max(6, 5) = 6，就该断开
    small = [_glyph(0, 0, 6, 10), _glyph(16, 0, 6, 10)]
    assert Lib._digit_rightmost_run(small) == [], "断开后每段只有 1 个字，不算数字段"


# ------------------------------------------------------- 画布归一化


def test_canvas_shape_and_range():
    """画布尺寸固定、取值在 0/1 之间"""
    canvas = Lib._digit_canvas(_glyph(0, 0, 15, 24))

    assert canvas.shape == (32, 28)
    assert canvas.dtype == np.float32
    assert set(np.unique(canvas)) <= {0.0, 1.0}


def test_canvas_preserves_aspect_ratio():
    """按高度等比缩放：窄字与宽字在画布上的宽度必须不同

    如果拉伸铺满，`1` 和 `0` 就会长得一样，数字 1 再也认不出来。
    """
    narrow = Lib._digit_canvas(_glyph(0, 0, 8, 24))
    wide = Lib._digit_canvas(_glyph(0, 0, 16, 24))

    assert narrow[:, :].sum() < wide[:, :].sum(), "窄字占的像素必须更少"


def test_canvas_centers_horizontally():
    """字形要水平居中，否则位移容忍会被白白吃掉"""
    canvas = Lib._digit_canvas(_glyph(0, 0, 8, 24))
    cols = np.nonzero(canvas.any(axis=0))[0]

    left_margin = cols[0]
    right_margin = canvas.shape[1] - 1 - cols[-1]
    assert abs(int(left_margin) - int(right_margin)) <= 1


def test_canvas_is_invariant_to_glyph_origin():
    """字形在源图里的位置不影响画布内容（画布只看局部掩码）"""
    a = Lib._digit_canvas((0, 0, 15, 24, np.ones((24, 15), bool)))
    b = Lib._digit_canvas((100, 200, 15, 24, np.ones((24, 15), bool)))

    assert np.array_equal(a, b)


# ------------------------------------------------------- 带位移的距离


def test_distance_zero_for_identical_canvas():
    canvas = Lib._digit_canvas(_glyph(0, 0, 15, 24))
    assert Lib._digit_distance(canvas, canvas) == 0.0


def test_distance_tolerates_one_pixel_shift():
    """整体横移 1~2 像素、纵移 1 像素后，距离必须仍然远小于判定阈值

    同一数字重切一次，外接框可能差一格；不放开位移会把它们判成两个数字。
    注意纵向只容忍 1 像素：字形本身占满画布高度，再多就会真的丢掉笔画，
    所以这里断言的是「远小于阈值」而不是「精确为 0」。
    """
    canvas = Lib._digit_canvas(_glyph(0, 0, 15, 24))
    limit = Lib.JIEJIE_DIGIT_THRESHOLD * 0.5

    for dx in (-2, -1, 1, 2):
        shifted = np.zeros_like(canvas)
        if dx > 0:
            shifted[:, dx:] = canvas[:, :-dx]
        else:
            shifted[:, :dx] = canvas[:, -dx:]
        assert Lib._digit_distance(canvas, shifted) < 1e-6, f"横移 {dx} 应被完全吸收"

    for dy in (-1, 1):
        shifted = np.zeros_like(canvas)
        if dy > 0:
            shifted[dy:, :] = canvas[:-dy, :]
        else:
            shifted[:dy, :] = canvas[-dy:, :]
        distance = Lib._digit_distance(canvas, shifted)
        assert distance < limit, f"纵移 {dy} 的残差 {distance} 必须远小于阈值 {limit}"


def test_distance_detects_real_difference():
    """真的不一样（一个全亮、一个全暗）时距离必须很大"""
    lit = np.ones((32, 28), dtype=np.float32)
    dark = np.zeros((32, 28), dtype=np.float32)

    assert Lib._digit_distance(lit, dark) == pytest.approx(1.0, abs=0.05)
