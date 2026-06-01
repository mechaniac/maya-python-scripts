"""Logic for building synchronized multi-object blendshape edit sets."""

import re

import maya.cmds as cmds
import maya.mel as mel


MANAGED_ATTR = "cbsManaged"
TARGETS_ATTR = "cbsTargets"
START_ATTR = "cbsStartFrame"
INTERVAL_ATTR = "cbsInterval"
COUNT_ATTR = "cbsTargetCount"
TRANSFORM_KEYS_ATTR = "cbsTransformKeysManaged"
TRANSFORM_FRAMES_ATTR = "cbsTransformKeyFrames"
KEY_GROUP_ROOT_ATTR = "cbsKeyGroupRootManaged"
KEY_GROUP_MANAGED_ATTR = "cbsKeyGroupManaged"
KEY_GROUP_INDEX_ATTR = "cbsKeyGroupIndex"
KEY_GROUP_TARGET_ATTR = "cbsKeyGroupTarget"
WRAP_MANAGED_ATTR = "cbsWrapManaged"
WRAP_DRIVER_ATTR = "cbsWrapDriver"
WRAP_TARGET_ATTR = "cbsWrapTarget"
WRAP_MAX_DISTANCE_ATTR = "cbsWrapMaxDistance"
HELPER_MANAGED_ATTR = "cbsHelperManaged"
HELPER_ROLE_ATTR = "cbsHelperRole"
HELPER_OWNER_ATTR = "cbsHelperOwner"
WIRE_PROXY_MANAGED_ATTR = "cbsWireProxyManaged"
WIRE_PROXY_OWNER_ATTR = "cbsWireProxyOwner"
TEMP_TARGET_MANAGED_ATTR = "cbsTempTargetManaged"

DEFAULT_PREFIX = "blendShape"
KEY_GROUP_ROOT = "BlendshapeKeyGroups"
KEY_GROUP_BIND_POSE = "BindPose"
TEMPLATE_ROOT = "BlendshapeRoster"
TEMPLATE_MESHES = "Meshes"
TEMPLATE_WRAP = "WRAPExample"
TEMPLATE_WRAP_TARGET = "WRAPTarget"
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
DEFAULT_WRAP_MAX_DISTANCE = 6.0
TRANSFORM_KEY_ATTRS = (
    "translateX",
    "translateY",
    "translateZ",
    "rotateX",
    "rotateY",
    "rotateZ",
    "scaleX",
    "scaleY",
    "scaleZ",
)
DISPLAY_OVERRIDE_ATTRS = (
    "overrideEnabled",
    "overrideDisplayType",
    "overrideShading",
    "overrideTexturing",
    "displayEdges",
)
DISPLAY_LOCK_ATTRS = DISPLAY_OVERRIDE_ATTRS
POLY_DISPLAY_OPTION_FLAGS = ("displayGeometry",)
WRAP_DRIVER_RENDER_ATTRS = (
    "castsShadows",
    "receiveShadows",
    "motionBlur",
    "primaryVisibility",
    "smoothShading",
    "visibleInReflections",
    "visibleInRefractions",
)
WRAP_INFLUENCE_ATTRS = (
    "dropoff",
    "smoothness",
    "inflType",
)
WIRE_TEST_METHODS = (
    {
        "id": "poly_geometry_off",
        "label": "Poly Geometry Off",
        "tooltip": "Runs polyOptions displayGeometry=False and allEdges=True on the selected polygon meshes.",
    },
    {
        "id": "override_no_shading",
        "label": "Override No Shading",
        "tooltip": "Enables draw overrides and disables overrideShading/overrideTexturing on selected mesh transforms and shapes.",
    },
    {
        "id": "template_override",
        "label": "Template Override",
        "tooltip": "Sets overrideDisplayType to Template on selected mesh transforms and shapes.",
    },
    {
        "id": "reference_override",
        "label": "Reference Override",
        "tooltip": "Sets overrideDisplayType to Reference on selected mesh transforms and shapes.",
    },
    {
        "id": "hide_shape",
        "label": "Hide Mesh Shape",
        "tooltip": "Turns selected mesh shape visibility off. This is the direct no-draw test, but it will not show wire by itself.",
    },
    {
        "id": "curve_proxy",
        "label": "Curve Proxy + Hide",
        "tooltip": "Creates curve wires from selected mesh edges, then hides the original mesh shape. Use Undo or Reset Wire Tests to remove proxies.",
    },
)


def selected_mesh_transforms():
    """Return selected or descendant transforms with polygon mesh shapes."""
    selection = cmds.ls(selection=True, long=True) or []
    transforms = []
    seen = set()

    for item in selection:
        for transform in _mesh_transforms_under(item):
            _append_unique(transforms, seen, transform)

    return transforms


def selected_transform_nodes():
    """Return selected/descendant transforms plus mesh parent groups."""
    selection = cmds.ls(selection=True, long=True) or []
    transforms = []
    seen = set()

    for item in selection:
        for transform in _transform_nodes_under(item):
            _append_unique(transforms, seen, transform)

    for mesh in selected_mesh_transforms():
        for group in _mesh_group_ancestors(mesh):
            _append_unique(transforms, seen, group)

    return transforms


def generate_setup(target_count=DEFAULT_TARGET_COUNT,
                   name_prefix=DEFAULT_PREFIX,
                   target_names=None,
                   start_frame=DEFAULT_START_FRAME,
                   interval=DEFAULT_INTERVAL,
                   replace_existing=True,
                   open_editor=True,
                   wrap_max_distance=DEFAULT_WRAP_MAX_DISTANCE):
    """Create managed blendShape deformers and keyed targets on selection."""
    if generated_setup_exists():
        raise RuntimeError(
            "Remove the existing generated setup before generating a new one."
        )

    meshes = selected_mesh_transforms()
    transform_nodes = selected_transform_nodes()
    if not meshes:
        raise RuntimeError("Select one or more polygon mesh transforms.")

    target_count = int(target_count)
    start_frame = int(start_frame)
    interval = int(interval)
    wrap_max_distance = float(wrap_max_distance)

    if target_count < 1:
        raise RuntimeError("Target count must be at least 1.")
    if interval < 1:
        raise RuntimeError("Frame interval must be at least 1.")
    if wrap_max_distance < 0:
        raise RuntimeError("Wrap max distance must be 0 or greater.")

    target_names = build_target_names(
        target_count=target_count,
        name_prefix=name_prefix,
        target_names=target_names,
    )
    target_count = len(target_names)
    wrap_links = discover_wrap_links(meshes)
    meshes = _with_wrap_target_meshes(meshes, wrap_links)
    transform_nodes = _with_wrap_target_meshes(transform_nodes, wrap_links)
    records = []
    wrap_records = []

    cmds.undoInfo(openChunk=True)
    try:
        for mesh in meshes:
            existing = managed_blendshape_for_mesh(mesh)
            if existing and replace_existing:
                cmds.delete(existing)
                existing = None

            node = existing or _create_blendshape_node(mesh, target_count)
            _configure_targets(node, mesh, target_names)
            _write_metadata(node, target_names, start_frame, interval)
            _key_targets(node, target_names, start_frame, interval)
            records.append({
                "mesh": mesh,
                "node": node,
                "targets": list(target_names),
                "start_frame": start_frame,
                "interval": interval,
            })

        wrap_records = create_wrap_deformers(
            wrap_links,
            max_distance=wrap_max_distance,
        )
        _key_transform_channels(
            transform_nodes,
            target_count,
            start_frame,
            interval,
        )
        _delete_temporary_target_meshes()

        end_frame = target_frame(target_count - 1, start_frame, interval)
        cmds.playbackOptions(
            min=start_frame,
            max=end_frame,
            animationStartTime=start_frame,
            animationEndTime=end_frame,
        )
        activate_all_off(records=records)
        if open_editor:
            open_blendshape_editor()
    finally:
        cmds.undoInfo(closeChunk=True)

    print("Blendshape setup created: {0} mesh(es), {1} target(s).".format(
        len(records), target_count))
    if wrap_records:
        print("Wrap setup created: {0} wrap deformer(s).".format(
            len(wrap_records)))
    return records


