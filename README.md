# Maya Python Animation Scripts

A collection of Maya Python scripts for procedural animation generation, rigging utilities, scene cleanup, and export tooling. Built around the **AdvancedSkeleton** rig naming convention. All animation generators provide GUI windows with adjustable parameters, JSON preset import/export, and operate on the current timeline range.

---

## Animation Generator Scripts

### walkcycleGenerator.py — `WalkCycleTool`

Generates a bipedal walk cycle using IK legs and FK upper body.

| Controller | Type | Attributes Keyed | Role |
|---|---|---|---|
| `IKLeg_R` | IK Handle | translateX, translateY, translateZ, rotateX, stretchy | Right foot stride, lift, raise |
| `IKLeg_L` | IK Handle | translateX, translateY, translateZ, rotateX, stretchy | Left foot stride, lift, raise |
| `HipSwinger_M` | FK | rotateX, rotateY | Hip swing (forward/back) and sway (L/R) |
| `RootX_M` | Root | translateX, translateY, translateZ, rotateX, rotateY, rotateZ | Bounce, sway, rock, twist, left-right, back-forth |
| `FKSpine1_M` | FK | rotateX, rotateY, rotateZ | Spine twist/sway/rock |
| `FKChest_M` | FK | rotateX, rotateY, rotateZ | Chest twist/sway/rock |
| `FKNeck_M` | FK | rotateX, rotateY, rotateZ | Neck counter-motion |
| `FKHead_M` | FK | rotateX, rotateY, rotateZ | Head counter-motion |
| `FKScapula_R` | FK | rotateY, rotateZ | Right scapula down + swing |
| `FKScapula_L` | FK | rotateY, rotateZ | Left scapula (mirrored) |
| `FKShoulder_R` / `_L` | FK | rotateX, rotateY, rotateZ | Shoulder down position + arm swing |
| `FKElbow_R` / `_L` | FK | rotateZ | Elbow bend during swing |
| `FKWrist_R` / `_L` | FK | rotateZ | Wrist follow-through |

---

### runCycleGenerator.py — `RunCycleGenerator`

Generates a bipedal run cycle with enhanced dynamics (bounce, lean, corkscrew twist).

| Controller | Type | Attributes Keyed | Role |
|---|---|---|---|
| `RootX_M` | Root | translateX, translateY, translateZ, rotateX, rotateY, rotateZ | Bounce up/down, lean, sway, swing, corkscrew, back-forth |
| `IKLeg_R` | IK Handle | translateX, translateY, translateZ, rotateX | Right foot stride, height, raise |
| `IKLeg_L` | IK Handle | translateX, translateY, translateZ, rotateX | Left foot stride, height, raise |
| `FKChest_M` (alias: `FKChest1_M`) | FK | rotateX, rotateY, rotateZ | Chest bounce, swing, tilt |
| `FKSpine_M` (alias: `FKSpine1_M`) | FK | rotateX, rotateY, rotateZ | Spine bounce, swing, tilt |
| `HipSwinger_M` (alias: `HipSwinger1_M`) | FK | rotateX, rotateY | Hip swing and side motion |
| `FKNeck_M` | FK | translateY, rotateX, rotateY, rotateZ | Neck bounce, rock, lean, sway, swing |
| `FKHead_M` (alias: `FKHead1_M`) | FK | translateY, rotateX, rotateY, rotateZ | Head bounce, rock, lean, sway, swing |
| `FKScapula1_L` / `FKScapula_L` | FK | rotateZ | Left scapula swing |
| `FKScapula1_R` / `FKScapula_R` | FK | rotateZ | Right scapula swing |
| `FKShoulder_L` / `_R` | FK | rotateX, rotateY, rotateZ | Shoulder down, rotate, swing, sway-out |
| `FKElbow_L` / `_R` | FK | rotateZ | Elbow flex (forward bias) |

---

### sideStepGenerator.py — `SideStepGenerator`

Generates a lateral side-step animation with mirroring support.

| Controller | Type | Attributes Keyed | Role |
|---|---|---|---|
| `RootX_M` | Root | translateX, translateY, rotateZ | Root shift, bounce, tilt |
| `IKLeg_R` | IK Handle | translateX, translateY | Right foot lateral step |
| `IKLeg_L` | IK Handle | translateX, translateY | Left foot lateral step |
| `HipSwinger_M` | FK | rotateY | Hip sway (side whip) |
| `FKSpine1_M` | FK | rotateY | Spine sway |
| `FKChest_M` | FK | rotateY | Chest sway |
| `FKNeck_M` | FK | rotateY | Neck sway |
| `FKHead_M` | FK | rotateY | Head sway |
| `FKScapula_L` / `_R` | FK | rotateX, rotateY, rotateZ | Scapula swing + additive down/bent/twist |
| `FKShoulder_L` / `_R` | FK | rotateX, rotateY, rotateZ | Shoulder swing + additive |
| `FKElbow_L` / `_R` | FK | rotateX, rotateY, rotateZ | Elbow swing + additive |
| `FKWrist_L` / `_R` | FK | rotateX, rotateY, rotateZ | Wrist additive pose |

