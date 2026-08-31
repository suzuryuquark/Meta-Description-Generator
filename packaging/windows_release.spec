# -*- mode: python ; coding: utf-8 -*-

import argparse
import atexit
import os
import shutil
import sys
from pathlib import Path

project_root = Path(SPECPATH).parent.resolve()
sys.path.insert(0, str(project_root))

import flet_cli.__pyinstaller.config as hook_config
from flet_cli.__pyinstaller.utils import copy_flet_bin
from flet_cli.__pyinstaller.win_utils import (
    update_flet_view_icon,
    update_flet_view_version_info,
)

from scripts.package_deduplication import filter_duplicate_flet_binaries

parser = argparse.ArgumentParser()
parser.add_argument("--version", required=True)
parser.add_argument("--name", default="MetaDescriptionGenerator")
parser.add_argument("--icon", type=Path, required=True)
options = parser.parse_args()

icon_path = options.icon.resolve()
file_version = f"{options.version}.0"
temp_bin_dir = copy_flet_bin()
if not temp_bin_dir:
    raise RuntimeError("Flet desktop runtime was not found.")

hook_config.temp_bin_dir = temp_bin_dir
atexit.register(shutil.rmtree, temp_bin_dir, ignore_errors=True)

fletd_path = Path(temp_bin_dir) / "fletd.exe"
if fletd_path.exists():
    fletd_path.unlink()

flet_executable = Path(temp_bin_dir) / "flet" / "flet.exe"
if not flet_executable.is_file():
    raise RuntimeError(f"Flet executable was not found: {flet_executable}")

update_flet_view_icon(str(flet_executable), str(icon_path))
version_file = update_flet_view_version_info(
    exe_path=str(flet_executable),
    product_name="Meta Description Generator",
    file_description="Gemini APIを利用したMeta title・description生成ツール",
    product_version=options.version,
    file_version=file_version,
    company_name="suzuryuquark",
    copyright="Copyright © suzuryuquark",
)

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "mypy",
        "lxml",
        "PIL",
        "setuptools",
        "pygments",
        "rich",
        "markdown_it",
        "click",
    ],
    noarchive=False,
    optimize=0,
)

a.binaries, removed_binaries = filter_duplicate_flet_binaries(a.binaries)
print(
    "Removed duplicate Flet root binaries:",
    len(removed_binaries),
    f"({sum(item.size_bytes for item in removed_binaries):,} uncompressed bytes)",
)
for removed_binary in removed_binaries:
    print("  -", removed_binary.root_name)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=options.name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version_file,
    icon=[str(icon_path)],
)

shutil.rmtree(temp_bin_dir, ignore_errors=True)
atexit.unregister(shutil.rmtree)
