"""Logic for building synchronized multi-object blendshape edit sets."""

import re

import maya.cmds as cmds
import maya.mel as mel


MANAGED_ATTR = "cbsManaged"
TARGETS_ATTR = "cbsTargets"
START_ATTR = "cbsStartFrame"
INTERVAL_ATTR = "cbsInterval"
COUNT_ATTR = "cbsTargetCount"

DEFAULT_PREFIX = "blendShape"
DEFAULT_TARGET_NAMES = [
    "SamAltman",
    "ElonMusk",
    "ShouZiChew",
    "SundarPichai",
    "JeffBezos",
    "MarkZuck",
    "TimCook",
    "SatyaNadella",
]
DEFAULT_TARGET_COUNT = len(DEFAULT_TARGET_NAMES)
DEFAULT_START_FRAME = 0
DEFAULT_INTERVAL = 10


def selected_mesh_transforms():
    """Return selected transforms that have non-intermediate polygon meshes."""
    selection = cmds.ls(selection=True, long=True) or []
    transforms = []
    seen = set()

    for item in selection:
        transform = _mesh_transform(item)
        if not transform or transform in seen:
            continue
        transforms.append(transform)
        seen.add(transform)

    return transforms


def generate_setup(target_count=DEFAULT_TARGET_COUNT,
                   name_prefix=DEFAULT_PREFIX,
                   target_names=None,
                   start_frame=DEFAULT_START_FRAME,
                   interval=DEFAULT_INTERVAL,
                   replace_existing=True,
                   open_editor=True):
    """Create managed blendShape deformers and keyed targets on selection."""
    if discover_setups():
        raise RuntimeError(
            "Remove the existing generated setup before generating a new one."
        )

    meshes = selected_mesh_transforms()
    if not meshes:
        raise RuntimeError("Select one or more polygon mesh transforms.")

    target_count = int(target_count)
    start_frame = int(start_frame)
    interval = int(interval)

    if target_count < 1:
        raise RuntimeError("Target count must be at least 1.")
    if interval < 1:
        raise RuntimeError("Frame interval must be at least 1.")

    target_names = build_target_names(
        target_count=target_count,
        name_prefix=name_prefix,
        target_names=target_names,
    )
    target_count = len(target_names)
    records = []

    cmds.undoInfo(openChunk=True)
    try:
        for mesh in meshes:
            existing = managed_blendshape_for_mesh(mesh)
            if existing and replace_existing:
                cmds.delete(existing)
                existing = None

            node = existing or _create_blendshape_node(mesh, target_count)
            _configure_targets(node, target_names)
            _write_metadata(node, target_names, start_frame, interval)
            _key_targets(node, target_names, start_frame, interval)
            records.append({
                "mesh": mesh,
                "node": node,
                "targets": list(target_names),
                "start_frame": start_frame,
                "interval": interval,
            })

        end_frame = target_frame(target_count - 1, start_frame, interval)
        cmds.playbackOptions(
            min=start_frame,
            max=end_frame,
            animationStartTime=start_frame,
            animationEndTime=end_frame,
        )
        activate_target(0, records=records, open_editor=open_editor)
    finally:
        cmds.undoInfo(closeChunk=True)

    print("Blendshape setup created: {0} mesh(es), {1} target(s).".format(
        len(records), target_count))
    return records


def activate_target(index, records=None, open_editor=False):
    """Set target index active on every managed blendShape and edit it."""
    records = records or discover_setups()
    if not records:
        raise RuntimeError("No managed blendshape setup found.")

    first = records[0]
    targets = first.get("targets", [])
    if index < 0 or index >= len(targets):
        raise RuntimeError("Target index out of range.")

    frame = target_frame(index, first["start_frame"], first["interval"])
    cmds.currentTime(frame, edit=True)

    selected_meshes = []
    for record in records:
        node = record["node"]
        if not cmds.objExists(node):
            continue
        if index >= len(record.get("targets", [])):
            continue

        _set_active_weights(node, len(record["targets"]), index)
        try:
            cmds.sculptTarget(node, edit=True, target=index, regenerate=True)
        except Exception as exc:
            cmds.warning("Could not set edit target on {0}: {1}".format(
                node, exc))

        mesh = record.get("mesh")
        if mesh and cmds.objExists(mesh):
            selected_meshes.append(mesh)

    if selected_meshes:
        cmds.select(selected_meshes, replace=True)

    if open_editor:
        open_blendshape_editor()

    print("Editing {0} at frame {1}.".format(targets[index], frame))
    return frame


def activate_all_off(records=None):
    """Set all managed blendShape targets to zero and jump to start frame."""
    records = records or discover_setups()
    if not records:
        raise RuntimeError("No managed blendshape setup found.")

    start_frame = records[0]["start_frame"]
    cmds.currentTime(start_frame, edit=True)
    for record in records:
        node = record["node"]
        if not cmds.objExists(node):
            continue
        _set_active_weights(node, len(record["targets"]), -1)
        try:
            cmds.sculptTarget(node, edit=True, target=-1)
        except Exception:
            pass

    meshes = [
        record["mesh"] for record in records
        if record.get("mesh") and cmds.objExists(record["mesh"])
    ]
    if meshes:
        cmds.select(meshes, replace=True)

    print("All managed blendShape targets set to 0 at frame {0}.".format(
        start_frame))
    return start_frame


