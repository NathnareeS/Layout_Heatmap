# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\OneDrive\\Work\\CRCS\\Code\\Layout_Heatmap\\src\\layout_combined.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\OneDrive\\Work\\CRCS\\Code\\Layout_Heatmap\\src\\version.py', 'src'), ('D:\\OneDrive\\Work\\CRCS\\Code\\Layout_Heatmap\\src\\updater.py', 'src'), ('D:\\OneDrive\\Work\\CRCS\\Code\\Layout_Heatmap\\src\\database.py', 'src'), ('D:\\OneDrive\\Work\\CRCS\\Code\\Layout_Heatmap\\src\\layout_heatmap.py', 'src'), ('D:\\OneDrive\\Work\\CRCS\\Code\\Layout_Heatmap\\src\\layout_text_labeler.py', 'src'), ('D:\\OneDrive\\Work\\CRCS\\Code\\Layout_Heatmap\\update_installer.py', '.')],
    hiddenimports=['PIL._tkinter_finder', 'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.simpledialog', 'fitz', 'pandas', 'openpyxl', 'matplotlib', 'numpy', 'requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib.tests', 'numpy.tests'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LayoutHeatmap',
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
    icon=['D:\\OneDrive\\Work\\CRCS\\Code\\Layout_Heatmap\\icon.ico'],
)
