"""Reusable slider widgets (PySide6) with notches and color tinting.

* ``RangeSlider`` – dual-handle (low / high).
* ``SingleSlider`` – one handle, replaces ``floatSliderGrp`` visually.

Embed into Maya cmds layouts via ``embed_in_layout()`` /
``embed_single_in_layout()``.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from shiboken6 import wrapInstance
import maya.OpenMayaUI as omui

# ── shared paint helpers ──

_TRACK_BG = QtGui.QColor(30, 30, 30)


def _notch_step(minimum, maximum):
    total = int(maximum - minimum)
    if total > 200:
        return total // 40
    if total > 60:
        return 5
    return 1


def _draw_notches(p, minimum, maximum, pad, usable, track_y, track_h, val_to_x):
    """Draw integer-step notch marks on a slider track."""
    if usable <= 0 or (maximum - minimum) <= 0:
        return
    step = _notch_step(minimum, maximum)
    first = int(minimum) if minimum == int(minimum) else int(minimum) + 1
    v = first
    while v <= maximum:
        x = int(val_to_x(v))
        if v == 0:
            p.setPen(QtGui.QPen(QtGui.QColor(180, 180, 180, 140), 1))
            p.drawLine(x, track_y - 1, x, track_y + track_h + 1)
        else:
            p.setPen(QtGui.QPen(QtGui.QColor(80, 80, 80, 100), 1))
            p.drawLine(x, track_y, x, track_y + track_h)
        v += step
    p.setPen(QtCore.Qt.NoPen)


def _color_brushes(color):
    """Return (bar_clr, handle_clr) from a 0-1 RGB tuple, or defaults.

    The bar stays neutral; only the handle is tinted.
    """
    bar = QtGui.QColor(100, 100, 100, 180)
    if color:
        r, g, b = [int(c * 255) for c in color]
        handle = QtGui.QColor(min(r + 120, 235), min(g + 120, 235),
                              min(b + 120, 235))
    else:
        handle = QtGui.QColor(158, 158, 158)
    return bar, handle


class RangeSlider(QtWidgets.QWidget):
    """Dual-handle range slider styled like Maya's native sliders."""

    rangeChanged = QtCore.Signal(float, float)
    handleChanged = QtCore.Signal(str)   # 'low', 'high', or ''

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
        self._active = None          # 'low' | 'high' | None
        self.setMouseTracking(True)

        self._track_bg = _TRACK_BG
        self._bar_clr, self._handle_clr = _color_brushes(color)

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

        # notches
        _draw_notches(p, self.minimum, self.maximum, pad, usable,
                      track_y, track_h, self._val_to_x)

        # selected range bar
        x1 = int(self._val_to_x(self.low))
        x2 = int(self._val_to_x(self.high))
        if x2 > x1:
            p.setBrush(self._bar_clr)
            p.drawRect(x1, track_y, x2 - x1, track_h)

        # handles — small vertical tabs (highlight active)
        hy = (h - handle_h) // 2
        active_pen = QtGui.QPen(QtGui.QColor(200, 200, 200), 1)
        normal_pen = QtGui.QPen(QtGui.QColor(90, 90, 90), 1)
        p.setBrush(self._handle_clr)
        p.setPen(active_pen if self._active == 'low' else normal_pen)
        p.drawRect(x1 - handle_w // 2, hy, handle_w, handle_h)
        p.setPen(active_pen if self._active == 'high' else normal_pen)
        p.drawRect(x2 - handle_w // 2, hy, handle_w, handle_h)
        p.end()

    # ── mouse ──

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        mx = event.position().x()
        lx = self._val_to_x(self.low)
        hx = self._val_to_x(self.high)

        if abs(mx - lx) < 10 and abs(mx - hx) < 10:
            # handles overlap — pick based on which side of center
            self._dragging = 'low'
            self._active = 'low'
        elif abs(mx - lx) < 10:
            self._dragging = 'low'
            self._active = 'low'
        elif abs(mx - hx) < 10:
            self._dragging = 'high'
            self._active = 'high'
        elif lx < mx < hx:
            self._dragging = 'range'
            self._drag_offset = mx - lx
            self._active = None
        else:
            self._dragging = None
            self._active = None
        self.handleChanged.emit(self._active or '')
        self.update()

    def mouseMoveEvent(self, event):
        if self._dragging is None:
            return
        mx = event.position().x()

        if self._dragging == 'low':
            v = self._x_to_val(mx)
            if v > self.high:
                # auto-switch: promote low drag to high
                self.low = self.high
                self.high = min(self.maximum, v)
                self._dragging = 'high'
                self._active = 'high'
                self.handleChanged.emit('high')
            else:
                self.low = max(self.minimum, v)
        elif self._dragging == 'high':
            v = self._x_to_val(mx)
            if v < self.low:
                # auto-switch: demote high drag to low
                self.high = self.low
                self.low = max(self.minimum, v)
                self._dragging = 'low'
                self._active = 'low'
                self.handleChanged.emit('low')
            else:
                self.high = min(self.maximum, v)
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
        self._active = None
        self.handleChanged.emit('')
        self.update()


# ────────────────────────────────────────────────────────────
#  SingleSlider — one handle, replaces floatSliderGrp visually
# ────────────────────────────────────────────────────────────

class SingleSlider(QtWidgets.QWidget):
    """Single-handle slider with dark track, notches, and color tint."""

    valueChanged = QtCore.Signal(float)

    def __init__(self, parent=None, minimum=-60, maximum=60,
                 value=0, color=None):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setMinimumWidth(60)
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self._value = max(self.minimum, min(float(value), self.maximum))
        self._dragging = False
        self.setMouseTracking(True)

        self._track_bg = _TRACK_BG
        self._bar_clr, self._handle_clr = _color_brushes(color)

    # ── public API ──

    def value(self):
        return self._value

    def setValue(self, v):
        self._value = max(self.minimum, min(float(v), self.maximum))
        self.update()

    def setRange(self, mn, mx):
        self.minimum = float(mn)
        self.maximum = float(mx)
        self._value = max(self.minimum, min(self._value, self.maximum))
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

        # notches
        _draw_notches(p, self.minimum, self.maximum, pad, usable,
                      track_y, track_h, self._val_to_x)

        # fill bar from left to handle
        vx = int(self._val_to_x(self._value))
        if vx > pad:
            p.setBrush(self._bar_clr)
            p.drawRect(pad, track_y, vx - pad, track_h)

        # handle
        hy = (h - handle_h) // 2
        p.setBrush(self._handle_clr)
        p.setPen(QtGui.QPen(QtGui.QColor(90, 90, 90), 1))
        p.drawRect(vx - handle_w // 2, hy, handle_w, handle_h)
        p.end()

    # ── mouse ──

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        self._dragging = True
        self._update_from_mouse(event.position().x())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_from_mouse(event.position().x())

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def _update_from_mouse(self, mx):
        v = self._x_to_val(mx)
        v = max(self.minimum, min(v, self.maximum))
        if v != self._value:
            self._value = v
            self.update()
            self.valueChanged.emit(self._value)


# ────────────────────────────────────────────────────────────
#  Embedding helpers
# ────────────────────────────────────────────────────────────

def _find_qt_parent(cmds_layout):
    ptr = omui.MQtUtil.findLayout(cmds_layout)
    if not ptr:
        ptr = omui.MQtUtil.findControl(cmds_layout)
    if not ptr:
        raise RuntimeError('Cannot find Qt object for: {}'.format(cmds_layout))
    return wrapInstance(int(ptr), QtWidgets.QWidget)


def _parent_widget(widget, qt_parent):
    layout = qt_parent.layout()
    if layout:
        layout.addWidget(widget)
    else:
        widget.setParent(qt_parent)
        widget.show()


def embed_in_layout(cmds_layout, **kwargs):
    """Create a RangeSlider and parent it under a cmds layout."""
    qt_parent = _find_qt_parent(cmds_layout)
    slider = RangeSlider(qt_parent, **kwargs)
    _parent_widget(slider, qt_parent)
    return slider


def embed_single_in_layout(cmds_layout, **kwargs):
    """Create a SingleSlider and parent it under a cmds layout."""
    qt_parent = _find_qt_parent(cmds_layout)
    slider = SingleSlider(qt_parent, **kwargs)
    _parent_widget(slider, qt_parent)
    return slider
