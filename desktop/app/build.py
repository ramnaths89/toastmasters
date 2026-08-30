#!/usr/bin/env python3
"""Stage the four tools and cross-compile the Windows .exe (and a Linux binary).

    python3 desktop/app/build.py

Writes:
    desktop/dist/ToastmastersTools.exe
    desktop/dist/ToastmastersTools-portable.zip
    desktop/dist/toastmasters-tools-linux-amd64
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

COPIES = [
    "index.html",
    "manifest.json",
    "icon.svg",
    "icon-512.png",
    ".nojekyll",
    "d80-club-finder/index.html",
    "programme-sheet-builder/index.html",
    "timer/index.html",
    "timer/manifest.json",
    "ah-counter/index.html",
    "ah-counter/manifest.json",
]


def stage_web() -> None:
    if WEB.exists():
        shutil.rmtree(WEB)
    for rel in COPIES:
        src = ROOT / rel
        if not src.is_file():
            sys.exit("missing %s" % src)
        dest = WEB / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    print("staged", len(COPIES), "files into", WEB)


def pack_portable() -> None:
    """Zip the HTML plus a .cmd launcher. Smart App Control blocks the unsigned
    .exe; it does not treat this folder as an app binary."""
    win = ROOT / "desktop" / "windows"
    staging = HERE / "portable-stage"
    if staging.exists():
        shutil.rmtree(staging)
    dest_root = staging / "ToastmastersTools"
    for rel in COPIES:
        src = ROOT / rel
        if not src.is_file():
            sys.exit("missing %s" % src)
        out = dest_root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
    for name in ("ToastmastersTools.cmd", "serve.ps1", "Open-online.cmd", "README.txt"):
        shutil.copy2(win / name, dest_root / name)
    DIST.mkdir(parents=True, exist_ok=True)
    zpath = DIST / "ToastmastersTools-portable.zip"
    if zpath.exists():
        zpath.unlink()
    now = time.localtime()[:6]
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in dest_root.rglob("*"):
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


def main() -> None:
    stage_web()
    pack_portable()
    DIST.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CGO_ENABLED"] = "0"
    env_win_tidy = env.copy()
    env_win_tidy["GOOS"] = "windows"
    env_win_tidy["GOARCH"] = "amd64"
    run(env_win_tidy, "go", "mod", "tidy")

    ico = HERE / "icon.ico"
    png = ROOT / "desktop" / "tauri" / "src-tauri" / "icons" / "256x256.png"
    if png.is_file():
        png_to_ico(png, ico)

    syso = HERE / "rsrc_windows_amd64.syso"
    if ico.is_file():
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

    ldflags = "-s -w -H windowsgui"
    envw = env.copy()
    envw["GOOS"] = "windows"
    envw["GOARCH"] = "amd64"
    exe = DIST / "ToastmastersTools.exe"
    run(envw, "go", "build", "-trimpath", "-ldflags", ldflags, "-o", str(exe), ".")
    print("windows exe", exe, exe.stat().st_size, "bytes")

    envl = env.copy()
    envl["GOOS"] = "linux"
    envl["GOARCH"] = "amd64"
    linux = DIST / "toastmasters-tools-linux-amd64"
    run(envl, "go", "build", "-trimpath", "-ldflags", "-s -w", "-o", str(linux), ".")
    print("linux bin", linux, linux.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
