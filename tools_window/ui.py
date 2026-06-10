import maya.cmds as cmds
import ui_word_weighting
from . import logic


THEME = {
    "window": (0.11, 0.12, 0.13),
    "field": (0.17, 0.19, 0.21),
    "field_text": "#b8d8e8",
}


AREAS = {
    "scene": {
        "header": (0.13, 0.22, 0.26),
        "panel": (0.10, 0.15, 0.17),
        "button": (0.14, 0.26, 0.31),
        "accent": "#9fe8ff",
    },
    "naming": {
        "header": (0.18, 0.15, 0.25),
        "panel": (0.13, 0.12, 0.17),
        "button": (0.23, 0.18, 0.32),
        "accent": "#cdb7ff",
    },
    "uv": {
        "header": (0.12, 0.24, 0.22),
        "panel": (0.10, 0.16, 0.15),
        "button": (0.15, 0.30, 0.27),
        "accent": "#99f0dc",
    },
    "fit": {
        "header": (0.15, 0.21, 0.24),
        "panel": (0.11, 0.15, 0.16),
        "button": (0.18, 0.26, 0.30),
        "accent": "#b3e6f4",
    },
    "layout": {
        "header": (0.17, 0.16, 0.25),
        "panel": (0.12, 0.12, 0.17),
        "button": (0.22, 0.20, 0.32),
        "accent": "#c7c0ff",
    },
}


_QT_STYLES = {}


def _apply_bg(control, color):
    for command in (cmds.control, cmds.layout):
        try:
            command(control, edit=True, backgroundColor=color)
            return
        except Exception:
            pass


def _css_rgb(color):
    return "rgb({0}, {1}, {2})".format(
        int(color[0] * 255),
        int(color[1] * 255),
        int(color[2] * 255),
    )


def _shift_color(color, amount):
    return tuple(max(0.0, min(1.0, channel + amount)) for channel in color)


def _remember_style(control, fg=None, bg=None, padding=None,
                    top=True, border=False):
    parts = []
    if bg:
        parts.append("background-color: {0};".format(_css_rgb(bg)))
    if fg:
        parts.append("color: {0};".format(fg))
    if padding:
        parts.append("padding: {0};".format(padding))
    if top:
        parts.append("text-align: center;")
    if border:
        parts.append("border: 1px solid rgba(255, 255, 255, 28);")
    if parts:
        _QT_STYLES[control] = " ".join(parts)


def _remember_button_style(control, area_key):
    area = AREAS[area_key]
    bg = area["button"]
    hover = _shift_color(bg, 0.075)
    pressed = _shift_color(bg, -0.075)
    accent = area["accent"]
    _QT_STYLES[control] = """
        QPushButton {{
            background-color: {bg};
            color: {fg};
            border: 1px solid rgba(255, 255, 255, 32);
            padding: 0px 6px;
            text-align: center;
        }}
        QPushButton:hover {{
            background-color: {hover};
            border: 1px solid {fg};
        }}
        QPushButton:pressed {{
            background-color: {pressed};
            border: 1px solid rgba(0, 0, 0, 150);
            padding: 1px 5px 0px 7px;
        }}
        QPushButton:disabled {{
            color: rgba(180, 190, 196, 120);
            background-color: rgb(50, 54, 58);
            border: 1px solid rgba(255, 255, 255, 16);
        }}
    """.format(
        bg=_css_rgb(bg),
        fg=accent,
        hover=_css_rgb(hover),
        pressed=_css_rgb(pressed),
    )


def _apply_qt_styles_deferred():
    try:
        import maya.utils as maya_utils
        maya_utils.executeDeferred(_apply_qt_styles)
    except Exception:
        _apply_qt_styles()


def _finish_qt_styles_deferred(win_id):
    def _finish():
        _apply_qt_styles()
        _disable_horizontal_scroll()
        ui_word_weighting.apply_to_window(win_id)

    try:
        import maya.utils as maya_utils
        maya_utils.executeDeferred(_finish)
    except Exception:
        _finish()


