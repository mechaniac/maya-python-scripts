import maya.cmds as m
import maya.cmds as cmds
import maya.mel as mm

def parent_objects(child_name, parent_name):
    # Check if the child and parent objects exist
    if not m.objExists(child_name):
        m.warning("Child object '{}' does not exist.".format(child_name))
        return
    
    if not m.objExists(parent_name):
        m.warning("Parent object '{}' does not exist.".format(parent_name))
        return
    
    # Parent the child to the parent
    cmds.parent(child_name, parent_name)
    print("Parented '{}' to '{}'.".format(child_name, parent_name))

def safeDelete(o):
	if m.objExists(o):
		m.delete(o)           
		

def MirrorMeshes(path):
    """
    Mirrors and processes meshes within the specified group or directly from a single mesh.

    Args:
        path (str): The path to the group containing meshes or the path to a single mesh.
    """
    # Check if the path is a group or a single mesh
    if cmds.objectType(path, isType="transform") and cmds.listRelatives(path, shapes=True, type='mesh'):
        # Path is directly a mesh
        meshes = [path]
    else:
        # Path is a group; find all child meshes
        children = cmds.listRelatives(path, allDescendents=True, fullPath=True, type='transform') or []
        meshes = [child for child in children if cmds.listRelatives(child, shapes=True, type='mesh')]

    if not meshes:
        cmds.warning("No meshes found at path: {}".format(path))
        return

    # Combine meshes if there's more than one, or use the single mesh directly
    if len(meshes) > 1:
        combined_mesh = cmds.polyUnite(meshes, name="{}_combined".format(path.split("|")[-1]))[0]
        cmds.delete(combined_mesh, constructionHistory=True)
    else:
        combined_mesh = meshes[0]

    # Duplicate and mirror the combined mesh
    mirrored_mesh = cmds.duplicate(combined_mesh, name=combined_mesh.replace("_combined", "_mirrored"))[0]
    cmds.setAttr("{}.scaleX".format(mirrored_mesh), -1)
    cmds.makeIdentity(mirrored_mesh, apply=True, translate=True, rotate=True, scale=True, normal=False)

    # Adjust UVs for the mirrored mesh
    try:
        cmds.select(mirrored_mesh)
        mm.eval("ConvertSelectionToUVs")
        cmds.polyFlipUV(local=False)
        mm.eval("ConvertSelectionToUVs")
        cmds.polyEditUV(uValue=1, vValue=0)
        cmds.select(mirrored_mesh)
        mm.eval("polyNormal -normalMode 0 -userNormalMode 0 -ch 1;")
    except RuntimeError as e:
        print("Error processing UVs or normals for {}: {}".format(mirrored_mesh, e))

    # Combine the original and mirrored meshes
    final_mesh = cmds.polyUnite(combined_mesh, mirrored_mesh, name="{}_final".format(path.split("|")[-1]))[0]
    cmds.delete(final_mesh, constructionHistory=True)

    # Merge vertices
    cmds.polyMergeVertex(final_mesh, distance=0.15)

    print("Processed and mirrored path: {}".format(path))
    print("Final mesh: {}".format(final_mesh))

    	
def preRig(*args):
    m.delete(m.ls(type='constraint'))
    m.delete(m.ls(type='character'))
    mm.eval('DeleteAllChannels')

    safeDelete('G_scaleGroup|G_meshes_toMirror1')
    safeDelete('G_arm_leg_rght1')
    safeDelete('G_scaleGroup|p_cc_hand')
    safeDelete('G_scaleGroup|G_ccs')
    safeDelete('G_scaleGroup|p_mesh_head_01|G_meshes_head_scale|G_eye_mirror1')
    safeDelete('G_scaleGroup|p_mesh_head_01|G_meshes_head_scale|G_meshes_toMirror_Face1')
    
    cmds.makeIdentity("G_scaleGroup", apply=True, translate=True, rotate=True, scale=True, normal=False)    

    MirrorMeshes("G_scaleGroup|p_mesh_head_01|G_meshes_head_scale|G_eye_mirror")
    MirrorMeshes("G_scaleGroup|p_mesh_head_01|G_meshes_head_scale|G_meshes_toMirror_Face")
    MirrorMeshes("G_meshes_toMirror")
    MirrorMeshes("G_arm_leg_rght")
