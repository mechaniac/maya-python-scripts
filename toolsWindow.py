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

def prep_function(*args):
    cmds.delete(cmds.ls(type='constraint'))
    cmds.delete(cmds.ls(type='character'))

def remove_plugin_requires():
    for info in cmds.fileInfo(q=True):
        if any(p in info for p in plugin_blacklist):
            try:
                cmds.fileInfo(info, remove=True)
                print(f"? Removed plugin require: {info}")
            except:
                print(f"?? Could not remove plugin require: {info}")

def remove_script_nodes():
    script_nodes = cmds.ls(type='script')
    for sn in script_nodes:
        try:
            cmds.delete(sn)
            print(f"? Deleted script node: {sn}")
        except:
            print(f"?? Could not delete: {sn}")

def remove_mentalray_nodes():
    for node in mental_ray_nodes:
        if cmds.objExists(node):
            try:
                cmds.delete(node)
                print(f"? Deleted mental ray node: {node}")
            except:
                print(f"?? Could not delete: {node}")

def run_cleanup(*args):
    prep_function()
    remove_plugin_requires()
    remove_script_nodes()
    remove_mentalray_nodes()
    print("?? Scene cleanup complete.")

# === Rename Selected Nodes ===
def rename_selected(*args):
    base_name = cmds.textField("renameBaseField", q=True, text=True)
    if not base_name:
        print("?? Please enter a base name.")
        return

    selected = cmds.ls(selection=True)
    if not selected:
        print("?? No objects selected.")
        return

    for i, obj in enumerate(selected):
        suffix = f"_{i:02d}"
        new_name = base_name + suffix
        cmds.rename(obj, new_name)

# === Delete extra UV sets ===
def delete_extra_uv_sets(*args):
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        print("?? No meshes selected.")
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
                            print(f"? Deleted UV set '{uv_set}' on {shape}")
                        except:
                            print(f"?? Failed to delete UV set '{uv_set}' on {shape}")

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

# === Spiral Curve UI ===
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
        print("? Deleted circularRingGroup")
    else:
        print("?? No instance group to delete.")

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
        print("?? No meshes selected.")
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
                        print(f"? Deleted extra UV set '{uv_set}' on {shape}")
                    except:
                        print(f"?? Failed to delete UV set '{uv_set}' on {shape}")

def rename_uv_sets(*args):
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        print("?? No meshes selected.")
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
                        print(f"? Renamed {uv_sets[0]} to 'map1' on {shape}")
                    except:
                        print(f"?? Failed to rename {uv_sets[0]} to 'map1' on {shape}")
            if len(uv_sets) >= 2:
                if "layout" not in uv_sets:
                    try:
                        cmds.polyUVSet(shape, rename=True, uvSet=uv_sets[1], newUVSet="layout")
                        print(f"? Renamed {uv_sets[1]} to 'layout' on {shape}")
                    except:
                        print(f"?? Failed to rename {uv_sets[1]} to 'layout' on {shape}")


def set_uv_set(index):
    meshes = cmds.ls(selection=True, type='transform')
    if not meshes:
        print("?? No meshes selected.")
        return

    for mesh in meshes:
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        for shape in shapes:
            if cmds.nodeType(shape) != "mesh":
                continue
            uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
            if len(uv_sets) > index:
                cmds.polyUVSet(shape, currentUVSet=True, uvSet=uv_sets[index])
                print(f"? Set current UV set of {shape} to '{uv_sets[index]}'")

def set_uv_set_0(*args):
    set_uv_set(0)

def set_uv_set_1(*args):
    set_uv_set(1)


# === Main Window ===
def show_cleanup_window():
    if cmds.window("sceneCleanupWin", exists=True):
        cmds.deleteUI("sceneCleanupWin")

    cmds.window("sceneCleanupWin", title="Scene Tools", widthHeight=(280, 400), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnAlign="center")

    cmds.button(label="Clean Scene", height=40, command=run_cleanup)

    cmds.separator(height=10)
    cmds.text(label="Rename Selected Nodes")
    cmds.textField("renameBaseField", placeholderText="Base name here...")
    cmds.button(label="Rename with _##", command=rename_selected)

    cmds.separator(height=10)
    cmds.text(label="UV Edits", align="center", height=20)
    cmds.button(label="Delete Extra UV Sets", command=delete_extra_uv_sets)
    cmds.button(label="Delete Third UVset", command=delete_third_uv_set)
    cmds.button(label="Rename UVsets", command=rename_uv_sets)
    cmds.button(label="Set UVs to 00", command=set_uv_set_0)
    cmds.button(label="Set UVs to 01", command=set_uv_set_1)


    cmds.separator(height=10)
    cmds.text(label="Layout Tools", align="center", height=20)
    cmds.floatField("gridSpacingField", value=5.0)
    cmds.button(label="Grid Place Selected", command=grid_place_selected)

    cmds.separator(height=10)
    cmds.button(label="Create Spiral Curve", command=open_spiral_window)

    cmds.separator(height=10)
    cmds.text(label="Circular Instancing", align="center", height=20)
    cmds.intField("instanceCountField", value=8)
    cmds.floatField("instanceRadiusField", value=0.0)
    cmds.button(label="Create Instances", command=on_create_instances)
    cmds.button(label="Delete Instances", command=delete_instances)
    cmds.button(label="Create Copies", command=on_create_copies)
    cmds.separator(height=10)
    cmds.text(label="Remove String From Name", align="center")
    cmds.textField("removeStringField", placeholderText="String to remove...")
    cmds.button(label="Remove From Selected Names", command=remove_string_from_names)


    cmds.showWindow("sceneCleanupWin")

# Show it
show_cleanup_window()
