# maya-python-scripts

renderLayerSetter: 
uses the legacy render layers.

creates:
one render layer for each light in the scene
one ambient render layer
one occlusion render layer (def CreateOcclShaderNetwork)
one Depth of Fiel render layer (def CreateDOFShaderNetwork)
one mask render layer per group in group renderset (def CreateMaskShaderNetworks)


prerequisites:
all your geometry to render in one Group called 'renderset'. Each group will get its own mask
a camera called 'rendercam' (will be used for rendering)
DO NOT USE shader assignment per face: only per object!


