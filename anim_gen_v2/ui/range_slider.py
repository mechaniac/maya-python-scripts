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
                 low=-5, high=5, color=None):
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

        # color tint — expects (r, g, b) floats 0-1 or None
        if color:
            r, g, b = [int(c * 255) for c in color]
            self._track_bg = QtGui.QColor(max(r, 35), max(g, 35), max(b, 35))
            self._bar_clr = QtGui.QColor(min(r + 60, 200),
                                         min(g + 60, 200),
                                         min(b + 60, 200), 180)
            self._handle_clr = QtGui.QColor(min(r + 100, 220),
                                            min(g + 100, 220),
                                            min(b + 100, 220))
        else:
            self._track_bg = QtGui.QColor(42, 42, 42)
            self._bar_clr = QtGui.QColor(100, 100, 100, 180)
            self._handle_clr = QtGui.QColor(158, 158, 158)

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

    def setRange(self, mn, mx):
        self.minimum = float(mn)
        self.maximum = float(mx)
        self.low = max(self.minimum, self.low)
        self.high = min(self.maximum, self.high)
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
        usable = w - 2 * pad

        # background track
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(self._track_bg)
        p.drawRect(pad, track_y, usable, track_h)

        # notches — integer steps
        if usable > 0 and (self.maximum - self.minimum) > 0:
            step = 1
            # avoid drawing too many notches when range is huge
            total_steps = int(self.maximum - self.minimum)
            if total_steps > 200:
                step = total_steps // 40
            elif total_steps > 60:
                step = 5
            first = int(self.minimum) if self.minimum == int(self.minimum) \
                else int(self.minimum) + 1
            v = first
            while v <= self.maximum:
                x = int(self._val_to_x(v))
                if v == 0:
                    # bold center notch
                    p.setPen(QtGui.QPen(QtGui.QColor(180, 180, 180, 140), 1))
                    p.drawLine(x, track_y - 1, x, track_y + track_h + 1)
                else:
                    p.setPen(QtGui.QPen(QtGui.QColor(80, 80, 80, 100), 1))
                    p.drawLine(x, track_y, x, track_y + track_h)
                v += step
            p.setPen(QtCore.Qt.NoPen)

        # selected range bar
        x1 = int(self._val_to_x(self.low))
        x2 = int(self._val_to_x(self.high))
        if x2 > x1:
            p.setBrush(self._bar_clr)
            p.drawRect(x1, track_y, x2 - x1, track_h)

        # handles — small vertical tabs
        hy = (h - handle_h) // 2
        p.setBrush(self._handle_clr)
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
