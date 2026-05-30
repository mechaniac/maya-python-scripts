"""Compact material browser panel for Maya.

The built-in Hypershade always shows Maya's default material nodes. This panel
keeps the common defaults out of view and can live directly inside a model
panel slot.
"""

import maya.cmds as cmds
import maya.mel as mel


PANEL_TYPE = "cHypershadePanelType"
PANEL_NAME = "cHypershadePanel"
PANEL_LABEL = "cHypershade"

_CREATE_CALLBACK = "cHypershadeCreateCallback"
_ADD_CALLBACK = "cHypershadeAddCallback"
_REMOVE_CALLBACK = "cHypershadeRemoveCallback"
_DELETE_CALLBACK = "cHypershadeDeleteCallback"
_SAVE_STATE_CALLBACK = "cHypershadeSaveStateCallback"

_DEFAULT_MATERIALS = {
    "openPBRSurface1",
    "standardSurface1",
    "lambert1",
    "particleCloud1",
    "shaderGlow1",
}

_PANEL_CONTROLS = {}


def open_panel(*args):
    """Open cHypershade in the active single panel or lower-right quad panel."""
    _ensure_panel_type()

    if cmds.scriptedPanel(PANEL_NAME, exists=True):
        if PANEL_NAME in (cmds.getPanel(visiblePanels=True) or []):
            refresh(PANEL_NAME)
            return PANEL_NAME
    else:
        cmds.scriptedPanel(
            PANEL_NAME,
            type=PANEL_TYPE,
            label=PANEL_LABEL,
            menuBarVisible=False,
        )

    target_panel = _target_model_panel()
    if not target_panel:
        cmds.warning("Could not find a visible model panel for cHypershade.")
        return PANEL_NAME

    cmds.scriptedPanel(PANEL_NAME, edit=True, replacePanel=target_panel)
    refresh(PANEL_NAME)
    print("Opened cHypershade in {0}.".format(target_panel))
    return PANEL_NAME


def _ensure_panel_type():
    mel.eval(
        """
        global proc cHypershadeCreateCallback(string $panelName) {
        }

        global proc cHypershadeAddCallback(string $panelName) {
            python("import tools_window.chypershade as _chs; _chs._add_panel_ui('" + $panelName + "')");
        }

        global proc cHypershadeRemoveCallback(string $panelName) {
            python("import tools_window.chypershade as _chs; _chs._remove_panel_ui('" + $panelName + "')");
        }

        global proc cHypershadeDeleteCallback(string $panelName) {
            python("import tools_window.chypershade as _chs; _chs._delete_panel_ui('" + $panelName + "')");
        }

        global proc string cHypershadeSaveStateCallback(string $panelName) {
            return "";
        }
        """
    )

    kwargs = dict(
        label=PANEL_LABEL,
        createCallback=_CREATE_CALLBACK,
        addCallback=_ADD_CALLBACK,
        removeCallback=_REMOVE_CALLBACK,
        deleteCallback=_DELETE_CALLBACK,
        saveStateCallback=_SAVE_STATE_CALLBACK,
        unique=True,
    )

    if cmds.scriptedPanelType(PANEL_TYPE, exists=True):
        cmds.scriptedPanelType(PANEL_TYPE, edit=True, **kwargs)
    else:
        cmds.scriptedPanelType(PANEL_TYPE, **kwargs)


def _target_model_panel():
    visible = cmds.getPanel(visiblePanels=True) or []
    model_panels = [
        panel for panel in visible
        if panel != PANEL_NAME and _panel_type(panel) == "modelPanel"
    ]

    if not model_panels:
        return None

    if len(model_panels) == 1:
        return model_panels[0]

    lower_right = _lower_right_panel(model_panels)
    if lower_right:
        return lower_right

    if "modelPanel4" in model_panels:
        return "modelPanel4"

    return model_panels[-1]


def _panel_type(panel):
    try:
        return cmds.getPanel(typeOf=panel)
    except Exception:
        return None


def _lower_right_panel(panels):
    positions = []
    for panel in panels:
        pos = _panel_screen_center(panel)
        if pos:
            positions.append((panel, pos))

    if not positions:
        return None

    return max(positions, key=lambda item: (item[1][1], item[1][0]))[0]


