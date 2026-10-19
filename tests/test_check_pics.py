# -*- coding: utf-8 -*-
"""tools/check_pics.py 的回归测试。

工具本身是"检查别人"的，一旦它自己误判，就会给出误导性的结论。
这里覆盖两类曾经出过的问题：

1. 收容所（.dsh-scratch/）里的历史源码被当成项目代码扫描，
   报出大量"引用了不存在的图片"——属于噪音，必须跳过。
2. pic/ 下的说明文档（README.md）被当成模板图，报成"未被引用"——它不是图片。
"""

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(PROJECT_ROOT, "tools")
for path in (TOOLS_DIR,):
    if path not in sys.path:
        sys.path.insert(0, path)

import check_pics  # noqa: E402


def test_skip_dirs_contains_scratch():
    assert ".dsh-scratch" in check_pics.SKIP_DIRS, "收容所必须跳过，否则备份里的旧路径会污染检查结果"


def test_skip_dirs_contains_common_noise():
    for name in (".venv", ".git", "__pycache__", "build", "dist", "logs"):
        assert name in check_pics.SKIP_DIRS


def test_image_exts_only_images():
    assert ".png" in check_pics.IMAGE_EXTS
    assert ".md" not in check_pics.IMAGE_EXTS, "pic/README.md 是索引文档，不是模板图"


def test_collect_disk_images_excludes_readme(project_root):
    """真实仓库里 pic/README.md 存在，但不应被当成模板图"""
    images = check_pics.collect_disk_images()
    lowered = {key.lower() for key in images}
    # 拼接写，避免本文件自己成为 check_pics 的扫描对象
    readme_key = ("./pic/" + "README" + ".md").lower()
    assert readme_key not in lowered
    assert len(images) > 150, "模板图数量异常，检查是否漏扫"


def test_collect_disk_images_all_have_image_ext(project_root):
    for real in check_pics.collect_disk_images().values():
        ext = os.path.splitext(real)[1].lower()
        assert ext in check_pics.IMAGE_EXTS, f"非图片被收录: {real}"


def test_iter_source_files_skips_scratch(project_root):
    """收容所里的 .py 不应出现在待扫描列表中"""
    files = list(check_pics.iter_source_files())
    assert files, "至少应扫到项目源码"
    for path in files:
        rel = os.path.relpath(path, project_root).replace("\\", "/")
        assert not rel.startswith(".dsh-scratch/"), f"收容所文件被扫描: {rel}"
        assert "/__pycache__/" not in rel


def test_collect_references_finds_known_template(project_root):
    """真实仓库里 Lib.py 引用了大量模板图，静态引用不应为空"""
    static, dynamic = check_pics.collect_references()
    assert static, "没收集到任何静态引用，说明扫描逻辑坏了"
    refs = {ref for ref, _, _ in static}
    assert any(ref.startswith("./pic/") for ref in refs)
    # 动态拼接的团队预设路径是已知的（f-string）
    assert dynamic, "没收集到动态拼接路径"


def test_all_static_refs_exist_on_disk(project_root):
    """仓库当前状态应当自洽：静态引用的图都在磁盘上"""
    static, _ = check_pics.collect_references()
    disk = check_pics.collect_disk_images()
    missing = [(ref, f, n) for ref, f, n in static if ref.lower() not in disk]
    assert not missing, f"存在失效引用: {missing[:5]}"


def test_all_static_refs_case_matches(project_root):
    """路径大小写必须与磁盘一致（换 Linux / 打包工具时会踩坑）"""
    static, _ = check_pics.collect_references()
    disk = check_pics.collect_disk_images()
    mismatched = [
        (ref, disk[ref.lower()], f, n)
        for ref, f, n in static
        if ref.lower() in disk and disk[ref.lower()] != ref
    ]
    assert not mismatched, f"存在大小写不一致: {mismatched[:5]}"


# ---------------------------------------------- 纯函数（用构造数据验证）


def test_classify_references_detects_missing():
    static = [("./pic/a/不存在.png", "Lib.py", 10)]
    disk = {"./pic/a/存在.png": "./pic/a/存在.png"}
    missing, mismatch = check_pics.classify_references(static, disk)
    assert missing == [("./pic/a/不存在.png", "Lib.py", 10)]
    assert mismatch == []


def test_classify_references_detects_case_mismatch():
    """代码写 Pic/A.png，磁盘是 pic/a.png —— 必须报出来"""
    static = [("./pic/A.png", "Lib.py", 20)]
    disk = {"./pic/a.png": "./pic/a.png"}
    missing, mismatch = check_pics.classify_references(static, disk)
    assert missing == []
    assert mismatch == [("./pic/A.png", "./pic/a.png", "Lib.py", 20)]


def test_classify_references_ok_when_exact_match():
    static = [("./pic/a.png", "Lib.py", 30)]
    disk = {"./pic/a.png": "./pic/a.png"}
    assert check_pics.classify_references(static, disk) == ([], [])


def test_collect_unused_flags_dead_image():
    static = [("./pic/a/用到.png", "Lib.py", 1)]
    disk = {"./pic/a/用到.png": "./pic/a/用到.png", "./pic/a/死图.png": "./pic/a/死图.png"}
    unused = check_pics.collect_unused(static, [], disk)
    assert unused == ["./pic/a/死图.png"]


def test_collect_unused_exempts_dynamic_dir():
    """f-string 拼接的目录整体豁免，不能误报死图"""
    static = []
    dynamic = [('f"./pic/team/{Preset_Group}.png"', "Lib.py", 5)]
    disk = {"./pic/team/某个预设.png": "./pic/team/某个预设.png"}
    unused = check_pics.collect_unused(static, dynamic, disk)
    assert unused == []


def test_collect_unused_keeps_other_dirs():
    """动态目录只豁免自己那一层，不能把别的目录也放过"""
    static = []
    dynamic = [('f"./pic/team/{Preset_Group}.png"', "Lib.py", 5)]
    disk = {
        "./pic/team/预设.png": "./pic/team/预设.png",
        "./pic/common/死图.png": "./pic/common/死图.png",
    }
    unused = check_pics.collect_unused(static, dynamic, disk)
    assert unused == ["./pic/common/死图.png"]
