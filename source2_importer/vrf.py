"""Wrapper for ValveResourceFormat (VRF) Decompiler CLI.

Handles locating, downloading, and invoking the VRF CLI tool
for decompiling Source 2 compiled resources (.vmat_c, .vtex_c, etc.).
"""

import json
import os
import subprocess
import zipfile

try:
    from urllib.request import urlopen, Request
except ImportError:
    urlopen = None

_EXE_NAMES = ("Source2Viewer-CLI.exe", "Decompiler.exe")
_GITHUB_LATEST = (
    "https://api.github.com/repos/"
    "ValveResourceFormat/ValveResourceFormat/releases/latest"
)


def find_vrf():
    """Search common locations for VRF Decompiler CLI. Returns path or None."""
    env = os.environ.get("VRF_DECOMPILER")
    if env and os.path.isfile(env):
        return env

    base_dirs = [
        os.path.join(os.path.dirname(__file__), "vrf"),
        os.path.join(os.path.expanduser("~"), "VRF"),
        os.path.join(os.path.expanduser("~"), "Tools", "VRF"),
    ]
    for d in base_dirs:
        for name in _EXE_NAMES:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    return None


def download_vrf(target_dir=None, progress_fn=None):
    """Download the latest VRF CLI from GitHub.  Returns path to the exe."""
    if urlopen is None:
        raise RuntimeError("urllib not available")

    if target_dir is None:
        target_dir = os.path.join(os.path.dirname(__file__), "vrf")
    os.makedirs(target_dir, exist_ok=True)

    req = Request(_GITHUB_LATEST, headers={"Accept": "application/vnd.github.v3+json"})
    with urlopen(req, timeout=30) as resp:
        release = json.loads(resp.read())

    dl_url = None
    for asset in release.get("assets", []):
        name = asset["name"]
        if name == "cli-windows-x64.zip":
            dl_url = asset["browser_download_url"]
            break

    if not dl_url:
        raise RuntimeError("cli-windows-x64.zip not found in latest VRF release")

    zip_path = os.path.join(target_dir, "cli-windows-x64.zip")
    if progress_fn:
        progress_fn("Downloading VRF CLI ...")
    with urlopen(dl_url, timeout=120) as resp:
        with open(zip_path, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)

    if progress_fn:
        progress_fn("Extracting ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_dir)
    os.remove(zip_path)

    exe = _locate_exe(target_dir)
    if not exe:
        raise RuntimeError("Extracted VRF but could not find Decompiler.exe")
    if progress_fn:
        progress_fn(f"Ready: {exe}")
    return exe


def _locate_exe(root):
    for dirpath, _, filenames in os.walk(root):
        for name in _EXE_NAMES:
            if name in filenames:
                return os.path.join(dirpath, name)
    return None


# ── decompile helpers ────────────────────────────────────────────────

def decompile(vrf_exe, input_path, output_dir):
    """Run VRF Decompiler on *input_path*, writing to *output_dir*.
    Returns list of newly-created file paths."""
    os.makedirs(output_dir, exist_ok=True)
    before_output = _snapshot(output_dir)
    # VRF sometimes writes next to the input; track that too
    input_dir = os.path.dirname(input_path)
    before_input = _snapshot(input_dir) if input_dir != output_dir else set()

    cmd = [vrf_exe, "-i", input_path, "-o", output_dir, "-d"]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"VRF returned {result.returncode} on {input_path}\n"
            f"{result.stderr}{result.stdout}"
        )

    after_output = _snapshot(output_dir)
    new_in_output = after_output - before_output

    # Also check if files appeared next to the input
    if input_dir != output_dir:
        after_input = _snapshot(input_dir)
        new_in_input = after_input - before_input
        # Include those too
        new_in_output |= new_in_input

    return sorted(new_in_output)


def export_texture(vrf_exe, vtex_c_path, output_dir):
    """Convert a .vtex_c to PNG.  Returns output PNG path or None."""
    new = decompile(vrf_exe, vtex_c_path, output_dir)
    pngs = [f for f in new if f.lower().endswith(".png")]
    return pngs[0] if pngs else (new[0] if new else None)


def decompile_material(vrf_exe, vmat_c_path, output_dir):
    """Decompile a .vmat_c to text.  Returns the .vmat output path or None."""
    new = decompile(vrf_exe, vmat_c_path, output_dir)
    vmats = [f for f in new if f.lower().endswith(".vmat")]
    return vmats[0] if vmats else (new[0] if new else None)


def _snapshot(directory):
    """Return a set of absolute file paths under *directory*."""
    paths = set()
    for dirpath, _, filenames in os.walk(directory):
        for fn in filenames:
            paths.add(os.path.join(dirpath, fn))
    return paths
