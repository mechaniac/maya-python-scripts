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

    cmds.separator(height=10)
    cmds.text(label="Layout Tools", align="center", height=20)
    cmds.floatField("gridSpacingField", value=5.0)
    cmds.button(label="Grid Place Selected", command=grid_place_selected)

    cmds.separator(height=10)
    cmds.button(label="Create Spiral Curve", command=open_spiral_window)

    cmds.showWindow("sceneCleanupWin")

# Show it
show_cleanup_window()
