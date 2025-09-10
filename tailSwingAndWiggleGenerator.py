import re, json
import maya.cmds as cmds

class TailWiggleGenerator:
    def __init__(self):
        self.win = "TailWiggleGeneratorWin"
        self.chain_input = "twg_baseInput"
        self.rows_parent = "twg_rowsParent"
        self.mirror_x = False
        self.mirror_y = False
        self.mirror_z = False
        self.node_rows = []  # [{...ui ids...}]

    # ---------- chain detection ----------
    def parse_base(self, name):
        m = re.search(r'(.*?)(\d+)(.*)$', name)
        if not m:
            cmds.warning("Name must contain a number block, e.g. FKhair0_M or FKTail0_M")
            return None
        prefix, num, suffix = m.group(1), m.group(2), m.group(3)
        return prefix, int(num), suffix

    def find_chain(self, seed_name):
        parsed = self.parse_base(seed_name)
        if not parsed:
            return []
        prefix, start_idx, suffix = parsed
        found = []
        i = start_idx
        while True:
            name = f"{prefix}{i}{suffix}"
            if cmds.objExists(name):
                found.append(name); i += 1
            else:
                break
        if not found:
            cmds.warning("No nodes found from seed.")
        return found

    # ---------- UI ----------
    def build_ui(self):
        if cmds.window(self.win, exists=True):
            cmds.deleteUI(self.win)
        self.node_rows = []

        win = cmds.window(self.win, t="Tail Swing & Wiggle", sizeable=True)
        col = cmds.columnLayout(adj=True, rs=6)

        # seed input + scan
        r = cmds.rowLayout(nc=3, adj=2)  # keep it simple/portable
        cmds.text(l="Base name:")
        cmds.textField(self.chain_input, tx="FKhair0_M")
        cmds.button(l="Scan Chain", c=lambda *_: self.populate_rows())
        cmds.setParent("..")

        cmds.separator(h=6, style="in")

        # headers (no risky columnWidth flags)
        hdr = cmds.rowLayout(nc=14)
        for lbl in [
            "Node",
            "RotX","RotY","RotZ",
            "OffX","OffY","OffZ",
            "X:Halves","Y:Halves","Z:Halves",
            "X:IsSine","Y:IsSine","Z:IsSine",
            "Del"
        ]:
            cmds.text(l=lbl, al="left")
        cmds.setParent("..")

        # --- Global mirrors row ---
        mir = cmds.rowLayout(nc=6, adj=1)
        cmds.text(l="Mirror Animation:")
        self.mirror_x_cb = cmds.checkBox(l="X", v=self.mirror_x, ann="Mirror all rotateX animation")
        self.mirror_y_cb = cmds.checkBox(l="Y", v=self.mirror_y, ann="Mirror all rotateY animation")
        self.mirror_z_cb = cmds.checkBox(l="Z", v=self.mirror_z, ann="Mirror all rotateZ animation")
        cmds.setParent("..")

        # rows scroll host
        rows_scroll = cmds.scrollLayout(h=320)
        if cmds.layout(self.rows_parent, q=True, ex=True):
            cmds.deleteUI(self.rows_parent)
        cmds.columnLayout(self.rows_parent, adj=True, p=rows_scroll)
        cmds.setParent(col)

        cmds.separator(h=6, style="in")

        # footer (one Save + one Load)
        f = cmds.rowLayout(nc=6, adj=3)
        cmds.button(l="Select Chain", c=lambda *_: self.select_chain())
        cmds.button(l="Clear Keys (timeline)", c=lambda *_: self.clear_keys_range())
        cmds.button(l="Save JSON", c=lambda *_: self.save_settings_ui())
        cmds.button(l="Load JSON", c=lambda *_: self.load_settings_ui())
        cmds.button(l="Animate", bgc=(0.6, 0.9, 0.6), c=lambda *_: self.animate())
        cmds.button(l="Close", c=lambda *_: cmds.deleteUI(self.win))
        cmds.setParent("..")

        cmds.showWindow(win)

    def clear_rows(self):
        if cmds.layout(self.rows_parent, q=True, ca=True):
            for c in cmds.layout(self.rows_parent, q=True, ca=True):
                cmds.deleteUI(c)
        self.node_rows = []

    def populate_rows(self):
        self.clear_rows()
        seed = cmds.textField(self.chain_input, q=True, tx=True).strip()
        chain = self.find_chain(seed)
        if not chain:
            return
        # defaults: X=0, Y=25, Z=0; all Halves True; all IsSine False
        for node in chain:
            self.add_row(node, 0.0, 25.0, 0.0, True, True, True, False, False, False, off_x=0.0, off_y=0.0, off_z=0.0)

    def add_row(self, node, x_amp, y_amp, z_amp,
                x_halves=True, y_halves=True, z_halves=True,
                x_sine=False, y_sine=False, z_sine=False,
                off_x=0.0, off_y=0.0, off_z=0.0):
        r = cmds.rowLayout(nc=14, adj=1, parent=self.rows_parent)

        cmds.text(l=node, al="left")

        # amplitudes
        x_amp_f = cmds.floatField(v=float(x_amp), pre=2, minValue=-1e6, maxValue=1e6)
        y_amp_f = cmds.floatField(v=float(y_amp), pre=2, minValue=-1e6, maxValue=1e6)
        z_amp_f = cmds.floatField(v=float(z_amp), pre=2, minValue=-1e6, maxValue=1e6)
        
        # offsets
        x_off_f = cmds.floatField(v=float(off_x), pre=2, minValue=-1e6, maxValue=1e6)
        y_off_f = cmds.floatField(v=float(off_y), pre=2, minValue=-1e6, maxValue=1e6)
        z_off_f = cmds.floatField(v=float(off_z), pre=2, minValue=-1e6, maxValue=1e6)


        # modes (now with labels)
        x_halves_cb = cmds.checkBox(l='X Halves', v=bool(x_halves), ann='Use halves pattern for rotateX')
        y_halves_cb = cmds.checkBox(l='Y Halves', v=bool(y_halves), ann='Use halves pattern for rotateY')
        z_halves_cb = cmds.checkBox(l='Z Halves', v=bool(z_halves), ann='Use halves pattern for rotateZ')

        x_sine_cb   = cmds.checkBox(l='X IsSine', v=bool(x_sine), ann='Use sine-style fifths for rotateX')
        y_sine_cb   = cmds.checkBox(l='Y IsSine', v=bool(y_sine), ann='Use sine-style fifths for rotateY')
        z_sine_cb   = cmds.checkBox(l='Z IsSine', v=bool(z_sine), ann='Use sine-style fifths for rotateZ')


        # delete
        cmds.button(l="X", c=lambda *_: self.delete_row(r))

        self.node_rows.append({
            "layout": r, "name": node,
            "xAmp": x_amp_f, "yAmp": y_amp_f, "zAmp": z_amp_f,
            "xOff": x_off_f, "yOff": y_off_f, "zOff": z_off_f,
            "xHalves": x_halves_cb, "yHalves": y_halves_cb, "zHalves": z_halves_cb,
            "xSine": x_sine_cb, "ySine": y_sine_cb, "zSine": z_sine_cb
        })

    def delete_row(self, row_layout):
        self.node_rows = [nr for nr in self.node_rows if nr["layout"] != row_layout]
        if cmds.layout(row_layout, q=True, ex=True):
            cmds.deleteUI(row_layout)

    def select_chain(self):
        names = [nr["name"] for nr in self.node_rows]
        if names:
            cmds.select(names, r=True)

    # ---------- JSON (single save/load including selection) ----------
    def get_settings_dict(self):
        """Return current UI state + selection as a Python dict."""
        data = {
            "version": 1,
            "base": cmds.textField(self.chain_input, q=True, tx=True).strip(),
            "selection": cmds.ls(sl=True) or [],
            "mirror": {  # NEW
                "x": cmds.checkBox(self.mirror_x_cb, q=True, v=True),
                "y": cmds.checkBox(self.mirror_y_cb, q=True, v=True),
                "z": cmds.checkBox(self.mirror_z_cb, q=True, v=True),
            },
            "nodes": []
        }
        for nr in self.node_rows:
            data["nodes"].append({
                "name": nr["name"],
                "rotX": cmds.floatField(nr["xAmp"], q=True, v=True),
                "rotY": cmds.floatField(nr["yAmp"], q=True, v=True),
                "rotZ": cmds.floatField(nr["zAmp"], q=True, v=True),
                "offX": cmds.floatField(nr["xOff"], q=True, v=True),
                "offY": cmds.floatField(nr["yOff"], q=True, v=True),
                "offZ": cmds.floatField(nr["zOff"], q=True, v=True),
                "xHalves": cmds.checkBox(nr["xHalves"], q=True, v=True),
                "yHalves": cmds.checkBox(nr["yHalves"], q=True, v=True),
                "zHalves": cmds.checkBox(nr["zHalves"], q=True, v=True),
                "xSine": cmds.checkBox(nr["xSine"], q=True, v=True),
                "ySine": cmds.checkBox(nr["ySine"], q=True, v=True),
                "zSine": cmds.checkBox(nr["zSine"], q=True, v=True),
            })
        return data

    def save_settings_ui(self):
        """One-click save: settings + selection -> JSON dialog."""
        txt = json.dumps(self.get_settings_dict(), indent=2)
        w = "TWG_SaveJSON"
        if cmds.window(w, exists=True): cmds.deleteUI(w)
        cmds.window(w, t="TailWiggle: Save JSON", sizeable=True)
        cmds.columnLayout(adj=True, rs=6)
        cmds.text(l="Copy this JSON:")
        cmds.scrollField(tx=txt, editable=False, wordWrap=False, h=260)
        cmds.button(l="Close", c=lambda *_: cmds.deleteUI(w))
        cmds.showWindow(w)

    def load_settings_ui(self):
        """One-click load: paste JSON -> apply UI; also restores selection if present."""
        w = "TWG_LoadJSON"
        if cmds.window(w, exists=True): cmds.deleteUI(w)
        cmds.window(w, t="TailWiggle: Load JSON", sizeable=True, w=560)
        cmds.columnLayout(adj=True, rs=6)
        cmds.text(l="Paste JSON then Apply:")
        sf = cmds.scrollField(tx="", editable=True, wordWrap=False, h=260)
        def _apply(*_):
            raw = cmds.scrollField(sf, q=True, tx=True)
            try:
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError("Top-level JSON must be an object.")
            except Exception as e:
                cmds.warning("Invalid JSON: %s" % e); return
            self.apply_settings(data)  # UI rows + base
            # optional: restore selection
            sel = [s for s in data.get("selection", []) if cmds.objExists(s)]
            if sel:
                try: cmds.select(sel, r=True)
                except: pass
            cmds.deleteUI(w)
        cmds.rowLayout(nc=2)
        cmds.button(l="Apply", bgc=(0.6,0.9,0.6), c=_apply)
        cmds.button(l="Cancel", c=lambda *_: cmds.deleteUI(w))
        cmds.setParent(".."); cmds.showWindow(w)

    def apply_settings(self, data):
        """Error-tolerant UI update from dict (Python 3 safe)."""
        self.clear_rows()

        base = data.get("base", "")
        if isinstance(base, str):
            try:
                cmds.textField(self.chain_input, e=True, tx=base)
            except Exception:
                pass
        mir = data.get("mirror", {})
        try:
            if "x" in mir: cmds.checkBox(self.mirror_x_cb, e=True, v=bool(mir["x"]))
            if "y" in mir: cmds.checkBox(self.mirror_y_cb, e=True, v=bool(mir["y"]))
            if "z" in mir: cmds.checkBox(self.mirror_z_cb, e=True, v=bool(mir["z"]))
        except:
            pass
        for item in data.get("nodes", []):
            if not isinstance(item, dict):
                continue
            self.add_row(
                item.get("name",""),
                item.get("rotX",0.0), item.get("rotY",25.0), item.get("rotZ",0.0),
                item.get("xHalves", True), item.get("yHalves", True), item.get("zHalves", True),
                item.get("xSine", False), item.get("ySine", False), item.get("zSine", False),
                off_x=item.get("offX", 0.0), off_y=item.get("offY", 0.0), off_z=item.get("offZ", 0.0)
            )


    # ---------- animation core ----------
    def get_timeline(self):
        start = int(round(cmds.playbackOptions(q=True, minTime=True)))
        end   = int(round(cmds.playbackOptions(q=True, maxTime=True)))
        if end <= start: end = start + 30
        return start, end

    def clear_keys_range(self):
        start, end = self.get_timeline()
        names = [nr["name"] for nr in self.node_rows]
        attrs = [".rotateX", ".rotateY", ".rotateZ"]
        for n in names:
            for a in attrs:
                plug = n + a
                if cmds.objExists(plug):
                    try: cmds.cutKey(plug, time=(start, end), option="keys")
                    except: pass

    def animate(self):
        if not self.node_rows:
            cmds.warning("No nodes to animate. Scan chain first."); return
        start, end = self.get_timeline()
        if (end - start) <= 0: cmds.warning("Invalid timeline length."); return
        self.clear_keys_range()
    
        # NEW: global multipliers
        mx = -1.0 if cmds.checkBox(self.mirror_x_cb, q=True, v=True) else 1.0
        my = -1.0 if cmds.checkBox(self.mirror_y_cb, q=True, v=True) else 1.0
        mz = -1.0 if cmds.checkBox(self.mirror_z_cb, q=True, v=True) else 1.0
    
        for row in self.node_rows:
            name   = row["name"]
            x_amp  = cmds.floatField(row["xAmp"], q=True, v=True)
            y_amp  = cmds.floatField(row["yAmp"], q=True, v=True)
            z_amp  = cmds.floatField(row["zAmp"], q=True, v=True)
            x_off  = cmds.floatField(row["xOff"], q=True, v=True)
            y_off  = cmds.floatField(row["yOff"], q=True, v=True)
            z_off  = cmds.floatField(row["zOff"], q=True, v=True)
            x_halves = cmds.checkBox(row["xHalves"], q=True, v=True)
            y_halves = cmds.checkBox(row["yHalves"], q=True, v=True)
            z_halves = cmds.checkBox(row["zHalves"], q=True, v=True)
            x_sine   = cmds.checkBox(row["xSine"],   q=True, v=True)
            y_sine   = cmds.checkBox(row["ySine"],   q=True, v=True)
            z_sine   = cmds.checkBox(row["zSine"],   q=True, v=True)
    
            # apply mirrors to amplitude and offset
            self.key_axis(name, "rotateX", mx * x_amp, start, end, halves=x_halves, is_sine=x_sine, offset=mx * x_off)
            self.key_axis(name, "rotateY", my * y_amp, start, end, halves=y_halves, is_sine=y_sine, offset=my * y_off)
            self.key_axis(name, "rotateZ", mz * z_amp, start, end, halves=z_halves, is_sine=z_sine, offset=mz * z_off)
    
        cmds.inViewMessage(amg="Tail/Hair keys set.", pos="midCenter", fade=True)


    def key_axis(self, node, attr, amp, start, end, halves=True, is_sine=False, offset=0.0):
        plug = f"{node}.{attr}"
        if not cmds.objExists(plug):
            return

        length = float(end - start)
        if length <= 0.0:
            return

        half = start + 0.5 * length
        q1   = start + 0.25 * length
        q3   = start + 0.75 * length

        def set_and_key(t, v):
            val = v + offset
            cmds.currentTime(t, e=True)
            cmds.setAttr(plug, val)
            cmds.setKeyframe(plug, t=t, v=val)

        A = float(amp)

        if halves:
            set_and_key(start,  A)
            set_and_key(half,  -abs(A) if A >= 0 else abs(A))
            set_and_key(end,    A)
        else:
            if is_sine:
                set_and_key(start, -A)
                set_and_key(q1,     A)
                set_and_key(half,  -A)
                set_and_key(q3,     A)
                set_and_key(end,   -A)
            else:
                set_and_key(start, 0.0)
                set_and_key(q1,    A)
                set_and_key(half,  0.0)
                set_and_key(q3,   -A)
                set_and_key(end,   0.0)

        cmds.keyTangent(plug, e=True, itt='auto', ott='auto', time=(start, end))
        cmds.keyTangent(plug, e=True, itt='flat', ott='flat', time=(start, start))
        cmds.keyTangent(plug, e=True, itt='flat', ott='flat', time=(end, end))

# ---------- run ----------
tool = TailWiggleGenerator()
tool.build_ui()
