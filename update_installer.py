"""
Update installer script for Layout Heatmap Generator
This script runs separately to replace application files while the main app is closed
"""

import sys
import os
import shutil
import time
import subprocess
from pathlib import Path


def show_progress(message):
    """Print progress message"""
    print(f"[UPDATE] {message}")


def install_update(source_dir, target_dir):
    """Install update by replacing files"""
    try:
        show_progress("Starting update installation...")
        
        # Wait a moment for the main app to close
        time.sleep(2)
        
        # Get list of files to update
        source_path = Path(source_dir)
        target_path = Path(target_dir)
        
        # Backup old version (optional)
        backup_dir = target_path / "backup_old_version"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        
        show_progress("Creating backup of current version...")
        backup_dir.mkdir(exist_ok=True)
        
        # Copy important files to backup
        important_files = ['layout_projects.db', 'data', 'examples']
        for item in important_files:
            item_path = target_path / item
            if item_path.exists():
                if item_path.is_file():
                    shutil.copy2(item_path, backup_dir / item)
                else:
                    shutil.copytree(item_path, backup_dir / item, dirs_exist_ok=True)
        
        show_progress("Installing new version...")
        
        # Files/folders to skip during copy (user data that will be restored later)
        skip_items = {'layout_projects.db', 'data', 'examples', 'backup_old_version'}
        
        # Copy new files
        for item in source_path.rglob('*'):
            if item.is_file():
                # Get relative path
                rel_path = item.relative_to(source_path)
                
                # Skip user data files - they will be restored from backup
                if rel_path.parts[0] in skip_items:
                    continue
                
                target_file = target_path / rel_path
                
                # Create parent directory if needed
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                try:
                    shutil.copy2(item, target_file)
                    show_progress(f"Updated: {rel_path}")
                except Exception as e:
                    show_progress(f"Warning: Could not update {rel_path}: {e}")
        
        # Restore user data
        show_progress("Restoring user data...")
        for item in important_files:
            backup_item = backup_dir / item
            if backup_item.exists():
                target_item = target_path / item
                if backup_item.is_file():
                    shutil.copy2(backup_item, target_item)
                else:
                    shutil.copytree(backup_item, target_item, dirs_exist_ok=True)
        
        show_progress("Update completed successfully!")
        
        # Launch the updated application
        show_progress("Launching updated application...")
        
        # Find the executable
        exe_path = target_path / "LayoutHeatmap.exe"
        bat_path = target_path / "run_app.bat"
        py_path = target_path / "src" / "layout_combined.py"
        
        if exe_path.exists():
            subprocess.Popen([str(exe_path)])
        elif bat_path.exists():
            subprocess.Popen([str(bat_path)], shell=True)
        elif py_path.exists():
            subprocess.Popen(["python", str(py_path)])
        
        show_progress("Application restarted. Update installer will now exit.")
        time.sleep(2)
        
        return True
        
    except Exception as e:
        show_progress(f"ERROR: Update failed: {e}")
        input("Press Enter to exit...")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: update_installer.py <source_dir> <target_dir>")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    target_dir = sys.argv[2]
    
    print("=" * 60)
    print("Layout Heatmap Generator - Update Installer")
    print("=" * 60)
    print()
    
    success = install_update(source_dir, target_dir)
    
    if success:
        print("\n✓ Update installed successfully!")
    else:
        print("\n✗ Update failed. Please try again or install manually.")
    
    sys.exit(0 if success else 1)
