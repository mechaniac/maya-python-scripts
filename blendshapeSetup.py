"""Top-level launcher for the Blendshape Setup shelf tool."""


def show():
    import importlib

    from blendshape_setup import logic
    from blendshape_setup import ui

    importlib.reload(logic)
    importlib.reload(ui)
    ui.show()


def show_on_main_screen():
    import importlib

    from blendshape_setup import logic
    from blendshape_setup import ui

    importlib.reload(logic)
    importlib.reload(ui)
    ui.show_on_main_screen()


def bring_to_main_screen():
    show_on_main_screen()


if __name__ == "__main__":
    show()
