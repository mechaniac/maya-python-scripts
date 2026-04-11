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

## Auto Control Rig — `autoControlRig.py`

Generates AdvancedSkeleton-compatible controls on **any joint hierarchy**, designed for use with the **s&box Citizen character rig** (`citizen_REF.fbx`) but works with any skeleton. A clean intermediate "driver" skeleton is built with proper orientations; IK/FK controls drive the driver joints, which in turn parent-constrain the original skin joints.

**Usage:**
```python
import autoControlRig; autoControlRig.show()
```

### Architecture

```
                     ┌─ FK Controls ──► FK Driver joints ──┐
Main_M ──► RootX_M ──┤                                     ├─ parentConstraint (blended) ──► Skin joints
                     └─ IK Controls ──► IK Driver joints ──┘
```

**Dual-chain FK/IK**: Each limb and the spine gets separate FK and IK driver joint chains. Skin joints receive a dual-target parentConstraint blended by the FKIK weight. The original skeleton is never modified — only constrained. Removing the rig restores the exact bind pose.

- **Main_M** — World-space master controller at the origin. All rig groups (Ctrl_GRP, Driver_GRP, IK_GRP, Misc_GRP) parent under it. ScaleConstraint from Main_M to the root skin joint provides uniform global scaling.
- **chestFollow_M** — Blends between FK and IK chest controls so neck, head, and arms always follow the active spine mode.
- **Space switching** — IK legs: Main / Root. IK arms: Main / Root / Chest / Head. Enum attr on each IK control with condition-driven parentConstraint weights.
- **Driver visibility** — Inactive driver joint chains are hidden via `drawStyle` toggling (Bone ↔ None) so only the active chain is visible.

### s&box Citizen Integration

The script auto-maps the s&box Citizen skeleton joints to rig slots via case-insensitive name matching. The default `SLOT_DEFS` hints cover the Citizen naming convention (`pelvis`, `spine_01`, `thigh_l`, `calf_l`, `foot_l`, `ball_l`, `clavicle_l`, `upperarm_l`, `lowerarm_l`, `hand_l`, etc.). Joint mappings can be saved/loaded as JSON presets for reuse across scenes.

### UI Workflow

1. **From Selection** — select the root joint, click to populate the hierarchy
2. **Auto-Map** — automatically matches joints to rig slots by name hints
3. **Create Foot Roll Locators** — (optional) place heel/toetip locators for precise reverse foot positions
4. **Build Control Rig** — generates the full rig with selected options
5. **Remove Control Rig** — cleanly deletes everything and restores bind pose

### Joint Mapping Slots

| Slot | Label | Side | Example Citizen Joint |
|---|---|---|---|
| `root` | Root / Pelvis | M | `pelvis` |
| `spine` | Spine | M | `spine_01` |
| `spine_1` | Spine 1 | M | `spine_02`, `spine2` |
| `chest` | Chest | M | `spine_03`, `spine_2` |
| `neck` | Neck | M | `neck` |
| `head` | Head | M | `head` |
| `scapula_l/r` | Scapula / Clavicle | L/R | `clavicle_l` |
| `shoulder_l/r` | Upper Arm | L/R | `upperarm_l` |
| `elbow_l/r` | Lower Arm | L/R | `lowerarm_l` |
| `wrist_l/r` | Hand | L/R | `hand_l` |
| `hip_l/r` | Upper Leg | L/R | `thigh_l` |
| `knee_l/r` | Lower Leg | L/R | `calf_l` |
| `foot_l/r` | Foot | L/R | `foot_l` |
| `toe_l/r` | Toe | L/R | `ball_l` |

### Controls Created

