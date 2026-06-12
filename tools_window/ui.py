import maya.cmds as cmds
import crash_logger
import ui_word_weighting
from . import logic


THEME = {
    "window": (0.11, 0.12, 0.13),
    "field": (0.17, 0.19, 0.21),
    "field_text": "#b8d8e8",
}


AREAS = {
    "scene": {
        "header": (0.12, 0.22, 0.27),
        "panel": (0.09, 0.14, 0.17),
        "button": (0.13, 0.25, 0.31),
        "accent": "#9fe8ff",
    },
    "naming": {
        "header": (0.17, 0.15, 0.25),
        "panel": (0.12, 0.11, 0.17),
        "button": (0.21, 0.18, 0.32),
        "accent": "#cdb7ff",
    },
    "uv": {
        "header": (0.10, 0.23, 0.24),
        "panel": (0.08, 0.15, 0.16),
        "button": (0.12, 0.28, 0.29),
        "accent": "#99f0dc",
    },
    "poly": {
        "header": (0.13, 0.22, 0.23),
        "panel": (0.09, 0.14, 0.15),
        "button": (0.15, 0.26, 0.27),
        "accent": "#b7edf2",
    },
    "fit": {
        "header": (0.15, 0.21, 0.24),
        "panel": (0.11, 0.15, 0.16),
        "button": (0.18, 0.26, 0.30),
        "accent": "#b3e6f4",
    },
    "chain": {
        "header": (0.12, 0.20, 0.25),
        "panel": (0.09, 0.13, 0.17),
        "button": (0.14, 0.23, 0.30),
        "accent": "#a9d7ed",
    },
    "layout": {
        "header": (0.17, 0.16, 0.25),
        "panel": (0.12, 0.12, 0.17),
        "button": (0.22, 0.20, 0.32),
        "accent": "#c7c0ff",
    },
}


_QT_STYLES = {}
_SECTION_FRAMES = []
_UI_BUTTONS = []
_BUTTON_ACTION_BUSY = False
_BUTTON_ACTION_LABEL = None
_BUTTON_ACTION_AUTO_KEY_STATE = None
WIN_ID = "sceneCleanupWin"
MAIN_ID = "sceneCleanupMain"
COMPACT_WIDTH = 360
_BUTTON_RELEASE_IDLE_STEPS = 3
_OVERLAY_AMOUNT = 0.46
_ACTION_OVERLAYS = (
    (
        ("stop", "delete", "remove", "undo"),
        (0.78, 0.18, 0.16),
        "#ffd4d0",
    ),
    (
        ("folder", "path", "directory"),
        (0.82, 0.68, 0.24),
        "#fff0b5",
    ),
    (
        ("create", "generate", "save"),
        (0.18, 0.62, 0.32),
        "#c7ffd5",
    ),
)


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


def _blend_color(base, overlay, amount):
    return tuple(
        max(0.0, min(1.0, (base[index] * (1.0 - amount))
                     + (overlay[index] * amount)))
        for index in range(3)
    )


def _semantic_button_style(label, base_bg, base_fg):
    words = str(label or "").lower()
    for keywords, overlay, fg in _ACTION_OVERLAYS:
        if any(keyword in words for keyword in keywords):
            return _blend_color(base_bg, overlay, _OVERLAY_AMOUNT), fg
    return base_bg, base_fg


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


def _remember_button_style(control, area_key, label):
    area = AREAS[area_key]
    bg, accent = _semantic_button_style(
        label,
        area["button"],
        area["accent"],
    )
    hover = _shift_color(bg, 0.075)
    pressed = _shift_color(bg, -0.075)
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
        ui_word_weighting.apply_to_window(win_id)
        _fit_window_to_children(win_id)

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


def _fit_window_to_children_deferred(win_id=WIN_ID):
    def _deferred_fit():
        _fit_window_to_children(win_id)
        try:
            import maya.utils as maya_utils
            maya_utils.executeDeferred(lambda: _fit_window_to_children(win_id))
        except Exception:
            pass

    try:
        import maya.utils as maya_utils
        maya_utils.executeDeferred(_deferred_fit)
    except Exception:
        _fit_window_to_children(win_id)