def _apply_qt_styles():
    try:
        from maya import OpenMayaUI as omui
        try:
            from PySide6 import QtWidgets, QtCore
            from shiboken6 import wrapInstance
        except ImportError:
            from PySide2 import QtWidgets, QtCore
            from shiboken2 import wrapInstance
    except Exception:
        return

    for control, style in _QT_STYLES.items():
        ptr = omui.MQtUtil.findControl(control)
        if ptr is None:
            ptr = omui.MQtUtil.findLayout(control)
        if ptr is None:
            continue

        widget = wrapInstance(int(ptr), QtWidgets.QWidget)
        existing = widget.styleSheet() or ""
        if style not in existing:
            widget.setStyleSheet((existing + "\n" + style).strip())


def _disable_horizontal_scroll():
    try:
        from maya import OpenMayaUI as omui
        try:
            from PySide6 import QtWidgets, QtCore
            from shiboken6 import wrapInstance
        except ImportError:
            from PySide2 import QtWidgets, QtCore
            from shiboken2 import wrapInstance
    except Exception:
        return

    ptr = omui.MQtUtil.findLayout("sceneCleanupScroll")
    if ptr is None:
        return

    widget = wrapInstance(int(ptr), QtWidgets.QWidget)
    scroll_area = widget if isinstance(widget, QtWidgets.QScrollArea) else None
    if scroll_area is None:
        scroll_area = widget.findChild(QtWidgets.QScrollArea)
    if scroll_area is not None:
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)


def _title(parent, label, area_key):
    area = AREAS[area_key]
    control = cmds.text(
        parent=parent,
        label=label,
        align="center",
        height=22,
        font="boldLabelFont",
    )
    _apply_bg(control, area["header"])
    _remember_style(control, fg=area["accent"], bg=area["header"],
                    padding="2px 6px")
    return control


def _label(parent, label, area_key):
    area = AREAS[area_key]
    control = cmds.text(parent=parent, label=label, align="left", height=20)
    _remember_style(control, fg=area["accent"], padding="1px 2px")
    return control


def _button(parent, label, command, area_key, height=20, width=None):
    area = AREAS[area_key]
    kwargs = {}
    if width is not None:
        kwargs["width"] = width

    control = cmds.button(
        parent=parent,
        label=label,
        height=height,
        command=command,
        **kwargs
    )
    _apply_bg(control, area["button"])
    _remember_button_style(control, area_key)
    return control


def _section(parent, label, area_key):
    area = AREAS[area_key]
    frame = cmds.frameLayout(
        parent=parent,
        label=label,
        collapsable=True,
        collapse=False,
        marginWidth=6,
        marginHeight=4,
    )
    _apply_bg(frame, area["header"])
    _remember_style(frame, fg=area["accent"], bg=area["header"],
                    padding="2px 6px")

    body = cmds.columnLayout(
        parent=frame,
        adjustableColumn=True,
        rowSpacing=2,
        columnAlign="center",
    )
    _apply_bg(body, area["panel"])
    return body


def _field(control, area_key):
    area = AREAS[area_key]
    _apply_bg(control, THEME["field"])
    _remember_style(
        control,
        fg=area["accent"],
        bg=THEME["field"],
        padding="1px 5px",
        top=False,
    )
    return control