#    MirrorMeshes("G_eye_mirror_final")
  
    # torso
    m.polyUnite("G_meshes_center", name="torso_and_neck")
    cmds.delete("torso_and_neck", constructionHistory=True)		
    cmds.polyMergeVertex( d=0.15 )    
                
    #COMBINE ALL                
    m.polyUnite("torso_and_neck", "G_meshes_toMirror_Face_final","G_arm_leg_rght_final", "G_scaleGroup","G_meshes_toMirror_final", "G_eye_mirror_final", name="body")
    cmds.delete("body", constructionHistory=True)			
    safeDelete('G_scaleGroup')
    safeDelete('G_doubleMeter')
    safeDelete('G_loc_toes')
    safeDelete('transform5')
    safeDelete('G_eye_rght_final2')
    safeDelete('G_eye_mirror_final2')

def createRig(*args):    				
    mm.eval('source "AdvancedSkeleton5Files/../AdvancedSkeleton5.mel";AdvancedSkeleton5;')
    mm.eval("asReBuildAdvancedSkeleton")
    
def bindSkinToCharacter(*args):    
    m.skinCluster('body', 'Root_M')
    m.parentConstraint("Head_M","p_mesh_head_01", mo=True)
    
    safeDelete("G_meshes_rght")
    safeDelete("G_ccs")
    
    parent_objects("body","Group|Geometry")
    parent_objects("p_mesh_head_01","Group|Geometry")

def bindSkinAndHeadToCharacter(*args): 
    cmds.polyUnite("body", "mesh_head_01", "mesh_eyes","mesh_ears", name="mesh_body")
    cmds.delete("mesh_body", constructionHistory=True)		
    m.skinCluster('mesh_body', 'Root_M')
    
    safeDelete("G_scaleGroup")
    safeDelete("G_ccs")
    
    parent_objects("mesh_body","Group|Geometry")

def select_all_curve_vertices(transform_node):
    # Check if the specified transform node exists
    if not cmds.objExists(transform_node):
        cmds.warning("The specified transform node does not exist.")
        return
    
    # Get the shape nodes of the transform node
    shape_nodes = cmds.listRelatives(transform_node, shapes=True, fullPath=True)
    
    if not shape_nodes:
        cmds.warning("The specified transform node does not have any shape nodes.")
        return
    
    # List to collect all CVs
    all_cvs = []
    
    for shape_node in shape_nodes:
        # Check if the shape node is a NURBS curve
        if cmds.nodeType(shape_node) == 'nurbsCurve':
            # Get the number of CVs
            num_cvs = cmds.getAttr(shape_node + ".spans") + cmds.getAttr(shape_node + ".degree")
            
            # Collect all CVs
            cv_list = ["{}.cv[{}]".format(shape_node, i) for i in range(num_cvs)]
            all_cvs.extend(cv_list)
    
    # Select all CVs
    if all_cvs:
        cmds.select(all_cvs, replace=True)
        print("Selected all CVs of the NURBS curves in transform node: {}".format(transform_node))
    else:
        cmds.warning("No NURBS curves found under the specified transform node.")

def select_specific_vertices(curve_name, vertices):
    # Check if the specified curve exists and is a NURBS curve
    if not cmds.objExists(curve_name) or cmds.nodeType(curve_name) != 'nurbsCurve':
        cmds.warning("The specified object does not exist or is not a NURBS curve.")
        return

    # Construct the CV selection list
    cv_list = ["{}.cv[{}]".format(curve_name, v) for v in vertices]
    
    # Select the specified CVs
    cmds.select(cv_list, replace=True)
    print("Selected CVs {} of the NURBS curve: {}".format(vertices, curve_name))


def move_selected_vertices(delta):
    # Get the currently selected vertices
    selected_vertices = cmds.ls(selection=True, flatten=True)
    
    if not selected_vertices:
        cmds.warning("No vertices selected.")
        return
    
    # Move each selected vertex by the specified delta
    for vertex in selected_vertices:
        cmds.xform(vertex, translation=delta, relative=True)
    
    print("Moved selected vertices by {}".format(delta))

