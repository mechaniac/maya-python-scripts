"""Logic for building synchronized multi-object blendshape edit sets."""

import re

import maya.cmds as cmds
import maya.mel as mel

import crash_logger
import maya_display


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
KEY_GROUP_LINEUP_ACTIVE_ATTR = "cbsKeyGroupLineupActive"
KEY_GROUP_LINEUP_OFFSET_ATTR = "cbsKeyGroupLineupOffset"
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
BAKE_MANAGED_ATTR = "cbsBakeManaged"
BAKE_SOURCE_ATTR = "cbsBakeSource"
BAKE_LABEL_ATTR = "cbsBakeLabel"
BAKE_DRIVER_MARK_ATTR = "cbsBakeDriverRemove"

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
DEFAULT_LINEUP_OFFSET = 50.0
OUTLINER_KEY_ROOT_COLOR = (0.48, 0.83, 0.95)
OUTLINER_KEY_TARGET_COLOR = (0.49, 0.72, 0.96)
OUTLINER_KEY_ACTIVE_COLOR = (0.55, 0.95, 0.62)
OUTLINER_KEY_BIND_COLOR = (0.72, 0.66, 1.0)
OUTLINER_TEMPLATE_ROOT_COLOR = (0.72, 0.66, 1.0)
OUTLINER_TEMPLATE_MESH_COLOR = (0.62, 0.94, 0.88)
OUTLINER_TEMPLATE_WRAP_COLOR = (0.95, 0.76, 0.45)
OUTLINER_TEMPLATE_TARGET_COLOR = (0.55, 0.95, 0.62)
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
    maya_display.ensure_display_affected()
    if generated_setup_exists():
        raise RuntimeError(
            "Remove the existing generated setup before generating a new one."
        )

    meshes = selected_mesh_transforms()
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
    maya_display.ensure_display_affected()
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
        key_group_only = _records_are_key_group_only(records)
        crash_logger.log_event(
            "activate_target_begin",
            action="activate_target",
            index=index,
            target=targets[index],
            frame=frame,
            records=len(records),
            key_group_only=key_group_only,
        )
        selected_meshes = []
        if key_group_only:
            crash_logger.log_event(
                "activate_target_key_group_only",
                action="activate_target",
                target=targets[index],
                reason="skip_time_and_blendshape_writes",
            )
        else:
            crash_logger.log_event(
                "activate_target_time_change_skipped",
                action="activate_target",
                frame=frame,
                reason="avoid_evaluating_child_transform_keys",
            )

            for record in records:
                node = record.get("node")
                if not node or not cmds.objExists(node):
                    continue
                if index >= len(record.get("targets", [])):
                    continue

                crash_logger.log_event(
                    "activate_target_weights_begin",
                    action="activate_target",
                    node=node,
                    active_index=index,
                )
                _set_active_weights(node, len(record["targets"]), index)
                crash_logger.log_event(
                    "activate_target_weights_end",
                    action="activate_target",
                    node=node,
                    active_index=index,
                )
                mesh = record.get("mesh")
                if mesh and cmds.objExists(mesh):
                    selected_meshes.append(mesh)

            if selected_meshes and not preserve_selection:
                cmds.select(selected_meshes, replace=True)

            if open_editor:
                open_blendshape_editor()

        # Direct visibility: no animCurves, no time dependency, no DG
        # eval surprises. The label of the active key group equals the
        # target name; BindPose is shown only by activate_all_off.
        crash_logger.log_event(
            "activate_target_groups_begin",
            action="activate_target",
            active_label=targets[index],
        )
        _apply_group_visibility(targets[index])
        crash_logger.log_event(
            "activate_target_groups_end",
            action="activate_target",
            active_label=targets[index],
        )

        _force_viewport_update()
    finally:
        if preserve_selection:
            crash_logger.log_event(
                "activate_target_restore_selection_begin",
                action="activate_target",
                count=len(previous_selection),
            )
            _restore_selection(previous_selection)
            crash_logger.log_event(
                "activate_target_restore_selection_end",
                action="activate_target",
            )
        _set_auto_key_state(auto_key_state)

    print("Editing {0} at frame {1}.".format(targets[index], frame))
    return frame


def activate_all_off(records=None, preserve_selection=True):
    """Set all managed blendShape targets to zero and jump to start frame."""
    maya_display.ensure_display_affected()
    records = records or discover_setups()
    if not records:
        raise RuntimeError("No managed blendshape setup found.")

    previous_selection = cmds.ls(selection=True, long=True) or []
    auto_key_state = _set_auto_key_state(False)
    try:
        start_frame = records[0]["start_frame"]
        key_group_only = _records_are_key_group_only(records)
        crash_logger.log_event(
            "activate_bind_pose_begin",
            action="activate_bind_pose",
            frame=start_frame,
            records=len(records),
            key_group_only=key_group_only,
        )
        if key_group_only:
            crash_logger.log_event(
                "activate_bind_pose_key_group_only",
                action="activate_bind_pose",
                reason="skip_time_and_blendshape_writes",
            )
        else:
            crash_logger.log_event(
                "activate_bind_pose_time_change_skipped",
                action="activate_bind_pose",
                frame=start_frame,
                reason="avoid_evaluating_child_transform_keys",
            )
            for record in records:
                node = record.get("node")
                if not node or not cmds.objExists(node):
                    continue
                crash_logger.log_event(
                    "activate_bind_pose_weights_begin",
                    action="activate_bind_pose",
                    node=node,
                )
                _set_active_weights(node, len(record["targets"]), -1)
                crash_logger.log_event(
                    "activate_bind_pose_weights_end",
                    action="activate_bind_pose",
                    node=node,
                )

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
            crash_logger.log_event(
                "activate_bind_pose_restore_selection_begin",
                action="activate_bind_pose",
                count=len(previous_selection),
            )
            _restore_selection(previous_selection)
            crash_logger.log_event(
                "activate_bind_pose_restore_selection_end",
                action="activate_bind_pose",
            )
        _set_auto_key_state(auto_key_state)

    print("All managed blendShape targets set to 0 at frame {0}.".format(
        start_frame))
    return start_frame


