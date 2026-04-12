"""Maya material creation from Source 2 texture files.

Exports ALL available textures to PNG, creates file nodes for every one
(even unconnected), builds Maya-native shaders with s&box names, and
cleans up FBX placeholder materials.
"""

import os
import re
import shutil

import maya.cmds as cmds

from . import vrf as _vrf


# Skin variants we skip - only import the default citizen_skin textures
_VARIANT_SKIP = ("_grey_", "_old_", "_young_")


# -- public entry point ------------------------------------------------


def process_material(vrf_exe, vmat_c_path, content_root, texture_output,
                     fbx_mat_name):
    """Convert ALL textures for a material and create a Maya shader.

    Every .vtex_c that belongs to this material gets exported to PNG
    and loaded as a file node in the scene. Only safe connections are
    made; the rest are left for manual hookup.
    """
    fbx_name  = fbx_mat_name.replace(".vmat", "")
    sbox_name = os.path.splitext(os.path.basename(vmat_c_path))[0]
    mat_dir   = os.path.dirname(vmat_c_path)

    # -- export ALL matching textures ----------------------------------
    tex_map = _export_all_textures(vrf_exe, mat_dir, sbox_name,
                                   fbx_name, texture_output)

    # eyeao references citizen_eyes_trans for opacity (cross-material ref)
    if _classify(sbox_name) == "eyeao":
        _add_cross_ref(vrf_exe, mat_dir, texture_output, tex_map,
                       "citizen_eyes_trans", "eyes_trans")

    if not tex_map:
        print(f"    No textures found for {sbox_name} - skipping")
        return None

    for label, png in sorted(tex_map.items()):
        print(f"    {label}: {os.path.basename(png)}")

    # -- collect geo from FBX placeholders, then delete them -----------
    old_members = _collect_and_remove_fbx_materials(fbx_name)

    # -- create shader + file nodes for every texture ------------------
    mat_type = _classify(sbox_name)
    mat, sg, file_nodes = _create_shader(sbox_name, tex_map, mat_type)

    print(f"    Created {len(file_nodes)} file node(s)")

    # -- assign geometry -----------------------------------------------
    if old_members:
        valid = [m for m in old_members if cmds.objExists(m)]
        if valid:
            cmds.sets(valid, e=True, forceElement=sg)
            print(f"    Assigned {len(valid)} object(s) to {sbox_name}")

    return {
        "name": sbox_name,
        "maya_material": mat,
        "textures": list(tex_map.keys()),
        "file_nodes": file_nodes,
    }


# -- texture export (ALL textures) ------------------------------------


def _export_all_textures(vrf_exe, mat_dir, sbox_name, fbx_name, output_dir):
    """Export every .vtex_c belonging to this material.

    Returns dict of human-readable label -> PNG path.
    """
    if not os.path.isdir(mat_dir):
        return {}

    # Build prefix list to match
    prefixes = []
    for p in (sbox_name.lower(), fbx_name.lower(),
              sbox_name.lower().rstrip("0123456789")):
        if p and p not in prefixes:
            prefixes.append(p)

    tex_map = {}
    for fn in sorted(os.listdir(mat_dir)):
        fn_lower = fn.lower()

        if fn_lower.endswith(".vtex_c"):
            # Compiled textures — export via VRF
            if not any(fn_lower.startswith(p) for p in prefixes):
                continue
            if any(v in fn_lower for v in _VARIANT_SKIP):
                continue

            png = _export_texture(vrf_exe, os.path.join(mat_dir, fn),
                                  output_dir)
            if png:
                label = _human_label(fn, sbox_name)
                tex_map[label] = png

        elif (fn_lower.endswith(".png")
              and not fn_lower.endswith(".generated.png")):
            # Raw PNG source textures (shipped alongside vtex_c)
            if not any(fn_lower.startswith(p) for p in prefixes):
                continue
            if any(v in fn_lower for v in _VARIANT_SKIP):
                continue
            src = os.path.join(mat_dir, fn)
            dest = os.path.join(output_dir, fn)
            if not os.path.isfile(dest):
                os.makedirs(output_dir, exist_ok=True)
                shutil.copy2(src, dest)
            label = _label_from_png(fn, sbox_name)
            if label:
                tex_map[label] = dest

    return tex_map


