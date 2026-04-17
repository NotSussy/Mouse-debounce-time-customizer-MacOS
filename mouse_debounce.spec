# PyInstaller spec for MouseDebounce.app
# Build with:  pyinstaller mouse_debounce.spec --clean --noconfirm

import glob
import os
import sys
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE

block_cipher = None

# Locate the hidapi shared library bundled inside the hid package.
# PyInstaller doesn't detect it automatically because hid loads it at runtime
# via ctypes — we must tell PyInstaller to include it explicitly.
import hid as _hid_mod
_hid_pkg_dir = os.path.dirname(_hid_mod.__file__)
_hidapi_binaries = [
    (p, "hid")
    for p in glob.glob(os.path.join(_hid_pkg_dir, "*.dylib"))
    + glob.glob(os.path.join(_hid_pkg_dir, "*.so"))
    + glob.glob(os.path.join(_hid_pkg_dir, "*.so.*"))
]
if not _hidapi_binaries:
    raise RuntimeError(
        f"Could not find hidapi shared library in {_hid_pkg_dir}.\n"
        "Run:  pip install hid  inside your virtual environment."
    )

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=_hidapi_binaries,
    datas=[],
    hiddenimports=["hid", "tkinter", "tkinter.ttk", "tkinter.messagebox"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MouseDebounce",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=True,  # lets .app receive sys.argv on macOS
    target_arch=None,     # build for current arch (arm64 on Apple Silicon, x86_64 on Intel)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="MouseDebounce",
)

app = BUNDLE(
    coll,
    name="MouseDebounce.app",
    icon=None,
    bundle_identifier="io.github.glorious.mouse-debounce",
    info_plist={
        "CFBundleName": "MouseDebounce",
        "CFBundleDisplayName": "Mouse Debounce Controller",
        "CFBundleShortVersionString": "1.0.0",
        "NSPrincipalClass": "NSApplication",
        "NSHighResolutionCapable": True,
        # Needed so macOS does not treat the window as a background-only app
        "LSUIElement": False,
        # Human-readable reason shown in the Input Monitoring privacy prompt
        "NSInputMonitoringUsageDescription": (
            "This app communicates with your Glorious mouse over USB HID "
            "to change its debounce setting."
        ),
    },
)
