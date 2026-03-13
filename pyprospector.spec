# -*- mode: python ; coding: utf-8 -*-
"""pyprospector.spec

PyInstaller build specification for pyProspector.
Uses one-dir (COLLECT) mode so the Playwright browser directory can be placed
next to the executable by the Inno Setup installer.

Build with:
    pyinstaller pyprospector.spec --clean --noconfirm
"""

import os
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
)

block_cipher = None

# ── Data files ────────────────────────────────────────────────────────────────
datas = []
datas += collect_data_files("streamlit", include_py_files=True)
datas += collect_data_files("altair")
datas += collect_data_files("pandas")
datas += collect_data_files("pyarrow")
datas += collect_data_files("pydeck")
datas += collect_data_files("playwright")        # includes the Node.js driver
datas += collect_data_files("playwright_stealth")
datas += collect_data_files("openpyxl")
datas += [("app.py", ".")]                       # the Streamlit app
datas += [("assets", "assets")]                  # icon & other assets

# ── Hidden imports ────────────────────────────────────────────────────────────
hiddenimports = [
    # Streamlit
    "streamlit",
    "streamlit.web",
    "streamlit.web.cli",
    "streamlit.web.server",
    "streamlit.web.server.server",
    "streamlit.runtime",
    "streamlit.runtime.caching",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "streamlit.components",
    "streamlit.components.v1",
    "streamlit.elements",
    "streamlit.delta_generator",
    # Tornado (Streamlit web server)
    "tornado",
    "tornado.platform.asyncio",
    "tornado.iostream",
    "tornado.websocket",
    "tornado.httpserver",
    "tornado.httpclient",
    # CLI / output
    "click",
    "rich",
    "rich.console",
    "rich.logging",
    # Playwright
    "playwright",
    "playwright.sync_api",
    "playwright.async_api",
    "playwright._impl._driver",
    "playwright_stealth",
    # Data
    "pandas",
    "pandas.io.formats.style",
    "pyarrow",
    "openpyxl",
    "openpyxl.styles",
    "openpyxl.styles.fills",
    "openpyxl.utils",
    "openpyxl.utils.dataframe",
    # Visualisation / Streamlit deps
    "altair",
    "pydeck",
    # Utilities
    "packaging",
    "packaging.version",
    "importlib_metadata",
    "attr",
    "attrs",
    "jsonschema",
    "jsonschema.validators",
    "referencing",
    "toolz",
    "blinker",
    "validators",
    "cachetools",
    "pytz",
    "tzdata",
    "toml",
    "watchdog",
    "watchdog.observers",
    "watchdog.events",
    "gitpython",
    "PIL",
    "PIL.Image",
]

# Collect all sub-modules so dynamic imports inside Streamlit and Playwright work
hiddenimports += collect_submodules("streamlit")
hiddenimports += collect_submodules("playwright")

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude heavy scientific packages that are not used
    excludes=["matplotlib", "scipy", "sklearn", "tensorflow", "notebook", "IPython"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pyProspector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX disabled to avoid antivirus false positives
    console=True,       # Change to False for a windowless (no terminal) build
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets\\icon\\pyProspector01.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="pyProspector",
)