---

### handWalkCycleGenerator.py — `HandWalkCycleTool`

Generates a quadruped-style hand-walk cycle (character walking on hands). Uses IK arms for hand placement and IK legs for feet.

| Controller | Type | Attributes Keyed | Role |
|---|---|---|---|
| `IKArm_R` / `IKArm_L` | IK Handle | translateX, translateY, translateZ, rotateY, stretchy | Hand stride, lift, offsets |
| `RootX_M` | Root | translateX, translateY, translateZ, rotateX, rotateY, rotateZ | Bounce, sway, rock, shift, swing, forward bounce |
| `HipSwinger_M` | FK | rotateX, rotateY | Hip swing and sway |
| `IKLeg_R` / `IKLeg_L` | IK Handle | translateX, translateY, translateZ, rotateX | Feet follow with offsets, bounce, swing, back-forth |
| `FKScapula_L` / `_R` | FK | rotateX, rotateY, rotateZ | Scapula rotation + offsets |
| `FKSpine_M` / `FKSpine1_M` | FK | rotateX, rotateY, rotateZ | Spine swing, rock, sway |
| `FKChest_M` | FK | rotateX, rotateY, rotateZ | Chest swing, rock, sway |
| `FKNeck_M` | FK | translateX, translateY, translateZ, rotateX, rotateY, rotateZ | Neck counter-rotation, bounce, bob, sway |
| `FKHead_M` | FK | translateX, translateY, translateZ, rotateX, rotateY, rotateZ | Head counter-rotation, bounce, bob, sway |
| `PoleArm_R` / `PoleArm_L` | Pole Vector | translateX, translateY, translateZ | Elbow pole positioning |
| `FKIKLeg_R` / `FKIKLeg_L` | Blend | FKIKBlend | FK/IK leg blend (0..10) |
| `FKHip_R` / `_L` | FK | rotateZ | FK leg hip pose |
| `FKKnee_R` / `_L` | FK | rotateZ | FK leg knee pose |
| `FKFoot_R` / `_L` | FK | rotateZ | FK leg foot pose |
| `FKToe_R` / `_L` | FK | rotateZ | FK leg toe pose |

---

### HandSideStepGenerator.py — `HandSideStepGenerator`

Generates a lateral side-step using hands (IK arms) as the stepping limbs.

| Controller | Type | Attributes Keyed | Role |
|---|---|---|---|
| `IKArm_R` / `IKArm_L` | IK Handle | translateX, translateY, stretchy | Hand lateral step, lift |
| `RootX_M` | Root | translateX, translateY, rotateZ | Root shift, bounce, tilt |
| `HipSwinger_M` | FK | rotateY | Hip sway |
| `FKSpine1_M` | FK | rotateY | Spine sway |
| `FKChest_M` | FK | rotateY | Chest sway |
| `FKNeck_M` | FK | rotateY | Neck sway |
| `FKHead_M` | FK | rotateY | Head sway |
| `FKScapula_L` / `_R` | FK | rotateX, rotateY, rotateZ | Scapula swing + additive |
| `FKIKLeg_R` / `FKIKLeg_L` | Blend | FKIKBlend | FK/IK leg blend |
| `FKHip_R` / `_L` | FK | rotateZ | FK leg hip pose (static) |
| `FKKnee_R` / `_L` | FK | rotateZ | FK leg knee pose (static) |
| `FKFoot_R` / `_L` | FK | rotateZ | FK leg foot pose (static) |
| `FKToe_R` / `_L` | FK | rotateZ | FK leg toe pose (static) |

---

### FlightGenerator.py — `FlightGenerator`

Generates a flying/flapping animation cycle using IK arms for wing motion.

