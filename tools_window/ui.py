import maya.cmds as cmds
from . import logic


def show_window():
    win_id = "sceneCleanupWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id,
                title="Scene Tools",
                widthHeight=(320, 500),
                sizeable=True)

    cmds.scrollLayout(
        "sceneCleanupScroll",
        verticalScrollBarThickness=12,
        childResizable=True
    )

    cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=10,
        columnAlign="center"
    )

    cmds.button(label="Clean Scene", height=40, command=logic.run_cleanup)

    cmds.separator(height=10)
    cmds.text(label="Rename Selected Nodes")
    cmds.textField("renameBaseField", placeholderText="Base name here...")
    cmds.button(label="Rename with _##", command=logic.rename_selected)

    cmds.separator(height=10)
    cmds.text(label="UV Edits", align="center", height=20)
    cmds.button(label="Delete Extra UV Sets", command=logic.delete_extra_uv_sets)
    cmds.button(label="Delete Third UVset", command=logic.delete_third_uv_set)
    cmds.button(label="Create 'layout' UVset (copy from map1)", command=logic.ensure_layout_uvset_from_map1)
    cmds.button(label="Set UV0 to LeZooColorGradient", command=logic.set_uv0_to_lezoo_color_gradient)
    cmds.button(label="Normalize + Pack UV1 'layout' (0..1)", command=logic.normalize_layout_uvs_non_overlapping)
    cmds.button(label="Rename UVsets", command=logic.rename_uv_sets)
    cmds.button(label="Set UVs to 00", command=logic.set_uv_set_0)
    cmds.button(label="Set UVs to 01", command=logic.set_uv_set_1)
    cmds.button(label="Log UV sets", command=logic.log_uv_sets)

    cmds.separator(height=10)
    cmds.text(label="Fit To Bounding Box", align="center", height=20)

    cmds.floatFieldGrp(
        "fitBoxField",
        label="Target Box (X,Y,Z)",
        numberOfFields=3,
        value1=1.0, value2=1.0, value3=1.0
    )

    cmds.optionMenu("fitScaleModeMenu", label="Scale Mode")
    cmds.menuItem(label="Uniform")
    cmds.menuItem(label="Non-uniform")

    cmds.checkBox("centerGroundPivotCB", label="centerGroundPivot", value=False)

    cmds.button(label="Fit Selected + Freeze", height=30, command=logic.scale_selected_to_bounding_box)

    cmds.separator(height=10)
    cmds.text(label="Layout Tools", align="center", height=20)
    cmds.floatField("gridSpacingField", value=5.0)
    cmds.button(label="Grid Place Selected", command=logic.grid_place_selected)

    cmds.separator(height=10)
    cmds.button(label="Create Spiral Curve", command=logic.open_spiral_window)

    cmds.separator(height=10)
    cmds.text(label="Circular Instancing", align="center", height=20)
    cmds.intField("instanceCountField", value=8)
    cmds.floatField("instanceRadiusField", value=0.0)
    cmds.button(label="Create Instances", command=logic.on_create_instances)
    cmds.button(label="Delete Instances", command=logic.delete_instances)
    cmds.button(label="Create Copies", command=logic.on_create_copies)
    cmds.separator(height=10)
    cmds.text(label="Remove String From Name", align="center")
    cmds.textField("removeStringField", placeholderText="String to remove...")
    cmds.button(label="Remove From Selected Names", command=logic.remove_string_from_names)

    cmds.showWindow(win_id)
