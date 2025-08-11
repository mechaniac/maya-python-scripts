import re, json
import maya.cmds as cmds

class TailWiggleGenerator:
    def __init__(self):
        self.win = "TailWiggleGeneratorWin"
        self.chain_input = "twg_baseInput"
        self.rows_parent = "twg_rowsParent"
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
        cmds.window(self.win, t="Tail Swing & Wiggle", sizeable=True)
        col = cmds.columnLayout(adj=True, rs=6)

        # seed input + scan
        cmds.rowLayout(nc=3, adj=2, columnWidth=[(1, 90), (2, 320), (3, 120)])
        cmds.text(l="Base name:")
        cmds.textField(self.chain_input, tx="FKhair0_M")
        cmds.button(l="Scan Chain", c=lambda *_: self.populate_rows())
        cmds.setParent("..")

        cmds.separator(h=6, style="in")

        # headers
        # Node | RotX RotY RotZ | X Halves? Y Halves? Z Halves? | X Sine? Y Sine? Z Sine? | Save | Load | Del
        cmds.rowLayout(
            nc=14,
            columnWidth=[(1,200),(2,60),(3,60),(4,60),
                         (5,88),(6,88),(7,88),
                         (8,80),(9,80),(10,80),
                         (11,70),(12,70),(13,60),(14,1)]
        )
        cmds.text(l="Node")
        cmds.text(l="RotX"); cmds.text(l="RotY"); cmds.text(l="RotZ")
        cmds.text(l="X: Halves?"); cmds.text(l="Y: Halves?"); cmds.text(l="Z: Halves?")
        cmds.text(l="X: IsSine"); cmds.text(l="Y: IsSine"); cmds.text(l="Z: IsSine")
        cmds.button(l="Save", c=lambda *_: self.save_settings_ui())
        cmds.button(l="Load", c=lambda *_: self.load_settings_ui())
        cmds.text(l="Del"); cmds.text(l="")  # spacer
        cmds.setParent("..")

        # rows scroll host
        cmds.scrollLayout(h=320)
        if cmds.layout(self.rows_parent, q=True, ex=True):
            cmds.deleteUI(self.rows_parent)
        cmds.columnLayout(self.rows_parent, adj=True)
        cmds.setParent(col)

        cmds.separator(h=6, style="in")

        # footer
        cmds.rowLayout(nc=4, columnWidth=[(1, 140), (2, 180), (3, 140), (4, 160)])
        cmds.button(l="Select Chain", c=lambda *_: self.select_chain())
        cmds.button(l="Clear Keys (timeline)", c=lambda *_: self.clear_keys_range())
        cmds.button(l="Animate", bgc=(0.6, 0.9, 0.6), c=lambda *_: self.animate())
        cmds.button(l="Close", c=lambda *_: cmds.deleteUI(self.win))
        cmds.setParent("..")

        cmds.showWindow(self.win)

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
            self.add_row(node, 0.0, 25.0, 0.0, True, True, True, False, False, False)

    def add_row(self, node, x_amp, y_amp, z_amp,
                x_halves=True, y_halves=True, z_halves=True,
                x_sine=False, y_sine=False, z_sine=False):
        r = cmds.rowLayout(
            nc=14, adj=1, parent=self.rows_parent,
            columnWidth=[(1,200),(2,60),(3,60),(4,60),
                         (5,88),(6,88),(7,88),
                         (8,80),(9,80),(10,80),
                         (11,70),(12,70),(13,60),(14,1)]
        )
        cmds.text(l=node, al="left")
        x_amp_f = cmds.floatField(v=float(x_amp), pre=2); y_amp_f = cmds.floatField(v=float(y_amp), pre=2); z_amp_f = cmds.floatField(v=float(z_amp), pre=2)
        x_halves_cb = cmds.checkBox(v=bool(x_halves), l=''); y_halves_cb = cmds.checkBox(v=bool(y_halves), l=''); z_halves_cb = cmds.checkBox(v=bool(z_halves), l='')
        x_sine_cb = cmds.checkBox(v=bool(x_sine), l=''); y_sine_cb = cmds.checkBox(v=bool(y_sine), l=''); z_sine_cb = cmds.checkBox(v=bool(z_sine), l='')
        del_btn = cmds.button(l="X", c=lambda *_: self.delete_row(r))
        cmds.text(l="")  # spacer to satisfy col count

        self.node_rows.append({
            "layout": r, "name": node,
            "xAmp": x_amp_f, "yAmp": y_amp_f, "zAmp": z_amp_f,
            "xHalves": x_halves_cb, "yHalves": y_halves_cb, "zHalves": z_halves_cb,
            "xSine": x_sine_cb, "ySine": y_sine_cb, "zSine": z_sine_cb
        })

    def delete_row(self, row_layout):
        self.node_rows = [nr for nr in self.node_rows if nr["layout"] != row_layout]
        if cmds.layout(row_layout, q=True, ex=True):
            cmds.deleteUI(row_layout)

    def select_chain(self):
        names = [nr["name"] for nr in self.node_rows]
        if names: cmds.select(names, r=True)

    # ---------- save/load (JSON string) ----------
    def serialize_settings(self):
        data = {"base": cmds.textField(self.chain_input, q=True, tx=True).strip(),"nodes":[]}
        for nr in self.node_rows:
            data["nodes"].append({
                "name": nr["name"],
                "rotX": cmds.floatField(nr["xAmp"], q=True, v=True),
                "rotY": cmds.floatField(nr["yAmp"], q=True, v=True),
                "rotZ": cmds.floatField(nr["zAmp"], q=True, v=True),
                "xHalves": cmds.checkBox(nr["xHalves"], q=True, v=True),
                "yHalves": cmds.checkBox(nr["yHalves"], q=True, v=True),
                "zHalves": cmds.checkBox(nr["zHalves"], q=True, v=True),
                "xSine": cmds.checkBox(nr["xSine"], q=True, v=True),
                "ySine": cmds.checkBox(nr["ySine"], q=True, v=True),
                "zSine": cmds.checkBox(nr["zSine"], q=True, v=True),
            })
        return json.dumps(data, indent=2)

    def apply_settings(self, data):
        self.clear_rows()
        if "base" in data:
            try: cmds.textField(self.chain_input, e=True, tx=data["base"])
            except: pass
        for item in data.get("nodes", []):
            self.add_row(
                item.get("name",""),
                item.get("rotX",0.0), item.get("rotY",25.0), item.get("rotZ",0.0),
                item.get("xHalves", True), item.get("yHalves", True), item.get("zHalves", True),
                item.get("xSine", False), item.get("ySine", False), item.get("zSine", False)
            )

    def save_settings_ui(self):
        txt = self.serialize_settings()
        w = "TWG_SaveJSON"
        if cmds.window(w, exists=True): cmds.deleteUI(w)
        cmds.window(w, t="TailWiggle: Save Settings", sizeable=True)
        cmds.columnLayout(adj=True, rs=6)
        cmds.text(l="Copy this JSON:")
        cmds.scrollField(tx=txt, editable=False, wordWrap=False, h=260)
        cmds.button(l="Close", c=lambda *_: cmds.deleteUI(w))
        cmds.showWindow(w)

    def load_settings_ui(self):
        w = "TWG_LoadJSON"
        if cmds.window(w, exists=True): cmds.deleteUI(w)
        cmds.window(w, t="TailWiggle: Load Settings", sizeable=True, w=560)
        cmds.columnLayout(adj=True, rs=6)
        cmds.text(l="Paste JSON then Apply:")
        sf = cmds.scrollField(tx="", editable=True, wordWrap=False, h=260)
        def _apply(*_):
            raw = cmds.scrollField(sf, q=True, tx=True)
            try:
                data = json.loads(raw)
            except Exception as e:
                cmds.warning("Invalid JSON: %s" % e); return
            self.apply_settings(data); cmds.deleteUI(w)
        cmds.rowLayout(nc=2, columnWidth=[(1,120),(2,120)])
        cmds.button(l="Apply", bgc=(0.6,0.9,0.6), c=_apply)
        cmds.button(l="Cancel", c=lambda *_: cmds.deleteUI(w))
        cmds.setParent(".."); cmds.showWindow(w)

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

        for row in self.node_rows:
            name = row["name"]
            x_amp = cmds.floatField(row["xAmp"], q=True, v=True)
            y_amp = cmds.floatField(row["yAmp"], q=True, v=True)
            z_amp = cmds.floatField(row["zAmp"], q=True, v=True)
            x_halves = cmds.checkBox(row["xHalves"], q=True, v=True)
            y_halves = cmds.checkBox(row["yHalves"], q=True, v=True)
            z_halves = cmds.checkBox(row["zHalves"], q=True, v=True)
            x_sine = cmds.checkBox(row["xSine"], q=True, v=True)
            y_sine = cmds.checkBox(row["ySine"], q=True, v=True)
            z_sine = cmds.checkBox(row["zSine"], q=True, v=True)

            self.key_axis(name, "rotateX", x_amp, start, end, halves=x_halves, is_sine=x_sine)
            self.key_axis(name, "rotateY", y_amp, start, end, halves=y_halves, is_sine=y_sine)
            self.key_axis(name, "rotateZ", z_amp, start, end, halves=z_halves, is_sine=z_sine)

        cmds.inViewMessage(amg="Tail/Hair keys set.", pos="midCenter", fade=True)

    def key_axis(self, node, attr, amp, start, end, halves=True, is_sine=False):
        """Idempotent inside [start,end]; keeps external keys.
           Halves:  start=+A, 1/2=-A, end=+A
           Fifths:  start=0, 1/4=+A, 1/2=0, 3/4=-A, end=0
           Fifths+IsSine (same timing as Fifths): start=-A, 1/4=+A, 1/2=-A, 3/4=+A, end=-A
        """
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
            cmds.currentTime(t, e=True)
            cmds.setAttr(plug, v)            # force evaluated value
            cmds.setKeyframe(plug, t=t, v=v) # key exactly that
    
        A = float(amp)
    
        if halves:
            set_and_key(start,  A)
            set_and_key(half,  -abs(A) if A >= 0 else abs(A))
            set_and_key(end,    A)
        else:
            if is_sine:
                # same timestamps as Fifths; alternate signs
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
    
        # keep ends exact; allow smooth interiors
        cmds.keyTangent(plug, e=True, itt='auto', ott='auto', time=(start, end))
        cmds.keyTangent(plug, e=True, itt='flat', ott='flat', time=(start, start))
        cmds.keyTangent(plug, e=True, itt='flat', ott='flat', time=(end, end))


# ---------- run ----------
tool = TailWiggleGenerator()
tool.build_ui()
