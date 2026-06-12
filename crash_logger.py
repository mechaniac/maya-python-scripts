"""Small crash-oriented logger for Maya tool button actions.

The log is deliberately written into this repository and flushed on every
event. If Maya hard-crashes, the final line should show the last button phase
that ran before the process died.
"""

import datetime
import json
import os
import sys
import traceback


LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "maya_tool_crash.log")

_SESSION_READY = False
_SESSION_KEY = "pid={0}".format(os.getpid())


def log_event(event, action=None, **data):
    """Append one flushed JSON line to the current Maya-session log."""
    try:
        _ensure_session()
        payload = {
            "time": datetime.datetime.now().isoformat(timespec="milliseconds"),
            "event": event,
        }
        if action:
            payload["action"] = action
        if data:
            payload.update(data)

        line = json.dumps(
            payload,
            sort_keys=True,
            default=_json_default,
        )
        _write_line(line)
    except Exception:
        pass


def log_exception(event, action=None, exc=None, **data):
    if exc is not None:
        data["exception"] = "{0}: {1}".format(
            exc.__class__.__name__,
            exc,
        )
    data["traceback"] = traceback.format_exc()
    log_event(event, action=action, **data)


def maya_state():
    """Return a tiny Maya state snapshot for button press logging."""
    try:
        import maya.cmds as cmds
    except Exception:
        return {}

    state = {}
    try:
        state["scene"] = cmds.file(query=True, sceneName=True) or "<unsaved>"
    except Exception:
        pass
    try:
        state["frame"] = cmds.currentTime(query=True)
    except Exception:
        pass
    try:
        selection = cmds.ls(selection=True, long=True) or []
        state["selection_count"] = len(selection)
        state["selection"] = selection[:12]
    except Exception:
        pass
    return state


def _ensure_session():
    global _SESSION_READY
    if _SESSION_READY:
        return

    header = "# maya_tool_crash_log {0}".format(_SESSION_KEY)
    first_line = ""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as handle:
                first_line = handle.readline().strip()
    except Exception:
        first_line = ""

    if first_line != header:
        _reset_log(header)
    _SESSION_READY = True


def _reset_log(header):
    lines = [
        header,
        "# started={0}".format(
            datetime.datetime.now().isoformat(timespec="seconds"),
        ),
        "# python={0}".format(sys.version.replace("\n", " ")),
    ]
    _write_text("\n".join(lines) + "\n", mode="w")


def _write_line(line):
    _write_text(line + "\n", mode="a")


def _write_text(text, mode):
    with open(LOG_FILE, mode, encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except Exception:
            pass


def _json_default(value):
    try:
        return repr(value)
    except Exception:
        return "<unrepresentable>"
