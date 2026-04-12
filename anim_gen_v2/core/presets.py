"""JSON preset save / load with Maya file-browser integration."""

import json

import maya.cmds as cmds


def save(filepath, data):
    """Write *data* dict to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def load(filepath):
    """Read and return a dict from a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def browse_save(data, title='Save Preset'):
    """Open a file dialog, save *data* as JSON.  Returns the path or None."""
    result = cmds.fileDialog2(fileFilter='JSON (*.json)', dialogStyle=2,
                              fileMode=0, caption=title)
    if not result:
        return None
    save(result[0], data)
    return result[0]


def browse_load(title='Load Preset'):
    """Open a file dialog, return the loaded dict or None."""
    result = cmds.fileDialog2(fileFilter='JSON (*.json)', dialogStyle=2,
                              fileMode=1, caption=title)
    if not result:
        return None
    return load(result[0])
