"""Maya window for the glTF / GLB Importer & Exporter."""

import os
import maya.cmds as cmds

from . import importer, exporter, plugin, fbx2gltf

_WIN = "GltfIoWin"


def show():
    if cmds.window(_WIN, exists=True):
        cmds.deleteUI(_WIN)

    cmds.window(_WIN, title="glTF / GLB Importer & Exporter",
                widthHeight=(500, 620), sizeable=True)
    main = cmds.columnLayout(adjustableColumn=True, rowSpacing=4,
                             columnAttach=("both", 8))

    cmds.separator(height=4, style="none")
    cmds.text(label="glTF / GLB Importer & Exporter",
              font="boldLabelFont", align="center")
    cmds.separator(height=8, style="in")

    # ── backend status ─────────────────────────────────────────────
    cmds.text("gltf_status_plugin", label="", align="left", wordWrap=True)
    cmds.text("gltf_status_fbx", label="", align="left", wordWrap=True)
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                   columnAttach3=("both", "right", "right"),
                   columnOffset3=(0, 4, 4))
    cmds.button(label="Refresh", height=22,
                command=lambda *_: _refresh_status())
    cmds.button(label="Diagnose", height=22, w=90,
                command=lambda *_: plugin.diagnostic_report())
    cmds.button(label="Download FBX2glTF", height=22, w=140,
                command=lambda *_: _do_download())
    cmds.setParent(main)
    cmds.separator(height=8, style="in")

    tabs = cmds.tabLayout(innerMarginWidth=6, innerMarginHeight=6)
    imp_tab = _build_import_tab(); cmds.setParent(tabs)
    exp_tab = _build_export_tab(); cmds.setParent(tabs)
    batch_tab = _build_batch_tab(); cmds.setParent(tabs)
    cmds.tabLayout(tabs, e=True, tabLabel=(
        (imp_tab, "Import"),
        (exp_tab, "Export"),
        (batch_tab, "Batch"),
    ))

    cmds.setParent(main)
    cmds.separator(height=8, style="in")
    cmds.text("gltf_msg", label="", align="left", wordWrap=True)

    _refresh_status()
    cmds.showWindow(_WIN)


# ── tab builders ──────────────────────────────────────────────────


def _build_import_tab():
    col = cmds.columnLayout(adjustableColumn=True, rowSpacing=4,
                            columnAttach=("both", 4))
    cmds.text(label="(maya2glTF plugin if loaded, otherwise pure-Python "
                    "fallback: meshes + basic materials only)", align="left",
              font="smallObliqueLabelFont")

    cmds.text(label="File (.glb / .gltf):", align="left")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach2=("both", "right"), columnOffset2=(0, 4))
    cmds.textField("gltf_imp_path", placeholderText="Path to .glb / .gltf")
    cmds.button(label="Browse", w=60, command=_browse_import)
    cmds.setParent(col)

    cmds.separator(height=6, style="none")
    cmds.text(label="Namespace (optional):", align="left")
    cmds.textField("gltf_imp_ns", placeholderText="leave empty for prefix")

    cmds.separator(height=6, style="none")
    cmds.checkBox("gltf_imp_anim", label="Import Animations", value=True)
    cmds.checkBox("gltf_imp_mat",  label="Import Materials",  value=True)
    cmds.checkBox("gltf_imp_skin", label="Import Skin Weights", value=True)
    cmds.checkBox("gltf_imp_merge", label="Merge Namespaces on Clash",
                  value=True)

    cmds.separator(height=10, style="in")
    cmds.button(label="Import", height=34, backgroundColor=(0.3, 0.55, 0.3),
                command=_do_import)
    return col


