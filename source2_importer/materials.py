"""Maya material creation from Source 2 texture files.

Discovers all available texture channels per material, creates
Maya-native shaders with s&box-matching names and settings, cleans up
FBX placeholder materials.
"""

import os
import re
import shutil

import maya.cmds as cmds

from . import vrf as _vrf


# ── texture slot definitions ──────────────────────────────────────
# (slot_name, match_patterns, exclude_patterns)
_TEXTURE_SLOTS = [
    ("color",       ["_color_", "_tcolor_"],
                    ["_grey_", "_old_", "_young_"]),
    ("normal",      ["_normal_", "_tnormal_"],
                    ["_iris_normal_", "_bentnormal_"]),
    ("ao",          ["_ao_", "_tambientocclusion_", "_tocclusion_"],
                    ["_grey_", "_old_", "_young_"]),
    ("roughness",   ["_roughness_"],          []),
    ("metalness",   ["_metalness_"],          []),
    ("emission",    ["_selfillum_", "_tselfillummask_"],  []),
    ("iris_mask",   ["_iris_mask_"],          []),
    ("iris_normal", ["_iris_normal_"],        []),
    ("transparency", ["_trans_"],             []),
]


# ── public entry point ────────────────────────────────────────────


def process_material(vrf_exe, vmat_c_path, content_root, texture_output,
                     fbx_mat_name):
    """Convert textures and create a Maya material for a .vmat_c.

    Uses the s&box material name from the vmat_c filename. Cleans up
    the FBX placeholder material after reassigning geometry.
    """
    fbx_name  = fbx_mat_name.replace(".vmat", "")
    sbox_name = os.path.splitext(os.path.basename(vmat_c_path))[0]
    mat_dir   = os.path.dirname(vmat_c_path)

    # ── discover all available textures ──────────────────────────
    textures = _discover_textures(vrf_exe, mat_dir, sbox_name,
                                  fbx_name, texture_output)
    if not textures:
        print(f"    No textures found for {sbox_name} — skipping")
        return None

    for slot, png in textures.items():
        print(f"    {slot}: {os.path.basename(png)}")

    # ── collect geo from FBX placeholders, then remove them ──────
    old_members = _collect_and_remove_fbx_materials(fbx_name)

    # ── create shader with s&box name ────────────────────────────
    mat_type = _classify(sbox_name)
    mat, sg = _create_shader(sbox_name, textures, mat_type)

    # ── assign geometry to new shader ────────────────────────────
    if old_members:
        valid = [m for m in old_members if cmds.objExists(m)]
        if valid:
            cmds.sets(valid, e=True, forceElement=sg)
            print(f"    Assigned {len(valid)} object(s) to {sbox_name}")

    return {
        "name": sbox_name,
        "maya_material": mat,
        "textures": list(textures.keys()),
    }


# ── texture discovery ─────────────────────────────────────────────


def _discover_textures(vrf_exe, mat_dir, sbox_name, fbx_name, output_dir):
    """Find and convert all available texture channels.

    Tries multiple prefix candidates to account for naming variations
    (citizen_skin01 vs citizen_skin_, citizen_eyes vs citizen_eyes_advanced_).
    """
    if not os.path.isdir(mat_dir):
        return {}

    # Prefix candidates: sbox name, fbx name, digits-stripped sbox name
    prefixes = [sbox_name.lower()]
    fbx_lower = fbx_name.lower()
    if fbx_lower not in prefixes:
        prefixes.append(fbx_lower)
    stripped = sbox_name.lower().rstrip("0123456789")
    if stripped not in prefixes and stripped != sbox_name.lower():
        prefixes.append(stripped)

    all_vtex = sorted(fn for fn in os.listdir(mat_dir)
                      if fn.endswith(".vtex_c"))

    textures = {}  # slot_name -> png_path
    for slot_name, patterns, excludes in _TEXTURE_SLOTS:
        for prefix in prefixes:
            match = _find_texture(all_vtex, prefix, patterns, excludes)
            if match:
                png = _export_texture(vrf_exe,
                                      os.path.join(mat_dir, match),
                                      output_dir)
                if png:
                    textures[slot_name] = png
                break

    return textures


def _find_texture(vtex_files, prefix, patterns, excludes):
    """Return first .vtex_c matching prefix + any pattern, excluding rejects."""
    for fn in vtex_files:
        fn_lower = fn.lower()
        if not fn_lower.startswith(prefix):
            continue
        if not any(p in fn_lower for p in patterns):
            continue
        if any(e in fn_lower for e in excludes):
            continue
        return fn
    return None


def _export_texture(vrf_exe, vtex_c_path, output_dir):
    """Convert a .vtex_c to PNG via VRF CLI."""
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(vtex_c_path))[0]
    dest = os.path.join(output_dir, base + ".png")

    # Already converted?
    if os.path.isfile(dest):
        return dest

    try:
        result = _vrf.export_texture(vrf_exe, vtex_c_path, output_dir)
    except Exception as exc:
        print(f"      VRF error: {exc}")
        return None

    if result and os.path.isfile(result):
        # VRF may have written next to input — move to output_dir
        if os.path.normpath(result) != os.path.normpath(dest):
            shutil.move(result, dest)
        return dest

    return dest if os.path.isfile(dest) else None