def activate_none(records=None, preserve_selection=True):
    """Set all managed blendShape targets to zero and hide every key group."""
    maya_display.ensure_display_affected()
    records = records or discover_setups()
    if not records:
        raise RuntimeError("No managed blendshape setup found.")

    previous_selection = cmds.ls(selection=True, long=True) or []
    auto_key_state = _set_auto_key_state(False)
    try:
        crash_logger.log_event(
            "activate_none_begin",
            action="activate_none",
            records=len(records),
        )
        for record in records:
            node = record.get("node")
            if not node or not cmds.objExists(node):
                continue
            crash_logger.log_event(
                "activate_none_weights_begin",
                action="activate_none",
                node=node,
            )
            _set_active_weights(node, len(record["targets"]), -1)
            crash_logger.log_event(
                "activate_none_weights_end",
                action="activate_none",
                node=node,
            )

        _apply_group_visibility(None)
        _force_viewport_update()
    finally:
        if preserve_selection:
            crash_logger.log_event(
                "activate_none_restore_selection_begin",
                action="activate_none",
                count=len(previous_selection),
            )
            _restore_selection(previous_selection)
            crash_logger.log_event(
                "activate_none_restore_selection_end",
                action="activate_none",
            )
        _set_auto_key_state(auto_key_state)

    print("All managed blendShape targets hidden.")
    return None


def _records_are_key_group_only(records):
    return bool(records) and all(
        bool(record.get("key_group_only")) or not record.get("node")
        for record in records
    )


def disable_edit_mode(records=None):
    """Turn off sculpt target edit mode on all managed blendShapes."""
    del records
    print("Blendshape edit mode calls are disabled for Maya crash safety.")


def auto_key_enabled():
    """Return True when Maya Auto Key is enabled."""
    try:
        return bool(cmds.autoKeyframe(query=True, state=True))
    except Exception:
        return False


def generated_setup_exists():
    """Return True if this tool has generated blendShapes, wraps, or states."""
    return bool(discover_setups() or discover_wrap_setups()
                or discover_helper_nodes() or discover_transform_key_nodes()
                or _key_group_roots())


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
        _write_key_group_root_metadata(root, targets, start_frame, interval)
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


def style_key_group_outliner(active_label=None):
    """Apply outliner colors to key groups owned by this tool."""
    styled = 0
    for root in _key_group_roots():
        if _set_outliner_color(root, OUTLINER_KEY_ROOT_COLOR):
            styled += 1
        for group in _key_group_children(root):
            label = _read_string_attr(group, KEY_GROUP_TARGET_ATTR) or \
                _short_name(group)
            if _style_key_group_outliner_node(
                group,
                label,
                active=label == active_label,
            ):
                styled += 1
    return styled


def key_group_lineup_is_active():
    """Return True if any managed key-group root is in lineup mode."""
    for root in _key_group_roots():
        attr = "{0}.{1}".format(root, KEY_GROUP_LINEUP_ACTIVE_ATTR)
        if not cmds.objExists(attr):
            continue
        try:
            if cmds.getAttr(attr):
                return True
        except Exception:
            pass
    return False


def set_key_group_lineup(active, offset=DEFAULT_LINEUP_OFFSET,
                         active_label=None):
    """Toggle direct key groups visible in an X-axis lineup.

    Deliberately simple and narrow:
    - touches only direct children of BlendshapeKeyGroups
    - writes only .visibility and .translateX on those direct key groups
    - never traverses or edits child meshes / shapes
    """
    crash_logger.log_event(
        "key_group_lineup_begin",
        action="key_group_lineup",
        active=bool(active),
        offset=offset,
        active_label=active_label,
    )
    roots = _key_group_roots()
    if not roots:
        raise RuntimeError("No BlendshapeKeyGroups hierarchy found.")

    offset = float(offset)
    if active:
        total = 0
        for root in roots:
            _write_key_group_lineup_root_state(root, True, offset)
            groups = _ordered_key_group_children(root)
            total += len(groups)
            _lineup_direct_key_groups(groups, offset)
        crash_logger.log_event(
            "key_group_lineup_end",
            action="key_group_lineup",
            active=True,
            groups=total,
        )
        return total

    restored = 0
    for root in roots:
        _write_key_group_lineup_root_state(root, False, offset)
        groups = _ordered_key_group_children(root)
        _reset_direct_key_group_lineup(groups)
        restored += len(groups)
    _apply_group_visibility(active_label)
    crash_logger.log_event(
        "key_group_lineup_end",
        action="key_group_lineup",
        active=False,
        groups=restored,
    )
    return restored


def update_key_group_lineup_offset(offset):
    """Update the active lineup spacing without changing stored originals."""
    if not key_group_lineup_is_active():
        return 0

    total = 0
    for root in _key_group_roots():
        _write_key_group_lineup_root_state(root, True, offset)
        groups = _ordered_key_group_children(root)
        _lineup_direct_key_groups(groups, float(offset))
        total += len(groups)
    crash_logger.log_event(
        "key_group_lineup_offset",
        action="key_group_lineup",
        offset=offset,
        groups=total,
    )
    return total


def repair_lineup_offsets(active_label=KEY_GROUP_BIND_POSE):
    """Clear lineup X offsets from direct key-group members only."""
    repaired = 0
    for root in _key_group_roots():
        _write_key_group_lineup_root_state(root, False, DEFAULT_LINEUP_OFFSET)
        groups = _key_group_children(root)
        _reset_direct_key_group_lineup(groups)
        repaired += len(groups)

    if repaired:
        _apply_group_visibility(active_label)
    crash_logger.log_event(
        "repair_lineup_offsets",
        action="repair_lineup_offsets",
        nodes=repaired,
        active_label=active_label,
    )
    return repaired


