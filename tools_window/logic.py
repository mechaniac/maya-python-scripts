import maya.cmds as cmds
import math

import crash_logger
import maya_display
from . import chain_creator

_CHAIN_CREATE_BUSY = False
_CHAIN_COUNT_UPDATE_PENDING = False
_CHAIN_PENDING_COUNT = None
_CHAIN_MENU_LABELS = {}
_CHAIN_SYNCING = False

# === Plugin and node cleanup ===
plugin_blacklist = [
    "CP_Exporter2009",
    "ByronsPolyTools",
    "RwExport",
    "Mayatomr",
]

mental_ray_nodes = [
    "mentalrayItemsList",
    "mentalrayGlobals",
    "mentalrayOptions",
    "mentalrayFramebuffer",
]


def toggle_display_affected(*args):
    """Toggle 'Display Affected' (history highlight) on selected nodes."""
    current = cmds.displayPref(q=True, displayAffected=True)
    cmds.displayPref(displayAffected=not current)
    print("Display Affected (History Highlight) is now: {0}".format(
        not current))


def ensure_display_affected(*args):
    """Force Display Affected on for tools that use construction history."""
    maya_display.ensure_display_affected()


def prep_function(*args):
    cmds.delete(cmds.ls(type='constraint'))
    cmds.delete(cmds.ls(type='character'))

def remove_plugin_requires():
    for info in cmds.fileInfo(q=True):
        if any(p in info for p in plugin_blacklist):
            try:
                cmds.fileInfo(info, remove=True)
                print(f"Removed plugin require: {info}")
            except:
                print(f"Could not remove plugin require: {info}")

def remove_script_nodes():
    script_nodes = cmds.ls(type='script')
    for sn in script_nodes:
        try:
            cmds.delete(sn)
            print(f"Deleted script node: {sn}")
        except:
            print(f"Could not delete: {sn}")

def remove_mentalray_nodes():
    for node in mental_ray_nodes:
        if cmds.objExists(node):
            try:
                cmds.delete(node)
                print(f"Deleted mental ray node: {node}")
            except:
                print(f"Could not delete: {node}")

def run_cleanup(*args):
    prep_function()
    remove_plugin_requires()
    remove_script_nodes()
    remove_mentalray_nodes()
    print("Scene cleanup complete.")

# === Rename Selected Nodes ===
def rename_selected(*args):
    base_name = cmds.textField("renameBaseField", q=True, text=True)
    if not base_name:
        print("Please enter a base name.")
        return

    selected = cmds.ls(selection=True)
    if not selected:
        print("No objects selected.")
        return

    for i, obj in enumerate(selected):
        suffix = f"_{i:02d}"
        new_name = base_name + suffix
        cmds.rename(obj, new_name)

# === Delete extra UV sets ===
def delete_extra_uv_sets(*args):
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        print("No meshes selected.")
        return

    for mesh in meshes:
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        for shape in shapes:
            if cmds.nodeType(shape) == "mesh":
                uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
                current_set = cmds.polyUVSet(shape, q=True, currentUVSet=True)[0]

                for uv_set in uv_sets:
                    if uv_set != current_set:
                        try:
                            cmds.polyUVSet(shape, delete=True, uvSet=uv_set)
                            print(f"Deleted UV set '{uv_set}' on {shape}")
                        except:
                            print(f"Failed to delete UV set '{uv_set}' on {shape}")

