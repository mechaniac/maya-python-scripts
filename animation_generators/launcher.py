import importlib
import maya.cmds as cmds

WINDOW_NAME = "AnimGeneratorsLauncher"
WINDOW_TITLE = "Animation Generators"


def _launch(module_name, class_name):
    """Import (or reload) a generator module and call show()."""
    mod = importlib.import_module(f"animation_generators.{module_name}")
    importlib.reload(mod)
    cls = getattr(mod, class_name)
    tool = cls()
    tool.show()


def show():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)
    cmds.window(WINDOW_NAME, title=WINDOW_TITLE, widthHeight=(340, 380), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnOffset=("both", 10))

    cmds.separator(height=6, style="none")
    cmds.text(label="Animation Generators", font="boldLabelFont", align="center")
    cmds.separator(height=8, style="in")

    cmds.frameLayout(label="Locomotion (Legs)", collapsable=True, marginWidth=6, marginHeight=4)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.button(label="Walk Cycle", height=28,
                command=lambda *_: _launch("walk_cycle", "WalkCycleTool"))
    cmds.button(label="Run Cycle", height=28,
                command=lambda *_: _launch("run_cycle", "RunCycleGenerator"))
    cmds.button(label="Side Step", height=28,
                command=lambda *_: _launch("side_step", "SideStepGenerator"))
    cmds.setParent(".."); cmds.setParent("..")

    cmds.frameLayout(label="Locomotion (Hands / Arms)", collapsable=True, marginWidth=6, marginHeight=4)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.button(label="Hand Walk Cycle", height=28,
                command=lambda *_: _launch("hand_walk_cycle", "HandWalkCycleTool"))
    cmds.button(label="Hand Side Step", height=28,
                command=lambda *_: _launch("hand_side_step", "HandSideStepGenerator"))
    cmds.setParent(".."); cmds.setParent("..")

    cmds.frameLayout(label="Aerial / Secondary", collapsable=True, marginWidth=6, marginHeight=4)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.button(label="Flight Cycle", height=28,
                command=lambda *_: _launch("flight", "FlightGenerator"))
    cmds.button(label="Tail / Hair Wiggle", height=28,
                command=lambda *_: _launch("tail_wiggle", "TailWiggleGenerator"))
    cmds.setParent(".."); cmds.setParent("..")

    cmds.separator(height=12, style="none")
    cmds.showWindow(WINDOW_NAME)
