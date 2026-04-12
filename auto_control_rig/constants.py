RIG_GRP = "AutoCtrlRig_GRP"

SLOT_DEFS = [
    ("root",       "Root / Pelvis",        "M", ["pelvis","hips","root"]),
    ("spine",      "Spine",                "M", ["spine_01","spine1","spine"]),
    ("spine_1",    "Spine 1 (Mid)",        "M", ["spine_02","spine2","spine_1","spine1a"]),
    ("chest",      "Chest",                "M", ["spine_03","spine3","chest"]),
    ("neck",       "Neck",                 "M", ["neck"]),
    ("head",       "Head",                 "M", ["head"]),
    ("scapula_l",  "Scapula / Clavicle L", "L", ["clavicle_l","l_clavicle","shoulder_l","leftshoulder"]),
    ("shoulder_l", "Upper Arm L",          "L", ["upperarm_l","l_upperarm","arm_l","leftarm"]),
    ("elbow_l",    "Lower Arm L",          "L", ["lowerarm_l","l_lowerarm","forearm_l","leftforearm"]),
    ("wrist_l",    "Hand L",               "L", ["hand_l","l_hand","lefthand"]),
    ("scapula_r",  "Scapula / Clavicle R", "R", ["clavicle_r","r_clavicle","shoulder_r","rightshoulder"]),
    ("shoulder_r", "Upper Arm R",          "R", ["upperarm_r","r_upperarm","arm_r","rightarm"]),
    ("elbow_r",    "Lower Arm R",          "R", ["lowerarm_r","r_lowerarm","forearm_r","rightforearm"]),
    ("wrist_r",    "Hand R",               "R", ["hand_r","r_hand","righthand"]),
    ("hip_l",      "Upper Leg L",          "L", ["thigh_l","l_thigh","upperleg_l","leftupleg"]),
    ("knee_l",     "Lower Leg L",          "L", ["calf_l","l_calf","lowerleg_l","shin_l","leftleg"]),
    ("foot_l",     "Foot L",               "L", ["foot_l","l_foot","leftfoot"]),
    ("toe_l",      "Toe L",                "L", ["toe_l","l_toe","ball_l","lefttoebase"]),
    ("hip_r",      "Upper Leg R",          "R", ["thigh_r","r_thigh","upperleg_r","rightupleg"]),
    ("knee_r",     "Lower Leg R",          "R", ["calf_r","r_calf","lowerleg_r","shin_r","rightleg"]),
    ("foot_r",     "Foot R",               "R", ["foot_r","r_foot","rightfoot"]),
    ("toe_r",      "Toe R",                "R", ["toe_r","r_toe","ball_r","righttoebase"]),
    ("eye_l",      "Eye L",                "L", ["eye_l","l_eye","lefteye"]),
    ("eye_r",      "Eye R",                "R", ["eye_r","r_eye","righteye"]),
    ("eyelid_upper_l", "Eyelid Upper L",   "L", ["eyelid_upper_l","lid_upper_l","upperlid_l"]),
    ("eyelid_lower_l", "Eyelid Lower L",   "L", ["eyelid_lower_l","lid_lower_l","lowerlid_l"]),
    ("eyelid_upper_r", "Eyelid Upper R",   "R", ["eyelid_upper_r","lid_upper_r","upperlid_r"]),
    ("eyelid_lower_r", "Eyelid Lower R",   "R", ["eyelid_lower_r","lid_lower_r","lowerlid_r"]),
    ("ear_l",      "Ear L",                "L", ["ear_l","l_ear","leftear"]),
    ("ear_r",      "Ear R",                "R", ["ear_r","r_ear","rightear"]),
]

SLOT_TO_CTRL = {
    "root": "RootX_M", "spine": "FKSpine1_M", "spine_1": "FKSpine2_M",
    "chest": "FKChest_M",
    "neck": "FKNeck_M", "head": "FKHead_M",
    "scapula_l": "FKScapula_L", "shoulder_l": "FKShoulder_L",
    "elbow_l": "FKElbow_L", "wrist_l": "FKWrist_L",
    "scapula_r": "FKScapula_R", "shoulder_r": "FKShoulder_R",
    "elbow_r": "FKElbow_R", "wrist_r": "FKWrist_R",
    "hip_l": "FKHip_L", "knee_l": "FKKnee_L", "foot_l": "FKFoot_L", "toe_l": "FKToe_L",
    "hip_r": "FKHip_R", "knee_r": "FKKnee_R", "foot_r": "FKFoot_R", "toe_r": "FKToe_R",
    "eye_l": "EyeAim_L", "eye_r": "EyeAim_R",
    "eyelid_upper_l": "FKEyelidUpper_L", "eyelid_lower_l": "FKEyelidLower_L",
    "eyelid_upper_r": "FKEyelidUpper_R", "eyelid_lower_r": "FKEyelidLower_R",
    "ear_l": "FKEar_L", "ear_r": "FKEar_R",
}

FINGER_NAMES = ("thumb", "index", "middle", "ring", "pinky")

COL_L = 13
COL_R = 6
COL_M = 17
COL_IK = 18
COL_POLE = 9
