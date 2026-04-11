"""
source2Importer.py  —  Source 2 Character Importer for Maya

Imports Source 2 models (.vmdl) into Maya: FBX mesh + skeleton,
texture decompilation (.vtex_c -> PNG), and material creation
using the VRF Decompiler CLI.

Usage:
    import source2Importer; source2Importer.show()
"""


def show():
    from source2_importer.ui import show as _show
    _show()
