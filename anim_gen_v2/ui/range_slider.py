"""Reusable dual-handle range slider widget (PySide6).

Embeds into Maya cmds layouts via ``embed_in_layout(cmds_layout)``.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from shiboken6 import wrapInstance
import maya.OpenMayaUI as omui


class RangeSlider(QtWidgets.QWidget):
    """Dual-handle range slider styled like Maya's native sliders."""

    rangeChanged = QtCore.Signal(float, float)

    def __init__(self, parent=None, minimum=-60, maximum=60,
                 low=-5, high=5):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setMinimumWidth(60)
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.low = float(low)
        self.high = float(high)
        self._dragging = None
        self._drag_offset = 0
        self.setMouseTracking(True)

    # ── public API ──

    def value(self):
        return (self.low, self.high)

    def setLow(self, v):
        self.low = max(self.minimum, min(float(v), self.high))
        self.update()

    def setHigh(self, v):
        self.high = min(self.maximum, max(float(v), self.low))
        self.update()

    def setValue(self, low, high):
        self.low = max(self.minimum, min(float(low), float(high)))
        self.high = min(self.maximum, max(float(high), float(low)))
        self.update()

    # ── coordinate helpers ──

    _PAD = 6

    def _val_to_x(self, val):
        span = self.maximum - self.minimum
        if span == 0:
            return self._PAD
        return self._PAD + (val - self.minimum) / span * (self.width() - 2 * self._PAD)

    def _x_to_val(self, x):
        usable = self.width() - 2 * self._PAD
        if usable <= 0:
            return self.minimum
        return self.minimum + (x - self._PAD) / usable * (self.maximum - self.minimum)

    # ── paint ──

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad = self._PAD
        track_y = h // 2 - 2
        track_h = 5
        handle_w = 8
        handle_h = h - 4

        # background track
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(42, 42, 42))
        p.drawRect(pad, track_y, w - 2 * pad, track_h)

        # selected range bar
        x1 = int(self._val_to_x(self.low))
        x2 = int(self._val_to_x(self.high))
        if x2 > x1:
            p.setBrush(QtGui.QColor(100, 100, 100))
            p.drawRect(x1, track_y, x2 - x1, track_h)

        # handles — small vertical tabs
        hy = (h - handle_h) // 2
        p.setBrush(QtGui.QColor(158, 158, 158))
        p.setPen(QtGui.QPen(QtGui.QColor(90, 90, 90), 1))
        p.drawRect(x1 - handle_w // 2, hy, handle_w, handle_h)
        p.drawRect(x2 - handle_w // 2, hy, handle_w, handle_h)
        p.end()

    # ── mouse ──

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        mx = event.position().x()
        lx = self._val_to_x(self.low)
        hx = self._val_to_x(self.high)

        if abs(mx - lx) < 10:
            self._dragging = 'low'
        elif abs(mx - hx) < 10:
            self._dragging = 'high'
        elif lx < mx < hx:
            self._dragging = 'range'
            self._drag_offset = mx - lx
        else:
            self._dragging = None
        self.update()

    def mouseMoveEvent(self, event):
        if self._dragging is None:
            return
        mx = event.position().x()

        if self._dragging == 'low':
            v = self._x_to_val(mx)
            self.low = max(self.minimum, min(v, self.high))
        elif self._dragging == 'high':
            v = self._x_to_val(mx)
            self.high = min(self.maximum, max(v, self.low))
        elif self._dragging == 'range':
            span = self.high - self.low
            new_low = self._x_to_val(mx - self._drag_offset)
            new_low = max(self.minimum, min(new_low, self.maximum - span))
            self.low = new_low
            self.high = new_low + span

        self.update()
        self.rangeChanged.emit(self.low, self.high)

    def mouseReleaseEvent(self, event):
        self._dragging = None


def embed_in_layout(cmds_layout, **kwargs):
    """Create a RangeSlider and parent it under a cmds layout.

    Returns the RangeSlider widget instance.
    """
    ptr = omui.MQtUtil.findLayout(cmds_layout)
    if not ptr:
        ptr = omui.MQtUtil.findControl(cmds_layout)
    if not ptr:
        raise RuntimeError('Cannot find Qt object for: {}'.format(cmds_layout))
    qt_parent = wrapInstance(int(ptr), QtWidgets.QWidget)
    slider = RangeSlider(qt_parent, **kwargs)
    layout = qt_parent.layout()
    if layout:
        layout.addWidget(slider)
    else:
        slider.setParent(qt_parent)
        slider.show()
    return slider
