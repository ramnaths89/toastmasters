#!/usr/bin/env python3
"""Stage the HTML tools and cross-compile the Windows .exe (and a Linux binary),
plus a portable zip per app. The sheet zip is cmd-only and is the copy that
runs under Smart App Control; the unsigned .exe files never will.

    python3 desktop/app/build.py            # both apps
    python3 desktop/app/build.py hub        # the four-tool hub only
    python3 desktop/app/build.py sheet      # the programme sheet builder only

Two apps come out of the same Go source and the same launcher scripts; only
the staged web/ tree, the window title, the profile folder and the preferred
port differ.

hub   -> desktop/dist/ToastmastersTools.exe
         desktop/dist/ToastmastersTools-portable.zip
         desktop/dist/toastmasters-tools-linux-amd64
sheet -> desktop/dist/ProgrammeSheet.exe
         desktop/dist/ProgrammeSheet-portable.zip
         desktop/dist/programme-sheet-linux-amd64
"""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DIST = ROOT / "desktop" / "dist"
WEB = HERE / "web"
WIN = ROOT / "desktop" / "windows"

VARIANTS = {
    "hub": {
        "title": "Toastmasters Tools",
        "app_id": "ToastmastersTools",
        "port": 8765,
        "exe": "ToastmastersTools.exe",
        "zip": "ToastmastersTools-portable.zip",
        "linux": "toastmasters-tools-linux-amd64",
        # The hub needs a server (its iframes point at folder URLs), so its
        # pack carries the PowerShell one. Under Smart App Control PowerShell
        # runs in Constrained Language Mode and that server cannot start;
        # see desktop/README.md.
        "launchers": WIN,
        "launcher_files": (
            "START.cmd",
            "Install.cmd",
            "Install.ps1",
            "serve.ps1",
            "Open-online.cmd",
            "README.txt",
            "ToastmastersTools.cmd",
        ),
        "shortcut": None,
        # (repo path, path inside the app)
        "copies": [
            ("index.html", "index.html"),
            ("manifest.json", "manifest.json"),
            ("icon.svg", "icon.svg"),
            ("icon-512.png", "icon-512.png"),
            (".nojekyll", ".nojekyll"),
            ("d80-club-finder/index.html", "d80-club-finder/index.html"),
            ("programme-sheet-builder/index.html", "programme-sheet-builder/index.html"),
            ("timer/index.html", "timer/index.html"),
            ("timer/manifest.json", "timer/manifest.json"),
            ("ah-counter/index.html", "ah-counter/index.html"),
            ("ah-counter/manifest.json", "ah-counter/manifest.json"),
        ],
    },
    "sheet": {
        "title": "Programme Sheet Builder",
        "app_id": "ProgrammeSheet",
        # Its own origin for the .exe, so its localStorage never collides with
        # the hub's copy of the builder and both apps can be open at once.
        "port": 8770,
        "exe": "ProgrammeSheet.exe",
        "zip": "ProgrammeSheet-portable.zip",
        "linux": "programme-sheet-linux-amd64",
        # The portable pack is cmd-only: Edge --app=file:///…/index.html, no
        # server, no PowerShell. That is the one shape Smart App Control
        # leaves alone (cmd.exe is not policed; Edge is Microsoft-signed).
        "launchers": WIN / "sheet",
        "launcher_files": ("START.cmd", "Install.cmd", "Open-online.cmd", "README.txt"),
        # Desktop / Start Menu shortcut, generated here because a cmd-only
        # installer cannot create one on the target PC.
        "shortcut": {
            "file": "Programme Sheet Builder.lnk",
            "run": r"%LOCALAPPDATA%\ProgrammeSheet\app\START.cmd",
            "icon": r"%LOCALAPPDATA%\ProgrammeSheet\app\icon.ico",
            "description": "Programme Sheet Builder — Toastmasters agenda, offline",
        },
        # The builder is one self-contained file; it becomes the root page.
        "copies": [
            ("programme-sheet-builder/index.html", "index.html"),
            ("icon.svg", "icon.svg"),
            ("icon-512.png", "icon-512.png"),
        ],
    },
}

# Windows text files ship with CRLF. cmd.exe mis-parses labels and goto in
# some LF-only batch files, and Notepad users read README.txt.
CRLF_SUFFIXES = {".cmd", ".bat", ".ps1", ".txt"}


def make_shortcut(spec: dict, dest: Path) -> None:
    """Write a Windows .lnk that runs a .cmd via cmd.exe /c.

    The target path holds %LOCALAPPDATA% so one shortcut fits every user;
    cmd.exe expands it when it parses its own command line. Runs minimised so
    the console does not flash before Edge opens. Icon and target also carry
    environment blocks (HasExpIcon / HasExpString) so Explorer resolves them
    on a PC whose Windows lives on another drive letter."""
    try:
        import pylnk3
    except ImportError:
        sys.exit("pylnk3 is needed to write %s:  pip install pylnk3" % spec["file"])
    cmd = r"C:\Windows\System32\cmd.exe"
    lnk = pylnk3.for_file(
        cmd,
        arguments='/c "%s"' % spec["run"],
        description=spec["description"],
        window_mode=pylnk3.WINDOW_MINIMIZED,
    )
    env = pylnk3.ExtraData_EnvironmentVariableDataBlock()
    env.target_ansi = env.target_unicode = r"%windir%\System32\cmd.exe"
    ico = pylnk3.ExtraData_IconEnvironmentDataBlock()
    ico.target_ansi = ico.target_unicode = spec["icon"]
    lnk.extra_data = pylnk3.ExtraData(blocks=[env, ico])
    lnk.link_flags.HasExpString = True
    lnk.link_flags.HasExpIcon = True
    lnk.link_flags.HasIconLocation = True
    lnk.icon = spec["icon"]
    lnk.icon_index = 0
    lnk.save(str(dest))
    print("wrote", dest, dest.stat().st_size, "bytes")