def move_selected_vertices_with_soft_selection(delta, mySoftSelectDistance):
    """
    Move selected vertices with soft selection active.

    :param delta: A list or tuple with three elements representing the movement along X, Y, and Z axes.
    """
    # Ensure delta has exactly three elements
    if len(delta) != 3:
        cmds.warning("Delta must be a list or tuple with three elements representing X, Y, and Z axes.")
        return
    
    # Enable soft selection
    cmds.softSelect(sse=True)
    
    # Set soft selection options (optional, customize as needed)
    cmds.softSelect(softSelectFalloff=1, softSelectDistance=mySoftSelectDistance)  # Example values for falloff curve, falloff radius, etc.
    
    # Move the selected vertices
    cmds.move(delta[0], delta[1], delta[2], relative=True, objectSpace=True)
        
    print("Moved selected vertices by {} units along the X, Y, and Z axes with smooth select active.".format(delta))

def add_to_y_rotation(object_name, rotation_increment):
    # Check if the specified object exists
    if not cmds.objExists(object_name):
        cmds.warning("The specified object does not exist: {}".format(object_name))
        return
    
    # Get the current x rotation of the object
    current_rotation = cmds.getAttr("{}.rotateY".format(object_name))
    
    # Calculate the new rotation value
    new_rotation = current_rotation + rotation_increment
    
    # Set the new x rotation of the object
    cmds.setAttr("{}.rotateY".format(object_name), new_rotation)
    print("Added {} degrees to the y rotation of {}. New rotation is {} degrees".format(rotation_increment, object_name, new_rotation))

def add_to_rotation(object_name, rotation_increments):
    # Check if the specified object exists
    if not cmds.objExists(object_name):
        cmds.warning("The specified object does not exist: {}".format(object_name))
        return
    
    # Get the current rotation values of the object
    current_rotation_x = cmds.getAttr("{}.rotateX".format(object_name))
    current_rotation_y = cmds.getAttr("{}.rotateY".format(object_name))
    current_rotation_z = cmds.getAttr("{}.rotateZ".format(object_name))
    
    # Calculate the new rotation values
    new_rotation_x = current_rotation_x + rotation_increments[0]
    new_rotation_y = current_rotation_y + rotation_increments[1]
    new_rotation_z = current_rotation_z + rotation_increments[2]
    
    # Set the new rotation values of the object
    cmds.setAttr("{}.rotateX".format(object_name), new_rotation_x)
    cmds.setAttr("{}.rotateY".format(object_name), new_rotation_y)
    cmds.setAttr("{}.rotateZ".format(object_name), new_rotation_z)
    
def select_objects(*object_names):
    # Check if each specified object exists before selecting
    existing_objects = [obj for obj in object_names if cmds.objExists(obj)]
    
    if not existing_objects:
        cmds.warning("None of the specified objects exist.")
        return
    
    # Select the specified objects
    cmds.select(existing_objects, replace=True)
    
