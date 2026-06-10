import maya.cmds as cmds
import math

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
        radius = cmds.floatFieldGrp(radius_field, query=True, value1=True)
        height = cmds.floatFieldGrp(height_field, query=True, value1=True)
        turns = cmds.intFieldGrp(turns_field, query=True, value1=True)
        points = cmds.intFieldGrp(points_field, query=True, value1=True)
        create_spiral_curve(radius, height, turns, points)

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

def ensure_layout_uvset_from_map1(*args):
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
