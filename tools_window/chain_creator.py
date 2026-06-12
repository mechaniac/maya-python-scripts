import maya.cmds as cmds

import maya_display


MIN_LINKS = 3
MAX_LINKS = 240
DEFAULT_ALTERNATE_ROLL = 90.0
DEFAULT_LINK_SCALE = 2.0
MIN_LINK_SCALE = 0.01
MAX_LINK_SCALE = 20.0
MOTION_PATH_VECTOR_UP = 3
FRONT_AXIS = "x"
ROLL_ATTR = "rotateX"
MANAGED_ATTR = "cChainCreator"
NODE_LINK_ATTR = "chainNodes"
ALT_ROLL_TARGET_ATTR = "chainAltRollTarget"
LINKS_ROOT_ATTR = "linksRoot"
LIVE_PATH_ATTR = "livePathCurve"
PREFIX_ATTR = "chainPrefix"

_LAST_CHAIN_GROUP = None


def create_from_selection(
    count,
    alternate_roll=DEFAULT_ALTERNATE_ROLL,
    selection=None,
    link_scale=DEFAULT_LINK_SCALE,
):
    """Create a live chain from the selected polygon mesh and curve."""
    link, curve = selected_link_and_curve(selection)
    if not link or not curve:
        cmds.warning("Select one polygon mesh link and one curve path.")
        return None
    return create_chain(link, curve, count, alternate_roll, link_scale)


def create_chain(
    link,
    curve,
    count,
    alternate_roll=DEFAULT_ALTERNATE_ROLL,
    link_scale=DEFAULT_LINK_SCALE,
):
    """Build a closed, live chain setup driven by Maya dependency nodes."""
    maya_display.ensure_display_affected()
    count = _bounded_link_count(count)
    alternate_roll = _clamp(float(alternate_roll), 0.0, 360.0)
    link_scale = _bounded_link_scale(link_scale)
    link = _as_transform(link)
    curve = _as_transform(curve)

    if not link or not _shape_of_type(link, "mesh"):
        cmds.warning("Chain link must be a polygon mesh transform.")
        return None
    if not curve or not _shape_of_type(curve, "nurbsCurve"):
        cmds.warning("Chain path must be a nurbs curve transform.")
        return None

    original_selection = cmds.ls(selection=True, long=True) or []
    root = None
    cmds.undoInfo(openChunk=True, chunkName="Create Live Chain")
    try:
        source_length = _axis_length_from_bbox(link, FRONT_AXIS)
        prefix = _clean_name("chain_{0}_{1}".format(
            _node_label(link),
            _node_label(curve),
        ))

        root = _create_transform(prefix + "_GRP")
        driver_nodes = _drive_root_from_curve(root, curve, prefix)
        links_root = _create_transform(prefix + "_links_GRP", parent=root)
        _tag_chain(
            root,
            link,
            curve,
            count,
            alternate_roll,
            source_length,
            link_scale,
        )
        _set_string_attr(root, LINKS_ROOT_ATTR, links_root)
        _set_string_attr(root, PREFIX_ATTR, prefix)

        path_curve, curve_shape, path_nodes = _live_closed_path(
            curve, root, prefix)
        _set_string_attr(root, LIVE_PATH_ATTR, path_curve)

        scale_output, scale_nodes = _create_scale_network(
            root, curve_shape, count, source_length, prefix)
        network_nodes = list(driver_nodes) + list(path_nodes) + list(scale_nodes)

        for index in range(count):
            nodes = _create_live_link(
                link=link,
                curve_shape=curve_shape,
                links_root=links_root,
                scale_output=scale_output,
                root=root,
                prefix=prefix,
                index=index,
                count=count,
            )
            network_nodes.extend(nodes)

        _register_nodes(root, network_nodes)
        _set_active_chain(root)
        print("Created live chain '{0}' with {1} links.".format(root, count))
        return root
    except Exception:
        if root and cmds.objExists(root):
            try:
                cmds.delete(root)
            except Exception:
                pass
        raise
    finally:
        _restore_selection(original_selection)
        cmds.undoInfo(closeChunk=True)