def activate_target(index, records=None, open_editor=False,
                    preserve_selection=True):
    """Set target index active on every managed blendShape and edit it."""
    records = records or discover_setups()
    if not records:
        raise RuntimeError("No managed blendshape setup found.")

    first = records[0]
    targets = first.get("targets", [])
    if index < 0 or index >= len(targets):
        raise RuntimeError("Target index out of range.")

    previous_selection = cmds.ls(selection=True, long=True) or []
    auto_key_state = _set_auto_key_state(False)
    try:
        frame = target_frame(index, first["start_frame"], first["interval"])
        cmds.currentTime(frame, edit=True)
        ensure_transform_keys(records, frame)

        selected_meshes = []
        for record in records:
            node = record["node"]
            if not cmds.objExists(node):
                continue
            if index >= len(record.get("targets", [])):
                continue

            _set_active_weights(node, len(record["targets"]), index)
            mesh = record.get("mesh")
            try:
                _set_sculpt_target(node, index, mesh)
            except Exception as exc:
                cmds.warning("Could not set edit target on {0}: {1}".format(
                    node, exc))

            if mesh and cmds.objExists(mesh):
                selected_meshes.append(mesh)

        if selected_meshes and not preserve_selection:
            cmds.select(selected_meshes, replace=True)

        if open_editor:
            open_blendshape_editor()

        # Direct visibility: no animCurves, no time dependency, no DG
        # eval surprises. The label of the active key group equals the
        # target name; BindPose is shown only by activate_all_off.
        _apply_group_visibility(targets[index])

        _force_viewport_update()
    finally:
        if preserve_selection:
            _restore_selection(previous_selection)
        _set_auto_key_state(auto_key_state)

    print("Editing {0} at frame {1}.".format(targets[index], frame))
    return frame


def activate_all_off(records=None, preserve_selection=True):
    """Set all managed blendShape targets to zero and jump to start frame."""
    records = records or discover_setups()
    if not records:
        raise RuntimeError("No managed blendshape setup found.")

    previous_selection = cmds.ls(selection=True, long=True) or []
    auto_key_state = _set_auto_key_state(False)
    try:
        start_frame = records[0]["start_frame"]
        cmds.currentTime(start_frame, edit=True)
        ensure_transform_keys(records, start_frame)
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
        if meshes and not preserve_selection:
            cmds.select(meshes, replace=True)

        # Direct visibility: show BindPose only.
        _apply_group_visibility(KEY_GROUP_BIND_POSE)

        _force_viewport_update()
    finally:
        if preserve_selection:
            _restore_selection(previous_selection)
        _set_auto_key_state(auto_key_state)

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


def auto_key_enabled():
    """Return True when Maya Auto Key is enabled."""
    try:
        return bool(cmds.autoKeyframe(query=True, state=True))
    except Exception:
        return False


def generated_setup_exists():
    """Return True if this tool has generated blendShapes or wraps."""
    return bool(discover_setups() or discover_wrap_setups()
                or discover_helper_nodes() or discover_transform_key_nodes())


def generate_key_groups(records=None):
    """Create/update a separate keyed visibility group per target button."""
    records = records or discover_setups()
    if not records:
        raise RuntimeError("Generate the blendshape setup first.")

    first = records[0]
    targets = list(first.get("targets") or [])
    if not targets:
        raise RuntimeError("The discovered setup has no blendshape targets.")

    start_frame = int(first.get("start_frame", DEFAULT_START_FRAME))
    interval = int(first.get("interval", DEFAULT_INTERVAL))
    key_items = [(-1, KEY_GROUP_BIND_POSE, all_zero_frame(start_frame))]
    key_items.extend(
        (index, target, target_frame(index, start_frame, interval))
        for index, target in enumerate(targets)
    )

    previous_selection = cmds.ls(selection=True, long=True) or []
    auto_key_state = _set_auto_key_state(False)
    groups = []
    cmds.undoInfo(openChunk=True)
    try:
        root = _ensure_key_group_root()
        _write_key_group_root_metadata(root)
        for index, label, frame in key_items:
            group = _ensure_key_group(root, index, label)
            _write_key_group_metadata(group, index, label)
            _key_key_group_visibility(group, frame, key_items)
            groups.append({
                "index": index,
                "name": label,
                "frame": frame,
                "group": group,
            })
    finally:
        _set_auto_key_state(auto_key_state)
        _restore_selection(previous_selection)
        cmds.undoInfo(closeChunk=True)

    print("Generated key groups under {0}: {1} group(s).".format(
        root,
        len(groups),
    ))
    return {
        "root": root,
        "groups": groups,
    }


def repair_setup():
    """Repair an existing setup whose visibility has drifted out of sync.

    Safe, non-destructive operation for existing scenes:

    1. Clear any keys / direct overrides on per-mesh ``.visibility`` and
       ``.lodVisibility`` under every ``BlendshapeKeyGroups/*`` group, and
       force them to 1. Effective visibility is then governed exclusively
       by the keyed parent-group ``.visibility``.
    2. Also clear ``.visibility`` keys on the shape nodes and force them
       on (shapes hidden directly will not respond to parent visibility).
    3. Re-key every parent key group's ``.visibility`` cleanly via
       :func:`generate_key_groups` (step tangents, single source of truth).
    4. Force a DG dirty + viewport refresh.

    Returns a summary dict with the number of nodes touched. Does not
    re-parent meshes, does not regenerate blendShape nodes, does not
    touch wrap deformers.
    """
    records = discover_setups()
    if not records:
        raise RuntimeError("No managed blendshape setup found in this scene.")

    roots = _key_group_roots()
    if not roots:
        raise RuntimeError(
            "No BlendshapeKeyGroups root found. Run Generate Key Groups first."
        )

    touched_transforms = 0
    touched_shapes = 0
    stripped_curves = 0
    cmds.undoInfo(openChunk=True)
    try:
        for root in roots:
            groups = cmds.listRelatives(
                root,
                children=True,
                type="transform",
                fullPath=True,
            ) or []
            for group in groups:
                # Delete every animCurve on this group's visibility.
                # The curve-driven visibility system was unreliable in
                # Maya 2026 (orphaned time inputs, DG eval refusing to
                # propagate). The replacement is direct setAttr on every
                # Target button click; no curves needed.
                for attr_name in ("visibility", "lodVisibility"):
                    attr = "{0}.{1}".format(group, attr_name)
                    if cmds.objExists(attr):
                        stripped_curves += _strip_anim_curves(attr)

                descendants = cmds.listRelatives(
                    group,
                    allDescendents=True,
                    type="transform",
                    fullPath=True,
                ) or []
                for node in descendants:
                    if _reset_visibility(node):
                        touched_transforms += 1
                    shapes = cmds.listRelatives(
                        node,
                        shapes=True,
                        fullPath=True,
                        noIntermediate=True,
                    ) or []
                    for shape in shapes:
                        if _reset_visibility(shape):
                            touched_shapes += 1

        # Rewrite parent group visibility (now direct setAttr, no curves).
        generate_key_groups(records=records)
    finally:
        cmds.undoInfo(closeChunk=True)

    _force_viewport_update()

    print(
        "Repaired blendshape setup: "
        "reset visibility on {0} transform(s) and {1} shape(s); "
        "stripped {2} stale animCurve(s) from key group visibility; "
        "key group visibility is now direct setAttr (no animation).".format(
            touched_transforms, touched_shapes, stripped_curves,
        )
    )
    return {
        "transforms": touched_transforms,
        "shapes": touched_shapes,
        "stripped_curves": stripped_curves,
    }


