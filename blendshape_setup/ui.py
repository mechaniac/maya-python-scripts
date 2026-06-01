"""Maya UI for the multi-object blendshape setup tool."""

import maya.cmds as cmds

import ui_word_weighting
from . import logic


_LEGACY_WRAP_DISPLAY_GUARD_JOBS = list(
    globals().get("_wrap_display_guard_jobs", []) or []
)
for _legacy_name in (
    "wrap_display_time_guard",
    "_install_wrap_display_guard_jobs",
):
    globals().pop(_legacy_name, None)

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
    "generate_section": "Set up generated blendShape names, timing, transform keys, and editor behavior.",
    "targets_section": "Buttons for BindPose and generated targets. Each button activates one keyed time-slider state.",
    "actions_section": "Utility actions for finding, resetting, or leaving the generated edit setup.",
    "wire_tests_section": "Isolated viewport display tests for selected polygon meshes. Use these on wrap drivers like wrapSkull or wrapJaw to find the method Maya respects in this scene.",
    "selection": "Shows how many selected or descendant transform nodes contain polygon mesh shapes.",
    "refresh": "Recount the currently selected polygon mesh transforms, including meshes under selected groups.",
    "template": "Create a BlendshapeRoster group with Meshes, WRAPExample, and WRAPExample/WRAPTarget folders.",
    "prefix": "Fallback prefix used for empty target names or extra targets beyond the default list.",
    "count": "Number of blendShape targets to create. Changing this rebuilds the name fields.",
    "start": "Frame where every generated blendShape target is keyed to 0.",
    "interval": "Frame distance between active target keys. Target 1 is start plus this interval.",
    "wrap_distance": "Maximum wrap influence distance in scene units. Vertices farther away from the wrap driver receive 0 wrap weight; 0 disables the distance limit.",
    "target_names": "Names for the blendShape weight aliases and final target buttons. Invalid Maya characters are cleaned on generate.",
    "open_editor": "When enabled, Generate opens Maya's Blend Shape or Shape Editor once. Target buttons keep it hidden.",
    "generate": "Generate blendShapes for meshes, transform keys for selected/descendant transforms plus mesh parent groups, and managed wraps from WRAP*/WRAPTarget groups.",
    "remove": "Delete all blendShape, wrap, and helper nodes created by this tool and return to a clean setup state.",
    "discover": "Scan the scene for blendShape setups created by this tool and rebuild the target button list.",
    "all_off": "Set all generated target weights to 0, jump to the start frame, and keep the current selection.",
    "bind_pose": "Jump to the setup start frame and set every generated blendShape target to 0.",
    "stop_edit": "Leave blendShape sculpt/edit mode without deleting the generated setup.",
    "wire_reset": "Reset the display-only wire test edits on selected meshes and remove curve wire proxies created by this tool.",
    "status": "Reports the latest Blendshape Setup action, warning, or selection state.",
    "empty_targets": "No managed blendShape setup has been generated or discovered yet.",
}

AUTO_KEY_WARNING = (
    "Auto Key is disabled. Transform edits on target frames will not be "
    "recorded automatically."
)

_ui = {}
_records = []
_active_wire_test = None
_active_target_index = None
_BIND_POSE_INDEX = -1


