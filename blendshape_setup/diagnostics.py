"""Diagnostics: log everything that touches managed group visibility.

Use when meshes/groups are being hidden "by themselves" on selection
changes and you need to find the offender. Adds three hooks:

1. **Visibility watchers** — one ``scriptJob -attributeChange`` per
   ``.visibility`` / ``.lodVisibility`` on every transform under every
   ``BlendshapeKeyGroups/*`` group (and their mesh shapes). Whenever the
   value changes, logs the new value, the current selection, the current
   time, and a Python traceback so you can see exactly which call did it.
2. **Selection marker** — one ``scriptJob -event SelectionChanged`` that
   writes a clearly-marked separator line into the log every time the
   user selects something. Makes it trivial to scan the log and see
   "selection changed -> these visibility plugs flipped."
3. **MEL command echo** — turns on ``commandEcho`` so every MEL command
   following a selection change is also visible in the script editor.

Logs go to BOTH the Maya script editor (via ``print``) and to a file
under the user's temp dir, timestamped per session.

Public API::

    from blendshape_setup import diagnostics
    diagnostics.start()    # begin watching
    diagnostics.stop()     # remove all watchers
    diagnostics.status()   # what's currently being watched
    diagnostics.log_path() # path to current log file

Safe to call ``start()`` multiple times — it tears down old watchers
first. ``stop()`` always cleans up. The watchers survive scene reloads
only if you call ``start()`` again afterwards (we do not auto-rebind on
``sceneOpened`` because that itself is part of what may be misbehaving).
"""

import datetime
import os
import tempfile
import traceback

import maya.cmds as cmds


# ---------------------------------------------------------------- module state

_STATE = {
    "jobs": [],            # list of scriptJob ids
    "log_file": None,      # path str
    "echo_was_on": None,   # bool snapshot of commandEcho state
    "watched": [],         # list of attr strings being watched
}

KEY_GROUP_ROOT = "BlendshapeKeyGroups"  # mirrors logic.KEY_GROUP_ROOT
SEPARATOR = "=" * 72


# ---------------------------------------------------------------- public api

def start(roots=None, watch_shapes=True, watch_lod=True, echo_mel=True):
    """Start logging visibility changes and selection events.

    Args:
        roots: optional list of root group names to watch under. Defaults
            to every transform named ``BlendshapeKeyGroups`` (or with the
            ``cbsKeyGroupRootManaged`` attribute) found in the scene.
        watch_shapes: also watch ``.visibility`` on each mesh shape under
            every group descendant. Default True.
        watch_lod: also watch ``.lodVisibility`` (Maya's other show/hide
            channel). Default True.
        echo_mel: turn on ``cmds.commandEcho`` so MEL commands also print
            into the script editor. Default True.
    """
    stop()  # idempotent

    log = _open_log()
    _write_header(log, roots, watch_shapes, watch_lod, echo_mel)

    discovered_roots = roots or _find_roots()
    if not discovered_roots:
        _emit("No BlendshapeKeyGroups roots found. Nothing to watch.")
        return

    nodes_to_watch = _collect_nodes(discovered_roots, watch_shapes)
    attrs = _collect_attrs(nodes_to_watch, watch_lod)

    for attr in attrs:
        job_id = _install_attr_watcher(attr)
        if job_id is not None:
            _STATE["jobs"].append(job_id)
            _STATE["watched"].append(attr)

    sel_job = cmds.scriptJob(event=("SelectionChanged", _on_selection_changed))
    _STATE["jobs"].append(sel_job)

    if echo_mel:
        try:
            _STATE["echo_was_on"] = bool(
                cmds.commandEcho(query=True, state=True)
            )
            cmds.commandEcho(state=True, lineNumbers=True)
        except Exception:
            _STATE["echo_was_on"] = None

    _emit(
        "Diagnostics started. Watching {0} attribute(s) across {1} root(s). "
        "Log file: {2}".format(
            len(_STATE["watched"]),
            len(discovered_roots),
            _STATE["log_file"],
        )
    )


def stop():
    """Tear down all watchers and restore commandEcho state."""
    for job_id in list(_STATE["jobs"]):
        try:
            if cmds.scriptJob(exists=job_id):
                cmds.scriptJob(kill=job_id, force=True)
        except Exception:
            pass

    if _STATE["echo_was_on"] is not None:
        try:
            cmds.commandEcho(state=bool(_STATE["echo_was_on"]))
        except Exception:
            pass

    cleared = {
        "jobs": len(_STATE["jobs"]),
        "watched": len(_STATE["watched"]),
        "log_file": _STATE["log_file"],
    }
    _STATE["jobs"] = []
    _STATE["watched"] = []
    _STATE["echo_was_on"] = None
    # keep _STATE["log_file"] so log_path() still works after stop()

    _emit("Diagnostics stopped. Cleared {0} job(s), {1} watcher(s).".format(
        cleared["jobs"], cleared["watched"]
    ))