def _reset_visibility(node):
    """Clear visibility keys and force visibility/lodVisibility on."""
    changed = False
    for attr_name in ("visibility", "lodVisibility"):
        attr = "{0}.{1}".format(node, attr_name)
        if not cmds.objExists(attr):
            continue
        try:
            if cmds.getAttr(attr, lock=True):
                cmds.setAttr(attr, lock=False)
        except Exception:
            pass
        try:
            cmds.cutKey(attr, clear=True)
        except Exception:
            pass
        try:
            if not bool(cmds.getAttr(attr)):
                cmds.setAttr(attr, True)
                changed = True
        except Exception:
            pass
    return changed


def remove_setup(records=None):
    """Delete managed blendShape and wrap nodes created by this tool."""
    records = records if records is not None else discover_setups()
    if not records:
        records = discover_setups()
    wrap_records = discover_wrap_setups()
    helper_nodes = discover_helper_nodes()
    transform_key_nodes = discover_transform_key_nodes()
    if (not records and not wrap_records and not helper_nodes
            and not transform_key_nodes):
        raise RuntimeError("No managed blendshape setup found.")

    blend_nodes = []
    seen = set()
    for record in records:
        node = record.get("node")
        if node and node not in seen and cmds.objExists(node):
            blend_nodes.append(node)
            seen.add(node)

    wrap_nodes = []
    for record in wrap_records:
        node = record.get("node")
        if node and node not in seen and cmds.objExists(node):
            wrap_nodes.append(node)
            seen.add(node)

    nodes = helper_nodes + wrap_nodes + blend_nodes
    if not nodes and not transform_key_nodes:
        raise RuntimeError("No managed setup nodes exist anymore.")

    cmds.undoInfo(openChunk=True)
    try:
        disable_edit_mode(records=records)
        _clear_transform_keys(records, transform_key_nodes)
        removed_wrap_attrs = _remove_wrap_influence_attrs(wrap_records)
        if nodes:
            cmds.delete(nodes)
    finally:
        cmds.undoInfo(closeChunk=True)

    result = {
        "blendShapes": len(blend_nodes),
        "wraps": len(wrap_nodes),
        "helpers": len(helper_nodes),
        "transformKeyedNodes": len(transform_key_nodes),
        "wrapInfluenceAttrs": removed_wrap_attrs,
        "total": len(nodes),
    }
    print(
        "Removed {0} blendShape node(s), {1} wrap node(s), "
        "{2} helper node(s), transform keys on {3} node(s), "
        "and {4} wrap influence attr(s).".format(
            result["blendShapes"],
            result["wraps"],
            result["helpers"],
            result["transformKeyedNodes"],
            result["wrapInfluenceAttrs"],
        )
    )
    return result


def create_template():
    """Create the preferred group structure for blendShape + wrap work."""
    root = cmds.group(empty=True, name=_unique_name(TEMPLATE_ROOT))
    meshes = cmds.group(empty=True, name=TEMPLATE_MESHES, parent=root)
    wrap_group = cmds.group(empty=True, name=TEMPLATE_WRAP, parent=root)
    wrap_targets = cmds.group(
        empty=True,
        name=TEMPLATE_WRAP_TARGET,
        parent=wrap_group,
    )
    cmds.select(root, replace=True)
    return {
        "root": root,
        "meshes": meshes,
        "wrap_group": wrap_group,
        "wrap_targets": wrap_targets,
    }


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


def discover_wrap_setups():
    """Find wrap nodes created by this tool."""
    records = []
    for node in cmds.ls(type="wrap") or []:
        attr = "{0}.{1}".format(node, WRAP_MANAGED_ATTR)
        if not cmds.objExists(attr) or not cmds.getAttr(attr):
            continue

        records.append({
            "node": node,
            "driver": _read_string_attr(node, WRAP_DRIVER_ATTR),
            "target": _read_string_attr(node, WRAP_TARGET_ATTR),
            "max_distance": _read_numeric_attr(
                node,
                WRAP_MAX_DISTANCE_ATTR,
                DEFAULT_WRAP_MAX_DISTANCE,
            ),
        })

    records.sort(key=lambda record: record["node"])
    return records


def discover_helper_nodes():
    """Find helper DAG nodes created by generated wrap/sculpt operations."""
    nodes = []
    for node in cmds.ls(type="transform", long=True) or []:
        attr = "{0}.{1}".format(node, HELPER_MANAGED_ATTR)
        if cmds.objExists(attr) and cmds.getAttr(attr):
            nodes.append(node)
    nodes.sort()
    return nodes


def discover_transform_key_nodes():
    """Find transform nodes that received generated setup transform keys."""
    nodes = []
    for node in cmds.ls(type="transform", long=True) or []:
        attr = "{0}.{1}".format(node, TRANSFORM_KEYS_ATTR)
        if cmds.objExists(attr) and cmds.getAttr(attr):
            nodes.append(node)
    nodes.sort()
    return nodes


def discover_wrap_links(meshes=None):
    """Return wrap driver/target pairs implied by WRAP*/WRAPTarget groups."""
    meshes = meshes or selected_mesh_transforms()
    links = []
    seen = set()

    for driver in meshes:
        wrap_group = _wrap_group_for_mesh(driver)
        if not wrap_group:
            continue

        target_groups = _wrap_target_groups(wrap_group)
        if not target_groups or _is_under_any(driver, target_groups):
            continue

        for target_group in target_groups:
            for target in _mesh_transforms_under(target_group):
                if target == driver:
                    continue

                key = (_long_name(driver), _long_name(target))
                if key in seen or _has_managed_wrap(driver, target):
                    continue

                links.append({
                    "wrap_group": wrap_group,
                    "target_group": target_group,
                    "driver": driver,
                    "target": target,
                })
                seen.add(key)

    return links


def create_wrap_deformers(links, max_distance=DEFAULT_WRAP_MAX_DISTANCE):
    """Create managed wrap deformers for discovered driver/target pairs."""
    created = []
    max_distance = float(max_distance)
    for link in links:
        try:
            result = _create_wrap_deformer(
                link["driver"],
                link["target"],
                parent_group=link.get("wrap_group"),
            )
        except Exception as exc:
            cmds.warning(
                "Could not create wrap {0} -> {1}: {2}".format(
                    link["driver"],
                    link["target"],
                    exc,
                )
            )
            continue

        owner_node = result["wrap_nodes"][0] if result["wrap_nodes"] else ""
        for helper in result["helpers"]:
            _write_helper_metadata(helper, "wrapBase", owner_node)

        for node in result["wrap_nodes"]:
            _write_wrap_metadata(node, link["driver"], link["target"])
            _configure_wrap_local_influence(node, max_distance)
            _set_wrap_driver_render_influence(link["driver"], False)
            created.append({
                "node": node,
                "driver": link["driver"],
                "target": link["target"],
                "helpers": list(result["helpers"]),
                "max_distance": max_distance,
            })

    return created


def apply_wire_display_test(method_id):
    """Apply one isolated wire/display method to the selected mesh transforms."""
    meshes = selected_mesh_transforms()
    if not meshes:
        raise RuntimeError("Select one or more polygon mesh transforms.")

    methods = {
        "poly_geometry_off": _wire_test_poly_geometry_off,
        "override_no_shading": _wire_test_override_no_shading,
        "template_override": _wire_test_template_override,
        "reference_override": _wire_test_reference_override,
        "hide_shape": _wire_test_hide_shape,
        "curve_proxy": _wire_test_curve_proxy,
    }
    if method_id not in methods:
        raise RuntimeError("Unknown wire display test: {0}".format(method_id))

    cmds.undoInfo(openChunk=True)
    try:
        methods[method_id](meshes)
    finally:
        cmds.undoInfo(closeChunk=True)

    return "Applied {0} to {1} selected mesh(es).".format(
        _wire_test_label(method_id),
        len(meshes),
    )