| Controller | Type | Attributes Keyed | Role |
|---|---|---|---|
| `IKArm_L` / `IKArm_R` | IK Handle | translateX, translateY, translateZ, rotateX, rotateY | Wing flap (Z), hand flap (Y), positioning (X/Y), arm angle (X) |
| `FKIKArm_L` / `FKIKArm_R` | Blend | FKIKBlend | Arm FK/IK blend (0..10) |
| `RootX_M` | Root | translateY, translateZ, rotateX | Up/down, back/forth translate, rotateX |
| `FKScapula_L` / `_R` | FK | rotateX, rotateY, rotateZ | Scapula flap with offset/base/mid per axis |
| `PoleArm_L` / `PoleArm_R` | Pole Vector | translateX, translateY, translateZ | Elbow pole positioning with offset + base/mid |
| `FKSpine1_M` / `FKSpine_M` | FK | rotateZ | Spine stretch & bend posture |
| `FKChest_M` | FK | rotateZ | Chest stretch & bend posture |
| `FKNeck_M` | FK | rotateZ | Neck stretch & bend posture |
| `FKHead_M` | FK | rotateZ | Head stretch & bend posture |
| `IKLeg_L` / `IKLeg_R` | IK Handle | translateX, translateY, translateZ, rotateX | Feet position and angle during flight |

---

### tailSwingAndWiggleGenerator.py — `TailWiggleGenerator`

Generates oscillating animation on any sequential FK chain (tails, hair, trunks, tentacles, etc.).

| Controller | Type | Attributes Keyed | Role |
|---|---|---|---|
| `FK{name}{N}_{side}` (e.g. `FKhair0_M`) | FK Chain | rotateX, rotateY, rotateZ | Per-joint amplitude, offset, halves/sine patterns |

> The chain is auto-detected from a seed name (e.g., `FKhair0_M` finds `FKhair0_M`, `FKhair1_M`, ...). Supports mirror X/Y/Z globally. Works on any numbered FK chain.

---

## Consolidated Controller Reference

All unique controllers targeted by the animation scripts:

### Root & Body Core
| Controller | Used By |
|---|---|
| `RootX_M` | Walk, Run, SideStep, HandWalk, HandSideStep, Flight |
| `HipSwinger_M` | Walk, Run, SideStep, HandWalk, HandSideStep |
| `FKSpine1_M` / `FKSpine_M` | Walk, Run, SideStep, HandWalk, HandSideStep, Flight |
| `FKChest_M` | Walk, Run, SideStep, HandWalk, HandSideStep, Flight |
| `FKNeck_M` | Walk, Run, SideStep, HandWalk, HandSideStep, Flight |
| `FKHead_M` | Walk, Run, SideStep, HandWalk, HandSideStep, Flight |

### IK Legs
| Controller | Used By |
|---|---|
| `IKLeg_R` | Walk, Run, SideStep, HandWalk, Flight |
| `IKLeg_L` | Walk, Run, SideStep, HandWalk, Flight |

### IK Arms
| Controller | Used By |
|---|---|
| `IKArm_R` | HandWalk, HandSideStep, Flight |
| `IKArm_L` | HandWalk, HandSideStep, Flight |

### FK Arms
| Controller | Used By |
|---|---|
| `FKScapula_R` / `FKScapula_L` | Walk, Run, SideStep, HandWalk, HandSideStep, Flight |
| `FKShoulder_R` / `FKShoulder_L` | Walk, Run, SideStep |
| `FKElbow_R` / `FKElbow_L` | Walk, Run, SideStep |
| `FKWrist_R` / `FKWrist_L` | Walk, SideStep |

### FK Legs (for hand-walk modes)
| Controller | Used By |
|---|---|
| `FKHip_R` / `FKHip_L` | HandWalk, HandSideStep |
| `FKKnee_R` / `FKKnee_L` | HandWalk, HandSideStep |
| `FKFoot_R` / `FKFoot_L` | HandWalk, HandSideStep |
| `FKToe_R` / `FKToe_L` | HandWalk, HandSideStep |

### Pole Vectors
| Controller | Used By |
|---|---|
| `PoleArm_R` / `PoleArm_L` | HandWalk, Flight |

### FK/IK Blend Switches
| Controller | Used By |
|---|---|
| `FKIKArm_L` / `FKIKArm_R` | Flight |
| `FKIKLeg_L` / `FKIKLeg_R` | HandWalk, HandSideStep |

### Dynamic Chains (variable)
| Controller | Used By |
|---|---|
| `FK{name}{N}_{side}` (e.g. `FKhair0_M`) | TailWiggle |

### Custom Attributes Used
| Attribute | On Controllers | Used By |
|---|---|---|
| `stretchy` | IKLeg_R/L, IKArm_R/L | Walk (legs), HandWalk (arms) |
| `FKIKBlend` | FKIKArm_R/L, FKIKLeg_R/L | Flight (arms), HandWalk/HandSideStep (legs) |

---

## Utility Scripts

### clipSetter.py — `GameExporterGenerator`
GUI tool to generate Maya Game FBX Exporter `.mel` preset files. Defines animation clip blocks (name, count, frame length) and outputs clips with frame ranges, optionally with color-tagged house variants.