| Control | Type | Purpose |
|---|---|---|
| `Main_M` | NURBS Circle | World-space master controller, global scale |
| `RootX_M` | NURBS Circle | Master root translation |
| `HipSwinger_M` | NURBS Circle | Hip orientation (parented under RootX_M) |
| `FKSpine1_M` | NURBS Circle | Spine FK orient |
| `FKSpine2_M` | NURBS Circle | Spine 1 FK orient |
| `FKChest_M` | NURBS Circle | Chest FK orient |
| `FKNeck_M` | NURBS Circle | Neck FK orient |
| `FKHead_M` | NURBS Circle | Head FK orient |
| `FKScapula_L/R` | NURBS Circle | Scapula FK orient |
| `FKShoulder_L/R` | NURBS Circle | Upper arm FK orient |
| `FKElbow_L/R` | NURBS Circle | Lower arm FK orient |
| `FKWrist_L/R` | NURBS Circle | Hand FK orient |
| `FKHip_L/R` | NURBS Circle | Upper leg FK orient |
| `FKKnee_L/R` | NURBS Circle | Lower leg FK orient |
| `FKFoot_L/R` | NURBS Circle | Foot FK orient |
| `FKToe_L/R` | NURBS Circle | Toe FK orient |
| `IKLeg_L/R` | Box Curve | IK foot placement (ikRPsolver) |
| `IKArm_L/R` | Box Curve | IK hand placement (ikRPsolver) |
| `PoleLeg_L/R` | Cross Curve | Knee pole vector |
| `PoleArm_L/R` | Cross Curve | Elbow pole vector |
| `IKSpine_M` | NURBS Circle | IK spine bottom (hip-level, spline solver) |
| `IKSpineMid_M` | NURBS Circle | IK spine mid (S-curve deformation) |
| `IKChest_M` | NURBS Circle | IK spine top (chest-level, drives appendages) |
| `FKIKSpine_M` | Diamond Curve | Spine FK/IK blend switch (`FKIKBlend` 0–10) |
| `FKIKLeg_L/R` | Diamond Curve | Leg FK/IK blend switch (`FKIKBlend` 0–10) |
| `FKIKArm_L/R` | Diamond Curve | Arm FK/IK blend switch (`FKIKBlend` 0–10) |

### Build Options

| Option | Default | Description |
|---|---|---|
| IK Legs | On | Create IK leg controls with ikRPsolver |
| IK Arms | On | Create IK arm controls with ikRPsolver |
| IK Spine | On | Create IK spline spine with 3 controllers (bottom, mid, top) |
| FK Arms | On | Create FK arm chain controls |
| FK Legs | On | Create FK leg chain controls |
| FK/IK Blend | On | Create blend switches with visibility toggling and driver chain hiding |
| Twist Joints | On | Create twist joint drivers for upper/lower arm and leg segments |
| Show Debug | Off | Create debug locators on all driver joints and foot roll pivots |
| Control Size | 1.0 | Global scale for all generated controls |
| Scale Taper | 1.3 | FK chain controls taper larger toward root |

### IK Foot Roll (Reverse Foot)

The IK leg setup includes a full **reverse foot roll** system:

- **Reverse hierarchy**: `footFollow → heelPiv → toetipPiv → ballPiv → [IK handle]`
- **SC solver** from foot to toe keeps the toe aimed forward during ball roll
- **Orient constraint** on the toe driver targets `toetipPiv` to keep toes flat on the ground while the heel lifts
- **Expression-driven** — `Roll`, `RollStartAngle`, and `RollEndAngle` are live attributes on the IK foot control that update in real time

| Roll Range | Heel (rx) | Ball (rx) | Toetip (rx) |
|---|---|---|---|
| -90 → 0 | Ramps from -90 to 0 | 0 | 0 |
| 0 → Start | 0 | Ramps 0 → Start | 0 |
| Start → End | 0 | Ramps Start → 0 | Ramps 0 → (End - Start) |

**Foot Roll Locators**: Optional pre-build locators (`footRoll_heel_L/R`, `footRoll_toetip_L/R`) can be positioned to customize heel and toe-tip pivot locations. If absent, default positions are computed from foot/toe joint locations.

### Debug Visualization

When **Show Debug** is enabled, locators are created for:
- All driver joints (`dbg_root`, `dbg_spine`, `dbg_foot_l`, `dbg_toe_l`, etc.)
- Foot roll pivots: `dbg_heelPiv_L/R` (yellow), `dbg_ballPiv_L/R` (yellow), `dbg_toetipPiv_L/R` (brown)

All debug locators are parent-constrained to their targets and track position + rotation in real time.

### IK Spline Spine

When **IK Spine** is enabled, a spline IK solver drives the spine with three controllers:

- **IKSpine_M** — Bottom control at the hip/spine base. Drives first CV of the spline curve.
- **IKSpineMid_M** — Mid control at the spine_1 level. Drives the middle CVs for S-curve deformation.
- **IKChest_M** — Top control at the chest level. Drives last CV. Appendages (neck, head, arms) follow via `chestFollow_M`.

