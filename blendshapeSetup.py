"""Top-level launcher for the Blendshape Setup shelf tool."""


def show():
    import importlib

    from blendshape_setup import logic
    from blendshape_setup import ui

    importlib.reload(logic)
    importlib.reload(ui)
    ui.show()


if __name__ == "__main__":
    show()