def set_alternate_roll(value, chain_group=None):
    """Set the roll angle used by every second link."""
    chain_group = chain_group or active_chain()
    if not chain_group:
        return None
    value = _clamp(float(value), 0.0, 360.0)
    if cmds.objExists(chain_group + ".alternateRoll"):
        cmds.setAttr(chain_group + ".alternateRoll", value)
    applied = _apply_alternate_roll_to_links(chain_group, value)
    if not applied:
        rebuild_chain(chain_group, alternate_roll=value)
    _set_active_chain(chain_group)
    return chain_group


def set_link_scale(value, chain_group=None):
    """Set the live link scale multiplier used to interlink chain links."""
    chain_group = chain_group or active_chain()
    if not chain_group:
        return None
    value = _bounded_link_scale(value)
    _ensure_numeric_attr(
        chain_group,
        "linkScaleMultiplier",
        "double",
        DEFAULT_LINK_SCALE,
        keyable=True,
    )
    cmds.setAttr(chain_group + ".linkScaleMultiplier", value)
    _set_active_chain(chain_group)
    return chain_group


def set_link_count(value, chain_group=None):
    """Rebuild the active chain with a new link count."""
    chain_group = chain_group or active_chain()
    if not chain_group:
        return None
    count = _bounded_link_count(value)
    rebuild_chain(chain_group, count=count)
    return chain_group


def rebuild_chain(chain_group, count=None, alternate_roll=None):
    """Recreate the generated links while preserving the path setup."""
    maya_display.ensure_display_affected()
    chain_group = _as_transform(chain_group)
    if not chain_group or not cmds.objExists(chain_group):
        return None
    if not cmds.attributeQuery(MANAGED_ATTR, node=chain_group, exists=True):
        cmds.warning("{0} is not a managed chain.".format(chain_group))
        return None

    count = _bounded_link_count(
        count if count is not None else _get_numeric_attr(
            chain_group, "linkCount", MIN_LINKS))
    if alternate_roll is None:
        alternate_roll = _get_numeric_attr(
            chain_group,
            "alternateRoll",
            DEFAULT_ALTERNATE_ROLL,
        )
    alternate_roll = _clamp(float(alternate_roll), 0.0, 360.0)

    link = _get_string_attr(chain_group, "sourceLink")
    if not link or not cmds.objExists(link):
        cmds.warning("Original chain link mesh is missing.")
        return None

    source_curve = _get_string_attr(chain_group, "pathCurve")
    source_curve = _as_transform(source_curve)
    if source_curve and cmds.objExists(source_curve):
        chain_group = _unparent_to_world(chain_group)

    path_curve = _chain_path_curve(chain_group)
    curve_shape = _shape_of_type(path_curve, "nurbsCurve") if path_curve else None
    if not curve_shape:
        cmds.warning("Chain path curve is missing.")
        return None

    prefix = _get_string_attr(chain_group, PREFIX_ATTR) or _node_label(chain_group)
    source_length = _get_numeric_attr(chain_group, "sourceAxisLength", 1.0)

    cmds.undoInfo(openChunk=True, chunkName="Rebuild Live Chain")
    try:
        _delete_generated_link_nodes(chain_group)
        driver_nodes = []
        if source_curve and cmds.objExists(source_curve):
            driver_nodes = _drive_root_from_curve(
                chain_group,
                source_curve,
                prefix,
            )
        links_root = _create_transform(prefix + "_links_GRP", parent=chain_group)
        _set_string_attr(chain_group, LINKS_ROOT_ATTR, links_root)
        _set_numeric_attr(chain_group, "linkCount", count)
        _set_numeric_attr(chain_group, "alternateRoll", alternate_roll)
        _ensure_numeric_attr(
            chain_group,
            "linkScaleMultiplier",
            "double",
            DEFAULT_LINK_SCALE,
            keyable=True,
        )

        scale_output, scale_nodes = _create_scale_network(
            chain_group, curve_shape, count, source_length, prefix)
        network_nodes = list(driver_nodes) + list(scale_nodes)

        for index in range(count):
            nodes = _create_live_link(
                link=link,
                curve_shape=curve_shape,
                links_root=links_root,
                scale_output=scale_output,
                root=chain_group,
                prefix=prefix,
                index=index,
                count=count,
            )
            network_nodes.extend(nodes)

        _register_nodes(chain_group, network_nodes)
        _apply_alternate_roll_to_links(chain_group, alternate_roll)
        _set_active_chain(chain_group)
        return chain_group
    finally:
        cmds.undoInfo(closeChunk=True)


