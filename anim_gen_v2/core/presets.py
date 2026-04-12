"""JSON preset save / load with repo and project preset discovery."""

import json
import os
import datetime

import maya.cmds as cmds


# ── paths ──

def _repo_preset_dir(cycle_type='walk'):
    """Return the repo-tracked presets folder for *cycle_type*."""
    pkg = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(pkg, 'presets', cycle_type)


def _project_preset_dir(cycle_type='walk'):
    """Return the current Maya project's preset folder, or None."""
    ws = cmds.workspace(q=True, rd=True)
    if not ws:
        return None
    return os.path.join(ws, 'data', 'anim_presets', cycle_type)


# ── low-level I/O ──

def save(filepath, data):
    """Write *data* dict to a JSON file (creating dirs as needed)."""
    d = os.path.dirname(filepath)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def load(filepath):
    """Read and return a dict from a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


# ── discovery ──

def list_presets(cycle_type='walk'):
    """Return a list of ``{'name', 'path', 'source'}`` dicts.

    Sources: ``'library'`` (repo-tracked) and ``'project'``.
    """
    found = []
    repo_dir = _repo_preset_dir(cycle_type)
    if os.path.isdir(repo_dir):
        for fn in sorted(os.listdir(repo_dir)):
            if fn.lower().endswith('.json'):
                found.append({
                    'name': os.path.splitext(fn)[0],
                    'path': os.path.join(repo_dir, fn),
                    'source': 'library',
                })
    proj_dir = _project_preset_dir(cycle_type)
    if proj_dir and os.path.isdir(proj_dir):
        for fn in sorted(os.listdir(proj_dir)):
            if fn.lower().endswith('.json'):
                found.append({
                    'name': os.path.splitext(fn)[0],
                    'path': os.path.join(proj_dir, fn),
                    'source': 'project',
                })
    return found


# ── save helpers ──

def _wrap_meta(data, name, cycle_type='walk', description=''):
    """Wrap param data with a meta block."""
    out = dict(data)
    out['meta'] = {
        'type': cycle_type,
        'name': name,
        'description': description,
        'author': os.environ.get('USERNAME', os.environ.get('USER', '')),
        'date': datetime.date.today().isoformat(),
    }
    return out


def save_to_library(data, name, cycle_type='walk', description=''):
    """Save preset to the repo-tracked library folder."""
    wrapped = _wrap_meta(data, name, cycle_type, description)
    path = os.path.join(_repo_preset_dir(cycle_type),
                        '{}.json'.format(name))
    save(path, wrapped)
    return path


def save_to_project(data, name, cycle_type='walk', description=''):
    """Save preset to the current Maya project."""
    proj_dir = _project_preset_dir(cycle_type)
    if not proj_dir:
        cmds.warning('No Maya project set -- cannot save to project.')
        return None
    wrapped = _wrap_meta(data, name, cycle_type, description)
    path = os.path.join(proj_dir, '{}.json'.format(name))
    save(path, wrapped)
    return path


# ── legacy file-browser helpers (still used by Save As...) ──

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