Advanced twist uses object rotation up (start = IKSpine_M, end = IKChest_M). The spline curve has `inheritsTransform` disabled to prevent double transforms. All three IK spine offsets parent under `RootX_M` so they follow the root.

### Twist Joints

When **Twist Joints** is enabled, twist extraction joints are created for upper/lower arm and leg segments. These distribute forearm twist and upper-arm roll across multiple joints for smoother deformation.

### Helper Joint Correctives

Automatic corrective helper joints at elbows and knees that activate based on bend angle to maintain volume during extreme poses.

### Post-Rig Utilities

- **Select All Controls** — selects all NURBS curve controls in the rig (filters by nurbsCurve shapes)
- **Return to Bind Pose** — zeros all control transforms and resets custom attributes to defaults (top-down order, includes Main_M)
- **Remove Control Rig** — deletes all rig nodes, removes skin joint constraints, restores original bind pose transforms

---

## Roadmap — Planned Features & Ideas

Informed by state-of-the-art rigging systems (AdvancedSkeleton, mGear, Rapid Rig, Houdini KineFX/APEX, Unreal Control Rig). Organized roughly by priority and complexity.

### High Priority

| Feature | Description | Status |
|---|---|---|
| **Space Switching** | IK legs: Main / Root. IK arms: Main / Root / Chest / Head. Enum attr with condition-driven parentConstraint weights. | ✅ Done |
| **IK/FK Snap Matching** | One-click buttons to match FK pose → current IK result and vice versa. Eliminates pose pops when blending. | Planned |
| **Stretchy IK Limbs** | Distance-based limb stretching via joint scale when IK target exceeds chain length. Soft-IK falloff to prevent pop at full extension. | Planned |
| **Finger / Hand Controls** | FK chain per finger with master curl, spread, and fist attributes on a single hand control. | Planned |
| **Global Scale** | ScaleConstraint from Main_M to root skin joint. Uniform scaling of rig + mesh. | ✅ Done |

### Medium Priority

| Feature | Description | Status |
|---|---|---|
| **IK Spine (Spline IK)** | 3-controller IK spline (bottom/mid/top) with FK/IK blend, chest follow for appendages, advanced twist. | ✅ Done |
| **Head Aim / Look-At** | Aim constraint on head with a world-space target locator. Auto look-at with adjustable blend. | Planned |
| **Prop / Object Attachment** | Pre-built parent-constraint slots on hand, head, and back joints so props can be parented to the rig with one click. Space-switchable between hands. | Planned |
| **Soft IK** | Smoothly ease into full extension instead of snapping. Node-based falloff curve before the IK chain reaches max length. | Planned |
| **Bendy / Ribbon Limbs** | Ribbon surface or spline-based intermediate deformation between main joints, giving volume-preserving bends at elbows and knees. | Planned |

### Lower Priority / Nice to Have

| Feature | Description | Status |
|---|---|---|
| **Animation Picker** | 2D visual picker panel (HTML or Qt-based) showing a character silhouette with clickable regions to select controls. | Planned |
| **Mirror Pose / Flip Animation** | Mirror selected keyframes or current pose from L↔R. Copy arm/leg pose across sides with axis correction. | Planned |
| **Secondary Dynamics / Jiggle** | Spring/jiggle solver on FK chains (hair, cloth, accessories) with damping and stiffness controls. | Planned |
| **Corrective Blend Shapes** | Pose-space deformation driver: activate corrective blend shape targets based on joint rotation thresholds. | Planned |
| **Volume Preservation** | Squash-and-stretch scaling perpendicular to joint compression. Applied to spine, limbs, and neck. | Planned |
| **Reverse Foot Improvements** | Toe tap, toe wiggle, bank (inner/outer edge roll), and heel swivel attributes. Side-roll pivot locators. | Planned |
| **Control Shape Library** | Swappable control curve shapes per control, selectable at build time or post-build. | Planned |
| **Rig Versioning / Update** | Rebuild the rig without losing animation. Store animation, remove rig, rebuild, reapply. | Planned |
| **Proxy Geo Display** | Low-poly proxy geometry per limb segment that follows the rig, toggleable for fast viewport playback. | Planned |
| **Animation Layer Support** | Additive animation layers on controls so base cycles can have layered adjustments without destructive edits. | Planned |




