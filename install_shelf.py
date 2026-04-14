"""Install / update the C_Scripts Maya shelf.

Run once from the Script Editor (or any shelf button) to create or
refresh the shelf with the latest button definitions.  Safe to
re-run -- existing buttons are deleted first so nothing duplicates.

Usage::

    import install_shelf; install_shelf.install()
"""

import maya.cmds as cmds
import maya.mel as mel
import textwrap


SHELF_NAME = 'C_Scripts'


# ── button definitions ────────────────────────────────────────────

_BUTTONS = [
    {
        'label': 'S2 Import',
        'annotation': 'Source 2 Character Importer',
        'image': 'fileOpen.png',
        'command': textwrap.dedent("""\
            import importlib
            import source2_importer.kv3 as _kv3; importlib.reload(_kv3)
            import source2_importer.vrf as _vrf; importlib.reload(_vrf)
            import source2_importer.materials as _mat; importlib.reload(_mat)
            import source2_importer.pipeline as _pip; importlib.reload(_pip)
            import source2_importer.ui as _sui; importlib.reload(_sui)
            import source2Importer; importlib.reload(source2Importer)
            source2Importer.show()
        """),
    },
    {
        'label': 'Ctrl Rig',
        'annotation': 'Auto Control Rig',
        'image': 'kinJoint.png',
        'command': textwrap.dedent("""\
            import importlib
            import auto_control_rig.constants as _con; importlib.reload(_con)
            import auto_control_rig.utils as _utl; importlib.reload(_utl)
            import auto_control_rig.helpers as _hlp; importlib.reload(_hlp)
            import auto_control_rig.skeleton as _skl; importlib.reload(_skl)
            import auto_control_rig.controls as _ctl; importlib.reload(_ctl)
            import auto_control_rig.stretchy as _str; importlib.reload(_str)
            import auto_control_rig.twist as _twt; importlib.reload(_twt)
            import auto_control_rig.mapping as _map; importlib.reload(_map)
            import auto_control_rig.operations as _ops; importlib.reload(_ops)
            import auto_control_rig.debug as _dbg; importlib.reload(_dbg)
            import auto_control_rig.builder as _bld; importlib.reload(_bld)
            import auto_control_rig.ui as _ui; importlib.reload(_ui)
            _ui.show_window()
        """),
    },
    {
        'label': 'AnimGen',
        'annotation': 'Animation Generator v2',
        'image': 'animCurveTA.png',
        'command': textwrap.dedent("""\
            import importlib
            # core
            import anim_gen_v2.core.patterns as _pat; importlib.reload(_pat)
            import anim_gen_v2.core.channel as _ch; importlib.reload(_ch)
            import anim_gen_v2.core.resolver as _res; importlib.reload(_res)
            import anim_gen_v2.core.engine as _eng; importlib.reload(_eng)
            import anim_gen_v2.core.presets as _pre; importlib.reload(_pre)
            # layers
            import anim_gen_v2.layers as _lay; importlib.reload(_lay)
            import anim_gen_v2.layers.walk_primary as _wp; importlib.reload(_wp)
            import anim_gen_v2.layers.walk_secondary as _ws; importlib.reload(_ws)
            import anim_gen_v2.layers.walk_arms as _wa; importlib.reload(_wa)
            import anim_gen_v2.layers.run_primary as _rp; importlib.reload(_rp)
            import anim_gen_v2.layers.sidestep_primary as _sp; importlib.reload(_sp)
            # ui
            import anim_gen_v2.ui.range_slider as _rs; importlib.reload(_rs)
            import anim_gen_v2.ui.window as _win; importlib.reload(_win)
            import anim_gen_v2.launcher as _lnc; importlib.reload(_lnc)
            _lnc.show()
        """),
    },
    {
        'label': 'Clip Set',
        'annotation': 'Clip Setter — s&box Character Export',
        'image': 'out_time.png',
        'command': textwrap.dedent("""\
            import importlib
            import clip_setter.clips as _clp; importlib.reload(_clp)
            import clip_setter.export as _exp; importlib.reload(_exp)
            import clip_setter.ui as _cui; importlib.reload(_cui)
            _cui.show()
        """),
    },
    {
        'label': 'Shelf\nSetup',
        'annotation': 'Reinstall / update this C_Scripts shelf',
        'image': 'refresh.png',
        'command': textwrap.dedent("""\
            import importlib
            import install_shelf; importlib.reload(install_shelf)
            install_shelf.install()
        """),
    },
]


# ── installer ─────────────────────────────────────────────────────

def _ensure_shelf():
    """Create the shelf if it doesn't already exist.  Return its full path."""
    top = mel.eval('$__tmp = $gShelfTopLevel')
    if cmds.shelfLayout(SHELF_NAME, exists=True, parent=top):
        return '{}|{}'.format(top, SHELF_NAME)
    cmds.shelfLayout(SHELF_NAME, parent=top)
    return '{}|{}'.format(top, SHELF_NAME)


def _clear_shelf(shelf_path):
    """Delete every button currently on the shelf."""
    children = cmds.shelfLayout(shelf_path, q=True, childArray=True) or []
    for child in children:
        cmds.deleteUI(child)


def install():
    """Create (or refresh) the C_Scripts shelf with the latest buttons."""
    shelf_path = _ensure_shelf()
    _clear_shelf(shelf_path)

    for btn in _BUTTONS:
        cmds.shelfButton(
            parent=shelf_path,
            label=btn['label'],
            annotation=btn.get('annotation', ''),
            image1=btn.get('image', 'commandButton.png'),
            command=btn['command'],
            sourceType='python',
            imageOverlayLabel=btn['label'].replace('\n', ' '),
        )

    # Switch to the newly created/updated shelf so the user sees it
    top = mel.eval('$__tmp = $gShelfTopLevel')
    cmds.tabLayout(top, e=True, selectTab=SHELF_NAME)
    print('// C_Scripts shelf installed  ({} buttons)'.format(len(_BUTTONS)))