def delete_active_chain():
    chain_group = active_chain()
    if not chain_group:
        cmds.warning("No live chain setup found.")
        return False
    return delete_chain(chain_group)


def delete_chain(chain_group):
    """Delete a generated chain and its helper dependency nodes."""
    global _LAST_CHAIN_GROUP
    if not chain_group or not cmds.objExists(chain_group):
        return False

    helper_nodes = _registered_nodes(chain_group)
    cmds.delete(chain_group)

    leftovers = [node for node in helper_nodes if cmds.objExists(node)]
    if leftovers:
        cmds.delete(leftovers)

    if _LAST_CHAIN_GROUP == chain_group:
        _LAST_CHAIN_GROUP = None
    print("Deleted live chain '{0}'.".format(chain_group))
    return True


def selected_link_and_curve(selection=None):
    """Return the first selected mesh transform and curve transform."""
    selection = selection or cmds.ls(selection=True, long=True) or []
    link = None
    curve = None

    for item in selection:
        transform = _as_transform(item)
        if not transform:
            continue
        if link is None and _shape_of_type(transform, "mesh"):
            link = transform
        if curve is None and _shape_of_type(transform, "nurbsCurve"):
            curve = transform
        if link and curve:
            break

    return link, curve


def active_chain():
    """Find the current generated chain, preferring selection and last create."""
    selected = cmds.ls(selection=True, long=True) or []
    for item in selected:
        transform = _as_transform(item)
        found = _managed_ancestor(transform)
        if found:
            return found

    if _LAST_CHAIN_GROUP and cmds.objExists(_LAST_CHAIN_GROUP):
        return _LAST_CHAIN_GROUP

    groups = chain_groups()
    return groups[-1] if groups else None


def chain_groups():
    transforms = cmds.ls(type="transform", long=True) or []
    return [
        node for node in transforms
        if cmds.attributeQuery(MANAGED_ATTR, node=node, exists=True)
    ]


def chain_label(chain_group):
    return _node_label(chain_group)


def chain_settings(chain_group=None):
    chain_group = chain_group or active_chain()
    if not chain_group or not cmds.objExists(chain_group):
        return {}
    return {
        "link_count": int(_get_numeric_attr(chain_group, "linkCount", MIN_LINKS)),
        "alternate_roll": float(_get_numeric_attr(
            chain_group, "alternateRoll", DEFAULT_ALTERNATE_ROLL)),
        "link_scale": float(_get_numeric_attr(
            chain_group, "linkScaleMultiplier", DEFAULT_LINK_SCALE)),
    }


def refresh_chain_orientation(chain_group=None):
    """Make existing chain roots and motion paths use curve-local space."""
    maya_display.ensure_display_affected()
    chain_group = chain_group or active_chain()
    chain_group = _as_transform(chain_group)
    if not chain_group or not cmds.objExists(chain_group):
        return 0

    source_curve = _chain_source_curve(chain_group)
    if source_curve:
        prefix = _get_string_attr(chain_group, PREFIX_ATTR) or _node_label(chain_group)
        chain_group = _unparent_to_world(chain_group)
        driver_nodes = _drive_root_from_curve(chain_group, source_curve, prefix)
        _register_nodes(chain_group, driver_nodes)
        _set_active_chain(chain_group)

    refreshed = 0
    for node in _registered_nodes(chain_group):
        if not node or not cmds.objExists(node):
            continue
        if cmds.nodeType(node) != "motionPath":
            continue
        _safe_set_attr(
            node + ".worldUpType",
            MOTION_PATH_VECTOR_UP,
        )
        try:
            cmds.setAttr(node + ".worldUpVector", 0.0, 1.0, 0.0)
        except Exception:
            pass
        _disconnect_motion_path_up_object(node)
        refreshed += 1
    return refreshed


def set_active_chain(chain_group):
    chain_group = _as_transform(chain_group)
    if chain_group and cmds.objExists(chain_group):
        _set_active_chain(chain_group)
        return chain_group
    return None