# === Grid placement ===
def grid_place_selected(*args):
    spacing = cmds.floatField("gridSpacingField", q=True, value=True)
    selected = cmds.ls(selection=True)
    if not selected:
        cmds.warning("No objects selected.")
        return
    count = len(selected)
    grid_size = int(math.ceil(math.sqrt(count)))
    for i, obj in enumerate(selected):
        x = (i % grid_size) * spacing
        z = (i // grid_size) * spacing
        cmds.xform(obj, worldSpace=True, translation=(x, 0, z))

# === Spiral Curve ===
def create_spiral_curve(radius=5.0, height=10.0, turns=3, points_per_turn=20):
    total_points = int(turns * points_per_turn)
    points = []
    for i in range(total_points + 1):
        angle = (2 * math.pi) * (i / float(points_per_turn))
        x = radius * math.cos(angle)
        z = radius * math.sin(angle)
        y = (height / float(total_points)) * i
        points.append((x, y, z))
    return cmds.curve(p=points, d=3)

def open_spiral_window(*args):
    if cmds.window("spiralCurveWin", exists=True):
        cmds.deleteUI("spiralCurveWin")
    cmds.window("spiralCurveWin", title="Spiral Curve Generator", sizeable=True, widthHeight=(300, 200))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=5)

    radius_field = cmds.floatFieldGrp(label="Radius", numberOfFields=1, value1=5.0)
    height_field = cmds.floatFieldGrp(label="Height", numberOfFields=1, value1=10.0)
    turns_field = cmds.intFieldGrp(label="Turns", numberOfFields=1, value1=3)
    points_field = cmds.intFieldGrp(label="Points/Turn", numberOfFields=1, value1=20)

    def on_create_pressed(*args):
        crash_logger.log_event(
            "button_pressed",
            action="Create Spiral Curve",
            window="spiralCurveWin",
            maya=crash_logger.maya_state(),
        )
        try:
            radius = cmds.floatFieldGrp(radius_field, query=True, value1=True)
            height = cmds.floatFieldGrp(height_field, query=True, value1=True)
            turns = cmds.intFieldGrp(turns_field, query=True, value1=True)
            points = cmds.intFieldGrp(points_field, query=True, value1=True)
            crash_logger.log_event(
                "button_start",
                action="Create Spiral Curve",
                window="spiralCurveWin",
            )
            create_spiral_curve(radius, height, turns, points)
            crash_logger.log_event(
                "button_return",
                action="Create Spiral Curve",
                window="spiralCurveWin",
                maya=crash_logger.maya_state(),
            )
        except Exception as exc:
            crash_logger.log_exception(
                "button_exception",
                action="Create Spiral Curve",
                exc=exc,
            )
            cmds.warning(str(exc))

    cmds.button(label="Create Spiral Curve", command=on_create_pressed)
    cmds.showWindow("spiralCurveWin")

# === Circular Instancing / Copying ===
def create_instance_circle(instances=8, radius=0.0):
    selected = cmds.ls(selection=True)
    if not selected:
        cmds.warning("No object selected.")
        return

    if instances < 2:
        cmds.warning("Need at least 2 objects total for a ring.")
        return

    original = selected[0]
    angle_step = 360.0 / instances

    group_name = "circularRingGroup"
    if cmds.objExists(group_name):
        cmds.delete(group_name)
    group = cmds.group(empty=True, name=group_name)

    for i in range(1, instances):
        angle = angle_step * i
        radians = math.radians(angle)
        x = math.sin(radians) * radius
        z = math.cos(radians) * radius
        inst = cmds.instance(original)[0]
        cmds.xform(inst, worldSpace=True,
                   translation=(x, 0, z),
                   rotation=(0, -angle, 0))
        cmds.parent(inst, group)

def create_copy_circle(instances=8, radius=0.0):
    selected = cmds.ls(selection=True)
    if not selected:
        cmds.warning("No object selected.")
        return

    if instances < 2:
        cmds.warning("Need at least 2 objects total for a ring.")
        return

    original = selected[0]
    angle_step = 360.0 / instances

    group_name = "circularRingGroup"
    if cmds.objExists(group_name):
        cmds.delete(group_name)
    group = cmds.group(empty=True, name=group_name)

    for i in range(1, instances):
        angle = angle_step * i
        radians = math.radians(angle)
        x = math.sin(radians) * radius
        z = math.cos(radians) * radius
        copy = cmds.duplicate(original)[0]
        cmds.xform(copy, worldSpace=True,
                   translation=(x, 0, z),
                   rotation=(0, -angle, 0))
        cmds.parent(copy, group)

def delete_instances(*args):
    group_name = "circularRingGroup"
    if cmds.objExists(group_name):
        cmds.delete(group_name)
        print("Deleted circularRingGroup")
    else:
        print("No instance group to delete.")

def on_create_instances(*args):
    count = cmds.intField("instanceCountField", q=True, value=True)
    radius = cmds.floatField("instanceRadiusField", q=True, value=True)
    create_instance_circle(count, radius)

def on_create_copies(*args):
    count = cmds.intField("instanceCountField", q=True, value=True)
    radius = cmds.floatField("instanceRadiusField", q=True, value=True)
    create_copy_circle(count, radius)


def create_chain_from_ui(*args):
    global _CHAIN_CREATE_BUSY
    if _CHAIN_CREATE_BUSY:
        cmds.warning("Chain creation is already running.")
        return

    ensure_display_affected()
    count = cmds.intSliderGrp("chainLinkCountField", q=True, value=True)
    roll = cmds.floatSliderGrp("chainAlternateRollField", q=True, value=True)
    scale = 2.0
    if cmds.floatSliderGrp("chainLinkScaleField", exists=True):
        scale = cmds.floatSliderGrp("chainLinkScaleField", q=True, value=True)
    selection = cmds.ls(selection=True, long=True) or []
    _CHAIN_CREATE_BUSY = True

    def _run():
        global _CHAIN_CREATE_BUSY
        try:
            chain = chain_creator.create_from_selection(
                count,
                roll,
                selection,
                scale,
            )
            refresh_chain_menu_from_ui(chain)
        except Exception as exc:
            cmds.warning("Chain creation failed: {0}".format(exc))
        finally:
            _CHAIN_CREATE_BUSY = False

    _execute_deferred(_run)


