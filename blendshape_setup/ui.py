"""Maya UI for the multi-object blendshape setup tool."""

import maya.cmds as cmds

import ui_word_weighting
from . import logic


WINDOW_NAME = "blendshapeSetupWin"
WINDOW_TITLE = "Blendshape Setup"
DEFAULT_WIDTH = 300
MIN_WIDTH = 260

THEME = {
    "window": (0.14, 0.15, 0.16),
    "panel": (0.19, 0.20, 0.22),
    "header": (0.23, 0.30, 0.37),
    "input": (0.24, 0.25, 0.27),
    "create": (0.35, 0.53, 0.34),
    "target": (0.30, 0.44, 0.58),
    "edit": (0.48, 0.40, 0.28),
    "danger": (0.57, 0.29, 0.27),
    "neutral": (0.34, 0.36, 0.39),
}

TOOLTIPS = {
    "header": "Creates one synchronized blendShape target set across multiple selected polygon meshes.",
    "subtitle": "Each target becomes an editable modelling pose and a keyed time-slider state.",
    "generate_section": "Set up the generated blendShape target names, timing, and editor behavior.",
    "targets_section": "Buttons for the generated targets. Each button activates one target for editing.",
    "actions_section": "Utility actions for finding, resetting, or leaving the generated edit setup.",
    "selection": "Shows how many selected transform nodes contain polygon mesh shapes.",
    "refresh": "Recount the currently selected polygon mesh transforms.",
    "prefix": "Fallback prefix used for empty target names or extra targets beyond the default list.",
    "count": "Number of blendShape targets to create. Changing this rebuilds the name fields.",
    "start": "Frame where every generated blendShape target is keyed to 0.",
    "interval": "Frame distance between active target keys. Target 1 is start plus this interval.",
    "target_names": "Names for the blendShape weight aliases and final target buttons. Invalid Maya characters are cleaned on generate.",
    "open_editor": "When enabled, opening or clicking a target also opens Maya's Blend Shape or Shape Editor.",
    "generate": "Generate the setup only when no managed setup exists in the scene.",
    "remove": "Delete all blendShape nodes created by this tool and return to a clean setup state.",
    "discover": "Scan the scene for blendShape setups created by this tool and rebuild the target button list.",
    "all_off": "Set all generated target weights to 0, jump to the start frame, and select the managed meshes.",
    "stop_edit": "Leave blendShape sculpt/edit mode without deleting the generated setup.",
    "status": "Reports the latest Blendshape Setup action, warning, or selection state.",
    "empty_targets": "No managed blendShape setup has been generated or discovered yet.",
}

_ui = {}
_records = []