def _create_live_link(link, curve_shape, links_root, scale_output,
                      root, prefix, index, count):
    u_value = index / float(count)
    path_group = _create_transform(
        "{0}_{1:03d}_path_GRP".format(prefix, index + 1),
        parent=links_root,
    )
    roll_group = _create_transform(
        "{0}_{1:03d}_roll_GRP".format(prefix, index + 1),
        parent=path_group,
    )

    instance = cmds.instance(
        link,
        name="{0}_{1:03d}_link".format(prefix, index + 1),
    )[0]
    instance = cmds.parent(instance, roll_group)[0]
    _zero_local_transform(instance)

    for axis in ("X", "Y", "Z"):
        cmds.connectAttr(scale_output, instance + ".scale" + axis, force=True)

    if index % 2:
        _tag_alt_roll_target(roll_group)
        _safe_set_attr(roll_group + "." + ROLL_ATTR,
                       _get_numeric_attr(
                           root,
                           "alternateRoll",
                           DEFAULT_ALTERNATE_ROLL,
                       ))

    motion_path = _create_motion_path(
        curve_shape=curve_shape,
        target=path_group,
        u_value=u_value,
        name="{0}_{1:03d}_motionPath".format(prefix, index + 1),
    )
    return [motion_path]


def _create_motion_path(curve_shape, target, u_value, name):
    motion_path = cmds.createNode("motionPath", name=name)
    cmds.setAttr(motion_path + ".uValue", u_value)
    cmds.setAttr(motion_path + ".fractionMode", True)
    cmds.setAttr(motion_path + ".follow", True)
    cmds.setAttr(motion_path + ".frontAxis", 0)
    cmds.setAttr(motion_path + ".upAxis", 1)
    cmds.setAttr(motion_path + ".worldUpVector", 0.0, 1.0, 0.0)

    _safe_set_attr(
        motion_path + ".worldUpType",
        MOTION_PATH_VECTOR_UP,
    )
    cmds.connectAttr(_curve_output_attr(curve_shape),
                     motion_path + ".geometryPath",
                     force=True)
    _connect_vector(motion_path + ".allCoordinates", target + ".translate")
    _connect_vector(motion_path + ".rotate", target + ".rotate")
    return motion_path


def _create_scale_network(root, curve_shape, count, source_length, prefix):
    curve_info = cmds.createNode("curveInfo", name=prefix + "_curveInfo")
    divider = cmds.createNode("multiplyDivide", name=prefix + "_scaleDivide")
    multiplier = cmds.createNode("multDoubleLinear",
                                 name=prefix + "_scaleMultiplier")

    cmds.connectAttr(_curve_output_attr(curve_shape),
                     curve_info + ".inputCurve",
                     force=True)
    cmds.setAttr(divider + ".operation", 2)
    cmds.connectAttr(curve_info + ".arcLength",
                     divider + ".input1X",
                     force=True)
    cmds.setAttr(divider + ".input2X", max(0.001, source_length * count))
    cmds.connectAttr(divider + ".outputX", multiplier + ".input1", force=True)
    cmds.connectAttr(root + ".linkScaleMultiplier",
                     multiplier + ".input2",
                     force=True)
    return multiplier + ".output", [curve_info, divider, multiplier]


def _tag_chain(root, link, curve, count, alternate_roll,
               source_length, link_scale):
    cmds.addAttr(root, longName=MANAGED_ATTR, attributeType="bool")
    cmds.setAttr(root + "." + MANAGED_ATTR, True)
    cmds.addAttr(root, longName=NODE_LINK_ATTR, attributeType="message",
                 multi=True)

    _add_numeric_attr(root, "linkCount", "long", count)
    _add_numeric_attr(root, "sourceAxisLength", "double", source_length)
    _add_numeric_attr(
        root,
        "linkScaleMultiplier",
        "double",
        link_scale,
        keyable=True,
    )
    _add_numeric_attr(root, "alternateRoll", "double", alternate_roll,
                      keyable=True)
    _set_string_attr(root, "sourceLink", link)
    _set_string_attr(root, "pathCurve", curve)