# ── FBX placeholder cleanup ──────────────────────────────────────


def _matches_fbx_name(mat_name, fbx_name):
    """True if mat_name is fbx_name with optional numeric suffix."""
    return bool(re.match(
        r'^' + re.escape(fbx_name) + r'\d*$', mat_name, re.IGNORECASE
    ))


_PROTECTED = {"lambert1", "standardSurface1", "particleCloud1"}


def _collect_and_remove_fbx_materials(fbx_name):
    """Collect mesh members from FBX placeholder materials, delete them."""
    all_members = []
    sgs_to_delete = []
    mats_to_delete = []

    for mat in cmds.ls(materials=True):
        if mat in _PROTECTED:
            continue
        if not _matches_fbx_name(mat, fbx_name):
            continue

        for sg in (cmds.listConnections(f"{mat}.outColor",
                                        type="shadingEngine") or []):
            if sg == "initialShadingGroup":
                continue
            members = cmds.sets(sg, q=True) or []
            all_members.extend(members)
            sgs_to_delete.append(sg)
        mats_to_delete.append(mat)

    # Park geometry on initialShadingGroup first
    if all_members:
        valid = [m for m in all_members if cmds.objExists(m)]
        if valid:
            cmds.sets(valid, e=True, forceElement="initialShadingGroup")

    # Delete SGs then materials
    for node in sgs_to_delete + mats_to_delete:
        if cmds.objExists(node):
            cmds.delete(node)

    print(f"    Cleaned up {len(mats_to_delete)} FBX placeholder(s)")
    return all_members


# ── shader creation (dispatch) ────────────────────────────────────


def _classify(name):
    n = name.lower()
    if "eyeao" in n:
        return "eyeao"
    if "eye" in n:
        return "eye"
    if "skin" in n:
        return "skin"
    return "generic"


def _create_shader(name, textures, mat_type):
    if _arnold_loaded():
        builders = {
            "skin":    _make_skin,
            "eye":     _make_eye,
            "eyeao":   _make_eyeao,
            "generic": _make_generic,
        }
        return builders[mat_type](name, textures)
    return _make_lambert(name, textures)


# ── skin shader ───────────────────────────────────────────────────


def _make_skin(name, textures):
    mat, sg = _make_base_ai(name)

    if "color" in textures:
        ftex = _file_node(f"{name}_color", textures["color"])
        cmds.connectAttr(f"{ftex}.outColor", f"{mat}.baseColor")

    if "normal" in textures:
        _connect_normal(name, mat, textures["normal"])

    if "ao" in textures:
        ao = _file_node(f"{name}_ao", textures["ao"], raw=True)
        cmds.connectAttr(f"{ao}.outColorR", f"{mat}.base")

    if "roughness" in textures:
        rtex = _file_node(f"{name}_rough", textures["roughness"], raw=True)
        cmds.connectAttr(f"{rtex}.outColorR", f"{mat}.specularRoughness")
    else:
        cmds.setAttr(f"{mat}.specularRoughness", 0.45)

    if "emission" in textures:
        etex = _file_node(f"{name}_emit", textures["emission"])
        cmds.setAttr(f"{mat}.emission", 1.0)
        cmds.connectAttr(f"{etex}.outColor", f"{mat}.emissionColor")

    # Subsurface scattering for skin
    cmds.setAttr(f"{mat}.subsurface", 0.15)
    cmds.setAttr(f"{mat}.subsurfaceColor", 0.9, 0.55, 0.4, type="double3")
    cmds.setAttr(f"{mat}.subsurfaceRadius", 1.0, 0.4, 0.25, type="double3")

    return mat, sg


# ── eye shader ────────────────────────────────────────────────────


def _make_eye(name, textures):
    mat, sg = _make_base_ai(name)

    if "color" in textures:
        ftex = _file_node(f"{name}_color", textures["color"])
        cmds.connectAttr(f"{ftex}.outColor", f"{mat}.baseColor")

    if "normal" in textures:
        _connect_normal(name, mat, textures["normal"])

    if "ao" in textures:
        ao = _file_node(f"{name}_ao", textures["ao"], raw=True)
        cmds.connectAttr(f"{ao}.outColorR", f"{mat}.base")

    if "transparency" in textures:
        ttex = _file_node(f"{name}_trans", textures["transparency"], raw=True)
        cmds.connectAttr(f"{ttex}.outColor", f"{mat}.opacity")

    # Wet glossy cornea
    cmds.setAttr(f"{mat}.specular", 1.0)
    cmds.setAttr(f"{mat}.specularRoughness", 0.05)
    cmds.setAttr(f"{mat}.specularIOR", 1.45)
    cmds.setAttr(f"{mat}.coat", 1.0)
    cmds.setAttr(f"{mat}.coatRoughness", 0.0)

    return mat, sg


# ── eye-AO overlay shader ────────────────────────────────────────