def adjustControllers(*args):
    select_all_curve_vertices('RootX_M')
    m.scale(2,2,2)
    cmds.select(clear=True)
    
    select_all_curve_vertices('RootX_M')
    m.scale(2,2,2)
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKNeck_M')
    m.scale(3,3,3)
    cmds.select(clear=True)
    
    select_specific_vertices('FKNeck_MShape', [1, 5])
    move_selected_vertices_with_soft_selection([0, 10, 0], 20)
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKRoot_M')
    m.scale(4,4,4)
    cmds.select(clear=True)
    
    select_specific_vertices('FKRoot_MShape', [1, 5])
    move_selected_vertices_with_soft_selection([0, -30, 0], 30)
    cmds.select(clear=True)
    
    
    select_all_curve_vertices('FKSpine1_M')
    m.scale(4,4,4)
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKChest_M')
    m.scale(2,2,2)
    cmds.select(clear=True)
    
    select_all_curve_vertices('IKLeg_R')
    m.scale(2,1,1)
    cmds.select(clear=True)
    
    select_all_curve_vertices('IKLeg_L')
    m.scale(2,1,1)
    cmds.select(clear=True)
    
    
    
    select_all_curve_vertices('FKHead_M')
    m.scale(1,2,2)
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKIKLeg_L')
    m.scale(6,6,6)
    move_selected_vertices([3,0,0])
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKIKLeg_R')
    m.scale(6,6,6)
    move_selected_vertices([-3,0,0])
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKIKArm_L')
    m.scale(6,6,6)
    move_selected_vertices([3,0,0])
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKIKArm_R')
    m.scale(6,6,6)
    move_selected_vertices([-3,0,0])
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKIKSpine_M')
    m.scale(6,6,6)
    move_selected_vertices([120,0,0])
    cmds.select(clear=True)


    select_all_curve_vertices('FKScapula_L')
    m.scale(2,2,2)
        
    select_specific_vertices('FKScapula_LShape', [3, 14])
    move_selected_vertices_with_soft_selection([-160, 20, 0], 300)
    cmds.select(clear=True)

    select_all_curve_vertices('FKScapula_R')
    m.scale(2,2,2)
        
    select_specific_vertices('FKScapula_RShape', [3, 14])
    move_selected_vertices_with_soft_selection([160, 20, 0], 300)
    cmds.select(clear=True)
    
    select_specific_vertices('FKShoulder_LShape', [4,5,6])
    move_selected_vertices_with_soft_selection([-60, 20, 0], 60)
    cmds.select(clear=True)    

    select_specific_vertices('FKShoulder_RShape', [4,5,6])
    move_selected_vertices_with_soft_selection([60, 20, 0], 60)
    cmds.select(clear=True)    
    
    
    select_all_curve_vertices('HipSwinger_M')
    m.scale(2,2,2)
    move_selected_vertices([0,0,-150])
    
#--------------QUADPED ONLY ----------------------------------------------

def adjustControllersQuadPed(*args):
    select_all_curve_vertices('FKIKLegBack_L')
    m.scale(6,6,6)
    move_selected_vertices([3,0,0])
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKIKLegBack_R')
    m.scale(6,6,6)
    move_selected_vertices([-3,0,0])
    cmds.select(clear=True)
    
    select_all_curve_vertices('IKLegBack_R')
    m.scale(3,1,1)
    cmds.select(clear=True)
    
    select_all_curve_vertices('IKLegBack_L')
    m.scale(3,1,1)
    cmds.select(clear=True)

#-------FINGERS-----------------
def adjustControllersFingers(size):
    select_all_curve_vertices('FKThumbFinger1_L')
    m.scale(size,size,size)
    cmds.select(clear=True)
    select_all_curve_vertices('FKThumbFinger2_L')
    m.scale(size,size,size)
    cmds.select(clear=True)
    select_all_curve_vertices('FKThumbFinger3_L')
    m.scale(size,size,size)
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKIndexFinger1_L')
    m.scale(size,size,size)
    cmds.select(clear=True)
    select_all_curve_vertices('FKIndexFinger2_L')
    m.scale(size,size,size)
    cmds.select(clear=True)

    select_all_curve_vertices('FKMiddleFinger1_L')
    m.scale(size,size,size)
    cmds.select(clear=True)
    select_all_curve_vertices('FKMiddleFinger2_L')
    m.scale(size,size,size)
    cmds.select(clear=True)

    select_all_curve_vertices('FKPinkyFinger1_L')
    m.scale(size,size,size)
    cmds.select(clear=True)
    select_all_curve_vertices('FKPinkyFinger2_L')
    m.scale(size,size,size)

    select_all_curve_vertices('FKThumbFinger1_R')
    m.scale(size,size,size)
    select_all_curve_vertices('FKThumbFinger2_R')
    m.scale(size,size,size)
    select_all_curve_vertices('FKThumbFinger3_R')
    m.scale(size,size,size)
    
    select_all_curve_vertices('FKIndexFinger1_R')
    m.scale(size,size,size)
    select_all_curve_vertices('FKIndexFinger2_R')
    m.scale(size,size,size)

    select_all_curve_vertices('FKMiddleFinger1_R')
    m.scale(size,size,size)
    select_all_curve_vertices('FKMiddleFinger2_R')
    m.scale(size,size,size)

    select_all_curve_vertices('FKPinkyFinger1_R')
    m.scale(size,size,size)
    select_all_curve_vertices('FKPinkyFinger2_R')
    m.scale(size,size,size)