### SceneCleanup.py / toolsWindow.py
Scene cleanup and utility tools:
- Delete constraints, characters, script nodes, Mental Ray nodes
- Remove legacy plugin requirements
- Rename selected nodes with `_##` suffix
- Delete/rename UV sets, set active UV set
- Grid-place selected objects
- Spiral curve generator
- Circular instance/copy ring generator
- Remove substrings from node names

### renderLayerSetter.py
Automated render layer setup (PyMEL, tested on Maya 2017/2018, uses legacy render layers). Creates per-light render layers, ambient occlusion layer, depth-of-field layer, and per-object mask layers with shader networks.

**Prerequisites:** geometry in a group called `renderset`, a camera called `rendercam`. Shader assignment must be per-object (not per-face).

### simpleCharacterRig_01.py / SimpleCRig.py
Character rigging preparation utilities:
- Mesh mirroring with UV correction
- Pre-rig cleanup (delete constraints, history, mirror meshes, combine)
- AdvancedSkeleton rig creation (calls `asReBuildAdvancedSkeleton`)
- Skin binding to `Root_M`
- Controller shape adjustment (scaling CVs on `RootX_M`, `FKNeck_M`, `FKRoot_M`, `FKSpine1_M`, `FKChest_M`, etc.)

---

## Next Steps: Auto Control Rig for citizen_REF.fbx (s&box)

The imported `citizen_REF.fbx` from s&box will have an existing joint hierarchy but **no AdvancedSkeleton controls**. To use these animation scripts, we need to create a control rig setup script that:

1. **Maps the s&box skeleton joints** to the expected AdvancedSkeleton controller names
2. **Creates the following control elements** on the imported rig:

### Required Controls to Create

| Control Name | Type | Purpose | Minimum Channels |
|---|---|---|---|
| `RootX_M` | NURBS Curve | Master root mover | tX, tY, tZ, rX, rY, rZ |
| `HipSwinger_M` | NURBS Curve | Hip rotation | rX, rY |
| `IKLeg_R` / `IKLeg_L` | IK + NURBS Curve | Foot placement | tX, tY, tZ, rX + `stretchy` attr |
| `IKArm_R` / `IKArm_L` | IK + NURBS Curve | Hand placement | tX, tY, tZ, rX, rY + `stretchy` attr |
| `FKSpine1_M` | NURBS Curve | Spine FK | rX, rY, rZ |
| `FKChest_M` | NURBS Curve | Chest FK | rX, rY, rZ |
| `FKNeck_M` | NURBS Curve | Neck FK | tX, tY, tZ, rX, rY, rZ |
| `FKHead_M` | NURBS Curve | Head FK | tX, tY, tZ, rX, rY, rZ |
| `FKScapula_R` / `_L` | NURBS Curve | Scapula FK | rX, rY, rZ |
| `FKShoulder_R` / `_L` | NURBS Curve | Shoulder FK | rX, rY, rZ |
| `FKElbow_R` / `_L` | NURBS Curve | Elbow FK | rZ |
| `FKWrist_R` / `_L` | NURBS Curve | Wrist FK | rX, rY, rZ |
| `FKHip_R` / `_L` | NURBS Curve | FK leg hip | rZ |
| `FKKnee_R` / `_L` | NURBS Curve | FK leg knee | rZ |
| `FKFoot_R` / `_L` | NURBS Curve | FK leg foot | rZ |
| `FKToe_R` / `_L` | NURBS Curve | FK leg toe | rZ |
| `PoleArm_R` / `_L` | Locator | Elbow pole vector | tX, tY, tZ |
| `FKIKArm_R` / `_L` | Attr holder | Arm FK/IK switch | `FKIKBlend` (0..10) |
| `FKIKLeg_R` / `_L` | Attr holder | Leg FK/IK switch | `FKIKBlend` (0..10) |

### Mapping Strategy

The auto-rig script will need to:

1. **Detect/map joints** from the FBX skeleton to AdvancedSkeleton naming
2. **Create NURBS curve controls** at each joint position with proper orientation
3. **Set up IK handles** for legs and arms (RP solvers)
4. **Create pole vectors** for elbows and knees
5. **Add custom attributes** (`stretchy`, `FKIKBlend`) on relevant controls
6. **Parent-constrain or orient-constrain** the FK controls to drive the joints
7. **Group controls** under a clean hierarchy (`Group|Main|...`)

> **Note**: All scripts include `resolve_node_case_insensitive()` which tries alias variants like `FKScapula1_L` ↔ `FKScapula_L` and `FKSpine1_M` ↔ `FKSpine_M`. The auto-rig can use either naming convention.