def repair_setup():
    """Repair an existing setup whose visibility has drifted out of sync.

    Safe, non-destructive operation for existing scenes. It only strips
    stale animation curves from direct ``BlendshapeKeyGroups/*`` visibility
    channels and re-applies direct group visibility. It does not walk into
    children and does not touch child transforms or mesh shapes.
    """
    records = discover_setups()
    if not records:
        raise RuntimeError("No managed blendshape setup found in this scene.")

    roots = _key_group_roots()
    if not roots:
        raise RuntimeError(
            "No BlendshapeKeyGroups root found. Run Generate Key Groups first."
        )

    stripped_curves = 0
    cmds.undoInfo(openChunk=True)
    try:
        for root in roots:
            for group in _key_group_children(root):
                # Delete every animCurve on this group's visibility.
                # The curve-driven visibility system was unreliable in
                # Maya 2026 (orphaned time inputs, DG eval refusing to
                # propagate). The replacement is direct setAttr on every
                # Target button click; no curves needed.
                for attr_name in ("visibility", "lodVisibility"):
                    attr = "{0}.{1}".format(group, attr_name)
                    if cmds.objExists(attr):
                        stripped_curves += _strip_anim_curves(attr)

        # Re-apply direct parent-group visibility. No child traversal.
        _apply_group_visibility(KEY_GROUP_BIND_POSE)
    finally:
        cmds.undoInfo(closeChunk=True)

    _force_viewport_update()

    print(
        "Repaired blendshape setup: "
        "stripped {0} stale animCurve(s) from direct key group visibility; "
        "children untouched.".format(stripped_curves)
    )
    return {
        "transforms": 0,
        "shapes": 0,
        "stripped_curves": stripped_curves,
    }


def bake_targets(records=None, preserve_selection=True):
    """Snapshot the whole character hierarchy per state, then replace
    the source setup with the snapshots.

    Algorithm:

    1. Compute the **snapshot root** = lowest common ancestor of every
       managed mesh. That subtree is the "whole character hierarchy"
       and contains all transform anim curves we want to preserve.
    2. **Loop 1**: for each state (BindPose plus every target), set the
       blendShape weights, duplicate the snapshot root (with input
       connections so transform anim curves come along), delete
       construction history on every mesh in the duplicate (which
       freezes the deformed shape and removes the blendShape /
       wrap / helper nodes), then also duplicate the matching
       ``BlendshapeKeyGroups/<state>`` subtree if any user content
       exists there. Park both under a temporary world-level group so
       they survive step 3.
    3. **Clean**: delete the original snapshot root and the entire
       original ``BlendshapeKeyGroups`` hierarchy. The source setup is
       gone.
    4. **Loop 2**: build a fresh ``BlendshapeKeyGroups`` root with one
       collapsed group per state. Re-parent each parked snapshot under
       its matching state group. Wire visibility so the existing
       Target buttons toggle exactly one snapshot visible at a time.

    Returns ``{"states": int, "snapshot_root": str}``.
    """
    maya_display.ensure_display_affected()
    records = records or discover_setups()
    if not records:
        raise RuntimeError("No managed blendshape setup found.")

    meshes = [
        record["mesh"] for record in records
        if record.get("mesh") and cmds.objExists(record["mesh"])
    ]
    if not meshes:
        raise RuntimeError("No managed meshes found to bake.")

    first = records[0]
    targets = list(first.get("targets") or [])
    if not targets:
        raise RuntimeError("The discovered setup has no blendshape targets.")

    snapshot_root = _common_ancestor(meshes)
    if not snapshot_root:
        raise RuntimeError(
            "Managed meshes share no common ancestor; cannot snapshot "
            "the character hierarchy."
        )

    # Capture each existing key group's subtree (without the group
    # transform itself) so user-added content survives the rebuild.
    keygroup_label_to_extras = {}
    for root in _key_group_roots():
        for group in _key_group_children(root):
            label = _read_string_attr(group, KEY_GROUP_TARGET_ATTR) or \
                _short_name(group)
            children = cmds.listRelatives(
                group, children=True, type="transform", fullPath=True,
            ) or []
            keygroup_label_to_extras.setdefault(label, []).extend(children)

    # (label, blendShape weight index) pairs. -1 = all weights at 0.
    states = [(KEY_GROUP_BIND_POSE, -1)] + [
        (target, index) for index, target in enumerate(targets)
    ]

    previous_selection = cmds.ls(selection=True, long=True) or []
    auto_key_state = _set_auto_key_state(False)
    cmds.undoInfo(openChunk=True)

    parking_name = _unique_name("BlendshapeBakeParking_TEMP")
    parking = cmds.group(empty=True, name=parking_name, world=True)
    parking = _long_name(parking)

    # Tag every wrap driver transform with a marker attr. The marker
    # survives cmds.duplicate, so every snapshot will carry it on the
    # same nodes and we can find + delete them per snapshot. After bake
    # we only want the wrapped targets, not the drivers.
    _tag_wrap_drivers_for_removal()

    snapshots = []  # list of (label, parked_node_long_path)
    try:
        # ---- Loop 1: snapshot every state into the parking group. ----
        for label, index in states:
            for record in records:
                node = record["node"]
                if cmds.objExists(node):
                    _set_active_weights(node, len(record["targets"]), index)

            snapshot_group = _snapshot_state(
                label=label,
                snapshot_root=snapshot_root,
                extra_sources=keygroup_label_to_extras.get(label, []),
                parking=parking,
            )
            snapshots.append((label, snapshot_group))

        # ---- Clean: remove the original source + key group hierarchy. ----
        for root in _key_group_roots():
            if cmds.objExists(root):
                try:
                    cmds.delete(root)
                except Exception as exc:
                    cmds.warning(
                        "Could not delete old key group root {0}: {1}".format(
                            root, exc,
                        )
                    )

        # Delete the source character subtree last so anim curves on the
        # parked duplicates don't accidentally end up the only reference
        # to any shared upstream node.
        if cmds.objExists(snapshot_root):
            try:
                cmds.delete(snapshot_root)
            except Exception as exc:
                cmds.warning(
                    "Could not delete source hierarchy {0}: {1}".format(
                        snapshot_root, exc,
                    )
                )

        # Strip leftover managed blendShape / wrap / helper nodes that
        # may not have been parented under snapshot_root.
        _purge_leftover_managed_nodes()

        # ---- Loop 2: rebuild a fresh BlendshapeKeyGroups hierarchy. ----
        new_root = cmds.group(empty=True, name=_unique_name(KEY_GROUP_ROOT))
        new_root = _long_name(new_root)
        _write_key_group_root_metadata(
            new_root,
            targets,
            first.get("start_frame", DEFAULT_START_FRAME),
            first.get("interval", DEFAULT_INTERVAL),
        )

        for state_index, (label, snapshot_group) in enumerate(snapshots):
            kg_name = _unique_child_name(new_root, _safe_target_name(label))
            kg = cmds.group(empty=True, name=kg_name, parent=new_root)
            kg = _long_name(kg)
            # Group index: -1 for BindPose, 0..N-1 for targets (matches
            # the order in `states`).
            group_index = -1 if state_index == 0 else state_index - 1
            _write_key_group_metadata(kg, group_index, label)

            if snapshot_group and cmds.objExists(snapshot_group):
                parented = cmds.parent(snapshot_group, kg) or [snapshot_group]
                # Resolve to long name after re-parenting.
                _long_name(parented[0])

        # Tear down the now-empty parking group.
        if cmds.objExists(parking):
            try:
                cmds.delete(parking)
            except Exception:
                pass

        # Visibility: show BindPose only. Direct setAttr, no curves.
        _apply_group_visibility(KEY_GROUP_BIND_POSE)

        # Collapse the new key groups in the outliner so children stay
        # hidden by default.
        _collapse_in_outliner([new_root])
        new_group_paths = cmds.listRelatives(
            new_root, children=True, type="transform", fullPath=True,
        ) or []
        _collapse_in_outliner(new_group_paths)
    finally:
        if preserve_selection:
            _restore_selection(previous_selection)
        else:
            try:
                cmds.select(clear=True)
            except Exception:
                pass
        _set_auto_key_state(auto_key_state)
        cmds.undoInfo(closeChunk=True)

    _force_viewport_update()

    print(
        "Baked {0} state snapshot(s) under new {1}.".format(
            len(snapshots), new_root,
        )
    )
    return {
        "states": len(snapshots),
        "snapshot_root": new_root,
    }


