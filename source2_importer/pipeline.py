"""Source 2 model import pipeline.

Orchestrates: parse vmdl -> import FBX -> convert textures ->
create materials -> assign.
"""

import os

import maya.cmds as cmds

from . import kv3
from . import vrf as _vrf
from . import materials as _mat


# ── vmdl parsing ──────────────────────────────────────────────────


def find_content_root(vmdl_path):
    """Determine the content root by looking for 'models/' in the path."""
    norm = os.path.normpath(vmdl_path)
    parts = norm.split(os.sep)
    for i, p in enumerate(parts):
        if p.lower() == "models":
            return os.sep.join(parts[:i])
    return os.path.dirname(vmdl_path)


def parse_vmdl(vmdl_path):
    """Parse a .vmdl (KV3 text) and inline prefab references.

    Returns::

        {
            'meshes':       [{'filename', 'name', 'import_filter', ...}, ...],
            'materials':    [{'from', 'to'}, ...],
            'scale':        float,
            'content_root': str,
            'vmdl_path':    str,
        }
    """
    content_root = find_content_root(vmdl_path)

    with open(vmdl_path, "r", encoding="utf-8") as f:
        data = kv3.parse(f.read())

    result = {
        "meshes": [],
        "materials": [],
        "scale": 1.0,
        "content_root": content_root,
        "vmdl_path": vmdl_path,
    }

    root_node = data.get("rootNode", data)
    _walk_children(root_node.get("children", []), content_root, result)
    return result


def _walk_children(children, content_root, result):
    for child in children:
        cls = child.get("_class", "")

        # ── resolve prefab ────────────────────────────────────
        if cls == "Prefab":
            target = child.get("target_file", "")
            if target:
                fp = os.path.join(content_root, target.replace("/", os.sep))
                if os.path.isfile(fp):
                    with open(fp, "r", encoding="utf-8") as f:
                        pdata = kv3.parse(f.read())
                    proot = pdata.get("rootNode", pdata)
                    _walk_children(proot.get("children", []),
                                   content_root, result)
            continue

        # ── mesh entries ──────────────────────────────────────
        if cls == "RenderMeshFile":
            info = {
                "filename": child.get("filename", ""),
                "name": child.get("name", ""),
                "import_scale": child.get("import_scale", 1.0),
                "import_filter": None,
            }
            filt = child.get("import_filter")
            if isinstance(filt, dict):
                info["import_filter"] = {
                    "exclude_by_default": filt.get("exclude_by_default", False),
                    "exception_list": filt.get("exception_list", []),
                }
            result["meshes"].append(info)

        # ── material remaps ───────────────────────────────────
        if cls == "DefaultMaterialGroup":
            for remap in child.get("remaps", []):
                if isinstance(remap, dict):
                    result["materials"].append({
                        "from": remap.get("from", ""),
                        "to": remap.get("to", ""),
                    })

        # ── scale modifier ────────────────────────────────────
        if cls == "ModelModifier_ScaleAndMirror":
            result["scale"] = child.get("scale", 1.0)

        # ── recurse ──────────────────────────────────────────
        sub = child.get("children")
        if sub:
            _walk_children(sub, content_root, result)


# ── path helpers ──────────────────────────────────────────────────


def _resolve_mesh(filename, content_root):
    return os.path.join(content_root, filename.replace("/", os.sep))


def _resolve_material(vmat_ref, content_root):
    ref = vmat_ref if vmat_ref.endswith("_c") else vmat_ref + "_c"
    return os.path.join(content_root, ref.replace("/", os.sep))


def _find_ref_fbx(fbx_path):
    """Look for a *_REF.fbx next to the given FBX (Maya-compatible export)."""
    d = os.path.dirname(fbx_path)
    base = os.path.splitext(os.path.basename(fbx_path))[0]
    ref = os.path.join(d, f"{base}_REF.fbx")
    if os.path.isfile(ref):
        return ref
    # Also search for any _REF.fbx in the same folder
    for fn in os.listdir(d):
        if fn.lower().endswith("_ref.fbx"):
            return os.path.join(d, fn)
    return None


# ── hierarchy organization ───────────────────────────────────────


