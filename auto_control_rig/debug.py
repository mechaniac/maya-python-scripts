import maya.cmds as cmds
import math


def _axis_direction(matrix, col):
    """Extract a column (axis direction) from a 4x4 matrix list."""
    return [matrix[col], matrix[col + 4], matrix[col + 8]]


def _normalize(v):
    mag = math.sqrt(sum(x * x for x in v))
    return [x / mag for x in v] if mag > 1e-9 else v


def _describe(vec):
    """Return a human-readable label for a world-space direction vector."""
    labels = [(0, "+Right"), (0, "-Left"),
              (1, "+Up"),    (1, "-Down"),
              (2, "+Fwd"),   (2, "-Back")]
    best = ""
    best_val = 0
    for i, (axis_idx, name) in enumerate(labels):
        sign = 1 if i % 2 == 0 else -1
        val = vec[axis_idx] * sign
        if val > best_val:
            best_val = val
            best = name
    return best


def log_joint_axes(joints=None):
    """Print local X, Y, Z axis directions for each joint in world space.

    If *joints* is ``None``, uses the current selection.
    Run this on the skin (forward) skeleton to inspect its convention.

    Usage from Maya Script Editor::

        from auto_control_rig.debug import log_joint_axes
        log_joint_axes()          # uses selection
        log_joint_axes(["FKSpine_M", "FKChest_M"])
    """
    if joints is None:
        joints = cmds.ls(sl=True, long=False)
    if not joints:
        cmds.warning("No joints selected or specified.")
        return

    header = "{:<30s}  {:>22s}  {:>22s}  {:>22s}".format(
        "Joint", "Local X", "Local Y", "Local Z")
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)

    for jnt in joints:
        if not cmds.objExists(jnt):
            print(f"  {jnt}: NOT FOUND")
            continue
        m = cmds.xform(jnt, q=True, ws=True, m=True)
        x = _normalize(_axis_direction(m, 0))
        y = _normalize(_axis_direction(m, 1))
        z = _normalize(_axis_direction(m, 2))

        def _fmt(v):
            desc = _describe(v)
            return "({:+.3f},{:+.3f},{:+.3f}) {}".format(*v, desc)

        print("{:<30s}  {}  {}  {}".format(jnt, _fmt(x), _fmt(y), _fmt(z)))

    print(sep)
