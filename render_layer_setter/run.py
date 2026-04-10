import struct
import binascii
import maya.cmds as cmds
from . import logic


def run():
    # Reset shared globals so re-runs start clean
    logic.reset_globals()

    renderCam = 'rendercam'

    mainObjectList = []
    shapeList = []
    shaderList = []
    materialClassList = []

    cmds.select(cmds.ls('renderset'))

    # Build list of objects and unique shaders from selection
    for selectedGroup in cmds.ls(sl=True):
        mainObjectList.append(selectedGroup)

    if not mainObjectList:
        cmds.warning("No 'renderset' found in scene. Please create a set named 'renderset' with your render objects.")
        return

    shapeList = cmds.listRelatives(mainObjectList, allDescendents=True, type='mesh') or []

    for shape in shapeList:
        selectedShadingGroup = cmds.listConnections(shape, type='shadingEngine')
        print('current ShadingGroup' + str(selectedShadingGroup))
        print('current Shape' + str(shape))
        if selectedShadingGroup:
            shader = cmds.ls(cmds.listConnections(selectedShadingGroup), materials=True)
            if shader:
                shaderList.append(shader[0])

    reducedShaderList = list(set(shaderList))

    # Create material class instances
    for material in reducedShaderList:
        mC = logic.materialClass(material)
        materialClassList.append(mC)

    # Create render layers per light
    lightsList = cmds.ls(type='light') or []
    renderCamObject = cmds.ls('rendercam')
    if not renderCamObject:
        cmds.warning("No 'rendercam' found in scene. Please create/rename a camera to 'rendercam'.")
        return
    renderCamShape = cmds.listRelatives(renderCamObject[0], shapes=True)[0]
    backgroundLightColorTuple = cmds.getAttr(renderCamShape + '.backgroundColor')[0]
    backgroundLightColorList = list(backgroundLightColorTuple)
    i = 0
    for t in backgroundLightColorList:
        backgroundLightColorList[i] = t * 255
        backgroundLightColorList[i] = int(round(backgroundLightColorList[i]))
        i = i + 1
    backgroundLightString = binascii.hexlify(struct.pack('BBB', *backgroundLightColorList)).decode('utf-8')

    amb_shape = cmds.ambientLight(ambientShade=0, n='AmbientLight', useRayTraceShadows=False)
    amb_transform = cmds.listRelatives(amb_shape, parent=True)[0]
    ambRenderLayer = cmds.createRenderLayer(amb_transform, makeCurrent=True, name='AmbientRenderLayer_hex_' + backgroundLightString)
    cmds.editRenderLayerMembers(ambRenderLayer, mainObjectList)
    cmds.editRenderLayerMembers(ambRenderLayer, renderCam)

    for light in lightsList:
        lightColorTuple = cmds.getAttr(light + '.color')[0]
        lightColorList = list(lightColorTuple)
        i = 0
        for t in lightColorList:
            lightColorList[i] = t * 255
            lightColorList[i] = int(round(lightColorList[i]))
            i = i + 1
        lightString = binascii.hexlify(struct.pack('BBB', *lightColorList)).decode('utf-8')

        fullLightName = light
        lightName = fullLightName.replace('Shape1', '')
        light_transform = cmds.listRelatives(light, parent=True)[0]
        currentRenderLayer = cmds.createRenderLayer(light_transform, makeCurrent=True, name='rl_' + lightName + '_hex_' + lightString)
        cmds.editRenderLayerMembers(currentRenderLayer, mainObjectList)
        cmds.editRenderLayerMembers(currentRenderLayer, renderCam)
        for mc in materialClassList:
            cmds.sets(mc.meshList, e=True, forceElement=mc.bS)

    # Occlusion render layer
    occlRenderLayer = cmds.createRenderLayer(makeCurrent=True, name='OcclusionRenderLayer')
    cmds.editRenderLayerMembers(occlRenderLayer, mainObjectList)
    cmds.editRenderLayerMembers(occlRenderLayer, renderCam)
    for mc in materialClassList:
        cmds.sets(mc.meshList, e=True, forceElement=mc.oS)

    # Depth render layer
    depthRenderLayer = cmds.createRenderLayer(makeCurrent=True, name='DepthRenderLayer')
    cmds.editRenderLayerMembers(depthRenderLayer, mainObjectList)
    cmds.editRenderLayerMembers(depthRenderLayer, renderCam)
    for mc in materialClassList:
        cmds.sets(mc.meshList, e=True, forceElement=mc.dofSG)

    cmds.select(renderCam)
    depthDistanceLoc = cmds.spaceLocator(n='DepthofField_Back')[0]
    nearDistanceLoc = cmds.spaceLocator(n='DepthofField_Front')[0]
    disLocGroup = cmds.group(empty=True, n='disLocGroup')
    cmds.parent(depthDistanceLoc, disLocGroup, relative=True)
    cmds.parent(nearDistanceLoc, disLocGroup, relative=True)
    cmds.parent(disLocGroup, renderCam, relative=True)
    cmds.setAttr(disLocGroup + '.rotateY', 180)
    cmds.connectAttr(depthDistanceLoc + '.translateZ', logic.mDF + '.input1X')
    cmds.connectAttr(nearDistanceLoc + '.translateZ', logic.mDN + '.input1X')
    cmds.setAttr(depthDistanceLoc + '.translateZ', 2000)
    cmds.setAttr(nearDistanceLoc + '.translateZ', 500)

    # Create masks
    for item in mainObjectList:
        name = item
        currentRenderLayer = cmds.createRenderLayer(makeCurrent=True, name='mask_' + name)
        cmds.editRenderLayerMembers(currentRenderLayer, mainObjectList)
        cmds.editRenderLayerMembers(currentRenderLayer, renderCam)
        for mc in materialClassList:
            cmds.sets(mc.meshList, e=True, forceElement=mc.msGBlack)
        shapeElements = cmds.listRelatives(item, allDescendents=True, type='mesh') or []
        for itemS in shapeElements:
            selectedShadingGroup = cmds.listConnections(itemS, type='shadingEngine')
            if not selectedShadingGroup:
                continue
            shadingGroupName = selectedShadingGroup[0]
            newShadingGroupName = shadingGroupName.replace('Black', 'White')
            cmds.sets(itemS, e=True, forceElement=newShadingGroupName)

    print("Render layer setup complete.")