def disable_edit_mode(records=None):
    """Turn off sculpt target edit mode on all managed blendShapes."""
    records = records or discover_setups()
    for record in records:
        node = record["node"]
        if cmds.objExists(node):
            try:
                cmds.sculptTarget(node, edit=True, target=-1)
            except Exception:
                pass


def remove_setup(records=None):
    """Delete managed blendShape nodes created by this tool."""
    records = records or discover_setups()
    if not records:
        raise RuntimeError("No managed blendshape setup found.")

    nodes = []
    seen = set()
    for record in records:
        node = record.get("node")
        if node and node not in seen and cmds.objExists(node):
            nodes.append(node)
            seen.add(node)

    if not nodes:
        raise RuntimeError("No managed blendshape nodes exist anymore.")

    cmds.undoInfo(openChunk=True)
    try:
        disable_edit_mode(records=records)
        cmds.delete(nodes)
    finally:
        cmds.undoInfo(closeChunk=True)

    print("Removed {0} managed blendShape setup node(s).".format(len(nodes)))
    return len(nodes)


def discover_setups():
    """Find blendShape nodes created by this tool."""
    records = []
    for node in cmds.ls(type="blendShape") or []:
        attr = "{0}.{1}".format(node, MANAGED_ATTR)
        if not cmds.objExists(attr) or not cmds.getAttr(attr):
            continue

        targets = _read_string_attr(node, TARGETS_ATTR).split("|")
        targets = [target for target in targets if target]
        mesh = _mesh_from_blendshape(node)
        start_frame = _read_numeric_attr(node, START_ATTR, DEFAULT_START_FRAME)
        interval = _read_numeric_attr(node, INTERVAL_ATTR, DEFAULT_INTERVAL)
        records.append({
            "mesh": mesh,
            "node": node,
            "targets": targets,
            "start_frame": int(start_frame),
            "interval": int(interval),
        })

    records.sort(key=lambda record: record["node"])
    return records


def target_frame(index, start_frame=DEFAULT_START_FRAME,
                 interval=DEFAULT_INTERVAL):
    return int(start_frame) + (int(interval) * (int(index) + 1))


def all_zero_frame(start_frame=DEFAULT_START_FRAME):
    return int(start_frame)


def build_target_names(target_count=DEFAULT_TARGET_COUNT,
                       name_prefix=DEFAULT_PREFIX,
                       target_names=None):
    """Return sanitized, unique target names for a generated setup."""
    target_count = int(target_count)
    if target_count < 1:
        return []

    source = list(target_names or [])
    names = []
    for index in range(target_count):
        if index < len(source):
            raw_name = str(source[index]).strip()
        else:
            raw_name = ""

        if not raw_name:
            if index < len(DEFAULT_TARGET_NAMES):
                raw_name = DEFAULT_TARGET_NAMES[index]
            else:
                raw_name = "{0}{1}".format(name_prefix, index + 1)
        names.append(_safe_target_name(raw_name))

    return _dedupe_target_names(names)


def managed_blendshape_for_mesh(mesh):
    history = cmds.listHistory(mesh, pruneDagObjects=True) or []
    for node in history:
        if cmds.nodeType(node) != "blendShape":
            continue
        attr = "{0}.{1}".format(node, MANAGED_ATTR)
        if cmds.objExists(attr) and cmds.getAttr(attr):
            return node
    return None


def open_blendshape_editor():
    """Open Maya's blendShape/Shape editor if available."""
    for command in ("BlendShapeEditor;", "ShapeEditor;"):
        try:
            mel.eval(command)
            return True
        except Exception:
            pass
    return False


def _mesh_transform(item):
    if not cmds.objExists(item):
        return None

    node_type = cmds.nodeType(item)
    if node_type == "mesh":
        if cmds.getAttr(item + ".intermediateObject"):
            return None
        parents = cmds.listRelatives(item, parent=True, fullPath=True) or []
        return parents[0] if parents else None

    if node_type == "transform":
        shapes = cmds.listRelatives(
            item,
            shapes=True,
            fullPath=True,
            noIntermediate=True,
        ) or []
        if any(cmds.nodeType(shape) == "mesh" for shape in shapes):
            return item

    return None


def _create_blendshape_node(mesh, target_count):
    base_name = _short_name(mesh) + "_cbs_blendShape"
    node_name = _unique_name(base_name)
    created = cmds.blendShape(
        mesh,
        name=node_name,
        origin="local",
        weightCount=target_count,
    )
    if not created:
        raise RuntimeError("Could not create blendShape for {0}.".format(mesh))
    return created[0]


def _configure_targets(node, target_names):
    for index, target_name in enumerate(target_names):
        cmds.blendShape(node, edit=True, weight=(index, 0.0))
        _alias_weight(node, index, target_name)

        try:
            cmds.sculptTarget(node, edit=True, target=index, regenerate=True)
        except Exception as exc:
            cmds.warning("Could not initialize {0}.{1}: {2}".format(
                node, target_name, exc))

    cmds.sculptTarget(node, edit=True, target=-1)