def update_chain_roll_from_ui(*args):
    if _CHAIN_SYNCING:
        return
    if not cmds.floatSliderGrp("chainAlternateRollField", exists=True):
        return
    roll = cmds.floatSliderGrp("chainAlternateRollField", q=True, value=True)
    chain_creator.set_alternate_roll(roll, _selected_chain_from_menu())


def update_chain_scale_from_ui(*args):
    if _CHAIN_SYNCING:
        return
    if not cmds.floatSliderGrp("chainLinkScaleField", exists=True):
        return
    scale = cmds.floatSliderGrp("chainLinkScaleField", q=True, value=True)
    chain_creator.set_link_scale(scale, _selected_chain_from_menu())


def update_chain_count_from_ui(*args):
    global _CHAIN_COUNT_UPDATE_PENDING, _CHAIN_PENDING_COUNT
    if _CHAIN_SYNCING:
        return
    if not cmds.intSliderGrp("chainLinkCountField", exists=True):
        return
    chain = _selected_chain_from_menu() or chain_creator.active_chain()
    if not chain:
        return

    ensure_display_affected()
    _CHAIN_PENDING_COUNT = cmds.intSliderGrp(
        "chainLinkCountField", q=True, value=True)
    if _CHAIN_COUNT_UPDATE_PENDING:
        return

    _CHAIN_COUNT_UPDATE_PENDING = True

    def _run():
        global _CHAIN_COUNT_UPDATE_PENDING, _CHAIN_PENDING_COUNT
        try:
            count = _CHAIN_PENDING_COUNT
            chain = _selected_chain_from_menu() or chain_creator.active_chain()
            if chain and count is not None:
                chain_creator.set_link_count(count, chain)
                refresh_chain_menu_from_ui(chain)
        except Exception as exc:
            cmds.warning("Chain link count update failed: {0}".format(exc))
        finally:
            _CHAIN_COUNT_UPDATE_PENDING = False

    _execute_deferred(_run)


def refresh_chain_menu_from_ui(select_chain=None, *args):
    menu = "chainActiveMenu"
    if not cmds.optionMenu(menu, exists=True):
        return

    ensure_display_affected()
    _CHAIN_MENU_LABELS.clear()
    for item in cmds.optionMenu(menu, q=True, itemListLong=True) or []:
        cmds.deleteUI(item)

    chains = chain_creator.chain_groups()
    if not chains:
        cmds.menuItem(parent=menu, label="No chains")
        _sync_chain_controls(None)
        return

    used = {}
    selected_label = None
    active = select_chain or chain_creator.active_chain()
    for chain in chains:
        label = _unique_chain_label(chain, used)
        _CHAIN_MENU_LABELS[label] = chain
        cmds.menuItem(parent=menu, label=label)
        if active and chain == active:
            selected_label = label

    selected_label = selected_label or next(iter(_CHAIN_MENU_LABELS.keys()))
    cmds.optionMenu(menu, edit=True, value=selected_label)
    chain_creator.set_active_chain(_CHAIN_MENU_LABELS[selected_label])
    chain_creator.refresh_chain_orientation(_CHAIN_MENU_LABELS[selected_label])
    active_chain = chain_creator.active_chain() or _CHAIN_MENU_LABELS[selected_label]
    _CHAIN_MENU_LABELS[selected_label] = active_chain
    _sync_chain_controls(active_chain)


def select_chain_from_ui(*args):
    chain = _selected_chain_from_menu()
    if chain:
        ensure_display_affected()
        chain_creator.set_active_chain(chain)
        chain_creator.refresh_chain_orientation(chain)
        active_chain = chain_creator.active_chain() or chain
        label = cmds.optionMenu("chainActiveMenu", q=True, value=True)
        _CHAIN_MENU_LABELS[label] = active_chain
        _sync_chain_controls(active_chain)


def delete_active_chain_from_ui(*args):
    def _run():
        chain_creator.delete_active_chain()
        refresh_chain_menu_from_ui()

    _execute_deferred(_run)


def _selected_chain_from_menu():
    menu = "chainActiveMenu"
    if not cmds.optionMenu(menu, exists=True):
        return None
    label = cmds.optionMenu(menu, q=True, value=True)
    chain = _CHAIN_MENU_LABELS.get(label)
    if chain and cmds.objExists(chain):
        return chain
    return None


def _unique_chain_label(chain, used):
    base = chain_creator.chain_label(chain)
    count = used.get(base, 0) + 1
    used[base] = count
    return base if count == 1 else "{0} ({1})".format(base, count)


