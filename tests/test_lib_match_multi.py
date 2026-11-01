# -*- coding: utf-8 -*-
"""一帧多用原语：Screenshot_window / Match_models_in_image / 画面指纹。

这三个原语是为了把「识别几次就截几次图」拆成「截一次、用多次」，
所以测试的重点不是「模板匹配准不准」（那是 cv2 的事），而是：

1. 同一帧上多次匹配，结果与逐个匹配一致（拆开后语义没变）；
2. 多模板返回值的形状、排序、阈值语义都对；
3. 模板缓存不会让「换了模板图却还在用旧图」；
4. 画面指纹能把「还在滚」和「滚到底了」区分开。

全部用合成图，不依赖真实截图，也不依赖窗口句柄。
"""

import cv2
import numpy as np
import pytest

import Lib


# ---------------------------------------------------------------- 合成图工具


def _make_scene(seed=0):
    """造一张有纹理的「背景」，让模板匹配有唯一解"""
    rng = np.random.default_rng(seed)
    scene = rng.integers(0, 60, size=(240, 320, 3), dtype=np.uint8)
    # 撒几个亮块，作为「模板」的来源
    cv2.rectangle(scene, (40, 50), (90, 90), (200, 180, 120), -1)
    cv2.rectangle(scene, (150, 120), (200, 160), (120, 200, 180), -1)
    return scene


def _crop(scene, x, y, w, h):
    return scene[y:y + h, x:x + w].copy()


def _write_template(tmp_path, name, patch):
    """把模板写到临时目录。项目里 Img_read_ch 走 imdecode，能读中文路径"""
    path = tmp_path / name
    ok, buf = cv2.imencode(".png", patch)
    assert ok
    path.write_bytes(buf.tobytes())
    return str(path)


@pytest.fixture()
def scene():
    return _make_scene()


@pytest.fixture(autouse=True)
def _reset_template_cache():
    """每个用例前后都清缓存，避免用例之间互相影响"""
    Lib.clear_template_cache()
    yield
    Lib.clear_template_cache()


# ---------------------------------------------------- Match_models_in_image


def test_multi_match_finds_each_template(tmp_path, scene):
    """两个模板各自命中自己的位置，坐标与单独匹配一致"""
    a = _write_template(tmp_path, "a.png", _crop(scene, 40, 50, 50, 40))
    b = _write_template(tmp_path, "b.png", _crop(scene, 150, 120, 50, 40))

    results = Lib.Match_models_in_image(scene, [("A", a), ("B", b)], 0.05)

    assert [r[0] for r in results] == ["A", "B"]
    by_name = {r[0]: r for r in results}
    assert by_name["A"][1] == [(40, 50), (90, 90)]
    assert by_name["B"][1] == [(150, 120), (200, 160)]


def test_multi_match_matches_single_match(tmp_path, scene):
    """拆开之后的结果必须和原来的 Match_model 逐字段一致"""
    path = _write_template(tmp_path, "a.png", _crop(scene, 40, 50, 50, 40))

    alone, alone_score = Lib.Match_model(scene, path, 0.05, 0)
    multi = Lib.Match_models_in_image(scene, [("A", path)], 0.05)

    assert len(multi) == 1
    _name, box, score = multi[0]
    assert box == alone
    assert score == alone_score


def test_multi_match_sorted_by_score(tmp_path, scene):
    """结果按得分升序，最像的在前面"""
    exact = _write_template(tmp_path, "exact.png", _crop(scene, 40, 50, 50, 40))
    noisy = _crop(scene, 40, 50, 50, 40).astype(np.int16)
    noisy = np.clip(noisy + 12, 0, 255).astype(np.uint8)
    near = _write_template(tmp_path, "near.png", noisy)

    results = Lib.Match_models_in_image(scene, [("near", near), ("exact", exact)], 0.5)

    assert [r[0] for r in results][0] == "exact", "完全一致的那张必须排在前面"
    scores = [float(r[2]) for r in results]
    assert scores == sorted(scores)


