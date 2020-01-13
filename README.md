# maya-python-scripts

**renderLayerSetter:** <br>
(uses the legacy render layers)<br> <br>

creates:<br>
one render layer for each light in the scene <br>
one ambient render layer<br>
one occlusion render layer (def CreateOcclShaderNetwork)<br>
one Depth of Fiel render layer (def CreateDOFShaderNetwork)<br>
one mask render layer per group in group renderset (def CreateMaskShaderNetworks)<br>
<br>

prerequisites:<br>
all your geometry to render in one Group called 'renderset'. Each group will get its own mask<br>
a camera called 'rendercam' (will be used for rendering)<br>
DO NOT USE shader assignment per face: only per object!<br>


