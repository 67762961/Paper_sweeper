# -*- coding: utf-8 -*-
"""Paper Sweeper 界面层。

模块职责（单向依赖，禁止反向引用）：

- ``theme``   ：设计 token（颜色/间距/圆角/字号），界面取值统一来自这里；
- ``icons``   ：今日状态图标与齿轮/运行图标按钮（QPainter 矢量绘制）；
- ``widgets`` ：整跑开关、任务行等基础组件；
- ``panels``  ：左侧任务列表、右侧日志控制台；
- ``window``  ：主窗口与任务线程。

弹窗与任务参数（都只被 ``window`` 引用，不反向依赖 ``panels``）：

- ``prefs``           ：界面偏好读写（``state/gui.json``）；
- ``settings_dialog`` ：日志区齿轮 → 主题 / 日志偏好 / 打开日志目录；
- ``after_run_dialog``：按钮区齿轮 → 完整运行完成后的动作；
- ``thirty_settings`` ：寮三十配置的纯逻辑读写（不依赖 Qt，可被 pytest 直接测）；
- ``thirty_dialog``   ：三十行齿轮 → 寮三十设置（副本/次数/主副账号）；
- ``jiejie_settings`` ：结界养成配置的纯逻辑读写（不依赖 Qt，枚举复用 ``Lib.JIEJIE_*``）；
- ``jiejie_dialog``   ：结界养成行齿轮 → 每账号一张卡片（放置顺序 + 四级寄养优先级）。

``GUI.py`` 只作为程序入口，负责环境变量、日志与异常钩子，并转出这里的组件。
"""