def _sync_chain_controls(chain):
    global _CHAIN_SYNCING
    if not chain:
        return
    settings = chain_creator.chain_settings(chain)
    _CHAIN_SYNCING = True
    try:
        if cmds.intSliderGrp("chainLinkCountField", exists=True):
            cmds.intSliderGrp(
                "chainLinkCountField",
                edit=True,
                value=settings.get("link_count", 16),
            )
        if cmds.floatSliderGrp("chainAlternateRollField", exists=True):
            cmds.floatSliderGrp(
                "chainAlternateRollField",
                edit=True,
                value=settings.get("alternate_roll", 90.0),
            )
        if cmds.floatSliderGrp("chainLinkScaleField", exists=True):
            cmds.floatSliderGrp(
                "chainLinkScaleField",
                edit=True,
                value=settings.get("link_scale", 2.0),
            )
    finally:
        _CHAIN_SYNCING = False


def _execute_deferred(callback):
    try:
        import maya.utils as maya_utils
        maya_utils.executeDeferred(callback)
    except Exception:
        callback()

def remove_string_from_names(*args):
    remove_str = cmds.textField("removeStringField", q=True, text=True)
    if not remove_str:
        cmds.warning("No string entered to remove.")
        return

    selected = cmds.ls(selection=True)
    if not selected:
        cmds.warning("No objects selected.")
        return

    for obj in selected:
        new_name = obj.replace(remove_str, "")
        if new_name != obj:
            cmds.rename(obj, new_name)

def delete_third_uv_set(*args):
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        print("No meshes selected.")
        return

    for mesh in meshes:
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        for shape in shapes:
            if cmds.nodeType(shape) != "mesh":
                continue
            uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
            if len(uv_sets) > 2:
                for uv_set in uv_sets[2:]:
                    try:
                        cmds.polyUVSet(shape, delete=True, uvSet=uv_set)
                        print(f"Deleted extra UV set '{uv_set}' on {shape}")
                    except:
                        print(f"Failed to delete UV set '{uv_set}' on {shape}")

def rename_uv_sets(*args):
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        print("No meshes selected.")
        return

    for mesh in meshes:
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        for shape in shapes:
            if cmds.nodeType(shape) != "mesh":
                continue

            uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
            if len(uv_sets) >= 1:
                if "map1" not in uv_sets:
                    try:
                        cmds.polyUVSet(shape, rename=True, uvSet=uv_sets[0], newUVSet="map1")
                        print(f"Renamed {uv_sets[0]} to 'map1' on {shape}")
                    except:
                        print(f"Failed to rename {uv_sets[0]} to 'map1' on {shape}")
            if len(uv_sets) >= 2:
                if "layout" not in uv_sets:
                    try:
                        cmds.polyUVSet(shape, rename=True, uvSet=uv_sets[1], newUVSet="layout")
                        print(f"Renamed {uv_sets[1]} to 'layout' on {shape}")
                    except:
                        print(f"Failed to rename {uv_sets[1]} to 'layout' on {shape}")

def set_uv_set(index):
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        print("No meshes selected.")
        return

    for mesh in meshes:
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        for shape in shapes:
            if cmds.nodeType(shape) != "mesh":
                continue
            uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
            if len(uv_sets) > index:
                cmds.polyUVSet(shape, currentUVSet=True, uvSet=uv_sets[index])
                print(f"Set current UV set of {shape} to '{uv_sets[index]}'")

def set_uv_set_0(*args):
    set_uv_set(0)

def set_uv_set_1(*args):
    set_uv_set(1)


def rotate_selected_uvs_from_ui(*args):
    degrees = 90.0
    if cmds.floatField("rotateUvDegreesField", exists=True):
        degrees = cmds.floatField(
            "rotateUvDegreesField",
            query=True,
            value=True,
        )
    rotate_selected_uvs_clockwise(degrees)


def rotate_selected_uvs_clockwise(degrees=90.0):
    selection = cmds.ls(selection=True, long=True, flatten=True) or []
    uvs = _selected_uv_components()
    if not uvs:
        cmds.warning("Select UVs, UV components, faces, edges, or mesh transforms.")
        return

    coords = cmds.polyEditUV(uvs, query=True) or []
    if len(coords) < 2:
        cmds.warning("Could not read selected UV coordinates.")
        return

    us = coords[0::2]
    vs = coords[1::2]
    pivot_u = sum(us) / float(len(us))
    pivot_v = sum(vs) / float(len(vs))

    try:
        cmds.polyEditUV(
            uvs,
            relative=True,
            rotation=True,
            angle=-float(degrees),
            pivotU=pivot_u,
            pivotV=pivot_v,
        )
    except TypeError:
        cmds.polyEditUV(
            uvs,
            relative=True,
            angle=-float(degrees),
            pivotU=pivot_u,
            pivotV=pivot_v,
        )

    if selection:
        try:
            cmds.select(selection, replace=True)
        except Exception:
            pass

    print(
        "Rotated {0} UV(s) clockwise by {1:.3f} degrees around "
        "({2:.4f}, {3:.4f}).".format(
            len(uvs),
            float(degrees),
            pivot_u,
            pivot_v,
        )
    )