def _fit_window_to_children(win_id=WIN_ID):
    try:
        if cmds.window(win_id, exists=True):
            cmds.window(win_id, edit=True, resizeToFitChildren=True)
    except Exception:
        pass

    try:
        from maya import OpenMayaUI as omui
        try:
            from PySide6 import QtWidgets
            from shiboken6 import wrapInstance
        except ImportError:
            from PySide2 import QtWidgets
            from shiboken2 import wrapInstance
    except Exception:
        return

    ptr = _qt_ptr(omui, win_id)
    if ptr is None:
        return

    widget = wrapInstance(int(ptr), QtWidgets.QWidget)
    main_ptr = omui.MQtUtil.findLayout(MAIN_ID)
    if widget is None or main_ptr is None:
        return

    main_widget = wrapInstance(int(main_ptr), QtWidgets.QWidget)
    if main_widget is None:
        return

    section_size = _section_stack_size(omui, QtWidgets, wrapInstance)
    if section_size is None:
        main_widget.updateGeometry()
        main_widget.adjustSize()
        fallback_size = main_widget.minimumSizeHint()
        section_size = fallback_size.width(), fallback_size.height()

    content_margin = 18
    title_margin = 34
    section_width, section_height = section_size
    target_width = max(COMPACT_WIDTH, section_width + content_margin)
    target_height = max(1, section_height + title_margin)

    try:
        if cmds.window(win_id, exists=True):
            cmds.window(
                win_id,
                edit=True,
                widthHeight=(int(target_width), int(target_height)),
            )
    except Exception:
        pass

    _force_window_height(widget, int(target_width), int(target_height))


def _force_window_height(widget, width, height):
    try:
        widget.setMinimumHeight(height)
        widget.setMaximumHeight(height)
        widget.resize(width, height)
        widget.updateGeometry()
    except Exception:
        pass


def _qt_ptr(omui, name):
    for finder in (omui.MQtUtil.findWindow,
                   omui.MQtUtil.findControl,
                   omui.MQtUtil.findLayout):
        try:
            ptr = finder(name)
            if ptr is not None:
                return ptr
        except Exception:
            pass
    return None


def _section_stack_size(omui, QtWidgets, wrapInstance):
    total_height = 0
    max_width = 0
    seen = False

    for frame in _SECTION_FRAMES:
        ptr = omui.MQtUtil.findLayout(frame)
        if ptr is None:
            ptr = omui.MQtUtil.findControl(frame)
        if ptr is None:
            continue

        widget = wrapInstance(int(ptr), QtWidgets.QWidget)
        if widget is None:
            continue

        widget.updateGeometry()
        hint = widget.sizeHint()
        minimum = widget.minimumSizeHint()
        if _frame_is_collapsed(frame):
            height = widget.height()
            if height <= 0:
                height = max(hint.height(), minimum.height())
        else:
            height = max(widget.height(), hint.height(), minimum.height())
        width = max(hint.width(), minimum.width())

        total_height += max(1, height)
        max_width = max(max_width, width)
        seen = True

    if not seen:
        return None

    row_spacing = 2
    total_height += max(0, len(_SECTION_FRAMES) - 1) * row_spacing
    return max_width, total_height


def _frame_is_collapsed(frame):
    try:
        return bool(cmds.frameLayout(frame, query=True, collapse=True))
    except Exception:
        return False


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
        command=_safe_button_command(label, command),
        **kwargs
    )
    _UI_BUTTONS.append(control)
    bg, _fg = _semantic_button_style(label, area["button"], area["accent"])
    _apply_bg(control, bg)
    _remember_button_style(control, area_key, label)
    return control


def _safe_button_command(label, command):
    def _wrapped(*args):
        _run_button_action(label, command, args)
    return _wrapped


def _run_button_action(label, command, args):
    global _BUTTON_ACTION_BUSY, _BUTTON_ACTION_LABEL
    global _BUTTON_ACTION_AUTO_KEY_STATE

    crash_logger.log_event(
        "button_pressed",
        action=label,
        window=WIN_ID,
        maya=crash_logger.maya_state(),
    )

    if _BUTTON_ACTION_BUSY:
        crash_logger.log_event(
            "button_ignored_busy",
            action=label,
            active_action=_BUTTON_ACTION_LABEL,
        )
        cmds.warning("Still finishing {0}; ignored {1}.".format(
            _BUTTON_ACTION_LABEL or "previous action",
            label,
        ))
        return

    _BUTTON_ACTION_BUSY = True
    _BUTTON_ACTION_LABEL = label
    _BUTTON_ACTION_AUTO_KEY_STATE = _set_auto_key_state(False)
    crash_logger.log_event(
        "button_auto_key_disabled",
        action=label,
        window=WIN_ID,
        previous_state=bool(_BUTTON_ACTION_AUTO_KEY_STATE),
    )
    _set_all_buttons_enabled(False)

    def _run():
        crash_logger.log_event(
            "button_start",
            action=label,
            window=WIN_ID,
            maya=crash_logger.maya_state(),
        )
        try:
            command(*args)
            crash_logger.log_event(
                "button_return",
                action=label,
                window=WIN_ID,
                maya=crash_logger.maya_state(),
            )
        except Exception as exc:
            crash_logger.log_exception(
                "button_exception",
                action=label,
                exc=exc,
            )
            cmds.warning(str(exc))
        finally:
            _release_button_action_deferred(label)

    _execute_deferred(_run)


