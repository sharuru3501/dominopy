# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[
        ('/usr/local/Cellar/fluid-synth/2.4.6/lib/libfluidsynth.3.3.6.dylib', '.'),
    ],
    datas=[('src', 'src'), ('soundfonts', 'soundfonts')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DominoPy',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DominoPy',
)
app = BUNDLE(
    coll,
    name='DominoPy.app',
    icon=None,
    bundle_identifier='app.dominopy.DominoPy',
    info_plist={
        'CFBundleName': 'DominoPy',
        'CFBundleDisplayName': 'DominoPy',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
)
