# -*- mode: python ; coding: utf-8 -*-

# 说明：qfluentwidgets 的图标资源内嵌在 Python 包里，无需收集 datas；
# 但它的子模块由内部动态导入，PyInstaller 静态分析可能漏掉，需显式声明 hiddenimports。

a = Analysis(
    ['GUI.py'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # Fluent 界面组件库及其拆分出的子包
        'qfluentwidgets',
        'qfluentwidgets.common',
        'qfluentwidgets.components',
        'qfluentwidgets.window',
        'qframelesswindow',
        'darkdetect',
        # 调试截图的图文对照渲染器：end_shots() 收尾时 import 它生成 index.md。
        # tools/ 没有 __init__.py（隐式命名空间包），打包版必须在这里登记，
        # 否则 exe 里 import 不到，收尾只会打一行「生成失败」。
        'tools.render_shots',
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
    icon=None  # 您可以在此指定程序图标路径，例如 'icon.ico'
)