def _register_nodes(root, nodes):
    for node in nodes:
        if not node or not cmds.objExists(node):
            continue
        index = _next_multi_index(root + "." + NODE_LINK_ATTR)
        try:
            cmds.connectAttr(node + ".message",
                             "{0}.{1}[{2}]".format(root, NODE_LINK_ATTR, index),
                             force=True)
        except Exception:
            pass


def _registered_nodes(root):
    attr = root + "." + NODE_LINK_ATTR
    if not cmds.objExists(attr):
        return []
    return cmds.listConnections(attr, source=True, destination=False) or []


def _delete_generated_link_nodes(root):
    links_root = _get_string_attr(root, LINKS_ROOT_ATTR)
    link_roots = []
    if links_root and cmds.objExists(links_root):
        link_roots.append(links_root)
    else:
        link_roots.extend(_discover_link_roots(root))
    if link_roots:
        cmds.delete(link_roots)

    volatile = []
    for node in _registered_nodes(root):
        if not cmds.objExists(node):
            continue
        if cmds.nodeType(node) in ("motionPath", "curveInfo",
                                   "multiplyDivide", "multDoubleLinear"):
            volatile.append(node)
    if volatile:
        cmds.delete(volatile)


def _discover_link_roots(root):
    children = cmds.listRelatives(
        root,
        children=True,
        type="transform",
        fullPath=True,
    ) or []
    return [
        child for child in children
        if _node_label(child).endswith("_links_GRP")
    ]


def _next_multi_index(attr):
    indices = cmds.getAttr(attr, multiIndices=True) or []
    return (max(indices) + 1) if indices else 0


def _live_closed_path(curve, root, prefix):
    curve_shape = _shape_of_type(curve, "nurbsCurve")
    if _curve_is_closed(curve_shape):
        return curve, curve_shape, []

    try:
        result = cmds.closeCurve(
            curve,
            constructionHistory=True,
            preserveShape=True,
            replaceOriginal=False,
            name=prefix + "_closedPath",
        )
    except Exception as exc:
        cmds.warning("Could not close chain curve: {0}".format(exc))
        return curve, curve_shape, []

    path_curve = _first_curve_transform(result)
    if not path_curve:
        cmds.warning("Could not build a closed live chain path.")
        return curve, curve_shape, []

    path_curve = cmds.parent(path_curve, root)[0]
    _safe_set_attr(path_curve + ".visibility", False)
    path_shape = _shape_of_type(path_curve, "nurbsCurve") or curve_shape
    history = _generated_history(path_curve, curve)
    return path_curve, path_shape, [path_curve] + history


def _first_curve_transform(nodes):
    if not isinstance(nodes, (list, tuple)):
        nodes = [nodes]
    for node in nodes:
        transform = _as_transform(node)
        if transform and _shape_of_type(transform, "nurbsCurve"):
            return transform
    return None


def _generated_history(path_curve, source_curve):
    source_shape = _shape_of_type(source_curve, "nurbsCurve")
    source_nodes = set([source_curve, source_shape])
    history = cmds.listHistory(path_curve, pruneDagObjects=True) or []
    return [
        node for node in history
        if node not in source_nodes and cmds.nodeType(node) != "nurbsCurve"
    ]


def _chain_path_curve(root):
    for attr in (LIVE_PATH_ATTR, "pathCurve"):
        value = _get_string_attr(root, attr)
        if value and cmds.objExists(value) and _shape_of_type(value, "nurbsCurve"):
            return value

    for node in _registered_nodes(root):
        transform = _as_transform(node)
        if transform and _shape_of_type(transform, "nurbsCurve"):
            return transform
    return None


def _chain_source_curve(root):
    curve = _get_string_attr(root, "pathCurve")
    curve = _as_transform(curve)
    if curve and cmds.objExists(curve):
        return curve
    return None


def _curve_is_closed(curve_shape):
    try:
        return int(cmds.getAttr(curve_shape + ".form")) in (1, 2)
    except Exception:
        return False


def _shape_of_type(transform, shape_type):
    if not transform or not cmds.objExists(transform):
        return None
    shapes = cmds.listRelatives(
        transform,
        shapes=True,
        fullPath=True,
        noIntermediate=True,
    ) or []
    if not shapes:
        shapes = cmds.listRelatives(transform, shapes=True, fullPath=True) or []
    for shape in shapes:
        if cmds.nodeType(shape) == shape_type:
            return shape
    return None