def _build_export_tab():
    col = cmds.columnLayout(adjustableColumn=True, rowSpacing=4,
                            columnAttach=("both", 4))

    cmds.text(label="Output File:", align="left")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach2=("both", "right"), columnOffset2=(0, 4))
    cmds.textField("gltf_exp_path", placeholderText="Path to .glb / .gltf")
    cmds.button(label="Browse", w=60, command=_browse_export)
    cmds.setParent(col)

    cmds.separator(height=6, style="none")
    cmds.radioButtonGrp("gltf_exp_format", label="Format",
                        labelArray2=("GLB (binary)", "glTF (text + bin)"),
                        numberOfRadioButtons=2, select=1,
                        columnWidth3=(60, 110, 110))
    cmds.optionMenu("gltf_exp_backend", label="Backend")
    cmds.menuItem(label="auto")
    cmds.menuItem(label="maya2gltf")
    cmds.menuItem(label="fbx2gltf")

    cmds.separator(height=6, style="none")
    cmds.checkBox("gltf_exp_sel",  label="Export Selection Only", value=False)
    cmds.checkBox("gltf_exp_anim", label="Export Animations",     value=True)
    cmds.checkBox("gltf_exp_mat",  label="Export Materials       (maya2glTF only)",
                  value=True)
    cmds.checkBox("gltf_exp_skin", label="Export Skin Weights",   value=True)
    cmds.checkBox("gltf_exp_cam",  label="Export Cameras          (maya2glTF only)",
                  value=False)
    cmds.checkBox("gltf_exp_lit",  label="Export Lights           (maya2glTF only)",
                  value=False)
    cmds.checkBox("gltf_exp_tex",  label="Embed Textures",        value=True)
    cmds.checkBox("gltf_exp_draco", label="Draco Mesh Compression (FBX2glTF only)",
                  value=False)
    cmds.checkBox("gltf_exp_unlit", label="KHR_materials_unlit    (FBX2glTF only)",
                  value=False)

    cmds.separator(height=6, style="none")
    cmds.checkBox("gltf_exp_userange", label="Override Frame Range",
                  value=False, changeCommand=lambda *_: _toggle_range())
    cmds.intFieldGrp("gltf_exp_range", numberOfFields=2,
                     label="Start / End", value1=1, value2=120,
                     columnWidth3=(60, 60, 60), enable=False)

    cmds.separator(height=10, style="in")
    cmds.button(label="Export", height=34, backgroundColor=(0.3, 0.55, 0.3),
                command=_do_export)
    return col


def _build_batch_tab():
    col = cmds.columnLayout(adjustableColumn=True, rowSpacing=4,
                            columnAttach=("both", 4))

    cmds.text(label="Batch Import - folder of .glb/.gltf:", align="left")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach2=("both", "right"), columnOffset2=(0, 4))
    cmds.textField("gltf_batch_in", placeholderText="Source folder")
    cmds.button(label="Browse", w=60, command=_browse_batch_in)
    cmds.setParent(col)
    cmds.button(label="Batch Import All", height=28, command=_do_batch_import)

    cmds.separator(height=10, style="in")
    cmds.text(label="Batch Export - one file per selected top node:",
              align="left")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach2=("both", "right"), columnOffset2=(0, 4))
    cmds.textField("gltf_batch_out", placeholderText="Output folder")
    cmds.button(label="Browse", w=60, command=_browse_batch_out)
    cmds.setParent(col)
    cmds.radioButtonGrp("gltf_batch_fmt", label="Format",
                        labelArray2=("GLB", "glTF"),
                        numberOfRadioButtons=2, select=1,
                        columnWidth3=(60, 60, 60))
    cmds.button(label="Batch Export Selection", height=28,
                command=_do_batch_export)
    return col


# ── helpers ───────────────────────────────────────────────────────


def _refresh_status():
    plugin._state["probed"] = False
    plug_msg = plugin.status_message()
    fbx_path = fbx2gltf.find_fbx2gltf()
    fbx_msg = ("FBX2glTF: " + fbx_path) if fbx_path \
        else "FBX2glTF: not installed (export fallback unavailable)"
    if cmds.text("gltf_status_plugin", exists=True):
        cmds.text("gltf_status_plugin", e=True, label=plug_msg)
    if cmds.text("gltf_status_fbx", exists=True):
        cmds.text("gltf_status_fbx", e=True, label=fbx_msg)


def _toggle_range():
    on = cmds.checkBox("gltf_exp_userange", q=True, value=True)
    cmds.intFieldGrp("gltf_exp_range", e=True, enable=on)


def _set_msg(text, error=False):
    if cmds.text("gltf_msg", exists=True):
        cmds.text("gltf_msg", e=True, label=text)
    if error:
        cmds.warning(text)
    else:
        print("[gltf_io] " + text)


def _do_download(*_):
    def progress(s):
        _set_msg(s)
        cmds.refresh()
    try:
        path = fbx2gltf.download_fbx2gltf(progress_fn=progress)
        _set_msg("FBX2glTF installed: " + path)
        _refresh_status()
    except Exception as exc:
        _set_msg("Download failed: " + str(exc), error=True)


# ── browse callbacks ──────────────────────────────────────────────


def _browse_import(*_):
    r = cmds.fileDialog2(fileFilter="glTF (*.glb *.gltf);;All Files (*.*)",
                         dialogStyle=2, fileMode=1,
                         caption="Select glTF / GLB File")
    if r:
        cmds.textField("gltf_imp_path", e=True, text=r[0])