def reset_wire_display_tests():
    """Reset simple display test edits on the selected mesh transforms."""
    meshes = selected_mesh_transforms()
    if not meshes:
        raise RuntimeError("Select one or more polygon mesh transforms.")

    cmds.undoInfo(openChunk=True)
    try:
        _delete_wire_proxies(meshes)
        _show_mesh_shapes(meshes, True)
        _apply_poly_display_options(meshes, {"displayGeometry": True})
        for mesh in meshes:
            _reset_display_overrides(mesh)
    finally:
        cmds.undoInfo(closeChunk=True)

    return "Reset wire display tests on {0} selected mesh(es).".format(
        len(meshes)
    )


def ensure_transform_keys(records, frame):
    """Ensure all managed mesh transforms have t/r/s keys at frame."""
    meshes = [
        record.get("mesh") for record in records or []
        if record.get("mesh") and cmds.objExists(record.get("mesh"))
    ]
    _set_transform_keys(meshes, [int(frame)])


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


def hide_blendshape_editor():
    """Hide Maya's blendShape/Shape editor windows if they are visible."""
    hidden = 0
    title_tokens = ("Blend Shape", "Shape Editor")
    for window in cmds.lsUI(windows=True) or []:
        try:
            title = cmds.window(window, query=True, title=True) or ""
        except Exception:
            title = ""
        if not any(token in title for token in title_tokens):
            continue
        try:
            cmds.window(window, edit=True, visible=False)
            hidden += 1
        except Exception:
            try:
                cmds.deleteUI(window)
                hidden += 1
            except Exception:
                pass
    return hidden


def _with_wrap_target_meshes(meshes, wrap_links):
    all_meshes = []
    seen = set()
    for mesh in meshes:
        _append_unique(all_meshes, seen, mesh)
    for link in wrap_links:
        _append_unique(all_meshes, seen, link["driver"])
        _append_unique(all_meshes, seen, link["target"])
    return all_meshes


def _set_sculpt_target(node, index, mesh=None):
    before = _transform_snapshot()
    cmds.sculptTarget(node, edit=True, target=index)
    _delete_new_sculpt_helpers(before, node)


def _create_wrap_deformer(driver, target, parent_group=None):
    before = set(cmds.ls(type="wrap") or [])
    target_history_before = set(
        cmds.ls(cmds.listHistory(target) or [], type="wrap") or []
    )
    transform_before = _transform_snapshot()

    previous_selection = cmds.ls(selection=True, long=True) or []
    try:
        cmds.select(clear=True)
        cmds.select(target, add=True)
        cmds.select(driver, add=True)
        mel.eval("CreateWrap;")
    finally:
        if previous_selection:
            cmds.select(previous_selection, replace=True)
        else:
            cmds.select(clear=True)

    after = set(cmds.ls(type="wrap") or [])
    target_history_after = set(
        cmds.ls(cmds.listHistory(target) or [], type="wrap") or []
    )
    nodes = list((after - before) | (target_history_after - target_history_before))
    if not nodes:
        raise RuntimeError("Maya did not create a wrap node.")

    helpers = _new_transforms(transform_before)
    helpers = [
        helper for helper in helpers
        if helper not in {_long_name(driver), _long_name(target)}
    ]
    helpers = _move_helpers_to_parent(helpers, parent_group)

    renamed = []
    for node in nodes:
        desired = "{0}_{1}_cbs_wrap".format(_short_name(target), _short_name(driver))
        try:
            node = cmds.rename(node, _unique_name(desired))
        except Exception:
            pass
        renamed.append(node)
    return {
        "wrap_nodes": renamed,
        "helpers": helpers,
    }


def _transform_snapshot():
    return set(cmds.ls(type="transform", long=True) or [])


def _new_transforms(before):
    after = set(cmds.ls(type="transform", long=True) or [])
    return sorted(after - set(before))


def _delete_new_sculpt_helpers(before, owner_node):
    helpers = _new_transforms(before)
    if not helpers:
        return

    deleted = []
    for helper in helpers:
        if not helper or not cmds.objExists(helper):
            continue
        try:
            cmds.delete(helper)
            deleted.append(helper)
        except Exception as exc:
            cmds.warning("Could not delete sculpt helper {0}: {1}".format(
                helper,
                exc,
            ))

    if deleted:
        cmds.warning(
            "Deleted {0} sculpt helper mesh(es) created by {1}; "
            "the setup keeps only the original selected nodes.".format(
                len(deleted),
                owner_node,
            )
        )


def _helper_parent_for_mesh(mesh):
    if not mesh or not cmds.objExists(mesh):
        return None

    wrap_group = _wrap_group_for_mesh(mesh)
    if wrap_group:
        return wrap_group

    parents = cmds.listRelatives(mesh, parent=True, fullPath=True) or []
    return parents[0] if parents else None


def _move_helpers_to_parent(helpers, parent):
    moved = []
    parent = _long_name(parent) if parent else None
    for helper in helpers:
        helper = _long_name(helper)
        if not helper or not cmds.objExists(helper):
            continue

        if parent and cmds.objExists(parent) and not _is_descendant(helper, parent):
            try:
                parented = cmds.parent(helper, parent) or [helper]
                helper = _long_name(parented[0])
            except Exception as exc:
                cmds.warning("Could not organize helper {0}: {1}".format(
                    helper, exc))
        moved.append(helper)
    return moved


def _has_managed_wrap(driver, target):
    driver = _long_name(driver)
    target = _long_name(target)
    for record in discover_wrap_setups():
        if (
            _long_name(record.get("driver")) == driver
            and _long_name(record.get("target")) == target
        ):
            return True
    return False


def _write_wrap_metadata(node, driver, target):
    _ensure_bool_attr(node, WRAP_MANAGED_ATTR)
    cmds.setAttr("{0}.{1}".format(node, WRAP_MANAGED_ATTR), True)

    _ensure_string_attr(node, WRAP_DRIVER_ATTR)
    cmds.setAttr(
        "{0}.{1}".format(node, WRAP_DRIVER_ATTR),
        _long_name(driver),
        type="string",
    )

    _ensure_string_attr(node, WRAP_TARGET_ATTR)
    cmds.setAttr(
        "{0}.{1}".format(node, WRAP_TARGET_ATTR),
        _long_name(target),
        type="string",
    )


def _configure_wrap_local_influence(node, max_distance):
    if not node or not cmds.objExists(node):
        return []

    max_distance = max(0.0, float(max_distance))
    configured = []

    if _set_attr_if_exists(node, "exclusiveBind", False):
        configured.append("exclusiveBind")

    # Maya ignores maxDistance and weightThreshold while this is enabled.
    if _set_attr_if_exists(node, "autoWeightThreshold", False):
        configured.append("autoWeightThreshold")
    if _set_attr_if_exists(node, "maxDistance", max_distance):
        configured.append("maxDistance")
    if _set_attr_if_exists(node, "weightThreshold", 0.0):
        configured.append("weightThreshold")
    if _set_attr_if_exists(node, "falloffMode", 0):
        configured.append("falloffMode")

    _ensure_double_attr(node, WRAP_MAX_DISTANCE_ATTR)
    cmds.setAttr(
        "{0}.{1}".format(node, WRAP_MAX_DISTANCE_ATTR),
        max_distance,
    )

    if max_distance > 0 and not cmds.objExists("{0}.maxDistance".format(node)):
        cmds.warning(
            "Wrap node {0} has no maxDistance attribute; local wrap "
            "influence could not be applied.".format(node)
        )

    return configured


def _set_wrap_driver_render_influence(driver, enabled):
    for shape in _mesh_shapes(driver):
        for attr_name in WRAP_DRIVER_RENDER_ATTRS:
            _set_attr_if_exists(shape, attr_name, bool(enabled))