def _human_label(vtex_filename, sbox_name):
    """Derive a short descriptive label from a vtex_c filename.

    e.g. 'citizen_skin_color_png_de459613.generated.vtex_c' -> 'color'
         'citizen_eyes_advanced_iris_mask_psd_...'            -> 'iris_mask'
    """
    base = vtex_filename.lower()
    # Strip hash suffix + extensions
    base = re.sub(r'_[0-9a-f]{6,}\.generated\.vtex_c$', '', base)
    # Strip material prefix
    for prefix in (sbox_name.lower(), sbox_name.lower().rstrip("0123456789")):
        if base.startswith(prefix + "_vmat_g_"):
            base = base[len(prefix) + len("_vmat_g_"):]
            break
        elif base.startswith(prefix + "_"):
            base = base[len(prefix) + 1:]
            break

    # Clean up remaining artifacts
    base = base.rstrip("_").replace("_png", "").replace("_psd", "")
    base = base.replace("_vmat_g_", "")
    return base or "unknown"


def _label_from_png(png_filename, sbox_name):
    """Derive label from a raw PNG filename (non-vtex_c source textures)."""
    base = os.path.splitext(png_filename.lower())[0]
    for prefix in (sbox_name.lower(), sbox_name.lower().rstrip("0123456789")):
        if base.startswith(prefix + "_"):
            base = base[len(prefix) + 1:]
            break
    return base or ""


def _add_cross_ref(vrf_exe, mat_dir, output_dir, tex_map, file_prefix,
                   label):
    """Find and export a texture from a different material's prefix."""
    for fn in sorted(os.listdir(mat_dir)):
        fn_lower = fn.lower()
        if not fn_lower.startswith(file_prefix.lower()):
            continue
        if fn_lower.endswith(".vtex_c"):
            png = _export_texture(vrf_exe, os.path.join(mat_dir, fn),
                                  output_dir)
            if png:
                tex_map[label] = png
                return
        elif fn_lower.endswith(".png") and not fn_lower.endswith(".generated.png"):
            dest = os.path.join(output_dir, fn)
            if not os.path.isfile(dest):
                os.makedirs(output_dir, exist_ok=True)
                shutil.copy2(os.path.join(mat_dir, fn), dest)
            tex_map[label] = dest
            return


def _export_texture(vrf_exe, vtex_c_path, output_dir):
    """Convert a .vtex_c to PNG via VRF CLI."""
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(vtex_c_path))[0]
    dest = os.path.join(output_dir, base + ".png")

    if os.path.isfile(dest):
        return dest

    try:
        result = _vrf.export_texture(vrf_exe, vtex_c_path, output_dir)
    except Exception as exc:
        print(f"      VRF error: {exc}")
        return None

    if result and os.path.isfile(result):
        if os.path.normpath(result) != os.path.normpath(dest):
            shutil.move(result, dest)
        return dest

    return dest if os.path.isfile(dest) else None


