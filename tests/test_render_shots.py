# -*- coding: utf-8 -*-
"""tools/render_shots.py 的回归测试。

渲染器本身不碰游戏窗口、不读图片像素，用合成的 shots 目录就能覆盖：
造一份 index.tsv + 一份 .log，检查「图 → 对应日志 → 下一张图」的切分是否成立。

重点守两件事：
1. 得分对齐是**单向**的——只往后扫，不能回头把同一段日志重复配给多帧；
2. 折叠只合并「同模板 + 同结果」的连拍，不能把不同模板的帧混成一段。
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(PROJECT_ROOT, "tools")
for path in (TOOLS_DIR,):
    if path not in sys.path:
        sys.path.insert(0, path)

import render_shots  # noqa: E402

HEADER = "序号\t时间\t结果\t来源\t模板\t得分\t阈值\t尺寸\t裁剪偏移\t文件\n"
STAMP = "2026-11-05_20-18-13"


def write_shot_dir(root, rows, log_lines=None, stamp=STAMP, prefix="console_output", name=None):
    """在 root 下造一份 shots_<stamp>/index.tsv（以及同 stamp 的 .log）。"""
    shot_dir = os.path.join(str(root), render_shots.SHOT_PREFIX + stamp)
    os.makedirs(shot_dir, exist_ok=True)
    with open(os.path.join(shot_dir, render_shots.INDEX_NAME), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(HEADER)
        for cells in rows:
            handle.write("\t".join(str(cell) for cell in cells) + "\n")
    if log_lines is not None:
        log_path = os.path.join(str(root), "%s_%s.log" % (prefix, stamp))
        with open(log_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(log_lines) + "\n")
    # 造占位图片文件：渲染器只判断文件在不在、不解码，名字取 index.tsv 的文件列
    for cells in rows:
        file_name = str(cells[9]) if len(cells) > 9 and cells[9] else "%06d.jpg" % int(cells[0])
        open(os.path.join(shot_dir, file_name), "wb").close()
    return shot_dir


def row(seq, result, template, score, threshold=0.05, name=None):
    return [
        seq, "20:18:%02d.000" % (seq % 60), result, "match_model", template,
        score, threshold, "1930x1165", "-",
        name if name is not None else "%06d_%s_%s_%s.jpg" % (seq, result, template, score),
    ]


# ------------------------------------------------------------------ 读 index.tsv


def test_parse_index读满十列(tmp_path):
    shot_dir = write_shot_dir(tmp_path, [row(1, "hit", "主界面", "0.012")])
    rows = render_shots.parse_index(shot_dir)
    assert len(rows) == 1
    assert rows[0]["序号"] == "1"
    assert rows[0]["结果"] == "hit"
    assert rows[0]["模板"] == "主界面"
    assert rows[0]["得分"] == "0.012"
    assert rows[0]["文件"].endswith(".jpg")


def test_parse_index缺文件返回空(tmp_path):
    shot_dir = os.path.join(str(tmp_path), render_shots.SHOT_PREFIX + STAMP)
    os.makedirs(shot_dir)
    assert render_shots.parse_index(shot_dir) == []


def test_parse_index只有表头返回空(tmp_path):
    shot_dir = write_shot_dir(tmp_path, [])
    assert render_shots.parse_index(shot_dir) == []


def test_parse_index列数不足不炸(tmp_path):
    shot_dir = write_shot_dir(tmp_path, [["1", "20:18:14.033", "hit"]])
    rows = render_shots.parse_index(shot_dir)
    assert len(rows) == 1
    assert rows[0]["得分"] == ""
    assert rows[0]["文件"] == ""


# ------------------------------------------------------------------ 找日志


def test_find_log按stamp反推(tmp_path):
    shot_dir = write_shot_dir(tmp_path, [row(1, "hit", "主界面", "0.012")], log_lines=["x"])
    found = render_shots.find_log(shot_dir)
    assert found is not None
    assert os.path.basename(found) == "console_output_%s.log" % STAMP


def test_find_log找不到返回None(tmp_path):
    shot_dir = write_shot_dir(tmp_path, [row(1, "hit", "主界面", "0.012")])
    assert render_shots.find_log(shot_dir) is None


def test_find_log认单任务前缀(tmp_path):
    shot_dir = write_shot_dir(tmp_path, [row(1, "hit", "主界面", "0.012")],
                             log_lines=["x"], prefix="single_digui")
    found = render_shots.find_log(shot_dir)
    assert os.path.basename(found) == "single_digui_%s.log" % STAMP


# ------------------------------------------------------------------ 得分对齐


def test_align按顺序往后找(tmp_path):
    rows = render_shots.parse_index(write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012"), row(2, "miss", "太鼓", "0.312")],
        log_lines=["a", "INFO- 0.012 检测到进入庭院", "b", "INFO- 0.312 未找到太鼓"],
    ))
    lines = render_shots.read_log(render_shots.find_log(os.path.join(str(tmp_path), render_shots.SHOT_PREFIX + STAMP)))
    positions = render_shots.align_rows(rows, lines)
    assert positions == [1, 3]


def test_align不回头复用同一行(tmp_path):
    """两帧同分时：第二帧必须落到后一处，不能两帧共用第一行"""
    rows = render_shots.parse_index(write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012"), row(2, "hit", "主界面", "0.012")],
        log_lines=["INFO- 0.012 第一次", "INFO- 0.012 第二次"],
    ))
    log_path = render_shots.find_log(os.path.join(str(tmp_path), render_shots.SHOT_PREFIX + STAMP))
    positions = render_shots.align_rows(rows, render_shots.read_log(log_path))
    assert positions == [0, 1], "只往后扫，第二帧才能拿到第二行"


def test_align找不到记未对齐(tmp_path):
    """调用方没打印得分的判定，如实标 None，不编造上下文"""
    rows = render_shots.parse_index(write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012")],
        log_lines=["INFO- 0.999 别的东西"],
    ))
    log_path = render_shots.find_log(os.path.join(str(tmp_path), render_shots.SHOT_PREFIX + STAMP))
    assert render_shots.align_rows(rows, render_shots.read_log(log_path)) == [None]


def test_align得分非三位小数不对齐(tmp_path):
    rows = render_shots.parse_index(write_shot_dir(
        tmp_path,
        [row(1, "miss", "未知", "")],
        log_lines=["INFO- 0.500 某处"],
    ))
    log_path = render_shots.find_log(os.path.join(str(tmp_path), render_shots.SHOT_PREFIX + STAMP))
    assert render_shots.align_rows(rows, render_shots.read_log(log_path)) == [None]


def test_同分密集时不错位(tmp_path):
    """回归：同一得分反复出现时，贪心会越走越偏，LCS 要对上全部得分行。

    真实样本（379 帧 / 645 行日志）里 `0.011` 出现 19 次、`0.012` 15 次——
    「往后找第一处同分行」会先把后面才对得上的行消耗掉，实测只对上 18 帧。
    这里按同样模式造数据，断言每一帧都落到它自己那一行、且顺序严格递增。
    """
    same_scores = ["0.011"] * 19 + ["0.012"] * 15 + ["0.038"] * 14
    log_lines = []
    expected = []
    for index, score in enumerate(same_scores):
        log_lines.append("        INFO- %s 第 %d 次判定" % (score, index))
        log_lines.append("        填充行 A")
        expected.append(len(log_lines) - 2)
    rows = [row(index + 1, "hit", "主界面", score) for index, score in enumerate(same_scores)]

    shot_dir = write_shot_dir(tmp_path, rows, log_lines=log_lines)
    lines = render_shots.read_log(render_shots.find_log(shot_dir))
    positions = render_shots.align_rows(render_shots.parse_index(shot_dir), lines)

    assert positions == expected, "每帧都要对上自己那一行，不能错位"
    assert len({pos for pos in positions if pos is not None}) == len(positions), "不许共用同一行"


def test_区间到下一帧之前(tmp_path):

    rows = render_shots.parse_index(write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012"), row(2, "miss", "太鼓", "0.312")],
        log_lines=["开头", "INFO- 0.012 a", "中间两行", "再一行", "INFO- 0.312 b", "尾巴"],
    ))
    log_path = render_shots.find_log(os.path.join(str(tmp_path), render_shots.SHOT_PREFIX + STAMP))
    lines = render_shots.read_log(log_path)
    ranges = render_shots.section_ranges(render_shots.align_rows(rows, lines), len(lines))
    assert ranges[0] == (1, 4)
    assert ranges[1] == (4, 6)


def test_区间末帧吃到文件尾(tmp_path):
    rows = render_shots.parse_index(write_shot_dir(
        tmp_path, [row(1, "hit", "主界面", "0.012")],
        log_lines=["INFO- 0.012 a", "结尾一", "结尾二"],
    ))
    log_path = render_shots.find_log(os.path.join(str(tmp_path), render_shots.SHOT_PREFIX + STAMP))
    lines = render_shots.read_log(log_path)
    ranges = render_shots.section_ranges(render_shots.align_rows(rows, lines), len(lines))
    assert ranges[0] == (0, 3)


def test_连续未对齐不劈开区间(tmp_path):
    """中间两帧没对齐时，前一帧的区间应直接延伸到下一帧真正对齐的位置"""
    rows = render_shots.parse_index(write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012"), row(2, "miss", "甲", ""), row(3, "miss", "乙", ""),
         row(4, "miss", "太鼓", "0.312")],
        log_lines=["INFO- 0.012 a", "中间", "INFO- 0.312 b"],
    ))
    log_path = render_shots.find_log(os.path.join(str(tmp_path), render_shots.SHOT_PREFIX + STAMP))
    lines = render_shots.read_log(log_path)
    ranges = render_shots.section_ranges(render_shots.align_rows(rows, lines), len(lines))
    assert ranges[0] == (0, 2)
    assert ranges[1] == (None, None)
    assert ranges[2] == (None, None)
    assert ranges[3] == (2, 3)


# ------------------------------------------------------------------ 渲染


def test_渲染出图文对照(tmp_path):
    shot_dir = write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012"), row(2, "miss", "太鼓", "0.312")],
        log_lines=["开头日志", "INFO- 0.012 检测到进入庭院", "INFO- 0.312 未找到太鼓"],
    )
    text = "\n".join(render_shots.render_run(shot_dir))
    assert "![](000001_hit_主界面_0.012.jpg)" in text
    assert "## #0001 hit · 主界面 · 0.012（阈值 0.05）" in text
    assert "INFO- 0.012 检测到进入庭院" in text
    assert "## #0002 miss · 太鼓 · 0.312" in text
    assert "INFO- 0.312 未找到太鼓" in text


def test_开头日志单独成段(tmp_path):
    shot_dir = write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012")],
        log_lines=["MAIN- 流程开始", "TASK- 开始某任务", "INFO- 0.012 进入庭院"],
    )
    text = "\n".join(render_shots.render_run(shot_dir))
    assert "开头的日志" in text
    assert "MAIN- 流程开始" in text
    assert "TASK- 开始某任务" in text


def test_汇总含命中率与模板统计(tmp_path):
    shot_dir = write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012"), row(2, "hit", "主界面", "0.013"),
         row(3, "miss", "太鼓", "0.312")],
        log_lines=["INFO- 0.012 a", "INFO- 0.013 b", "INFO- 0.312 c"],
    )
    text = "\n".join(render_shots.render_run(shot_dir))
    assert "总张数：**3**（hit 2 / miss 1）" in text
    assert "命中率 66.7%" in text
    assert "| 主界面 | 2 | 2 | 0 | 0.012 | 0.013 |" in text
    assert "| 太鼓 | 1 | 0 | 1 | 0.312 | 0.312 |" in text


def test_汇总报告未对齐数量(tmp_path):
    shot_dir = write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012"), row(2, "hit", "体力", "0.029")],
        log_lines=["INFO- 0.012 a"],
    )
    text = "\n".join(render_shots.render_run(shot_dir))
    assert "未对齐的帧：1 张" in text


def test_缺日志也能渲染(tmp_path):
    shot_dir = write_shot_dir(tmp_path, [row(1, "hit", "主界面", "0.012")])
    text = "\n".join(render_shots.render_run(shot_dir))
    assert "没有找到同名 .log" in text
    assert "![](000001_hit_主界面_0.012.jpg)" in text


def test_没有记录时给说明(tmp_path):
    shot_dir = write_shot_dir(tmp_path, [])
    text = "\n".join(render_shots.render_run(shot_dir))
    assert "没有可渲染的记录" in text


def test_图片缺失时不编图片链接(tmp_path):
    shot_dir = write_shot_dir(tmp_path, [row(1, "hit", "主界面", "0.012")], log_lines=["INFO- 0.012 a"])
    os.remove(os.path.join(shot_dir, "000001_hit_主界面_0.012.jpg"))
    text = "\n".join(render_shots.render_run(shot_dir))
    assert "图片缺失" in text
    assert "![](000001_hit_主界面_0.012.jpg)" not in text


# ------------------------------------------------------------------ 筛选与分组


def test_miss_only只留未命中(tmp_path):
    shot_dir = write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012"), row(2, "miss", "太鼓", "0.312")],
        log_lines=["INFO- 0.012 a", "INFO- 0.312 b"],
    )
    text = "\n".join(render_shots.render_run(shot_dir, miss_only=True))
    assert "miss · 太鼓" in text
    assert "hit · 主界面" not in text


def test_by_template按模板归堆(tmp_path):
    shot_dir = write_shot_dir(
        tmp_path,
        [row(1, "hit", "主界面", "0.012"), row(2, "miss", "太鼓", "0.312"), row(3, "hit", "主界面", "0.014")],
        log_lines=["INFO- 0.012 a", "INFO- 0.312 b", "INFO- 0.014 c"],
    )
    text = "\n".join(render_shots.render_run(shot_dir, by_template=True))
    assert "## 模板：主界面（2 次，未命中 0）" in text
    assert "## 模板：太鼓（1 次，未命中 1）" in text
    # 主界面出现两次，应排在只出现一次的太鼓前面
    assert text.index("## 模板：主界面") < text.index("## 模板：太鼓")


def test_连拍折叠(tmp_path):
    """同模板同结果连成 6 张时，第一张正常显示，其余折进 details"""
    rows = [row(index + 1, "miss", "胜利太鼓", "0.3%02d" % index) for index in range(6)]
    log_lines = ["INFO- 0.3%02d 未检测到结束" % index for index in range(6)]
    shot_dir = write_shot_dir(tmp_path, rows, log_lines=log_lines)
    text = "\n".join(render_shots.render_run(shot_dir))
    assert "此处还有 5 张相同画面" in text
    assert "<details>" in text
    # 折叠后第一张仍在外面
    assert text.index("## #0001 miss") < text.index("<details>")


def test_折叠只合并同模板(tmp_path):
    """不同模板交替出现时不许合并——那会把无关的帧糊成一段"""
    rows = [row(1, "miss", "甲", "0.300"), row(2, "miss", "乙", "0.310"),
            row(3, "miss", "甲", "0.320"), row(4, "miss", "乙", "0.330"),
            row(5, "miss", "甲", "0.340")]
    shot_dir = write_shot_dir(tmp_path, rows)
    text = "\n".join(render_shots.render_run(shot_dir))
    assert "此处还有" not in text


def test_no_fold全展开(tmp_path):
    rows = [row(index + 1, "miss", "胜利太鼓", "0.3%02d" % index) for index in range(6)]
    log_lines = ["INFO- 0.3%02d 未找到" % index for index in range(6)]
    shot_dir = write_shot_dir(tmp_path, rows, log_lines=log_lines)
    text = "\n".join(render_shots.render_run(shot_dir, fold=False))
    assert "此处还有" not in text
    for index in range(1, 7):
        assert "## #%04d miss" % index in text


# ------------------------------------------------------------------ 写盘与入口


def test_write_index落盘(tmp_path):
    shot_dir = write_shot_dir(tmp_path, [row(1, "hit", "主界面", "0.012")])
    path = render_shots.write_index(shot_dir, ["# 标题", "", "内容"])
    assert os.path.isfile(path)
    with open(path, encoding="utf-8") as handle:
        assert handle.read() == "# 标题\n\n内容\n"


def test_iter_shot_dirs按日期排序(tmp_path):
    root = str(tmp_path)
    for month, day in (("2026-11", "2026-11-04"), ("2026-10", "2026-10-21")):
        os.makedirs(os.path.join(root, month, day, render_shots.SHOT_PREFIX + "2026-01-01_00-00-00"))
    found = render_shots.iter_shot_dirs(root)
    assert len(found) == 2
    assert "2026-10" in found[0], "10 月的应排在 11 月前面"


def test_iter_shot_dirs没有目录返回空(tmp_path):
    assert render_shots.iter_shot_dirs(str(tmp_path)) == []


def test_resolve给日志推截图目录(tmp_path, monkeypatch):
    shot_dir = write_shot_dir(tmp_path, [row(1, "hit", "主界面", "0.012")], log_lines=["x"])
    log_path = render_shots.find_log(shot_dir)
    monkeypatch.setattr(render_shots, "PROJECT_ROOT", str(tmp_path))
    targets, error = render_shots.resolve_targets(_Args(log=log_path))
    assert error is None
    assert targets == [shot_dir]


def test_resolve给不存在的路径报错(tmp_path, monkeypatch):
    monkeypatch.setattr(render_shots, "PROJECT_ROOT", str(tmp_path))
    targets, error = render_shots.resolve_targets(_Args(log=str(tmp_path / "nope.log")))
    assert targets == []
    assert "路径不存在" in error


def test_resolve日志没有对应截图目录(tmp_path, monkeypatch):
    orphan = os.path.join(str(tmp_path), "console_output_2026-01-01_00-00-00.log")
    open(orphan, "w", encoding="utf-8").close()
    monkeypatch.setattr(render_shots, "PROJECT_ROOT", str(tmp_path))
    targets, error = render_shots.resolve_targets(_Args(log=orphan))
    assert targets == []
    assert "没有对应的截图目录" in error


def test_human_size口径():
    assert render_shots.human_size(512) == "512 B"
    assert render_shots.human_size(2048) == "2.0 KB"
    assert render_shots.human_size(3 * 1024 * 1024) == "3.0 MB"


def test_human_span口径():
    assert render_shots.human_span(12) == "12 秒"
    assert render_shots.human_span(72) == "1 分 12 秒"
    assert render_shots.human_span(3720) == "1 小时 2 分"


class _Args:
    """冒充 argparse 的结果，只带 resolve_targets 会读的字段。"""

    def __init__(self, log=None, all=False):
        self.log = log
        self.all = all