#mouthScripts
def adjustControllersMouthUp(size):
    select_all_curve_vertices('FKUpperLip_M')
    m.scale(size,size,size)
    cmds.select(clear=True)

    select_all_curve_vertices('FKMouthCorner_R')
    m.scale(size,size,size)
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKMouthCorner_L')
    m.scale(size,size,size)
    cmds.select(clear=True)    


def adjustControllersMouthLow(size):
    select_all_curve_vertices('FKLowerLip_M')
    m.scale(size,size,size)
    cmds.select(clear=True)

    select_all_curve_vertices('FKLowerLipOuter_R')
    m.scale(size,size,size)
    cmds.select(clear=True)

    select_all_curve_vertices('FKLowerLipOuter_L')
    m.scale(size,size,size)
    cmds.select(clear=True)
    

def adjustBrowsAndCheeks(size):
    select_all_curve_vertices('FKBrow_In_L')
    m.scale(size,size,size)
    cmds.select(clear=True)

    select_all_curve_vertices('FKBrow_In_R')
    m.scale(size,size,size)
    cmds.select(clear=True)
    
    select_all_curve_vertices('FKBrow_Out_L')
    m.scale(size,size,size)
    cmds.select(clear=True)

    select_all_curve_vertices('FKBrow_Out_R')
    m.scale(size,size,size)
    cmds.select(clear=True)


    select_all_curve_vertices('FKCheek_Low_L')
    m.scale(size,size,size)
    cmds.select(clear=True)

    select_all_curve_vertices('FKCheek_Low_R')
    m.scale(size,size,size)
    cmds.select(clear=True)
    
    
def pushMouthVerticesForward():

    select_specific_vertices('FKLowerLip_MShape', [0,1, 5,6,7])
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)
    
    select_specific_vertices('FKUpperLip_MShape', [1,2, 3,4,5])
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)
    
    select_specific_vertices('FKLowerLipOuter_RShape', [0,4,5,6,7])
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)
    
    select_specific_vertices('FKLowerLipOuter_LShape', [2,3,4,5,6])
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)
    
    select_specific_vertices('FKMouthCorner_RShape', [2,3,4,5,6])
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)

    select_specific_vertices('FKMouthCorner_LShape', [0,4,5,6,7])
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)

def adjustEyeBrowCheekControllers():
    select_specific_vertices('FKEyeLid_Up_RShape', [1,2,3,4,5])
    cmds.rotate(0, 0, -60, relative=True, objectSpace=True)
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)

    select_specific_vertices('FKEyeLid_Low_RShape', [0,1,5,6,7])
    cmds.rotate(0, 0, 60, relative=True, objectSpace=True)
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)
    
    select_specific_vertices('FKEyeLid_Up_LShape', [0,1,5,6,7])
    cmds.rotate(0, 0, -60, relative=True, objectSpace=True)
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)

    select_specific_vertices('FKEyeLid_Low_LShape', [1,2,3,4,5])
    cmds.rotate(0, 0, 60, relative=True, objectSpace=True)
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)

    select_all_curve_vertices('FKEye_R')
    move_selected_vertices_with_soft_selection([20, 0, 0], 30)
    m.scale(.5,.5,.5)

    select_all_curve_vertices('FKEye_L')
    move_selected_vertices_with_soft_selection([-20, 0, 0], 30)
    m.scale(.5,.5,.5)
    
    select_all_curve_vertices('FKCheek_Low_R')
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)

    select_all_curve_vertices('FKCheek_Low_L')
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)
    
    select_specific_vertices('FKBrow_In_RShape', [2,3,4])
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)

    select_specific_vertices('FKBrow_In_LShape', [0,6,7])
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)
    
    select_specific_vertices('FKBrow_Out_RShape', [2,3,4])
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)
    
    select_specific_vertices('FKBrow_Out_LShape', [0,6,7])
    move_selected_vertices_with_soft_selection([10, 0, 0], 30)    

