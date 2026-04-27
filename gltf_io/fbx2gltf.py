"""Wrapper for the FBX2glTF CLI.

`FBX2glTF <https://github.com/godotengine/FBX2glTF>`_ is a
single-binary command-line tool that converts ``.fbx`` files to
``.glb`` / ``.gltf``. It is **export-only** (FBX -> glTF).

This module:

* Locates ``FBX2glTF.exe`` in common places (env var, package bundle,
  ``~/Tools/FBX2glTF``).
* Downloads the latest Windows release from GitHub on demand.
* Provides ``convert(fbx_path, out_path, binary=True, ...)``.

Combined with Maya's built-in FBX exporter (``cmds.file -type FBX export``)
this gives us a glTF *exporter* that needs no Maya plugin.
"""

import json
import os
import ssl
import stat
import subprocess
import zipfile

try:
    from urllib.request import urlopen, Request
except ImportError:
    urlopen = None


# ── locations & names ────────────────────────────────────────────


_EXE_NAMES = (
    "FBX2glTF.exe",
    "FBX2glTF-windows-x86_64.exe",
    "FBX2glTF-windows-x64.exe",
    "FBX2glTF",  # non-Windows
)

# The original facebookincubator/FBX2glTF repo has been removed.
# The actively maintained fork lives under the Godot Engine org.
_GITHUB_LATEST = (
    "https://api.github.com/repos/"
    "godotengine/FBX2glTF/releases/latest"
)

_WIN_ASSET_HINTS = ("windows", "win")


def _bundle_dir():
    return os.path.join(os.path.dirname(__file__), "fbx2gltf")


def _user_tools_dir():
    return os.path.join(os.path.expanduser("~"), "Tools", "FBX2glTF")


def find_fbx2gltf():
    """Return the path to a usable FBX2glTF executable, or None."""
    env = os.environ.get("FBX2GLTF")
    if env and os.path.isfile(env):
        return env

    for d in (_bundle_dir(), _user_tools_dir(),
              os.path.join(os.path.expanduser("~"), "FBX2glTF")):
        for name in _EXE_NAMES:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    return None


# ── download ────────────────────────────────────────────────────────


def _make_ssl_context():
    """Build an SSL context that works inside Maya's bundled Python."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    ctx = ssl.create_default_context()
    if ctx.get_ca_certs():
        return ctx
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_default_certs()
    if ctx.get_ca_certs():
        return ctx
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _pick_windows_asset(release):
    """Choose the best Windows asset from a GitHub release JSON blob.

    Prefers a bare .exe; falls back to .zip (which we'll extract).
    Returns ``(asset_name, download_url)`` or ``(None, None)``.
    """
    assets = release.get("assets", [])

    # 1) bare windows exe
    for asset in assets:
        name = asset.get("name", "")
        low = name.lower()
        if low.endswith(".exe") and any(h in low for h in _WIN_ASSET_HINTS):
            return name, asset["browser_download_url"]

    # 2) windows zip (current godotengine/FBX2glTF format)
    for asset in assets:
        name = asset.get("name", "")
        low = name.lower()
        if low.endswith(".zip") and any(h in low for h in _WIN_ASSET_HINTS):
            return name, asset["browser_download_url"]

    return None, None


def _extract_exe_from_zip(zip_path, target_dir):
    """Extract the FBX2glTF executable from a release zip.

    Returns the absolute path to the extracted exe.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.namelist()
        exe_member = None
        for m in members:
            base = os.path.basename(m).lower()
            if base.endswith(".exe") and "fbx2gltf" in base:
                exe_member = m
                break
        if exe_member is None:
            # POSIX builds have no extension
            for m in members:
                base = os.path.basename(m).lower()
                if base.startswith("fbx2gltf") and "license" not in base:
                    exe_member = m
                    break
        if exe_member is None:
            raise RuntimeError("FBX2glTF executable not found inside "
                               + os.path.basename(zip_path))

        # Extract just the exe (flatten -- ignore any directory prefix)
        out_name = os.path.basename(exe_member)
        out_path = os.path.join(target_dir, out_name)
        with zf.open(exe_member) as src, open(out_path, "wb") as dst:
            dst.write(src.read())
        return out_path


def download_fbx2gltf(target_dir=None, progress_fn=None):
    """Download the latest FBX2glTF Windows build from GitHub.

    Pulls from ``godotengine/FBX2glTF`` (the maintained fork; the
    original ``facebookincubator/FBX2glTF`` repo has been removed).

    Returns the absolute path to the saved executable.
    """
    if urlopen is None:
        raise RuntimeError("urllib not available")

    if target_dir is None:
        target_dir = _bundle_dir()
    os.makedirs(target_dir, exist_ok=True)

    ssl_ctx = _make_ssl_context()

    if progress_fn:
        progress_fn("Querying GitHub for latest FBX2glTF release ...")
    req = Request(_GITHUB_LATEST,
                  headers={"Accept": "application/vnd.github.v3+json"})
    with urlopen(req, timeout=30, context=ssl_ctx) as resp:
        release = json.loads(resp.read())

    asset_name, dl_url = _pick_windows_asset(release)
    if not dl_url:
        raise RuntimeError(
            "No Windows FBX2glTF asset found in latest release.\n"
            "Download manually from "
            "https://github.com/godotengine/FBX2glTF/releases")

    download_path = os.path.join(target_dir, asset_name)
    if progress_fn:
        progress_fn("Downloading {0} ...".format(asset_name))
    with urlopen(dl_url, timeout=300, context=ssl_ctx) as resp:
        with open(download_path, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)

    if asset_name.lower().endswith(".zip"):
        if progress_fn:
            progress_fn("Extracting {0} ...".format(asset_name))
        out_path = _extract_exe_from_zip(download_path, target_dir)
        try:
            os.remove(download_path)
        except Exception:
            pass
    else:
        out_path = download_path

    # Mark executable on POSIX
    try:
        st = os.stat(out_path)
        os.chmod(out_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass

    if progress_fn:
        progress_fn("Ready: {0}".format(out_path))
    return out_path


def ensure_fbx2gltf(progress_fn=None):
    """Return a usable FBX2glTF.exe path, downloading it if necessary."""
    p = find_fbx2gltf()
    if p:
        return p
    return download_fbx2gltf(progress_fn=progress_fn)


# ── conversion ──────────────────────────────────────────────────────


def convert(fbx_path, out_path,
            binary=True,
            embed_textures=True,
            draco=False,
            khr_materials_unlit=False,
            extra_args=None,
            exe_path=None):
    """Run FBX2glTF on *fbx_path*, writing to *out_path*.

    Parameters
    ----------
    fbx_path : str
        Source ``.fbx`` file.
    out_path : str
        Destination ``.glb`` or ``.gltf``. Format is auto-detected
        from the extension unless ``binary`` is set explicitly.
    """
    if not os.path.isfile(fbx_path):
        raise IOError("FBX not found: " + fbx_path)

    exe = exe_path or find_fbx2gltf()
    if not exe:
        raise RuntimeError("FBX2glTF.exe not found. Call ensure_fbx2gltf() "
                           "to download it, or set the FBX2GLTF env var.")

    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    cmd = [exe, "--input", fbx_path, "--output", out_path]
    if binary:
        cmd.append("--binary")
    if embed_textures:
        cmd.append("--embed")
    if draco:
        cmd.append("--draco")
    if khr_materials_unlit:
        cmd.append("--khr-materials-unlit")
    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=600,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError(
            "FBX2glTF returned {0}\n{1}{2}".format(
                result.returncode, result.stderr, result.stdout))

    return out_path