def _organize_hierarchy(new_nodes, model_name):
    """Group imported nodes under a clean hierarchy.

    Creates::

        <model_name>_GRP
        ├── <model_name>_GEO_GRP   — mesh transforms
        └── <model_name>_SKEL_GRP  — skeleton root(s)

    Nodes already parented under the skeleton (skinned meshes via
    intermediate groups) stay where they are.
    """
    top = cmds.group(empty=True, name=f"{model_name}_GRP")
    geo_grp = cmds.group(empty=True, name=f"{model_name}_GEO_GRP",
                         parent=top)
    skel_grp = cmds.group(empty=True, name=f"{model_name}_SKEL_GRP",
                          parent=top)

    # Identify skeleton roots: joints at world level (no joint parent)
    skel_roots = []
    for node in new_nodes:
        if not cmds.objExists(node):
            continue
        if cmds.nodeType(node) != "joint":
            continue
        par = cmds.listRelatives(node, parent=True)
        if par is None or (cmds.objExists(par[0])
                           and cmds.nodeType(par[0]) != "joint"):
            skel_roots.append(node)

    # Parent skeleton roots
    for root in skel_roots:
        if cmds.objExists(root):
            par = cmds.listRelatives(root, parent=True)
            if par is None:
                cmds.parent(root, skel_grp)

    # Identify top-level mesh transforms (transforms with mesh shapes)
    mesh_tops = []
    for node in new_nodes:
        if not cmds.objExists(node):
            continue
        if cmds.nodeType(node) != "transform":
            continue
        shapes = cmds.listRelatives(node, shapes=True, type="mesh") or []
        if not shapes:
            continue
        # Only grab truly top-level (world-parented) mesh transforms
        par = cmds.listRelatives(node, parent=True)
        if par is None:
            mesh_tops.append(node)

    for mesh in mesh_tops:
        if cmds.objExists(mesh):
            cmds.parent(mesh, geo_grp)

    # Catch any remaining world-level transforms that were imported
    for node in new_nodes:
        if not cmds.objExists(node):
            continue
        if cmds.nodeType(node) != "transform":
            continue
        par = cmds.listRelatives(node, parent=True)
        if par is not None:
            continue
        # Still at world level — put in top group
        cmds.parent(node, top)


# ── main entry point ─────────────────────────────────────────────


