import maya.cmds as cmds
import json
import os

from .constants import SLOT_DEFS


def get_hierarchy_joints(root):
    desc = cmds.listRelatives(root, ad=1, type="joint", f=1) or []
    return [j.split("|")[-1] for j in [root] + desc]


def auto_map_joints(joint_list):
    mapping = {}
    lmap = {j.lower(): j for j in joint_list}
    for key, _, _, hints in SLOT_DEFS:
        found = ""
        for h in hints:
            hl = h.lower()
            if hl in lmap:
                found = lmap[hl]
                break
            for jl, jn in lmap.items():
                if hl in jl:
                    found = jn
                    break
            if found:
                break
        mapping[key] = found
    return mapping


def save_mapping(filepath, root_joint, mapping):
    dirpath = os.path.dirname(filepath)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    data = {"root": root_joint, "mapping": mapping}
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print("// Saved:", filepath)


def load_mapping(filepath):
    with open(filepath) as f:
        data = json.load(f)
    return data.get("root", ""), data.get("mapping", {})