def _snapshot_state(label, snapshot_root, extra_sources, parking):
    """Duplicate ``snapshot_root`` (and any per-state extras) into a single
    parked group, freezing every mesh by deleting construction history.
    """
    state_name = _unique_name("{0}_{1}_bake".format(
        _short_name(snapshot_root),
        _safe_target_name(label),
    ))

    # Duplicate the whole character subtree. inputConnections=True keeps
    # the transform anim curves on the duplicate's transforms.
    duplicates = cmds.duplicate(
        snapshot_root,
        name=state_name,
        returnRootsOnly=True,
        renameChildren=True,
        inputConnections=True,
    ) or []
    if not duplicates:
        raise RuntimeError(
            "duplicate returned nothing for {0}".format(snapshot_root)
        )
    snapshot = _long_name(duplicates[0])

    # Freeze every mesh in the duplicate: delete construction history
    # removes blendShape/wrap/skinCluster connections and bakes the
    # currently-deformed shape into the static mesh. delete -ch does NOT
    # remove animation curves on transforms.
    descendant_meshes = cmds.listRelatives(
        snapshot, allDescendents=True, type="mesh", fullPath=True,
        noIntermediate=True,
    ) or []
    transform_paths = set()
    for shape in descendant_meshes:
        parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
        if parents:
            transform_paths.add(parents[0])

    # Capture shader assignments BEFORE delete -ch: wrap-driven meshes
    # in particular tend to lose their shadingEngine link when their
    # deformer chain is destroyed, falling back to the default lambert
    # (green in the viewport). We re-apply by transform after the freeze.
    shader_records = _capture_shader_assignments(transform_paths)

    if transform_paths:
        try:
            cmds.delete(list(transform_paths), constructionHistory=True)
        except Exception as exc:
            cmds.warning(
                "delete -ch failed on {0}: {1}".format(label, exc)
            )

    _restore_shader_assignments(shader_records)

    # Remove every node tagged as a wrap driver. The marker was set on
    # the source before duplication, so duplicate carried it along.
    _remove_tagged_wrap_drivers(snapshot)

    # Strip any managed metadata attrs that survived (blendShape /
    # wrap / helper attrs may still be present on cleared transforms).
    _strip_managed_attrs_recursive(snapshot)

    # Park under the temporary parking node so nothing dangles in world
    # while we delete the originals.
    parented = cmds.parent(snapshot, parking) or [snapshot]
    snapshot = _long_name(parented[0])

    # Duplicate per-state extras (user content under the matching old
    # key group) and stuff them under the same snapshot.
    for extra in extra_sources:
        if not cmds.objExists(extra):
            continue
        try:
            extra_dup = cmds.duplicate(
                extra,
                returnRootsOnly=True,
                renameChildren=True,
                inputConnections=True,
            ) or []
        except Exception as exc:
            cmds.warning(
                "Could not duplicate extra {0} for {1}: {2}".format(
                    extra, label, exc,
                )
            )
            continue
        if not extra_dup:
            continue
        try:
            cmds.parent(extra_dup[0], snapshot)
        except Exception:
            pass

    # Tag the snapshot so we can identify baked content later.
    _ensure_bool_attr(snapshot, BAKE_MANAGED_ATTR)
    cmds.setAttr("{0}.{1}".format(snapshot, BAKE_MANAGED_ATTR), True)
    _ensure_string_attr(snapshot, BAKE_LABEL_ATTR)
    cmds.setAttr(
        "{0}.{1}".format(snapshot, BAKE_LABEL_ATTR), label, type="string",
    )

    return snapshot