def import_source2_model(vmdl_path, vrf_exe=None, texture_output=None,
                         progress_fn=None):
    """Full import pipeline.

    Args:
        vmdl_path:      Path to a .vmdl file.
        vrf_exe:        Path to Decompiler.exe (None = FBX only, no textures).
        texture_output: Folder where exported PNGs go (default: sourceimages/).
        progress_fn:    Optional callable(str) for status updates.

    Returns:
        dict with 'fbx_path', 'new_nodes', 'materials_created'.
    """
    def _log(msg):
        print(msg)
        if progress_fn:
            progress_fn(msg)

    _log(f"--- Source 2 Import: {os.path.basename(vmdl_path)} ---")

    # 1 ── parse vmdl ──────────────────────────────────────────────
    _log("Parsing .vmdl ...")
    model = parse_vmdl(vmdl_path)
    content_root = model["content_root"]

    # 2 ── pick FBX to import ─────────────────────────────────────
    meshes = model["meshes"]
    if not meshes:
        raise RuntimeError("No mesh entries found in .vmdl")

    # Check if any LOD0 mesh references a non-FBX file (.dmx etc.)
    # If so, a _REF.fbx is needed for the complete character.
    has_non_fbx_lod0 = any(
        "lod0" in m.get("name", "").lower()
        and not m["filename"].lower().endswith(".fbx")
        for m in meshes
    )

    # Collect unique FBX filenames that have LOD0 entries (skip .dmx)
    seen = set()
    lod0_candidates = []
    any_fbx = []
    for m in meshes:
        fn = m["filename"]
        if fn in seen or not fn.lower().endswith(".fbx"):
            seen.add(fn)
            continue
        seen.add(fn)
        any_fbx.append(fn)
        if "lod0" in m.get("name", "").lower():
            lod0_candidates.append(fn)

    lod0_fbx = (lod0_candidates[0] if lod0_candidates
                else any_fbx[0] if any_fbx else None)
    if lod0_fbx is None:
        raise RuntimeError("No FBX mesh entries found in .vmdl")

    fbx_path = _resolve_mesh(lod0_fbx, content_root)
    ref_path = _find_ref_fbx(fbx_path)

    # Prefer _REF.fbx when parts of the model are non-FBX (.dmx),
    # because _REF.fbx is a single complete Maya-friendly export.
    if has_non_fbx_lod0 and ref_path:
        _log("Some LOD0 meshes are .dmx — using _REF.fbx for "
             "complete character")
        fbx_path = ref_path
    elif not os.path.isfile(fbx_path):
        if ref_path:
            fbx_path = ref_path
        else:
            raise RuntimeError(f"FBX not found: {fbx_path}")

    # 3 ── import FBX ─────────────────────────────────────────────
    _log(f"Importing FBX: {os.path.basename(fbx_path)}")
    before = set(cmds.ls(dag=True))
    try:
        cmds.file(fbx_path, i=True, type="FBX", ignoreVersion=True,
                  mergeNamespacesOnClash=True, rpr="", pr=True)
    except RuntimeError:
        # FBX version may be too new — try _REF.fbx fallback
        if ref_path and ref_path != fbx_path:
            _log(f"FBX import failed, trying fallback: "
                 f"{os.path.basename(ref_path)}")
            cmds.file(ref_path, i=True, type="FBX", ignoreVersion=True,
                      mergeNamespacesOnClash=True, rpr="", pr=True)
            fbx_path = ref_path
        else:
            raise
    after = set(cmds.ls(dag=True))
    new_nodes = sorted(after - before)

    # ── organize into groups ─────────────────────────────────────
    mdl_name = os.path.splitext(os.path.basename(vmdl_path))[0]
    _organize_hierarchy(new_nodes, mdl_name)

    result = {
        "fbx_path": fbx_path,
        "new_nodes": new_nodes,
        "materials_created": [],
    }

    # 4 ── textures & materials (requires VRF) ────────────────────
    if not vrf_exe or not os.path.isfile(vrf_exe):
        _log("VRF not available — skipping textures/materials.")
        _log(f"Done. {len(new_nodes)} nodes imported (mesh only).")
        return result

    if texture_output is None:
        proj = cmds.workspace(q=True, rd=True)
        mdl = os.path.splitext(os.path.basename(vmdl_path))[0]
        texture_output = os.path.join(proj, "sourceimages", mdl)
    os.makedirs(texture_output, exist_ok=True)

    for remap in model["materials"]:
        mat_from = remap["from"]
        mat_to   = remap["to"]
        vmat_c   = _resolve_material(mat_to, content_root)

        if not os.path.isfile(vmat_c):
            _log(f"  Material not found: {os.path.basename(vmat_c)}")
            continue

        _log(f"  Processing: {mat_from} -> {os.path.basename(vmat_c)}")
        try:
            info = _mat.process_material(
                vrf_exe, vmat_c, content_root, texture_output, mat_from
            )
            if info:
                result["materials_created"].append(info)
        except Exception as exc:
            _log(f"  Warning — material failed: {exc}")

    # 5 -- export any remaining textures as orphan file nodes ----------
    all_exported = []
    for info in result["materials_created"]:
        for png in (info.get("textures") or []):
            if isinstance(png, str) and os.path.isfile(png):
                all_exported.append(png)
        for fn in (info.get("file_nodes") or {}).values():
            png = cmds.getAttr(f"{fn}.fileTextureName") if cmds.objExists(fn) else None
            if png:
                all_exported.append(png)

    # Find the skin/ subfolder where textures live
    first_vmat = None
    for remap in model["materials"]:
        path = _resolve_material(remap["to"], content_root)
        if os.path.isfile(path):
            first_vmat = path
            break
    if first_vmat:
        mat_dir = os.path.dirname(first_vmat)
        orphans = _mat.export_remaining_textures(
            vrf_exe, mat_dir, texture_output, all_exported
        )
        if orphans:
            _log(f"  Loaded {len(orphans)} additional texture(s) as orphan file nodes")

    _log(f"Done. {len(new_nodes)} nodes, "
         f"{len(result['materials_created'])} materials.")
    return result