def _panel_screen_center(panel):
    control = _panel_control(panel)
    if not control:
        return None

    try:
        from maya import OpenMayaUI as omui

        try:
            from PySide6 import QtWidgets
            from shiboken6 import wrapInstance
        except ImportError:
            from PySide2 import QtWidgets
            from shiboken2 import wrapInstance

        ptr = omui.MQtUtil.findControl(control)
        if ptr is None:
            ptr = omui.MQtUtil.findLayout(control)
        if ptr is None:
            return None

        widget = wrapInstance(int(ptr), QtWidgets.QWidget)
        center = widget.mapToGlobal(widget.rect().center())
        return center.x(), center.y()
    except Exception:
        return None


def _panel_control(panel):
    try:
        return cmds.panel(panel, query=True, control=True)
    except Exception:
        return None


def _ui_exists(name):
    for command in (cmds.control, cmds.layout):
        try:
            if command(name, exists=True):
                return True
        except Exception:
            pass
    return False


def _add_panel_ui(panel_name):
    parent = cmds.setParent(query=True)
    controls = _controls(panel_name)

    if _ui_exists(controls["root"]):
        cmds.deleteUI(controls["root"])

    root = cmds.formLayout(controls["root"], parent=parent)

    toolbar = cmds.rowLayout(
        controls["toolbar"],
        parent=root,
        numberOfColumns=4,
        adjustableColumn=1,
        columnWidth4=(160, 74, 74, 96),
        columnAttach4=("both", "both", "both", "both"),
    )
    cmds.textField(
        controls["filter"],
        parent=toolbar,
        placeholderText="Filter materials...",
        changeCommand=lambda *a: refresh(panel_name),
        enterCommand=lambda *a: refresh(panel_name),
    )
    cmds.button(
        controls["refresh"],
        parent=toolbar,
        label="Refresh",
        command=lambda *a: refresh(panel_name),
    )
    cmds.button(
        controls["select"],
        parent=toolbar,
        label="Select",
        command=lambda *a: select_material(panel_name),
    )
    cmds.button(
        controls["assign"],
        parent=toolbar,
        label="Assign",
        command=lambda *a: assign_to_selection(panel_name),
    )

    material_list = cmds.textScrollList(
        controls["list"],
        parent=root,
        allowMultiSelection=False,
        selectCommand=lambda *a: update_info(panel_name),
        doubleClickCommand=lambda *a: select_material(panel_name),
    )

    action_row = cmds.rowLayout(
        controls["actions"],
        parent=root,
        numberOfColumns=2,
        adjustableColumn=1,
        columnWidth2=(150, 150),
        columnAttach2=("both", "both"),
    )
    cmds.button(
        controls["select_objects"],
        parent=action_row,
        label="Select Assigned Objects",
        command=lambda *a: select_assigned_objects(panel_name),
    )
    cmds.button(
        controls["open_hypershade"],
        parent=action_row,
        label="Full Hypershade",
        command=lambda *a: mel.eval("HypershadeWindow;"),
    )

    info = cmds.text(
        controls["info"],
        parent=root,
        label="",
        align="left",
        height=44,
    )

    cmds.formLayout(
        root,
        edit=True,
        attachForm=[
            (toolbar, "top", 6),
            (toolbar, "left", 6),
            (toolbar, "right", 6),
            (material_list, "left", 6),
            (material_list, "right", 6),
            (info, "left", 6),
            (info, "right", 6),
            (info, "bottom", 6),
            (action_row, "left", 6),
            (action_row, "right", 6),
        ],
        attachControl=[
            (material_list, "top", 6, toolbar),
            (material_list, "bottom", 6, action_row),
            (action_row, "bottom", 6, info),
        ],
    )

    refresh(panel_name)


def _remove_panel_ui(panel_name):
    controls = _PANEL_CONTROLS.get(panel_name)
    if controls and _ui_exists(controls["root"]):
        cmds.deleteUI(controls["root"])


def _delete_panel_ui(panel_name):
    _remove_panel_ui(panel_name)
    _PANEL_CONTROLS.pop(panel_name, None)


def refresh(panel_name=PANEL_NAME):
    controls = _controls(panel_name)
    list_control = controls["list"]

    if not _ui_exists(list_control):
        return

    previous = _selected_material(panel_name)
    materials = _filtered_materials(panel_name)

    cmds.textScrollList(list_control, edit=True, removeAll=True)
    if materials:
        cmds.textScrollList(list_control, edit=True, append=materials)

    if previous in materials:
        cmds.textScrollList(list_control, edit=True, selectItem=previous)
    elif materials:
        cmds.textScrollList(list_control, edit=True, selectIndexedItem=1)

    update_info(panel_name)