def _selected_uv_components():
    selection = cmds.ls(selection=True, long=True, flatten=True) or []
    if not selection:
        return []

    converted = cmds.polyListComponentConversion(selection, toUV=True) or []
    uvs = cmds.ls(converted, flatten=True) or []
    uvs = [uv for uv in uvs if ".map[" in uv]
    if uvs:
        return list(dict.fromkeys(uvs))

    fallback = []
    for item in selection:
        node = item.split(".", 1)[0]
        if not cmds.objExists(node):
            continue
        node_type = cmds.nodeType(node)
        shapes = []
        if node_type == "mesh":
            shapes = [node]
        elif node_type == "transform":
            shapes = cmds.listRelatives(
                node,
                shapes=True,
                fullPath=True,
                noIntermediate=True,
                type="mesh",
            ) or []

        for shape in shapes:
            count = cmds.polyEvaluate(shape, uvcoord=True) or 0
            if count:
                fallback.append("{0}.map[0:{1}]".format(shape, int(count) - 1))

    return cmds.ls(fallback, flatten=True) or []


def clean_vertex_color_sets(*args):
    """Delete every vertex color set on selected polygon meshes."""
    shapes = _selected_mesh_shapes(include_descendants=True)
    if not shapes:
        cmds.warning("No polygon mesh shapes found in selection.")
        return

    removed, failed = _clean_vertex_color_sets_on_shapes(shapes)
    _report_vertex_color_cleanup(removed, failed)


def clean_poly_mesh_display(*args):
    """Reset common mesh display problems that cause black or invisible faces."""
    selection = cmds.ls(selection=True, long=True, flatten=True) or []
    explicit_transforms = set(_selected_explicit_transforms())
    shapes = _selected_mesh_shapes(include_descendants=True)
    included_intermediate = False
    if not shapes:
        shapes = _selected_mesh_shapes(
            include_descendants=True,
            include_intermediate=True,
        )
        included_intermediate = True

    if not shapes:
        cmds.warning("No polygon mesh shapes found in selection.")
        return

    report = {
        "shapes": 0,
        "parents": 0,
        "attrs": 0,
        "color_sets": 0,
        "materials": 0,
        "normal_unlocks": 0,
        "errors": [],
    }
    seen_parents = set()

    auto_key_state = _set_auto_key_state(False)
    try:
        for shape in shapes:
            report["shapes"] += 1
            parent = _mesh_parent(shape)
            if (
                parent
                and parent in explicit_transforms
                and parent not in seen_parents
            ):
                seen_parents.add(parent)
                report["parents"] += 1
                _reset_display_attrs(parent, _TRANSFORM_DISPLAY_ATTRS, report)

            _reset_display_attrs(shape, _MESH_DISPLAY_ATTRS, report)

            if included_intermediate:
                _safe_set_attr(shape, "intermediateObject", 0, report)

            if _unlock_mesh_normals(shape):
                report["normal_unlocks"] += 1

            removed, failed = _clean_vertex_color_sets_on_shapes([shape])
            report["color_sets"] += len(removed)
            for failed_shape, color_set, error in failed:
                report["errors"].append(
                    "{0} color set {1}: {2}".format(
                        failed_shape,
                        color_set,
                        error,
                    )
                )

            if _ensure_basic_shading_group(shape):
                report["materials"] += 1
    finally:
        _set_auto_key_state(auto_key_state)

    try:
        cmds.refresh(force=True)
    except Exception:
        pass

    if selection:
        try:
            cmds.select(selection, replace=True)
        except Exception:
            pass

    print(
        "Clean Poly Mesh: {shapes} shape(s), {parents} transform(s), "
        "{attrs} attr reset(s), {color_sets} color set(s) removed, "
        "{materials} default material repair(s), {normal_unlocks} normal "
        "unlock(s).".format(**report)
    )
    if report["errors"]:
        for error in report["errors"]:
            print("Clean Poly Mesh warning: {0}".format(error))
        cmds.warning(
            "Clean Poly Mesh finished with {0} warning(s). See Script Editor.".format(
                len(report["errors"])
            )
        )


def _clean_vertex_color_sets_on_shapes(shapes):
    removed = []
    failed = []
    for shape in shapes:
        try:
            color_sets = cmds.polyColorSet(
                shape,
                query=True,
                allColorSets=True,
            ) or []
        except Exception as exc:
            failed.append((shape, "<query>", str(exc)))
            continue

        for color_set in color_sets:
            ok, error = _delete_vertex_color_set(shape, color_set)
            if ok:
                removed.append((shape, color_set))
            else:
                failed.append((shape, color_set, error))

        if color_sets:
            try:
                cmds.setAttr(shape + ".displayColors", 0)
            except Exception:
                pass

    return removed, failed