def test_multi_match_threshold_is_inclusive_like_match_model(tmp_path, scene):
    """阈值语义与 Match_model 一致：得分大于阈值才算失败"""
    path = _write_template(tmp_path, "a.png", _crop(scene, 40, 50, 50, 40))

    # 阈值 0 时，只有逐像素完全相同的才可能通过（合成图里正是这种情况）
    hit = Lib.Match_models_in_image(scene, [("A", path)], 0.0)
    assert len(hit) == 1

    # 阈值给负值必然全部落空，用来确认「过滤」真的生效而不是永远返回
    miss = Lib.Match_models_in_image(scene, [("A", path)], -1.0)
    assert miss == []


def test_multi_match_empty_models(scene):
    """空模板列表返回空结果，不抛异常"""
    assert Lib.Match_models_in_image(scene, [], 0.05) == []


def test_multi_match_skips_template_larger_than_image(tmp_path):
    """模板比待匹配图还大时跳过，不能让 cv2 抛错"""
    big = np.zeros((80, 80, 3), dtype=np.uint8)
    path = _write_template(tmp_path, "big.png", big)
    small_scene = np.zeros((40, 40, 3), dtype=np.uint8)

    assert Lib.Match_models_in_image(small_scene, [("big", path)], 0.9) == []


def test_multi_match_raises_on_missing_template(scene, tmp_path):
    """模板文件不存在时明确报错，而不是静默当成未命中

    Img_read_ch 用 open() 读文件，文件不存在时抛的是 FileNotFoundError；
    它对「解不出来」返回 None，那一路才由这里补成 ValueError。
    """
    missing = str(tmp_path / "nope.png")
    with pytest.raises((ValueError, FileNotFoundError)):
        Lib.Match_models_in_image(scene, [("X", missing)], 0.05)


# ------------------------------------------------------------ 模板缓存


def test_template_cache_reuses_decoded_image(tmp_path, scene, monkeypatch):
    """同一张模板连续用两次，只应该解码一次"""
    path = _write_template(tmp_path, "a.png", _crop(scene, 40, 50, 50, 40))

    calls = []
    original = Lib.Img_read_ch

    def counting_read(p):
        calls.append(p)
        return original(p)

    monkeypatch.setattr(Lib, "Img_read_ch", counting_read)

    Lib.Match_models_in_image(scene, [("A", path)], 0.05)
    Lib.Match_models_in_image(scene, [("A", path)], 0.05)

    assert calls == [path], "第二次必须命中缓存"


def test_template_cache_invalidates_when_file_changes(tmp_path, scene, monkeypatch):
    """模板图被替换后必须重新读，不能继续用旧图"""
    path = _write_template(tmp_path, "a.png", _crop(scene, 40, 50, 50, 40))
    Lib.Match_models_in_image(scene, [("A", path)], 0.05)

    calls = []
    original = Lib.Img_read_ch

    def counting_read(p):
        calls.append(p)
        return original(p)

    monkeypatch.setattr(Lib, "Img_read_ch", counting_read)

    # 改写文件：内容不同，mtime 与大小都可能变
    _write_template(tmp_path, "a.png", _crop(scene, 150, 120, 50, 40))
    Lib.Match_models_in_image(scene, [("A", path)], 0.05)

    assert calls == [path], "文件变了就必须重新解码"


def test_clear_template_cache_forces_reread(tmp_path, scene, monkeypatch):
    """clear_template_cache 之后必然重新解码"""
    path = _write_template(tmp_path, "a.png", _crop(scene, 40, 50, 50, 40))
    Lib.Match_models_in_image(scene, [("A", path)], 0.05)

    Lib.clear_template_cache()
    calls = []
    original = Lib.Img_read_ch

    def counting_read(p):
        calls.append(p)
        return original(p)

    monkeypatch.setattr(Lib, "Img_read_ch", counting_read)
    Lib.Match_models_in_image(scene, [("A", path)], 0.05)

    assert calls == [path]