def makeFistRight():
    add_to_rotation("FKIndexFinger1_R", [-10,120,0])
    add_to_y_rotation("FKIndexFinger2_R", 90)
    add_to_y_rotation("FKIndexFinger3_R", 90)
    
    add_to_y_rotation("FKMiddleFinger1_R",120)
    add_to_y_rotation("FKMiddleFinger2_R", 90)
    add_to_y_rotation("FKMiddleFinger3_R", 90)
    
    add_to_rotation("FKRingFinger1_R", [10,120,0])
    add_to_y_rotation("FKRingFinger2_R", 90)
    add_to_y_rotation("FKRingFinger3_R", 90)

    add_to_rotation("FKPinkyFinger1_R", [10,120,0])
    add_to_y_rotation("FKPinkyFinger2_R", 90)
    add_to_y_rotation("FKPinkyFinger3_R", 90)

    add_to_rotation("FKThumbFinger1_R",[-45,20,-20])
    add_to_y_rotation("FKThumbFinger2_R", 80)
    add_to_y_rotation("FKThumbFinger3_R", 110)

def makeRelaxedHandRight():
    add_to_rotation("FKIndexFinger1_R", [-10,-10,0])
    add_to_y_rotation("FKIndexFinger2_R", -10)
    add_to_y_rotation("FKIndexFinger3_R", -5)
        
    add_to_y_rotation("FKMiddleFinger1_R",55)
    add_to_y_rotation("FKMiddleFinger2_R", 55)
    add_to_y_rotation("FKMiddleFinger3_R", 35)

    add_to_rotation("FKRingFinger1_R", [5,90,0])
    add_to_y_rotation("FKRingFinger2_R", 80)
    add_to_y_rotation("FKRingFinger3_R", 45)
        
    add_to_rotation("FKPinkyFinger1_R", [10,110,0])
    add_to_y_rotation("FKPinkyFinger2_R", 110)
    add_to_y_rotation("FKPinkyFinger3_R", 80)

    add_to_rotation("FKThumbFinger1_R",[-45,20,-20])
    add_to_y_rotation("FKThumbFinger2_R", 35)
    add_to_y_rotation("FKThumbFinger3_R", 35)
    

def spreadFingersRight():
    add_to_rotation("FKIndexFinger1_R", [0,0,20])
    add_to_rotation("FKPinkyFinger1_R", [0,0,-20])
    
def selectFingersRight():
    select_objects("FKIndexFinger1_R", "FKIndexFinger2_R","FKMiddleFinger1_R", "FKMiddleFinger2_R", "FKPinkyFinger1_R", "FKPinkyFinger2_R")
    
def selectFingersLeft():
    select_objects("FKIndexFinger1_L", "FKIndexFinger2_L","FKMiddleFinger1_L", "FKMiddleFinger2_L", "FKPinkyFinger1_L", "FKPinkyFinger2_L")
    
    

####################CREATE ARMOR####################

def createArmorMaterial(*args):
	armor_mat_name = "armor_mat"
	if m.objExists(armor_mat_name):
		armor_mat = m.ls(armor_mat_name, materials=True)[0]
		SGs = m.listConnections(armor_mat, type='shadingEngine')
		if SGs:
			armor_SG = SGs[0]
	else:
		armor_mat = m.shadingNode('blinn', asShader=True, name = "armor_mat")
		m.setAttr(armor_mat + '.color', 0.1, 0.1, 0.1, type='double3')
		armor_SG = m.sets(renderable=True, noSurfaceShader=True, empty=True, name = "armor_SG")
		m.connectAttr(armor_mat + '.outColor', armor_SG + '.surfaceShader')

	return armor_SG


def createAllArmor(*args):
	createArmor()
	mirrorArmor()