def show(move_to_primary=False):
    global _active_wire_test, _active_target_index

    _kill_legacy_wrap_display_jobs()
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)
    _kill_legacy_wrap_display_jobs()

    _ui.clear()
    _active_wire_test = None
    _active_target_index = _BIND_POSE_INDEX

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
        rowSpacing=0,
    )
    _apply_bg(header, THEME["header"])
    subtitle = cmds.text(
        parent=header,
        label="// multi-object blendshape modelling",
        align="left",
        height=16,
        font="smallObliqueLabelFont",
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
    template_row = cmds.rowLayout(
        parent=setup,
        numberOfColumns=2,
        adjustableColumn=1,
        columnWidth2=(126, 126),
        columnAttach2=("both", "both"),
    )
    _button(template_row, "Refresh Count", _refresh_selection,
            THEME["neutral"], tooltip=TOOLTIPS["refresh"])
    _button(template_row, "Create Template", _create_template,
            THEME["neutral"], tooltip=TOOLTIPS["template"])

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
    _field_row(
        setup,
        "Wrap Distance",
        "wrap_max_distance",
        field_type="float",
        value=logic.DEFAULT_WRAP_MAX_DISTANCE,
        tooltip=TOOLTIPS["wrap_distance"],
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
        label="Open Blend Shape Editor after generate",
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

    wire_tests = _section(
        main,
        "Wire Display Tests",
        (0.20, 0.27, 0.24),
        tooltip=TOOLTIPS["wire_tests_section"],
    )
    _wire_test_buttons(wire_tests)

    _refresh_selection()
    _discover(update_status=False)
    _update_generate_toggle()
    _warn_auto_key_disabled()

    cmds.showWindow(WINDOW_NAME)
    if move_to_primary:
        _move_window_to_primary_screen_deferred()
    _finish_deferred()


def show_on_main_screen():
    if not cmds.window(WINDOW_NAME, exists=True):
        show(move_to_primary=True)
        return

    try:
        cmds.showWindow(WINDOW_NAME)
    except Exception:
        pass
    _move_window_to_primary_screen_deferred()


def _generate_or_remove(*_):
    global _records

    if logic.generated_setup_exists():
        _records = logic.discover_setups()
        _remove_setup()
        return

    _generate()


def _generate(*_):
    global _records, _active_target_index

    try:
        _sync_target_name_fields()
        _records = logic.generate_setup(
            target_count=cmds.intField(_ui["target_count"], query=True, value=True),
            name_prefix=cmds.textField(_ui["prefix"], query=True, text=True),
            target_names=_target_name_values(),
            start_frame=cmds.intField(_ui["start_frame"], query=True, value=True),
            interval=cmds.intField(_ui["interval"], query=True, value=True),
            wrap_max_distance=cmds.floatField(
                _ui["wrap_max_distance"],
                query=True,
                value=True,
            ),
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

    _active_target_index = _BIND_POSE_INDEX
    _rebuild_target_buttons()
    _refresh_selection()
    _set_status_with_auto_key(
        "Generated {0} target(s) on {1} mesh(es), {2} wrap(s), "
        "{3} helper(s), {4} transform-keyed node(s).".format(
            len(_records[0]["targets"]) if _records else 0,
            len(_records),
            len(logic.discover_wrap_setups()),
            len(logic.discover_helper_nodes()),
            len(logic.discover_transform_key_nodes()),
        )
    )
    _update_generate_toggle()
    _finish_deferred()


def _discover(*_, update_status=True):
    global _records, _active_target_index
    _records = logic.discover_setups()
    wrap_count = len(logic.discover_wrap_setups())
    helper_count = len(logic.discover_helper_nodes())
    transform_key_count = len(logic.discover_transform_key_nodes())
    _active_target_index = _target_index_from_current_time()
    _rebuild_target_buttons()
    _update_generate_toggle()
    if update_status:
        if _records or wrap_count or helper_count or transform_key_count:
            _set_status(
                "Discovered {0} blendShape node(s), {1} wrap node(s), "
                "{2} helper node(s), and transform keys on {3} node(s).".format(
                    len(_records),
                    wrap_count,
                    helper_count,
                    transform_key_count,
                )
            )
        else:
            _set_status("No managed blendshape setup found in the scene.")
        _finish_deferred()


def _activate(index):
    global _active_target_index

    try:
        frame = logic.activate_target(
            index,
            records=_records,
            open_editor=False,
        )
    except Exception as exc:
        _set_status(str(exc), warning=True)
        cmds.warning(str(exc))
        return

    _active_target_index = index
    _update_target_button_states()
    target_name = _records[0]["targets"][index]
    _set_status_with_auto_key(
        "Editing {0} at frame {1}.".format(target_name, frame)
    )
    logic.hide_blendshape_editor()


def _activate_all_off(*_):
    global _active_target_index

    try:
        frame = logic.activate_all_off(records=_records)
    except Exception as exc:
        _set_status(str(exc), warning=True)
        cmds.warning(str(exc))
        return
    _active_target_index = _BIND_POSE_INDEX
    _update_target_button_states()
    _set_status_with_auto_key("BindPose at frame {0}.".format(frame))


def _stop_edit_mode(*_):
    logic.disable_edit_mode(records=_records)
    _set_status("Blendshape edit mode disabled.")


def _run_wire_test(method_id):
    global _active_wire_test

    try:
        if _active_wire_test == method_id:
            message = logic.reset_wire_display_tests()
            _active_wire_test = None
            _update_wire_test_toggles()
            _set_status("{0} off. {1}".format(
                _wire_test_label(method_id),
                message,
            ))
            _finish_deferred()
            return

        if _active_wire_test:
            logic.reset_wire_display_tests()

        message = logic.apply_wire_display_test(method_id)
    except Exception as exc:
        _set_status(str(exc), warning=True)
        cmds.warning(str(exc))
        return

    _active_wire_test = method_id
    _update_wire_test_toggles()
    _set_status(message)
    _finish_deferred()


def _reset_wire_tests(*_):
    global _active_wire_test

    try:
        message = logic.reset_wire_display_tests()
    except Exception as exc:
        _set_status(str(exc), warning=True)
        cmds.warning(str(exc))
        return

    _active_wire_test = None
    _update_wire_test_toggles()
    _set_status(message)
    _finish_deferred()


def _remove_setup(*_):
    global _records, _active_target_index

    try:
        removed_count = logic.remove_setup(records=_records)
    except Exception as exc:
        _set_status(str(exc), warning=True)
        cmds.warning(str(exc))
        return

    _records = []
    _active_target_index = None
    _rebuild_target_buttons()
    _update_generate_toggle()
    _set_status(
        "Removed {0} blendShape node(s), {1} wrap node(s), "
        "{2} helper node(s), transform keys on {3} node(s), "
        "and {4} wrap influence attr(s).".format(
            removed_count.get("blendShapes", 0),
            removed_count.get("wraps", 0),
            removed_count.get("helpers", 0),
            removed_count.get("transformKeyedNodes", 0),
            removed_count.get("wrapInfluenceAttrs", 0),
        )
    )
    _finish_deferred()


def _create_template(*_):
    try:
        template = logic.create_template()
    except Exception as exc:
        _set_status(str(exc), warning=True)
        cmds.warning(str(exc))
        return

    _refresh_selection()
    _set_status(
        "Created template group: {0}. Put driver meshes in WRAPExample and "
        "affected meshes in WRAPTarget.".format(template["root"])
    )
    _finish_deferred()


def _update_generate_toggle():
    button = _ui.get("generate_toggle")
    if not button or not cmds.control(button, exists=True):
        return

    has_setup = logic.generated_setup_exists()
    if has_setup:
        cmds.button(button, edit=True, label="Remove Generated Setup")
        _apply_bg(button, THEME["danger"])
        _annotate(button, TOOLTIPS["remove"])
    else:
        cmds.button(button, edit=True, label="Generate Blend Shapes")
        _apply_bg(button, THEME["create"])
        _annotate(button, TOOLTIPS["generate"])


def _warn_auto_key_disabled():
    if logic.auto_key_enabled():
        return False

    cmds.warning(AUTO_KEY_WARNING)
    _set_status(AUTO_KEY_WARNING, warning=True)
    return True


def _set_status_with_auto_key(message):
    if logic.auto_key_enabled():
        _set_status(message)
        return

    cmds.warning(AUTO_KEY_WARNING)
    _set_status("{0} {1}".format(message, AUTO_KEY_WARNING), warning=True)


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

    _ui["target_buttons"] = {}
    _ui["bind_pose_button"] = None
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

    _ui["bind_pose_button"] = _button(
        target_col,
        "BindPose",
        _activate_all_off,
        THEME["target"],
        height=32,
        tooltip=TOOLTIPS["bind_pose"],
    )

    for index, target_name in enumerate(targets):
        button = _button(
            target_col,
            target_name,
            lambda *_args, i=index: _activate(i),
            THEME["target"],
            height=32,
            tooltip=(
                "Activate {0}: jump to its keyed frame, set only this "
                "target to 1, ensure transform keys, and enter blendShape "
                "edit mode while keeping the current selection."
            ).format(target_name),
        )
        _ui["target_buttons"][index] = button
    _update_target_button_states()


def _update_target_button_states():
    buttons = _ui.get("target_buttons", {})
    bind_button = _ui.get("bind_pose_button")
    if bind_button and cmds.control(bind_button, exists=True):
        if _active_target_index == _BIND_POSE_INDEX:
            cmds.button(bind_button, edit=True, label="[ON] BindPose")
            _apply_bg(bind_button, THEME["create"])
        else:
            cmds.button(bind_button, edit=True, label="BindPose")
            _apply_bg(bind_button, THEME["target"])

    if not buttons:
        return

    targets = _records[0]["targets"] if _records else []
    for index, button in buttons.items():
        if not cmds.control(button, exists=True):
            continue
        target_name = targets[index] if index < len(targets) else str(index + 1)
        if index == _active_target_index:
            cmds.button(button, edit=True, label="[ON] {0}".format(target_name))
            _apply_bg(button, THEME["create"])
        else:
            cmds.button(button, edit=True, label=target_name)
            _apply_bg(button, THEME["target"])


def _target_index_from_current_time():
    if not _records:
        return None
    first = _records[0]
    try:
        frame = int(round(cmds.currentTime(query=True)))
    except Exception:
        return None

    if frame == int(first.get("start_frame", logic.DEFAULT_START_FRAME)):
        return _BIND_POSE_INDEX

    for index in range(len(first.get("targets", []))):
        if frame == logic.target_frame(
            index,
            first.get("start_frame", logic.DEFAULT_START_FRAME),
            first.get("interval", logic.DEFAULT_INTERVAL),
        ):
            return index
    return None


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


def _wire_test_buttons(parent):
    _ui["wire_test_buttons"] = {}
    methods = list(logic.WIRE_TEST_METHODS)
    for row_start in range(0, len(methods), 2):
        row_methods = methods[row_start:row_start + 2]
        row_kwargs = {
            "parent": parent,
            "numberOfColumns": len(row_methods),
            "adjustableColumn": 1,
        }
        if len(row_methods) == 1:
            row_kwargs["columnAttach1"] = "both"
        else:
            row_kwargs["columnAttach2"] = ("both", "both")
            row_kwargs["columnWidth2"] = (126, 126)
        row = cmds.rowLayout(**row_kwargs)
        if len(row_methods) == 2:
            cmds.rowLayout(row, edit=True, columnWidth2=(126, 126))

        for method in row_methods:
            method_id = method["id"]
            button = _button(
                row,
                method["label"],
                lambda *_args, current=method_id: _run_wire_test(current),
                THEME["neutral"],
                tooltip=method["tooltip"],
            )
            _ui["wire_test_buttons"][method_id] = button

    _button(
        parent,
        "Reset Wire Tests",
        _reset_wire_tests,
        THEME["danger"],
        tooltip=TOOLTIPS["wire_reset"],
    )
    _update_wire_test_toggles()


def _update_wire_test_toggles():
    buttons = _ui.get("wire_test_buttons", {})
    if not buttons:
        return

    for method in logic.WIRE_TEST_METHODS:
        method_id = method["id"]
        button = buttons.get(method_id)
        if not button or not cmds.control(button, exists=True):
            continue

        if method_id == _active_wire_test:
            cmds.button(
                button,
                edit=True,
                label="[ON] {0}".format(method["label"]),
            )
            _apply_bg(button, THEME["create"])
        else:
            cmds.button(button, edit=True, label=method["label"])
            _apply_bg(button, THEME["neutral"])


def _wire_test_label(method_id):
    for method in logic.WIRE_TEST_METHODS:
        if method["id"] == method_id:
            return method["label"]
    return method_id


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
    elif field_type == "float":
        control = cmds.floatField(
            parent=row,
            value=float(value),
            precision=3,
            **kwargs
        )
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


def _move_window_to_primary_screen_deferred():
    try:
        import maya.utils as maya_utils
        maya_utils.executeDeferred(_move_window_to_primary_screen)
    except Exception:
        _move_window_to_primary_screen()


def _move_window_to_primary_screen():
    try:
        from maya import OpenMayaUI as omui
        try:
            from PySide6 import QtWidgets, QtGui
            from shiboken6 import wrapInstance
        except ImportError:
            from PySide2 import QtWidgets, QtGui
            from shiboken2 import wrapInstance
    except Exception:
        return _move_window_with_cmds_fallback()

    ptr = omui.MQtUtil.findWindow(WINDOW_NAME)
    if ptr is None:
        return _move_window_with_cmds_fallback()

    widget = wrapInstance(int(ptr), QtWidgets.QWidget)
    if widget is None:
        return _move_window_with_cmds_fallback()

    screen = None
    try:
        screen = QtGui.QGuiApplication.primaryScreen()
    except Exception:
        pass
    if screen is None:
        try:
            app = QtWidgets.QApplication.instance()
            screen = app.primaryScreen() if app else None
        except Exception:
            pass

    if screen is None:
        widget.move(80, 80)
    else:
        geometry = screen.availableGeometry()
        margin = 32
        width = max(widget.width(), DEFAULT_WIDTH)
        height = max(widget.height(), 420)
        max_width = max(DEFAULT_WIDTH, geometry.width() - (margin * 2))
        max_height = max(300, geometry.height() - (margin * 2))
        width = min(width, max_width)
        height = min(height, max_height)
        if widget.width() != width or widget.height() != height:
            widget.resize(width, height)

        x = geometry.x() + max(margin, int((geometry.width() - width) / 2))
        y = geometry.y() + max(margin, int((geometry.height() - height) / 2))
        widget.move(x, y)

    widget.show()
    widget.raise_()
    widget.activateWindow()
    return True


def _move_window_with_cmds_fallback():
    if not cmds.window(WINDOW_NAME, exists=True):
        return False
    try:
        cmds.window(WINDOW_NAME, edit=True, topLeftCorner=(80, 80))
        return True
    except Exception:
        return False


def _kill_legacy_wrap_display_jobs():
    job_ids = set()
    for job_id in _LEGACY_WRAP_DISPLAY_GUARD_JOBS:
        try:
            job_ids.add(int(job_id))
        except (TypeError, ValueError):
            pass

    tokens = (
        "wrap_display_time_guard",
        "guard_wrap_display_on_time_change",
        "apply_wrap_display_defaults",
        "_install_wrap_display_guard_jobs",
    )
    for job in cmds.scriptJob(listJobs=True) or []:
        if not any(token in job for token in tokens):
            continue
        try:
            job_ids.add(int(job.split(":", 1)[0].strip()))
        except (IndexError, TypeError, ValueError):
            pass

    killed = []
    for job_id in sorted(job_ids):
        try:
            if cmds.scriptJob(exists=job_id):
                cmds.scriptJob(kill=job_id, force=True)
                killed.append(job_id)
        except Exception:
            pass

    if killed:
        print("[BlendshapeSetup] killed legacy wrap display job(s): {0}".format(
            ", ".join(str(job_id) for job_id in killed)
        ))


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
