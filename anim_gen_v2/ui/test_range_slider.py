"""Standalone range-slider test window (PySide6 / Qt).

Run in Maya::

    from anim_gen_v2.ui import test_range_slider
    test_range_slider.show()

    # reload:
    import importlib
    from anim_gen_v2.ui import test_range_slider
    importlib.reload(test_range_slider)
    test_range_slider.show()
"""

import maya.cmds as cmds
from PySide6 import QtWidgets, QtCore, QtGui
from shiboken6 import wrapInstance
import maya.OpenMayaUI as omui

def get_maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)

class TrueRangeSlider(QtWidgets.QWidget):
    rangeChanged = QtCore.Signal(int, int)

    def __init__(self, parent=None, minimum=0, maximum=200):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.minimum = minimum
        self.maximum = maximum
        self.low = minimum + 40
        self.high = maximum - 40
        self._dragging = None        # "low", "high", or "range"
        self._drag_offset = 0
        self.setMouseTracking(True)

    def value(self):
        return (self.low, self.high)

    def setValue(self, low, high):
        self.low = max(self.minimum, min(low, self.high - 1))
        self.high = min(self.maximum, max(high, self.low + 1))
        self.update()
        self.rangeChanged.emit(self.low, self.high)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w, h = self.width(), self.height()
        pad = 6
        track_y = h // 2 - 2
        track_height = 5
        handle_w = 8
        handle_h = h - 4

        # Background track
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(42, 42, 42))
        painter.drawRect(pad, track_y, w - 2 * pad, track_height)

        # Selected range bar
        if self.low < self.high:
            x1 = pad + int((self.low - self.minimum) / (self.maximum - self.minimum) * (w - 2 * pad))
            x2 = pad + int((self.high - self.minimum) / (self.maximum - self.minimum) * (w - 2 * pad))
            painter.setBrush(QtGui.QColor(100, 100, 100))
            painter.drawRect(x1, track_y, x2 - x1, track_height)

        # Handles — small vertical tabs
        low_x = pad + int((self.low - self.minimum) / (self.maximum - self.minimum) * (w - 2 * pad))
        high_x = pad + int((self.high - self.minimum) / (self.maximum - self.minimum) * (w - 2 * pad))
        hy = (h - handle_h) // 2

        painter.setBrush(QtGui.QColor(158, 158, 158))
        painter.setPen(QtGui.QPen(QtGui.QColor(90, 90, 90), 1))
        painter.drawRect(low_x - handle_w // 2, hy, handle_w, handle_h)
        painter.drawRect(high_x - handle_w // 2, hy, handle_w, handle_h)

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return

        w = self.width()
        pad = 6
        low_x = pad + int((self.low - self.minimum) / (self.maximum - self.minimum) * (w - 2 * pad))
        high_x = pad + int((self.high - self.minimum) / (self.maximum - self.minimum) * (w - 2 * pad))
        pos = int(event.position().x())

        if abs(pos - low_x) < 10:
            self._dragging = "low"
        elif abs(pos - high_x) < 10:
            self._dragging = "high"
        elif low_x < pos < high_x:               # clicked on blue bar
            self._dragging = "range"
            self._drag_offset = pos - low_x       # store relative position to left handle
        else:
            self._dragging = None

        self.update()

    def mouseMoveEvent(self, event):
        if self._dragging is None:
            return

        w = self.width()
        pad = 6
        pos = max(pad, min(int(event.position().x()), w - pad))

        if self._dragging == "low":
            new_val = self.minimum + int((pos - pad) / (w - 2 * pad) * (self.maximum - self.minimum))
            self.low = min(new_val, self.high - 1)

        elif self._dragging == "high":
            new_val = self.minimum + int((pos - pad) / (w - 2 * pad) * (self.maximum - self.minimum))
            self.high = max(new_val, self.low + 1)

        elif self._dragging == "range":
            # Move entire range while preserving width
            width = self.high - self.low
            # Calculate where the left handle should be based on mouse position + original offset
            new_low = self.minimum + int((pos - self._drag_offset - pad) / (w - 2 * pad) * (self.maximum - self.minimum))
            new_low = max(self.minimum, min(new_low, self.maximum - width))
            self.low = new_low
            self.high = new_low + width

        self.update()
        self.rangeChanged.emit(self.low, self.high)

    def mouseReleaseEvent(self, event):
        self._dragging = None

# ====================== Main Window ======================
class RangeSliderWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Maya 2026 - Range Slider (Fixed Range Drag)")
        self.resize(580, 120)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        self.slider = TrueRangeSlider(self, minimum=0, maximum=200)
        self.slider.rangeChanged.connect(self.on_range_changed)

        layout.addWidget(self.slider)

        form = QtWidgets.QFormLayout()
        self.min_spin = QtWidgets.QSpinBox()
        self.max_spin = QtWidgets.QSpinBox()
        self.min_spin.setRange(0, 1000)
        self.max_spin.setRange(0, 1000)
        form.addRow("Min Value:", self.min_spin)
        form.addRow("Max Value:", self.max_spin)
        layout.addLayout(form)

        self.min_spin.valueChanged.connect(self.sync_from_spins)
        self.max_spin.valueChanged.connect(self.sync_from_spins)

        low, high = self.slider.value()
        self.min_spin.setValue(low)
        self.max_spin.setValue(high)

    def on_range_changed(self, low, high):
        self.min_spin.setValue(low)
        self.max_spin.setValue(high)

    def sync_from_spins(self):
        low = self.min_spin.value()
        high = self.max_spin.value()
        if low >= high:
            low = high - 1
            self.min_spin.setValue(low)
        self.slider.setValue(low, high)


_win = None

def show():
    global _win
    if _win is not None:
        try:
            _win.close()
        except Exception:
            pass
    _win = RangeSliderWindow(get_maya_main_window())
    _win.show()
    return _win