def _remove_wrap_influence_attrs(wrap_records):
    removed = 0
    seen = set()

    for record in wrap_records or []:
        driver = record.get("driver")
        for node in _wrap_influence_attr_nodes(driver):
            node = _long_name(node)
            if not node or node in seen:
                continue
            seen.add(node)
            removed += _delete_dynamic_attrs(node, WRAP_INFLUENCE_ATTRS)

    return removed


def _wrap_influence_attr_nodes(driver):
    transform = _mesh_transform(driver) or _transform_node(driver)
    if not transform or not cmds.objExists(transform):
        return []

    nodes = [_long_name(transform)]
    nodes.extend(_mesh_shapes(transform))
    return nodes


def _delete_dynamic_attrs(node, attr_names):
    removed = 0
    user_attrs = set(cmds.listAttr(node, userDefined=True) or [])

    for attr_name in attr_names:
        if attr_name not in user_attrs:
            continue

        attr = "{0}.{1}".format(node, attr_name)
        if not cmds.objExists(attr):
            continue

        try:
            if cmds.getAttr(attr, lock=True):
                cmds.setAttr(attr, lock=False)
        except Exception:
            pass

        try:
            cmds.deleteAttr(attr)
            removed += 1
        except Exception as exc:
            cmds.warning("Could not delete wrap influence attr {0}: {1}".format(
                attr,
                exc,
            ))

    return removed


def _write_helper_metadata(node, role, owner):
    if not node or not cmds.objExists(node):
        return

    _ensure_bool_attr(node, HELPER_MANAGED_ATTR)
    cmds.setAttr("{0}.{1}".format(node, HELPER_MANAGED_ATTR), True)

    _ensure_string_attr(node, HELPER_ROLE_ATTR)
    cmds.setAttr(
        "{0}.{1}".format(node, HELPER_ROLE_ATTR),
        role,
        type="string",
    )

    _ensure_string_attr(node, HELPER_OWNER_ATTR)
    cmds.setAttr(
        "{0}.{1}".format(node, HELPER_OWNER_ATTR),
        owner or "",
        type="string",
    )


def _wire_test_label(method_id):
    for method in WIRE_TEST_METHODS:
        if method["id"] == method_id:
            return method["label"]
    return method_id


def _wire_test_poly_geometry_off(meshes):
    _apply_poly_display_options(meshes, {"displayGeometry": False})
    _apply_poly_all_edges(meshes)
    _set_mesh_display_edges(meshes, True)


def _wire_test_override_no_shading(meshes):
    _apply_override_no_shading(meshes)
    _set_mesh_display_edges(meshes, True)


def _wire_test_template_override(meshes):
    for mesh in meshes:
        for node in _display_override_nodes(mesh):
            _set_display_attr(node, "overrideEnabled", True)
            _set_display_attr(node, "overrideDisplayType", 1)
    _set_mesh_display_edges(meshes, True)


def _wire_test_reference_override(meshes):
    for mesh in meshes:
        for node in _display_override_nodes(mesh):
            _set_display_attr(node, "overrideEnabled", True)
            _set_display_attr(node, "overrideDisplayType", 2)
    _set_mesh_display_edges(meshes, True)


def _wire_test_hide_shape(meshes):
    _show_mesh_shapes(meshes, False)


def _wire_test_curve_proxy(meshes):
    created = []
    for mesh in meshes:
        created.extend(_create_curve_wire_proxy(mesh))
    if not created:
        raise RuntimeError("Could not create curve wire proxies.")
    _show_mesh_shapes(meshes, False)
    cmds.select(created, replace=True)


def _show_mesh_shapes(meshes, visible):
    for mesh in meshes:
        for shape in _mesh_shapes(mesh):
            _set_display_attr(shape, "visibility", bool(visible))


def _set_mesh_display_edges(meshes, enabled):
    for mesh in meshes:
        for shape in _mesh_shapes(mesh):
            _set_display_attr(shape, "displayEdges", bool(enabled))


def _reset_display_overrides(mesh):
    for node in _display_override_nodes(mesh):
        _unlock_display_attrs(node)
        _set_display_attr(node, "overrideEnabled", False)
        _set_display_attr(node, "overrideDisplayType", 0)
        _set_display_attr(node, "overrideShading", True)
        _set_display_attr(node, "overrideTexturing", True)
    _set_mesh_display_edges([mesh], False)


def _create_curve_wire_proxy(mesh):
    mesh = _mesh_transform(mesh)
    if not mesh or not cmds.objExists(mesh):
        return []

    edge_count = cmds.polyEvaluate(mesh, edge=True) or 0
    if edge_count < 1:
        return []

    previous_selection = cmds.ls(selection=True, long=True) or []
    created = []
    group = None
    try:
        group = cmds.group(
            empty=True,
            name=_unique_name("{0}_cbs_wireProxy_GRP".format(_short_name(mesh))),
        )
        parent = (cmds.listRelatives(mesh, parent=True, fullPath=True) or [None])[0]
        if parent:
            try:
                group = (cmds.parent(group, parent) or [group])[0]
            except Exception:
                pass

        _write_wire_proxy_metadata(group, mesh)
        cmds.select("{0}.e[0:{1}]".format(mesh, edge_count - 1), replace=True)
        result = cmds.polyToCurve(form=2, degree=1) or []
        curve_transforms = []
        seen = set()
        for item in result:
            transform = _transform_node(item)
            if transform:
                _append_unique(curve_transforms, seen, transform)

        for curve in curve_transforms:
            try:
                curve = (cmds.parent(curve, group) or [curve])[0]
            except Exception:
                pass
            _style_wire_proxy_curve(curve)
            created.append(curve)

        if not created and group and cmds.objExists(group):
            cmds.delete(group)
    finally:
        _restore_selection(previous_selection)

    return created


def _style_wire_proxy_curve(curve):
    for node in [curve] + (cmds.listRelatives(curve, shapes=True, fullPath=True) or []):
        _set_display_attr(node, "overrideEnabled", True)
        _set_display_attr(node, "overrideColor", 14)


def _write_wire_proxy_metadata(node, owner):
    _ensure_bool_attr(node, WIRE_PROXY_MANAGED_ATTR)
    cmds.setAttr("{0}.{1}".format(node, WIRE_PROXY_MANAGED_ATTR), True)
    _ensure_string_attr(node, WIRE_PROXY_OWNER_ATTR)
    cmds.setAttr(
        "{0}.{1}".format(node, WIRE_PROXY_OWNER_ATTR),
        _long_name(owner),
        type="string",
    )


def _delete_wire_proxies(meshes):
    owners = {_long_name(mesh) for mesh in meshes}
    nodes = []
    for node in cmds.ls(type="transform", long=True) or []:
        attr = "{0}.{1}".format(node, WIRE_PROXY_MANAGED_ATTR)
        if not cmds.objExists(attr) or not cmds.getAttr(attr):
            continue
        owner = _read_string_attr(node, WIRE_PROXY_OWNER_ATTR)
        if _long_name(owner) in owners:
            nodes.append(node)
    if nodes:
        cmds.delete(nodes)


def _apply_override_no_shading(transforms):
    seen = set()
    for transform in transforms:
        for node in _display_override_nodes(transform):
            if node in seen:
                continue
            seen.add(node)
            _unlock_display_attrs(node)
            _set_display_attr(node, "overrideEnabled", True)
            _set_display_attr(node, "overrideDisplayType", 0)
            _set_display_attr(node, "overrideShading", False)
            _set_display_attr(node, "overrideTexturing", False)


def _display_override_nodes(transform):
    transform = _mesh_transform(transform) or _transform_node(transform)
    if not transform or not cmds.objExists(transform):
        return []

    nodes = [_long_name(transform)]
    nodes.extend(_mesh_shapes(transform))
    return nodes


