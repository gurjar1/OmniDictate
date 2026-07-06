# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

package_profile = os.environ.get("OMNIDICTATE_PACKAGE_PROFILE", "full").strip().lower()
whisper_only = package_profile in {"whisper", "whisper-only", "baseline"}
runtime_hooks = ['pyi_runtime_whisper_only.py'] if whisper_only else []

hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtSvg',
    'PIL.Image',
    'PIL.ImageGrab',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'requests',
    'comtypes',
    'pythoncom',
    'huggingface_hub',
]

hidden_imports += collect_submodules('av')
binaries = collect_dynamic_libs('av')

if not whisper_only:
    hidden_imports += [
        'accelerate',
        'cv2',
        'engines.gemma_gguf_backend',
        'engines.gemma4_backend',
        'model_downloader',
        'sentencepiece',
        'transformers',
    ]

excludes = ['matplotlib', 'pandas', 'tkinter']
if whisper_only:
    excludes += [
        'accelerate',
        'bitsandbytes',
        'cv2',
        'librosa',
        'llvmlite',
        'model_downloader',
        'moviepy',
        'numba',
        'onnxruntime',
        'scipy',
        'sklearn',
        'sentencepiece',
        'torch',
        'torchvision',
        'transformers',
    ]

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=[
        ('style.qss', '.'),
        ('icon.ico', '.')
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OmniDictate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    a.zipfiles,
    name='OmniDictate',
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
    icon='icon.ico',
)
