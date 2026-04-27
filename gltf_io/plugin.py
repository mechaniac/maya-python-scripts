"""Detect and load the community ``maya2glTF`` plugin if it is installed.

Maya 2026 has **no** built-in glTF support. The community plugin
`maya2glTF <https://github.com/iimachines/Maya2glTF>`_ adds a Maya
file translator (and MEL ``maya2glTF_export`` command). When this
plugin is loaded both glTF *import* and glTF *export* are available
through the standard ``cmds.file`` API.

For Maya 2026 specifically, see the maintained fork
`Maya2glTF_Update <https://github.com/JunkYardRobotBoy/Maya2glTF_Update>`_.

If the plugin is not installed, the tool falls back to the
FBX2glTF binary pipeline for *export only*.
"""

import maya.cmds as cmds


# The maya2glTF plugin ships under one of these file names depending
# on build.  We probe each.
_PLUGIN_CANDIDATES = (
    "maya2glTF",
    "maya2gltf",
    "Maya2glTF",
)


_state = {"probed": False}


def _try_load(name):
    try:
        if cmds.pluginInfo(name, q=True, loaded=True):
            return True
    except Exception:
        pass
    try:
        cmds.loadPlugin(name, quiet=True)
        return bool(cmds.pluginInfo(name, q=True, loaded=True))
    except Exception:
        return False


def ensure_loaded(force=False):
    """Try to load the maya2glTF plugin. Returns True if loaded."""
    if _state["probed"] and not force and is_loaded():
        return True
    for name in _PLUGIN_CANDIDATES:
        _try_load(name)
    _state["probed"] = True
    return is_loaded()


def is_loaded():
    """True if any maya2glTF-style plugin is currently loaded."""
    try:
        loaded = cmds.pluginInfo(q=True, listPlugins=True) or []
    except Exception:
        return False
    return any("gltf" in p.lower() for p in loaded)


def loaded_gltf_plugins():
    try:
        loaded = cmds.pluginInfo(q=True, listPlugins=True) or []
    except Exception:
        return []
    return [p for p in loaded if "gltf" in p.lower()]


# ── translator discovery ──────────────────────────────────────────


def _all_translators():
    try:
        return list(cmds.translator(q=True, list=True) or [])
    except Exception:
        return []


def _translator_extension(name):
    try:
        return (cmds.translator(name, q=True, extension=True) or "").lower()
    except Exception:
        return ""


def _looks_like_gltf(name):
    n = name.lower()
    if "gltf" in n or "glb" in n:
        return True
    return _translator_extension(name) in ("gltf", "glb")


def _is_readable(name):
    try:
        return bool(cmds.translator(name, q=True, readSupport=True))
    except Exception:
        return False


def _is_writable(name):
    try:
        return bool(cmds.translator(name, q=True, writeSupport=True))
    except Exception:
        return False


def _wants_binary(name):
    n = name.lower()
    if "glb" in n:
        return True
    return _translator_extension(name) == "glb"


def import_translator():
    """Return the maya2glTF import-translator name, or None if unavailable."""
    ensure_loaded()
    cands = [t for t in _all_translators()
             if _looks_like_gltf(t) and _is_readable(t)]
    if not cands:
        return None
    for t in cands:
        if "import" in t.lower():
            return t
    return cands[0]


def export_translator(binary=True):
    """Return the maya2glTF export-translator name, or None if unavailable."""
    ensure_loaded()
    cands = [t for t in _all_translators()
             if _looks_like_gltf(t) and _is_writable(t)]
    if not cands:
        return None
    matching = [t for t in cands if _wants_binary(t) == binary]
    pool = matching or cands
    for t in pool:
        if "export" in t.lower():
            return t
    return pool[0]


# ── status / diagnostics ──────────────────────────────────────────


def status_message():
    ensure_loaded()
    if not is_loaded():
        return ("maya2glTF plugin not installed.  "
                "Install it from https://github.com/iimachines/Maya2glTF "
                "(Maya 2026: https://github.com/JunkYardRobotBoy/Maya2glTF_Update). "
                "Export will fall back to FBX2glTF.")
    plugins = loaded_gltf_plugins()
    imp = import_translator()
    exp = export_translator(binary=True) or export_translator(binary=False)
    parts = ["plugin: " + ", ".join(plugins)]
    parts.append("import: " + ("'{0}'".format(imp) if imp else "<none>"))
    parts.append("export: " + ("'{0}'".format(exp) if exp else "<none>"))
    return "  |  ".join(parts)


def diagnostic_report():
    ensure_loaded(force=True)
    lines = ["[gltf_io] maya2glTF diagnostic"]
    lines.append("  candidate plugin names probed: " + ", ".join(_PLUGIN_CANDIDATES))
    lines.append("  loaded glTF plugins: "
                 + (", ".join(loaded_gltf_plugins()) or "<none>"))
    lines.append("  glTF-ish translators registered:")
    found = False
    for t in _all_translators():
        if _looks_like_gltf(t):
            found = True
            lines.append("    * {0}  (ext={1}, read={2}, write={3})".format(
                t, _translator_extension(t),
                _is_readable(t), _is_writable(t)))
    if not found:
        lines.append("    <none>")
    lines.append("  chosen import translator:      " + str(import_translator()))
    lines.append("  chosen GLB export translator:  " + str(export_translator(True)))
    lines.append("  chosen glTF export translator: " + str(export_translator(False)))
    msg = "\n".join(lines)
    print(msg)
    return msg
