# -*- coding: utf-8 -*-
"""图标组件：今日状态图标与齿轮/运行图标按钮。

图标全部用 QPainter 矢量绘制，不依赖字体字形与图片资源；
后续接入 Fluent 时可在这里整体替换为 FluentIcon，不影响上层组件。
"""

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QAbstractButton, QWidget

from . import theme


class StatusIcon(QWidget):
    """行首的今日状态图标：已完成 check / 今日未完成 alert / 运行中 play"""

    STATE_STYLES = {
        "done": (theme.COLOR_STATUS_DONE_BG, theme.COLOR_STATUS_DONE_FG, "check", "今日已完成"),
        "pending": (theme.COLOR_STATUS_PENDING_BG, theme.COLOR_STATUS_PENDING_FG, "alert", "今日尚未完成"),
        "running": (theme.COLOR_ACCENT, theme.COLOR_CARD_BG, "play", "正在运行"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "pending"
        self.setFixedSize(theme.SIZE_STATUS_ICON, theme.SIZE_STATUS_ICON)
        self.set_state("pending")

    def set_state(self, state):
        self.state = state if state in self.STATE_STYLES else "pending"
        _, _, _, tooltip = self.STATE_STYLES[self.state]
        self.setToolTip(tooltip)
        self.update()

    def paintEvent(self, event):
        background, color, glyph, _ = self.STATE_STYLES[self.state]
        size = theme.SIZE_STATUS_ICON
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(background))
        painter.drawEllipse(QRectF(0, 0, size, size))

        pen = QPen(QColor(color))
        pen.setWidthF(2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QColor(color))

        if glyph == "check":
            painter.drawLine(QPointF(6.2, 11.4), QPointF(9.8, 15.0))
            painter.drawLine(QPointF(9.8, 15.0), QPointF(15.8, 7.4))
        elif glyph == "alert":
            painter.drawLine(QPointF(11, 5.8), QPointF(11, 12.4))
            painter.drawEllipse(QRectF(9.9, 14.6, 2.2, 2.2))
        else:  # play
            painter.drawPolygon(
                QPolygonF([QPointF(8.4, 6.2), QPointF(8.4, 15.8), QPointF(15.6, 11.0)])
            )
        painter.end()


class IconButton(QAbstractButton):
    """行内圆形图标按钮（齿轮 / 运行），图形用 QPainter 绘制，不依赖字体与图片"""

    def __init__(self, kind, tooltip, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(theme.SIZE_ICON_BUTTON, theme.SIZE_ICON_BUTTON)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        hovered = self.underMouse() and self.isEnabled()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.COLOR_HOVER_BG))
            painter.drawEllipse(QRectF(1, 1, theme.SIZE_ICON_BUTTON - 2, theme.SIZE_ICON_BUTTON - 2))

        color = QColor(theme.COLOR_TEXT_PRIMARY) if hovered else QColor(theme.COLOR_TEXT_SECONDARY)
        if not self.isEnabled():
            color = QColor(theme.COLOR_TEXT_DISABLED)

        if self.kind == "gear":
            self._paint_gear(painter, color)
        else:
            self._paint_play(painter, color)
        painter.end()

    @staticmethod
    def _paint_play(painter, color):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(
            QPolygonF([QPointF(9.6, 7.2), QPointF(9.6, 18.8), QPointF(18.4, 13.0)])
        )

    @staticmethod
    def _paint_gear(painter, color):
        """齿轮：环形 + 8 个轮齿 + 中心孔"""
        center = QPointF(theme.SIZE_ICON_BUTTON / 2, theme.SIZE_ICON_BUTTON / 2)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        for index in range(8):
            painter.save()
            painter.translate(center)
            painter.rotate(index * 45)
            painter.drawRoundedRect(QRectF(-1.9, -10.4, 3.8, 4.4), 1.0, 1.0)
            painter.restore()

        ring_pen = QPen(color)
        ring_pen.setWidthF(3.4)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, 6.2, 6.2)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.COLOR_CARD_BG))
        painter.drawEllipse(center, 2.2, 2.2)
