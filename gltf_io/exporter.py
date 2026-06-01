"""glTF / GLB export.

Two backends, auto-selected:

* **maya2glTF** plugin (preferred when installed) -- direct export
  through ``cmds.file``.
* **FBX2glTF** binary (fallback) -- exports to FBX first via Maya's
  built-in FBX exporter, then converts FBX -> .glb / .gltf.
"""

import os
import tempfile
import maya.cmds as cmds
import maya.mel as mel

from . import plugin, fbx2gltf


# ── maya2glTF backend ─────────────────────────────────────────────


def _gltf_export_options(export_animation, export_materials, export_skin,
                         export_cameras, export_lights, embed_textures,
                         frame_range):
    opts = [
        "exportAnimations={0}".format(1 if export_animation else 0),
        "exportMaterials={0}".format(1 if export_materials else 0),
        "exportSkins={0}".format(1 if export_skin else 0),
        "exportCameras={0}".format(1 if export_cameras else 0),
        "exportLights={0}".format(1 if export_lights else 0),
        "embedTextures={0}".format(1 if embed_textures else 0),
    ]
    if frame_range is not None:
        opts.append("animationStart={0}".format(int(frame_range[0])))
        opts.append("animationEnd={0}".format(int(frame_range[1])))
    return ";".join(opts)


def _export_via_maya2gltf(path, selection_only, binary,
                          export_animation, export_materials, export_skin,
                          export_cameras, export_lights, embed_textures,
                          frame_range):
    translator = plugin.export_translator(binary=binary)
    if not translator:
        return False

    options = _gltf_export_options(
        export_animation, export_materials, export_skin,
        export_cameras, export_lights, embed_textures, frame_range)

    kwargs = dict(force=True, type=translator, options=options,
                  preserveReferences=True)
    if selection_only:
        kwargs["exportSelected"] = True
    else:
        kwargs["exportAll"] = True

    cmds.file(path, **kwargs)
    return True


# ── FBX2glTF backend ──────────────────────────────────────────────


def _ensure_fbx_plugin():
    if not cmds.pluginInfo("fbxmaya", q=True, loaded=True):
        try:
            cmds.loadPlugin("fbxmaya", quiet=True)
        except Exception as exc:
            raise RuntimeError("Could not load Maya FBX plugin: " + str(exc)) from exc


def _configure_fbx(export_animation, export_skin, frame_range):
    """Drive the FBX exporter via FBXExport* MEL commands."""
    mel.eval("FBXResetExport;")
    mel.eval("FBXExportFileVersion -v FBX202000;")
    mel.eval("FBXExportInAscii -v false;")
    mel.eval('FBXExportUpAxis y;')
    mel.eval("FBXExportSmoothingGroups -v true;")
    mel.eval("FBXExportTangents -v true;")
    mel.eval("FBXExportSmoothMesh -v true;")
    mel.eval("FBXExportTriangulate -v false;")
    mel.eval("FBXExportEmbeddedTextures -v true;")
    mel.eval("FBXExportInputConnections -v false;")

    mel.eval("FBXExportSkins -v {0};".format(
        "true" if export_skin else "false"))
    mel.eval("FBXExportShapes -v {0};".format(
        "true" if export_skin else "false"))
    mel.eval("FBXExportSkeletonDefinitions -v {0};".format(
        "true" if export_skin else "false"))

    mel.eval("FBXExportAnimationOnly -v false;")
    if export_animation:
        mel.eval("FBXExportBakeComplexAnimation -v true;")
        if frame_range is not None:
            mel.eval("FBXExportBakeComplexStart -v {0};".format(int(frame_range[0])))
            mel.eval("FBXExportBakeComplexEnd -v {0};".format(int(frame_range[1])))
        mel.eval("FBXExportBakeComplexStep -v 1;")
        mel.eval("FBXExportBakeResampleAnimation -v true;")
    else:
        mel.eval("FBXExportBakeComplexAnimation -v false;")


def _export_fbx(fbx_path, selection_only,
                export_animation, export_skin, frame_range):
    _ensure_fbx_plugin()
    _configure_fbx(export_animation, export_skin, frame_range)
    fbx_path = fbx_path.replace("\\", "/")
    if selection_only:
        mel.eval('FBXExport -f "{0}" -s;'.format(fbx_path))
    else:
        mel.eval('FBXExport -f "{0}";'.format(fbx_path))
    if not os.path.isfile(fbx_path):
        raise RuntimeError("FBX export failed: " + fbx_path)


