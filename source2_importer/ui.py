"""Maya window for the Source 2 Character Importer."""

import os
import maya.cmds as cmds
import ui_word_weighting

from . import vrf as _vrf
from . import pipeline

_WIN = "Source2ImporterWin"

_DEFAULT_VMDL = ("C:/Program Files (x86)/Steam/steamapps/common/"
                 "sbox/addons/citizen/Assets/models/citizen/citizen.vmdl")
_DEFAULT_TEX = ("D:/WORK/Christof/2018_AssetSets_01/WiP/3D/"
                "maya_project/sourceimages/cit")


def show():
    """Open the Source 2 Importer window."""
    if cmds.window(_WIN, exists=True):
        cmds.deleteUI(_WIN)

    cmds.window(_WIN, title="Source 2 Importer", widthHeight=(460, 320),
                sizeable=True)
    main = cmds.columnLayout(adjustableColumn=True, rowSpacing=5,
                             columnAttach=("both", 8))

    # ── model file ────────────────────────────────────────────────
    cmds.text(label="Model File (.vmdl):", align="left")
    r1 = cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                        columnAttach2=("both", "right"), columnOffset2=(0, 4))
    cmds.textField("s2i_vmdl", text=_DEFAULT_VMDL if os.path.isfile(_DEFAULT_VMDL) else "",
                   placeholderText="Path to .vmdl file")
    cmds.button(label="Browse", w=60, command=_browse_vmdl)
    cmds.setParent(main)

    cmds.separator(height=4, style="none")

    # ── VRF path ──────────────────────────────────────────────────
    cmds.text(label="VRF Decompiler (optional — for textures & materials):",
              align="left")
    r2 = cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                        columnAttach3=("both", "right", "right"),
                        columnOffset3=(0, 4, 4))
    cmds.textField("s2i_vrf", placeholderText="Decompiler.exe (auto-detected)")
    cmds.button(label="Browse", w=60, command=_browse_vrf)
    cmds.button(label="Download", w=68, command=_download_vrf)
    cmds.setParent(main)

    # auto-fill if found on disk
    found = _vrf.find_vrf()
    if found:
        cmds.textField("s2i_vrf", e=True, text=found)

    cmds.separator(height=4, style="none")

    # ── texture output ────────────────────────────────────────────
    cmds.text(label="Texture Output:", align="left")
    r3 = cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                        columnAttach2=("both", "right"), columnOffset2=(0, 4))
    cmds.textField("s2i_tex",
                   text=_DEFAULT_TEX if os.path.isdir(os.path.dirname(_DEFAULT_TEX)) else "",
                   placeholderText="Default: project/sourceimages/<model>/")
    cmds.button(label="Browse", w=60, command=_browse_tex)
    cmds.setParent(main)

    cmds.separator(height=12, style="in")

    # ── import button ─────────────────────────────────────────────
    cmds.button(label="Import Model", height=36, command=_do_import,
                backgroundColor=(0.3, 0.55, 0.3))

    cmds.separator(height=4, style="none")
    cmds.text("s2i_status", label="", align="left", wordWrap=True)

    cmds.showWindow(_WIN)
    ui_word_weighting.apply_deferred(_WIN)


# ── callbacks ─────────────────────────────────────────────────────


def _browse_vmdl(*_):
    r = cmds.fileDialog2(fileFilter="Source 2 Model (*.vmdl);;All Files (*.*)",
                         dialogStyle=2, fileMode=1,
                         caption="Select .vmdl File")
    if r:
        cmds.textField("s2i_vmdl", e=True, text=r[0])


def _browse_vrf(*_):
    r = cmds.fileDialog2(fileFilter="Decompiler (*.exe);;All Files (*.*)",
                         dialogStyle=2, fileMode=1,
                         caption="Select VRF Decompiler")
    if r:
        cmds.textField("s2i_vrf", e=True, text=r[0])


def _browse_tex(*_):
    r = cmds.fileDialog2(dialogStyle=2, fileMode=3,
                         caption="Select Texture Output Folder")
    if r:
        cmds.textField("s2i_tex", e=True, text=r[0])


def _download_vrf(*_):
    _status("Downloading VRF Decompiler ...")
    cmds.refresh()
    try:
        exe = _vrf.download_vrf(progress_fn=_status)
        cmds.textField("s2i_vrf", e=True, text=exe)
        _status("VRF downloaded successfully.")
    except Exception as exc:
        _status(f"Download failed: {exc}")


def _do_import(*_):
    vmdl = cmds.textField("s2i_vmdl", q=True, text=True).strip()
    vrf_exe = cmds.textField("s2i_vrf", q=True, text=True).strip()
    tex_out = cmds.textField("s2i_tex", q=True, text=True).strip()

    if not vmdl or not os.path.isfile(vmdl):
        _status("Please select a valid .vmdl file.")
        return

    vrf_exe = vrf_exe if vrf_exe and os.path.isfile(vrf_exe) else None

    # Offer to download VRF if not set
    if not vrf_exe:
        answer = cmds.confirmDialog(
            title="VRF Decompiler Not Found",
            message="VRF Decompiler is needed for textures and materials.\n"
                    "Download it now? (~50 MB from GitHub)",
            button=["Download", "Skip (mesh only)", "Cancel"],
            defaultButton="Download",
            cancelButton="Cancel",
            dismissString="Cancel",
        )
        if answer == "Cancel":
            return
        if answer == "Download":
            _download_vrf()
            vrf_exe = cmds.textField("s2i_vrf", q=True, text=True).strip()
            vrf_exe = vrf_exe if vrf_exe and os.path.isfile(vrf_exe) else None

    tex_out = tex_out if tex_out else None

    _status("Importing ...")
    cmds.refresh()

    try:
        result = pipeline.import_source2_model(
            vmdl, vrf_exe=vrf_exe, texture_output=tex_out,
            progress_fn=_status,
        )
        n = len(result.get("new_nodes", []))
        m = len(result.get("materials_created", []))
        _status(f"Done!  {n} nodes imported, {m} materials created.")
    except Exception as exc:
        _status(f"Error: {exc}")
        raise


def _status(msg):
    if cmds.text("s2i_status", exists=True):
        cmds.text("s2i_status", e=True, label=str(msg))
        cmds.refresh()