def _mesh_shapes(transform):
    transform = _mesh_transform(transform) or _transform_node(transform)
    if not transform or not cmds.objExists(transform):
        return []

    shapes = cmds.listRelatives(
        transform,
        shapes=True,
        fullPath=True,
        noIntermediate=True,
    ) or []
    return [
        _long_name(shape) for shape in shapes
        if cmds.nodeType(shape) == "mesh"
    ]


def _set_display_attr(node, attr_name, value):
    attr = "{0}.{1}".format(node, attr_name)
    if not cmds.objExists(attr):
        return False
    try:
        current = cmds.getAttr(attr)
        if current == value:
            return False
        cmds.setAttr(attr, value)
        return True
    except Exception:
        return False


def _set_attr_if_exists(node, attr_name, value):
    attr = "{0}.{1}".format(node, attr_name)
    if not cmds.objExists(attr):
        return False
    try:
        if cmds.getAttr(attr, lock=True):
            cmds.setAttr(attr, lock=False)
    except Exception:
        pass
    try:
        cmds.setAttr(attr, value)
        return True
    except Exception:
        return False


def _unlock_display_attrs(node):
    for attr_name in DISPLAY_LOCK_ATTRS:
        _set_display_lock(node, attr_name, False)


def _set_display_lock(node, attr_name, locked):
    attr = "{0}.{1}".format(node, attr_name)
    if not cmds.objExists(attr):
        return
    try:
        if bool(cmds.getAttr(attr, lock=True)) == bool(locked):
            return
        cmds.setAttr(attr, lock=bool(locked))
    except Exception:
        pass


def _poly_display_options_state(transform):
    transform = _mesh_transform(transform) or _transform_node(transform)
    if not transform or not cmds.objExists(transform):
        return {}

    state = {}
    previous_selection = cmds.ls(selection=True, long=True) or []
    try:
        cmds.select(transform, replace=True)
        for flag in POLY_DISPLAY_OPTION_FLAGS:
            try:
                value = cmds.polyOptions(query=True, **{flag: True})
            except Exception:
                continue
            value = _first_query_value(value)
            if value is not None:
                state[flag] = bool(value)
    finally:
        _restore_selection(previous_selection)
    return state


def _apply_poly_display_options(transforms, options):
    transforms = _valid_mesh_transforms(transforms)
    if not transforms or not options:
        return

    previous_selection = cmds.ls(selection=True, long=True) or []
    try:
        cmds.select(transforms, replace=True)
        kwargs = {"activeObjects": True}
        for flag, value in options.items():
            if flag in POLY_DISPLAY_OPTION_FLAGS:
                kwargs[flag] = bool(value)
        if len(kwargs) > 1:
            cmds.polyOptions(**kwargs)
    except Exception:
        pass
    finally:
        _restore_selection(previous_selection)


def _apply_poly_all_edges(transforms):
    transforms = _valid_mesh_transforms(transforms)
    if not transforms:
        return

    previous_selection = cmds.ls(selection=True, long=True) or []
    try:
        cmds.select(transforms, replace=True)
        cmds.polyOptions(activeObjects=True, allEdges=True)
    except Exception:
        pass
    finally:
        _restore_selection(previous_selection)


def _valid_mesh_transforms(transforms):
    valid = []
    seen = set()
    for transform in transforms:
        mesh = _mesh_transform(transform) or _transform_node(transform)
        if not mesh or not cmds.objExists(mesh):
            continue
        if not _mesh_transform(mesh):
            continue
        _append_unique(valid, seen, mesh)
    return valid


def _first_query_value(value):
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def _restore_selection(selection):
    if not selection:
        cmds.select(clear=True)
        return

    try:
        cmds.select(selection, replace=True)
        return
    except Exception:
        pass

    existing = []
    for item in selection:
        try:
            if cmds.objExists(item):
                existing.append(item)
        except Exception:
            pass

    if existing:
        try:
            cmds.select(existing, replace=True)
            return
        except Exception:
            pass

    cmds.select(clear=True)


def _set_auto_key_state(state):
    try:
        previous = cmds.autoKeyframe(query=True, state=True)
        if state is not None:
            cmds.autoKeyframe(state=bool(state))
        return previous
    except Exception:
        return None


def _force_viewport_update():
    """Force the DG and viewport to re-evaluate after a time/weight change.

    Without this, Maya 2026 cached playback / Viewport 2.0 will frequently
    skip re-evaluating keyed .visibility on currently-hidden DAG nodes, so
    the time slider moves but the viewport keeps drawing the previous
    target's state (meshes look hidden-but-painted or visible-but-blank).
    """
    # 1. Invalidate the cached playback cache for the current frame range.
    #    Cached playback can hold stale visibility values on currently-hidden
    #    DAG nodes; refresh(force=True) alone does not flush it.
    try:
        cmds.cacheEvaluator(invalidate=True)
    except Exception:
        pass
    try:
        cmds.flushIdleQueue()
    except Exception:
        pass

    # 2. Force every managed key-group visibility plug to re-evaluate. This
    #    is the surgical fix for "key value is 1 at current frame but
    #    getAttr returns 0" — dgeval forces the animCurve to recompute.
    try:
        for root in _key_group_roots():
            groups = cmds.listRelatives(
                root, children=True, type="transform", fullPath=True,
            ) or []
            for group in groups:
                for attr_name in ("visibility", "lodVisibility"):
                    attr = "{0}.{1}".format(group, attr_name)
                    if cmds.objExists(attr):
                        try:
                            cmds.dgeval(attr)
                        except Exception:
                            pass
    except Exception:
        pass

    # 3. Mark everything dirty and force a viewport redraw.
    try:
        cmds.dgdirty(allPlugs=True)
    except Exception:
        pass
    try:
        cmds.refresh(force=True)
    except Exception:
        pass


def _ensure_key_group_root():
    roots = _key_group_roots()
    if roots:
        return roots[0]
    root = cmds.group(empty=True, name=_unique_name(KEY_GROUP_ROOT))
    return _long_name(root)


def _key_group_roots():
    roots = []
    for node in cmds.ls(type="transform", long=True) or []:
        attr = "{0}.{1}".format(node, KEY_GROUP_ROOT_ATTR)
        if cmds.objExists(attr) and cmds.getAttr(attr):
            roots.append(node)
    roots.sort()
    return roots


def _write_key_group_root_metadata(root):
    _ensure_bool_attr(root, KEY_GROUP_ROOT_ATTR)
    cmds.setAttr("{0}.{1}".format(root, KEY_GROUP_ROOT_ATTR), True)


def _ensure_key_group(root, index, label):
    for child in _key_group_children(root):
        existing_index = _read_numeric_attr(child, KEY_GROUP_INDEX_ATTR, None)
        if existing_index is not None and int(existing_index) == int(index):
            return child

    for child in _key_group_children(root):
        existing_label = _read_string_attr(child, KEY_GROUP_TARGET_ATTR)
        if existing_label == label:
            return child

    name = _unique_child_name(root, _safe_target_name(label))
    group = cmds.group(empty=True, name=name, parent=root)
    return _long_name(group)


def _key_group_children(root):
    children = cmds.listRelatives(
        root,
        children=True,
        type="transform",
        fullPath=True,
    ) or []
    result = []
    for child in children:
        attr = "{0}.{1}".format(child, KEY_GROUP_MANAGED_ATTR)
        if cmds.objExists(attr) and cmds.getAttr(attr):
            result.append(child)
    return result


