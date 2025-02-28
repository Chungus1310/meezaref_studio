# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['c:\\Users\\Administrator\\Desktop\\testing'],
    binaries=[],
    datas=[
        ('icon.png', '.'),          # Include the in-app icon
        # Add any other data files your app needs
    ],
    hiddenimports=[
        'PyQt6.QtSvg',  # Required for SVG icons
        'PyQt6.sip',    # Required PyQt internals
        'cv2',          # OpenCV
        'numpy',        # NumPy functions
        'siphash24',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'tkinter',   # Large unnecessary packages
        'PyQt5', 'PySide2', 'PySide6',               # Competing UI frameworks
        'IPython', 'notebook', 'sphinx', 'docutils',  # Dev tools
        'pytest', 'pylint', 'black',                  # Testing/linting tools
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove unnecessary Qt modules to reduce size
qt_excludes = [
    'QtBluetooth', 'QtDBus', 'QtDesigner', 'QtHelp',
    'QtLocation', 'QtMultimedia', 'QtMultimediaWidgets',
    'QtNetwork', 'QtNfc', 'QtOpenGL', 'QtPositioning',
    'QtQml', 'QtQuick', 'QtQuickWidgets', 'QtSensors',
    'QtSerialPort', 'QtSql', 'QtTest', 'QtWebChannel',
    'QtWebEngine', 'QtWebEngineCore', 'QtWebEngineWidgets',
    'QtWebSockets', 'QtXml', 'QtXmlPatterns'
]

for exclude in qt_excludes:
    a.binaries = [x for x in a.binaries if not x[0].startswith(f'PyQt6\\Qt6\\{exclude}')]

pyz = PYZ(
    a.pure, 
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MeezaRefStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_dir='C:\\upx-4.2.4-win64',  # UPX directory for compression
    console=False,  # No console window
    icon='icon.ico',  # Application icon
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_dir='C:\\upx-4.2.4-win64',
    upx_exclude=['vcruntime140.dll'],  # Don't compress certain system DLLs
    name='MeezaRefStudio',
)