def _report_vertex_color_cleanup(removed, failed):
    if removed:
        for shape, color_set in removed:
            print("Deleted vertex color set '{0}' on {1}".format(
                color_set,
                shape,
            ))
        print("Cleaned {0} vertex color set(s) on {1} mesh shape(s).".format(
            len(removed),
            len(set(shape for shape, _ in removed)),
        ))
    else:
        print("No vertex color sets found on selected mesh shape(s).")

    if failed:
        for shape, color_set, error in failed:
            print("Failed to delete vertex color set '{0}' on {1}: {2}".format(
                color_set,
                shape,
                error,
            ))
        cmds.warning(
            "Could not remove {0} vertex color set(s). See Script Editor.".format(
                len(failed)
            )
        )


_TRANSFORM_DISPLAY_ATTRS = {
    "visibility": 1,
    "overrideEnabled": 0,
    "overrideDisplayType": 0,
    "overrideLevelOfDetail": 0,
    "overrideVisibility": 1,
    "overrideShading": 1,
    "lodVisibility": 1,
}

_MESH_DISPLAY_ATTRS = {
    "visibility": 1,
    "template": 0,
    "displayColors": 0,
    "displayVertices": 0,
    "displayBorders": 0,
    "displayCenter": 0,
    "displayTriangles": 0,
    "displayInvisibleFaces": 0,
    "displayNonPlanar": 0,
    "displayNormal": 0,
    "displayTangent": 0,
    "backfaceCulling": 0,
    "doubleSided": 1,
    "opposite": 0,
    "overrideEnabled": 0,
    "overrideDisplayType": 0,
    "overrideLevelOfDetail": 0,
    "overrideVisibility": 1,
    "overrideShading": 1,
}


def _reset_display_attrs(node, attrs, report):
    for attr, value in attrs.items():
        _safe_set_attr(node, attr, value, report)


def _safe_set_attr(node, attr, value, report=None):
    plug = node + "." + attr
    if not cmds.objExists(plug):
        return False
    try:
        if cmds.getAttr(plug, lock=True):
            cmds.setAttr(plug, lock=False)
    except Exception:
        pass
    try:
        cmds.setAttr(plug, value)
        if report is not None:
            report["attrs"] += 1
        return True
    except Exception as exc:
        if report is not None:
            report["errors"].append("{0}: {1}".format(plug, exc))
        return False


def _unlock_mesh_normals(shape):
    try:
        cmds.polyNormalPerVertex(shape, unFreezeNormal=True)
        return True
    except Exception:
        try:
            cmds.polyNormalPerVertex(shape + ".vtx[*]", unFreezeNormal=True)
            return True
        except Exception:
            return False


def _ensure_basic_shading_group(shape):
    shading_engines = cmds.listConnections(
        shape,
        type="shadingEngine",
        destination=True,
        source=False,
    ) or []
    if shading_engines:
        return False
    if not cmds.objExists("initialShadingGroup"):
        return False
    try:
        cmds.sets(shape, edit=True, forceElement="initialShadingGroup")
        return True
    except Exception:
        return False


def _mesh_parent(shape):
    parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
    return parents[0] if parents else None


def _delete_vertex_color_set(shape, color_set):
    try:
        cmds.polyColorSet(shape, delete=True, colorSet=color_set)
        return True, ""
    except Exception as first_error:
        try:
            cmds.polyColorSet(
                shape,
                currentColorSet=True,
                colorSet=color_set,
            )
            cmds.polyColorSet(shape, delete=True)
            return True, ""
        except Exception as second_error:
            return False, "{0}; {1}".format(first_error, second_error)


def _selected_mesh_shapes(include_descendants=False, include_intermediate=False):
    selection = cmds.ls(selection=True, long=True, flatten=True) or []
    shapes = []
    seen = set()

    def add_shape(shape):
        if not shape or not cmds.objExists(shape):
            return
        try:
            if cmds.nodeType(shape) != "mesh":
                return
        except Exception:
            return

        try:
            if (
                cmds.getAttr(shape + ".intermediateObject")
                and not include_intermediate
            ):
                return
        except Exception:
            pass

        long_name = (cmds.ls(shape, long=True) or [shape])[0]
        if long_name in seen:
            return
        seen.add(long_name)
        shapes.append(long_name)

    for item in selection:
        node = item.split(".", 1)[0]
        matches = cmds.ls(node, long=True) or [node]
        for match in matches:
            if not cmds.objExists(match):
                continue

            node_type = cmds.nodeType(match)
            if node_type == "mesh":
                add_shape(match)
                continue

            if node_type != "transform":
                continue

            for shape in cmds.listRelatives(
                match,
                shapes=True,
                fullPath=True,
            ) or []:
                add_shape(shape)

            if include_descendants:
                for shape in cmds.listRelatives(
                    match,
                    allDescendents=True,
                    fullPath=True,
                    type="mesh",
                ) or []:
                    add_shape(shape)

    return shapes