def show():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    _ui.clear()

    cmds.window(
        WINDOW_NAME,
        title=WINDOW_TITLE,
        widthHeight=(DEFAULT_WIDTH, 620),
        sizeable=True,
    )

    scroll = cmds.scrollLayout(
        childResizable=True,
        verticalScrollBarThickness=12,
        horizontalScrollBarThickness=0,
    )
    _ui["scroll"] = scroll
    _apply_bg(scroll, THEME["window"])

    main = cmds.columnLayout(
        parent=scroll,
        adjustableColumn=True,
        rowSpacing=5,
        columnAttach=("both", 5),
    )
    _apply_bg(main, THEME["window"])

    header = cmds.columnLayout(
        parent=main,
        adjustableColumn=True,
        rowSpacing=3,
    )
    _apply_bg(header, THEME["header"])
    _title(
        header,
        "Blendshape Setup",
        THEME["header"],
        tooltip=TOOLTIPS["header"],
    )
    subtitle = cmds.text(
        parent=header,
        label="Multi-object WYSIWYG blendshape modelling",
        align="center",
        height=22,
    )
    _annotate(subtitle, TOOLTIPS["subtitle"])

    setup = _section(
        main,
        "Generate",
        (0.20, 0.27, 0.31),
        tooltip=TOOLTIPS["generate_section"],
    )
    _ui["selection"] = cmds.text(
        parent=setup,
        label="Selected polygon meshes: 0",
        align="left",
        height=20,
    )
    _annotate(_ui["selection"], TOOLTIPS["selection"])
    _button(
        setup,
        "Refresh Selection Count",
        _refresh_selection,
        THEME["neutral"],
        tooltip=TOOLTIPS["refresh"],
    )

    _field_row(
        setup,
        "Target Prefix",
        "prefix",
        field_type="text",
        value=logic.DEFAULT_PREFIX,
        tooltip=TOOLTIPS["prefix"],
    )
    _field_row(
        setup,
        "Target Count",
        "target_count",
        field_type="int",
        value=logic.DEFAULT_TARGET_COUNT,
        change_command=_sync_target_name_fields,
        tooltip=TOOLTIPS["count"],
    )
    _field_row(
        setup,
        "Start Frame",
        "start_frame",
        field_type="int",
        value=logic.DEFAULT_START_FRAME,
        tooltip=TOOLTIPS["start"],
    )
    _field_row(
        setup,
        "Frame Interval",
        "interval",
        field_type="int",
        value=logic.DEFAULT_INTERVAL,
        tooltip=TOOLTIPS["interval"],
    )

    target_names_label = cmds.text(
        parent=setup,
        label="Target Names",
        align="left",
        height=20,
    )
    _annotate(target_names_label, TOOLTIPS["target_names"])
    _ui["target_name_col"] = cmds.columnLayout(
        parent=setup,
        adjustableColumn=True,
        rowSpacing=3,
    )
    _apply_bg(_ui["target_name_col"], THEME["panel"])
    _ui["target_name_fields"] = []
    _sync_target_name_fields()

    _ui["open_editor"] = cmds.checkBox(
        parent=setup,
        label="Open Blend Shape Editor on target buttons",
        value=True,
    )
    _annotate(_ui["open_editor"], TOOLTIPS["open_editor"])

    _ui["generate_toggle"] = _button(
        setup,
        "Generate Blend Shapes",
        _generate_or_remove,
        THEME["create"],
        height=32,
        tooltip=TOOLTIPS["generate"],
    )

    targets = _section(
        main,
        "Generated Targets",
        (0.21, 0.24, 0.32),
        tooltip=TOOLTIPS["targets_section"],
    )
    _ui["target_col"] = cmds.columnLayout(
        parent=targets,
        adjustableColumn=True,
        rowSpacing=5,
    )
    _apply_bg(_ui["target_col"], THEME["panel"])

    actions = _section(
        main,
        "Actions",
        (0.25, 0.23, 0.27),
        tooltip=TOOLTIPS["actions_section"],
    )
    action_row = cmds.rowLayout(
        parent=actions,
        numberOfColumns=2,
        adjustableColumn=1,
        columnWidth2=(126, 126),
        columnAttach2=("both", "both"),
    )
    _button(action_row, "Discover Setup", _discover,
            THEME["neutral"], tooltip=TOOLTIPS["discover"])
    _button(action_row, "All Targets Off", _activate_all_off,
            THEME["neutral"], tooltip=TOOLTIPS["all_off"])

    _button(actions, "Stop Edit Mode", _stop_edit_mode,
            THEME["danger"], tooltip=TOOLTIPS["stop_edit"])

    _ui["status"] = cmds.text(
        parent=main,
        label="Select polygon meshes, choose a target count, then generate.",
        align="left",
        wordWrap=True,
        height=44,
    )
    _annotate(_ui["status"], TOOLTIPS["status"])

    _refresh_selection()
    _discover(update_status=False)
    _update_generate_toggle()

    cmds.showWindow(WINDOW_NAME)
    _finish_deferred()


def _generate_or_remove(*_):
    global _records

    existing = logic.discover_setups()
    if existing:
        _records = existing
        _remove_setup()
        return

    _generate()


def _generate(*_):
    global _records

    try:
        _sync_target_name_fields()
        _records = logic.generate_setup(
            target_count=cmds.intField(_ui["target_count"], query=True, value=True),
            name_prefix=cmds.textField(_ui["prefix"], query=True, text=True),
            target_names=_target_name_values(),
            start_frame=cmds.intField(_ui["start_frame"], query=True, value=True),
            interval=cmds.intField(_ui["interval"], query=True, value=True),
            replace_existing=False,
            open_editor=cmds.checkBox(
                _ui["open_editor"],
                query=True,
                value=True,
            ),
        )
    except Exception as exc:
        _set_status(str(exc), warning=True)
        cmds.warning(str(exc))
        return

    _rebuild_target_buttons()
    _refresh_selection()
    _set_status(
        "Generated {0} target(s) on {1} mesh(es).".format(
            len(_records[0]["targets"]) if _records else 0,
            len(_records),
        )
    )
    _update_generate_toggle()
    _finish_deferred()