def _browse_export(*_):
    r = cmds.fileDialog2(fileFilter="GLB (*.glb);;glTF (*.gltf)",
                         dialogStyle=2, fileMode=0,
                         caption="Save glTF / GLB File")
    if r:
        cmds.textField("gltf_exp_path", e=True, text=r[0])


def _browse_batch_in(*_):
    r = cmds.fileDialog2(dialogStyle=2, fileMode=3,
                         caption="Select Folder to Batch-Import")
    if r:
        cmds.textField("gltf_batch_in", e=True, text=r[0])


def _browse_batch_out(*_):
    r = cmds.fileDialog2(dialogStyle=2, fileMode=3,
                         caption="Select Folder for Batch Export")
    if r:
        cmds.textField("gltf_batch_out", e=True, text=r[0])


# ── action callbacks ──────────────────────────────────────────────


def _do_import(*_):
    path = cmds.textField("gltf_imp_path", q=True, text=True).strip()
    if not path:
        _set_msg("Pick a file first.", error=True); return
    ns = cmds.textField("gltf_imp_ns", q=True, text=True).strip() or None
    try:
        importer.import_file(
            path,
            namespace=ns,
            merge_namespaces=cmds.checkBox("gltf_imp_merge", q=True, value=True),
            import_animation=cmds.checkBox("gltf_imp_anim", q=True, value=True),
            import_materials=cmds.checkBox("gltf_imp_mat",  q=True, value=True),
            import_skin=cmds.checkBox("gltf_imp_skin", q=True, value=True),
        )
        _set_msg("Imported: " + os.path.basename(path))
    except Exception as exc:
        _set_msg("Import failed: " + str(exc), error=True)


def _do_export(*_):
    path = cmds.textField("gltf_exp_path", q=True, text=True).strip()
    if not path:
        _set_msg("Pick an output path first.", error=True); return
    binary = cmds.radioButtonGrp("gltf_exp_format", q=True, select=True) == 1
    backend = cmds.optionMenu("gltf_exp_backend", q=True, value=True)

    rng = None
    if cmds.checkBox("gltf_exp_userange", q=True, value=True):
        rng = (cmds.intFieldGrp("gltf_exp_range", q=True, value1=True),
               cmds.intFieldGrp("gltf_exp_range", q=True, value2=True))

    def progress(s):
        _set_msg(s); cmds.refresh()

    try:
        out = exporter.export_file(
            path,
            selection_only=cmds.checkBox("gltf_exp_sel", q=True, value=True),
            binary=binary,
            backend=backend,
            export_animation=cmds.checkBox("gltf_exp_anim", q=True, value=True),
            export_materials=cmds.checkBox("gltf_exp_mat",  q=True, value=True),
            export_skin=cmds.checkBox("gltf_exp_skin", q=True, value=True),
            export_cameras=cmds.checkBox("gltf_exp_cam", q=True, value=True),
            export_lights=cmds.checkBox("gltf_exp_lit", q=True, value=True),
            embed_textures=cmds.checkBox("gltf_exp_tex", q=True, value=True),
            draco=cmds.checkBox("gltf_exp_draco", q=True, value=True),
            khr_materials_unlit=cmds.checkBox("gltf_exp_unlit", q=True, value=True),
            frame_range=rng,
            progress_fn=progress,
        )
        _set_msg("Exported: " + out)
    except Exception as exc:
        _set_msg("Export failed: " + str(exc), error=True)


def _do_batch_import(*_):
    folder = cmds.textField("gltf_batch_in", q=True, text=True).strip()
    if not folder:
        _set_msg("Pick a source folder.", error=True); return
    try:
        files = importer.batch_import(folder)
        _set_msg("Batch-imported {0} file(s).".format(len(files)))
    except Exception as exc:
        _set_msg("Batch import failed: " + str(exc), error=True)


def _do_batch_export(*_):
    folder = cmds.textField("gltf_batch_out", q=True, text=True).strip()
    if not folder:
        _set_msg("Pick an output folder.", error=True); return
    nodes = cmds.ls(sl=True, long=True) or []
    if not nodes:
        _set_msg("Select one or more top-level nodes to export.", error=True); return
    binary = cmds.radioButtonGrp("gltf_batch_fmt", q=True, select=True) == 1
    try:
        files = exporter.batch_export(nodes, folder, binary=binary)
        _set_msg("Batch-exported {0} file(s).".format(len(files)))
    except Exception as exc:
        _set_msg("Batch export failed: " + str(exc), error=True)
