# -*- coding: utf-8 -*-
"""模板图引用检查工具

用法：
    python tools/check_pics.py            # 检查并报告
    python tools/check_pics.py --quiet    # 只输出问题

检查项：
1. 源码中引用的 ./pic/... 路径是否都真实存在
2. 磁盘上是否有未被任何源码引用的图片（死图）
3. 是否存在路径大小写与磁盘不一致（Windows 不敏感，但换系统/打包工具会踩坑）
4. 报告动态拼接的路径（无法静态校验，需人工确认）
"""
import argparse
import ast
import os
import re
import sys

# 项目根目录 = 本文件的上上级
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIC_DIR_NAME = "pic"

# 不参与检查的目录
SKIP_DIRS = {".venv", ".git", "__pycache__", "build", "dist", "logs", "config", "tools"}


def iter_source_files():
    """遍历项目内所有 .py 源码文件"""
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.endswith(".py"):
                yield os.path.join(root, fn)


def collect_references():
    """扫描源码，收集所有 ./pic/ 路径引用

    :return: (静态引用集合, 动态路径列表)
             静态引用为 [(相对路径, 文件, 行号)]
             动态路径为 [(源码片段, 文件, 行号)]
    """
    static = []
    dynamic = []

    for path in iter_source_files():
        rel_file = os.path.relpath(path, PROJECT_ROOT).replace("\\", "/")
        try:
            with open(path, encoding="utf-8") as f:
                src = f.read()
            tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"[警告] 跳过无法解析的文件 {rel_file}: {e}")
            continue

        # 先收集 f-string 里出现的行号，避免把它的静态片段当成完整路径
        dynamic_lines = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.JoinedStr):
                continue
            seg = ast.get_source_segment(src, node)
            if seg and "pic" in seg:
                dynamic.append((seg, rel_file, node.lineno))
                dynamic_lines.add(node.lineno)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant):
                continue
            if not isinstance(node.value, str):
                continue
            if not node.value.startswith("./pic/"):
                continue
            # f-string 里的静态片段（如 "./pic/Team/"）不是完整路径，跳过
            if node.lineno in dynamic_lines:
                continue
            # 以 "/" 结尾的片段也不是完整文件路径
            if node.value.endswith("/"):
                continue
            static.append((node.value, rel_file, node.lineno))

    return static, dynamic


def collect_disk_images():
    """收集磁盘上的所有图片

    :return: {小写相对路径: 真实相对路径}
    """
    images = {}
    pic_root = os.path.join(PROJECT_ROOT, PIC_DIR_NAME)
    if not os.path.isdir(pic_root):
        return images
    for root, dirs, files in os.walk(pic_root):
        for fn in files:
            full = os.path.join(root, fn)
            rel = "./" + os.path.relpath(full, PROJECT_ROOT).replace("\\", "/")
            images[rel.lower()] = rel
    return images


def main():
    parser = argparse.ArgumentParser(description="检查模板图引用")
    parser.add_argument("--quiet", action="store_true", help="只输出问题")
    args = parser.parse_args()

    if not os.path.isdir(os.path.join(PROJECT_ROOT, PIC_DIR_NAME)):
        print(f"[错误] 找不到 {PIC_DIR_NAME}/ 目录（项目根：{PROJECT_ROOT}）")
        return 2

    static, dynamic = collect_references()
    disk = collect_disk_images()

    problems = 0

    # ---- 1. 引用但不存在的文件 ----
    missing = []
    case_mismatch = []
    for ref, rel_file, lineno in static:
        key = ref.lower()
        if key not in disk:
            missing.append((ref, rel_file, lineno))
        elif disk[key] != ref:
            case_mismatch.append((ref, disk[key], rel_file, lineno))

    # ---- 2. 未被引用的图片 ----
    referenced_keys = {ref.lower() for ref, _, _ in static}

    # 动态拼接的目录：从 f-string 里提取目录前缀（如 "./pic/team/{Preset_Group}.png" -> "./pic/team/"）
    # 该目录下的图片按"动态引用"处理，不判定为死图
    dynamic_dirs = set()
    for seg, _, _ in dynamic:
        for m in re.finditer(r'["\'](\./pic/[^"\'{]+/)', seg):
            dynamic_dirs.add(m.group(1).lower())

    unused = []
    for key, real in sorted(disk.items()):
        if key in referenced_keys:
            continue
        if any(key.startswith(d) for d in dynamic_dirs):
            continue
        unused.append(real)

    # ---- 输出 ----
    if not args.quiet:
        print("=" * 72)
        print("模板图引用检查")
        print("=" * 72)
        print(f"  项目根：{PROJECT_ROOT}")
        print(f"  磁盘图片：{len(disk)} 张")
        print(f"  静态引用：{len(static)} 处（唯一 {len(referenced_keys)} 个）")
        print(f"  动态拼接：{len(dynamic)} 处")
        print()

    if missing:
        problems += len(missing)
        print(f"[错误] 引用了不存在的图片：{len(missing)} 处")
        print("        这类引用在运行到该步骤时必然失败")
        for ref, rel_file, lineno in missing:
            print(f"    {rel_file}:{lineno}")
            print(f"        {ref}")
        print()

    if case_mismatch:
        problems += len(case_mismatch)
        print(f"[错误] 路径大小写与磁盘不一致：{len(case_mismatch)} 处")
        print("        Windows 不敏感，但 Linux / 打包工具 / 大小写敏感文件系统会失败")
        for ref, real, rel_file, lineno in case_mismatch:
            print(f"    {rel_file}:{lineno}")
            print(f"        代码: {ref}")
            print(f"        磁盘: {real}")
        print()

    if unused:
        # 未被引用不算错误（可能是保留素材），只作提示，不影响退出码
        if not args.quiet:
            print(f"[提示] 未被引用的图片：{len(unused)} 张")
            print("        确认确实无用后可删除；若是有意保留的素材请忽略")
            for p in unused:
                print(f"    {p}")
            print()

    if dynamic and not args.quiet:
        print(f"[信息] 动态拼接的路径：{len(dynamic)} 处（无法静态校验，需人工确认）")
        for seg, rel_file, lineno in dynamic:
            print(f"    {rel_file}:{lineno}  {seg}")
        print()

    # ---- 汇总 ----
    if problems == 0:
        if not args.quiet:
            print("=" * 72)
            print("检查通过：无失效引用、无大小写不一致")
            print("=" * 72)
        return 0

    print("=" * 72)
    print(f"发现 {problems} 个错误")
    print("=" * 72)
    return 1


if __name__ == "__main__":
    sys.exit(main())
