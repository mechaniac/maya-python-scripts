"""Pure-Python glTF 2.0 / GLB importer for Maya.

No compiled plugin required.  Builds Maya geometry directly with the
``maya.api.OpenMaya`` API.

Currently supported in this milestone:

* ``.gltf`` (with external ``.bin`` and embedded ``data:`` URIs)
* ``.glb`` (binary container, JSON + BIN chunks)
* Node hierarchy (translate / rotate / scale, matrices)
* Triangle meshes (positions, normals, UVs, vertex colors)
* Per-primitive material assignment (Lambert + optional file texture
  from ``baseColorTexture`` / ``baseColorFactor``)

Not implemented yet (silently ignored):

* Skinning / skinClusters
* Morph targets / blend shapes
* Animation channels
* PBR roughness/metallic/normal/emissive textures
* KHR_* extensions (lights, draco, etc.)
* Lines / points / triangle strips / fans

Reference: glTF 2.0 spec
https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
"""

import os
import json
import struct
import base64

import maya.cmds as cmds
import maya.api.OpenMaya as om


# ---------------------------------------------------------------------------
# glTF spec constants
# ---------------------------------------------------------------------------

_GLB_MAGIC      = 0x46546C67  # "glTF"
_GLB_CHUNK_JSON = 0x4E4F534A  # "JSON"
_GLB_CHUNK_BIN  = 0x004E4942  # "BIN\0"

# Component types
_COMP_BYTE   = 5120
_COMP_UBYTE  = 5121
_COMP_SHORT  = 5122
_COMP_USHORT = 5123
_COMP_UINT   = 5125
_COMP_FLOAT  = 5126

_COMP_FORMAT = {
    _COMP_BYTE:   ("b", 1),
    _COMP_UBYTE:  ("B", 1),
    _COMP_SHORT:  ("h", 2),
    _COMP_USHORT: ("H", 2),
    _COMP_UINT:   ("I", 4),
    _COMP_FLOAT:  ("f", 4),
}

_TYPE_COMPONENTS = {
    "SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
    "MAT2": 4, "MAT3": 9, "MAT4": 16,
}

# Primitive modes
_MODE_TRIANGLES      = 4
_MODE_TRIANGLE_STRIP = 5
_MODE_TRIANGLE_FAN   = 6


# ---------------------------------------------------------------------------
# Container loading
# ---------------------------------------------------------------------------

def _load_glb(path):
    """Read a .glb file -> (gltf_json_dict, [buffer_bytes_or_None ...])."""
    with open(path, "rb") as fh:
        header = fh.read(12)
        if len(header) < 12:
            raise IOError("Not a GLB file (header too short): " + path)
        magic, version, total = struct.unpack("<III", header)
        if magic != _GLB_MAGIC:
            raise IOError("Not a GLB file (bad magic): " + path)
        if version != 2:
            raise IOError("Unsupported GLB version: {0}".format(version))

        gltf = None
        bin_chunk = b""
        while fh.tell() < total:
            chunk_hdr = fh.read(8)
            if len(chunk_hdr) < 8:
                break
            chunk_len, chunk_type = struct.unpack("<II", chunk_hdr)
            data = fh.read(chunk_len)
            if chunk_type == _GLB_CHUNK_JSON:
                gltf = json.loads(data.decode("utf-8"))
            elif chunk_type == _GLB_CHUNK_BIN:
                bin_chunk = data

        if gltf is None:
            raise IOError("GLB has no JSON chunk: " + path)

    buffers = []
    for i, buf in enumerate(gltf.get("buffers", [])):
        if i == 0 and "uri" not in buf:
            buffers.append(bin_chunk)
        else:
            buffers.append(_load_uri(buf.get("uri"), os.path.dirname(path)))
    return gltf, buffers