def _as_transform(node):
    if not node:
        return None
    node = node.split(".", 1)[0]
    if not cmds.objExists(node):
        return None
    if cmds.nodeType(node) == "transform":
        return node
    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    return parents[0] if parents else None


def _managed_ancestor(transform):
    current = transform
    while current and cmds.objExists(current):
        if cmds.attributeQuery(MANAGED_ATTR, node=current, exists=True):
            return current
        parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
        current = parents[0] if parents else None
    return None


def _axis_length_from_bbox(transform, axis):
    bbox = cmds.exactWorldBoundingBox(transform)
    lengths = {
        "x": bbox[3] - bbox[0],
        "y": bbox[4] - bbox[1],
        "z": bbox[5] - bbox[2],
    }
    return max(0.001, lengths.get(axis, lengths["x"]))


def _create_transform(name, parent=None):
    kwargs = {"name": name}
    if parent:
        kwargs["parent"] = parent
    return cmds.createNode("transform", **kwargs)


def _drive_root_from_curve(root, curve, prefix):
    root = _as_transform(root)
    curve = _as_transform(curve)
    if not root or not curve or _same_node(root, curve):
        return []
    if _is_descendant(curve, root):
        cmds.warning("Cannot parent a chain root under its own path curve.")
        return []

    root = _unparent_to_world(root)
    _remove_root_driver_constraints(root)
    _match_world_matrix(root, curve)

    constraints = []
    try:
        constraints.extend(cmds.parentConstraint(
            curve,
            root,
            maintainOffset=False,
            name=prefix + "_root_parentConstraint",
        ) or [])
    except Exception as exc:
        cmds.warning("Could not parent constrain chain root: {0}".format(exc))

    try:
        constraints.extend(cmds.scaleConstraint(
            curve,
            root,
            maintainOffset=False,
            name=prefix + "_root_scaleConstraint",
        ) or [])
    except Exception:
        pass

    return [_long_name(node) for node in constraints if cmds.objExists(node)]


def _unparent_to_world(transform):
    transform = _as_transform(transform)
    if not transform:
        return transform
    parents = cmds.listRelatives(transform, parent=True, fullPath=True) or []
    if not parents:
        return _long_name(transform)
    try:
        unparented = cmds.parent(transform, world=True)[0]
        return _long_name(unparented)
    except Exception:
        return _long_name(transform)


def _match_world_matrix(target, source):
    try:
        matrix = cmds.xform(source, query=True, matrix=True, worldSpace=True)
        cmds.xform(target, matrix=matrix, worldSpace=True)
    except Exception:
        pass


def _remove_root_driver_constraints(root):
    constraint_types = ("parentConstraint", "scaleConstraint")
    to_delete = []

    for constraint_type in constraint_types:
        to_delete.extend(cmds.listRelatives(
            root,
            children=True,
            type=constraint_type,
            fullPath=True,
        ) or [])
        to_delete.extend(cmds.listConnections(
            root,
            source=True,
            destination=False,
            type=constraint_type,
        ) or [])

    to_delete = list(dict.fromkeys(
        node for node in to_delete
        if node and cmds.objExists(node)
    ))
    if to_delete:
        try:
            cmds.delete(to_delete)
        except Exception:
            pass


def _curve_output_attr(curve_shape):
    try:
        if cmds.attributeQuery("local", node=curve_shape, exists=True):
            return curve_shape + ".local"
    except Exception:
        pass
    return curve_shape + ".worldSpace[0]"


def _disconnect_motion_path_up_object(motion_path):
    attr = motion_path + ".worldUpMatrix"
    if not cmds.objExists(attr):
        return
    connections = cmds.listConnections(
        attr,
        source=True,
        destination=False,
        plugs=True,
    ) or []
    for source in connections:
        try:
            cmds.disconnectAttr(source, attr)
        except Exception:
            pass


def _zero_local_transform(transform):
    for attr, values in (
        ("translate", (0.0, 0.0, 0.0)),
        ("rotate", (0.0, 0.0, 0.0)),
    ):
        try:
            cmds.setAttr(transform + "." + attr, *values)
        except Exception:
            pass