def _selected_explicit_transforms():
    transforms = []
    seen = set()
    for item in cmds.ls(selection=True, long=True, flatten=True) or []:
        node = item.split(".", 1)[0]
        if not cmds.objExists(node):
            continue
        if cmds.nodeType(node) == "mesh":
            parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
            node = parents[0] if parents else node
        if not cmds.objExists(node) or cmds.nodeType(node) != "transform":
            continue
        long_name = (cmds.ls(node, long=True) or [node])[0]
        if long_name in seen:
            continue
        seen.add(long_name)
        transforms.append(long_name)
    return transforms


def _set_auto_key_state(enabled):
    try:
        previous = bool(cmds.autoKeyframe(query=True, state=True))
    except Exception:
        previous = False
    try:
        cmds.autoKeyframe(state=bool(enabled))
    except Exception:
        pass
    return previous


def ensure_layout_uvset_from_map1(*args):
    ensure_display_affected()
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        cmds.warning("No meshes selected.")
        return

    for mesh in meshes:
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        for shape in shapes:
            if cmds.nodeType(shape) != "mesh":
                continue

            uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
            current = (cmds.polyUVSet(shape, q=True, currentUVSet=True) or ["map1"])[0]

            src = "map1" if "map1" in uv_sets else (uv_sets[0] if uv_sets else None)
            if not src:
                print(f"No UV sets found on {shape}")
                continue

            if "layout" in uv_sets:
                print(f"'{shape}' already has UV set 'layout' (skipping create)")
                continue

            try:
                cmds.polyUVSet(shape, create=True, uvSet="layout")
                cmds.polyCopyUV(shape, uvSetNameInput=src, uvSetName="layout")
                cmds.polyUVSet(shape, currentUVSet=True, uvSet=current)
                print(f"Created 'layout' on {shape} and copied from '{src}'")
            except Exception as e:
                print(f"Failed on {shape}: {e}")

def set_uv0_to_lezoo_color_gradient(*args):
    ensure_display_affected()
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        cmds.warning("No meshes selected.")
        return

    target_u = 1.0 / 81.0
    target_v = 1.0 / 4.0

    for mesh in meshes:
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        for shape in shapes:
            if cmds.nodeType(shape) != "mesh":
                continue

            uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
            if not uv_sets:
                print(f"No UV sets on {shape}")
                continue

            uv0 = "map1" if "map1" in uv_sets else uv_sets[0]

            try:
                prev_current = (cmds.polyUVSet(shape, q=True, currentUVSet=True) or [uv0])[0]
                cmds.polyUVSet(shape, currentUVSet=True, uvSet=uv0)

                shells = cmds.polyEvaluate(shape, uvShell=True) or 0
                if shells <= 0:
                    print(f"No UV shells on {shape}")
                    cmds.polyUVSet(shape, currentUVSet=True, uvSet=prev_current)
                    continue

                for shell_index in range(shells):
                    cmds.select(clear=True)
                    cmds.polySelectConstraint(mode=3, type=0x0010, shell=True, uvShell=shell_index)
                    cmds.select(cmds.polyListComponentConversion(shape, toUV=True))
                    uvs = cmds.ls(selection=True, flatten=True) or []
                    cmds.polySelectConstraint(disable=True)

                    if not uvs:
                        continue

                    cmds.polyEditUV(uvs, u=0, v=0)
                    cmds.polyNormalizeUV(uvs, normalizeType=1, preserveAspectRatio=False)
                    cmds.polyEditUV(uvs, relative=True, scaleU=target_u, scaleV=target_v)
                    cmds.polyEditUV(uvs, u=0.0, v=0.0)

                cmds.polyUVSet(shape, currentUVSet=True, uvSet=prev_current)
                print(f"UV0 set to LeZooColorGradient on {shape} (uvSet='{uv0}')")

            except Exception as e:
                try:
                    cmds.polySelectConstraint(disable=True)
                except:
                    pass
                print(f"Failed on {shape}: {e}")