# ------------------------------------------------- Match_models_in_image_all


def _make_list_scene(rows):
    """造一张「列表」图：在固定的几个纵向位置各贴一份同样的卡面"""
    rng = np.random.default_rng(11)
    scene = rng.integers(0, 50, size=(400, 320, 3), dtype=np.uint8)
    patch = np.zeros((60, 80, 3), dtype=np.uint8)
    cv2.rectangle(patch, (5, 5), (75, 55), (190, 170, 130), -1)
    cv2.circle(patch, (40, 30), 18, (60, 120, 200), -1)
    for y in rows:
        scene[y:y + 60, 100:180] = patch
    return scene, patch


def test_multi_all_finds_every_row(tmp_path):
    """一屏四行同款卡面时，必须四行全都找出来（Match_models_in_image 只给一行）"""
    scene, patch = _make_list_scene([20, 120, 220, 320])
    path = _write_template(tmp_path, "card.png", patch)

    boxes = Lib.Match_models_in_image_all(scene, path, 0.05, max_matches=8)

    assert len(boxes) == 4
    assert [b[0][1] for b in boxes] == [20, 120, 220, 320], "按从上到下排序"


def test_multi_all_respects_max_matches(tmp_path):
    """上限到了就停，不能无限找下去"""
    scene, patch = _make_list_scene([20, 120, 220, 320])
    path = _write_template(tmp_path, "card.png", patch)

    boxes = Lib.Match_models_in_image_all(scene, path, 0.05, max_matches=2)

    assert len(boxes) == 2


def test_multi_all_does_not_repeat_same_row(tmp_path):
    """涂黑之后不能把同一行再报一次，否则会重复点击同一张卡"""
    scene, patch = _make_list_scene([20, 120])
    path = _write_template(tmp_path, "card.png", patch)

    boxes = Lib.Match_models_in_image_all(scene, path, 0.05, max_matches=8)

    assert len(boxes) == 2
    assert len({tuple(b[0]) for b in boxes}) == 2


def test_multi_all_returns_empty_when_absent(tmp_path):
    """画面里没有这张卡时返回空列表，而不是抛异常"""
    scene, _patch = _make_list_scene([])
    other = np.full((60, 80, 3), 255, dtype=np.uint8)
    path = _write_template(tmp_path, "other.png", other)

    assert Lib.Match_models_in_image_all(scene, path, 0.05) == []


def test_multi_all_skips_template_larger_than_image(tmp_path):
    """模板比图还大时返回空，不能让 cv2 抛错"""
    big = np.zeros((80, 80, 3), dtype=np.uint8)
    path = _write_template(tmp_path, "big.png", big)

    assert Lib.Match_models_in_image_all(np.zeros((40, 40, 3), dtype=np.uint8), path, 0.05) == []


def test_multi_all_does_not_modify_input(tmp_path):
    """内部会涂黑工作副本，但不能改到调用方传进来的那一帧"""
    scene, patch = _make_list_scene([20, 120])
    path = _write_template(tmp_path, "card.png", patch)
    before = scene.copy()

    Lib.Match_models_in_image_all(scene, path, 0.05)

    assert np.array_equal(scene, before), "调用方的图必须原样"


# ------------------------------------------------------------ Match_models_rows


def _make_card_patch(seed, color):
    """造一块有辨识度的「卡面」：纯色底 + 几块随机亮斑"""
    rng = np.random.default_rng(seed)
    patch = np.zeros((70, 90, 3), dtype=np.uint8)
    patch[:, :] = color
    for _ in range(6):
        x = int(rng.integers(4, 80))
        y = int(rng.integers(4, 60))
        patch[y:y + 8, x:x + 10] = rng.integers(120, 255, size=3, dtype=np.uint8)
    return patch