def status():
    """Return a dict describing the current diagnostics state."""
    return {
        "running": bool(_STATE["jobs"]),
        "job_count": len(_STATE["jobs"]),
        "watched_attrs": list(_STATE["watched"]),
        "log_file": _STATE["log_file"],
    }


def log_path():
    """Return the path to the current (or most recent) log file."""
    return _STATE["log_file"]


# ---------------------------------------------------------------- internals


def _find_roots():
    roots = []
    seen = set()

    # By managed attribute (preferred).
    for node in cmds.ls(type="transform", long=True) or []:
        if cmds.objExists("{0}.cbsKeyGroupRootManaged".format(node)):
            if node not in seen:
                roots.append(node)
                seen.add(node)

    # Fallback: by name.
    for node in cmds.ls(KEY_GROUP_ROOT, long=True) or []:
        if node not in seen:
            roots.append(node)
            seen.add(node)

    return roots


def _collect_nodes(roots, watch_shapes):
    nodes = []
    seen = set()
    for root in roots:
        if root not in seen:
            nodes.append(root)
            seen.add(root)
        descendants = cmds.listRelatives(
            root,
            allDescendents=True,
            type="transform",
            fullPath=True,
        ) or []
        for node in descendants:
            if node in seen:
                continue
            nodes.append(node)
            seen.add(node)
            if watch_shapes:
                shapes = cmds.listRelatives(
                    node,
                    shapes=True,
                    fullPath=True,
                    noIntermediate=True,
                ) or []
                for shape in shapes:
                    if shape in seen:
                        continue
                    nodes.append(shape)
                    seen.add(shape)
    return nodes


def _collect_attrs(nodes, watch_lod):
    attrs = []
    for node in nodes:
        for attr_name in ("visibility", "lodVisibility") if watch_lod else ("visibility",):
            attr = "{0}.{1}".format(node, attr_name)
            if cmds.objExists(attr):
                attrs.append(attr)
    return attrs


def _install_attr_watcher(attr):
    # Closure captures attr name so the callback can identify itself.
    def _callback(_attr=attr):
        _on_visibility_changed(_attr)

    try:
        return cmds.scriptJob(attributeChange=(attr, _callback))
    except Exception as exc:
        _emit("Could not watch {0}: {1}".format(attr, exc))
        return None


def _on_visibility_changed(attr):
    try:
        value = cmds.getAttr(attr)
    except Exception:
        value = "<unreadable>"

    try:
        connections = cmds.listConnections(attr, source=True, plugs=True) or []
    except Exception:
        connections = []

    try:
        current_frame = cmds.currentTime(query=True)
    except Exception:
        current_frame = "?"

    try:
        sel = cmds.ls(selection=True, long=True) or []
    except Exception:
        sel = []

    stack = traceback.format_stack(limit=15)
    # Trim the last frames that are inside this module itself.
    stack = [line for line in stack if "diagnostics.py" not in line]

    lines = [
        "",
        SEPARATOR,
        "[{0}] VISIBILITY CHANGED".format(_timestamp()),
        "  attr     : {0}".format(attr),
        "  new value: {0}".format(value),
        "  time     : {0}".format(current_frame),
        "  selection: {0}".format(sel if sel else "<empty>"),
        "  incoming : {0}".format(connections if connections else "<none>"),
        "  python traceback (most recent call last):",
    ]
    for entry in stack:
        for sub in entry.rstrip().splitlines():
            lines.append("    " + sub)
    lines.append(SEPARATOR)
    _emit("\n".join(lines))


def _on_selection_changed():
    try:
        sel = cmds.ls(selection=True, long=True) or []
    except Exception:
        sel = []
    try:
        current_frame = cmds.currentTime(query=True)
    except Exception:
        current_frame = "?"

    _emit(
        "\n{sep}\n[{ts}] SELECTION CHANGED -> {n} item(s) @ frame {f}\n  {sel}\n{sep}".format(
            sep="-" * 72,
            ts=_timestamp(),
            n=len(sel),
            f=current_frame,
            sel=sel if sel else "<empty>",
        )
    )


def _open_log():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(
        tempfile.gettempdir(),
        "blendshape_setup_diagnostics_{0}.log".format(ts),
    )
    _STATE["log_file"] = path
    return path


def _write_header(path, roots, watch_shapes, watch_lod, echo_mel):
    header = [
        SEPARATOR,
        "Blendshape Setup Diagnostics",
        "Started : {0}".format(_timestamp()),
        "Log file: {0}".format(path),
        "Args    : roots={0} watch_shapes={1} watch_lod={2} echo_mel={3}".format(
            roots, watch_shapes, watch_lod, echo_mel,
        ),
        SEPARATOR,
        "",
    ]
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(header))
    except Exception:
        pass
    for line in header:
        print(line)


def _emit(message):
    try:
        print(message)
    except Exception:
        pass
    path = _STATE["log_file"]
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(message)
            if not message.endswith("\n"):
                fh.write("\n")
    except Exception:
        pass


def _timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
