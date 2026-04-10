import maya.cmds as cmds
import os

from .constants import SLOT_DEFS
from .builder import AutoControlRigBuilder
from .operations import remove_control_rig, reset_to_bind_pose, create_foot_roll_locators
from .mapping import get_hierarchy_joints, auto_map_joints, save_mapping, load_mapping


_ui = {"win": "AutoCtrlRigWin", "joints": [], "fields": {}, "labels": {}, "root": None}

try:
    _PRESET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "joint_mappings")
except NameError:
    _PRESET_DIR = os.path.join(cmds.workspace(q=1, rd=1), "joint_mappings")


def _color_labels():
    for k, lbl in _ui["labels"].items():
        v = cmds.optionMenu(_ui["fields"][k], q=1, v=1)
        bg = (0.8, 0.3, 0.3) if v == "(none)" else (0.36, 0.36, 0.36)
        cmds.text(lbl, e=1, bgc=bg)


def _on_root(*a):
    sel = cmds.ls(sl=1, type="joint")
    if not sel:
        cmds.warning("Select a root joint.")
        return
    cmds.textField(_ui["root"], e=1, tx=sel[0])
    _ui["joints"] = get_hierarchy_joints(sel[0])
    _fill_menus()


def _on_sel(slot, *a):
    sel = cmds.ls(sl=1, type="joint")
    if not sel:
        return
    menu = _ui["fields"].get(slot)
    if not menu:
        return
    items = [cmds.menuItem(i, q=1, l=1) for i in (cmds.optionMenu(menu, q=1, ill=1) or [])]
    if sel[0] not in items:
        cmds.menuItem(l=sel[0], p=menu)
    cmds.optionMenu(menu, e=1, v=sel[0])
    _color_labels()


def _on_auto(*a):
    if not _ui["joints"]:
        cmds.warning("Load a root joint first.")
        return
    mp = auto_map_joints(_ui["joints"])
    for k, j in mp.items():
        menu = _ui["fields"].get(k)
        if menu and j:
            try:
                cmds.optionMenu(menu, e=1, v=j)
            except:
                pass
    _color_labels()


def _fill_menus():
    jts = ["(none)"] + sorted(_ui["joints"])
    for k, menu in _ui["fields"].items():
        for i in (cmds.optionMenu(menu, q=1, ill=1) or []):
            cmds.deleteUI(i)
        for j in jts:
            cmds.menuItem(l=j, p=menu)
    _color_labels()


def _read_map():
    return {k: ("" if cmds.optionMenu(m, q=1, v=1) == "(none)" else cmds.optionMenu(m, q=1, v=1))
            for k, m in _ui["fields"].items()}


def _on_build(*a):
    opts = {
        "control_size": cmds.floatField(_ui["sz"], q=1, v=1),
        "create_ik_legs": cmds.checkBox(_ui["ik_l"], q=1, v=1),
        "create_ik_arms": cmds.checkBox(_ui["ik_a"], q=1, v=1),
        "create_fk_arms": cmds.checkBox(_ui["fk_a"], q=1, v=1),
        "create_fk_legs": cmds.checkBox(_ui["fk_l"], q=1, v=1),
        "create_fkik_blend": cmds.checkBox(_ui["fkik"], q=1, v=1),
        "scale_taper": cmds.floatField(_ui["taper"], q=1, v=1),
        "show_debug": cmds.checkBox(_ui["dbg"], q=1, v=1),
        "create_twist_drivers": cmds.checkBox(_ui["twist"], q=1, v=1),
        "roll_start_angle": cmds.floatField(_ui["roll_start"], q=1, v=1),
        "roll_end_angle": cmds.floatField(_ui["roll_end"], q=1, v=1),
    }
    AutoControlRigBuilder(_read_map(), opts).build()


def _on_save(*a):
    r = cmds.fileDialog2(cap="Save Mapping", ff="JSON (*.json)", ds=2, fm=0, dir=_PRESET_DIR)
    if not r:
        return
    save_mapping(r[0], cmds.textField(_ui["root"], q=1, tx=1), _read_map())


def _on_load(*a):
    sd = _PRESET_DIR if os.path.exists(_PRESET_DIR) else ""
    r = cmds.fileDialog2(cap="Load Mapping", ff="JSON (*.json)", ds=2, fm=1, dir=sd)
    if not r:
        return
    rj, mp = load_mapping(r[0])
    if rj and cmds.objExists(rj):
        cmds.textField(_ui["root"], e=1, tx=rj)
        _ui["joints"] = get_hierarchy_joints(rj)
        _fill_menus()
    for k, j in mp.items():
        menu = _ui["fields"].get(k)
        if menu and j:
            items = [cmds.menuItem(i, q=1, l=1) for i in (cmds.optionMenu(menu, q=1, ill=1) or [])]
            if j not in items:
                cmds.menuItem(l=j, p=menu)
            try:
                cmds.optionMenu(menu, e=1, v=j)
            except:
                pass
    _color_labels()
    print("// Loaded:", r[0])