def _common_ancestor(nodes):
    """Return the longest common DAG ancestor of ``nodes`` (long path).

    For a single node this is its parent transform. If no common
    ancestor exists above the world, returns ``""``.
    """
    if not nodes:
        return ""
    paths = []
    for node in nodes:
        long_path = _long_name(node)
        if not long_path or not long_path.startswith("|"):
            return ""
        paths.append(long_path.split("|")[1:])  # drop leading ""

    common = []
    for parts in zip(*paths):
        first = parts[0]
        if all(part == first for part in parts):
            common.append(first)
        else:
            break

    # If every node shares the full path (single node case), drop the
    # last segment so we get the parent.
    if len(common) == len(paths[0]):
        common = common[:-1]
    if not common:
        return ""

    candidate = "|" + "|".join(common)
    if cmds.objExists(candidate):
        return candidate
    return ""


def _strip_managed_attrs_recursive(root):
    """Remove cbs* metadata attrs from every transform under ``root``.

    Stops the rebuilt setup from being re-discovered as the original
    managed setup. Best effort; ignores locked / unknown attrs.
    """
    cbs_attrs = (
        MANAGED_ATTR, TARGETS_ATTR, START_ATTR, INTERVAL_ATTR, COUNT_ATTR,
        TRANSFORM_KEYS_ATTR, TRANSFORM_FRAMES_ATTR,
        KEY_GROUP_ROOT_ATTR, KEY_GROUP_MANAGED_ATTR, KEY_GROUP_INDEX_ATTR,
        KEY_GROUP_TARGET_ATTR,
        WRAP_MANAGED_ATTR, WRAP_DRIVER_ATTR, WRAP_TARGET_ATTR,
        WRAP_MAX_DISTANCE_ATTR,
        HELPER_MANAGED_ATTR, HELPER_ROLE_ATTR, HELPER_OWNER_ATTR,
        WIRE_PROXY_MANAGED_ATTR, WIRE_PROXY_OWNER_ATTR,
        TEMP_TARGET_MANAGED_ATTR,
    )
    nodes = [root] + (cmds.listRelatives(
        root, allDescendents=True, type="transform", fullPath=True,
    ) or [])
    for node in nodes:
        for attr in cbs_attrs:
            full = "{0}.{1}".format(node, attr)
            if cmds.objExists(full):
                try:
                    cmds.setAttr(full, lock=False)
                except Exception:
                    pass
                try:
                    cmds.deleteAttr(node, attribute=attr)
                except Exception:
                    pass


def _capture_shader_assignments(transforms):
    """Return a list of (shape_long_path, shadingEngine) pairs for the
    visible shape under every transform.

    Recorded BEFORE delete -ch so we can restore the assignments after
    the deformer chain (especially wrap) is torn down, since otherwise
    the deformed shape falls back to the default lambert shader.
    """
    records = []
    for transform in transforms:
        if not cmds.objExists(transform):
            continue
        shapes = cmds.listRelatives(
            transform, shapes=True, fullPath=True, noIntermediate=True,
        ) or []
        for shape in shapes:
            try:
                ses = cmds.listConnections(
                    shape, source=False, destination=True,
                    type="shadingEngine",
                ) or []
            except Exception:
                ses = []
            for se in dict.fromkeys(ses):  # preserve order, dedupe
                records.append((shape, se))
    return records


def _restore_shader_assignments(records):
    """Re-add shapes to their original shadingEngines via cmds.sets."""
    for shape, se in records:
        if not cmds.objExists(shape) or not cmds.objExists(se):
            continue
        try:
            cmds.sets(shape, edit=True, forceElement=se)
        except Exception:
            pass


def _tag_wrap_drivers_for_removal():
    """Add a marker bool attr to every wrap driver transform so the
    duplicated copies in each snapshot can be located and deleted.

    Resolves the driver path from each managed wrap node's metadata.
    Silent on missing nodes; this is a best-effort tag pass.
    """
    for record in discover_wrap_setups():
        driver_path = record.get("driver") or ""
        if not driver_path or not cmds.objExists(driver_path):
            continue
        # Drivers stored in WRAP_DRIVER_ATTR are mesh transforms; tag
        # the transform itself.
        node = _long_name(driver_path)
        if not node:
            continue
        try:
            _ensure_bool_attr(node, BAKE_DRIVER_MARK_ATTR)
            cmds.setAttr(
                "{0}.{1}".format(node, BAKE_DRIVER_MARK_ATTR), True,
            )
        except Exception:
            pass


def _remove_tagged_wrap_drivers(root):
    """Delete every transform under ``root`` carrying the wrap-driver
    marker attr. After bake we only want the wrap targets, not drivers.
    """
    candidates = [root] + (cmds.listRelatives(
        root, allDescendents=True, type="transform", fullPath=True,
    ) or [])
    to_delete = []
    for node in candidates:
        attr = "{0}.{1}".format(node, BAKE_DRIVER_MARK_ATTR)
        if cmds.objExists(attr):
            try:
                if cmds.getAttr(attr):
                    to_delete.append(node)
            except Exception:
                pass
    # Delete deepest paths first so we don't try to delete a child of an
    # already-deleted parent.
    to_delete.sort(key=lambda p: p.count("|"), reverse=True)
    for node in to_delete:
        if cmds.objExists(node):
            try:
                cmds.delete(node)
            except Exception:
                pass


