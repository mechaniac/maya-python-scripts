from pymel.core import *
import struct
import binascii

mainObjectList = []
objectList = []
shapeList=[]
shaderList = []
reducedShaderList=[]
materialClassList = []
renderLayerList = []

renderCam = 'rendercam'

mA = None
sR = None
mDN = None
mDF = None


select(ls('renderset'))



#create List of objects and List of all unique shaders from selection

for selectedGroup in ls(sl=True):
	mainObjectList.append(selectedGroup)

shapeList = listRelatives(mainObjectList, allDescendents = True, type = 'mesh')


for shape in shapeList:
    selectedShadingGroup = listConnections(shape, type = 'shadingEngine')
    print('current ShadingGroup'+str(selectedShadingGroup))
    print('current Shape' + str(shape))
    if selectedShadingGroup != []:
        shader = ls(listConnections(selectedShadingGroup), materials =1)[0]
        shaderList.append(shader)

reducedShaderList = list(set(shaderList))

#--------------------------------------------------


def CreateOcclShaderNetwork(sourceMaterialClass):
    oS = sourceMaterialClass.oS = sets(renderable = True, nss = True, em = True, n = 'occlShSG_'+sourceMaterialClass.baseMaterial.name())
    global mA
    if not mA:
        mA = shadingNode('mib_amb_occlusion', asUtility = True, n = 'occlusionShader')
        mA.max_distance.set(32)
    if sourceMaterialClass.hasTransparency:
         lS=sourceMaterialClass.occlusionShader = shadingNode('layeredShader', asShader = True, n = 'OcclSh_'+sourceMaterialClass.baseMaterial.name())
         lS.setCompositingFlag(1)
         connectAttr(mA.outValue, lS+'.inputs[0].color')
         connectAttr(sourceMaterialClass.baseMaterial.outTransparency,lS+'.inputs[0].transparency')
         
    else:
        lS = sourceMaterialClass.occlusionShader = shadingNode('surfaceShader', asShader=True, n= 'OcclSh_'+sourceMaterialClass.baseMaterial.name())
        connectAttr(mA.outValue,lS.outColor)
    connectAttr(lS.outColor,oS.surfaceShader)

def CreateBaseRenderShaderNetwork(sourceMaterialClass):
    bS = sourceMaterialClass.bS = sets(renderable = True, nss = True, em = True, n = 'baseShSg_'+sourceMaterialClass.baseMaterial.name())
    b = sourceMaterialClass.baseRenderShader = shadingNode('lambert', asShader = True, n = 'BaseRenderSh_'+sourceMaterialClass.baseMaterial.name())
    connectAttr(b.outColor,bS.surfaceShader)
    if sourceMaterialClass.hasTransparency:
        connectAttr(sourceMaterialClass.baseMaterial.outTransparency,b.transparency)
    if sourceMaterialClass.hasBump:
        connectAttr(sourceMaterialClass.bumpNode.outNormal,b.normalCamera)
    
def CreateDOFShaderNetwork(sourceMaterialClass):
    sSS = sourceMaterialClass.dofSG = sets(renderable= True, nss = True, em = True, n = 'depthShaderSG'+sourceMaterialClass.baseMaterial.name())
    global sR
    global mDN
    global mDF
    if not sR:    
        sI = shadingNode('samplerInfo', asUtility = True, n= 'sampI')
        mD =  shadingNode('multiplyDivide', asUtility = True, n= 'multD')
        sR = shadingNode('setRange', asUtility = True, n = 'setR')
        mDN = shadingNode('multiplyDivide', asUtility=True,n='mD_Near')
        mDF = shadingNode('multiplyDivide', asUtility=True,n='mD_Far')
        connectAttr(mDF.outputX,sR.oldMaxX)
        connectAttr(mDN.outputX,sR.oldMinX)
        sR.minX.set(1)
        mD.input2X.set(-1)
        connectAttr(sI.pointCameraZ, mD.input1X)
        connectAttr(mD.outputX,sR.valueX)
        mDN.input2X.set(1) #set to 1 if scene unit size is centimeters, set to 100 if scene unit size is meter
        mDF.input2X.set(1) #same as above

    if sourceMaterialClass.hasTransparency:
        sS = sourceMaterialClass.depthShader = shadingNode('layeredShader', asShader=True,n='DepthShader_'+sourceMaterialClass.baseMaterial.name())
        sS.setCompositingFlag(1)
        connectAttr(sR.outValueX,sS+'.inputs[0].colorR')
        connectAttr(sR.outValueX,sS+'.inputs[0].colorG')
        connectAttr(sR.outValueX,sS+'.inputs[0].colorB')
        connectAttr(sourceMaterialClass.baseMaterial.outTransparency,sS+'.inputs[0].transparency')
    else:
        sS = sourceMaterialClass.depthShader = shadingNode('surfaceShader', asShader=True, n= 'DepthShader_'+sourceMaterialClass.baseMaterial.name())
        connectAttr(sR.outValueX,sS.outColorR)
        connectAttr(sR.outValueX,sS.outColorG)
        connectAttr(sR.outValueX,sS.outColorB)
    connectAttr(sS.outColor,sSS.surfaceShader)

