# -*- coding: utf-8 -*-
"""调试截图的事后渲染器：把截图与日志拼成一份能直接看的图文对照。

用法：
    python tools/render_shots.py                       # 渲染 logs 下最近一次运行
    python tools/render_shots.py --log <日志路径>       # 指定某次运行（也可以给 shots_* 目录）
    python tools/render_shots.py --all                 # 渲染 logs 下所有还没渲染过的运行
    python tools/render_shots.py --miss-only           # 只看未命中
    python tools/render_shots.py --by-template         # 按模板分组
    python tools/render_shots.py --no-fold             # 轮询连拍段不折叠

做的事：
1. 读 shots_<stamp>/index.tsv（唯一权威清单，图片明细不在 .log 里，也不在 GUI 里）；
2. 读同目录同 stamp 的 .log（`shots_2026-11-05_20-18-13` → `console_output_2026-11-05_20-18-13.log`）；
3. 输出 shots_<stamp>/index.md：**一张图 → 它之后那段日志 → 下一张图**；
4. 顶部给汇总（张数 / 命中率 / 体积 / 跨度 / 按模板统计 / 未对齐的帧）。

图与日志怎么对上：日志行本身不带时间戳，但每条匹配结果几乎都会把得分打进
`INFO- 0.312 未找到太鼓` 这样的行里，而 index.tsv 的「得分」列是同一份三位小数。
于是把「帧序号有序」与「日志行号有序」同时满足的配对整体求最长公共子序列
（LCS，用 Hunt-Szymanski + 二分 LIS），把「这一帧的判定之后、下一帧的判定之前」的
日志行归给这一帧。找不到得分的帧（调用方压根没打印）记为未对齐，不编造上下文。

为什么不用「往后找第一处同分行」的贪心：同一次运行里同一个得分会反复出现
（实测一次 379 帧的运行里 `0.011` 出现 19 次、`0.012` 出现 15 次），贪心会先把
后面才对得上的行消耗掉，越走越偏——同一份数据贪心只对上 18 帧，LCS 能对上 192 帧。

只用标准库：markdown 内嵌图片不需要读图片尺寸，也不需要解码。
"""

import argparse
import bisect
import datetime
import glob
import os
import re
import sys

# 项目根目录 = 本文件的上上级
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

SHOT_PREFIX = "shots_"
INDEX_NAME = "index.tsv"
OUTPUT_NAME = "index.md"

# 日志里出现的得分 token：index.tsv 的得分列就是同一份三位小数（Lib 里 f"{min_val:.3f}"）
# 前后不能再接数字或小数点，避免把 0.0115 这类更长的小数误认成 0.011。
# 不认 1.000：那是未命中时调用方写的兜底值，日志里没有对应行，
# 认了会把 NULL 配给不相干的日志。
SCORE_TOKEN_PATTERN = re.compile(r"(?<![\d.])0\.\d{3}(?!\d)")

# 连续这么多次「同模板 + 同结果」就折叠（轮询场景动辄上百张几乎一样的画面）
FOLD_MIN = 4

# 开头那段没有任何帧可归属的日志行，超过这个行数就折起来
LEAD_MAX_LINES = 12


# ----------------------------------------------------------------- 读文件


