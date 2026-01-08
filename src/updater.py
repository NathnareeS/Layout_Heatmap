"""
Automatic update checker and installer for Layout Heatmap Generator
Checks GitHub releases for new versions and handles automatic updates
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
import sys
import zipfile
import tempfile
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from version import __version__, __github_repo__


class UpdateChecker:
    def __init__(self, parent=None):
        self.parent = parent
        self.github_repo = __github_repo__
        self.current_version = __version__
        self.last_check_file = Path(tempfile.gettempdir()) / "layout_heatmap_last_check.txt"
        
    def should_check_for_updates(self):
        """Check if we should check for updates (once per day)"""
        if not self.last_check_file.exists():
            return True
        
        try:
            with open(self.last_check_file, 'r') as f:
                last_check = datetime.fromisoformat(f.read().strip())
                return datetime.now() - last_check > timedelta(days=1)
        except:
            return True
    
    def mark_update_checked(self):
        """Mark that we've checked for updates"""
        try:
            with open(self.last_check_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except:
            pass
    
    def get_latest_release(self):
        """Fetch latest release info from GitHub"""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return None
    
    def compare_versions(self, latest_version):
        """Compare current version with latest version"""
        # Remove 'v' prefix if present
        latest = latest_version.lstrip('v')
        current = self.current_version.lstrip('v')
        
        # Split into major.minor.patch
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            # Pad to same length
            while len(latest_parts) < 3:
                latest_parts.append(0)
            while len(current_parts) < 3:
                current_parts.append(0)
            
            return latest_parts > current_parts
        except:
            return False
    
    def check_for_updates(self, silent=False):
        """Check for updates and show dialog if available"""
        release_info = self.get_latest_release()
        
        if not release_info:
            if not silent:
                messagebox.showinfo(
                    "Update Check",
                    "Unable to check for updates.\nPlease check your internet connection."
                )
            return
        
        latest_version = release_info.get('tag_name', '').lstrip('v')
        
        if self.compare_versions(latest_version):
            # New version available!
            self.show_update_dialog(release_info)
        else:
            if not silent:
                messagebox.showinfo(
                    "No Updates",
                    f"You're running the latest version ({self.current_version})"
                )
        
        self.mark_update_checked()
    
    def show_update_dialog(self, release_info):
        """Show update available dialog"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Update Available")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Version info
        version = release_info.get('tag_name', 'Unknown')
        release_date = release_info.get('published_at', '')[:10]
        release_notes = release_info.get('body', 'No release notes available.')
        
        # Header
        header_frame = tk.Frame(dialog, bg="#4CAF50", height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text="🎉 New Version Available!",
            font=("Segoe UI", 16, "bold"),
            bg="#4CAF50",
            fg="white"
        ).pack(pady=10)
        
        tk.Label(
            header_frame,
            text=f"Version {version} (Released: {release_date})",
            font=("Segoe UI", 10),
            bg="#4CAF50",
            fg="white"
        ).pack()
        
        # Current version
        info_frame = tk.Frame(dialog, bg="white")
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(
            info_frame,
            text=f"Current version: {self.current_version}  →  New version: {version}",
            font=("Segoe UI", 9),
            bg="white"
        ).pack()
        
        # Release notes
        notes_frame = tk.LabelFrame(dialog, text="What's New", font=("Segoe UI", 10, "bold"))
        notes_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        notes_text = tk.Text(notes_frame, wrap=tk.WORD, height=10, font=("Segoe UI", 9))
        notes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        notes_text.insert("1.0", release_notes)
        notes_text.config(state=tk.DISABLED)
        
        # Scrollbar for notes
        scrollbar = ttk.Scrollbar(notes_text, command=notes_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        notes_text.config(yscrollcommand=scrollbar.set)
        
        # Buttons
        button_frame = tk.Frame(dialog, bg="white")
        button_frame.pack(fill=tk.X, padx=20, pady=15)
        
        def start_update():
            dialog.destroy()
            self.download_and_install_update(release_info)
        
        update_btn = tk.Button(
            button_frame,
            text="Update Now",
            command=start_update,
            bg="#4CAF50",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2"
        )
        update_btn.pack(side=tk.LEFT, padx=5)
        
        later_btn = tk.Button(
            button_frame,
            text="Remind Me Later",
            command=dialog.destroy,
            bg="#757575",
            fg="white",
            font=("Segoe UI", 10),
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2"
        )
        later_btn.pack(side=tk.LEFT, padx=5)
    
    def download_and_install_update(self, release_info):
        """Download and install update"""
        # Find the ZIP asset
        assets = release_info.get('assets', [])
        zip_asset = None
        
        for asset in assets:
            if asset['name'].endswith('.zip'):
                zip_asset = asset
                break
        
        if not zip_asset:
            messagebox.showerror(
                "Update Error",
                "No downloadable update package found.\nPlease visit GitHub to download manually."
            )
            return
        
        # Create progress dialog
        progress_dialog = tk.Toplevel(self.parent)
        progress_dialog.title("Downloading Update")
        progress_dialog.geometry("400x150")
        progress_dialog.resizable(False, False)
        progress_dialog.transient(self.parent)
        progress_dialog.grab_set()
        
        tk.Label(
            progress_dialog,
            text="Downloading update...",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=20)
        
        progress_bar = ttk.Progressbar(
            progress_dialog,
            mode='indeterminate',
            length=300
        )
        progress_bar.pack(pady=10)
        progress_bar.start()
        
        status_label = tk.Label(
            progress_dialog,
            text="Please wait...",
            font=("Segoe UI", 9)
        )
        status_label.pack(pady=5)
        
        def download_thread():
            try:
                # Download the ZIP file
                download_url = zip_asset['browser_download_url']
                temp_dir = tempfile.mkdtemp()
                zip_path = os.path.join(temp_dir, "update.zip")
                
                status_label.config(text="Downloading...")
                response = requests.get(download_url, stream=True)
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                status_label.config(text="Extracting...")
                
                # Extract to temp directory
                extract_dir = os.path.join(temp_dir, "update")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                status_label.config(text="Installing...")
                
                # Get the application directory
                if getattr(sys, 'frozen', False):
                    app_dir = os.path.dirname(sys.executable)
                else:
                    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
                # Launch the updater script
                updater_script = os.path.join(app_dir, "update_installer.py")
                
                # Create a batch file to run the updater
                batch_content = f"""@echo off
timeout /t 2 /nobreak > nul
python "{updater_script}" "{extract_dir}" "{app_dir}"
"""
                batch_path = os.path.join(temp_dir, "run_updater.bat")
                with open(batch_path, 'w') as f:
                    f.write(batch_content)
                
                # Close progress dialog
                progress_dialog.destroy()
                
                # Show final message
                messagebox.showinfo(
                    "Update Ready",
                    "Update downloaded successfully!\n\nThe application will now restart to complete the update."
                )
                
                # Launch updater and exit
                subprocess.Popen([batch_path], shell=True)
                
                # Exit the application
                if self.parent:
                    self.parent.quit()
                else:
                    sys.exit(0)
                
            except Exception as e:
                progress_dialog.destroy()
                messagebox.showerror(
                    "Update Error",
                    f"Failed to download update:\n{str(e)}\n\nPlease try again later or download manually from GitHub."
                )
        
        # Start download in background thread
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()


def check_for_updates_on_startup(parent=None):
    """Check for updates on application startup (once per day)"""
    checker = UpdateChecker(parent)
    if checker.should_check_for_updates():
        # Check in background thread to not block startup
        def check_thread():
            checker.check_for_updates(silent=True)
        
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()


def manual_update_check(parent=None):
    """Manually check for updates (from menu)"""
    checker = UpdateChecker(parent)
    checker.check_for_updates(silent=False)
