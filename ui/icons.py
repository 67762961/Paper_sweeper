# -*- coding: utf-8 -*-
"""图标组件：今日状态图标与齿轮/运行图标按钮。

今日状态图标用 QPainter 直接绘制（对勾 / 感叹号 / 播放三角），不依赖字体字形，
在任意 DPI 下都清晰；齿轮与运行按钮使用 FluentIcon。
自绘颜色按当前主题从 ``ui/theme.py`` 取，深色主题下自动换成更亮的取值。
"""

from PyQt6.QtCore import Qt, QPointF, QSize
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon, TransparentToolButton, qconfig

from . import theme


class StatusIcon(QWidget):
    """行首的今日状态图标：已完成 check / 今日未完成 alert / 运行中 play"""

    # 状态 → (颜色 token, 图形, 提示语)
    STATE_STYLES = {
        "done": ("COLOR_STATUS_DONE", "check", "今日已完成"),
        "pending": ("COLOR_STATUS_PENDING", "alert", "今日尚未完成"),
        "running": ("COLOR_STATUS_RUNNING", "play", "正在运行"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "pending"
        self.setFixedSize(theme.SIZE_STATUS_ICON - 2, theme.SIZE_STATUS_ICON - 2)
        self.set_state("pending")
        # 深浅色切换后重绘，避免深色主题下仍是浅色的深绿 / 深橙
        qconfig.themeChangedFinished.connect(self.update)

    def set_state(self, state):
        self.state = state if state in self.STATE_STYLES else "pending"
        _, _, tooltip = self.STATE_STYLES[self.state]
        self.setToolTip(tooltip)
        self.update()

    def paintEvent(self, event):
        token, glyph, _ = self.STATE_STYLES[self.state]
        color = QColor(theme.color(token))
        side = float(self.width())

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(color)
        pen.setWidthF(2.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        if glyph == "check":
            painter.drawPolyline(
                QPolygonF([
                    QPointF(side * 0.22, side * 0.52),
                    QPointF(side * 0.44, side * 0.74),
                    QPointF(side * 0.80, side * 0.28),
                ])
            )
        elif glyph == "alert":
            painter.drawLine(QPointF(side * 0.5, side * 0.18), QPointF(side * 0.5, side * 0.62))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(side * 0.5, side * 0.82), 1.4, 1.4)
        else:  # play
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(
                QPolygonF([
                    QPointF(side * 0.32, side * 0.20),
                    QPointF(side * 0.32, side * 0.80),
                    QPointF(side * 0.80, side * 0.50),
                ])
            )
        painter.end()


class IconButton(TransparentToolButton):
    """行内图标按钮（齿轮 / 运行），使用 FluentIcon"""

    _ICONS = {
        "gear": FluentIcon.SETTING,
        "play": FluentIcon.PLAY,
    }

    def __init__(self, kind, tooltip, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(theme.SIZE_ICON_BUTTON + 2, theme.SIZE_ICON_BUTTON + 2)
        self.setIconSize(QSize(14, 14))
        self.setIcon(self._ICONS.get(kind, FluentIcon.SETTING))