def _make_eyeao(name, textures):
    """Transparent darkening overlay — opaque black where AO is dark."""
    mat, sg = _make_base_ai(name)

    # Pure black surface, no specular
    cmds.setAttr(f"{mat}.baseColor", 0, 0, 0, type="double3")
    cmds.setAttr(f"{mat}.specular", 0)

    if "ao" in textures:
        ao = _file_node(f"{name}_ao", textures["ao"], raw=True)
        # opacity = 1 − AO → transparent where lit, opaque where shadowed
        rev = cmds.shadingNode("reverse", asUtility=True,
                               name=f"{name}_reverse")
        cmds.connectAttr(f"{ao}.outColor", f"{rev}.input")
        cmds.connectAttr(f"{rev}.output", f"{mat}.opacity")

    if "normal" in textures:
        _connect_normal(name, mat, textures["normal"])

    return mat, sg


# ── generic / fallback shaders ───────────────────────────────────


def _make_generic(name, textures):
    mat, sg = _make_base_ai(name)

    if "color" in textures:
        ftex = _file_node(f"{name}_color", textures["color"])
        cmds.connectAttr(f"{ftex}.outColor", f"{mat}.baseColor")

    if "normal" in textures:
        _connect_normal(name, mat, textures["normal"])

    if "ao" in textures:
        ao = _file_node(f"{name}_ao", textures["ao"], raw=True)
        cmds.connectAttr(f"{ao}.outColorR", f"{mat}.base")

    if "roughness" in textures:
        rtex = _file_node(f"{name}_rough", textures["roughness"], raw=True)
        cmds.connectAttr(f"{rtex}.outColorR", f"{mat}.specularRoughness")

    if "metalness" in textures:
        mtex = _file_node(f"{name}_metal", textures["metalness"], raw=True)
        cmds.connectAttr(f"{mtex}.outColorR", f"{mat}.metalness")

    if "emission" in textures:
        etex = _file_node(f"{name}_emit", textures["emission"])
        cmds.setAttr(f"{mat}.emission", 1.0)
        cmds.connectAttr(f"{etex}.outColor", f"{mat}.emissionColor")

    return mat, sg


def _make_lambert(name, textures):
    """Fallback when Arnold is not loaded."""
    mat = cmds.shadingNode("lambert", asShader=True, name=name)
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                   name=f"{name}SG")
    cmds.connectAttr(f"{mat}.outColor", f"{sg}.surfaceShader")

    if "color" in textures:
        ftex = _file_node(f"{name}_color", textures["color"])
        cmds.connectAttr(f"{ftex}.outColor", f"{mat}.color")

    return mat, sg


# ── shared helpers ────────────────────────────────────────────────


def _make_base_ai(name):
    """Create an aiStandardSurface + shading group pair."""
    mat = cmds.shadingNode("aiStandardSurface", asShader=True, name=name)
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                   name=f"{name}SG")
    cmds.connectAttr(f"{mat}.outColor", f"{sg}.surfaceShader")
    return mat, sg


def _connect_normal(prefix, mat, png_path):
    """Connect a normal-map PNG to mat.normalCamera via aiNormalMap."""
    ntex = _file_node(f"{prefix}_normal", png_path, raw=True)
    bump = cmds.shadingNode("aiNormalMap", asUtility=True,
                            name=f"{prefix}_normalMap")
    cmds.connectAttr(f"{ntex}.outColor", f"{bump}.input")
    cmds.connectAttr(f"{bump}.outValue", f"{mat}.normalCamera")


def _file_node(name, png_path, raw=False):
    """Create a file + place2dTexture node pair."""
    ftex = cmds.shadingNode("file", asTexture=True, name=name)
    p2d = cmds.shadingNode("place2dTexture", asUtility=True)
    _connect_p2d(p2d, ftex)
    cmds.setAttr(f"{ftex}.fileTextureName", png_path, type="string")
    if raw:
        cmds.setAttr(f"{ftex}.colorSpace", "Raw", type="string")
    return ftex


def _arnold_loaded():
    try:
        return (cmds.pluginInfo("mtoa", q=True, registered=True)
                and cmds.pluginInfo("mtoa", q=True, loaded=True))
    except Exception:
        return False


def _connect_p2d(p2d, ftex):
    pairs = [
        ("coverage", "coverage"), ("translateFrame", "translateFrame"),
        ("rotateFrame", "rotateFrame"), ("mirrorU", "mirrorU"),
        ("mirrorV", "mirrorV"), ("stagger", "stagger"),
        ("wrapU", "wrapU"), ("wrapV", "wrapV"),
        ("repeatUV", "repeatUV"), ("offset", "offset"),
        ("rotateUV", "rotateUV"), ("noiseUV", "noiseUV"),
        ("vertexUvOne", "vertexUvOne"), ("vertexUvTwo", "vertexUvTwo"),
        ("vertexUvThree", "vertexUvThree"),
        ("vertexCameraOne", "vertexCameraOne"),
        ("outUV", "uv"), ("outUvFilterSize", "uvFilterSize"),
    ]
    for src, dst in pairs:
        cmds.connectAttr(f"{p2d}.{src}", f"{ftex}.{dst}", force=True)
