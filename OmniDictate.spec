# OmniDictate.spec

# -*- mode: python ; coding: utf-8 -*-

# --- Analysis Section ---
# Defines the inputs to PyInstaller: your script, data files, hidden imports, etc.
a = Analysis(
    ['main_gui.py'], # Entry-point script
    pathex=['.'],    # Add current directory to Python path for analysis (optional but good practice)
    binaries=[],     # List of tuples: ('source/path/to/file', 'destination/in/bundle') - for DLLs/SOs not found automatically
    datas=[          # List of tuples: ('source/path/to/file', 'destination/in/bundle') - for non-code files
        ('style.qss', '.'),   # Include the stylesheet in the root of the output folder
        ('icon.ico', '.')      # Include the icon file in the root of the output folder
    ],
    hiddenimports=[  # Modules PyInstaller might miss during static analysis
        # Essential for PySide6
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork', # Often needed indirectly
        'PySide6.QtSvg',    # Often needed for icons/styles

        # Essential for pynput global hotkeys on Windows
        'pynput.keyboard._win32',
        'pynput.mouse._win32', # Include mouse just in case

        # Dependencies for pywinauto/OS interaction (handled by hooks usually, but explicit can help)
        'comtypes',
        'pythoncom',
        # 'pywin32', # Explicitly removed - rely on hooks for pythoncom/pywintypes

        # Add any other modules reported as missing during testing below:
        # 'sounddevice',
        # 'cffi',
    ],
    hookspath=[],          # Paths to custom PyInstaller hooks (usually not needed)
    hooksconfig={},        # Configuration for hooks
    runtime_hooks=[],      # Scripts to run at runtime before your main script starts
    excludes=[],           # Modules to explicitly exclude (leave empty)
    # win_no_prefer_redirects, win_private_assemblies, crypto_key, cipher_block_size: Defaults are usually fine
)

# --- PYZ Section ---
# Creates a compressed archive of pure Python modules found during Analysis.
pyz = PYZ(a.pure)

# --- EXE Section ---
# Creates the actual executable file from your script, the PYZ archive, and the bootloader.
# For a one-folder build (using COLLECT), this primarily bundles the core execution logic.
exe = EXE(
    pyz,
    a.scripts, # Your script(s) from Analysis
    [],        # Binaries are handled by COLLECT
    name='OmniDictate', # Name of the output .exe file
    debug=False,        # Set to True ONLY for debugging build issues
    bootloader_ignore_signals=False,
    strip=False,        # Set to True for potentially smaller exe (removes symbols)
    upx=True,           # Use UPX compression if available (reduces size)
    upx_exclude=[],
    runtime_tmpdir=None,# Use default temp location for bootloader
    console=False,      # <<< CRITICAL: False for a GUI application (no background console)
    disable_windowed_traceback=False, # Keep False to see tracebacks if windowed app crashes
    argv_emulation=False,
    target_arch=None,   # Auto-detect architecture (e.g., 'x86_64')
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'     # <<< Path to your application icon relative to this spec file
)

# --- COLLECT Section ---
# Gathers everything needed into the output folder for a one-folder distribution.
coll = COLLECT(
    exe,            # The executable created above
    a.datas,        # Data files specified in Analysis (e.g., style.qss, icon.ico)
    a.binaries,     # Binary files (DLLs, etc.) found by Analysis or added manually
    a.zipfiles,     # Zipped archives (like the PYZ)
    a.scripts,      # Usually empty here as scripts are in PYZ/EXE
    [],             # Runtime hooks (usually empty)
    name='OmniDictate', # <<< Name of the OUTPUT FOLDER created in 'dist'
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # Match the EXE console setting
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'     # Icon associated with the bundle/folder (can be same as EXE)
)