def _release_button_action_deferred(label, idle_steps=None):
    if idle_steps is None:
        idle_steps = _BUTTON_RELEASE_IDLE_STEPS
    if idle_steps <= 0:
        _release_button_action(label)
        return
    _execute_deferred(
        lambda: _release_button_action_deferred(label, idle_steps - 1)
    )


def _release_button_action(label):
    global _BUTTON_ACTION_BUSY, _BUTTON_ACTION_LABEL
    global _BUTTON_ACTION_AUTO_KEY_STATE

    if _BUTTON_ACTION_LABEL != label:
        return

    crash_logger.log_event(
        "button_release",
        action=label,
        window=WIN_ID,
        maya=crash_logger.maya_state(),
    )
    if _BUTTON_ACTION_AUTO_KEY_STATE is not None:
        _set_auto_key_state(_BUTTON_ACTION_AUTO_KEY_STATE)
        crash_logger.log_event(
            "button_auto_key_restored",
            action=label,
            window=WIN_ID,
            restored_state=bool(_BUTTON_ACTION_AUTO_KEY_STATE),
        )
    _BUTTON_ACTION_BUSY = False
    _BUTTON_ACTION_LABEL = None
    _BUTTON_ACTION_AUTO_KEY_STATE = None
    _set_all_buttons_enabled(True)


def _set_all_buttons_enabled(enabled):
    for control in list(_UI_BUTTONS):
        if control and cmds.control(control, exists=True):
            try:
                cmds.button(control, edit=True, enable=bool(enabled))
            except Exception:
                pass


def _set_auto_key_state(enabled):
    try:
        previous = bool(cmds.autoKeyframe(query=True, state=True))
    except Exception:
        previous = False
    try:
        cmds.autoKeyframe(state=bool(enabled))
    except Exception:
        pass
    return previous


def _execute_deferred(callback):
    try:
        import maya.utils as maya_utils
        maya_utils.executeDeferred(callback)
    except Exception:
        callback()


def _button_row(parent, area_key, buttons):
    row = cmds.rowLayout(
        parent=parent,
        numberOfColumns=len(buttons),
        adjustableColumn=1,
        columnAttach=[(index + 1, "both", 0)
                      for index in range(len(buttons))],
        columnWidth=[(index + 1, 156) for index in range(len(buttons))],
    )
    _apply_bg(row, AREAS[area_key]["panel"])
    for label, command in buttons:
        _button(row, label, command, area_key)
    return row


