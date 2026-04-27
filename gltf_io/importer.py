"""glTF / GLB import.

Two backends are tried in order:

1. ``maya2glTF`` plugin (if loaded) -- richest support
2. ``native`` pure-Python importer  -- always available, geometry +
   basic materials only

The backend can be forced via the ``backend`` argument.
"""

import os
import maya.cmds as cmds

from . import plugin
from . import native_importer


def available_import_backends():
    """Return the list of importer backends available right now."""
    backends = []
    if plugin.import_translator():
        backends.append("maya2glTF")
    backends.append("native")  # always works
    return backends


def _import_options(merge_namespaces, import_animation,
                    import_materials, import_skin):
    return ";".join([
        "loadSettings=1",
        "importAnimations={0}".format(1 if import_animation else 0),
        "importMaterials={0}".format(1 if import_materials else 0),
        "importSkins={0}".format(1 if import_skin else 0),
        "mergeNamespaces={0}".format(1 if merge_namespaces else 0),
    ])


def _import_via_maya2gltf(path, namespace, merge_namespaces,
                          import_animation, import_materials, import_skin):
    translator = plugin.import_translator()
    if not translator:
        raise RuntimeError("maya2glTF plugin not loaded.")

    kwargs = dict(
        i=True,
        type=translator,
        ignoreVersion=True,
        mergeNamespacesOnClash=merge_namespaces,
        options=_import_options(merge_namespaces, import_animation,
                                import_materials, import_skin),
        preserveReferences=True,
    )
    if namespace:
        kwargs["namespace"] = namespace
    else:
        kwargs["renamingPrefix"] = os.path.splitext(os.path.basename(path))[0]

    return cmds.file(path, **kwargs)


def import_file(path,
                namespace=None,
                merge_namespaces=True,
                import_animation=True,
                import_materials=True,
                import_skin=True,
                backend="auto"):
    """Import a single .glb / .gltf file.

    ``backend`` may be ``"auto"`` (prefer maya2glTF, else native),
    ``"maya2glTF"`` (force the plugin), or ``"native"`` (force the
    pure-Python importer).
    """
    if not os.path.isfile(path):
        raise IOError("File not found: " + path)

    chosen = backend
    if chosen == "auto":
        chosen = ("maya2glTF" if plugin.import_translator()
                  else "native")

    if chosen == "maya2glTF":
        return _import_via_maya2gltf(
            path, namespace, merge_namespaces,
            import_animation, import_materials, import_skin)

    if chosen == "native":
        cmds.inViewMessage(
            amg="<hl>glTF</hl> importing via native (pure-Python) backend...",
            pos="topCenter", fade=True)
        return native_importer.import_native(path, namespace=namespace)

    raise ValueError("Unknown import backend: " + str(backend))


def batch_import(folder, pattern=(".glb", ".gltf"), **kwargs):
    """Import every .glb / .gltf file in *folder* (non-recursive)."""
    if not os.path.isdir(folder):
        raise IOError("Folder not found: " + folder)
    imported = []
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(tuple(pattern)):
            full = os.path.join(folder, name)
            try:
                import_file(full, **kwargs)
                imported.append(full)
            except Exception as exc:
                cmds.warning("Failed to import {0}: {1}".format(full, exc))
    return imported