def CreateMaskShaderNetworks(sourceMaterialClass):
    msGWhite = sourceMaterialClass.msGWhite = sets(renderable = True, nss = True, em = True, n = 'maskWhite_'+sourceMaterialClass.baseMaterial.name())
    msGBlack = sourceMaterialClass.msGBlack = sets(renderable=True,nss= True, em = True, n = 'maskBlack_'+sourceMaterialClass.baseMaterial.name())
    if sourceMaterialClass.hasTransparency:
        mSW = sourceMaterialClass.maskMaterialWhite = shadingNode('layeredShader', asShader=True, n='MaskWhiteShader_'+sourceMaterialClass.baseMaterial.name())
        mSB = sourceMaterialClass.maskMaterialBlack = shadingNode('layeredShader', asShader=True, n='MaskBlackShader_'+sourceMaterialClass.baseMaterial.name())
        mSW.setCompositingFlag(1)
        mSB.setCompositingFlag(1)
        connectAttr(sourceMaterialClass.baseMaterial.outTransparency,mSW+'.inputs[0].transparency')
        connectAttr(sourceMaterialClass.baseMaterial.outTransparency,mSB+'.inputs[0].transparency')
        setAttr(mSW+'.inputs[0].color',1,1,1, type = 'double3')
        setAttr(mSB+'.inputs[0].color',0,0,0, type = 'double3')
    else:
        mSW = sourceMaterialClass.maskMaterialWhite = shadingNode('surfaceShader', asShader = True, n='MaskWhiteShader_'+sourceMaterialClass.baseMaterial.name())
        mSB = sourceMaterialClass.maskMaterialBlack = shadingNode('surfaceShader', asShader = True, n='MaskBlackShader_'+sourceMaterialClass.baseMaterial.name())
        mSW.outColor.set([1,1,1])
        mSB.outColor.set([0,0,0])

    connectAttr(mSW.outColor, msGWhite.surfaceShader)
    connectAttr(mSB.outColor, msGBlack.surfaceShader)

        
class materialClass(object):
    def __init__(self,sourceMaterial):
        self.name = 'mC_' + sourceMaterial.name()
        self.baseMaterial = sourceMaterial
        self.hasTransparency = True
        self.hasBump = False
        self.baseShadingGroup = sourceMaterial.listConnections(type='shadingEngine')[0]
        self.meshList = self.baseShadingGroup.members()
        if not listConnections(sourceMaterial.transparency):
        	self.hasTransparency = False
        if listConnections(sourceMaterial.normalCamera):
            self.hasBump = True
            self.bumpNode = listConnections(sourceMaterial.normalCamera)[0]
        CreateOcclShaderNetwork(self)
        CreateBaseRenderShaderNetwork(self)
        CreateDOFShaderNetwork(self)
        CreateMaskShaderNetworks(self)

for material in reducedShaderList:
	mC = materialClass(material)
	materialClassList.append(mC)


#Create List of all lights and one RenderLayer per Light
lightsList = ls(type = 'light')
renderCamObject = ls('rendercam')
renderCamShape = renderCamObject[0].getShape()
backgroundLightColorTuple = renderCamShape.backgroundColor.get()
backgroundLightColorList = list(backgroundLightColorTuple)
i=0
for t in backgroundLightColorList:
    backgroundLightColorList[i] = t*255
    backgroundLightColorList[i] = int(round(backgroundLightColorList[i]))
    i = i+1
backgroundLightString = binascii.hexlify(struct.pack('BBB',*backgroundLightColorList)).decode('utf-8')