def _write_key_group_metadata(group, index, label):
    _ensure_bool_attr(group, KEY_GROUP_MANAGED_ATTR)
    cmds.setAttr("{0}.{1}".format(group, KEY_GROUP_MANAGED_ATTR), True)

    _ensure_long_attr(group, KEY_GROUP_INDEX_ATTR)
    cmds.setAttr("{0}.{1}".format(group, KEY_GROUP_INDEX_ATTR), int(index))

    _ensure_string_attr(group, KEY_GROUP_TARGET_ATTR)
    cmds.setAttr(
        "{0}.{1}".format(group, KEY_GROUP_TARGET_ATTR),
        label,
        type="string",
    )


def _key_key_group_visibility(group, active_frame, key_items):
    """Set this key group's visibility directly (no animCurves).

    The previous time-driven curve approach was unreliable in Maya 2026:
    curves could get orphaned from time1, the DG sometimes refused to
    propagate the curve output to the attribute even when everything was
    connected, and step-tangent rounding produced salmon channels.

    The replacement: strip any existing animCurves on this attribute and
    setAttr the correct value directly. ``active_frame`` is compared to
    ``cmds.currentTime`` to decide whether this group is the active one.
    """
    del key_items  # only kept for backward signature compatibility
    attr = "{0}.visibility".format(group)
    if not cmds.objExists(attr):
        return

    _strip_anim_curves(attr)

    try:
        current_frame = int(round(cmds.currentTime(query=True)))
    except Exception:
        current_frame = int(active_frame)

    try:
        if cmds.getAttr(attr, lock=True):
            cmds.setAttr(attr, lock=False)
    except Exception:
        pass

    try:
        cmds.setAttr(attr, int(active_frame) == int(current_frame))
    except Exception:
        pass


def _apply_group_visibility(active_label):
    """Show only the key group matching ``active_label``; hide the rest.

    Direct setAttr, no animCurves. Strips any leftover animCurves on each
    group's .visibility before writing, so nothing fights the value.
    """
    for root in _key_group_roots():
        for group in _key_group_children(root):
            attr = "{0}.visibility".format(group)
            if not cmds.objExists(attr):
                continue
            _strip_anim_curves(attr)
            try:
                if cmds.getAttr(attr, lock=True):
                    cmds.setAttr(attr, lock=False)
            except Exception:
                pass
            label = _read_string_attr(group, KEY_GROUP_TARGET_ATTR) or \
                _short_name(group)
            try:
                cmds.setAttr(attr, label == active_label)
            except Exception:
                pass


def _strip_anim_curves(attr):
    """Disconnect and delete every animCurve driving ``attr``.

    Returns the number of curves removed. Safe if there are none.
    """
    removed = 0
    try:
        curves = cmds.listConnections(
            attr, source=True, destination=False, type="animCurve",
        ) or []
    except Exception:
        return 0
    for curve in curves:
        try:
            outputs = cmds.listConnections(
                curve + ".output",
                source=False, destination=True, plugs=True,
            ) or []
            for dest in outputs:
                try:
                    cmds.disconnectAttr(curve + ".output", dest)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            cmds.delete(curve)
            removed += 1
        except Exception:
            pass
    return removed


def _key_group_visible_at_frame(active_frame, key_items, current_frame):
    sorted_items = sorted(
        (int(frame), int(index)) for index, _label, frame in key_items
    )
    active_frame = int(active_frame)
    current_frame = int(current_frame)

    for offset, (frame, _index) in enumerate(sorted_items):
        next_frame = None
        if offset + 1 < len(sorted_items):
            next_frame = sorted_items[offset + 1][0]
        if frame != active_frame:
            continue
        if next_frame is None:
            return current_frame >= frame
        return frame <= current_frame < next_frame


def _ensure_curve_time_input(attr):
    """Make sure every animCurve driving ``attr`` is connected to time1.

    A scene-saved-with-broken-eval state or a stray "disconnect from time"
    leaves animCurve.input with no incoming connection. The curve then
    evaluates at whatever value .input was last set to (frequently 0),
    making the attribute appear stuck regardless of the playhead. This
    helper reconnects ``time1.outTime`` to every driving curve's input.

    Returns the number of connections it had to make.
    """
    fixed = 0
    if not cmds.objExists("time1"):
        return fixed
    try:
        curves = cmds.listConnections(
            attr, source=True, destination=False, type="animCurve",
        ) or []
    except Exception:
        return fixed
    for curve in curves:
        input_plug = "{0}.input".format(curve)
        if not cmds.objExists(input_plug):
            continue
        try:
            existing = cmds.listConnections(
                input_plug, source=True, destination=False, plugs=True,
            ) or []
        except Exception:
            existing = []
        if existing:
            continue
        try:
            cmds.connectAttr("time1.outTime", input_plug, force=True)
            fixed += 1
        except Exception:
            pass
    return fixed
    return False


def _unique_child_name(parent, base_name):
    existing = {
        _short_name(child)
        for child in cmds.listRelatives(
            parent,
            children=True,
            type="transform",
            fullPath=True,
        ) or []
    }
    candidate = base_name
    index = 1
    while candidate in existing:
        candidate = "{0}_{1}".format(base_name, index)
        index += 1
    return candidate


def _wrap_group_for_mesh(mesh):
    for ancestor in _ancestors(mesh):
        short_name = _short_name(ancestor)
        if _is_wrap_group_name(short_name):
            return ancestor
    return None


def _is_wrap_group_name(name):
    short_name = _short_name(name)
    if short_name == TEMPLATE_WRAP_TARGET:
        return False
    return "WRAP" in short_name.upper()


def _wrap_target_groups(wrap_group):
    descendants = cmds.listRelatives(
        wrap_group,
        allDescendents=True,
        fullPath=True,
        type="transform",
    ) or []
    groups = [
        node for node in descendants
        if _short_name(node) == TEMPLATE_WRAP_TARGET
    ]
    groups.sort(key=lambda node: node.count("|"))
    return groups


def _is_under_any(node, parents):
    return any(_is_descendant(node, parent) for parent in parents)


def _is_descendant(node, parent):
    node = _long_name(node)
    parent = _long_name(parent)
    return bool(node and parent and node.startswith(parent + "|"))


def _ancestors(node):
    node = _long_name(node)
    ancestors = []
    parent = node
    while parent:
        parents = cmds.listRelatives(parent, parent=True, fullPath=True) or []
        if not parents:
            break
        parent = parents[0]
        ancestors.append(parent)
    return ancestors


def _mesh_group_ancestors(mesh):
    groups = []
    for ancestor in _ancestors(mesh):
        if _short_name(ancestor) == TEMPLATE_WRAP_TARGET:
            continue
        groups.append(ancestor)
    return groups


def _mesh_transforms_under(item):
    transforms = []
    seen = set()
    transform = _mesh_transform(item)
    if transform:
        _append_unique(transforms, seen, transform)

    if not cmds.objExists(item) or cmds.nodeType(item) != "transform":
        return transforms

    descendants = cmds.listRelatives(
        item,
        allDescendents=True,
        fullPath=True,
        type="transform",
    ) or []
    descendants.reverse()

    for descendant in descendants:
        transform = _mesh_transform(descendant)
        if transform:
            _append_unique(transforms, seen, transform)

    return transforms


def _transform_nodes_under(item):
    transforms = []
    seen = set()

    transform = _transform_node(item)
    if transform:
        _append_unique(transforms, seen, transform)

    if not transform or not cmds.objExists(transform):
        return transforms

    descendants = cmds.listRelatives(
        transform,
        allDescendents=True,
        fullPath=True,
        type="transform",
    ) or []
    descendants.reverse()

    for descendant in descendants:
        _append_unique(transforms, seen, descendant)

    return transforms


def _transform_node(item):
    item = _component_owner(item)
    if not item or not cmds.objExists(item):
        return None

    node_type = cmds.nodeType(item)
    if node_type == "transform":
        return item

    parents = cmds.listRelatives(item, parent=True, fullPath=True) or []
    if parents and cmds.nodeType(parents[0]) == "transform":
        return parents[0]

    return None


def _mesh_transform(item):
    item = _component_owner(item)
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