def _purge_leftover_managed_nodes():
    """Delete leftover managed blendShape / wrap / helper / temp nodes
    that may have survived because they were not parented under the
    snapshot root."""
    # Managed blendShape nodes.
    for node in cmds.ls(type="blendShape") or []:
        attr = "{0}.{1}".format(node, MANAGED_ATTR)
        if cmds.objExists(attr):
            try:
                if cmds.getAttr(attr) and cmds.objExists(node):
                    cmds.delete(node)
            except Exception:
                pass
    # Managed wrap deformers.
    for node in cmds.ls(type="wrap") or []:
        attr = "{0}.{1}".format(node, WRAP_MANAGED_ATTR)
        if cmds.objExists(attr):
            try:
                if cmds.getAttr(attr) and cmds.objExists(node):
                    cmds.delete(node)
            except Exception:
                pass
    # Helper transforms.
    for node in cmds.ls(type="transform", long=True) or []:
        attr = "{0}.{1}".format(node, HELPER_MANAGED_ATTR)
        if cmds.objExists(attr):
            try:
                if cmds.getAttr(attr) and cmds.objExists(node):
                    cmds.delete(node)
            except Exception:
                pass
    # Temp target meshes.
    _delete_temporary_target_meshes()


def _collapse_in_outliner(nodes):
    """Best-effort: collapse the given DAG nodes in the active outliner.

    Maya has no public per-node outliner-collapse API. The closest
    reliable trick is to select the nodes and run the ``OutlinerCollapse``
    MEL runtime command, which collapses every selected item in the
    focused outliner. Silent on failure; this is a UI nicety, and newly
    created groups are collapsed by default anyway as long as nothing
    expands them.
    """
    if not nodes:
        return
    existing = [_long_name(n) for n in nodes if cmds.objExists(n)]
    if not existing:
        return
    try:
        previous = cmds.ls(selection=True, long=True) or []
        cmds.select(existing, replace=True, noExpand=True)
        try:
            mel.eval("OutlinerCollapse;")
        except Exception:
            pass
        if previous:
            try:
                cmds.select(previous, replace=True, noExpand=True)
            except Exception:
                cmds.select(clear=True)
        else:
            cmds.select(clear=True)
    except Exception:
        pass


def _reset_visibility(node):
    """Deprecated: child visibility resets are disabled."""
    crash_logger.log_event(
        "visibility_reset_skipped",
        action="reset_visibility",
        node=node,
        reason="child_transform_writes_disabled",
    )
    return False