def _discover(*_, update_status=True):
    global _records
    _records = logic.discover_setups()
    _rebuild_target_buttons()
    _update_generate_toggle()
    if update_status:
        if _records:
            _set_status("Discovered {0} managed blendShape node(s).".format(
                len(_records)))
        else:
            _set_status("No managed blendshape setup found in the scene.")
        _finish_deferred()


def _activate(index):
    try:
        frame = logic.activate_target(
            index,
            records=_records,
            open_editor=cmds.checkBox(
                _ui["open_editor"],
                query=True,
                value=True,
            ),
        )
    except Exception as exc:
        _set_status(str(exc), warning=True)
        cmds.warning(str(exc))
        return

    target_name = _records[0]["targets"][index]
    _set_status("Editing {0} at frame {1}.".format(target_name, frame))


def _activate_all_off(*_):
    try:
        frame = logic.activate_all_off(records=_records)
    except Exception as exc:
        _set_status(str(exc), warning=True)
        cmds.warning(str(exc))
        return
    _set_status("All targets off at frame {0}.".format(frame))


def _stop_edit_mode(*_):
    logic.disable_edit_mode(records=_records)
    _set_status("Blendshape edit mode disabled.")


def _remove_setup(*_):
    global _records

    try:
        removed_count = logic.remove_setup(records=_records)
    except Exception as exc:
        _set_status(str(exc), warning=True)
        cmds.warning(str(exc))
        return

    _records = []
    _rebuild_target_buttons()
    _update_generate_toggle()
    _set_status("Removed {0} generated blendShape setup node(s).".format(
        removed_count))
    _finish_deferred()


def _update_generate_toggle():
    button = _ui.get("generate_toggle")
    if not button or not cmds.control(button, exists=True):
        return

    has_setup = bool(logic.discover_setups())
    if has_setup:
        cmds.button(button, edit=True, label="Remove Generated Setup")
        _apply_bg(button, THEME["danger"])
        _annotate(button, TOOLTIPS["remove"])
    else:
        cmds.button(button, edit=True, label="Generate Blend Shapes")
        _apply_bg(button, THEME["create"])
        _annotate(button, TOOLTIPS["generate"])


def _refresh_selection(*_):
    count = len(logic.selected_mesh_transforms())
    if "selection" in _ui and cmds.control(_ui["selection"], exists=True):
        cmds.text(
            _ui["selection"],
            edit=True,
            label="Selected polygon meshes: {0}".format(count),
        )


def _rebuild_target_buttons():
    target_col = _ui.get("target_col")
    if not target_col or not cmds.layout(target_col, exists=True):
        return

    children = cmds.columnLayout(
        target_col,
        query=True,
        childArray=True,
    ) or []
    for child in children:
        cmds.deleteUI(child)

    if not _records:
        empty = cmds.text(
            parent=target_col,
            label="No generated targets yet.",
            align="left",
            height=24,
        )
        _annotate(empty, TOOLTIPS["empty_targets"])
        return

    first = _records[0]
    targets = first["targets"]

    for index, target_name in enumerate(targets):
        _button(
            target_col,
            target_name,
            lambda *_args, i=index: _activate(i),
            THEME["target"],
            height=32,
            tooltip=(
                "Activate {0}: jump to its keyed frame, set only this "
                "target to 1, and enter blendShape edit mode."
            ).format(target_name),
        )


def _sync_target_name_fields(*_):
    name_col = _ui.get("target_name_col")
    if not name_col or not cmds.layout(name_col, exists=True):
        return

    existing_names = _target_name_values()
    target_count = max(
        1,
        cmds.intField(_ui["target_count"], query=True, value=True),
    )
    prefix = cmds.textField(_ui["prefix"], query=True, text=True)
    defaults = logic.build_target_names(
        target_count=target_count,
        name_prefix=prefix,
        target_names=existing_names,
    )

    children = cmds.columnLayout(name_col, query=True, childArray=True) or []
    for child in children:
        cmds.deleteUI(child)

    fields = []
    for index in range(target_count):
        row = cmds.rowLayout(
            parent=name_col,
            numberOfColumns=2,
            adjustableColumn=2,
            columnWidth2=(24, 220),
            columnAttach2=("both", "both"),
        )
        index_label = cmds.text(parent=row, label=str(index + 1), align="left")
        _annotate(index_label, "Target name slot {0}.".format(index + 1))
        field = cmds.textField(parent=row, text=defaults[index])
        _annotate(
            field,
            (
                "Name for target {0}. This becomes the blendShape alias and "
                "the generated edit button label."
            ).format(index + 1),
        )
        _apply_bg(field, THEME["input"])
        fields.append(field)

    _ui["target_name_fields"] = fields


