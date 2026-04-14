"""Clip Setter UI -- Maya window for managing animation clip layout.

Usage::

    from clip_setter.ui import show
    show()
"""

import os

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from shiboken6 import wrapInstance
from PySide6 import QtWidgets

from .clips import (DEFAULT_CLIPS, DEFAULT_BUFFER, DEFAULT_START,
                    layout_clips, timeline_end, clip_by_name)
from . import export

WINDOW_NAME = 'clipSetterWin'
WINDOW_TITLE = 'Clip Setter — s&box Character'


class ClipSetterWindow:

    def __init__(self):
        self._clip_rows = []   # [(name_fld, frames_fld, loop_cb, cat_fld)]
        self._buffer_fld = None
        self._start_fld = None

    # ──────────────────────────────────────────────
    #  Show
    # ──────────────────────────────────────────────

    def show(self):
        if cmds.window(WINDOW_NAME, exists=True):
            cmds.deleteUI(WINDOW_NAME)
        win = cmds.window(WINDOW_NAME, title=WINDOW_TITLE,
                          widthHeight=(560, 520), sizeable=True)
        root_form = cmds.formLayout()

        scroll = cmds.scrollLayout(childResizable=True)
        main_col = cmds.columnLayout(adjustableColumn=True)

        # ── Settings ──
        cmds.frameLayout(label='Layout Settings', collapsable=True,
                         marginHeight=4, marginWidth=4)
        cmds.columnLayout(adjustableColumn=True)
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(100, 60, 100, 60))
        cmds.text(label='Start Frame:', align='right')
        self._start_fld = cmds.intField(v=DEFAULT_START, min=0, width=50)
        cmds.text(label='Buffer Frames:', align='right')
        self._buffer_fld = cmds.intField(v=DEFAULT_BUFFER, min=0, width=50)
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.setParent(main_col)

        # ── Clip Table ──
        cmds.frameLayout(label='Animation Clips', collapsable=True,
                         marginHeight=4, marginWidth=4)
        self._clip_col = cmds.columnLayout(adjustableColumn=True)

        # Header
        cmds.rowLayout(numberOfColumns=8,
                       columnWidth=[(1, 130), (2, 50), (3, 45),
                                    (4, 80), (5, 50), (6, 50),
                                    (7, 28), (8, 28)])
        cmds.text(label='  Name', align='left', font='boldLabelFont')
        cmds.text(label='Frames', align='left', font='boldLabelFont')
        cmds.text(label='Loop', align='left', font='boldLabelFont')
        cmds.text(label='Category', align='left', font='boldLabelFont')
        cmds.text(label='Start', align='left', font='boldLabelFont')
        cmds.text(label='End', align='left', font='boldLabelFont')
        cmds.text(label='', width=28)
        cmds.text(label='', width=28)
        cmds.setParent('..')

        for clip in DEFAULT_CLIPS:
            self._add_clip_row(clip)

        cmds.setParent(main_col)

        # ── Add/Remove ──
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(280, 280))
        cmds.button(label='+ Add Clip',
                    command=lambda *_: self._add_clip_row(
                        {'name': 'new_clip', 'frames': 30,
                         'loop': True, 'category': 'locomotion'}))
        cmds.button(label='- Remove Last',
                    command=lambda *_: self._remove_last_row())
        cmds.setParent(main_col)

        # ── Preview ──
        cmds.separator(height=8, style='in')
        cmds.button(label='Preview Layout (Print)',
                    annotation='Print clip layout with frame ranges to Script Editor',
                    command=lambda *_: self._preview())

        # ── Character Set / Bind Pose Separators ──
        cmds.separator(height=8, style='in')
        cmds.frameLayout(label='Bind Pose Separators', collapsable=True,
                         marginHeight=4, marginWidth=4)
        cmds.columnLayout(adjustableColumn=True)
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(100, 250, 80),
                       adjustableColumn=2)
        cmds.text(label='Character Set:', align='right')
        self._charset_menu = cmds.optionMenu(
            annotation='Select the character set to use for bind pose keys')
        cmds.menuItem(label='(none)')
        self._populate_charset_menu()
        cmds.button(label='Refresh',
                    command=lambda *_: self._populate_charset_menu())
        cmds.setParent('..')
        cmds.button(label='Key Bind Pose Separators', height=28,
                    backgroundColor=(0.50, 0.35, 0.55),
                    annotation='Key all character set channels to bind pose '
                               'at buffer midpoints between clips',
                    command=lambda *_: self._key_separators())
        cmds.setParent('..')
        cmds.setParent('..')

        cmds.setParent(root_form)

        # ── Bottom actions ──
        bottom = cmds.columnLayout(adjustableColumn=True)
        cmds.separator(height=8, style='in')

        cmds.rowLayout(numberOfColumns=3, columnWidth3=(186, 186, 186),
                       adjustableColumn=2)
        cmds.button(label='Apply to Timeline', height=32,
                    backgroundColor=(0.22, 0.45, 0.55),
                    annotation='Set Maya timeline range to cover all clips',
                    command=lambda *_: self._apply_timeline())
        cmds.button(label='Apply to Game Exporter', height=32,
                    backgroundColor=(0.22, 0.55, 0.22),
                    annotation='Set clips directly on the Game Exporter node',
                    command=lambda *_: self._apply_game_exporter())
        cmds.button(label='Export All FBX', height=32,
                    backgroundColor=(0.55, 0.40, 0.15),
                    annotation='Export each clip as a separate FBX (selection-based)',
                    command=lambda *_: self._export_fbx())
        cmds.setParent(bottom)

        cmds.setParent(root_form)
        cmds.formLayout(root_form, e=True,
            attachForm=[(scroll, 'top', 0), (scroll, 'left', 0),
                        (scroll, 'right', 0),
                        (bottom, 'left', 0), (bottom, 'right', 0),
                        (bottom, 'bottom', 0)],
            attachControl=[(scroll, 'bottom', 0, bottom)],
            attachNone=[(bottom, 'top')])

        cmds.showWindow(win)

    # ──────────────────────────────────────────────
    #  Clip rows
    # ──────────────────────────────────────────────

    def _add_clip_row(self, clip):
        cmds.setParent(self._clip_col)
        idx = len(self._clip_rows)
        row = cmds.rowLayout(numberOfColumns=8,
                             columnWidth=[(1, 130), (2, 50), (3, 45),
                                          (4, 80), (5, 50), (6, 50),
                                          (7, 28), (8, 28)])
        name_fld = cmds.textField(text=clip['name'], width=125)
        frames_fld = cmds.intField(v=clip['frames'], min=1, width=50)
        loop_cb = cmds.checkBox(label='', v=clip.get('loop', True))
        cat_fld = cmds.textField(text=clip.get('category', ''), width=80)
        start_lbl = cmds.text(label='—', width=50, align='center')
        end_lbl = cmds.text(label='—', width=50, align='center')
        cmds.button(label='[ ]', width=24, height=18,
                    backgroundColor=(0.18, 0.18, 0.18),
                    annotation='Set playback range to this clip',
                    command=lambda *_, i=idx: self._view_clip(i))
        cmds.button(label='|>', width=24, height=18,
                    backgroundColor=(0.15, 0.45, 0.15),
                    annotation='Play this clip',
                    command=lambda *_, i=idx: self._play_clip(i))
        cmds.setParent('..')
        self._clip_rows.append({
            'row': row,
            'name': name_fld,
            'frames': frames_fld,
            'loop': loop_cb,
            'category': cat_fld,
            'start_lbl': start_lbl,
            'end_lbl': end_lbl,
        })
        self._update_ranges()

    def _remove_last_row(self):
        if not self._clip_rows:
            return
        entry = self._clip_rows.pop()
        cmds.deleteUI(entry['row'])
        self._update_ranges()

    def _read_clips(self):
        """Read current clip definitions from the UI."""
        clips = []
        for entry in self._clip_rows:
            clips.append({
                'name': cmds.textField(entry['name'], q=True, text=True).strip(),
                'frames': cmds.intField(entry['frames'], q=True, v=True),
                'loop': cmds.checkBox(entry['loop'], q=True, v=True),
                'category': cmds.textField(entry['category'], q=True, text=True).strip(),
            })
        return clips

    def _get_layout(self):
        """Read UI and compute layout."""
        clips = self._read_clips()
        buf = cmds.intField(self._buffer_fld, q=True, v=True)
        start = cmds.intField(self._start_fld, q=True, v=True)
        return layout_clips(clips, buffer=buf, start=start)

    def _update_ranges(self):
        """Recompute and display start/end labels for each row."""
        layout = self._get_layout()
        for i, entry in enumerate(self._clip_rows):
            if i < len(layout):
                cmds.text(entry['start_lbl'], e=True,
                          label=str(int(layout[i]['start'])))
                cmds.text(entry['end_lbl'], e=True,
                          label=str(int(layout[i]['end'])))

    # ──────────────────────────────────────────────
    #  Clip playback
    # ──────────────────────────────────────────────

    def _view_clip(self, idx):
        """Set the playback range to the given clip's frame range."""
        layout = self._get_layout()
        if idx >= len(layout):
            return
        clip = layout[idx]
        cmds.playbackOptions(min=clip['start'], max=clip['end'],
                             ast=clip['start'], aet=clip['end'])
        cmds.currentTime(clip['start'])

    def _play_clip(self, idx):
        """Set playback range to the clip and start playback."""
        self._view_clip(idx)
        layout = self._get_layout()
        if idx >= len(layout):
            return
        cmds.play(forward=True)

    # ──────────────────────────────────────────────
    #  Character Set / Bind Pose
    # ──────────────────────────────────────────────

    def _populate_charset_menu(self):
        """Refresh the character set dropdown with sets from the scene."""
        items = cmds.optionMenu(self._charset_menu, q=True, ill=True) or []
        for item in items:
            cmds.deleteUI(item)
        cmds.menuItem(label='(none)', parent=self._charset_menu)
        char_sets = cmds.ls(type='character') or []
        for cs in sorted(char_sets):
            cmds.menuItem(label=cs, parent=self._charset_menu)

    def _key_separators(self):
        """Key bind pose at buffer midpoints using the selected character set."""
        cs = cmds.optionMenu(self._charset_menu, q=True, v=True)
        if not cs or cs == '(none)':
            cmds.warning('Select a character set first.')
            return
        layout = self._get_layout()
        self._update_ranges()
        count = export.key_bind_pose_separators(layout, cs)
        if count:
            cmds.confirmDialog(
                title='Bind Pose Separators',
                message='{} keys set across buffer gaps.\n'
                        'All clips are now isolated.'.format(count),
                button=['OK'])

    # ──────────────────────────────────────────────
    #  Actions
    # ──────────────────────────────────────────────

    def _preview(self):
        layout = self._get_layout()
        self._update_ranges()
        print('// ── Clip Layout ──')
        for c in layout:
            loop_tag = 'loop' if c['loop'] else 'once'
            print('//   {:20s}  {:4d} - {:4d}  ({} frames, {})'.format(
                c['name'], c['start'], c['end'], c['frames'], loop_tag))
        print('//   Total: {} clips, last frame: {}'.format(
            len(layout), timeline_end(layout)))

    def _apply_timeline(self):
        layout = self._get_layout()
        self._update_ranges()
        export.setup_timeline(layout)

    def _apply_game_exporter(self):
        layout = self._get_layout()
        self._update_ranges()
        node = export.apply_clips(layout)
        cmds.confirmDialog(
            title='Applied',
            message='{} clips set on Game Exporter node "{}"\n\n'
                    'Open the Game Exporter to verify.'.format(
                        len(layout), node),
            button=['OK'])

    def _export_fbx(self):
        layout = self._get_layout()
        self._update_ranges()

        # Warn if nothing is selected
        sel = cmds.ls(sl=True)
        if not sel:
            result = cmds.confirmDialog(
                title='No Selection',
                message='No nodes are selected. Export all?\n'
                        '(For cleaner FBX, select the skeleton root + mesh first.)',
                button=['Export All', 'Cancel'],
                defaultButton='Cancel',
                cancelButton='Cancel')
            if result != 'Export All':
                return

        result = cmds.fileDialog2(
            fileMode=3, caption='Choose Export Folder')
        if not result:
            return
        output_dir = result[0]
        selection_only = bool(sel)

        exported = export.export_clips(layout, output_dir,
                                       selection_only=selection_only)
        cmds.confirmDialog(
            title='Export Complete',
            message='Exported {} clips to:\n{}'.format(
                len(exported), output_dir),
            button=['OK'])

    def _qt_parent(self):
        ptr = omui.MQtUtil.mainWindow()
        return wrapInstance(int(ptr), QtWidgets.QWidget) if ptr else None


# ── module-level convenience ──

def show():
    """Create and show the Clip Setter window."""
    win = ClipSetterWindow()
    win.show()
    return win