def _load_gltf(path):
    """Read a .gltf JSON file -> (gltf_dict, [buffer_bytes ...])."""
    with open(path, "rb") as fh:
        gltf = json.loads(fh.read().decode("utf-8"))
    basedir = os.path.dirname(path)
    buffers = [_load_uri(buf.get("uri"), basedir)
               for buf in gltf.get("buffers", [])]
    return gltf, buffers


def _load_uri(uri, basedir):
    if uri is None:
        return b""
    if uri.startswith("data:"):
        # data:application/octet-stream;base64,XXXX
        comma = uri.find(",")
        return base64.b64decode(uri[comma + 1:])
    full = os.path.join(basedir, uri)
    with open(full, "rb") as fh:
        return fh.read()


def _load_container(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".glb":
        return _load_glb(path)
    if ext == ".gltf":
        return _load_gltf(path)
    raise IOError("Unknown extension (expected .glb or .gltf): " + path)


# ---------------------------------------------------------------------------
# Accessor decoding
# ---------------------------------------------------------------------------

def _accessor_bytes(gltf, buffers, accessor_idx):
    """Return raw bytes plus stride/count/format info for an accessor."""
    accessor   = gltf["accessors"][accessor_idx]
    comp_type  = accessor["componentType"]
    count      = accessor["count"]
    type_name  = accessor["type"]
    ncomp      = _TYPE_COMPONENTS[type_name]
    fmt_char, comp_size = _COMP_FORMAT[comp_type]
    elem_size  = ncomp * comp_size

    bv_idx = accessor.get("bufferView")
    if bv_idx is None:
        # Sparse-only accessor; treat as zeros.
        return b"\x00" * (elem_size * count), fmt_char, ncomp, count, elem_size

    bv         = gltf["bufferViews"][bv_idx]
    buf_idx    = bv["buffer"]
    bv_off     = bv.get("byteOffset", 0)
    acc_off    = accessor.get("byteOffset", 0)
    stride     = bv.get("byteStride", elem_size)
    start      = bv_off + acc_off

    raw = buffers[buf_idx]
    if stride == elem_size:
        return (raw[start:start + elem_size * count],
                fmt_char, ncomp, count, elem_size)
    # Interleaved -> repack tightly.
    chunks = bytearray()
    for i in range(count):
        s = start + i * stride
        chunks += raw[s:s + elem_size]
    return bytes(chunks), fmt_char, ncomp, count, elem_size


def _read_accessor(gltf, buffers, accessor_idx):
    """Decode an accessor into a flat list of numbers."""
    raw, fmt_char, ncomp, count, _ = _accessor_bytes(
        gltf, buffers, accessor_idx)
    fmt = "<" + fmt_char * (ncomp * count)
    return list(struct.unpack(fmt, raw))


def _read_accessor_grouped(gltf, buffers, accessor_idx):
    """Decode an accessor into a list of tuples (one per element)."""
    flat = _read_accessor(gltf, buffers, accessor_idx)
    ncomp = _TYPE_COMPONENTS[gltf["accessors"][accessor_idx]["type"]]
    return [tuple(flat[i:i + ncomp]) for i in range(0, len(flat), ncomp)]


# ---------------------------------------------------------------------------
# Geometry builders
# ---------------------------------------------------------------------------

def _triangle_indices(prim, gltf, buffers):
    """Return a flat list of triangle indices (always TRIANGLES mode)."""
    mode = prim.get("mode", _MODE_TRIANGLES)
    if "indices" in prim:
        idx = _read_accessor(gltf, buffers, prim["indices"])
    else:
        # Implicit indices 0..N-1 over the position accessor.
        pos_acc = prim["attributes"]["POSITION"]
        n = gltf["accessors"][pos_acc]["count"]
        idx = list(range(n))

    if mode == _MODE_TRIANGLES:
        return idx
    if mode == _MODE_TRIANGLE_STRIP:
        out = []
        for i in range(len(idx) - 2):
            if i % 2 == 0:
                out += [idx[i], idx[i + 1], idx[i + 2]]
            else:
                out += [idx[i], idx[i + 2], idx[i + 1]]
        return out
    if mode == _MODE_TRIANGLE_FAN:
        out = []
        for i in range(1, len(idx) - 1):
            out += [idx[0], idx[i], idx[i + 1]]
        return out
    cmds.warning("[gltf_io] Unsupported primitive mode {0}, "
                 "skipping primitive.".format(mode))
    return []


def _build_mesh(parent_path, name, primitives, gltf, buffers, ctx):
    """Create a Maya mesh shape under an existing transform.

    ``parent_path`` is the DAG path of the transform that should own the
    new mesh shape.  All glTF primitives on this mesh become contiguous
    runs of polygons on that single shape; per-primitive material
    assignments are applied by face range.
    Returns the shape's full DAG path (string), or ``None`` if empty.
    """
    # ---- merge primitive vertex data into one MFnMesh-friendly buffer ----
    all_points = om.MPointArray()
    poly_counts = om.MIntArray()
    poly_connects = om.MIntArray()
    u_array = om.MFloatArray()
    v_array = om.MFloatArray()
    uv_face_counts = om.MIntArray()   # per-face uv count, parallel to poly_counts
    uv_ids = om.MIntArray()
    has_any_uv = False

    normals_per_vertex = []   # list of (Nx, Ny, Nz) shared with vertex index
    colors_per_vertex = []    # list of (R, G, B[, A]) by vertex index
    has_any_normal = False
    has_any_color = False

    prim_ranges = []          # [(face_start, face_count, material_idx_or_None)]
    vertex_offset = 0

    for prim in primitives:
        attrs = prim.get("attributes", {})
        if "POSITION" not in attrs:
            continue
        positions = _read_accessor_grouped(gltf, buffers, attrs["POSITION"])
        normals = (_read_accessor_grouped(gltf, buffers, attrs["NORMAL"])
                   if "NORMAL" in attrs else None)
        uvs = (_read_accessor_grouped(gltf, buffers, attrs["TEXCOORD_0"])
               if "TEXCOORD_0" in attrs else None)
        colors = (_read_accessor_grouped(gltf, buffers, attrs["COLOR_0"])
                  if "COLOR_0" in attrs else None)
        tris = _triangle_indices(prim, gltf, buffers)
        if not positions or not tris:
            continue

        # Append positions
        for p in positions:
            all_points.append(om.MPoint(p[0], p[1], p[2]))

        # Normals & colors per-vertex
        if normals:
            has_any_normal = True
        for i in range(len(positions)):
            normals_per_vertex.append(
                normals[i] if normals else (0.0, 1.0, 0.0))

        if colors:
            has_any_color = True
        for i in range(len(positions)):
            if colors:
                c = colors[i]
                if len(c) == 3:
                    colors_per_vertex.append((c[0], c[1], c[2], 1.0))
                else:
                    colors_per_vertex.append(tuple(c))
            else:
                colors_per_vertex.append((1.0, 1.0, 1.0, 1.0))

        # UVs
        uv_start_idx = u_array.__len__()
        if uvs:
            has_any_uv = True
            for uv in uvs:
                u_array.append(uv[0])
                v_array.append(1.0 - uv[1])  # glTF V flipped vs Maya

        # Triangles -> polygons
        face_start = poly_counts.__len__()
        n_tris = len(tris) // 3
        for t in range(n_tris):
            a, b, c = tris[3 * t], tris[3 * t + 1], tris[3 * t + 2]
            poly_counts.append(3)
            poly_connects.append(vertex_offset + a)
            poly_connects.append(vertex_offset + b)
            poly_connects.append(vertex_offset + c)
            if uvs:
                uv_face_counts.append(3)
                uv_ids.append(uv_start_idx + a)
                uv_ids.append(uv_start_idx + b)
                uv_ids.append(uv_start_idx + c)
            else:
                uv_face_counts.append(0)

        prim_ranges.append((face_start, n_tris, prim.get("material")))
        vertex_offset += len(positions)

    if all_points.__len__() == 0:
        return None

    # ---- build mesh shape directly under the supplied parent transform ----
    sel = om.MSelectionList()
    sel.add(parent_path)
    parent_obj = sel.getDependNode(0)

    mesh_fn = om.MFnMesh()
    mesh_obj = mesh_fn.create(
        all_points, poly_counts, poly_connects,
        u_array if has_any_uv else om.MFloatArray(),
        v_array if has_any_uv else om.MFloatArray(),
        parent_obj,
    )
    if has_any_uv:
        mesh_fn.assignUVs(uv_face_counts, uv_ids)

    mesh_fn.setName(name + "Shape")
    shape_path = mesh_fn.fullPathName()

    # Vertex normals (locked, per-vertex)
    if has_any_normal:
        normal_array = om.MVectorArray()
        vert_ids = om.MIntArray()
        for i, n in enumerate(normals_per_vertex):
            normal_array.append(om.MVector(n[0], n[1], n[2]))
            vert_ids.append(i)
        try:
            mesh_fn.setVertexNormals(normal_array, vert_ids)
        except Exception:
            pass

    # Vertex colors
    if has_any_color:
        try:
            color_array = om.MColorArray()
            vert_ids = om.MIntArray()
            for i, c in enumerate(colors_per_vertex):
                color_array.append(om.MColor(c))
                vert_ids.append(i)
            mesh_fn.createColorSetWithName("colorSet1")
            mesh_fn.setCurrentColorSetName("colorSet1")
            mesh_fn.setVertexColors(color_array, vert_ids)
        except Exception:
            pass

    # Initial shading group on whole mesh; then override per-primitive.
    cmds.sets(shape_path, edit=True, forceElement="initialShadingGroup")

    # Assign per-primitive materials by face range.
    for face_start, n_tris, mat_idx in prim_ranges:
        if mat_idx is None or n_tris == 0:
            continue
        sg = ctx.material(mat_idx)
        if not sg:
            continue
        face_list = ["{0}.f[{1}:{2}]".format(
            shape_path, face_start, face_start + n_tris - 1)]
        cmds.sets(face_list, edit=True, forceElement=sg)

    return shape_path


# ---------------------------------------------------------------------------
# Material builder
# ---------------------------------------------------------------------------

class _ImportContext(object):
    """Caches per-import lookups (materials, images)."""

    def __init__(self, gltf, buffers, basedir, name_prefix):
        self.gltf = gltf
        self.buffers = buffers
        self.basedir = basedir
        self.name_prefix = name_prefix
        self._materials = {}    # mat_idx -> shading group name
        self._images = {}       # image_idx -> file path on disk

    def material(self, mat_idx):
        if mat_idx in self._materials:
            return self._materials[mat_idx]
        sg = self._build_material(mat_idx)
        self._materials[mat_idx] = sg
        return sg

    def _build_material(self, mat_idx):
        mats = self.gltf.get("materials", [])
        if mat_idx >= len(mats):
            return None
        mat = mats[mat_idx]
        name = mat.get("name") or "gltfMat_{0}".format(mat_idx)
        name = _safe_name(self.name_prefix + name)
        shader = cmds.shadingNode("lambert", asShader=True, name=name)
        sg = cmds.sets(name=name + "SG", empty=True,
                       renderable=True, noSurfaceShader=True)
        cmds.connectAttr(shader + ".outColor", sg + ".surfaceShader",
                         force=True)

        pbr = mat.get("pbrMetallicRoughness", {})
        base = pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])
        cmds.setAttr(shader + ".color", base[0], base[1], base[2],
                     type="double3")
        if len(base) > 3 and base[3] < 1.0:
            cmds.setAttr(shader + ".transparency",
                         1 - base[3], 1 - base[3], 1 - base[3],
                         type="double3")

        # baseColorTexture -> file node
        tex = pbr.get("baseColorTexture")
        if tex and "index" in tex:
            file_node = self._image_file_node(tex["index"], shader)
            if file_node:
                cmds.connectAttr(file_node + ".outColor",
                                 shader + ".color", force=True)
        return sg

    def _image_file_node(self, tex_idx, shader_name):
        textures = self.gltf.get("textures", [])
        if tex_idx >= len(textures):
            return None
        img_idx = textures[tex_idx].get("source")
        if img_idx is None:
            return None
        path = self._image_path(img_idx)
        if not path:
            return None
        f = cmds.shadingNode("file", asTexture=True, isColorManaged=True,
                             name=shader_name + "_baseColor")
        place = cmds.shadingNode("place2dTexture", asUtility=True,
                                 name=f + "_p2d")
        for src, dst in (("coverage", "coverage"),
                         ("translateFrame", "translateFrame"),
                         ("rotateFrame", "rotateFrame"),
                         ("mirrorU", "mirrorU"),
                         ("mirrorV", "mirrorV"),
                         ("stagger", "stagger"),
                         ("wrapU", "wrapU"),
                         ("wrapV", "wrapV"),
                         ("repeatUV", "repeatUV"),
                         ("offset", "offset"),
                         ("rotateUV", "rotateUV"),
                         ("noiseUV", "noiseUV"),
                         ("vertexUvOne", "vertexUvOne"),
                         ("vertexUvTwo", "vertexUvTwo"),
                         ("vertexUvThree", "vertexUvThree"),
                         ("vertexCameraOne", "vertexCameraOne"),
                         ("outUV", "uv"),
                         ("outUvFilterSize", "uvFilterSize")):
            cmds.connectAttr(place + "." + src, f + "." + dst, force=True)
        cmds.setAttr(f + ".fileTextureName", path, type="string")
        return f

    def _image_path(self, img_idx):
        if img_idx in self._images:
            return self._images[img_idx]
        images = self.gltf.get("images", [])
        if img_idx >= len(images):
            return None
        img = images[img_idx]
        path = None
        if "uri" in img and not img["uri"].startswith("data:"):
            cand = os.path.join(self.basedir, img["uri"])
            if os.path.isfile(cand):
                path = cand
        else:
            # Embedded image (data: URI or bufferView).  Write to a temp file.
            data = self._embedded_image_bytes(img)
            if data:
                ext = _guess_image_ext(img.get("mimeType"), data)
                path = _write_temp(data, "gltfimg_{0}{1}".format(img_idx, ext))
        self._images[img_idx] = path
        return path

    def _embedded_image_bytes(self, img):
        if "uri" in img and img["uri"].startswith("data:"):
            return _load_uri(img["uri"], self.basedir)
        bv_idx = img.get("bufferView")
        if bv_idx is None:
            return None
        bv = self.gltf["bufferViews"][bv_idx]
        start = bv.get("byteOffset", 0)
        return self.buffers[bv["buffer"]][start:start + bv["byteLength"]]


