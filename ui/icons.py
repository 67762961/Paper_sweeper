# -*- coding: utf-8 -*-
"""图标组件：今日状态图标与齿轮/运行图标按钮。

齿轮与运行按钮使用 FluentIcon；今日状态图标以 FluentIcon（对勾 / 运行）
叠加在语义色圆底上，未完成态保留绘制感叹号（FluentIcon 没有现成的「!」图标）。
"""

from PyQt6.QtCore import Qt, QPointF, QRectF, QSize
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon, TransparentToolButton

from . import theme


class StatusIcon(QWidget):
    """行首的今日状态图标：已完成 accept / 今日未完成 alert / 运行中 play"""

    STATE_STYLES = {
        "done": (theme.COLOR_STATUS_DONE_BG, theme.COLOR_STATUS_DONE_FG, "accept", "今日已完成"),
        "pending": (theme.COLOR_STATUS_PENDING_BG, theme.COLOR_STATUS_PENDING_FG, "alert", "今日尚未完成"),
        "running": (theme.COLOR_ACCENT, theme.COLOR_CARD_BG, "play", "正在运行"),
    }

    _GLYPHS = {
        "accept": FluentIcon.ACCEPT,
        "play": FluentIcon.PLAY,
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

    def _icon_pixmap(self, kind, color):
        """把 FluentIcon 渲染成指定颜色的小位图"""
        side = theme.SIZE_STATUS_ICON - 8
        icon = self._GLYPHS[kind].icon(QColor(color))
        return icon.pixmap(QSize(side, side))

    def paintEvent(self, event):
        background, foreground, kind, _ = self.STATE_STYLES[self.state]
        size = theme.SIZE_STATUS_ICON
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(background))
        painter.drawEllipse(QRectF(0, 0, size, size))

        if kind in self._GLYPHS:
            pixmap = self._icon_pixmap(kind, foreground)
            offset = (size - pixmap.width()) / 2
            painter.drawPixmap(QPointF(offset, offset), pixmap)
            painter.end()
            return

        # 未完成态：绘制感叹号（FluentIcon 无对应图标）
        pen = QPen(QColor(foreground))
        pen.setWidthF(2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QColor(foreground))
        painter.drawLine(QPointF(11, 5.8), QPointF(11, 12.4))
        painter.drawEllipse(QRectF(9.9, 14.6, 2.2, 2.2))
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