def export_remaining_textures(vrf_exe, mat_dir, texture_output,
                             already_exported):
    """Export any .vtex_c not already handled and create orphan file nodes.

    Returns list of (label, file_node) for textures loaded but not
    connected to any material.
    """
    if not os.path.isdir(mat_dir):
        return []

    exported_bases = set()
    for png in already_exported:
        exported_bases.add(os.path.splitext(os.path.basename(png))[0].lower())

    orphans = []
    for fn in sorted(os.listdir(mat_dir)):
        fn_lower = fn.lower()

        if fn_lower.endswith(".vtex_c"):
            if any(v in fn_lower for v in _VARIANT_SKIP):
                continue
            base = os.path.splitext(fn)[0].lower()
            if base in exported_bases:
                continue
            png = _export_texture(vrf_exe, os.path.join(mat_dir, fn),
                                  texture_output)
            if png:
                label = re.sub(r'_[0-9a-f]{6,}\.generated$', '',
                               os.path.splitext(os.path.basename(png))[0])
                node = _file_node(label, png)
                orphans.append((label, node))
                print(f"    Orphan texture: {label}")

        elif (fn_lower.endswith(".png")
              and not fn_lower.endswith(".generated.png")):
            if any(v in fn_lower for v in _VARIANT_SKIP):
                continue
            base = os.path.splitext(fn)[0].lower()
            if base in exported_bases:
                continue
            src = os.path.join(mat_dir, fn)
            dest = os.path.join(texture_output, fn)
            if not os.path.isfile(dest):
                os.makedirs(texture_output, exist_ok=True)
                shutil.copy2(src, dest)
            label = os.path.splitext(fn)[0]
            node = _file_node(label, dest)
            orphans.append((label, node))
            print(f"    Orphan texture (PNG): {label}")

    return orphans


# -- FBX placeholder cleanup ------------------------------------------


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

    if all_members:
        valid = [m for m in all_members if cmds.objExists(m)]
        if valid:
            cmds.sets(valid, e=True, forceElement="initialShadingGroup")

    for node in sgs_to_delete + mats_to_delete:
        if cmds.objExists(node):
            cmds.delete(node)

    print(f"    Cleaned up {len(mats_to_delete)} FBX placeholder(s)")
    return all_members


# -- shader creation ---------------------------------------------------


def _classify(name):
    n = name.lower()
    if "eyeao" in n:
        return "eyeao"
    if "eye" in n:
        return "eye"
    if "skin" in n:
        return "skin"
    return "generic"


def _create_shader(name, tex_map, mat_type):
    """Create material, file nodes for ALL textures, connect safe ones."""
    if _arnold_loaded():
        builders = {
            "skin":    _make_skin,
            "eye":     _make_eye,
            "eyeao":   _make_eyeao,
            "generic": _make_generic,
        }
        return builders[mat_type](name, tex_map)
    return _make_lambert(name, tex_map)


# -- skin shader -------------------------------------------------------


def _make_skin(name, tex_map):
    mat, sg = _make_base_ai(name)
    file_nodes = {}

    # Create file nodes for ALL textures
    for label, png in tex_map.items():
        raw = label not in ("color",)
        fn = _file_node(f"{name}_{label}", png, raw=raw)
        file_nodes[label] = fn

    # Connect only safe channels
    if "color" in file_nodes:
        cmds.connectAttr(f"{file_nodes['color']}.outColor",
                         f"{mat}.baseColor")

    if "normal" in file_nodes:
        _connect_normal(name, mat, file_nodes["normal"])
        # Normal map alpha carries packed roughness data
        cmds.connectAttr(f"{file_nodes['normal']}.outAlpha",
                         f"{mat}.specularRoughness")

    # Translucency mask drives subsurface scattering intensity
    if "trans" in file_nodes:
        cmds.connectAttr(f"{file_nodes['trans']}.outColorR",
                         f"{mat}.subsurface")
    else:
        cmds.setAttr(f"{mat}.subsurface", 0.15)
    cmds.setAttr(f"{mat}.subsurfaceColor", 0.9, 0.55, 0.4, type="double3")
    cmds.setAttr(f"{mat}.subsurfaceRadius", 1.0, 0.4, 0.25, type="double3")

    return mat, sg, file_nodes


# -- eye shader (citizen_eyes_advanced) --------------------------------


