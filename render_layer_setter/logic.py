import maya.cmds as cmds


# Module-level globals shared across shader creation functions (node name strings)
mA = None
sR = None
mDN = None
mDF = None


def reset_globals():
    global mA, sR, mDN, mDF
    mA = None
    sR = None
    mDN = None
    mDF = None


def CreateOcclShaderNetwork(sourceMaterialClass):
    global mA
    mat = sourceMaterialClass.baseMaterial
    oS = sourceMaterialClass.oS = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, n='occlShSG_' + mat)
    if not mA:
        mA = cmds.shadingNode('mib_amb_occlusion', asUtility=True, n='occlusionShader')
        cmds.setAttr(mA + '.max_distance', 32)
    if sourceMaterialClass.hasTransparency:
        lS = sourceMaterialClass.occlusionShader = cmds.shadingNode('layeredShader', asShader=True, n='OcclSh_' + mat)
        cmds.setAttr(lS + '.compositingFlag', 1)
        cmds.connectAttr(mA + '.outValue', lS + '.inputs[0].color')
        cmds.connectAttr(mat + '.outTransparency', lS + '.inputs[0].transparency')
    else:
        lS = sourceMaterialClass.occlusionShader = cmds.shadingNode('surfaceShader', asShader=True, n='OcclSh_' + mat)
        cmds.connectAttr(mA + '.outValue', lS + '.outColor')
    cmds.connectAttr(lS + '.outColor', oS + '.surfaceShader')


def CreateBaseRenderShaderNetwork(sourceMaterialClass):
    mat = sourceMaterialClass.baseMaterial
    bS = sourceMaterialClass.bS = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, n='baseShSg_' + mat)
    b = sourceMaterialClass.baseRenderShader = cmds.shadingNode('lambert', asShader=True, n='BaseRenderSh_' + mat)
    cmds.connectAttr(b + '.outColor', bS + '.surfaceShader')
    if sourceMaterialClass.hasTransparency:
        cmds.connectAttr(mat + '.outTransparency', b + '.transparency')
    if sourceMaterialClass.hasBump:
        cmds.connectAttr(sourceMaterialClass.bumpNode + '.outNormal', b + '.normalCamera')


def CreateDOFShaderNetwork(sourceMaterialClass):
    global sR, mDN, mDF
    mat = sourceMaterialClass.baseMaterial
    sSS = sourceMaterialClass.dofSG = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, n='depthShaderSG' + mat)
    if not sR:
        sI = cmds.shadingNode('samplerInfo', asUtility=True, n='sampI')
        mD = cmds.shadingNode('multiplyDivide', asUtility=True, n='multD')
        sR = cmds.shadingNode('setRange', asUtility=True, n='setR')
        mDN = cmds.shadingNode('multiplyDivide', asUtility=True, n='mD_Near')
        mDF = cmds.shadingNode('multiplyDivide', asUtility=True, n='mD_Far')
        cmds.connectAttr(mDF + '.outputX', sR + '.oldMaxX')
        cmds.connectAttr(mDN + '.outputX', sR + '.oldMinX')
        cmds.setAttr(sR + '.minX', 1)
        cmds.setAttr(mD + '.input2X', -1)
        cmds.connectAttr(sI + '.pointCameraZ', mD + '.input1X')
        cmds.connectAttr(mD + '.outputX', sR + '.valueX')
        cmds.setAttr(mDN + '.input2X', 1)
        cmds.setAttr(mDF + '.input2X', 1)

    if sourceMaterialClass.hasTransparency:
        sS = sourceMaterialClass.depthShader = cmds.shadingNode('layeredShader', asShader=True, n='DepthShader_' + mat)
        cmds.setAttr(sS + '.compositingFlag', 1)
        cmds.connectAttr(sR + '.outValueX', sS + '.inputs[0].colorR')
        cmds.connectAttr(sR + '.outValueX', sS + '.inputs[0].colorG')
        cmds.connectAttr(sR + '.outValueX', sS + '.inputs[0].colorB')
        cmds.connectAttr(mat + '.outTransparency', sS + '.inputs[0].transparency')
    else:
        sS = sourceMaterialClass.depthShader = cmds.shadingNode('surfaceShader', asShader=True, n='DepthShader_' + mat)
        cmds.connectAttr(sR + '.outValueX', sS + '.outColorR')
        cmds.connectAttr(sR + '.outValueX', sS + '.outColorG')
        cmds.connectAttr(sR + '.outValueX', sS + '.outColorB')
    cmds.connectAttr(sS + '.outColor', sSS + '.surfaceShader')


def CreateMaskShaderNetworks(sourceMaterialClass):
    mat = sourceMaterialClass.baseMaterial
    msGWhite = sourceMaterialClass.msGWhite = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, n='maskWhite_' + mat)
    msGBlack = sourceMaterialClass.msGBlack = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, n='maskBlack_' + mat)
    if sourceMaterialClass.hasTransparency:
        mSW = sourceMaterialClass.maskMaterialWhite = cmds.shadingNode('layeredShader', asShader=True, n='MaskWhiteShader_' + mat)
        mSB = sourceMaterialClass.maskMaterialBlack = cmds.shadingNode('layeredShader', asShader=True, n='MaskBlackShader_' + mat)
        cmds.setAttr(mSW + '.compositingFlag', 1)
        cmds.setAttr(mSB + '.compositingFlag', 1)
        cmds.connectAttr(mat + '.outTransparency', mSW + '.inputs[0].transparency')
        cmds.connectAttr(mat + '.outTransparency', mSB + '.inputs[0].transparency')
        cmds.setAttr(mSW + '.inputs[0].color', 1, 1, 1, type='double3')
        cmds.setAttr(mSB + '.inputs[0].color', 0, 0, 0, type='double3')
    else:
        mSW = sourceMaterialClass.maskMaterialWhite = cmds.shadingNode('surfaceShader', asShader=True, n='MaskWhiteShader_' + mat)
        mSB = sourceMaterialClass.maskMaterialBlack = cmds.shadingNode('surfaceShader', asShader=True, n='MaskBlackShader_' + mat)
        cmds.setAttr(mSW + '.outColor', 1, 1, 1, type='double3')
        cmds.setAttr(mSB + '.outColor', 0, 0, 0, type='double3')

    cmds.connectAttr(mSW + '.outColor', msGWhite + '.surfaceShader')
    cmds.connectAttr(mSB + '.outColor', msGBlack + '.surfaceShader')


class materialClass(object):
    def __init__(self, sourceMaterial):
        self.name = 'mC_' + sourceMaterial
        self.baseMaterial = sourceMaterial
        self.hasTransparency = True
        self.hasBump = False
        sgs = cmds.listConnections(sourceMaterial, type='shadingEngine')
        self.baseShadingGroup = sgs[0]
        self.meshList = cmds.sets(self.baseShadingGroup, q=True) or []
        if not cmds.listConnections(sourceMaterial + '.transparency'):
            self.hasTransparency = False
        if cmds.listConnections(sourceMaterial + '.normalCamera'):
            self.hasBump = True
            self.bumpNode = cmds.listConnections(sourceMaterial + '.normalCamera')[0]
        CreateOcclShaderNetwork(self)
        CreateBaseRenderShaderNetwork(self)
        CreateDOFShaderNetwork(self)
        CreateMaskShaderNetworks(self)