def _make_two_card_scene(tmp_path):
    """一屏两行，两行是**不同**的卡；另外造一张「似是而非」的模板

    真机上四张结界卡共用金色托盘与橙色星点，一张斗鱼卡在太鼓模板上
    换个滑窗位置也可能过阈值，于是同一行被两张模板各报一次。
    这里复现这个局面：B 是 A 的近似（同一位置也能过阈值，但分数更差）。
    """
    card_a = _make_card_patch(1, (40, 60, 180))
    card_b = _make_card_patch(2, (60, 160, 60))
    near_a = card_a.copy()
    near_a[0:12, 0:14] = (10, 10, 10)      # A 的近似：改了一小块，仍能过阈值但更差

    rng = np.random.default_rng(5)
    scene = rng.integers(0, 40, size=(420, 360, 3), dtype=np.uint8)
    scene[60:130, 120:210] = card_a       # 第一行
    scene[260:330, 120:210] = card_b      # 第二行

    path_a = _write_template(tmp_path, "card_a.png", card_a)
    path_b = _write_template(tmp_path, "card_b.png", card_b)
    path_near = _write_template(tmp_path, "near_a.png", near_a)
    return scene, path_a, path_b, path_near


def test_rows_picks_best_template_per_row(tmp_path):
    """同一行被两张模板命中时，只能报一次，且报最像的那一张

    这是真机上「点开的是五星斗鱼，日志却写五星太鼓」的直接成因：
    逐张模板各找各的，同一行会出两条，于是点两次、记两次账。
    """
    scene, path_a, path_b, path_near = _make_two_card_scene(tmp_path)

    rows = Lib.Match_models_rows(
        scene, [("真A", path_a), ("近A", path_near), ("真B", path_b)], 0.05, max_matches=8
    )

    assert len(rows) == 2, "两行只能出两条，不能因为近似模板多出一条"
    assert [r[0] for r in rows] == ["真A", "真B"], "每行取分数最低（最像）的那张模板"


def test_rows_sorted_top_to_bottom(tmp_path):
    """结果按纵向排序：调用方按人的阅读顺序从上往下点"""
    scene, path_a, path_b, _near = _make_two_card_scene(tmp_path)

    rows = Lib.Match_models_rows(scene, [("真B", path_b), ("真A", path_a)], 0.05)

    ys = [r[1][0][1] for r in rows]
    assert ys == sorted(ys)


def test_rows_returns_named_boxes(tmp_path):
    """返回值的形状要能直接喂给 Move_to_range / Click"""
    scene, path_a, _path_b, _near = _make_two_card_scene(tmp_path)

    rows = Lib.Match_models_rows(scene, [("真A", path_a)], 0.05)

    assert len(rows) == 1
    name, box, score = rows[0]
    assert name == "真A"
    assert len(box) == 2 and len(box[0]) == 2 and len(box[1]) == 2
    assert box[0][0] < box[1][0] and box[0][1] < box[1][1]
    assert isinstance(score, str)


def test_rows_drops_row_when_winner_too_weak(tmp_path):
    """行内胜出者的分数仍然超过阈值时，整行不算命中

    阈值必须作用在**行内胜出者**身上，而不是「随便哪张模板过线就算」，
    否则一堆弱命中会把画面里的空白格也算成卡。
    """
    scene, _path_a, _path_b, path_near = _make_two_card_scene(tmp_path)

    # 近似模板在默认阈值下能命中（分数约 0.02）
    assert len(Lib.Match_models_rows(scene, [("近A", path_near)], 0.05)) == 1
    # 阈值收到比它更严时，这一行就不该算命中
    assert Lib.Match_models_rows(scene, [("近A", path_near)], 0.001) == []


def test_rows_returns_empty_when_absent(tmp_path):
    """画面里没有这些卡时返回空列表，而不是抛异常"""
    scene, _a, _b, _near = _make_two_card_scene(tmp_path)
    blank = np.full((70, 90, 3), 255, dtype=np.uint8)
    other = _write_template(tmp_path, "other.png", blank)

    assert Lib.Match_models_rows(scene, [("别的", other)], 0.05) == []