def createArmor(*args):
    aSG = createArmorMaterial()
    rghtJoints = ["Shoulder", "Elbow", "Hip", "Knee"]
    rghtEndJoints = ["Wrist", "Foot"]
    middleJoints = ["Root", "Spine1", "Chest", "Neck", "Head"]

    gL = m.group(n="LFT", em=True)
    gR = m.group(n="RGT", em=True)
    gM = m.group(n="MDL", em=True)
    m.group(gL, gR, gM, n="G_armor")

    def createMiddleShapes(j, g):
        c = m.polyCylinder(sx=10, sy=1, sz=1, h=5, r=16, n="C_"+j+"_M")
        # print(z)
        if c[0] == "C_Head_M":
            m.polyCylinder(c, e=True, sh=2, h=10)
        if c[0] == "C_Neck_M":
            m.polyCylinder(c, e=True, sh=2, h=10, r=10)
        if c[0] == "C_Chest_M":
            m.polyCylinder(c, e=True, sh=2, h=20)
        m.sets(c, e=True, forceElement=aSG)
        innerG = m.group(c, n="G_"+j+"_M")
        m.move(10, 0, 0, c, r=True, os=True)
        m.rotate(0, -90, -90, c)
        m.parentConstraint(j+"_M", innerG)
        m.parent(innerG, g)

    for j in middleJoints:
        createMiddleShapes(j, gM)

    def createRghtShapes(j, g):
        c = m.polyCylinder(sx=10, sy=1, sz=1, h=20, r=6, n="C_"+j+"_R")
        m.sets(c, e=True, forceElement=aSG)

        s = m.polySphere(r=6, sy=6, sx=8, n="S_"+j+"_R")
        m.sets(s, e=True, forceElement=aSG)

        innerG = m.group(c, s, n="G_"+j+"_R")

        m.parentConstraint(j+"_R", innerG)
        m.parent(innerG, g)

        m.rotate(0, 0, 90, c)
        m.rotate(0, 0, 90, s)
        m.move(0, -10, 0, c, r=True, os=True)

        if s[0] == "S_Hip_R":
            m.polySphere(s, e=True, r=12)
        if c[0] == "C_Hip_R":
            m.polyCylinder(c, e=True, sh=2, h=40, r=12)
            m.move(0, -15, 0, c, r=True, os=True)
        if c[0] == "C_Knee_R":
            m.polyCylinder(c, e=True, sh=2, h=40, r=8)
            m.move(0, -10, 0, c, r=True, os=True)

        if c[0] == "C_tit1_R":
            m.polyCylinder(c, e=True, h=5, r=6)
            m.move(0, 5, 0, c, r=True, os=True)

    for j in rghtJoints:
        createRghtShapes(j, gR)

    def createRghtEndShapes(j, g):
        c = m.polyCube(name="C_"+j+"_R", w=5, h=5, d=5)
        m.sets(c, e=True, forceElement=aSG)
        innerG = m.group(c, n="G_"+j+"_R")
        m.parentConstraint(j+"_R", innerG)
        m.parent(innerG, g)

    for j in rghtEndJoints:
        createRghtEndShapes(j, gR)



    
##########REPEAT MIRROR IN NEWLY OPENED SCENE##########

def mirrorArmor(*args):
    if m.objExists("G_armor"):
        children = m.listRelatives("G_armor", children=True)
        if children and "LFT" in children:
            lftArmor = "G_armor|LFT"
        else:
            print("Create node LFT in node G_armor")
    else:
        print("Error: create Armor first")

    rghtJoints = ["Shoulder", "Elbow", "Hip", "Knee"]
    rghtEndJoints = ["Wrist", "Foot"]
    middleJoints = ["Root", "Spine1", "Chest", "Neck", "Head"]

    gL = m.select("LFT")
    gR = m.select("RGT")
    gM = m.select("MDL")

    def mirrorShapes(j, g):
        m.select("C_"+j+"_R")
        m.duplicate(n="C_"+j+"_L")
        m.select("S_"+j+"_R")
        m.duplicate(n="S_"+j+"_L")

        innerG = m.group("C_"+j+"_L", "S_"+j+"_L", n="G_"+j+"_L", w=True)
        m.xform(ws=True, a=True, rp=(0, 0, 0), sp=(0, 0, 0))
        m.scale(-1, 1, 1)
        m.parentConstraint(j+"_L", innerG, mo=True)
        m.parent(innerG, lftArmor)

    for j in rghtJoints:
        mirrorShapes(j, gL)

    def mirrorEndShapes(j, g):
        m.select("C_"+j+"_R")
        m.duplicate(n="C_"+j+"_L")

        innerG = m.group("C_"+j+"_L", n="G_"+j+"_L", w=True)
        m.xform(ws=True, a=True, rp=(0, 0, 0), sp=(0, 0, 0))
        m.scale(-1, 1, 1)
        m.parentConstraint(j+"_L", innerG, mo=True)
        m.parent(innerG, lftArmor)

    for j in rghtEndJoints:
        mirrorEndShapes(j, gL)

   	 