def _target_name_values():
    values = []
    for field in _ui.get("target_name_fields", []):
        if cmds.control(field, exists=True):
            values.append(cmds.textField(field, query=True, text=True))
    return values


def _field_row(parent, label, key, field_type="int", value=0,
               change_command=None, tooltip=""):
    row = cmds.rowLayout(
        parent=parent,
        numberOfColumns=2,
        adjustableColumn=2,
        columnWidth2=(92, 160),
        columnAttach2=("both", "both"),
    )
    label_control = cmds.text(parent=row, label=label, align="left")
    _annotate(label_control, tooltip)

    kwargs = {}
    if change_command:
        kwargs["changeCommand"] = change_command

    if field_type == "text":
        control = cmds.textField(parent=row, text=value, **kwargs)
    else:
        control = cmds.intField(parent=row, value=int(value), **kwargs)
    _apply_bg(control, THEME["input"])
    _annotate(control, tooltip)
    _ui[key] = control
    return control


def _section(parent, label, color, tooltip=""):
    frame = cmds.frameLayout(
        parent=parent,
        label=label,
        collapsable=True,
        collapse=False,
        marginWidth=5,
        marginHeight=5,
        borderStyle="etchedIn",
    )
    _apply_bg(frame, color)
    _annotate(frame, tooltip)
    body = cmds.columnLayout(
        parent=frame,
        adjustableColumn=True,
        rowSpacing=4,
    )
    _apply_bg(body, THEME["panel"])
    _annotate(body, tooltip)
    return body


def _title(parent, label, color, tooltip=""):
    control = cmds.text(
        parent=parent,
        label=label,
        align="center",
        height=24,
        font="boldLabelFont",
    )
    _apply_bg(control, color)
    _annotate(control, tooltip)
    return control


def _button(parent, label, command, color, height=24, tooltip=""):
    control = cmds.button(
        parent=parent,
        label=label,
        height=height,
        command=command,
    )
    _apply_bg(control, color)
    _annotate(control, tooltip)
    return control


def _apply_bg(control, color):
    for command in (cmds.control, cmds.layout):
        try:
            command(control, edit=True, backgroundColor=color)
            return
        except Exception:
            pass


def _annotate(control, tooltip):
    if not control or not tooltip:
        return

    for command in (cmds.control, cmds.layout):
        try:
            command(control, edit=True, annotation=tooltip)
            return
        except Exception:
            pass


def _finish_deferred():
    def _finish():
        _set_window_min_width()
        _disable_horizontal_scroll()
        ui_word_weighting.apply_to_window(WINDOW_NAME)

    try:
        import maya.utils as maya_utils
        maya_utils.executeDeferred(_finish)
    except Exception:
        _finish()


def _set_window_min_width():
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

    ptr = omui.MQtUtil.findWindow(WINDOW_NAME)
    if ptr is None:
        return

    widget = wrapInstance(int(ptr), QtWidgets.QWidget)
    widget.setMinimumWidth(MIN_WIDTH)


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

    scroll = _ui.get("scroll")
    if not scroll or not cmds.scrollLayout(scroll, exists=True):
        return

    ptr = omui.MQtUtil.findLayout(scroll)
    if ptr is None:
        return

    widget = wrapInstance(int(ptr), QtWidgets.QWidget)
    scroll_area = widget if isinstance(widget, QtWidgets.QScrollArea) else None
    if scroll_area is None:
        scroll_area = widget.findChild(QtWidgets.QScrollArea)
    if scroll_area is not None:
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)


def _set_status(message, warning=False):
    if "status" not in _ui or not cmds.control(_ui["status"], exists=True):
        return

    cmds.text(_ui["status"], edit=True, label=message)
    _apply_bg(_ui["status"], THEME["danger"] if warning else THEME["panel"])
