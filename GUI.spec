# -*- mode: python ; coding: utf-8 -*-

distpath = '.'  # 设置输出路径为根目录

a = Analysis(
    ['GUI.py'],
    binaries=[],
    # datas 部分：打包资源文件 [1,2](@ref)
    # 格式: [('源路径1', '目标路径1'), ('源路径2', '目标路径2')]
    datas=[
        # 示例：如果您有 images 文件夹或 qt_material 的主题文件，在此添加
        # (join(PROJECT_PATH, 'images'), 'images'),
        # (join(PROJECT_PATH, 'styles'), 'styles'),
    ],
    # hiddenimports 部分：显式声明隐藏的依赖 [1,6,8](@ref)
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'qt_material',
        # 如果您的 'main' 模块或其依赖有未自动检测到的，也加在这里
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['PyQt5'],  # 排除 PyQt5 是正确的，因为您使用 PyQt6
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='GUI',
    debug=False,
    strip=False,
    upx=True,  # 使用 UPX 压缩，减小体积
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 对于 GUI 程序，设置为 False 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None  # 您可以在此处指定程序图标路径，例如 'icon.ico'
)