def _alias_weight(node, index, target_name):
    attr = "{0}.w[{1}]".format(node, index)
    aliases = cmds.aliasAttr(node, query=True) or []
    for i in range(0, len(aliases), 2):
        alias = aliases[i]
        plug = aliases[i + 1]
        if plug == "weight[{0}]".format(index) or alias == target_name:
            try:
                cmds.aliasAttr("{0}.{1}".format(node, alias), remove=True)
            except Exception:
                try:
                    cmds.aliasAttr("{0}.w[{1}]".format(node, index), remove=True)
                except Exception:
                    pass
    cmds.aliasAttr(target_name, attr)


def _write_metadata(node, target_names, start_frame, interval):
    _ensure_bool_attr(node, MANAGED_ATTR)
    cmds.setAttr("{0}.{1}".format(node, MANAGED_ATTR), True)

    _ensure_string_attr(node, TARGETS_ATTR)
    cmds.setAttr(
        "{0}.{1}".format(node, TARGETS_ATTR),
        "|".join(target_names),
        type="string",
    )

    _ensure_long_attr(node, START_ATTR)
    cmds.setAttr("{0}.{1}".format(node, START_ATTR), int(start_frame))

    _ensure_long_attr(node, INTERVAL_ATTR)
    cmds.setAttr("{0}.{1}".format(node, INTERVAL_ATTR), int(interval))

    _ensure_long_attr(node, COUNT_ATTR)
    cmds.setAttr("{0}.{1}".format(node, COUNT_ATTR), len(target_names))


def _key_targets(node, target_names, start_frame, interval):
    frames = [all_zero_frame(start_frame)]
    frames.extend(target_frame(i, start_frame, interval)
                  for i in range(len(target_names)))

    for frame in frames:
        active_index = -1
        if frame != start_frame:
            active_index = int((frame - start_frame) / interval) - 1

        for index, target_name in enumerate(target_names):
            value = 1.0 if index == active_index else 0.0
            attr = "{0}.{1}".format(node, target_name)
            if not cmds.objExists(attr):
                attr = "{0}.w[{1}]".format(node, index)
            cmds.setAttr(attr, value)
            cmds.setKeyframe(attr, time=frame, value=value)

    for index, target_name in enumerate(target_names):
        attr = "{0}.{1}".format(node, target_name)
        if not cmds.objExists(attr):
            attr = "{0}.w[{1}]".format(node, index)
        try:
            cmds.keyTangent(
                attr,
                edit=True,
                inTangentType="step",
                outTangentType="step",
            )
        except Exception:
            pass


def _set_active_weights(node, count, active_index):
    for index in range(count):
        value = 1.0 if index == active_index else 0.0
        cmds.blendShape(node, edit=True, weight=(index, value))


def _mesh_from_blendshape(node):
    geometry = cmds.blendShape(node, query=True, geometry=True) or []
    if not geometry:
        return None

    shape = geometry[0]
    if cmds.nodeType(shape) == "mesh":
        parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
        return parents[0] if parents else shape
    return shape


def _safe_target_name(name):
    name = re.sub(r"[^A-Za-z0-9_]", "_", name.strip())
    name = re.sub(r"_+", "_", name)
    if not name:
        name = DEFAULT_PREFIX
    if name[0].isdigit():
        name = "_" + name
    return name


def _dedupe_target_names(names):
    used = set()
    unique = []
    for name in names:
        base_name = name
        candidate = base_name
        index = 2
        while candidate in used:
            candidate = "{0}_{1}".format(base_name, index)
            index += 1
        used.add(candidate)
        unique.append(candidate)
    return unique


def _short_name(node):
    return node.split("|")[-1].split(":")[-1]


def _unique_name(base_name):
    if not cmds.objExists(base_name):
        return base_name

    index = 1
    while cmds.objExists("{0}{1}".format(base_name, index)):
        index += 1
    return "{0}{1}".format(base_name, index)


def _ensure_bool_attr(node, attr):
    if not cmds.objExists("{0}.{1}".format(node, attr)):
        cmds.addAttr(node, longName=attr, attributeType="bool")


def _ensure_long_attr(node, attr):
    if not cmds.objExists("{0}.{1}".format(node, attr)):
        cmds.addAttr(node, longName=attr, attributeType="long")


def _ensure_string_attr(node, attr):
    if not cmds.objExists("{0}.{1}".format(node, attr)):
        cmds.addAttr(node, longName=attr, dataType="string")


def _read_string_attr(node, attr):
    full_attr = "{0}.{1}".format(node, attr)
    if not cmds.objExists(full_attr):
        return ""
    return cmds.getAttr(full_attr) or ""


def _read_numeric_attr(node, attr, default):
    full_attr = "{0}.{1}".format(node, attr)
    if not cmds.objExists(full_attr):
        return default
    value = cmds.getAttr(full_attr)
    return default if value is None else value
