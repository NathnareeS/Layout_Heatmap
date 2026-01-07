"""
Combined Layout Application - Heatmap Generator & Text Labeler
Author: AI Assistant
Description: Unified application combining store layout heatmap generation and text labeling
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from typing import Optional, List

# Import both application classes
from layout_heatmap import LayoutHeatmapApp
from layout_text_labeler import LayoutTextLabeler

# Import project management
from database import Database

# Import version and updater
from version import __version__, get_version_string
from updater import check_for_updates_on_startup, manual_update_check


class CombinedLayoutApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Layout Tools - Heatmap Generator & Text Labeler v{__version__}")
        self.root.geometry("800x600")
        
        # Center window on screen
        self.center_window(800, 600)
        
        # Project management
        self.db = Database()
        self.current_project_id: Optional[int] = None
        self.current_project_name: Optional[str] = None
        
        # Shared state between Heatmap Generator and Text Labeler
        self.current_pdf_path: Optional[str] = None
        self.shared_shapes: List = []  # Shared shape data
        self.shared_json_path: Optional[str] = None  # Shared shapes file path
        self.shape_name_counter = 0  # For auto-generating shape names
        
        # Initialize with project selection screen
        self.show_project_selection()
        
        # Check for updates on startup (runs in background)
        check_for_updates_on_startup(self.root)
    
    def center_window(self, width, height):
        """Center window on screen"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def show_project_selection(self):
        """Show project selection UI in the main window"""
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Set window background to a modern gradient-like color
        self.root.configure(bg="#f5f7fa")
        
        # Create main container with modern styling
        main_frame = tk.Frame(self.root, bg="#f5f7fa")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        # Header section with modern design
        header_frame = tk.Frame(main_frame, bg="#f5f7fa")
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        # Title with modern font and color
        title_label = tk.Label(
            header_frame,
            text="Layout Heatmap",
            font=("Segoe UI", 32, "bold"),
            fg="#1a1a2e",
            bg="#f5f7fa"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            header_frame,
            text="Professional Layout Analysis & Text Labeling Tool",
            font=("Segoe UI", 11),
            fg="#6c757d",
            bg="#f5f7fa"
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Card container for projects
        card_frame = tk.Frame(main_frame, bg="white", relief=tk.FLAT, bd=0)
        card_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Add subtle shadow effect with multiple frames
        shadow_frame = tk.Frame(main_frame, bg="#e0e0e0")
        shadow_frame.place(in_=card_frame, x=2, y=2, relwidth=1, relheight=1)
        card_frame.lift()
        
        # Projects header inside card
        card_header = tk.Frame(card_frame, bg="white")
        card_header.pack(fill=tk.X, padx=25, pady=(20, 15))
        
        projects_label = tk.Label(
            card_header, 
            text="Your Projects",
            font=("Segoe UI", 16, "bold"),
            fg="#1a1a2e",
            bg="white"
        )
        projects_label.pack(anchor=tk.W)
        
        # Projects listbox with modern styling
        list_container = tk.Frame(card_frame, bg="white")
        list_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 20))
        
        scrollbar = tk.Scrollbar(list_container, width=12)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        self.projects_listbox = tk.Listbox(
            list_container,
            yscrollcommand=scrollbar.set,
            font=("Segoe UI", 11),
            height=10,
            selectmode=tk.SINGLE,
            bg="#fafbfc",
            fg="#1a1a2e",
            selectbackground="#2196F3",
            selectforeground="white",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground="#e1e4e8",
            highlightcolor="#2196F3",
            activestyle="none"
        )
        self.projects_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.projects_listbox.yview)
        
        # Bind double-click to open project
        self.projects_listbox.bind("<Double-Button-1>", lambda e: self.open_selected_project())
        
        # Load projects
        self.load_projects_list()
        
        # Modern action buttons
        buttons_frame = tk.Frame(main_frame, bg="#f5f7fa")
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Button style helper with rounded appearance
        def create_modern_button(parent, text, command, bg_color, hover_color):
            # Create container frame for rounded effect
            btn_container = tk.Frame(parent, bg=bg_color, highlightthickness=0)
            
            btn = tk.Label(
                btn_container,
                text=text,
                bg=bg_color,
                fg="white",
                font=("Segoe UI", 11, "bold"),
                padx=30,
                pady=15,
                cursor="hand2"
            )
            btn.pack(padx=2, pady=2)
            
            # Make it clickable
            def on_click(e):
                command()
            
            btn.bind("<Button-1>", on_click)
            btn_container.bind("<Button-1>", on_click)
            
            # Hover effect
            def on_enter(e):
                btn.config(bg=hover_color)
                btn_container.config(bg=hover_color)
            
            def on_leave(e):
                btn.config(bg=bg_color)
                btn_container.config(bg=bg_color)
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            btn_container.bind("<Enter>", on_enter)
            btn_container.bind("<Leave>", on_leave)
            
            return btn_container
        
        # New Project button (vibrant green)
        new_btn = create_modern_button(
            buttons_frame,
            "➕  New Project",
            self.create_new_project,
            "#10b981",  # emerald-500
            "#059669"   # emerald-600
        )
        new_btn.pack(side=tk.LEFT, padx=(0, 12))
        
        # Open Project button (vibrant blue)
        open_btn = create_modern_button(
            buttons_frame,
            "📂  Open Project",
            self.open_selected_project,
            "#3b82f6",  # blue-500
            "#2563eb"   # blue-600
        )
        open_btn.pack(side=tk.LEFT, padx=(0, 12))
        
        # Rename Project button (vibrant orange)
        rename_btn = create_modern_button(
            buttons_frame,
            "✏️  Rename",
            self.rename_selected_project,
            "#f97316",  # orange-500
            "#ea580c"   # orange-600
        )
        rename_btn.pack(side=tk.LEFT, padx=(0, 12))
        
        # Delete Project button (vibrant red)
        delete_btn = create_modern_button(
            buttons_frame,
            "🗑️  Delete",
            self.delete_selected_project,
            "#ef4444",  # red-500
            "#dc2626"   # red-600
        )
        delete_btn.pack(side=tk.LEFT)

    
    def load_projects_list(self):
        """Load all projects into the listbox"""
        self.projects_listbox.delete(0, tk.END)
        self.projects = self.db.get_all_projects()
        
        if not self.projects:
            self.projects_listbox.insert(tk.END, "No projects found. Create a new project to get started!")
            self.projects_listbox.config(fg="gray")
        else:
            self.projects_listbox.config(fg="black")
            for project in self.projects:
                # Format: "Project Name (Last modified: YYYY-MM-DD)"
                last_modified = project['last_modified'].split('T')[0]  # Get date part
                display_text = f"{project['name']} (Last modified: {last_modified})"
                self.projects_listbox.insert(tk.END, display_text)
    
    def create_new_project(self):
        """Create a new project"""
        from tkinter import simpledialog
        
        # Ask for project name
        name = simpledialog.askstring(
            "New Project",
            "Enter project name:",
            parent=self.root
        )
        
        if name:
            name = name.strip()
            if not name:
                messagebox.showwarning("Warning", "Project name cannot be empty")
                return
            
            try:
                # Create project in database
                import sqlite3
                project_id = self.db.create_project(name)
                self.current_project_id = project_id
                self.current_project_name = name
                
                # Switch to main UI
                self.root.geometry("1400x900")
                self.center_window(1400, 900)
                self.setup_ui()
                
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", f"Project '{name}' already exists")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create project: {str(e)}")
    
    def open_selected_project(self):
        """Open the selected project"""
        selection = self.projects_listbox.curselection()
        
        if not selection:
            messagebox.showwarning("Warning", "Please select a project to open")
            return
        
        if not self.projects:
            messagebox.showwarning("Warning", "No projects available")
            return
        
        project_index = selection[0]
        project = self.projects[project_index]
        
        self.current_project_id = project['id']
        self.current_project_name = project['name']
        
        # Switch to main UI
        self.root.geometry("1400x900")
        self.center_window(1400, 900)
        self.setup_ui()
        
        # Load project data
        self.load_project()
    
    def delete_selected_project(self):
        """Delete the selected project"""
        selection = self.projects_listbox.curselection()
        
        if not selection:
            messagebox.showwarning("Warning", "Please select a project to delete")
            return
        
        if not self.projects:
            return
        
        project_index = selection[0]
        project = self.projects[project_index]
        
        # Confirm deletion
        response = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete project '{project['name']}'?\n\n"
            "This will delete all labels, variables, and settings.\n"
            "This action cannot be undone!"
        )
        
        if response:
            try:
                self.db.delete_project(project['id'])
                messagebox.showinfo("Success", f"Project '{project['name']}' deleted")
                self.load_projects_list()  # Refresh list
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete project: {str(e)}")
    
    def rename_selected_project(self):
        """Rename the selected project"""
        selection = self.projects_listbox.curselection()
        
        if not selection:
            messagebox.showwarning("Warning", "Please select a project to rename")
            return
        
        if not self.projects:
            return
        
        project_index = selection[0]
        project = self.projects[project_index]
        old_name = project['name']
        
        # Show input dialog for new name
        from tkinter import simpledialog
        new_name = simpledialog.askstring(
            "Rename Project",
            f"Enter new name for project '{old_name}':",
            initialvalue=old_name
        )
        
        if new_name is None:  # User cancelled
            return
        
        new_name = new_name.strip()
        
        # Validate new name
        if not new_name:
            messagebox.showwarning("Warning", "Project name cannot be empty")
            return
        
        if new_name == old_name:
            return  # No change
        
        # Check for duplicate names
        existing_names = [p['name'] for p in self.projects if p['id'] != project['id']]
        if new_name in existing_names:
            messagebox.showwarning("Warning", f"A project named '{new_name}' already exists")
            return
        
        try:
            self.db.rename_project(project['id'], new_name)
            messagebox.showinfo("Success", f"Project renamed from '{old_name}' to '{new_name}'")
            self.load_projects_list()  # Refresh list
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename project: {str(e)}")
    
    def open_project_dialog(self):
        """Show dialog to select and open a project"""
        # Create a simple dialog to select from existing projects
        dialog = tk.Toplevel(self.root)
        dialog.title("Open Project")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"400x300+{x}+{y}")
        
        tk.Label(dialog, text="Select a project to open:", font=("Segoe UI", 12, "bold")).pack(pady=10)
        
        # Listbox for projects
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        projects_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Segoe UI", 10))
        projects_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=projects_list.yview)
        
        # Load projects
        projects = self.db.get_all_projects()
        for project in projects:
            last_modified = project['last_modified'].split('T')[0]
            projects_list.insert(tk.END, f"{project['name']} (Modified: {last_modified})")
        
        def on_open():
            selection = projects_list.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a project")
                return
            
            project = projects[selection[0]]
            self.current_project_id = project['id']
            self.current_project_name = project['name']
            
            dialog.destroy()
            
            # Reload the UI with the new project
            self.setup_ui()
            self.load_project()
        
        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Open", command=on_open, bg="#10b981", fg="white", 
                 font=("Segoe UI", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, 
                 font=("Segoe UI", 10), padx=20, pady=5).pack(side=tk.LEFT, padx=5)
    
    def close_project(self):
        """Close current project and return to project selection"""
        if self.current_project_id:
            response = messagebox.askyesnocancel(
                "Close Project",
                f"Do you want to save '{self.current_project_name}' before closing?\n\n"
                "Yes = Save and close\n"
                "No = Close without saving\n"
                "Cancel = Don't close"
            )
            
            if response is None:  # Cancel
                return
            elif response:  # Yes - Save
                self.save_project()
        
        # Reset project state
        self.current_project_id = None
        self.current_project_name = None
        self.shared_shapes.clear()
        self.shared_json_path = None
        
        # Return to project selection
        self.root.geometry("800x600")
        self.center_window(800, 600)
        self.show_project_selection()

    
    def setup_ui(self):
        """Setup the main user interface with tabs"""
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Menu bar
        self.setup_menu_bar()
        
        # Modern header bar with project info
        header_bar = tk.Frame(self.root, bg="#2c3e50", height=50)
        header_bar.pack(fill=tk.X, side=tk.TOP)
        header_bar.pack_propagate(False)
        
        # Project name on the left
        project_label = tk.Label(
            header_bar,
            text=f"📋 {self.current_project_name}" if self.current_project_name else "📁 Project",
            font=("Segoe UI", 14, "bold"),
            fg="white",
            bg="#2c3e50"
        )
        project_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        # Buttons on the right
        btn_container = tk.Frame(header_bar, bg="#2c3e50")
        btn_container.pack(side=tk.RIGHT, padx=15, pady=8)
        
        # Helper function for modern buttons
        def create_header_button(text, command, bg_color, hover_color, icon=""):
            btn = tk.Button(
                btn_container,
                text=f"{icon} {text}" if icon else text,
                command=command,
                bg=bg_color,
                fg="white",
                font=("Segoe UI", 9, "bold"),
                padx=12,
                pady=6,
                relief=tk.FLAT,
                bd=0,
                cursor="hand2",
                activebackground=hover_color,
                activeforeground="white"
            )
            
            def on_enter(e):
                btn.config(bg=hover_color)
            def on_leave(e):
                btn.config(bg=bg_color)
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            
            return btn
        
        # Save button (green)
        save_btn = create_header_button("💾 Save", self.save_project, "#10b981", "#059669")
        save_btn.pack(side=tk.LEFT, padx=2)
        
        # New button (blue)
        new_btn = create_header_button("📁 New", self.create_new_project, "#3498db", "#2980b9")
        new_btn.pack(side=tk.LEFT, padx=2)
        
        # Open button (purple)
        open_btn = create_header_button("📂 Open", self.open_project_dialog, "#8b5cf6", "#7c3aed")
        open_btn.pack(side=tk.LEFT, padx=2)
        
        # Close button (gray)
        close_btn = create_header_button("✕ Close", self.close_project, "#6c757d", "#5a6268")
        close_btn.pack(side=tk.LEFT, padx=2)
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Heatmap Generator
        self.heatmap_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.heatmap_frame, text="🎨 Heatmap Generator")
        
        # Tab 2: Text Labeler
        self.labeler_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.labeler_frame, text="📝 Text Labeler")
        
        # Initialize both applications
        self.heatmap_app = LayoutHeatmapApp(self.heatmap_frame)
        self.labeler_app = LayoutTextLabeler(self.labeler_frame)
        
        # Connect shapes to shared data
        self.heatmap_app.shapes = self.shared_shapes
        self.labeler_app.shapes = self.shared_shapes
        
        # Set up callback for shape deletion to also delete labels
        self.heatmap_app.on_shape_deleted = self.on_shape_deleted_callback
        
        # Set up callback for PDF loading to sync between apps
        self.heatmap_app.on_pdf_loaded = self.on_pdf_loaded_callback
        
        # Bind tab change event for auto-sync
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Status bar
        self.setup_status_bar()
    
    def on_shape_deleted_callback(self, shape_index):
        """Called when a shape is deleted in heatmap app - delete associated labels"""
        try:
            # Remove all labels associated with this shape
            labels_to_remove = [label for label in self.labeler_app.labels 
                               if label.shape_index == shape_index]
            
            for label in labels_to_remove:
                self.labeler_app.labels.remove(label)
            
            # Update shape indices for remaining labels (shift down if needed)
            for label in self.labeler_app.labels:
                if label.shape_index > shape_index:
                    label.shape_index -= 1
            
            # Redraw canvas to reflect changes
            if hasattr(self.labeler_app, 'display_canvas'):
                self.labeler_app.display_canvas()
        except Exception as e:
            # If there's an error, just print it and continue
            print(f"Error deleting labels for shape {shape_index}: {e}")
    
    def on_pdf_loaded_callback(self, pdf_path):
        """Called when PDF is loaded in heatmap app - sync to labeler app"""
        try:
            print(f"PDF loaded in Heatmap Generator: {pdf_path}")
            print("Syncing PDF to Text Labeler...")
            
            # Load PDF into Text Labeler
            self.labeler_app.load_pdf_internal(pdf_path)
            
            # Update status
            import os
            filename = os.path.basename(pdf_path)
            self.status_var.set(f"PDF synced to both apps: {filename}")
            print(f"✓ PDF successfully synced to Text Labeler")
            
        except Exception as e:
            print(f"Error syncing PDF to Text Labeler: {e}")
            import traceback
            traceback.print_exc()
    
    def setup_menu_bar(self):
        """Setup the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Project menu
        project_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Project", menu=project_menu)
        
        project_menu.add_command(label="📁 New Project", command=self.create_new_project)
        project_menu.add_command(label="📂 Open Project", command=self.open_project_dialog)
        project_menu.add_separator()
        project_menu.add_command(label="🔙 Close Project", command=self.close_project)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)

        
        file_menu.add_command(label="Load PDF (Shared)", command=self.load_shared_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="💾 Save Project (Ctrl+S)", command=self.save_project, accelerator="Ctrl+S")
        file_menu.add_command(label="📂 Load Project", command=self.load_project)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Bind Ctrl+S to save
        self.root.bind('<Control-s>', lambda e: self.save_project())
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        help_menu.add_command(label="🔄 Check for Updates", command=lambda: manual_update_check(self.root))
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_status_bar(self):
        """Setup the status bar"""
        project_text = f"Project: {self.current_project_name}" if self.current_project_name else "No project"
        self.status_var = tk.StringVar(value=f"{project_text} - Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def generate_shape_name(self, shape_type="Shape"):
        """Generate auto-name for shapes"""
        self.shape_name_counter += 1
        return f"{shape_type} {self.shape_name_counter}"
    
    def sync_shapes_to_labeler(self):
        """Sync shapes from Heatmap Generator to Text Labeler"""
        if not hasattr(self, 'labeler_app'):
            return
        
        # Ensure all shapes have names
        for i, shape in enumerate(self.shared_shapes):
            if "name" not in shape or not shape["name"]:
                shape["name"] = self.generate_shape_name(shape.get("type", "Shape").capitalize())
        
        # Update labeler's shapes reference
        self.labeler_app.shapes = self.shared_shapes
        self.labeler_app.current_json_path = self.shared_json_path
        self.labeler_app.update_shape_list()
        self.labeler_app.display_canvas()
        
        self.status_var.set(f"Synced {len(self.shared_shapes)} shapes to Text Labeler")
    
    def sync_shapes_to_heatmap(self):
        """Sync shapes from Text Labeler to Heatmap Generator"""
        if not hasattr(self, 'heatmap_app'):
            return
        
        # Update heatmap's shapes reference
        self.heatmap_app.shapes = self.shared_shapes
        self.heatmap_app.redraw_shapes()
        
        self.status_var.set(f"Synced {len(self.shared_shapes)} shapes to Heatmap Generator")
    
    def on_tab_changed(self, event):
        """Handle tab change to sync shapes"""
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 0:  # Heatmap Generator tab
            # Sync from labeler to heatmap
            if hasattr(self, 'labeler_app') and self.labeler_app.shapes:
                # Update shared shapes from labeler
                self.shared_shapes = self.labeler_app.shapes
                # Make heatmap reference the same list
                self.heatmap_app.shapes = self.shared_shapes
                self.heatmap_app.redraw_shapes()
                self.heatmap_app.update_shape_list()
        elif current_tab == 1:  # Text Labeler tab
            # Sync from heatmap to labeler
            if hasattr(self, 'heatmap_app') and self.heatmap_app.shapes:
                # Update shared shapes from heatmap
                self.shared_shapes = self.heatmap_app.shapes
                # Make labeler reference the same list
                self.labeler_app.shapes = self.shared_shapes
                self.labeler_app.update_shape_list()
                self.labeler_app.display_canvas()
    
    def load_shared_pdf(self):
        """Load a PDF file and share it with both applications"""
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if file_path:
            self.current_pdf_path = file_path
            filename = os.path.basename(file_path)
            
            # Ask which app to load into
            response = messagebox.askyesnocancel(
                "Load PDF",
                f"Load '{filename}' into:\n\n"
                "Yes = Heatmap Generator\n"
                "No = Text Labeler\n"
                "Cancel = Both"
            )
            
            if response is None:
                # PRIORITY 1: Load into both applications
                self.heatmap_app.current_pdf_path = file_path
                self.heatmap_app.file_info.set(f"Selected: {filename}")
                self.heatmap_app.process_btn.config(state="normal")
                self.heatmap_app.process_pdf()
                
                self.labeler_app.current_pdf_path = file_path
                self.labeler_app.load_pdf_internal(file_path)
                
                self.status_var.set(f"PDF loaded into both applications: {filename}")
                
            elif response is True:
                # PRIORITY 2: Load into Heatmap Generator
                self.heatmap_app.current_pdf_path = file_path
                self.heatmap_app.file_info.set(f"Selected: {filename}")
                self.heatmap_app.process_btn.config(state="normal")
                self.heatmap_app.process_pdf()
                self.notebook.select(0)  # Switch to heatmap tab
                self.status_var.set(f"PDF loaded into Heatmap Generator: {filename}")
                
            elif response is False:
                # PRIORITY 3: Load into Text Labeler
                self.labeler_app.current_pdf_path = file_path
                self.labeler_app.load_pdf_internal(file_path)
                self.notebook.select(1)  # Switch to labeler tab
                self.status_var.set(f"PDF loaded into Text Labeler: {filename}")
    
    def save_project(self):
        """Save current project to database"""
        if not self.current_project_id:
            messagebox.showwarning("Warning", "No project loaded")
            return
        
        try:
            print(f"Saving project: {self.current_project_name} (ID: {self.current_project_id})")
            
            # Update project paths - check both apps for PDF path
            pdf_path = self.labeler_app.current_pdf_path or self.heatmap_app.current_pdf_path
            print(f"PDF path: {pdf_path}")
            if pdf_path:
                self.db.update_project(self.current_project_id, pdf_path=pdf_path)
                print("✓ PDF path saved")
            
            # Save shapes to JSON file
            # Use shared_json_path or labeler's path (heatmap doesn't have current_json_path)
            json_path = self.shared_json_path or self.labeler_app.current_json_path
            print(f"JSON path: {json_path}")
            print(f"Number of shapes: {len(self.shared_shapes)}")
            
            # If we have shapes but no JSON path, auto-generate one
            if self.shared_shapes and not json_path:
                # Auto-generate a JSON filename based on project name
                import os
                script_dir = os.path.dirname(os.path.abspath(__file__))
                suggested_name = f"{self.current_project_name.replace(' ', '_')}_shapes.json"
                json_path = os.path.join(script_dir, suggested_name)
                
                self.shared_json_path = json_path
                self.labeler_app.current_json_path = json_path
                print(f"Auto-generated JSON path: {json_path}")
            
            if json_path and self.shared_shapes:
                import json
                # Prepare shapes data for saving (exclude canvas_id and selection_id)
                shapes_to_save = []
                for shape in self.shared_shapes:
                    shape_data = {
                        "type": shape["type"],
                        "coordinates": shape["coordinates"],
                        "color": shape["color"],
                        "stipple": shape.get("stipple", ""),
                        "name": shape.get("name", "")  # Include the name!
                    }
                    shapes_to_save.append(shape_data)
                
                print(f"Prepared {len(shapes_to_save)} shapes for saving")
                
                # Save to JSON file
                layout_data = {
                    "pdf_file": pdf_path,
                    "shapes": shapes_to_save
                }
                
                with open(json_path, 'w') as f:
                    json.dump(layout_data, f, indent=2)
                
                print(f"✓ Shapes saved to {json_path}")
                
                # Update shapes path in database
                self.db.update_project(self.current_project_id, shapes_path=json_path)
                print("✓ Shapes path saved to database")
            
            # Save variables
            print(f"Number of variables: {len(self.labeler_app.variables)}")
            if self.labeler_app.variables:
                self.db.save_variables(self.current_project_id, self.labeler_app.variables)
                print("✓ Variables saved")
            
            # Save labels
            print(f"Number of labels: {len(self.labeler_app.labels)}")
            if self.labeler_app.labels:
                self.db.save_labels(self.current_project_id, self.labeler_app.labels)
                print("✓ Labels saved")
            
            messagebox.showinfo("Success", f"Project '{self.current_project_name}' saved successfully!")
            self.status_var.set(f"Project: {self.current_project_name} - Saved")
            print("="*60)
            print("PROJECT SAVED SUCCESSFULLY")
            print("="*60)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print("="*60)
            print("ERROR SAVING PROJECT:")
            print("="*60)
            print(error_details)
            print("="*60)
            messagebox.showerror("Error", f"Failed to save project: {str(e)}\n\nCheck console for details.")
    
    def load_project(self):
        """Load project from database"""
        if not self.current_project_id:
            return
        
        try:
            project = self.db.get_project(self.current_project_id)
            if not project:
                return
            
            # Load shapes FIRST (before PDF processing)
            if project['shapes_path'] and os.path.exists(project['shapes_path']):
                import json
                with open(project['shapes_path'], 'r') as f:
                    data = json.load(f)
                
                # Load shapes into shared data
                self.shared_shapes = data.get("shapes", [])
                self.shared_json_path = project['shapes_path']
                
                # Ensure all shapes have names and update counter
                max_shape_num = 0
                for i, shape in enumerate(self.shared_shapes):
                    if "name" not in shape or not shape["name"]:
                        # Generate name based on shape type
                        shape_type = shape.get("type", "Shape").capitalize()
                        self.shape_name_counter += 1
                        shape["name"] = f"{shape_type} {self.shape_name_counter}"
                        max_shape_num = max(max_shape_num, self.shape_name_counter)
                    else:
                        # Extract number from existing name to update counter
                        import re
                        match = re.search(r'(\d+)$', shape["name"])
                        if match:
                            num = int(match.group(1))
                            max_shape_num = max(max_shape_num, num)
                
                # Update counter to avoid duplicates
                self.shape_name_counter = max_shape_num
                
                # Assign shapes to both apps BEFORE loading PDF
                self.labeler_app.current_json_path = project['shapes_path']
                self.labeler_app.shapes = self.shared_shapes
                
                # Heatmap app doesn't have current_json_path, only assign shapes
                self.heatmap_app.shapes = self.shared_shapes
            
            # Load PDF into both apps (this will trigger redraw_shapes automatically)
            if project['pdf_path'] and os.path.exists(project['pdf_path']):
                pdf_path = project['pdf_path']
                filename = os.path.basename(pdf_path)
                
                # Load into Text Labeler
                self.labeler_app.load_pdf_internal(pdf_path)
                
                # Load into Heatmap Generator (process_pdf will call display_pdf_image which calls redraw_shapes)
                self.heatmap_app.current_pdf_path = pdf_path
                self.heatmap_app.file_info.set(f"Selected: {filename}")
                self.heatmap_app.process_btn.config(state="normal")
                self.heatmap_app.process_pdf()
            
            # Update UI elements after everything is loaded
            if self.shared_shapes:
                self.labeler_app.update_shape_list()
                self.labeler_app.display_canvas()
                self.heatmap_app.update_shape_list()
            
            # Load variables
            from layout_text_labeler import Variable, ColorRule
            variables_data = self.db.load_variables(self.current_project_id)
            self.labeler_app.variables = []
            for var_dict in variables_data:
                var = Variable(var_dict['name'])
                # Load text formatting properties
                var.text_color = var_dict.get('text_color')
                var.bg_color = var_dict.get('bg_color')
                var.text_size = var_dict.get('text_size')
                # Load rules
                for rule_dict in var_dict['rules']:
                    var.add_rule(rule_dict['operator'], rule_dict['threshold'], rule_dict['color'])
                self.labeler_app.variables.append(var)
            self.labeler_app.update_variables_summary()
            
            # Load labels
            from layout_text_labeler import TextLabel
            labels_data = self.db.load_labels(self.current_project_id)
            self.labeler_app.labels = []
            for label_dict in labels_data:
                label = TextLabel(
                    label_dict['shape_index'],
                    (label_dict['position_x'], label_dict['position_y'])
                )
                label.has_leader = bool(label_dict['has_leader'])
                label.leader_points = label_dict['leader_points']
                
                # Load label lines
                label.text_lines = []
                label.line_font_sizes = []
                label.line_font_colors = []
                label.line_bg_colors = []
                label.line_variables = []
                label.line_is_sales = []
                label.line_unit_metric = []
                
                for line_dict in label_dict['lines']:
                    label.text_lines.append(line_dict['text'])
                    label.line_font_sizes.append(line_dict['font_size'])
                    label.line_font_colors.append(line_dict['font_color'])
                    label.line_bg_colors.append(line_dict['bg_color'])
                    label.line_variables.append(line_dict['variable_name'])
                    label.line_is_sales.append(bool(line_dict.get('is_sales', 0)))
                    label.line_unit_metric.append(line_dict.get('unit_metric', 'None'))

                
                self.labeler_app.labels.append(label)
            
            # Clean up any orphaned labels (labels that reference non-existent shapes)
            self.labeler_app.clean_orphaned_labels()
            
            self.labeler_app.display_canvas()
            self.labeler_app.update_shape_list()
            
            messagebox.showinfo("Success", f"Project '{self.current_project_name}' loaded successfully!")
            self.status_var.set(f"Project: {self.current_project_name} - Loaded")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print("="*60)
            print("ERROR LOADING PROJECT:")
            print("="*60)
            print(error_details)
            print("="*60)
            messagebox.showerror("Error", f"Failed to load project: {str(e)}\n\nCheck console for details.")
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About",
            "Combined Layout Application v2.0\n\n"
            "Features:\n"
            "• Heatmap Generator - Create store layout heatmaps\n"
            "• Text Labeler - Add text labels to shapes\n"
            "• Project Management - Save and load projects\n\n"
            "Author: AI Assistant"
        )


def main():
    root = tk.Tk()
    app = CombinedLayoutApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
