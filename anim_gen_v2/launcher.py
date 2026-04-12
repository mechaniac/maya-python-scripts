"""Entry point for the anim_gen_v2 package.

Usage in Maya::

    from anim_gen_v2 import launcher
    launcher.show()
"""


def show():
    """Open the Animation Generator v2 window."""
    from .ui.window import show as _show
    return _show()