def _component_owner(item):
    if not item:
        return item
    item = str(item)
    if "." in item and "[" in item:
        return item.split(".", 1)[0]
    return item


def _append_unique(items, seen, item):
    item = _long_name(item)
    if item and item not in seen:
        items.append(item)
        seen.add(item)


def _long_name(node):
    if not node or not cmds.objExists(node):
        return node
    matches = cmds.ls(node, long=True) or []
    return matches[0] if matches else node


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


def _configure_targets(node, mesh, target_names):
    for index, target_name in enumerate(target_names):
        _ensure_internal_target(node, mesh, index, target_name)
        cmds.blendShape(node, edit=True, weight=(index, 0.0))
        _alias_weight(node, index, target_name)

    try:
        cmds.sculptTarget(node, edit=True, target=-1)
    except Exception:
        pass


def _ensure_internal_target(node, mesh, index, target_name):
    if _target_index_exists(node, index):
        return

    temp = None
    previous_selection = cmds.ls(selection=True, long=True) or []
    try:
        temp = _duplicate_mesh_for_target(mesh, target_name)
        cmds.blendShape(
            node,
            edit=True,
            target=(mesh, index, temp, 1.0),
        )
    finally:
        if temp and cmds.objExists(temp):
            try:
                cmds.delete(temp)
            except Exception as exc:
                cmds.warning("Could not delete temporary target {0}: {1}".format(
                    temp,
                    exc,
                ))
        _restore_selection(previous_selection)


def _target_index_exists(node, index):
    attr = "{0}.inputTarget[0].inputTargetGroup[{1}]".format(node, index)
    if not cmds.objExists(attr):
        return False
    weights = cmds.aliasAttr(node, query=True) or []
    if any(item == "weight[{0}]".format(index) for item in weights[1::2]):
        return True
    target_item = "{0}.inputTarget[0].inputTargetGroup[{1}].inputTargetItem".format(
        node,
        index,
    )
    try:
        items = cmds.getAttr(target_item, multiIndices=True) or []
    except Exception:
        items = []
    return bool(items)


def _duplicate_mesh_for_target(mesh, target_name):
    temp_name = _unique_name("{0}_{1}_cbsTmpTarget".format(
        _short_name(mesh),
        _safe_target_name(target_name),
    ))
    duplicates = cmds.duplicate(
        mesh,
        name=temp_name,
        returnRootsOnly=True,
        inputConnections=False,
    ) or []
    if not duplicates:
        raise RuntimeError("Could not create temporary target for {0}.".format(
            mesh
        ))
    temp = duplicates[0]
    _ensure_bool_attr(temp, TEMP_TARGET_MANAGED_ATTR)
    cmds.setAttr("{0}.{1}".format(temp, TEMP_TARGET_MANAGED_ATTR), True)
    return temp


def _delete_temporary_target_meshes():
    deleted = []
    for node in cmds.ls(type="transform", long=True) or []:
        attr = "{0}.{1}".format(node, TEMP_TARGET_MANAGED_ATTR)
        if not cmds.objExists(attr) or not cmds.getAttr(attr):
            continue
        try:
            cmds.delete(node)
            deleted.append(node)
        except Exception as exc:
            cmds.warning("Could not delete temporary target mesh {0}: {1}".format(
                node,
                exc,
            ))
    if deleted:
        cmds.warning("Deleted {0} leftover temporary target mesh(es).".format(
            len(deleted)
        ))


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


def _key_transform_channels(meshes, target_count, start_frame, interval):
    frames = _setup_frames(target_count, start_frame, interval)
    _set_transform_keys(meshes, frames)
    for mesh in meshes:
        if cmds.objExists(mesh):
            _write_transform_metadata(mesh, frames)


def _set_transform_keys(meshes, frames):
    for mesh in meshes:
        if not mesh or not cmds.objExists(mesh):
            continue
        for frame in frames:
            for attr_name in TRANSFORM_KEY_ATTRS:
                attr = "{0}.{1}".format(mesh, attr_name)
                if not cmds.objExists(attr):
                    continue
                try:
                    value = cmds.getAttr(attr)
                    cmds.setKeyframe(attr, time=frame, value=value)
                except Exception:
                    pass

        for attr_name in TRANSFORM_KEY_ATTRS:
            attr = "{0}.{1}".format(mesh, attr_name)
            if not cmds.objExists(attr):
                continue
            try:
                cmds.keyTangent(
                    attr,
                    edit=True,
                    inTangentType="step",
                    outTangentType="step",
                )
            except Exception:
                pass


def _setup_frames(target_count, start_frame, interval):
    frames = [all_zero_frame(start_frame)]
    frames.extend(target_frame(i, start_frame, interval)
                  for i in range(int(target_count)))
    return frames


def _write_transform_metadata(mesh, frames):
    _ensure_bool_attr(mesh, TRANSFORM_KEYS_ATTR)
    cmds.setAttr("{0}.{1}".format(mesh, TRANSFORM_KEYS_ATTR), True)

    _ensure_string_attr(mesh, TRANSFORM_FRAMES_ATTR)
    cmds.setAttr(
        "{0}.{1}".format(mesh, TRANSFORM_FRAMES_ATTR),
        "|".join(str(int(frame)) for frame in frames),
        type="string",
    )


def _clear_transform_keys(records, extra_nodes=None):
    meshes = []
    seen = set()
    for record in records or []:
        mesh = record.get("mesh")
        if not mesh or not cmds.objExists(mesh):
            continue
        _append_unique(meshes, seen, mesh)

    for node in extra_nodes or []:
        if node and cmds.objExists(node):
            _append_unique(meshes, seen, node)

    for node in meshes:
        frames = _transform_frames_from_metadata(node)
        if not frames:
            frames = _transform_frames_from_record(node, records)
        for attr_name in TRANSFORM_KEY_ATTRS:
            attr = "{0}.{1}".format(node, attr_name)
            if not cmds.objExists(attr):
                continue
            for frame in frames:
                try:
                    cmds.cutKey(attr, time=(frame, frame), clear=True)
                except Exception:
                    pass
            _delete_empty_anim_curves(attr)
        _remove_transform_metadata(node)


def _transform_frames_from_metadata(mesh):
    value = _read_string_attr(mesh, TRANSFORM_FRAMES_ATTR)
    frames = []
    for item in value.split("|"):
        if not item:
            continue
        try:
            frames.append(int(float(item)))
        except (TypeError, ValueError):
            pass
    return frames


def _transform_frames_from_record(mesh, records):
    for record in records or []:
        if record.get("mesh") != mesh:
            continue
        return _setup_frames(
            len(record.get("targets", [])),
            record.get("start_frame", DEFAULT_START_FRAME),
            record.get("interval", DEFAULT_INTERVAL),
        )
    return []


def _remove_transform_metadata(mesh):
    for attr_name in (TRANSFORM_KEYS_ATTR, TRANSFORM_FRAMES_ATTR):
        attr = "{0}.{1}".format(mesh, attr_name)
        if not cmds.objExists(attr):
            continue
        try:
            cmds.deleteAttr(attr)
        except Exception:
            pass


def _delete_empty_anim_curves(attr):
    curves = cmds.listConnections(
        attr,
        source=True,
        destination=False,
        type="animCurve",
    ) or []
    for curve in curves:
        try:
            key_count = cmds.keyframe(curve, query=True, keyframeCount=True) or 0
        except Exception:
            key_count = 0
        if key_count:
            continue
        try:
            cmds.delete(curve)
        except Exception:
            pass


def _key_targets(node, target_names, start_frame, interval):
    frames = _setup_frames(len(target_names), start_frame, interval)

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


def _ensure_double_attr(node, attr):
    if not cmds.objExists("{0}.{1}".format(node, attr)):
        cmds.addAttr(node, longName=attr, attributeType="double")


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
