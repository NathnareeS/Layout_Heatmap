"""
PyInstaller Build Script for Layout Heatmap Generator
Creates a standalone executable for Windows
"""

import PyInstaller.__main__
import os
import shutil
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent
src_dir = project_root / "src"
dist_dir = project_root / "dist"
build_dir = project_root / "build"

# Clean previous builds
print("Cleaning previous builds...")
try:
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
except Exception as e:
    print(f"Warning: Could not fully clean dist folder: {e}")
    print("This is usually fine - PyInstaller will overwrite files.")

try:
    if build_dir.exists():
        shutil.rmtree(build_dir)
except Exception as e:
    print(f"Warning: Could not clean build folder: {e}")

print("Building executable with PyInstaller...")

# PyInstaller arguments
# Note: Windows uses semicolon (;) for path separator in --add-data
# Using --onedir (folder mode) for MUCH faster startup time
pyinstaller_args = [
    str(src_dir / "layout_combined.py"),  # Main script
    "--name=LayoutHeatmap",  # Executable name
    "--windowed",  # No console window
    "--onedir",  # Folder mode - FASTER startup (was --onefile)
    f"--icon={project_root / 'icon.ico'}",  # Application icon
    
    # Add data files (Windows uses semicolon separator)
    f"--add-data={src_dir / 'version.py'};src",
    f"--add-data={src_dir / 'updater.py'};src",
    f"--add-data={src_dir / 'database.py'};src",
    f"--add-data={src_dir / 'layout_heatmap.py'};src",
    f"--add-data={src_dir / 'layout_text_labeler.py'};src",
    f"--add-data={project_root / 'update_installer.py'};.",
    
    # Hidden imports (modules that PyInstaller might miss)
    "--hidden-import=PIL._tkinter_finder",
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.ttk",
    "--hidden-import=tkinter.filedialog",
    "--hidden-import=tkinter.messagebox",
    "--hidden-import=tkinter.simpledialog",
    "--hidden-import=fitz",  # PyMuPDF
    "--hidden-import=pandas",
    "--hidden-import=openpyxl",
    "--hidden-import=matplotlib",
    "--hidden-import=numpy",
    "--hidden-import=requests",
    
    # Exclude unnecessary modules to reduce size
    "--exclude-module=matplotlib.tests",
    "--exclude-module=numpy.tests",
    
    # Other options
    "--clean",  # Clean PyInstaller cache
    "--noconfirm",  # Replace output directory without asking
]

# Run PyInstaller
PyInstaller.__main__.run(pyinstaller_args)

print("\n" + "="*60)
print("Build completed!")
print("="*60)

# Copy additional files to dist folder
print("\nCopying additional files...")

dist_folder = dist_dir / "LayoutHeatmap"
if not dist_folder.exists():
    dist_folder = dist_dir

# Create necessary folders in dist
(dist_folder / "data").mkdir(exist_ok=True)
(dist_folder / "examples").mkdir(exist_ok=True)

# Copy example files
examples_src = project_root / "examples"
if examples_src.exists():
    for file in examples_src.glob("*"):
        if file.is_file():
            shutil.copy2(file, dist_folder / "examples" / file.name)
    print("✓ Copied example files")

# Copy README
readme_src = project_root / "README.md"
if readme_src.exists():
    shutil.copy2(readme_src, dist_folder / "README.md")
    print("✓ Copied README.md")

# Copy update installer
update_installer_src = project_root / "update_installer.py"
if update_installer_src.exists():
    shutil.copy2(update_installer_src, dist_folder / "update_installer.py")
    print("✓ Copied update_installer.py")

# Copy icon file
icon_src = project_root / "icon.ico"
if icon_src.exists():
    shutil.copy2(icon_src, dist_folder / "icon.ico")
    print("✓ Copied icon.ico")

# Create a simple batch file to run the app
batch_content = """@echo off
echo Starting Layout Heatmap Generator...
LayoutHeatmap.exe
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit...
    pause > nul
)
"""

with open(dist_folder / "run.bat", 'w') as f:
    f.write(batch_content)
print("✓ Created run.bat")

print("\n" + "="*60)
print("Distribution package ready!")
print("="*60)
print(f"\nLocation: {dist_folder}")
print("\nContents:")
print("  - LayoutHeatmap.exe (main executable)")
print("  - update_installer.py (for auto-updates)")
print("  - data/ (user data folder)")
print("  - examples/ (example files)")
print("  - README.md (documentation)")
print("  - run.bat (launcher script)")
print("\nTo distribute:")
print("1. ZIP the entire folder")
print("2. Upload to GitHub releases")
print("3. Users can download, extract, and run LayoutHeatmap.exe")
print("\n" + "="*60)