def _make_eye(name, tex_map):
    mat, sg = _make_base_ai(name)
    file_nodes = {}

    for label, png in tex_map.items():
        raw = label not in ("color",)
        fn = _file_node(f"{name}_{label}", png, raw=raw)
        file_nodes[label] = fn

    # Connect safe channels - NO opacity (eyes must be opaque)
    if "color" in file_nodes:
        cmds.connectAttr(f"{file_nodes['color']}.outColor",
                         f"{mat}.baseColor")

    if "normal" in file_nodes:
        _connect_normal(name, mat, file_nodes["normal"])

    # Wet glossy cornea
    cmds.setAttr(f"{mat}.specular", 1.0)
    cmds.setAttr(f"{mat}.specularRoughness", 0.05)
    cmds.setAttr(f"{mat}.specularIOR", 1.45)
    cmds.setAttr(f"{mat}.coat", 1.0)
    cmds.setAttr(f"{mat}.coatRoughness", 0.0)

    return mat, sg, file_nodes


# -- eye-AO overlay shader --------------------------------------------


def _make_eyeao(name, tex_map):
    """Eye AO overlay — eyes_trans drives opacity, AO darkens the base."""
    mat, sg = _make_base_ai(name)
    file_nodes = {}

    for label, png in tex_map.items():
        fn = _file_node(f"{name}_{label}", png, raw=True)
        file_nodes[label] = fn

    # Dark overlay: AO tints the base, no specular
    cmds.setAttr(f"{mat}.specular", 0)
    cmds.setAttr(f"{mat}.metalness", 0)
    cmds.setAttr(f"{mat}.transmission", 0.3)
    cmds.setAttr(f"{mat}.thinWalled", 1)

    # AO texture drives base color (dark = shadow)
    if "tambientocclusion" in file_nodes:
        cmds.connectAttr(f"{file_nodes['tambientocclusion']}.outColor",
                         f"{mat}.baseColor")
    else:
        cmds.setAttr(f"{mat}.baseColor", 0, 0, 0, type="double3")

    # citizen_eyes_trans is the actual opacity map
    if "eyes_trans" in file_nodes:
        cmds.connectAttr(f"{file_nodes['eyes_trans']}.outColor",
                         f"{mat}.opacity")

    if "tnormal" in file_nodes:
        _connect_normal(name, mat, file_nodes["tnormal"])

    return mat, sg, file_nodes


# -- generic fallback --------------------------------------------------


def _make_generic(name, tex_map):
    mat, sg = _make_base_ai(name)
    file_nodes = {}

    for label, png in tex_map.items():
        raw = label not in ("color",)
        fn = _file_node(f"{name}_{label}", png, raw=raw)
        file_nodes[label] = fn

    if "color" in file_nodes:
        cmds.connectAttr(f"{file_nodes['color']}.outColor",
                         f"{mat}.baseColor")

    if "normal" in file_nodes:
        _connect_normal(name, mat, file_nodes["normal"])

    return mat, sg, file_nodes


def _make_lambert(name, tex_map):
    """Fallback when Arnold is not loaded."""
    mat = cmds.shadingNode("lambert", asShader=True, name=name)
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                   name=f"{name}SG")
    cmds.connectAttr(f"{mat}.outColor", f"{sg}.surfaceShader")

    file_nodes = {}
    for label, png in tex_map.items():
        fn = _file_node(f"{name}_{label}", png)
        file_nodes[label] = fn

    if "color" in file_nodes:
        cmds.connectAttr(f"{file_nodes['color']}.outColor", f"{mat}.color")

    return mat, sg, file_nodes


# -- shared helpers ----------------------------------------------------


def _make_base_ai(name):
    mat = cmds.shadingNode("aiStandardSurface", asShader=True, name=name)
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                   name=f"{name}SG")
    cmds.connectAttr(f"{mat}.outColor", f"{sg}.surfaceShader")
    return mat, sg


def _connect_normal(prefix, mat, file_node):
    """Connect an existing file node to mat.normalCamera via aiNormalMap."""
    bump = cmds.shadingNode("aiNormalMap", asUtility=True,
                            name=f"{prefix}_normalMap")
    cmds.connectAttr(f"{file_node}.outColor", f"{bump}.input")
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