def _section(parent, label, area_key):
    area = AREAS[area_key]
    frame = cmds.frameLayout(
        parent=parent,
        label=label,
        collapsable=True,
        collapse=True,
        collapseCommand=lambda *a: _fit_window_to_children_deferred(),
        expandCommand=lambda *a: _fit_window_to_children_deferred(),
        marginWidth=6,
        marginHeight=4,
    )
    _apply_bg(frame, area["header"])
    _remember_style(frame, fg=area["accent"], bg=area["header"],
                    padding="2px 6px")
    _SECTION_FRAMES.append(frame)

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
    global _BUTTON_ACTION_BUSY, _BUTTON_ACTION_LABEL
    global _BUTTON_ACTION_AUTO_KEY_STATE

    win_id = WIN_ID
    _QT_STYLES.clear()
    del _SECTION_FRAMES[:]
    del _UI_BUTTONS[:]
    _BUTTON_ACTION_BUSY = False
    _BUTTON_ACTION_LABEL = None
    _BUTTON_ACTION_AUTO_KEY_STATE = None
    crash_logger.log_event(
        "window_show",
        action="Scene Tools",
        window=WIN_ID,
    )
    logic.ensure_display_affected()

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)
    try:
        if cmds.windowPref(win_id, exists=True):
            cmds.windowPref(win_id, remove=True)
    except Exception:
        pass

    cmds.window(
        win_id,
        title="Scene Tools",
        widthHeight=(COMPACT_WIDTH, 1),
        resizeToFitChildren=True,
        sizeable=True,
    )

    main = cmds.columnLayout(
        MAIN_ID,
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
        columnWidth2=(220, 92),
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

    poly = _section(main, "Edit Polygon", "poly")
    _button(
        poly,
        "Clean Poly Mesh",
        logic.clean_poly_mesh_display,
        "poly",
    )
    _button(
        poly,
        "Clean Vertex Colors",
        logic.clean_vertex_color_sets,
        "poly",
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
    rotate_uv_row = cmds.rowLayout(
        parent=uv,
        numberOfColumns=3,
        adjustableColumn=3,
        columnWidth3=(92, 64, 156),
        columnAttach3=("both", "both", "both"),
    )
    _apply_bg(rotate_uv_row, AREAS["uv"]["panel"])
    rotate_uv_label = cmds.text(
        parent=rotate_uv_row,
        label="CW Degrees",
        align="left",
    )
    _remember_style(
        rotate_uv_label,
        fg=AREAS["uv"]["accent"],
        padding="1px 2px",
    )
    _field(cmds.floatField(
        "rotateUvDegreesField",
        parent=rotate_uv_row,
        value=90.0,
        precision=3,
    ), "uv")
    _button(
        rotate_uv_row,
        "Rotate Selected UVs",
        logic.rotate_selected_uvs_from_ui,
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
        columnWidth4=(86, 54, 54, 54),
        value1=1.0,
        value2=1.0,
        value3=1.0,
    ), "fit")

    fit_row = cmds.rowLayout(
        parent=fit,
        numberOfColumns=2,
        adjustableColumn=1,
        columnWidth2=(206, 106),
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

    chain = _section(main, "Chain Creator", "chain")
    _field(cmds.optionMenu(
        "chainActiveMenu",
        parent=chain,
        label="Chain",
        changeCommand=logic.select_chain_from_ui,
    ), "chain")
    _label(chain, "Link Mesh + Curve", "chain")
    _field(cmds.intSliderGrp(
        "chainLinkCountField",
        parent=chain,
        label="Links",
        field=True,
        minValue=3,
        maxValue=120,
        fieldMinValue=3,
        fieldMaxValue=240,
        value=16,
        columnWidth3=(76, 48, 168),
        dragCommand=logic.update_chain_count_from_ui,
        changeCommand=logic.update_chain_count_from_ui,
    ), "chain")
    _field(cmds.floatSliderGrp(
        "chainAlternateRollField",
        parent=chain,
        label="Alt Roll",
        field=True,
        minValue=0.0,
        maxValue=360.0,
        fieldMinValue=0.0,
        fieldMaxValue=360.0,
        value=90.0,
        columnWidth3=(76, 58, 158),
        dragCommand=logic.update_chain_roll_from_ui,
        changeCommand=logic.update_chain_roll_from_ui,
    ), "chain")
    _field(cmds.floatSliderGrp(
        "chainLinkScaleField",
        parent=chain,
        label="Link Scale",
        field=True,
        minValue=0.25,
        maxValue=4.0,
        fieldMinValue=0.01,
        fieldMaxValue=20.0,
        value=2.0,
        columnWidth3=(76, 58, 158),
        dragCommand=logic.update_chain_scale_from_ui,
        changeCommand=logic.update_chain_scale_from_ui,
    ), "chain")
    _button_row(chain, "chain", [
        ("Generate Chain", logic.create_chain_from_ui),
        ("Delete Active Chain", logic.delete_active_chain_from_ui),
    ])

    layout = _section(main, "Layout And Instancing", "layout")
    grid_row = cmds.rowLayout(
        parent=layout,
        numberOfColumns=2,
        adjustableColumn=2,
        columnWidth2=(86, 226),
        columnAttach2=("both", "both"),
    )
    grid_label = cmds.text(parent=grid_row, label="Grid Spacing", align="left")
    _remember_style(grid_label, fg=AREAS["layout"]["accent"],
                    padding="1px 2px")
    _field(cmds.floatField("gridSpacingField", parent=grid_row, value=5.0),
           "layout")
    _button_row(layout, "layout", [
        ("Grid Place Selected", logic.grid_place_selected),
        ("Create Spiral Curve", logic.open_spiral_window),
    ])

    _title(layout, "Circular Instancing", "layout")
    instance_row = cmds.rowColumnLayout(
        parent=layout,
        numberOfColumns=4,
        columnWidth=[(1, 50), (2, 86), (3, 54), (4, 92)],
        columnSpacing=[(1, 4), (2, 6), (3, 4), (4, 4)],
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

    _button_row(layout, "layout", [
        ("Instances", logic.on_create_instances),
        ("Copies", logic.on_create_copies),
    ])
    _button(layout, "Delete", logic.delete_instances, "layout")

    logic.refresh_chain_menu_from_ui()
    cmds.showWindow(win_id)
    _finish_qt_styles_deferred(win_id)
