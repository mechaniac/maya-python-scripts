"""Per-window semantic text tinting for Maya UI.

The old word-frequency font scaling is intentionally disabled. This module now
only applies the text-color overlays for semantic labels.
"""

import html
import re


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_TAG_RE = re.compile(r"<[^>]+>")

_PROP_BASE_POINT = "_cscript_word_weight_base_point"
_PROP_BASE_WEIGHT = "_cscript_word_weight_base_weight"
_PROP_BASE_STYLESHEET = "_cscript_word_weight_base_stylesheet"
_PROP_DESCRIPTION_STYLE = "_cscript_window_description_style"

_SEMANTIC_OVERLAY = 0.8
_STRING_WORDS = {
    "name",
    "names",
    "namespace",
    "namespaces",
    "naming",
    "prefix",
    "rename",
    "renamed",
    "renaming",
    "string",
    "strings",
}
_GO_WORDS = {
    "generate",
    "generated",
    "generator",
    "play",
    "playback",
    "start",
    "started",
    "starting",
}
_DANGER_WORDS = {
    "delete",
    "deleted",
    "deleting",
    "remove",
    "removed",
    "removing",
}

_STRING_COLOR = (244, 154, 174)
_GO_COLOR = (132, 222, 150)
_DANGER_COLOR = (244, 116, 112)


def apply_deferred(window_name, min_extra=0.0, max_scale=1.0):
    """Apply semantic text tinting to a Maya window after Qt controls exist."""
    try:
        import maya.utils as maya_utils
        maya_utils.executeDeferred(
            lambda: apply_to_window(
                window_name,
                min_extra=min_extra,
                max_scale=max_scale,
            )
        )
    except Exception:
        apply_to_window(window_name, min_extra=min_extra, max_scale=max_scale)


def apply_to_window(window_name, min_extra=0.0, max_scale=1.0):
    """Tint visible text in one window by semantic keywords."""
    try:
        qt = _qt()
        root = _maya_window(window_name, qt)
    except Exception:
        return {}

    if root is None:
        return {}

    entries = _collect_text_entries(root, qt)
    if not entries:
        return {"widgets": 0, "words": 0}

    _apply_window_chrome(root, entries, qt)

    styled = 0
    for widget, text in entries:
        words = _words(text)
        if not words:
            continue

        _restore_base_font(widget, qt)
        _float_text_top(widget, qt)
        if _apply_semantic_text_color(widget, qt, text):
            styled += 1

    return {"widgets": styled, "words": 0}


def _qt():
    try:
        from PySide6 import QtWidgets, QtGui, QtCore
        from shiboken6 import wrapInstance
    except ImportError:
        from PySide2 import QtWidgets, QtGui, QtCore
        from shiboken2 import wrapInstance

    return {
        "QtWidgets": QtWidgets,
        "QtGui": QtGui,
        "QtCore": QtCore,
        "wrapInstance": wrapInstance,
    }


def _maya_window(window_name, qt):
    from maya import OpenMayaUI as omui

    ptr = omui.MQtUtil.findWindow(window_name)
    if ptr is None:
        ptr = omui.MQtUtil.findControl(window_name)
    if ptr is None:
        return None

    return qt["wrapInstance"](int(ptr), qt["QtWidgets"].QWidget)


def _collect_text_entries(root, qt):
    widgets = [root] + list(root.findChildren(qt["QtWidgets"].QWidget))
    entries = []
    for widget in widgets:
        text = _widget_text(widget, qt)
        if text:
            entries.append((widget, text))
    return entries


def _widget_text(widget, qt):
    QtWidgets = qt["QtWidgets"]

    if isinstance(widget, QtWidgets.QTabBar):
        return " ".join(
            widget.tabText(i)
            for i in range(widget.count())
            if widget.tabText(i)
        )

    if isinstance(widget, QtWidgets.QGroupBox):
        return widget.title()

    if isinstance(widget, QtWidgets.QAbstractButton):
        return widget.text()

    if isinstance(widget, QtWidgets.QLabel):
        return widget.text()

    return ""


def _word_counts(entries):
    counts = {}
    for _, text in entries:
        for word in _words(text):
            counts[word] = counts.get(word, 0) + 1
    return counts


