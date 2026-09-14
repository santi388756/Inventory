# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# Mantener NumPy, Pandas y Matplotlib sin escanear TODOS sus submodulos.
# PyInstaller y sus hooks oficiales detectan los imports reales; collect_submodules()
# para estas librerias provocaba cientos de miles de operaciones innecesarias.

datas_customtkinter = collect_data_files("customtkinter")

# No se fuerza ningun backend grafico: Inventory no usa un backend de Matplotlib.
# Esto evita que PyInstaller arrastre Qt/Gtk/Tk y cientos de modulos opcionales.
hiddenimports = []

# Evitar que PyInstaller analice frameworks instalados en el entorno del usuario
# que Inventory no utiliza. Esto reduce enormemente el tiempo de Analysis.
excludes = [
    "IPython",
    "jupyter",
    "notebook",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "wx",
    "tkinter.test",
    "scipy",
    "sklearn",
    "pandas.tests",
    "pandas.plotting._matplotlib",
    "pandas.io.formats.style",
    "pandas.io.clipboard",
    "numpy.testing",
    "numpy.f2py",
    "numpy.distutils",
    "matplotlib.tests",
    "matplotlib.backends.qt_compat",
    "matplotlib.backends.backend_qt5",
    "matplotlib.backends.backend_qt6",
    "matplotlib.backends.backend_gtk3",
    "matplotlib.backends.backend_gtk4",
    "matplotlib.backends.backend_wx",
    "matplotlib.backends.backend_macosx",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_nbagg",
    "matplotlib.backends.backend_webagg",
    "matplotlib.backends.backend_ipympl",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas_customtkinter,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Inventory",
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
)