def update_info(panel_name=PANEL_NAME):
    controls = _controls(panel_name)
    info_control = controls["info"]

    if not _ui_exists(info_control):
        return

    material = _selected_material(panel_name)
    if not material:
        label = "{0} material(s)".format(len(_filtered_materials(panel_name)))
        cmds.text(info_control, edit=True, label=label)
        return

    shader_type = cmds.nodeType(material)
    shading_groups = _material_shading_groups(material)
    assigned = _assigned_objects(material)
    label = "{0}  |  {1}  |  SG: {2}  |  Objects: {3}".format(
        material,
        shader_type,
        len(shading_groups),
        len(assigned),
    )
    cmds.text(info_control, edit=True, label=label)


def select_material(panel_name=PANEL_NAME):
    material = _selected_material(panel_name)
    if not material:
        cmds.warning("No material selected in cHypershade.")
        return

    cmds.select(material, replace=True)


def assign_to_selection(panel_name=PANEL_NAME):
    material = _selected_material(panel_name)
    if not material:
        cmds.warning("No material selected in cHypershade.")
        return

    selection = cmds.ls(selection=True, long=True) or []
    if not selection:
        cmds.warning("Select object(s) before assigning a material.")
        return

    shading_group = _ensure_shading_group(material)
    cmds.sets(selection, edit=True, forceElement=shading_group)
    update_info(panel_name)
    print("Assigned {0} to {1} item(s).".format(material, len(selection)))


def select_assigned_objects(panel_name=PANEL_NAME):
    material = _selected_material(panel_name)
    if not material:
        cmds.warning("No material selected in cHypershade.")
        return

    objects = _assigned_objects(material)
    if not objects:
        cmds.warning("{0} is not assigned to any objects.".format(material))
        return

    cmds.select(objects, replace=True)


def _controls(panel_name):
    controls = _PANEL_CONTROLS.get(panel_name)
    if controls:
        return controls

    prefix = panel_name.replace("|", "_").replace(":", "_")
    controls = {
        "root": prefix + "_root",
        "toolbar": prefix + "_toolbar",
        "filter": prefix + "_filter",
        "refresh": prefix + "_refresh",
        "select": prefix + "_select",
        "assign": prefix + "_assign",
        "list": prefix + "_list",
        "actions": prefix + "_actions",
        "select_objects": prefix + "_selectObjects",
        "open_hypershade": prefix + "_openHypershade",
        "info": prefix + "_info",
    }
    _PANEL_CONTROLS[panel_name] = controls
    return controls


def _filtered_materials(panel_name):
    controls = _controls(panel_name)
    query = ""
    if _ui_exists(controls["filter"]):
        query = cmds.textField(controls["filter"], query=True, text=True).lower()

    materials = []
    for material in cmds.ls(materials=True) or []:
        if _is_default_material(material):
            continue
        if query and query not in material.lower():
            continue
        materials.append(material)

    return sorted(materials, key=lambda name: name.lower())


def _is_default_material(material):
    short_name = material.rsplit(":", 1)[-1]
    return short_name in _DEFAULT_MATERIALS


def _selected_material(panel_name):
    controls = _controls(panel_name)
    list_control = controls["list"]
    if not _ui_exists(list_control):
        return None

    selected = cmds.textScrollList(list_control, query=True, selectItem=True) or []
    return selected[0] if selected else None


def _material_shading_groups(material):
    groups = cmds.listConnections(
        material,
        source=False,
        destination=True,
        type="shadingEngine",
    ) or []
    return sorted(set(groups))


def _ensure_shading_group(material):
    shading_groups = _material_shading_groups(material)
    if shading_groups:
        return shading_groups[0]

    sg_name = material.rsplit(":", 1)[-1] + "SG"
    shading_group = cmds.sets(
        renderable=True,
        noSurfaceShader=True,
        empty=True,
        name=sg_name,
    )

    out_attr = material + ".outColor"
    if cmds.objExists(out_attr):
        cmds.connectAttr(out_attr, shading_group + ".surfaceShader", force=True)

    return shading_group


def _assigned_objects(material):
    objects = set()
    for shading_group in _material_shading_groups(material):
        for member in cmds.sets(shading_group, query=True) or []:
            node = member.split(".", 1)[0]
            if not cmds.objExists(node):
                continue

            try:
                node_type = cmds.nodeType(node)
            except Exception:
                node_type = None

            if node_type in ("mesh", "nurbsSurface", "subdiv"):
                parents = cmds.listRelatives(node, parent=True, fullPath=False) or []
                objects.add(parents[0] if parents else node)
            else:
                objects.add(node)

    return sorted(objects)