##########REPEAT MIRROR IN NEWLY OPENED SCENE##########
def deleteLeftArmor(*args):
    if cmds.objExists("G_armor|LFT"):
        # Get the children of "G_armor|LFT"
        children = cmds.listRelatives("G_armor|LFT", children=True)

        # Delete each child node
        if children:
            cmds.delete(children)
            print("Deleted all children of 'G_armor|LFT'.")
        else:
            print("There are no children to delete under 'G_armor|LFT'.")
    else:
        print("The node 'G_armor|LFT' does not exist.")


            
def create_window():
    # Check if the window exists
    if cmds.window('simpeCRig', exists=True):
        cmds.deleteUI('simpeCRig', window=True)
    
    # Create a new window
    window = cmds.window('simpeCRig', title='Simple C Rig', widthHeight=(400, 100))
    
    # Create a column layout
    cmds.columnLayout(adjustableColumn=True)
    
    # Add a button that calls the on_button_click function when pressed
    cmds.button(label='pre Rig', command=preRig)
    cmds.button(label='Create Advanced Skeleton', command=createRig)
    cmds.button(label='Bind Body / Parent Head', command=bindSkinToCharacter)
    cmds.button(label='Bind Body AND Head', command=bindSkinAndHeadToCharacter)
    cmds.separator(height=50, style='in')

    cmds.button(label='Adjust Controllers', command=adjustControllers)   
    
    # Add a text field for size input
    cmds.text(label='Finger Controller Size:')
    fingerSize_field = cmds.floatField(value=1.0)
    
    # Add a button to trigger the adjustControllersQuadPed function
    cmds.button(label='Adjust Finger Controllers', command=lambda x: adjustControllersFingers(cmds.floatField(fingerSize_field, query=True, value=True)))

    # Add a text field for size input
    cmds.text(label='Upperlip Controller Size:')
    upperLipSize_field = cmds.floatField(value=0.5)
    
    # Add a button to trigger the adjustControllersQuadPed function
    cmds.button(label='Resize UpperLip Controllers', command=lambda x: adjustControllersMouthUp(cmds.floatField(upperLipSize_field, query=True, value=True)))

    # Add a text field for size input
    cmds.text(label='Lowerlip Controller Size:')
    lowerLipSize_field = cmds.floatField(value=0.5)
    
    # Add a button to trigger the adjustControllersQuadPed function
    cmds.button(label='Resize LowerLip Controllers', command=lambda x: adjustControllersMouthLow(cmds.floatField(lowerLipSize_field, query=True, value=True)))

    cmds.button(label='Adjust Mouth Controllers', command=lambda x: pushMouthVerticesForward())
    cmds.button(label='Adjust Eye Brow Cheek Controllers', command=lambda x: adjustEyeBrowCheekControllers())

    # Add a text field for size input
    cmds.text(label='BrowAndCheek Controller Size:')
    browSize_field = cmds.floatField(value=0.5)
    
    cmds.button(label='Resize BrowCheek Controllers', command=lambda x: adjustBrowsAndCheeks(cmds.floatField(browSize_field, query=True, value=True)))
    
    cmds.separator(height=20, style='out')   
    
    cmds.button(label='make fist right', command=lambda x: makeFistRight())
    cmds.button(label='make relaxedHand right', command=lambda x: makeRelaxedHandRight())
    cmds.button(label='spread fingers right', command=lambda x: spreadFingersRight())
    cmds.separator(height=20, style='out')
    cmds.button(label='select fingers right', command=lambda x: selectFingersRight())
    cmds.button(label='select fingers left', command=lambda x: selectFingersLeft())
    
    m.iconTextStaticLabel( st='textOnly', l='CREATE ARMOR' )
    m.button(label="create Armor", command = createAllArmor, width = 12)
    m.button(label="mirror (rght to lft)", command = mirrorArmor, width = 12)
    m.button(label="delete left armor", command = deleteLeftArmor, width = 12)
    # Show the window
    cmds.showWindow(window)

# Run the function to create the window
create_window()