def show_window():
    w = _ui["win"]
    if cmds.window(w, ex=1):
        cmds.deleteUI(w)
    cmds.window(w, t="Auto Control Rig", wh=(520, 700), s=1)
    cmds.scrollLayout(cr=1)
    cmds.columnLayout(adj=1, rs=6)

    cmds.frameLayout(l="Joint Hierarchy", cll=0, mw=10, mh=5)
    cmds.rowLayout(nc=3, cw3=(60, 300, 100), adj=2)
    cmds.text(l="Root:")
    _ui["root"] = cmds.textField(pht="Select root joint...")
    cmds.button(l="From Selection", c=_on_root)
    cmds.setParent("..")
    cmds.button(l="Auto-Map", c=_on_auto, h=28)
    cmds.rowLayout(nc=2, cw2=(200, 200), adj=2)
    cmds.button(l="Save Mapping", c=_on_save)
    cmds.button(l="Load Mapping", c=_on_load)
    cmds.setParent("..")
    cmds.setParent("..")

    cmds.frameLayout(l="Joint Mapping", cll=1, mw=10, mh=5)
    _ui["fields"], _ui["labels"] = {}, {}
    for key, name, side, _ in SLOT_DEFS:
        cmds.rowLayout(nc=3, cw3=(160, 240, 80), adj=2)
        tag = {"L": " [L]", "R": " [R]", "M": ""}[side]
        _ui["labels"][key] = cmds.text(l=name + tag, al="right", bgc=(0.8, 0.3, 0.3))
        _ui["fields"][key] = cmds.optionMenu(cc=lambda *a: _color_labels())
        cmds.menuItem(l="(none)")
        cmds.button(l="< Sel", c=lambda x, k=key: _on_sel(k))
        cmds.setParent("..")
    cmds.separator(h=6, st="in")
    cmds.button(l="Create Foot Roll Locators", h=28, bgc=(0.6, 0.6, 0.8),
                c=lambda *a: create_foot_roll_locators(_read_map()))
    cmds.setParent("..")

    cmds.frameLayout(l="Options", cll=1, mw=10, mh=5)
    cmds.rowColumnLayout(nc=2, cw=[(1, 200), (2, 200)])
    _ui["ik_l"] = cmds.checkBox(l="IK Legs", v=1)
    _ui["ik_a"] = cmds.checkBox(l="IK Arms", v=1)
    _ui["fk_a"] = cmds.checkBox(l="FK Arms", v=1)
    _ui["fk_l"] = cmds.checkBox(l="FK Legs", v=1)
    _ui["fkik"] = cmds.checkBox(l="FK/IK Blend", v=1)
    _ui["twist"] = cmds.checkBox(l="Twist Joints", v=1)
    _ui["dbg"] = cmds.checkBox(l="Show Debug", v=0)
    cmds.setParent("..")
    cmds.rowLayout(nc=2, cw2=(130, 100))
    cmds.text(l="Control Size:")
    _ui["sz"] = cmds.floatField(v=1, min=0.1, max=100)
    cmds.setParent("..")
    cmds.rowLayout(nc=2, cw2=(130, 100))
    cmds.text(l="Scale Taper:")
    _ui["taper"] = cmds.floatField(v=1.3, min=1.0, max=3.0)
    cmds.setParent("..")
    cmds.separator(h=6, st="in")
    cmds.text(l="IK Foot Roll:", fn="boldLabelFont")
    cmds.rowLayout(nc=2, cw2=(130, 100))
    cmds.text(l="Roll Start Angle:")
    _ui["roll_start"] = cmds.floatField(v=30, min=0, max=90)
    cmds.setParent("..")
    cmds.rowLayout(nc=2, cw2=(130, 100))
    cmds.text(l="Roll End Angle:")
    _ui["roll_end"] = cmds.floatField(v=60, min=0, max=120)
    cmds.setParent("..")
    cmds.setParent("..")

    cmds.separator(h=10, st="in")
    cmds.button(l="Build Control Rig", h=40, bgc=(0.4, 0.8, 0.4), c=_on_build)
    cmds.button(l="Remove Control Rig", h=32, bgc=(0.9, 0.4, 0.4),
                c=lambda *a: remove_control_rig())
    cmds.separator(h=10, st="in")

    cmds.frameLayout(l="Post Rig", cll=1, mw=10, mh=5)
    cmds.button(l="Return to Bind Pose", h=32, bgc=(0.5, 0.7, 1.0),
                c=lambda *a: reset_to_bind_pose())
    cmds.setParent("..")

    cmds.showWindow(w)