# ---------------------------------------------------------------------------
# Node hierarchy
# ---------------------------------------------------------------------------

def _build_node(node_idx, parent_path, gltf, buffers, ctx, mesh_cache):
    node = gltf["nodes"][node_idx]
    name = _safe_name(ctx.name_prefix + (node.get("name")
                                         or "node_{0}".format(node_idx)))

    transform = cmds.createNode("transform", name=name,
                                parent=parent_path or None)

    if "matrix" in node:
        m = node["matrix"]
        # glTF matrices are column-major float[16]
        mm = om.MMatrix([
            m[0],  m[1],  m[2],  m[3],
            m[4],  m[5],  m[6],  m[7],
            m[8],  m[9],  m[10], m[11],
            m[12], m[13], m[14], m[15],
        ])
        tm = om.MTransformationMatrix(mm)
        t = tm.translation(om.MSpace.kWorld)
        rot = tm.rotation()
        s = tm.scale(om.MSpace.kWorld)
        cmds.setAttr(transform + ".translate", t.x, t.y, t.z)
        cmds.setAttr(transform + ".rotate",
                     om.MAngle(rot.x).asDegrees(),
                     om.MAngle(rot.y).asDegrees(),
                     om.MAngle(rot.z).asDegrees())
        cmds.setAttr(transform + ".scale", s[0], s[1], s[2])
    else:
        if "translation" in node:
            t = node["translation"]
            cmds.setAttr(transform + ".translate", t[0], t[1], t[2])
        if "rotation" in node:
            qx, qy, qz, qw = node["rotation"]
            q = om.MQuaternion(qx, qy, qz, qw)
            e = q.asEulerRotation()
            cmds.setAttr(transform + ".rotate",
                         om.MAngle(e.x).asDegrees(),
                         om.MAngle(e.y).asDegrees(),
                         om.MAngle(e.z).asDegrees())
        if "scale" in node:
            s = node["scale"]
            cmds.setAttr(transform + ".scale", s[0], s[1], s[2])

    if "mesh" in node:
        mesh_idx = node["mesh"]
        mesh = gltf["meshes"][mesh_idx]
        mesh_name = _safe_name(ctx.name_prefix
                               + (mesh.get("name") or "mesh_{0}".format(mesh_idx))
                               + "_geo")
        _build_mesh(transform, mesh_name, mesh.get("primitives", []),
                    gltf, buffers, ctx)

    for child_idx in node.get("children", []):
        _build_node(child_idx, transform, gltf, buffers, ctx, mesh_cache)

    return transform


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def import_native(path, namespace=None, name_prefix=None):
    """Import a .glb or .gltf file using the pure-Python pipeline.

    Returns a list of top-level transform names that were created.
    """
    if not os.path.isfile(path):
        raise IOError("File not found: " + path)

    gltf, buffers = _load_container(path)
    basedir = os.path.dirname(path)

    if name_prefix is None:
        stem = _safe_name(os.path.splitext(os.path.basename(path))[0])
        name_prefix = stem + "_"

    ctx = _ImportContext(gltf, buffers, basedir, name_prefix)

    # Determine root nodes
    scenes = gltf.get("scenes", [])
    if scenes:
        scene_idx = gltf.get("scene", 0)
        roots = scenes[scene_idx].get("nodes", [])
    else:
        roots = list(range(len(gltf.get("nodes", []))))

    # Optional Maya namespace
    prev_ns = cmds.namespaceInfo(currentNamespace=True)
    if namespace:
        if not cmds.namespace(exists=":" + namespace):
            cmds.namespace(add=":" + namespace)
        cmds.namespace(set=":" + namespace)

    created = []
    try:
        # Wrap in a single root group so the import is one selectable thing.
        group_name = _safe_name(name_prefix + "root")
        root_group = cmds.group(empty=True, name=group_name, world=True)
        for node_idx in roots:
            _build_node(node_idx, root_group, gltf, buffers, ctx, {})
        created.append(root_group)
    finally:
        if namespace:
            cmds.namespace(set=":" + prev_ns)

    cmds.select(created, replace=True)
    return created


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_name(name):
    out = []
    for ch in name:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    s = "".join(out)
    if not s or not (s[0].isalpha() or s[0] == "_"):
        s = "_" + s
    return s


def _guess_image_ext(mime, data):
    if mime == "image/png":
        return ".png"
    if mime in ("image/jpeg", "image/jpg"):
        return ".jpg"
    # sniff by magic
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    return ".bin"


def _write_temp(data, name):
    import tempfile
    tmpdir = os.path.join(tempfile.gettempdir(), "gltf_io_images")
    if not os.path.isdir(tmpdir):
        os.makedirs(tmpdir)
    path = os.path.join(tmpdir, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path