def show_window():
    win_id = "sceneCleanupWin"
    _QT_STYLES.clear()

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(
        win_id,
        title="Scene Tools",
        widthHeight=(460, 620),
        sizeable=True,
    )

    scroll = cmds.scrollLayout(
        "sceneCleanupScroll",
        verticalScrollBarThickness=12,
        horizontalScrollBarThickness=0,
        childResizable=True,
    )
    _apply_bg(scroll, THEME["window"])

    main = cmds.columnLayout(
        parent=scroll,
        adjustableColumn=True,
        rowSpacing=2,
        columnAlign="center",
    )
    _apply_bg(main, THEME["window"])

    scene = _section(main, "Scene And View", "scene")
    _button(scene, "Clean Scene", logic.run_cleanup, "scene")
    _button(
        scene,
        "Toggle Display Affected",
        logic.toggle_display_affected,
        "scene",
    )

    naming = _section(main, "Naming", "naming")
    _label(naming, "Rename Selected Nodes", "naming")
    _field(cmds.textField(
        "renameBaseField",
        parent=naming,
        placeholderText="Base name here...",
    ), "naming")
    _button(naming, "Rename with _##", logic.rename_selected, "naming")

    remove_row = cmds.rowLayout(
        parent=naming,
        numberOfColumns=2,
        adjustableColumn=1,
        columnWidth2=(280, 116),
        columnAttach2=("both", "both"),
    )
    _field(cmds.textField(
        "removeStringField",
        parent=remove_row,
        placeholderText="String to remove...",
    ), "naming")
    _button(
        remove_row,
        "Remove",
        logic.remove_string_from_names,
        "naming",
    )

    uv = _section(main, "UV Edits", "uv")
    _button(
        uv,
        "Create 'layout' UVset from map1",
        logic.ensure_layout_uvset_from_map1,
        "uv",
    )
    _button(
        uv,
        "Normalize + Pack UV1 'layout' (0..1)",
        logic.normalize_layout_uvs_non_overlapping,
        "uv",
    )
    _button(
        uv,
        "Set UV0 to LeZooColorGradient",
        logic.set_uv0_to_lezoo_color_gradient,
        "uv",
    )
    _button(uv, "Rename UVsets", logic.rename_uv_sets, "uv")
    _button(uv, "Log UV Sets", logic.log_uv_sets, "uv")
    _button(uv, "Set UVs to 00", logic.set_uv_set_0, "uv")
    _button(uv, "Set UVs to 01", logic.set_uv_set_1, "uv")
    _button(uv, "Delete Extra UV Sets", logic.delete_extra_uv_sets, "uv")
    _button(uv, "Delete Third UVset", logic.delete_third_uv_set, "uv")

    fit = _section(main, "Fit To Bounding Box", "fit")
    _field(cmds.floatFieldGrp(
        "fitBoxField",
        parent=fit,
        label="Target Box",
        numberOfFields=3,
        value1=1.0,
        value2=1.0,
        value3=1.0,
    ), "fit")

    fit_row = cmds.rowLayout(
        parent=fit,
        numberOfColumns=2,
        adjustableColumn=1,
        columnWidth2=(280, 116),
        columnAttach2=("both", "both"),
    )
    menu = cmds.optionMenu("fitScaleModeMenu", parent=fit_row, label="Scale Mode")
    cmds.menuItem(parent=menu, label="Uniform")
    cmds.menuItem(parent=menu, label="Non-uniform")
    _field(menu, "fit")
    check = cmds.checkBox(
        "centerGroundPivotCB",
        parent=fit_row,
        label="Ground Pivot",
        value=False,
    )
    _remember_style(check, fg=AREAS["fit"]["accent"], padding="3px 4px")
    _button(
        fit,
        "Fit Selected + Freeze",
        logic.scale_selected_to_bounding_box,
        "fit",
    )

    layout = _section(main, "Layout And Instancing", "layout")
    grid_row = cmds.rowLayout(
        parent=layout,
        numberOfColumns=2,
        adjustableColumn=2,
        columnWidth2=(110, 286),
        columnAttach2=("both", "both"),
    )
    grid_label = cmds.text(parent=grid_row, label="Grid Spacing", align="left")
    _remember_style(grid_label, fg=AREAS["layout"]["accent"],
                    padding="1px 2px")
    _field(cmds.floatField("gridSpacingField", parent=grid_row, value=5.0),
           "layout")
    _button(layout, "Grid Place Selected", logic.grid_place_selected, "layout")
    _button(layout, "Create Spiral Curve", logic.open_spiral_window, "layout")

    _title(layout, "Circular Instancing", "layout")
    instance_row = cmds.rowColumnLayout(
        parent=layout,
        numberOfColumns=4,
        columnWidth=[(1, 70), (2, 110), (3, 70), (4, 110)],
        columnSpacing=[(1, 4), (2, 8), (3, 4), (4, 4)],
    )
    count_label = cmds.text(parent=instance_row, label="Count", align="left")
    _remember_style(count_label, fg=AREAS["layout"]["accent"],
                    padding="1px 2px")
    _field(cmds.intField("instanceCountField", parent=instance_row, value=8),
           "layout")
    radius_label = cmds.text(parent=instance_row, label="Radius", align="left")
    _remember_style(radius_label, fg=AREAS["layout"]["accent"],
                    padding="1px 2px")
    _field(cmds.floatField("instanceRadiusField", parent=instance_row, value=0.0),
           "layout")

    _button(layout, "Instances", logic.on_create_instances, "layout")
    _button(layout, "Copies", logic.on_create_copies, "layout")
    _button(layout, "Delete", logic.delete_instances, "layout")

    cmds.showWindow(win_id)
    _finish_qt_styles_deferred(win_id)
