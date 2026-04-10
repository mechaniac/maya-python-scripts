import json
import maya.cmds as cmds


class AnimGeneratorBase:
    """Shared base class for all animation cycle generators."""

    WINDOW_NAME = ""
    WINDOW_TITLE = ""
    WINDOW_SIZE = (600, 400)

    # Axis color-coding for UI float fields (RGB = XYZ)
    COLOR_X = (0.45, 0.18, 0.18)  # Red
    COLOR_Y = (0.18, 0.45, 0.18)  # Green
    COLOR_Z = (0.18, 0.18, 0.45)  # Blue

    def __init__(self):
        self.window = self.WINDOW_NAME
        self.frames = []

    # ------------------------------------------------------------------ #
    #  Node resolution
    # ------------------------------------------------------------------ #
    @staticmethod
    def resolve_node(name):
        """Case-insensitive node lookup with scapula alias support.

        Returns the actual scene node name if found, else ``None``.
        """
        if not name:
            return None
        name_lower = name.lower()
        aliases = {
            'fkscapula1_l': 'fkscapula_l',
            'fkscapula_l':  'fkscapula1_l',
            'fkscapula1_r': 'fkscapula_r',
            'fkscapula_r':  'fkscapula1_r',
        }
        candidates = [name_lower, aliases.get(name_lower, name_lower)]
        if name_lower.endswith(('_l', '_r', '_m')):
            base_no_one = name_lower.replace('1_', '_')
            if base_no_one not in candidates:
                candidates.append(base_no_one)

        all_nodes = (cmds.ls(type="transform") or []) + \
                    (cmds.ls(type="joint") or []) + \
                    (cmds.ls(type="locator") or [])
        lower_map = {n.lower(): n for n in all_nodes}
        for c in candidates:
            if c in lower_map:
                return lower_map[c]

        # General fallback: match ignoring '1' in numbered suffixes
        # e.g. FKSpine1_M <-> FKSpine_M, FKScapula1_L <-> FKScapula_L
        search = name_lower.replace('1_', '_')
        for n in all_nodes:
            if n.lower().replace('1_', '_') == search:
                return n
        return None

    # backward-compat alias
    def resolve_node_case_insensitive(self, name):
        return self.resolve_node(name)

    # ------------------------------------------------------------------ #
    #  Timeline helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def timeline_range():
        """Return ``(start, end)`` from playback options."""
        s = cmds.playbackOptions(q=True, min=True)
        e = cmds.playbackOptions(q=True, max=True)
        return s, e

    def compute_frames(self):
        """Compute the standard 5-point timing list
        ``[start, quarter, mid, three_quarter, end]``
        and store it in ``self.frames``.
        """
        start, end = self.timeline_range()
        quarter = start + (end - start) / 4.0
        mid = (start + end) / 2.0
        three_quarter = start + 3 * (end - start) / 4.0
        self.frames = [start, quarter, mid, three_quarter, end]

    # ------------------------------------------------------------------ #
    #  Keyframing
    # ------------------------------------------------------------------ #
    def set_key(self, obj, attr, time, value):
        """Set a keyframe, resolving nodes case-insensitively.

        Handles missing nodes/attrs, locked attrs, and connected attrs
        gracefully without raising.
        """
        if not cmds.objExists(obj):
            resolved = self.resolve_node(obj)
            if resolved:
                obj = resolved
            else:
                print(f"?? Skipping key: {obj}.{attr} (not found)")
                return
        if not cmds.attributeQuery(attr, node=obj, exists=True):
            print(f"?? Skipping key: {obj}.{attr} (attr not found)")
            return

        full_attr = f"{obj}.{attr}"
        try:
            locked = cmds.getAttr(full_attr, lock=True)
        except Exception:
            locked = False

        cmds.currentTime(time, edit=True)

        if locked:
            try:
                cmds.setKeyframe(obj, at=attr, t=time)
            except Exception as e:
                print(f"!! Could not key locked {full_attr}: {e}")
            return

        connected = False
        try:
            connected = cmds.connectionInfo(full_attr, isDestination=True)
        except Exception:
            pass

        try:
            if connected:
                cmds.setKeyframe(obj, at=attr, t=time)
                cmds.keyframe(obj, at=attr, e=True, t=(time, time), vc=float(value))
            else:
                cmds.setAttr(full_attr, float(value))
                cmds.setKeyframe(obj, at=attr, t=time)
        except Exception as e:
            print(f"!! set_key failed on {full_attr} @ {time}: {e}")

    def cut_attr_keys_in_range(self, node, attr, start, end, reset_to_zero=False):
        """Cut keys on *node.attr* in ``[start, end]``; optionally reset to 0."""
        resolved = self.resolve_node(node) or node
        full = f"{resolved}.{attr}"
        if not cmds.objExists(resolved):
            return
        if not cmds.attributeQuery(attr, node=resolved, exists=True):
            return
        cmds.cutKey(resolved, at=attr, time=(start, end))
        if reset_to_zero:
            if not cmds.getAttr(full, lock=True) and \
               not cmds.connectionInfo(full, isDestination=True):
                try:
                    cmds.setAttr(full, 0)
                except Exception:
                    pass

    def clear_keys_on(self, controls, attrs=None):
        """Clear keys and reset attrs on *controls* within the playback range."""
        if attrs is None:
            attrs = ['translateX', 'translateY', 'translateZ',
                     'rotateX', 'rotateY', 'rotateZ']
        start, end = self.timeline_range()
        for ctrl in controls:
            resolved = self.resolve_node(ctrl)
            if not resolved:
                if cmds.objExists(ctrl):
                    resolved = ctrl
                else:
                    continue
            for attr in attrs:
                full = f"{resolved}.{attr}"
                if not cmds.attributeQuery(attr, node=resolved, exists=True):
                    continue
                cmds.cutKey(resolved, at=attr, time=(start, end))
                if not cmds.getAttr(full, lock=True) and \
                   not cmds.connectionInfo(full, isDestination=True):
                    try:
                        cmds.setAttr(full, 0)
                    except Exception:
                        pass

    # ------------------------------------------------------------------ #
    #  Settings I/O helpers
    # ------------------------------------------------------------------ #
    def print_settings_json(self, label, settings):
        """Print a settings dict as formatted JSON."""
        print(f"// {label} Settings:\n" + json.dumps(settings, indent=2))

    def prompt_and_apply(self, apply_fn, refresh_fn=None):
        """Show a prompt dialog for JSON input, parse, and call *apply_fn*.

        Optionally calls *refresh_fn()* afterward to update the UI.
        """
        result = cmds.promptDialog(
            title="Apply Settings",
            message="Paste JSON settings string here:",
            button=['Apply', 'Cancel'],
            defaultButton='Apply',
            cancelButton='Cancel',
            dismissString='Cancel',
        )
        if result != 'Apply':
            return
        try:
            text = cmds.promptDialog(query=True, text=True)
            settings = json.loads(text)
            apply_fn(settings)
            if refresh_fn:
                refresh_fn()
        except Exception as e:
            cmds.confirmDialog(title="Error", message=str(e))

    # ------------------------------------------------------------------ #
    #  UI helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def two_col_row(label1, fn1, label2, fn2, widths=(180, 100, 180, 100)):
        """Create a 4-column row layout with two *label + field* pairs."""
        cmds.rowLayout(numberOfColumns=4, columnWidth4=widths,
                       adjustableColumn=4)
        cmds.text(label=label1); fn1()
        cmds.text(label=label2); fn2()
        cmds.setParent('..')

    @staticmethod
    def try_set_float(ctrl, val):
        """Safely update a floatField or floatSlider value."""
        if not ctrl or not cmds.control(ctrl, exists=True):
            return
        try:
            cmds.floatField(ctrl, e=True, v=float(val))
            return
        except Exception:
            pass
        try:
            cmds.floatSlider(ctrl, e=True, v=float(val))
        except Exception:
            pass

    # pattern helpers used by several generators
    @staticmethod
    def pattern_thirds(amp):
        """Return ``[+amp, -amp, +amp]`` for start/mid/end keying."""
        return [amp, -amp, amp]

    @staticmethod
    def pattern_fifths(amp):
        """Return ``[+amp, -amp, +amp, -amp, +amp]`` for 5-point keying."""
        return [amp, -amp, amp, -amp, amp]
