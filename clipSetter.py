
import maya.cmds as cmds
import json

class GameExporterGenerator:
    def __init__(self):
        self.window_name = "GameExporterGenerator"
        self.entries = []
        self.base_frame = 100
        self.frame_spacing = 10
        self.color_tags = ["RED", "YELLOW", "BLUE", "GREEN", "WHITE", "BLACK"]

        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        self.window = cmds.window(self.window_name, title="Game Exporter Preset Generator", widthHeight=(460, 350))
        self.layout = cmds.columnLayout(adjustableColumn=True)

        cmds.text(label="Animation Blocks (name, count, length)")
        self.scroll = cmds.scrollLayout(height=200)
        self.entry_col = cmds.columnLayout(adjustableColumn=True)
        self.add_entry()

        cmds.setParent(self.layout)
        cmds.button(label="Add Entry", command=lambda *_: self.add_entry())
        self.use_houses = cmds.checkBox(label="Use Houses (color variants)", value=False)
        cmds.button(label="Save Preset", command=lambda *_: self.save_preset())
        cmds.button(label="Load Preset", command=lambda *_: self.load_preset())
        cmds.button(label="Generate MEL File", command=lambda *_: self.generate_file())
        cmds.showWindow(self.window)

    def add_entry(self):
        cmds.setParent(self.entry_col)
        cmds.rowLayout(nc=4, adjustableColumn=2)
        name = cmds.textField(placeholderText="base_name (e.g. walk)")
        amount = cmds.intField(value=1, min=1)
        length = cmds.intField(value=30, min=1)
        cmds.setParent("..")
        self.entries.append((name, amount, length))

    def save_preset(self):
        data = []
        for nameField, amountField, lengthField in self.entries:
            data.append({
                "name": cmds.textField(nameField, q=True, text=True),
                "amount": cmds.intField(amountField, q=True, value=True),
                "length": cmds.intField(lengthField, q=True, value=True)
            })
        state = {
            "entries": data,
            "use_houses": cmds.checkBox(self.use_houses, q=True, value=True)
        }
        preset_string = json.dumps(state)
        cmds.promptDialog(title="Save Preset", message="Copy this string:", text=preset_string, button=["OK"])

    def load_preset(self):
        if cmds.promptDialog(title="Load Preset", message="Paste preset string:", button=["OK", "Cancel"], cancelButton="Cancel", dismissString="Cancel") == "OK":
            preset_string = cmds.promptDialog(q=True, text=True)
            try:
                state = json.loads(preset_string)
                self.clear_entries()
                for entry in state.get("entries", []):
                    self.add_entry()
                    nameField, amountField, lengthField = self.entries[-1]
                    cmds.textField(nameField, e=True, text=entry["name"])
                    cmds.intField(amountField, e=True, value=entry["amount"])
                    cmds.intField(lengthField, e=True, value=entry["length"])
                cmds.checkBox(self.use_houses, e=True, value=state.get("use_houses", False))
            except Exception as e:
                cmds.confirmDialog(title="Error", message=f"Failed to load preset: {str(e)}", button=["OK"])

    def clear_entries(self):
        for child in cmds.columnLayout(self.entry_col, q=True, ca=True) or []:
            cmds.deleteUI(child)
        self.entries = []

    def generate_file(self):
        filepath = cmds.fileDialog2(fileMode=0, caption="Save MEL File", fileFilter="MEL Files (*.mel)")
        if not filepath:
            return
        filepath = filepath[0]

        index = 0
        frame = self.base_frame
        lines = []
        use_houses = cmds.checkBox(self.use_houses, q=True, value=True)

        lines.append('// requires maya "2026";')
        lines.append('startAttrPreset( "gameFbxExporter" );')
        lines.append('blendAttrStr "presetName" "Anim Default";')

        for nameField, amountField, lengthField in self.entries:
            base_name = cmds.textField(nameField, q=True, text=True).strip()
            amount = cmds.intField(amountField, q=True, value=True)
            length = cmds.intField(lengthField, q=True, value=True)

            tag_list = self.color_tags if use_houses else [""]
            for tag in tag_list:
                for i in range(amount):
                    suffix = f"_{tag}_{i+1:02}" if tag else f"_{i+1:02}"
                    clip_name = f"{base_name}{suffix}"
                    lines.append(f'blendAttrStr "animClips[{index}].animClipName" "{clip_name}";')
                    lines.append(f'blendAttr "animClips[{index}].animClipStart" {frame};')
                    lines.append(f'blendAttr "animClips[{index}].animClipEnd" {frame + length};')
                    lines.append(f'blendAttr "animClips[{index}].exportAnimClip" 1;')
                    lines.append(f'blendAttr "animClips[{index}].animClipId" 0;')
                    index += 1
                    frame = ((frame + length + self.frame_spacing + 9) // 10) * 10

        lines.append('blendAttrStr "fileVersion" "FBX201800";')
        lines += [
            'blendAttr "frozen" 0;', 'blendAttr "overridePresetValue" 0;',
            'blendAttr "isTheLastOneSelected" 1;', 'blendAttr "isTheLastOneUsed" 1;',
            'blendAttr "useFilenameAsPrefix" 1;', 'blendAttr "viewInFBXReview" 0;',
            'blendAttr "exportTypeIndex" 2;', 'blendAttr "exportSetIndex" 1;',
            'blendAttr "modelFileMode" 1;', 'blendAttr "moveToOrigin" 0;',
            'blendAttr "smoothingGroups" 1;', 'blendAttr "splitVertexNormals" 0;',
            'blendAttr "tangentsBinormals" 1;', 'blendAttr "smoothMesh" 0;',
            'blendAttr "selectionSets" 0;', 'blendAttr "convertToNullObj" 0;',
            'blendAttr "preserveInstances" 0;', 'blendAttr "referencedAssetsContent" 0;',
            'blendAttr "triangulate" 0;', 'blendAttr "exportAnimation" 0;',
            'blendAttr "useSceneName" 0;', 'blendAttr "removeSingleKey" 0;',
            'blendAttr "fileSplitType" 2;', 'blendAttr "includeCombinedClips" 0;',
            'blendAttr "bakeAnimation" 1;', 'blendAttr "bakeAnimStart" 0;',
            'blendAttr "bakeAnimEnd" 0;', 'blendAttr "bakeAnimStep" 0;',
            'blendAttr "resampleAll" 0;', 'blendAttr "deformedModels" 0;',
            'blendAttr "skinning" 1;', 'blendAttr "blendshapes" 1;',
            'blendAttr "curveFilters" 0;', 'blendAttr "constantKeyReducer" 0;',
            'blendAttr "ckrTranslationPrecision" 0;', 'blendAttr "ckrRotationPrecision" 0;',
            'blendAttr "ckrScalingPrecision" 0;', 'blendAttr "ckrOtherPrecision" 0;',
            'blendAttr "ckrAutoTangentOnly" 0;', 'blendAttr "constraints" 0;',
            'blendAttr "skeletonDefinitions" 0;', 'blendAttr "includeCameras" 0;',
            'blendAttr "includeLights" 1;', 'blendAttr "upAxis" 1;',
            'blendAttr "embedMedia" 1;', 'blendAttr "includeChildren" 0;',
            'blendAttr "inputConnections" 0;', 'blendAttr "autoScaleFactor" 0;',
            'blendAttr "showWarningManager" 0;', 'blendAttr "generateLogData" 0;',
            'blendAttr "fileType" 0;', 'endAttrPreset();'
        ]

        with open(filepath, "w") as f:
            f.write("\n".join(lines))

        cmds.confirmDialog(title="Success", message="MEL file generated successfully!", button=["OK"])

GameExporterGenerator()