def copies_of(v: dict) -> list[tuple[Path, str]]:
    out = []
    for rel, dest in v["copies"]:
        src = ROOT / rel
        if not src.is_file():
            sys.exit("missing %s" % src)
        out.append((src, dest))
    return out


def launcher_bytes(v: dict, name: str) -> bytes:
    path = v["launchers"] / name
    data = path.read_bytes()
    if path.suffix.lower() in CRLF_SUFFIXES:
        data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return data


def stage_web(v: dict) -> None:
    if WEB.exists():
        shutil.rmtree(WEB)
    for src, dest in copies_of(v):
        out = WEB / dest
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
    print("staged", len(v["copies"]), "files into", WEB)


def pack_portable(v: dict) -> None:
    """Zip the HTML plus a .cmd launcher. Smart App Control blocks the unsigned
    .exe; it does not treat this folder as an app binary."""
    staging = HERE / "portable-stage"
    if staging.exists():
        shutil.rmtree(staging)
    dest_root = staging / v["app_id"]
    for src, dest in copies_of(v):
        out = dest_root / dest
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
    for name in v["launcher_files"]:
        (dest_root / name).write_bytes(launcher_bytes(v, name))
    if v["shortcut"]:
        shutil.copy2(HERE / "icon.ico", dest_root / "icon.ico")
        make_shortcut(v["shortcut"], dest_root / v["shortcut"]["file"])
    DIST.mkdir(parents=True, exist_ok=True)
    zpath = DIST / v["zip"]
    if zpath.exists():
        zpath.unlink()
    now = time.localtime()[:6]
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(dest_root.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(staging).as_posix())
                info.date_time = now
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, path.read_bytes())
    shutil.rmtree(staging)
    print("portable zip", zpath, zpath.stat().st_size, "bytes")


def png_to_ico(png_path: Path, ico_path: Path) -> None:
    """Wrap a PNG as a Vista-style ICO (Windows accepts PNG images inside ICO)."""
    png = png_path.read_bytes()
    # ICONDIR (6) + ICONDIRENTRY (16) + PNG
    ico = bytearray()
    ico += struct.pack("<HHH", 0, 1, 1)
    ico += struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22)
    ico += png
    ico_path.write_bytes(bytes(ico))
    print("wrote", ico_path, len(ico), "bytes")


def run(env, *args, cwd=None) -> None:
    print("+", " ".join(args))
    r = subprocess.run(args, cwd=cwd or HERE, env=env)
    if r.returncode != 0:
        sys.exit(r.returncode)


def ensure_icon(env) -> None:
    ico = HERE / "icon.ico"
    png = ROOT / "desktop" / "tauri" / "src-tauri" / "icons" / "256x256.png"
    if png.is_file():
        png_to_ico(png, ico)
    syso = HERE / "rsrc_windows_amd64.syso"
    if not ico.is_file():
        return
    rsrc = shutil.which("rsrc")
    if rsrc is None:
        gobin = Path(os.environ.get("GOBIN") or Path.home() / "go" / "bin")
        candidate = gobin / "rsrc"
        if not candidate.is_file():
            run(env, "go", "install", "github.com/akavel/rsrc@v0.10.2")
        rsrc = str(candidate) if candidate.is_file() else shutil.which("rsrc")
    if rsrc:
        run(env, rsrc, "-arch", "amd64", "-ico", str(ico), "-o", str(syso))
    else:
        print("rsrc not on PATH — exe will build without a Windows icon resource")


def build_variant(name: str, env) -> None:
    v = VARIANTS[name]
    print("==== %s: %s ====" % (name, v["title"]))
    stage_web(v)
    pack_portable(v)
    xflags = " ".join(
        "-X 'main.%s=%s'" % (k, val)
        for k, val in (
            ("title", v["title"]),
            ("appID", v["app_id"]),
            ("prefAddr", "127.0.0.1:%d" % v["port"]),
        )
    )
    envw = env.copy()
    envw["GOOS"] = "windows"
    envw["GOARCH"] = "amd64"
    exe = DIST / v["exe"]
    run(envw, "go", "build", "-trimpath", "-ldflags", "-s -w -H windowsgui " + xflags, "-o", str(exe), ".")
    print("windows exe", exe, exe.stat().st_size, "bytes")

    envl = env.copy()
    envl["GOOS"] = "linux"
    envl["GOARCH"] = "amd64"
    linux = DIST / v["linux"]
    run(envl, "go", "build", "-trimpath", "-ldflags", "-s -w " + xflags, "-o", str(linux), ".")
    print("linux bin", linux, linux.stat().st_size, "bytes")


def main() -> None:
    wanted = sys.argv[1:] or list(VARIANTS)
    for name in wanted:
        if name not in VARIANTS:
            sys.exit("unknown variant %r — choose from %s" % (name, ", ".join(VARIANTS)))
    DIST.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CGO_ENABLED"] = "0"
    env_win_tidy = env.copy()
    env_win_tidy["GOOS"] = "windows"
    env_win_tidy["GOARCH"] = "amd64"
    run(env_win_tidy, "go", "mod", "tidy")
    ensure_icon(env)
    for name in wanted:
        build_variant(name, env)


if __name__ == "__main__":
    main()