def remove_setup(records=None):
    """Delete managed blendShape and wrap nodes created by this tool."""
    records = records if records is not None else discover_setups()
    if not records:
        records = discover_setups()
    wrap_records = discover_wrap_setups()
    helper_nodes = discover_helper_nodes()
    transform_key_nodes = discover_transform_key_nodes()
    key_group_roots = _key_group_roots()
    if (not records and not wrap_records and not helper_nodes
            and not transform_key_nodes and not key_group_roots):
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

    key_group_nodes = []
    for node in key_group_roots:
        if node and node not in seen and cmds.objExists(node):
            key_group_nodes.append(node)
            seen.add(node)

    nodes = helper_nodes + wrap_nodes + blend_nodes + key_group_nodes
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
        "keyGroups": len(key_group_nodes),
        "total": len(nodes),
    }
    print(
        "Removed {0} blendShape node(s), {1} wrap node(s), "
        "{2} helper node(s), transform metadata on {3} node(s), "
        "{4} wrap influence attr(s), and {5} key group root(s).".format(
            result["blendShapes"],
            result["wraps"],
            result["helpers"],
            result["transformKeyedNodes"],
            result["wrapInfluenceAttrs"],
            result["keyGroups"],
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
    _set_outliner_color(root, OUTLINER_TEMPLATE_ROOT_COLOR)
    _set_outliner_color(meshes, OUTLINER_TEMPLATE_MESH_COLOR)
    _set_outliner_color(wrap_group, OUTLINER_TEMPLATE_WRAP_COLOR)
    _set_outliner_color(wrap_targets, OUTLINER_TEMPLATE_TARGET_COLOR)
    cmds.select(root, replace=True)
    return {
        "root": root,
        "meshes": meshes,
        "wrap_group": wrap_group,
        "wrap_targets": wrap_targets,
    }


def discover_setups():
    """Find blendShape nodes created by this tool, or saved key groups."""
    records = discover_blendshape_setups()
    if records:
        return records
    return discover_key_group_setups()


def discover_blendshape_setups():
    """Find only live managed blendShape nodes created by this tool."""
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


def discover_key_group_setups():
    """Rebuild a target-button record from saved BlendshapeKeyGroups."""
    records = []
    for root in _key_group_roots():
        targets = _key_group_targets(root)
        if not targets:
            continue
        start_frame = int(_read_numeric_attr(
            root,
            START_ATTR,
            DEFAULT_START_FRAME,
        ))
        interval = int(_read_numeric_attr(
            root,
            INTERVAL_ATTR,
            DEFAULT_INTERVAL,
        ))
        records.append({
            "mesh": None,
            "node": "",
            "targets": targets,
            "start_frame": start_frame,
            "interval": interval,
            "key_group_root": root,
            "key_group_only": True,
        })

    records.sort(key=lambda record: record["key_group_root"])
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
    maya_display.ensure_display_affected()
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
    if method_id == "curve_proxy":
        maya_display.ensure_display_affected()
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


def apply_transform_keys_at_current_time():
    """Deprecated safety no-op.

    Transform-keyed child objects must be evaluated by Maya's timeline, not
    force-written by this tool. Direct writes caused child rotations/scales to
    snap to the setup defaults.
    """
    crash_logger.log_event(
        "transform_keys_apply_skipped",
        action="apply_transform_keys",
        reason="direct_transform_writes_disabled",
    )
    return 0


def target_frame(index, start_frame=DEFAULT_START_FRAME,
                 interval=DEFAULT_INTERVAL):
    return int(start_frame) + (int(interval) * (int(index) + 1))


def all_zero_frame(start_frame=DEFAULT_START_FRAME):
    return int(start_frame)


def _set_current_frame_safely(frame, reason):
    """Deprecated: timeline writes are disabled for child-transform safety."""
    crash_logger.log_event(
        "current_time_write_skipped",
        action=reason,
        frame=frame,
        reason="timeline_writes_disabled_to_protect_child_transforms",
    )
    return int(frame)


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
    del node, index, mesh
    return False


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


def _set_outliner_color(node, color):
    if not node or not cmds.objExists(node):
        return False

    enabled_attr = "{0}.useOutlinerColor".format(node)
    color_attr = "{0}.outlinerColor".format(node)
    if not cmds.objExists(enabled_attr) or not cmds.objExists(color_attr):
        return False

    try:
        if cmds.getAttr(enabled_attr, lock=True):
            cmds.setAttr(enabled_attr, lock=False)
    except Exception:
        pass
    try:
        if cmds.getAttr(color_attr, lock=True):
            cmds.setAttr(color_attr, lock=False)
    except Exception:
        pass

    try:
        cmds.setAttr(enabled_attr, True)
        cmds.setAttr(color_attr, color[0], color[1], color[2])
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
    """Do not force a viewport refresh from target-button callbacks."""
    crash_logger.log_event(
        "viewport_refresh_skipped",
        action="safe_button_mode",
    )
    return


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
        has_marker = False
        if cmds.objExists(attr):
            try:
                has_marker = bool(cmds.getAttr(attr))
            except Exception:
                has_marker = False
        if has_marker or _short_name(node).startswith(KEY_GROUP_ROOT):
            roots.append(node)
    roots.sort()
    return roots


def _write_key_group_root_metadata(root, targets=None, start_frame=None,
                                   interval=None):
    _set_outliner_color(root, OUTLINER_KEY_ROOT_COLOR)

    _ensure_bool_attr(root, KEY_GROUP_ROOT_ATTR)
    cmds.setAttr("{0}.{1}".format(root, KEY_GROUP_ROOT_ATTR), True)

    if targets is not None:
        _ensure_string_attr(root, TARGETS_ATTR)
        cmds.setAttr(
            "{0}.{1}".format(root, TARGETS_ATTR),
            "|".join(targets),
            type="string",
        )

    if start_frame is not None:
        _ensure_long_attr(root, START_ATTR)
        cmds.setAttr("{0}.{1}".format(root, START_ATTR), int(start_frame))

    if interval is not None:
        _ensure_long_attr(root, INTERVAL_ATTR)
        cmds.setAttr("{0}.{1}".format(root, INTERVAL_ATTR), int(interval))


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
        has_marker = False
        if cmds.objExists(attr):
            try:
                has_marker = bool(cmds.getAttr(attr))
            except Exception:
                has_marker = False
        if has_marker or _is_likely_key_group_child(child):
            result.append(child)
    return result


def _ordered_key_group_children(root):
    children = _key_group_children(root)
    order_by_child = dict((child, order) for order, child in enumerate(children))

    def _sort_key(child):
        label = _read_string_attr(child, KEY_GROUP_TARGET_ATTR) or \
            _short_name(child)
        if label == KEY_GROUP_BIND_POSE:
            return (-1, order_by_child.get(child, 0), label)
        index = _read_numeric_attr(child, KEY_GROUP_INDEX_ATTR, None)
        if index is None:
            return (100000, order_by_child.get(child, 0), label)
        return (int(index), order_by_child.get(child, 0), label)

    return sorted(children, key=_sort_key)


def _key_group_targets(root):
    stored = [
        target for target in _read_string_attr(root, TARGETS_ATTR).split("|")
        if target
    ]
    if stored:
        return stored

    targets = []
    seen = set()
    for order, child in enumerate(_key_group_children(root)):
        label = _read_string_attr(child, KEY_GROUP_TARGET_ATTR) or \
            _short_name(child)
        if label == KEY_GROUP_BIND_POSE:
            continue
        index = _read_numeric_attr(child, KEY_GROUP_INDEX_ATTR, None)
        if index is None or int(index) < 0:
            sort_key = 100000 + order
        else:
            sort_key = int(index)
        targets.append((sort_key, order, label))

    result = []
    for _sort_key, _order, label in sorted(targets):
        if label in seen:
            continue
        result.append(label)
        seen.add(label)
    return result


def _is_likely_key_group_child(child):
    name = _short_name(child)
    if name == KEY_GROUP_BIND_POSE:
        return True
    return not name.startswith("_")


def _write_key_group_lineup_root_state(root, active, offset):
    _ensure_bool_attr(root, KEY_GROUP_LINEUP_ACTIVE_ATTR)
    _ensure_double_attr(root, KEY_GROUP_LINEUP_OFFSET_ATTR)
    try:
        cmds.setAttr(
            "{0}.{1}".format(root, KEY_GROUP_LINEUP_ACTIVE_ATTR),
            bool(active),
        )
        cmds.setAttr(
            "{0}.{1}".format(root, KEY_GROUP_LINEUP_OFFSET_ATTR),
            float(offset),
        )
    except Exception:
        pass


def _lineup_direct_key_groups(groups, offset):
    count = len(groups)
    if not count:
        return

    center = (count - 1) / 2.0
    for index, group in enumerate(groups):
        label = _read_string_attr(group, KEY_GROUP_TARGET_ATTR) or \
            _short_name(group)
        _style_key_group_outliner_node(group, label, active=True)
        _set_key_group_visibility(group, True)
        _set_key_group_translate_x(
            group,
            (index - center) * float(offset),
        )


def _reset_direct_key_group_lineup(groups):
    for group in groups:
        _set_key_group_translate_x(group, 0.0)


def _set_key_group_translate_x(group, value):
    attr = "{0}.translateX".format(group)
    if not cmds.objExists(attr):
        return
    auto_key_state = _set_auto_key_state(False)
    try:
        if cmds.getAttr(attr, lock=True):
            cmds.setAttr(attr, lock=False)
    except Exception:
        pass
    try:
        try:
            cmds.setAttr(attr, float(value))
        except Exception:
            pass
    finally:
        _set_auto_key_state(auto_key_state)


def _apply_key_group_lineup(root, groups, offset, store_original=True):
    del root, store_original
    _lineup_direct_key_groups(groups, offset)


def _set_key_group_visibility(group, visible):
    attr = "{0}.visibility".format(group)
    if not cmds.objExists(attr):
        return
    auto_key_state = _set_auto_key_state(False)
    try:
        if cmds.getAttr(attr, lock=True):
            cmds.setAttr(attr, lock=False)
    except Exception:
        pass
    try:
        try:
            cmds.setAttr(attr, bool(visible))
        except Exception:
            pass
    finally:
        _set_auto_key_state(auto_key_state)


def _write_key_group_metadata(group, index, label):
    _style_key_group_outliner_node(group, label, active=False)

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


def _style_key_group_outliner_node(group, label, active=False):
    if active:
        color = OUTLINER_KEY_ACTIVE_COLOR
    elif label == KEY_GROUP_BIND_POSE:
        color = OUTLINER_KEY_BIND_COLOR
    else:
        color = OUTLINER_KEY_TARGET_COLOR
    return _set_outliner_color(group, color)


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

    _set_key_group_visibility(group, int(active_frame) == int(current_frame))


def _apply_group_visibility(active_label):
    """Show only the key group matching ``active_label``; hide the rest.

    Direct setAttr only. Normal target switching must not delete nodes or
    rebuild animation connections.
    """
    for root in _key_group_roots():
        _set_outliner_color(root, OUTLINER_KEY_ROOT_COLOR)
        _set_key_group_visibility(root, True)
        for group in _key_group_children(root):
            attr = "{0}.visibility".format(group)
            if not cmds.objExists(attr):
                continue
            try:
                if cmds.getAttr(attr, lock=True):
                    cmds.setAttr(attr, lock=False)
            except Exception:
                pass
            label = _read_string_attr(group, KEY_GROUP_TARGET_ATTR) or \
                _short_name(group)
            visible = label == active_label
            _style_key_group_outliner_node(
                group,
                label,
                active=visible,
            )
            crash_logger.log_event(
                "key_group_visibility_set",
                action="apply_group_visibility",
                group=group,
                label=label,
                visible=visible,
            )
            _set_key_group_visibility(group, visible)


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
    """Deprecated: transform-channel keying is disabled.

    The tool must never write translate/rotate/scale keys on selected
    hierarchy contents. Target buttons are now controlled by blendShape
    weights and direct visibility on the generated key groups only.
    """
    del meshes, target_count, start_frame, interval
    crash_logger.log_event(
        "transform_key_generation_skipped",
        action="generate_setup",
        reason="direct_transform_keying_disabled",
    )
    return 0


def _set_transform_keys(meshes, frames):
    del meshes, frames
    crash_logger.log_event(
        "transform_key_write_skipped",
        action="set_transform_keys",
        reason="direct_transform_keying_disabled",
    )
    return 0


def _setup_frames(target_count, start_frame, interval):
    frames = [all_zero_frame(start_frame)]
    frames.extend(target_frame(i, start_frame, interval)
                  for i in range(int(target_count)))
    return frames


def _write_transform_metadata(mesh, frames):
    del mesh, frames
    crash_logger.log_event(
        "transform_metadata_write_skipped",
        action="write_transform_metadata",
        reason="direct_transform_keying_disabled",
    )
    return 0


def _clear_transform_keys(records, extra_nodes=None):
    """Remove only obsolete transform-key metadata, never transform keys.

    Older versions marked selected children/groups with cbsTransform* attrs
    and wrote translate/rotate/scale keys. Removing keys here is no longer
    safe because scenes may contain unrelated animation on those channels.
    """
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


def _apply_transform_keys_at_frame(frame):
    crash_logger.log_event(
        "transform_keys_apply_skipped",
        action="apply_transform_keys",
        frame=frame,
        reason="direct_transform_writes_disabled",
    )
    return 0


def _keyed_attr_value_at_frame(attr, frame):
    try:
        values = cmds.keyframe(
            attr,
            query=True,
            time=(frame, frame),
            valueChange=True,
        ) or []
    except Exception:
        values = []
    if values:
        return values[-1]

    try:
        frames = cmds.keyframe(
            attr,
            query=True,
            timeChange=True,
        ) or []
    except Exception:
        return None

    previous = [
        keyed_frame for keyed_frame in frames
        if int(round(float(keyed_frame))) <= int(frame)
    ]
    if not previous:
        return None
    nearest = max(previous)
    try:
        values = cmds.keyframe(
            attr,
            query=True,
            time=(nearest, nearest),
            valueChange=True,
        ) or []
    except Exception:
        values = []
    return values[-1] if values else None


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
        crash_logger.log_event(
            "maya_call_begin",
            action="set_blendshape_weight",
            call="cmds.blendShape",
            node=node,
            weight_index=index,
            value=value,
        )
        cmds.blendShape(node, edit=True, weight=(index, value))
        crash_logger.log_event(
            "maya_call_end",
            action="set_blendshape_weight",
            call="cmds.blendShape",
            node=node,
            weight_index=index,
            value=value,
        )


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
