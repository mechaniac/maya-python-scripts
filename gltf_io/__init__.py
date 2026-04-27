"""Maya glTF / GLB Importer and Exporter.

Backends, auto-selected:

* ``maya2glTF`` plugin (community)        -- import + export via ``cmds.file``
* ``native`` pure-Python importer         -- import-only fallback (no plugin)
* ``FBX2glTF`` CLI binary                 -- export-only fallback
                                             (Maya FBX -> FBX2glTF -> .glb)

Usage::

    import gltf_io
    gltf_io.show()                              # open the UI
    gltf_io.import_file("C:/asset.glb")         # native fallback if no plugin
    gltf_io.export_file("C:/out.glb")           # auto-picks backend
"""

from . import plugin, fbx2gltf, native_importer, importer, exporter, ui  # noqa: F401

from .importer import import_file, batch_import, available_import_backends
from .exporter import export_file, batch_export, available_backends
from .plugin import diagnostic_report, status_message
from .fbx2gltf import find_fbx2gltf, download_fbx2gltf, ensure_fbx2gltf
from .native_importer import import_native
from .ui import show

__all__ = [
    "show",
    "import_file",
    "export_file",
    "batch_import",
    "batch_export",
    "available_backends",
    "available_import_backends",
    "import_native",
    "diagnostic_report",
    "status_message",
    "find_fbx2gltf",
    "download_fbx2gltf",
    "ensure_fbx2gltf",
]