def _connect_vector(source, destination):
    try:
        cmds.connectAttr(source, destination, force=True)
        return
    except Exception:
        pass

    for axis in ("X", "Y", "Z"):
        cmds.connectAttr(source + axis, destination + axis, force=True)


def _add_numeric_attr(node, name, attr_type, value, keyable=False):
    cmds.addAttr(node, longName=name, attributeType=attr_type,
                 defaultValue=value, keyable=keyable)
    cmds.setAttr(node + "." + name, value)


def _ensure_numeric_attr(node, name, attr_type, value, keyable=False):
    if not cmds.attributeQuery(name, node=node, exists=True):
        _add_numeric_attr(node, name, attr_type, value, keyable=keyable)


def _set_string_attr(node, name, value):
    if not cmds.attributeQuery(name, node=node, exists=True):
        cmds.addAttr(node, longName=name, dataType="string")
    cmds.setAttr(node + "." + name, value or "", type="string")


def _get_string_attr(node, name):
    if not node or not cmds.objExists(node + "." + name):
        return ""
    try:
        return cmds.getAttr(node + "." + name) or ""
    except Exception:
        return ""


def _get_numeric_attr(node, name, default):
    if not node or not cmds.objExists(node + "." + name):
        return default
    try:
        return cmds.getAttr(node + "." + name)
    except Exception:
        return default


def _set_numeric_attr(node, name, value):
    if not node or not cmds.objExists(node + "." + name):
        return
    try:
        cmds.setAttr(node + "." + name, value)
    except Exception:
        pass


def _safe_set_attr(attr, value):
    try:
        cmds.setAttr(attr, value)
    except Exception:
        pass


def _tag_alt_roll_target(transform):
    try:
        if not cmds.attributeQuery(ALT_ROLL_TARGET_ATTR,
                                   node=transform,
                                   exists=True):
            cmds.addAttr(transform,
                         longName=ALT_ROLL_TARGET_ATTR,
                         attributeType="bool")
        cmds.setAttr(transform + "." + ALT_ROLL_TARGET_ATTR, True)
    except Exception:
        pass


def _apply_alternate_roll_to_links(root, value):
    links_root = _get_string_attr(root, LINKS_ROOT_ATTR)
    if not links_root or not cmds.objExists(links_root):
        return 0
    applied = 0
    descendants = cmds.listRelatives(
        links_root,
        allDescendents=True,
        type="transform",
        fullPath=True,
    ) or []
    for node in descendants:
        if not cmds.objExists(node + "." + ALT_ROLL_TARGET_ATTR):
            continue
        if not cmds.getAttr(node + "." + ALT_ROLL_TARGET_ATTR):
            continue
        _safe_set_attr(node + "." + ROLL_ATTR, value)
        applied += 1
    return applied


def _set_active_chain(chain_group):
    global _LAST_CHAIN_GROUP
    _LAST_CHAIN_GROUP = chain_group


def _restore_selection(selection):
    if selection:
        existing = [node for node in selection if cmds.objExists(node)]
        if existing:
            cmds.select(existing, replace=True)
            return
    cmds.select(clear=True)


def _clean_name(value):
    cleaned = "".join(
        char if char.isalnum() or char == "_" else "_"
        for char in str(value)
    ).strip("_")
    return cleaned or "chain"


def _node_label(node):
    return str(node).split("|")[-1].split(":")[-1]


def _long_name(node):
    matches = cmds.ls(node, long=True) or []
    return matches[0] if matches else node


def _same_node(first, second):
    return _long_name(first) == _long_name(second)


def _is_descendant(node, possible_parent):
    current = _as_transform(node)
    target = _long_name(possible_parent)
    while current and cmds.objExists(current):
        if _long_name(current) == target:
            return True
        parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
        current = parents[0] if parents else None
    return False


def _clamp(value, low, high):
    return max(low, min(high, value))


def _bounded_link_count(count):
    count = max(MIN_LINKS, int(count))
    if count > MAX_LINKS:
        cmds.warning(
            "Chain link count capped at {0} for viewport stability.".format(
                MAX_LINKS))
        count = MAX_LINKS
    return count


def _bounded_link_scale(value):
    return _clamp(float(value), MIN_LINK_SCALE, MAX_LINK_SCALE)
