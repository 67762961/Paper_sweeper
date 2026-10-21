# -*- coding: utf-8 -*-
"""日志清理工具

用法：
    python tools/clean_logs.py                 # 预览：列出会被删除的目录（不删）
    python tools/clean_logs.py --apply         # 真正删除
    python tools/clean_logs.py --keep-months 3 # 只保留最近 3 个月（默认 6）
    python tools/clean_logs.py --apply --keep-days 30   # 额外按天清理

日志结构（由 main._log_stream 生成）：

    logs/
    ├── app_crash.log              ← 崩溃日志，不参与按月清理
    ├── 2026-10/
    │   └── 2026-10-21/
    │       └── console_output_2026-10-21_21-30-00.log
    └── 2026-09/
        └── ...

清理规则：
- 只处理形如 `YYYY-MM` 的月份目录，其它文件/目录一律不碰（避免误删）；
- 默认保留最近 N 个月（按目录名排序，不依赖文件修改时间）；
- `--keep-days` 可选，在保留月份内再按天清理（删除早于 N 天的日期目录）。
"""

import argparse
import datetime
import os
import re
import shutil
import sys

# 项目根目录 = 本文件的上上级
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

# 月份目录名形如 2026-10；日期目录名形如 2026-10-21
MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
DAY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def iter_month_dirs():
    """按名字升序返回所有月份目录（旧 -> 新）"""
    if not os.path.isdir(LOGS_DIR):
        return []
    months = []
    for name in os.listdir(LOGS_DIR):
        path = os.path.join(LOGS_DIR, name)
        if os.path.isdir(path) and MONTH_PATTERN.match(name):
            months.append((name, path))
    months.sort(key=lambda item: item[0])
    return months


def dir_size(path):
    """目录占用字节数"""
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def human_size(size):
    """把字节数格式化成易读形式"""
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024
    return f"{size:.1f} GB"


def plan_month_cleanup(keep_months):
    """返回 (要删除的月份目录路径列表, 要保留的 [(月份名, 路径)] 列表)"""
    months = iter_month_dirs()
    if keep_months <= 0:
        return [path for _name, path in months], []
    return [path for _name, path in months[:-keep_months]], months[-keep_months:]


def plan_day_cleanup(kept_months, keep_days):
    """在保留的月份目录内，找出早于 keep_days 天的日期目录"""
    if keep_days <= 0:
        return []
    cutoff = datetime.date.today() - datetime.timedelta(days=keep_days)
    stale = []
    for _name, month_path in kept_months:
        for day_name in sorted(os.listdir(month_path)):
            day_path = os.path.join(month_path, day_name)
            if not (os.path.isdir(day_path) and DAY_PATTERN.match(day_name)):
                continue
            try:
                day = datetime.date.fromisoformat(day_name)
            except ValueError:
                continue
            if day < cutoff:
                stale.append(day_path)
    return stale


def main():
    parser = argparse.ArgumentParser(description="清理旧日志目录（按年月分层）")
    parser.add_argument("--apply", action="store_true", help="真正删除；不加此参数只预览")
    parser.add_argument("--keep-months", type=int, default=6, help="保留最近几个月（默认 6）")
    parser.add_argument("--keep-days", type=int, default=0, help="保留月份内再按天清理（默认关闭）")
    args = parser.parse_args()

    if not os.path.isdir(LOGS_DIR):
        print(f"没有日志目录，无需清理: {LOGS_DIR}")
        return 0

    to_delete, kept = plan_month_cleanup(args.keep_months)
    to_delete = list(to_delete)
    to_delete += plan_day_cleanup(kept, args.keep_days)

    print("=" * 60)
    print("日志清理" + ("" if args.apply else "（预览，未删除）"))
    print("=" * 60)
    print(f"  日志根目录：{LOGS_DIR}")
    print(f"  保留月份：最近 {args.keep_months} 个月")
    if args.keep_days:
        print(f"  保留天数：最近 {args.keep_days} 天")
    print(f"  保留目录：{len(kept)} 个月份")
    print()

    if not to_delete:
        print("没有需要清理的目录。")
        return 0

    total = 0
    for path in to_delete:
        size = dir_size(path)
        total += size
        rel = os.path.relpath(path, LOGS_DIR)
        print(f"  {'删除' if args.apply else '将删除'} {rel}  ({human_size(size)})")

    print()
    print(f"合计：{len(to_delete)} 个目录，{human_size(total)}")

    if not args.apply:
        print()
        print("以上只是预览。确认无误后加 --apply 执行：")
        print("    python tools/clean_logs.py --apply")
        return 0

    failed = 0
    for path in to_delete:
        try:
            shutil.rmtree(path)
        except OSError as error:
            failed += 1
            print(f"  [失败] {path}: {error}")

    if failed:
        print(f"\n完成，但有 {failed} 个目录删除失败。")
        return 1
    print("\n清理完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