def _words(text):
    text = _clean_text(text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = text.replace("_", " ").replace("-", " ").replace("/", " ")

    words = []
    for match in _WORD_RE.finditer(text):
        word = match.group(0).lower()
        if len(word) < 2:
            continue
        words.append(word)
    return words


def _clean_text(text):
    text = html.unescape(str(text))
    text = _TAG_RE.sub(" ", text)
    text = text.replace("&&", " ")
    text = text.replace("&", "")
    return text.strip()


def _restore_base_font(widget, qt):
    QtGui = qt["QtGui"]
    font = QtGui.QFont(widget.font())
    base_point = _base_point_size(widget, font, qt)
    base_weight = _base_weight(widget, font)
    font.setPointSizeF(base_point)
    font.setWeight(_qt_font_weight(QtGui, base_weight))
    widget.setFont(font)


def _base_point_size(widget, font, qt):
    stored = widget.property(_PROP_BASE_POINT)
    if stored is not None:
        try:
            return float(stored)
        except (TypeError, ValueError):
            pass

    point_size = font.pointSizeF()
    if point_size <= 0:
        app = qt["QtWidgets"].QApplication.instance()
        if app:
            point_size = app.font().pointSizeF()
    if point_size <= 0:
        point_size = 9.0

    widget.setProperty(_PROP_BASE_POINT, point_size)
    return point_size


def _base_weight(widget, font):
    stored = widget.property(_PROP_BASE_WEIGHT)
    if stored is not None:
        try:
            return int(stored)
        except (TypeError, ValueError):
            pass

    weight = _font_weight_value(font.weight())
    widget.setProperty(_PROP_BASE_WEIGHT, weight)
    return weight


def _font_weight_value(weight):
    try:
        return int(weight)
    except (TypeError, ValueError):
        try:
            return int(weight.value)
        except Exception:
            return 50


def _qt_font_weight(QtGui, weight):
    weight_enum = getattr(QtGui.QFont, "Weight", None)
    if weight_enum is not None:
        return weight_enum(weight)
    return weight


def _apply_semantic_text_color(widget, qt, text):
    overlay = _semantic_overlay_color(_words(text))
    if overlay is None:
        return False

    base = _base_text_color(widget, qt)
    mixed = _mix_color(base, overlay, _SEMANTIC_OVERLAY)
    style = "color: rgb({0}, {1}, {2});".format(*mixed)
    current = widget.styleSheet() or ""
    widget.setStyleSheet((current + "\n" + style).strip())
    return True


def _semantic_overlay_color(words):
    word_set = set(words)
    if word_set & _DANGER_WORDS:
        return _DANGER_COLOR
    if word_set & _GO_WORDS:
        return _GO_COLOR
    if word_set & _STRING_WORDS:
        return _STRING_COLOR
    return None


def _base_text_color(widget, qt):
    style = widget.property(_PROP_BASE_STYLESHEET)
    if style is None:
        style = widget.styleSheet() or ""
        widget.setProperty(_PROP_BASE_STYLESHEET, style)

    parsed = _last_css_color(style)
    if parsed:
        return parsed

    palette = widget.palette()
    role = widget.foregroundRole()
    color = palette.color(role)
    if not color.isValid():
        color = palette.color(qt["QtGui"].QPalette.WindowText)
    return color.red(), color.green(), color.blue()


def _last_css_color(style):
    matches = re.findall(
        r"color\s*:\s*(#[0-9a-fA-F]{6}|rgb\([^)]+\))",
        style or "",
    )
    if not matches:
        return None

    value = matches[-1].strip()
    if value.startswith("#"):
        return (
            int(value[1:3], 16),
            int(value[3:5], 16),
            int(value[5:7], 16),
        )

    numbers = [int(float(n)) for n in re.findall(r"[\d.]+", value)]
    if len(numbers) >= 3:
        return tuple(max(0, min(255, n)) for n in numbers[:3])
    return None


def _mix_color(base, overlay, amount):
    return tuple(
        int(round((overlay[i] * amount) + (base[i] * (1.0 - amount))))
        for i in range(3)
    )


def _apply_window_chrome(root, entries, qt):
    _hide_duplicate_window_titles(root, entries, qt)
    _style_window_description(root, entries, qt)


def _hide_duplicate_window_titles(root, entries, qt):
    title = _clean_text(root.windowTitle())
    if not title:
        return

    title_key = _title_key(title)
    QtWidgets = qt["QtWidgets"]
    for widget, text in entries:
        if not isinstance(widget, QtWidgets.QLabel):
            continue
        if _title_key(text) != title_key:
            continue
        widget.setVisible(False)
        try:
            widget.setMaximumHeight(0)
        except Exception:
            pass


def _style_window_description(root, entries, qt):
    title_key = _title_key(root.windowTitle())
    QtWidgets = qt["QtWidgets"]

    candidates = []
    for widget, text in entries:
        if not isinstance(widget, QtWidgets.QLabel) or _is_hidden(widget):
            continue

        clean = _clean_text(text)
        if not _looks_like_window_description(clean, title_key):
            continue

        try:
            top = widget.mapTo(root, widget.rect().topLeft()).y()
        except Exception:
            top = widget.y()
        if top > 140:
            continue

        candidates.append((top, widget))

    if not candidates:
        return

    _, widget = sorted(candidates, key=lambda item: item[0])[0]
    if widget.property(_PROP_DESCRIPTION_STYLE):
        return

    font = qt["QtGui"].QFont(widget.font())
    point_size = font.pointSizeF()
    if point_size <= 0:
        point_size = 9.0
    font.setPointSizeF(max(7.0, point_size - 1.0))
    font.setItalic(True)
    font.setWeight(_qt_font_weight(qt["QtGui"], 50))
    widget.setFont(font)
    widget.setStyleSheet(
        ((widget.styleSheet() or "") + "\n"
         "color: rgba(190, 215, 225, 150); padding: 0px 6px;").strip()
    )
    try:
        widget.setMaximumHeight(18)
    except Exception:
        pass
    widget.setProperty(_PROP_DESCRIPTION_STYLE, True)


def _looks_like_window_description(text, title_key):
    if not text:
        return False
    if _title_key(text) == title_key:
        return False
    if len(text) < 12 or len(text) > 140:
        return False
    if text.endswith(":"):
        return False

    words = _words(text)
    if len(words) < 3:
        return False
    return True


def _title_key(text):
    return re.sub(r"[^a-z0-9]+", "", _clean_text(text).lower())


def _is_hidden(widget):
    try:
        return widget.isHidden() or not widget.isVisible()
    except Exception:
        return False


def _bump_minimum_height(widget, font, qt):
    QtWidgets = qt["QtWidgets"]
    if not isinstance(widget, (QtWidgets.QAbstractButton, QtWidgets.QLabel)):
        return

    metrics = qt["QtGui"].QFontMetricsF(font)
    target = int(metrics.height() + 8)
    if widget.minimumHeight() < target:
        widget.setMinimumHeight(target)
    if widget.maximumHeight() < target:
        widget.setMaximumHeight(target)


def _float_text_top(widget, qt):
    QtWidgets = qt["QtWidgets"]

    if isinstance(widget, QtWidgets.QLabel):
        widget.setWordWrap(True)
        alignment = widget.alignment()
        horizontal = alignment & (
            qt["QtCore"].Qt.AlignLeft
            | qt["QtCore"].Qt.AlignHCenter
            | qt["QtCore"].Qt.AlignRight
            | qt["QtCore"].Qt.AlignJustify
        )
        if not horizontal:
            horizontal = qt["QtCore"].Qt.AlignLeft
        widget.setAlignment(horizontal | qt["QtCore"].Qt.AlignTop)
        try:
            widget.setMargin(max(widget.margin(), 2))
        except Exception:
            pass
        return

    if isinstance(widget, QtWidgets.QAbstractButton):
        base = widget.property(_PROP_BASE_STYLESHEET)
        if base is None:
            base = widget.styleSheet() or ""
            widget.setProperty(_PROP_BASE_STYLESHEET, base)

        extra = "padding: 0px 6px; text-align: center;"
        if extra not in base:
            widget.setStyleSheet((base + "\n" + extra).strip())