def test_rows_skips_template_larger_than_image(tmp_path):
    """模板比图还大时跳过，不能让 cv2 抛错"""
    big = np.zeros((500, 500, 3), dtype=np.uint8)
    path = _write_template(tmp_path, "big.png", big)

    assert Lib.Match_models_rows(np.zeros((40, 40, 3), dtype=np.uint8), [("大", path)], 0.05) == []


def test_rows_does_not_modify_input(tmp_path):
    """内部会涂黑分数图，但不能改到调用方传进来的那一帧"""
    scene, path_a, path_b, _near = _make_two_card_scene(tmp_path)
    before = scene.copy()

    Lib.Match_models_rows(scene, [("真A", path_a), ("真B", path_b)], 0.05)

    assert np.array_equal(scene, before), "调用方的图必须原样"


def test_rows_handles_empty_models(tmp_path):
    """一张模板都不给时返回空列表"""
    scene, _a, _b, _near = _make_two_card_scene(tmp_path)

    assert Lib.Match_models_rows(scene, [], 0.05) == []


# ------------------------------------------------------- 画面指纹


def test_fingerprint_shape(scene):
    """指纹尺寸要稳定，才能每屏都算一次"""
    fp = Lib.Image_fingerprint(scene)
    assert fp.shape == (18, 32)

    fp2 = Lib.Image_fingerprint(scene, size=(16, 9))
    assert fp2.shape == (9, 16)


def test_fingerprint_stable_for_same_image(scene):
    """同一帧算两次，差必须为 0"""
    assert Lib.Fingerprint_diff(Lib.Image_fingerprint(scene), Lib.Image_fingerprint(scene)) == 0.0
    assert Lib.Fingerprint_same(Lib.Image_fingerprint(scene), Lib.Image_fingerprint(scene))


def test_fingerprint_tolerates_compression_noise(scene):
    """轻微噪声不应被判成「画面变了」，否则列表到底时会被误判成还在滚"""
    rng = np.random.default_rng(7)
    noisy = np.clip(scene.astype(np.int16) + rng.integers(-3, 4, scene.shape), 0, 255).astype(np.uint8)

    fp_a = Lib.Image_fingerprint(scene)
    fp_b = Lib.Image_fingerprint(noisy)

    diff = Lib.Fingerprint_diff(fp_a, fp_b)
    assert diff < 3.0, f"噪声后的平均差 {diff} 应该远小于容差"
    assert Lib.Fingerprint_same(fp_a, fp_b)


def test_fingerprint_detects_scroll(scene):
    """内容真的滚动了，必须判成「变了」——这是「还没到底」的判据"""
    scrolled = np.roll(scene, 40, axis=0)

    fp_a = Lib.Image_fingerprint(scene)
    fp_b = Lib.Image_fingerprint(scrolled)

    diff = Lib.Fingerprint_diff(fp_a, fp_b)
    assert diff > 10.0, f"滚动后的平均差 {diff} 应该远大于容差"
    assert not Lib.Fingerprint_same(fp_a, fp_b)


def test_fingerprint_tolerance_is_tunable(scene):
    """容差可调：给 0 时连噪声都判成不同，给很大时什么都算相同"""
    rng = np.random.default_rng(7)
    noisy = np.clip(scene.astype(np.int16) + rng.integers(-3, 4, scene.shape), 0, 255).astype(np.uint8)
    fp_a = Lib.Image_fingerprint(scene)
    fp_b = Lib.Image_fingerprint(noisy)

    assert not Lib.Fingerprint_same(fp_a, fp_b, Tolerance=0.0)
    assert Lib.Fingerprint_same(fp_a, fp_b, Tolerance=255.0)


def test_fingerprint_rejects_shape_mismatch(scene):
    """尺寸不一致时明确报错，而不是悄悄算出一个错误的差值"""
    fp_a = Lib.Image_fingerprint(scene)
    fp_b = Lib.Image_fingerprint(scene, size=(16, 9))
    with pytest.raises(ValueError):
        Lib.Fingerprint_diff(fp_a, fp_b)
