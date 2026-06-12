import maya.cmds as cmds


def ensure_display_affected():
    """Enable Maya's Display Affected viewport preference."""
    try:
        if not cmds.displayPref(q=True, displayAffected=True):
            cmds.displayPref(displayAffected=True)
            print("Display Affected (History Highlight) is now: True")
    except Exception:
        pass