def normalize_layout_uvs_non_overlapping(*args):
    ensure_display_affected()
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        cmds.warning("No meshes selected.")
        return

    for mesh in meshes:
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        for shape in shapes:
            if cmds.nodeType(shape) != "mesh":
                continue

            uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
            if not uv_sets:
                print(f"No UV sets on {shape}")
                continue

            if "layout" not in uv_sets:
                print(f"'{shape}' has no UV set named 'layout'")
                continue

            try:
                prev_current = (cmds.polyUVSet(shape, q=True, currentUVSet=True) or ["layout"])[0]
                cmds.polyUVSet(shape, currentUVSet=True, uvSet="layout")

                cmds.select(clear=True)
                cmds.select(cmds.polyListComponentConversion(shape, toUV=True))
                uvs = cmds.ls(selection=True, flatten=True) or []
                if not uvs:
                    print(f"No UVs on {shape}")
                    cmds.polyUVSet(shape, currentUVSet=True, uvSet=prev_current)
                    continue

                cmds.polyNormalizeUV(uvs, normalizeType=1, preserveAspectRatio=True)

                cmds.polyLayoutUV(
                    uvs,
                    layout=2,
                    rotateForBestFit=True,
                    scaleMode=1,
                    separate=1,
                    spacing=0.002
                )

                cmds.polyUVSet(shape, currentUVSet=True, uvSet=prev_current)
                print(f"Packed non-overlapping UV shells into 0..1 on {shape} (uvSet='layout')")

            except Exception as e:
                print(f"Failed on {shape}: {e}")

def log_uv_sets(*args):
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        cmds.warning("No meshes selected.")
        return

    records = []
    for mesh in meshes:
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        for shape in shapes:
            if cmds.nodeType(shape) != "mesh":
                continue
            uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
            records.append((len(uv_sets), shape, uv_sets))

    if not records:
        cmds.warning("No polygon mesh shapes found in selection.")
        return

    records.sort(key=lambda r: r[0])

    print("\n=== UV SETS PER MESH (sorted by UV set count) ===")
    counts_hist = {}
    total = 0

    for uv_count, shape, uv_sets in records:
        total += 1
        counts_hist[uv_count] = counts_hist.get(uv_count, 0) + 1
        uv_list = ", ".join(uv_sets) if uv_sets else "(none)"
        print(f"- {shape}  |  UV sets: {uv_count}  |  [{uv_list}]")

    print("\n--- Summary ---")
    for uv_count in sorted(counts_hist.keys()):
        print(f"{counts_hist[uv_count]} mesh(es) with {uv_count} UV set(s)")
    print(f"Total mesh shapes logged: {total}")
    print("=== END ===\n")

def _get_world_bbox(transform):
    bbox = cmds.exactWorldBoundingBox(transform)
    return bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]

def _safe_size(minv, maxv):
    return max(1e-8, maxv - minv)

def scale_selected_to_bounding_box(*args):
    tx = cmds.floatFieldGrp("fitBoxField", q=True, value1=True)
    ty = cmds.floatFieldGrp("fitBoxField", q=True, value2=True)
    tz = cmds.floatFieldGrp("fitBoxField", q=True, value3=True)

    if tx <= 0 or ty <= 0 or tz <= 0:
        cmds.warning("Bounding box dimensions must be > 0.")
        return

    selected = cmds.ls(selection=True, type='transform')
    if not selected:
        cmds.warning("No transforms selected.")
        return

    mode = cmds.optionMenu("fitScaleModeMenu", q=True, value=True)
    center_ground_pivot = cmds.checkBox("centerGroundPivotCB", q=True, value=True)

    for obj in selected:
        try:
            minx, miny, minz, maxx, maxy, maxz = _get_world_bbox(obj)
            sx = _safe_size(minx, maxx)
            sy = _safe_size(miny, maxy)
            sz = _safe_size(minz, maxz)

            fx = tx / sx
            fy = ty / sy
            fz = tz / sz

            if mode == "Uniform":
                f = min(fx, fy, fz)
                cmds.xform(obj, relative=True, scale=(f, f, f))
            else:
                cmds.xform(obj, relative=True, scale=(fx, fy, fz))

            if center_ground_pivot:
                cmds.xform(obj, centerPivots=True)

                minx, miny, minz, maxx, maxy, maxz = _get_world_bbox(obj)
                px, py, pz = cmds.xform(obj, q=True, ws=True, rp=True)
                cmds.xform(obj, ws=True, pivots=(px, miny, pz))

                px2, py2, pz2 = cmds.xform(obj, q=True, ws=True, rp=True)
                cmds.xform(obj, ws=True, t=(-px2, -py2, -pz2), r=True)

                cmds.makeIdentity(obj, apply=True, translate=True, rotate=True, scale=True, normal=False)
            else:
                cmds.makeIdentity(obj, apply=True, translate=True, rotate=True, scale=True, normal=False)

            print(f"Fit: {obj} -> target ({tx:.3f}, {ty:.3f}, {tz:.3f}) mode={mode} centerGroundPivot={center_ground_pivot}")

        except Exception as e:
            print(f"Failed on {obj}: {e}")