def _export_via_fbx2gltf(path, selection_only, binary,
                         export_animation, export_skin, embed_textures,
                         draco, khr_unlit, frame_range,
                         progress_fn=None):
    exe = fbx2gltf.ensure_fbx2gltf(progress_fn=progress_fn)

    tmp_dir = tempfile.mkdtemp(prefix="gltf_io_")
    try:
        fbx_path = os.path.join(tmp_dir, "stage.fbx")
        if progress_fn:
            progress_fn("Exporting FBX intermediate ...")
        _export_fbx(fbx_path, selection_only,
                    export_animation, True, frame_range)

        if progress_fn:
            progress_fn("Converting FBX -> glTF ...")
        fbx2gltf.convert(
            fbx_path, path,
            binary=binary,
            embed_textures=embed_textures,
            draco=draco,
            khr_materials_unlit=khr_unlit,
            exe_path=exe,
        )
    finally:
        try:
            for f in os.listdir(tmp_dir):
                try:
                    os.remove(os.path.join(tmp_dir, f))
                except Exception:
                    pass
            os.rmdir(tmp_dir)
        except Exception:
            pass

    return True


# ── public API ────────────────────────────────────────────────────


def available_backends():
    """Return list of backends usable right now: 'maya2gltf', 'fbx2gltf'."""
    out = []
    if plugin.export_translator(binary=True) or plugin.export_translator(False):
        out.append("maya2gltf")
    if fbx2gltf.find_fbx2gltf():
        out.append("fbx2gltf")
    return out


def export_file(path,
                selection_only=False,
                binary=None,
                backend="auto",
                export_animation=True,
                export_materials=True,
                export_skin=True,
                export_cameras=False,
                export_lights=False,
                embed_textures=True,
                draco=False,
                khr_materials_unlit=False,
                frame_range=None,
                progress_fn=None):
    """Export current scene (or selection) to .glb / .gltf.

    Parameters
    ----------
    path : str
        Output path.
    backend : 'auto' | 'maya2gltf' | 'fbx2gltf'
        Which exporter to use.  ``'auto'`` prefers maya2glTF when
        the plugin is loaded, otherwise falls back to FBX2glTF.
    """
    if binary is None:
        binary = path.lower().endswith(".glb")
    if not binary and not path.lower().endswith(".gltf"):
        path += ".gltf"
    if binary and not path.lower().endswith(".glb"):
        path += ".glb"

    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    if frame_range is None and export_animation:
        frame_range = (cmds.playbackOptions(q=True, min=True),
                       cmds.playbackOptions(q=True, max=True))

    chosen = backend
    if chosen == "auto":
        chosen = "maya2gltf" if plugin.export_translator(binary=binary) \
            else "fbx2gltf"

    if chosen == "maya2gltf":
        ok = _export_via_maya2gltf(
            path, selection_only, binary,
            export_animation, export_materials, export_skin,
            export_cameras, export_lights, embed_textures, frame_range)
        if ok:
            return path
        # fall through to FBX2glTF
        chosen = "fbx2gltf"

    if chosen == "fbx2gltf":
        _export_via_fbx2gltf(
            path, selection_only, binary,
            export_animation, export_skin, embed_textures,
            draco, khr_materials_unlit, frame_range,
            progress_fn=progress_fn)
        return path

    raise ValueError("Unknown backend: " + str(backend))


def batch_export(nodes, folder, binary=True, backend="auto", **kwargs):
    """Export each top-level node in *nodes* to its own file in *folder*."""
    if not os.path.isdir(folder):
        os.makedirs(folder)
    ext = ".glb" if binary else ".gltf"
    written = []
    original = cmds.ls(sl=True, long=True) or []
    try:
        for node in nodes:
            if not cmds.objExists(node):
                cmds.warning("Skipping missing node: " + node)
                continue
            cmds.select(node, replace=True)
            base = node.split("|")[-1].split(":")[-1]
            out = os.path.join(folder, base + ext)
            export_file(out, selection_only=True, binary=binary,
                        backend=backend, **kwargs)
            written.append(out)
    finally:
        if original:
            cmds.select(original, replace=True)
        else:
            cmds.select(clear=True)
    return written