ambLight = ambientLight(ambientShade = 0, n = 'AmbientLight',useRayTraceShadows=False)
ambRenderLayer = createRenderLayer(ambLight, makeCurrent=True, name= 'AmbientRenderLayer_hex_'+backgroundLightString)
ambRenderLayer.addMembers(mainObjectList)
ambRenderLayer.addMembers(renderCam)

str("test")

for light in lightsList:
    lightColorTuple = light.color.get()
    lightColorList = list(lightColorTuple)
    i=0
    for t in lightColorList:
        lightColorList[i] = t*255
        lightColorList[i] = int(round(lightColorList[i]))
        i = i+1
    lightString = binascii.hexlify(struct.pack('BBB',*lightColorList)).decode('utf-8')
    #lightString =struct.pack('BBB',*lightColorList).encode('hex')              gives the same result as line above

    fullLightName = light.name()
    lightName = fullLightName.replace('Shape1','')
    currentRenderLayer = createRenderLayer(light,makeCurrent=True, name = 'rl_' + lightName + '_hex_'+lightString)
    currentRenderLayer.addMembers( mainObjectList)
    currentRenderLayer.addMembers(renderCam)
    for materialClass in materialClassList:
        sets(materialClass.bS, e = True, forceElement = materialClass.meshList)


        # select(materialClass.baseMaterial)
        # hyperShade(objects="")
        # hyperShade(a=materialClass.baseRenderShader)

occlRenderLayer = createRenderLayer(makeCurrent=True, name = 'OcclusionRenderLayer')
occlRenderLayer.addMembers(mainObjectList)
occlRenderLayer.addMembers(renderCam)
for materialClass in materialClassList:
    sets(materialClass.oS, e = True, forceElement = materialClass.meshList)
        


    #hyperShade(objects="")
    #hyperShade(a=materialClass.occlusionShader)

depthRenderLayer = createRenderLayer(makeCurrent=True, name = 'DepthRenderLayer')
depthRenderLayer.addMembers(mainObjectList)
depthRenderLayer.addMembers(renderCam)
for materialClass in materialClassList:
    sets(materialClass.dofSG, e = True, forceElement = materialClass.meshList)
    #select(materialClass.baseMaterial)             old version. doesnt work in batch mode
    #hyperShade(objects="")
    #hyperShade(a=materialClass.depthShader)



select(renderCam)
depthDistanceLoc = spaceLocator(n='DepthofField_Back')
nearDistanceLoc = spaceLocator(n='DepthofField_Front')
disLocGroup = group(n='disLocGroup')
parent(depthDistanceLoc,disLocGroup, relative = True)
parent(nearDistanceLoc,disLocGroup, relative = True)
parent(disLocGroup, renderCam, relative = True)
disLocGroup.rotateY.set(180)
connectAttr(depthDistanceLoc.translateZ,mDF.input1X)
connectAttr(nearDistanceLoc.translateZ,mDN.input1X)
depthDistanceLoc.translateZ.set(2000) #dependent on scene unit size (either cm or m)
nearDistanceLoc.translateZ.set(500) #dependent on scene unit size (either cm or m)


#Create Masks
for item in mainObjectList:
    name = item.name()
    currentRenderLayer = createRenderLayer(makeCurrent=True, name = 'mask_'+name)
    currentRenderLayer.addMembers(mainObjectList)
    currentRenderLayer.addMembers(renderCam)
    for materialClass in materialClassList: #set all elements to black
        sets(materialClass.msGBlack, e = True, forceElement = materialClass.meshList)
        # select(materialClas.baseMaterial)
        # hyperShade(objects="")
        # hyperShade(a=materialClas.maskMaterialBlack)
    shapeElements = listRelatives(item, allDescendents = True, type = 'mesh')
    #swap active element to white
    for itemS in shapeElements:
        selectedShadingGroup = listConnections(itemS, type = 'shadingEngine')
        if selectedShadingGroup == []:
            continue
        shadingGroupName = selectedShadingGroup[0].name()
        newShadingGroupName = shadingGroupName.replace('Black', 'White')
        sets(newShadingGroupName, e = True, forceElement = itemS)


        # shader = ls(listConnections(selectedShadingGroup), materials =1)
        # shaderName = shader[0].name()
        # newShaderName = shaderName.replace('Black', 'White')
        # select(itemS)
        # hyperShade(a=newShaderName)