def parse_index(shot_dir):
    """读 index.tsv，返回按序号排列的行字典列表。缺文件或只有表头时返回空列表。"""
    path = os.path.join(shot_dir, INDEX_NAME)
    if not os.path.isfile(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        header = handle.readline()
        if not header.strip():
            return []
        for line in handle:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            cells = line.split("\t")
            # 表头 10 列：序号 时间 结果 来源 模板 得分 阈值 尺寸 裁剪偏移 文件
            if len(cells) < 10:
                cells = cells + [""] * (10 - len(cells))
            rows.append({
                "序号": cells[0],
                "时间": cells[1],
                "结果": cells[2],
                "来源": cells[3],
                "模板": cells[4],
                "得分": cells[5],
                "阈值": cells[6],
                "尺寸": cells[7],
                "偏移": cells[8],
                "文件": cells[9],
            })
    return rows


def find_log(shot_dir):
    """由 shots_<stamp> 反推同 stamp 的 <prefix>_<stamp>.log。

    stamp 里带 `:` 之外的分隔符全是 `-`，不会与日志前缀冲突；
    同 stamp 理论上只有一份日志（_log_stream 的 timestamp 精确到秒）。

    开截图时 _log_stream 会把 .log 直接放进截图目录（一次排查的东西放一处），
    老目录的 .log 则仍与截图目录同级——两处都找，先看目录内。
    """
    name = os.path.basename(shot_dir.rstrip("\\/"))
    if not name.startswith(SHOT_PREFIX):
        return None
    stamp = name[len(SHOT_PREFIX):]
    pattern = "*_" + stamp + ".log"
    for folder in (shot_dir, os.path.dirname(shot_dir)):
        hits = sorted(glob.glob(os.path.join(folder, pattern)))
        if hits:
            return hits[0]
    return None


def read_log(path):
    """按行读日志，去掉行尾。文件不存在时返回空列表并提示。"""
    if not path or not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return [line.rstrip("\r\n") for line in handle]


def iter_shot_dirs(root=LOGS_DIR):
    """列出 logs 下所有 shots_* 目录，按路径（含日期与时间）升序。"""
    if not os.path.isdir(root):
        return []
    found = []
    for month in sorted(os.listdir(root)):
        month_dir = os.path.join(root, month)
        if not os.path.isdir(month_dir):
            continue
        for day in sorted(os.listdir(month_dir)):
            day_dir = os.path.join(month_dir, day)
            if not os.path.isdir(day_dir):
                continue
            for entry in sorted(os.listdir(day_dir)):
                if entry.startswith(SHOT_PREFIX) and os.path.isdir(os.path.join(day_dir, entry)):
                    found.append(os.path.join(day_dir, entry))
    return found


# ----------------------------------------------------------------- 对齐


def align_rows(rows, lines):
    """给每一行找它在日志里的位置，返回与 rows 等长的位置列表（找不到为 None）。

    求的是「帧序与行号同时递增」的最长公共子序列（LCS）：帧的顺序与日志顺序天然一致，
    但同一得分在一次运行里会反复出现（实测 379 帧的运行里 `0.011` 出现 19 次），
    「往后找第一处同分行」的贪心会先把后面才对得上的行消耗掉，越走越偏——
    同一份数据贪心只对上 18 帧，LCS 能对上 192 帧。

    实现用 Hunt-Szymanski：按帧顺序展开候选 (行号, 帧号)，同一帧内的候选按行号倒序
    （保证一帧最多贡献一个配对），再用二分对行号序列求严格递增的最长上升子序列。
    规模上 379 帧 × 192 条得分行不到 0.1 秒，几千帧也没问题。
    """
    positions = [None] * len(rows)

    # 得分 -> 出现它的日志行号（一次扫描建索引，避免逐帧重扫日志）
    line_numbers = {}
    for index, line in enumerate(lines):
        for match in SCORE_TOKEN_PATTERN.finditer(line):
            line_numbers.setdefault(match.group(0), []).append(index)

    tails = []        # tails[k]：长度为 k+1 的上升子序列的末尾行号
    nodes = []        # 只追加：nodes[i] = (帧号, 行号, 父节点下标)
    slot_node = []    # slot_node[k]：tails[k] 对应的节点下标

    for frame, row in enumerate(rows):
        score = (row["得分"] or "").strip()
        candidates = line_numbers.get(score)
        if not candidates:
            continue
        for line_no in reversed(candidates):
            slot = bisect.bisect_left(tails, line_no)
            if slot < len(tails) and tails[slot] == line_no:
                # 这一行已经被更早的帧用掉了，换成当前帧不会让子序列更长
                continue
            parent = slot_node[slot - 1] if slot > 0 else -1
            nodes.append((frame, line_no, parent))
            index = len(nodes) - 1
            if slot == len(tails):
                tails.append(line_no)
                slot_node.append(index)
            else:
                tails[slot] = line_no
                slot_node[slot] = index

    # 从最优末尾回溯出所有配对
    if slot_node:
        current = slot_node[-1]
        while current >= 0:
            frame, line_no, parent = nodes[current]
            positions[frame] = line_no
            current = parent
    return positions


def section_ranges(positions, total_lines):
    """把「每帧的日志区间」算出来：从本帧的判定行到下一帧出现位置之前。

    返回与 positions 等长的 [(start, end)]；未对齐的帧拿到 (None, None)。
    """
    # 先算「下一个有位置的行」在哪，避免多帧连续未对齐时区间断开
    next_pos = [None] * len(positions)
    upcoming = None
    for index in range(len(positions) - 1, -1, -1):
        next_pos[index] = upcoming
        if positions[index] is not None:
            upcoming = positions[index]
    ranges = []
    for index, start in enumerate(positions):
        if start is None:
            ranges.append((None, None))
            continue
        end = next_pos[index]
        if end is None or end < start:
            end = total_lines
        ranges.append((start, end))
    return ranges


# ----------------------------------------------------------------- 格式化


def human_size(count):
    """字节数转人话，与 tools/clean_logs.py 的口径保持一致。"""
    if count < 1024:
        return "%d B" % count
    if count < 1024 * 1024:
        return "%.1f KB" % (count / 1024.0)
    if count < 1024 * 1024 * 1024:
        return "%.1f MB" % (count / 1024.0 / 1024.0)
    return "%.2f GB" % (count / 1024.0 / 1024.0 / 1024.0)


def human_span(seconds):
    """秒数转「1 分 12 秒」这种，超过一小时给小时。"""
    seconds = int(round(seconds))
    if seconds < 0:
        seconds += 24 * 3600
    if seconds < 60:
        return "%d 秒" % seconds
    if seconds < 3600:
        return "%d 分 %d 秒" % (seconds // 60, seconds % 60)
    return "%d 小时 %d 分" % (seconds // 3600, seconds % 3600 // 60)


def parse_time(text):
    """解析 index.tsv 的 HH:MM:SS.mmm，失败返回 None。"""
    try:
        return datetime.datetime.strptime(text, "%H:%M:%S.%f")
    except (TypeError, ValueError):
        return None


def shot_dir_size(shot_dir):
    """目录里所有文件的总字节数（不含 index.md 本身）。"""
    total = 0
    for entry in os.listdir(shot_dir):
        if entry == OUTPUT_NAME:
            continue
        path = os.path.join(shot_dir, entry)
        if os.path.isfile(path):
            try:
                total += os.path.getsize(path)
            except OSError:
                pass
    return total


# ----------------------------------------------------------------- 渲染


def build_summary(run_name, rows, lines, log_name, log_lines, shot_dir):
    """顶部汇总：张数、命中率、体积、跨度、按模板统计、未对齐数量。"""
    total = len(rows)
    missed = [row for row in rows if row["结果"] != "hit"]
    hits = total - len(missed)
    rate = (hits * 100.0 / total) if total else 0.0

    times = [parse_time(row["时间"]) for row in rows]
    times = [value for value in times if value is not None]
    if len(times) >= 2:
        span = human_span((times[-1] - times[0]).total_seconds())
        span_text = "%s ~ %s（%s）" % (rows[0]["时间"], rows[-1]["时间"], span)
    elif times:
        span_text = rows[0]["时间"]
    else:
        span_text = "未知"

    out = []
    out.append("# 调试截图 · %s" % run_name)
    out.append("")
    out.append("- 总张数：**%d**（hit %d / miss %d）· 命中率 %.1f%%" % (total, hits, len(missed), rate))
    out.append("- 体积：%s" % human_size(shot_dir_size(shot_dir)))
    out.append("- 跨度：%s" % span_text)
    if log_name:
        out.append("- 日志：`%s`（%d 行）" % (log_name, log_lines))
    else:
        out.append("- 日志：**没有找到同名 .log**，只有图片明细")
    unaligned = sum(1 for row in rows if row["_区间"][0] is None)
    if unaligned:
        out.append("- 未对齐的帧：%d 张（这几次判定调用方没有打印得分，不编造上下文）" % unaligned)
    out.append("")

    # 按模板统计（次数多的排前面，同次数按名字，保证多次渲染结果一致）
    stats = {}
    for row in rows:
        key = row["模板"] or "未知"
        item = stats.setdefault(key, {"count": 0, "hit": 0, "best": None, "worst": None})
        item["count"] += 1
        if row["结果"] == "hit":
            item["hit"] += 1
        value = parse_float(row["得分"])
        if value is not None:
            if item["best"] is None or value < item["best"]:
                item["best"] = value
            if item["worst"] is None or value > item["worst"]:
                item["worst"] = value

    if stats:
        out.append("按模板：")
        out.append("")
        out.append("| 模板 | 次数 | 命中 | 未命中 | 最好 | 最差 |")
        out.append("|---|---|---|---|---|---|")
        ordered = sorted(stats.items(), key=lambda pair: (-pair[1]["count"], pair[0]))
        for name, item in ordered:
            out.append("| %s | %d | %d | %d | %s | %s |" % (
                name, item["count"], item["hit"], item["count"] - item["hit"],
                fmt_score(item["best"]), fmt_score(item["worst"]),
            ))
        out.append("")
    return out


def parse_float(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def fmt_score(value):
    return "-" if value is None else "%.3f" % value


def render_frame(row, lines, section, shot_dir):
    """渲染单帧：标题 + 图 + 一行元信息 + 这帧之后的日志。"""
    start, end = section
    marker = "hit" if row["结果"] == "hit" else "miss"
    out = []
    out.append("## #%s %s · %s · %s（阈值 %s）· %s" % (
        row["序号"].zfill(4), marker, row["模板"] or "未知",
        row["得分"] or "-", row["阈值"] or "-", row["时间"] or "-",
    ))
    out.append("")

    image_path = os.path.join(shot_dir, row["文件"])
    if row["文件"] and os.path.isfile(image_path):
        out.append("![](%s)" % row["文件"])
    else:
        out.append("> 图片缺失：`%s`" % (row["文件"] or "(空)"))
    out.append("")

    meta = ["来源 `%s`" % (row["来源"] or "-"), "尺寸 %s" % (row["尺寸"] or "-")]
    if row["偏移"] and row["偏移"] != "-":
        meta.append("裁剪偏移 %s（坐标是相对这块裁剪的）" % row["偏移"])
    out.append("*%s*" % " · ".join(meta))
    out.append("")

    if start is not None and end is not None and end > start:
        body = lines[start:end]
        if body:
            out.append("```text")
            out.extend(body)
            out.append("```")
            out.append("")
    return out


def fold_key(row):
    """折叠用的键：同模板 + 同结果，认为是一轮轮询里的同一件事。"""
    return (row["结果"], row["模板"])


def group_runs(rows):
    """把连续同 fold_key 的行切成段，返回 [(key, [rows...])]。"""
    groups = []
    for row in rows:
        key = fold_key(row)
        if groups and groups[-1][0] == key:
            groups[-1][1].append(row)
        else:
            groups.append((key, [row]))
    return groups


def render_run(shot_dir, miss_only=False, by_template=False, fold=True):
    """渲染一次运行，返回 index.md 的文本行列表。"""
    rows = parse_index(shot_dir)
    log_path = find_log(shot_dir)
    lines = read_log(log_path)

    positions = align_rows(rows, lines)
    ranges = section_ranges(positions, len(lines))
    for row, section in zip(rows, ranges):
        row["_区间"] = section

    run_name = os.path.basename(shot_dir.rstrip("\\/"))
    if run_name.startswith(SHOT_PREFIX):
        run_name = run_name[len(SHOT_PREFIX):]
    log_name = os.path.basename(log_path) if log_path else None

    out = []
    if not rows:
        out.append("# 调试截图 · %s" % run_name)
        out.append("")
        out.append("> 没有可渲染的记录：`%s` 不存在或只有表头。" % INDEX_NAME)
        out.append("")
        out.append("这通常说明这次运行开了截图档位但一次匹配都没发生（或早就退出了）。")
        return out

    out.extend(build_summary(run_name, rows, lines, log_name, len(lines), shot_dir))

    # 第一帧之前的日志，是这次运行的开头（TASK- 分隔线、账号切换、SKIP- 之类）
    first_start = next((row["_区间"][0] for row in rows if row["_区间"][0] is not None), None)
    if first_start:
        leading = lines[:first_start]
        if leading:
            out.append("## 开头的日志（第 1~%d 行，还没有任何匹配判定）" % first_start)
            out.append("")
            if fold and len(leading) > LEAD_MAX_LINES:
                out.append("<details><summary>展开 %d 行</summary>" % len(leading))
                out.append("")
                out.append("```text")
                out.extend(leading)
                out.append("```")
                out.append("")
                out.append("</details>")
            else:
                out.append("```text")
                out.extend(leading)
                out.append("```")
            out.append("")

    shown = [row for row in rows if not (miss_only and row["结果"] == "hit")]

    if by_template:
        out.extend(render_by_template(shown, lines, shot_dir, fold))
    else:
        out.extend(render_chronological(shown, lines, shot_dir, fold))

    return out


def render_chronological(rows, lines, shot_dir, fold):
    out = []
    if not rows:
        out.append("> 按当前筛选条件（`--miss-only`）没有任何帧可显示。")
        out.append("")
        return out
    for _key, chunk in group_runs(rows) if fold else [(None, [row]) for row in rows]:
        if len(chunk) < FOLD_MIN:
            for row in chunk:
                out.extend(render_frame(row, lines, row["_区间"], shot_dir))
                out.append("---")
                out.append("")
            continue
        # 连拍段：第一张正常显示，其余折进 details，避免 120 张几乎一样的画面刷屏
        head = chunk[0]
        rest = chunk[1:]
        out.extend(render_frame(head, lines, head["_区间"], shot_dir))
        out.append("<details><summary>此处还有 %d 张相同画面（#%s ~ #%s，%s · %s）</summary>" % (
            len(rest), rest[0]["序号"].zfill(4), rest[-1]["序号"].zfill(4),
            head["模板"] or "未知", "命中" if head["结果"] == "hit" else "未命中",
        ))
        out.append("")
        for row in rest:
            out.extend(render_frame(row, lines, row["_区间"], shot_dir))
        out.append("</details>")
        out.append("")
        out.append("---")
        out.append("")
    return out


def render_by_template(rows, lines, shot_dir, fold):
    """按模板分组：同一模板的帧集中在一起，方便回答「这个模板到底认不认得出」。"""
    out = []
    if not rows:
        out.append("> 按当前筛选条件（`--miss-only`）没有任何帧可显示。")
        out.append("")
        return out
    buckets = {}
    order = []
    for row in rows:
        key = row["模板"] or "未知"
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(row)
    # 出现次数多的模板排前面
    order.sort(key=lambda name: (-len(buckets[name]), name))
    for name in order:
        chunk = buckets[name]
        miss = sum(1 for row in chunk if row["结果"] != "hit")
        out.append("## 模板：%s（%d 次，未命中 %d）" % (name, len(chunk), miss))
        out.append("")
        for row in chunk:
            out.extend(render_frame(row, lines, row["_区间"], shot_dir))
            out.append("---")
            out.append("")
    return out


def write_index(shot_dir, text_lines):
    """写 index.md（UTF-8，换行用 \\n：markdown 渲染器都认，不必跟仓库的 CRLF 走）。"""
    path = os.path.join(shot_dir, OUTPUT_NAME)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(text_lines).rstrip("\n") + "\n")
    return path


# ----------------------------------------------------------------- 入口


def resolve_targets(args):
    """按参数决定要渲染哪些 shots 目录。返回 (目录列表, 错误信息)。"""
    explicit = args.log
    if explicit:
        path = explicit if os.path.isabs(explicit) else os.path.join(PROJECT_ROOT, explicit)
        if os.path.isdir(path):
            return [path], None
        if os.path.isfile(path):
            # 给了 .log：按同 stamp 反推 shots 目录
            stem = os.path.splitext(os.path.basename(path))[0]
            shot_dir = os.path.join(os.path.dirname(path), SHOT_PREFIX + stem[-19:])
            if os.path.isdir(shot_dir):
                return [shot_dir], None
            return [], "这个日志没有对应的截图目录：%s" % shot_dir
        return [], "路径不存在：%s" % path

    found = iter_shot_dirs()
    if not found:
        return [], "logs 下还没有任何 shots_* 目录（先在设置里把「调试截图」开起来跑一次）"
    if args.all:
        return found, None
    return [found[-1]], None


def main():
    parser = argparse.ArgumentParser(description="把调试截图与日志渲染成可读的图文对照（index.md）")
    parser.add_argument("--log", help="指定某次运行：.log 文件路径或 shots_* 目录")
    parser.add_argument("--all", action="store_true", help="渲染 logs 下所有 shots_* 目录")
    parser.add_argument("--miss-only", action="store_true", help="只输出未命中的帧")
    parser.add_argument("--by-template", action="store_true", help="按模板分组而不是按时间顺序")
    parser.add_argument("--no-fold", action="store_true", help="轮询连拍段也全部展开")
    args = parser.parse_args()

    targets, error = resolve_targets(args)
    if error:
        print(error)
        return 1

    for shot_dir in targets:
        text_lines = render_run(
            shot_dir,
            miss_only=args.miss_only,
            by_template=args.by_template,
            fold=not args.no_fold,
        )
        path = write_index(shot_dir, text_lines)
        rows = parse_index(shot_dir)
        missed = sum(1 for row in rows if row["结果"] != "hit")
        print("%s  (%d 张，未命中 %d)  ->  %s" % (
            os.path.basename(shot_dir.rstrip("\\/")), len(rows), missed,
            os.path.relpath(path, PROJECT_ROOT),
        ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
