"""
Layout Text Labeler - Add text labels to PDF layouts with shapes
Author: AI Assistant
Description: A tool for adding multi-line text labels to shapes defined in JSON files,
             with automatic leader lines when text is positioned outside shapes.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, font as tkfont
from tkinter.scrolledtext import ScrolledText
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw, ImageFont
import numpy as np
import json
import os
import io
from typing import Dict, List, Tuple, Optional
import math
import re
import pandas as pd  # For Excel/CSV import



class ColorRule:
    """Represents a conditional coloring rule"""
    def __init__(self, operator: str = ">", threshold: float = 0, color: str = "#FF0000"):
        self.operator = operator  # ">", ">=", "<", "<=", "==", "!="
        self.threshold = threshold
        self.color = color
    
    def evaluate(self, value: float) -> bool:
        """Check if value meets this rule's condition"""
        if self.operator == ">":
            return value > self.threshold
        elif self.operator == ">=":
            return value >= self.threshold
        elif self.operator == "<":
            return value < self.threshold
        elif self.operator == "<=":
            return value <= self.threshold
        elif self.operator == "==":
            return value == self.threshold
        elif self.operator == "!=":
            return value != self.threshold
        return False


class Variable:
    """Represents a named variable with conditional coloring rules"""
    def __init__(self, name: str):
        self.name = name
        self.rules: List[ColorRule] = []
        # Text formatting properties (apply to labels with this variable)
        self.text_color: Optional[str] = None
        self.bg_color: Optional[str] = None
        self.text_size: Optional[int] = None
        # Auto Sales/Area settings
        self.auto_enable_sales: bool = False  # Auto-check Sales/Area when this variable is selected
        self.default_unit: str = "None"  # Default unit metric to use

    
    def add_rule(self, operator: str, threshold: float, color: str):
        """Add a color rule to this variable"""
        rule = ColorRule(operator, threshold, color)
        self.rules.append(rule)
    
    def evaluate(self, value: float) -> Optional[str]:
        """Evaluate rules and return color for the most specific matching rule
        
        Algorithm: Find all matching rules, then pick the one with threshold
        closest to the value (most specific/restrictive condition wins).
        
        Example: If value=6000 and rules are:
        - x >= 2000 (matches, distance = 4000)
        - x > 5000 (matches, distance = 1000) <- WINS (closest threshold)
        """
        matching_rules = []
        
        # Find all rules that match the value
        for rule in self.rules:
            if rule.evaluate(value):
                # Calculate "distance" from threshold to value
                # This represents how specific/restrictive the rule is
                distance = abs(value - rule.threshold)
                matching_rules.append((rule, distance))
        
        if not matching_rules:
            return None
        
        # Sort by distance (ascending) - closest threshold wins
        matching_rules.sort(key=lambda x: x[1])
        
        # Return color of the most specific rule (smallest distance)
        return matching_rules[0][0].color



class TextLabel:
    """Represents a text label associated with a shape"""
    def __init__(self, shape_index: int, position: Tuple[float, float]):
        self.shape_index = shape_index
        self.text_lines = [""]
        self.position = position  # (x, y) in image coordinates
        # Per-line formatting (arrays matching text_lines length)
        self.line_font_sizes = [12]  # One font size per line
        self.line_font_colors = ["#000000"]  # One text color per line
        self.line_bg_colors = ["#FFFFFF"]  # One background color per line
        self.line_variables = ["None"]  # Variable assignment per line
        self.line_is_sales = [False]  # Sales checkbox state per line
        self.line_unit_metric = ["None"]  # Unit metric per line (m², m³, etc.)
        self.has_leader = False
        self.leader_points = []  # [[x1, y1], [x2, y2]]
        # Leader line customization
        self.leader_style = "solid"  # solid, dashed, dotted
        self.leader_width = 2  # Line thickness
        self.leader_color = "#666666"  # Line color
        self.canvas_text_ids = []  # Canvas IDs for text lines
        self.canvas_leader_id = None  # Canvas ID for leader line
        self.canvas_box_id = None  # Canvas ID for text background box
        self.dragging = False
        self.drag_offset = (0, 0)
        # Custom text feature
        self.use_custom_text = False  # If False, use shape name; if True, use custom text


class LayoutTextLabeler:
    def __init__(self, parent):
        # Parent can be either root window or a frame
        self.root = parent
        
        # Only set title and geometry if parent is a Tk root window
        if isinstance(parent, tk.Tk):
            self.root.title("Layout Text Labeler - v2.0 (Zoom-Independent Text)")
            self.root.geometry("1400x900")
        
        # Application state
        self.current_pdf_path: Optional[str] = None
        self.current_json_path: Optional[str] = None
        self.pdf_image: Optional[Image.Image] = None
        self.canvas_image: Optional[ImageTk.PhotoImage] = None
        self.shapes: List[Dict] = []
        self.labels: List[TextLabel] = []
        self.selected_label: Optional[TextLabel] = None
        
        # Zoom and pan variables
        self.zoom_factor = 1.0
        self.panning = False
        self.original_image_size = None
        
        # UI state
        self.text_entry_widgets = []  # List of text entry widgets
        self.selected_shape_index = None
        
        # Conditional coloring state
        self.variables: List[Variable] = []  # Defined variables
        self.color_rules: List[ColorRule] = []  # Legacy: for backward compatibility
        self.value_line_index = 0  # Legacy: Which text line contains the numeric value
        self.cond_enabled_var = tk.BooleanVar(value=True)  # Legacy: for backward compatibility, always enabled now
        self.original_shape_colors = {}  # Backup of original colors
        
        # Import/Remap state
        self.last_imported_df = None  # Store last imported Excel/CSV data
        self.current_mapping = {}  # Store current shape-to-row mapping {shape_idx: excel_row_idx}
        
        # Undo functionality
        self.undo_stack = []  # Stack to store previous states for undo
        self.max_undo_steps = 20  # Maximum number of undo steps to keep
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the main user interface"""
        # Set root background
        if hasattr(self.root, 'configure'):
            try:
                self.root.configure(bg="#f5f7fa")
            except:
                pass
        
        # Main container
        main_frame = tk.Frame(self.root, bg="#f5f7fa")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top toolbar
        self.setup_toolbar(main_frame)
        
        # Content area
        content_frame = tk.Frame(main_frame, bg="#f5f7fa")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Left panel (shape list and text editor)
        self.setup_left_panel(content_frame)
        
        # Right panel (canvas)
        self.setup_canvas_area(content_frame)
        
        # Status bar
        self.setup_status_bar()
    
    def setup_toolbar(self, parent):
        """Setup the toolbar with file operations"""
        toolbar = tk.Frame(parent, bg="#ffffff", relief=tk.FLAT, bd=0)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # Add subtle shadow
        shadow = tk.Frame(parent, bg="#d0d0d0", height=2)
        shadow.place(in_=toolbar, x=0, rely=1, relwidth=1)
        toolbar.lift()
        
        # Title label on the left
        title_label = tk.Label(
            toolbar,
            text="📝 Text Labeler",
            font=("Segoe UI", 14, "bold"),
            fg="#2c3e50",
            bg="#ffffff"
        )
        title_label.pack(side=tk.LEFT, padx=15, pady=8)
        
        # Separator
        sep1 = tk.Frame(toolbar, bg="#bdc3c7", width=2)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        
        # Modern button style helper
        def create_toolbar_button(text, command, icon=""):
            btn = tk.Button(
                toolbar,
                text=f"{icon} {text}" if icon else text,
                command=command,
                bg="#3498db",
                fg="white",
                font=("Segoe UI", 9, "bold"),
                relief=tk.FLAT,
                bd=0,
                padx=12,
                pady=8,
                cursor="hand2",
                activebackground="#2980b9",
                activeforeground="white"
            )
            
            def on_enter(e):
                btn.config(bg="#2980b9")
            def on_leave(e):
                btn.config(bg="#3498db")
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            
            return btn
        
        # File operations
        create_toolbar_button("💾 Save", self.save_labels).pack(side=tk.LEFT, padx=2, pady=8)
        create_toolbar_button("📂 Load", self.load_labels).pack(side=tk.LEFT, padx=2, pady=8)
        create_toolbar_button("📊 Import Excel/CSV", self.import_excel_csv).pack(side=tk.LEFT, padx=2, pady=8)
        create_toolbar_button("🔄 Remap", self.remap_shapes).pack(side=tk.LEFT, padx=2, pady=8)
        create_toolbar_button("🗑️ Clear", self.clear_all_labels).pack(side=tk.LEFT, padx=2, pady=8)
        
        # Separator
        sep = tk.Frame(toolbar, bg="#bdc3c7", width=2)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        
        create_toolbar_button("🖼️ Export", self.export_image).pack(side=tk.LEFT, padx=2, pady=8)
        
        # File info
        self.file_info_var = tk.StringVar(value="No files loaded")
        info_label = tk.Label(
            toolbar,
            textvariable=self.file_info_var,
            font=("Segoe UI", 9),
            fg="#7f8c8d",
            bg="#ffffff"
        )
        info_label.pack(side=tk.LEFT, padx=15)
    
    def setup_left_panel(self, parent):
        """Setup the left panel with shape list and text editor"""
        # Create a scrollable left panel
        left_panel_container = ttk.Frame(parent, width=450)
        left_panel_container.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_panel_container.pack_propagate(False)
        
        # Create canvas for scrolling
        canvas = tk.Canvas(left_panel_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_panel_container, orient="vertical", command=canvas.yview)
        left_panel = ttk.Frame(canvas)
        
        # Configure canvas scrolling
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas_frame = canvas.create_window((0, 0), window=left_panel, anchor=tk.NW)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Update scroll region when content changes
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Also update the canvas window width to match canvas width
            canvas_width = canvas.winfo_width()
            canvas.itemconfig(canvas_frame, width=canvas_width)
        
        left_panel.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_scroll_region)
        
        # Store references to widgets that should handle their own scrolling
        self.scrollable_widgets = []
        
        # Enable mousewheel scrolling for the main left panel
        # Individual components (shape list, text editor) will handle their own scrolling
        # when the mouse is directly over them
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to canvas and left panel
        canvas.bind("<MouseWheel>", on_mousewheel)
        left_panel.bind("<MouseWheel>", on_mousewheel)
        
        # Recursively bind mousewheel to all child widgets EXCEPT scrollable components
        def bind_mousewheel_to_children(widget):
            # Skip widgets that handle their own scrolling
            if widget in self.scrollable_widgets:
                return
            # Skip Listbox and Canvas widgets (they have their own scrolling)
            if isinstance(widget, (tk.Listbox, tk.Canvas)):
                return
            
            widget.bind("<MouseWheel>", on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_to_children(child)
        
        # Bind after a short delay to ensure all widgets are created
        left_panel.after(100, lambda: bind_mousewheel_to_children(left_panel))
        
        # Shape list
        shape_list_frame = ttk.LabelFrame(left_panel, text="Shapes", padding=10)
        shape_list_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Scrollable listbox for shapes
        list_container = ttk.Frame(shape_list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        shape_scrollbar = ttk.Scrollbar(list_container)
        shape_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.shape_listbox = tk.Listbox(list_container, yscrollcommand=shape_scrollbar.set, 
                                       font=("Arial", 10), height=8)
        self.shape_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        shape_scrollbar.config(command=self.shape_listbox.yview)
        
        # Add mousewheel scrolling for shape listbox
        def on_shape_listbox_mousewheel(event):
            self.shape_listbox.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mousewheel to listbox and container
        self.shape_listbox.bind("<MouseWheel>", on_shape_listbox_mousewheel)
        list_container.bind("<MouseWheel>", on_shape_listbox_mousewheel)
        
        self.shape_listbox.bind("<<ListboxSelect>>", self.on_shape_select)
        
        # ===== DEFAULT SETTINGS SECTION =====
        defaults_frame = ttk.LabelFrame(left_panel, text="⚙️ Default Settings", padding=10)
        defaults_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Default Text Size
        size_row = ttk.Frame(defaults_frame)
        size_row.pack(fill=tk.X, pady=2)
        ttk.Label(size_row, text="Text Size:", width=10).pack(side=tk.LEFT)
        self.default_text_size = tk.IntVar(value=30)
        ttk.Spinbox(size_row, from_=8, to=72, textvariable=self.default_text_size, width=8).pack(side=tk.LEFT, padx=5)
        
        # Default Text Color
        color_row = ttk.Frame(defaults_frame)
        color_row.pack(fill=tk.X, pady=2)
        ttk.Label(color_row, text="Text Color:", width=10).pack(side=tk.LEFT)
        self.default_text_color = tk.StringVar(value="#000000")
        self.default_text_color_btn = tk.Button(color_row, text="⬛", bg="#000000", fg="white",
                                               width=3, relief=tk.RAISED, bd=1,
                                               command=self.pick_default_text_color)
        self.default_text_color_btn.pack(side=tk.LEFT, padx=5)
        
        # Default Background Color
        bg_row = ttk.Frame(defaults_frame)
        bg_row.pack(fill=tk.X, pady=2)
        ttk.Label(bg_row, text="BG Color:", width=10).pack(side=tk.LEFT)
        self.default_bg_color = tk.StringVar(value="#FFFFFF")
        self.default_bg_color_btn = tk.Button(bg_row, text="⬛", bg="#FFFFFF", fg="black",
                                             width=3, relief=tk.RAISED, bd=1,
                                             command=self.pick_default_bg_color)
        self.default_bg_color_btn.pack(side=tk.LEFT, padx=5)
        
        # Default Leader Line Width
        leader_row = ttk.Frame(defaults_frame)
        leader_row.pack(fill=tk.X, pady=2)
        ttk.Label(leader_row, text="Line Width:", width=10).pack(side=tk.LEFT)
        self.default_leader_width = tk.IntVar(value=5)
        ttk.Spinbox(leader_row, from_=1, to=10, textvariable=self.default_leader_width, width=8).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(defaults_frame, text="💡 Applied to new text lines", 
                 font=("Arial", 8), foreground="gray").pack(pady=(5,0))
        
        ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Text editor
        editor_frame = ttk.LabelFrame(left_panel, text="Text Editor", padding=10)
        editor_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Container for both placeholder and scroll frame (only one visible at a time)
        editor_content_frame = ttk.Frame(editor_frame)
        editor_content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Placeholder label for when no shape is selected
        self.editor_placeholder = ttk.Label(
            editor_content_frame,
            text="Select a shape to edit its label",
            font=("Arial", 10, "italic"),
            foreground="gray"
        )
        self.editor_placeholder.pack(pady=20)
        
        # Scrollable text entries container with height limit
        scroll_frame = ttk.Frame(editor_content_frame)
        # Don't pack it yet - will be shown when shape is selected
        
        scroll_canvas = tk.Canvas(scroll_frame, height=300, highlightthickness=0)  # Set max height
        text_scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=scroll_canvas.yview)
        self.text_entries_container = ttk.Frame(scroll_canvas)
        
        scroll_canvas.create_window((0, 0), window=self.text_entries_container, anchor=tk.NW)
        scroll_canvas.configure(yscrollcommand=text_scrollbar.set)
        
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store reference to scroll frame and canvas
        self.editor_scroll_frame = scroll_frame
        self.editor_scroll_canvas = scroll_canvas
        
        # Update scroll region when container changes
        def update_scroll_region(event=None):
            # Update the scroll region to match content
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            # Reset scroll position to top to prevent phantom scrolling
            scroll_canvas.yview_moveto(0)
        
        self.text_entries_container.bind("<Configure>", update_scroll_region)
        
        # Add mousewheel scrolling for text editor
        def on_text_editor_mousewheel(event):
            # Only scroll if content exceeds visible area
            bbox = scroll_canvas.bbox("all")
            if bbox and bbox[3] > scroll_canvas.winfo_height():
                scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mousewheel to scroll canvas and text entries container
        scroll_canvas.bind("<MouseWheel>", on_text_editor_mousewheel)
        self.text_entries_container.bind("<MouseWheel>", on_text_editor_mousewheel)
        scroll_frame.bind("<MouseWheel>", on_text_editor_mousewheel)
        
        # Add text line button
        ttk.Button(editor_frame, text="+ Add Text Line", command=self.add_text_line, width=20).pack(pady=5)
        
        # Action buttons - BELOW everything else
        button_frame = ttk.Frame(editor_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Delete button
        ttk.Button(button_frame, text="Delete Label", command=self.delete_label, width=12).pack(side=tk.LEFT, padx=2)
        
        # Undo button
        self.undo_button = ttk.Button(button_frame, text="↶ Undo", command=self.undo_last_change, width=12, state='disabled')
        self.undo_button.pack(side=tk.LEFT, padx=2)
        
        # Track if changes are pending
        self.changes_pending = False
        
        # Leader Line Settings
        leader_frame = ttk.LabelFrame(left_panel, text="Leader Line Settings", padding=10)
        leader_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Line Style
        style_row = ttk.Frame(leader_frame)
        style_row.pack(fill=tk.X, pady=2)
        ttk.Label(style_row, text="Style:", width=8).pack(side=tk.LEFT)
        self.leader_style_var = tk.StringVar(value="solid")
        style_combo = ttk.Combobox(style_row, textvariable=self.leader_style_var,
                                   values=["solid", "dashed", "dotted"], state="readonly", width=12)
        style_combo.pack(side=tk.LEFT, padx=5)
        style_combo.bind("<<ComboboxSelected>>", lambda e: self.mark_changes_pending())
        
        # Line Width
        width_row = ttk.Frame(leader_frame)
        width_row.pack(fill=tk.X, pady=2)
        ttk.Label(width_row, text="Width:", width=8).pack(side=tk.LEFT)
        self.leader_width_var = tk.IntVar(value=2)
        width_spinner = ttk.Spinbox(width_row, from_=1, to=10, textvariable=self.leader_width_var,
                                    width=10)
        width_spinner.pack(side=tk.LEFT, padx=5)
        self.leader_width_var.trace_add("write", lambda *args: self.mark_changes_pending())
        
        # Line Color
        color_row = ttk.Frame(leader_frame)
        color_row.pack(fill=tk.X, pady=2)
        ttk.Label(color_row, text="Color:", width=8).pack(side=tk.LEFT)
        self.leader_color_var = tk.StringVar(value="#666666")
        self.leader_color_btn = tk.Button(color_row, text="⬛", bg="#666666", fg="white",
                                         width=3, relief=tk.RAISED, bd=1,
                                         command=self.pick_leader_color)
        self.leader_color_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(leader_frame, text="💡 Click 'Apply Changes' to update line", 
                 font=("Arial", 8), foreground="gray").pack(pady=(5,0))
        
        # Zoom controls
        zoom_frame = ttk.LabelFrame(left_panel, text="View Controls", padding=10)
        zoom_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        zoom_btn_frame = ttk.Frame(zoom_frame)
        zoom_btn_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(zoom_btn_frame, text="Zoom In", command=self.zoom_in, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_btn_frame, text="Zoom Out", command=self.zoom_out, width=10).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(zoom_frame, text="Fit to Window", command=self.fit_to_window, width=20).pack(pady=2)
        
        self.zoom_var = tk.StringVar(value="Zoom: 100%")
        ttk.Label(zoom_frame, textvariable=self.zoom_var).pack(pady=2)
        
        # Conditional Coloring Panel
        self.setup_conditional_panel(left_panel)
    
    def setup_canvas_area(self, parent):
        """Setup the canvas area for PDF display"""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Canvas with scrollbars
        canvas_container = ttk.Frame(canvas_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        v_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.HORIZONTAL)
        
        self.canvas = tk.Canvas(
            canvas_container,
            bg="white",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            scrollregion=(0, 0, 1000, 1000)
        )
        
        v_scrollbar.config(command=self.canvas.yview)
        h_scrollbar.config(command=self.canvas.xview)
        
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.pan_motion)
        self.canvas.bind("<ButtonRelease-3>", self.end_pan)
        self.canvas.bind("<MouseWheel>", self.zoom_canvas)
        
        # Instructions
        instruction_text = "Load a PDF file and JSON shapes file to begin labeling"
        self.canvas.create_text(500, 300, text=instruction_text, font=("Arial", 16), fill="gray", tags="instruction")
    
    def setup_status_bar(self):
        """Setup the status bar"""
        self.status_var = tk.StringVar(value="Ready - Load PDF and JSON files to begin")
        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.FLAT,
            bg="#34495e",
            fg="white",
            font=("Segoe UI", 9),
            anchor=tk.W,
            padx=15,
            pady=8
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_conditional_panel(self, parent):
        """Setup the conditional coloring panel"""
        cond_frame = ttk.LabelFrame(parent, text="Conditional Coloring", padding=10)
        cond_frame.pack(fill=tk.X, padx=5, pady=(0, 10))
        
        # Manage Variables button
        ttk.Button(
            cond_frame, 
            text="📊 Manage Variables", 
            command=self.open_variable_manager,
            width=25
        ).pack(pady=5)
        
        # Export/Import buttons
        export_import_frame = ttk.Frame(cond_frame)
        export_import_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            export_import_frame,
            text="📤 Export Conditions",
            command=self.export_conditions,
            width=12
        ).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        ttk.Button(
            export_import_frame,
            text="📥 Import Conditions",
            command=self.import_conditions,
            width=12
        ).pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        
        # Variables summary label
        self.variables_summary_var = tk.StringVar(value="No variables defined")
        ttk.Label(
            cond_frame, 
            textvariable=self.variables_summary_var,
            font=("Arial", 9),
            foreground="gray"
        ).pack(pady=2)
        
        # Separator
        ttk.Separator(cond_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Unified Apply button at the bottom
        apply_frame = ttk.Frame(cond_frame)
        apply_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Apply All Changes button (prominent green) - applies both text and colors
        self.apply_button = tk.Button(
            apply_frame, 
            text="✓ Apply All Changes",
            command=self.apply_all_changes,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            width=30,
            height=2
        )
        self.apply_button.pack(pady=5)
        
        ttk.Label(
            cond_frame,
            text="💡 Applies text changes, formatting, and conditional colors",
            font=("Arial", 8),
            foreground="gray"
        ).pack(pady=(0, 5))
    
    
    def load_pdf(self):
        """Load a PDF file"""
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if file_path:
            self.load_pdf_internal(file_path)
    
    def load_pdf_internal(self, file_path):
        """Internal method to load a PDF file from a given path"""
        try:
            self.current_pdf_path = file_path
            
            # Open PDF with PyMuPDF
            doc = fitz.open(file_path)
            
            if len(doc) == 0:
                messagebox.showerror("Error", "PDF file appears to be empty")
                return
            
            # Get first page
            page = doc[0]
            
            # Convert to image (high resolution)
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("ppm")
            self.pdf_image = Image.open(io.BytesIO(img_data))
            
            doc.close()
            
            # Reset zoom and display
            self.zoom_factor = 1.0
            self.original_image_size = None
            self.display_canvas()
            
            self.update_file_info()
            self.status_var.set(f"PDF loaded: {os.path.basename(file_path)}")
            
            # Auto-fit to window
            self.root.after(100, self.fit_to_window)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading PDF: {str(e)}")
    
    def load_json(self):
        """Load a JSON shapes file"""
        file_path = filedialog.askopenfilename(
            title="Select JSON Shapes File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                self.current_json_path = file_path
                self.shapes = data.get("shapes", [])
                
                # Update shape list
                self.update_shape_list()
                
                # Redraw canvas
                self.display_canvas()
                
                self.update_file_info()
                self.status_var.set(f"Loaded {len(self.shapes)} shapes from {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error loading JSON: {str(e)}")
    
    def update_file_info(self):
        """Update the file info display"""
        pdf_name = os.path.basename(self.current_pdf_path) if self.current_pdf_path else "None"
        json_name = os.path.basename(self.current_json_path) if self.current_json_path else "None"
        self.file_info_var.set(f"PDF: {pdf_name} | Shapes: {json_name}")
    
    def update_shape_list(self):
        """Update the shape listbox"""
        self.shape_listbox.delete(0, tk.END)
        
        for i, shape in enumerate(self.shapes):
            # Find if this shape has a label
            display_text = None
            for label in self.labels:
                if label.shape_index == i and label.text_lines:
                    # Show the first line of mapped label text as the identifier
                    non_empty_lines = [line for line in label.text_lines if line.strip()]
                    if non_empty_lines:
                        display_text = non_empty_lines[0]  # Just show first line
                    break
            
            # If no label, fall back to shape name
            if not display_text:
                shape_name = shape.get("name", f"Shape {i+1}")
                display_text = f"{shape_name} (no label)"
            
            self.shape_listbox.insert(tk.END, display_text)
    
    def on_shape_select(self, event):
        """Handle shape selection from listbox"""
        selection = self.shape_listbox.curselection()
        if selection:
            self.selected_shape_index = selection[0]
            
            # Validate shape index
            if self.selected_shape_index < 0 or self.selected_shape_index >= len(self.shapes):
                self.status_var.set("Error: Invalid shape selection")
                return
            
            # Find or create label for this shape
            label = self.find_label_for_shape(self.selected_shape_index)
            
            if label:
                # Load existing label
                self.load_label_to_editor(label)
                self.selected_label = label
            else:
                # Create new label at shape center
                shape = self.shapes[self.selected_shape_index]
                center = self.get_shape_center(shape)
                
                label = TextLabel(self.selected_shape_index, center)
                # Start with empty text - user will add their own
                label.text_lines = []
                label.use_custom_text = True  # User will provide custom text
                # Set default leader line width
                if hasattr(self, 'default_leader_width'):
                    label.leader_width = self.default_leader_width.get()
                self.labels.append(label)
                self.selected_label = label
                
                # Clear editor - no text lines added yet
                self.clear_text_editor()
            
            # Highlight shape on canvas
            self.highlight_selected_shape()
            
            self.status_var.set(f"Selected Shape {self.selected_shape_index + 1}")
    
    def find_label_for_shape(self, shape_index: int) -> Optional[TextLabel]:
        """Find label associated with a shape"""
        for label in self.labels:
            if label.shape_index == shape_index:
                return label
        return None
    
    def clean_orphaned_labels(self):
        """Remove labels that reference non-existent shapes"""
        if not self.shapes:
            # If there are no shapes, clear all labels
            if self.labels:
                self.labels.clear()
                self.selected_label = None
                return
        
        # Remove labels with invalid shape indices
        valid_labels = []
        removed_count = 0
        
        for label in self.labels:
            if 0 <= label.shape_index < len(self.shapes):
                valid_labels.append(label)
            else:
                removed_count += 1
                # Clear selection if this was the selected label
                if self.selected_label == label:
                    self.selected_label = None
        
        self.labels = valid_labels
        
        if removed_count > 0:
            print(f"Cleaned up {removed_count} orphaned label(s)")
            self.display_canvas()
    
    def get_shape_center(self, shape: Dict) -> Tuple[float, float]:
        """Calculate the center point of a shape"""
        coords = shape["coordinates"]
        shape_type = shape.get("type", "rectangle")
        
        if shape_type == "rectangle":
            x1, y1, x2, y2 = coords
            return ((x1 + x2) / 2, (y1 + y2) / 2)
        elif shape_type == "polygon":
            # Calculate centroid
            x_coords = [coords[i] for i in range(0, len(coords), 2)]
            y_coords = [coords[i] for i in range(1, len(coords), 2)]
            return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))
        else:
            # Default to first two coordinates
            return (coords[0], coords[1])
    
    def clear_text_editor(self):
        """Clear all text entry widgets"""
        for widget in self.text_entry_widgets:
            widget.destroy()
        self.text_entry_widgets.clear()
        
        # Show placeholder and hide scroll frame
        if hasattr(self, 'editor_placeholder'):
            self.editor_placeholder.pack(pady=20)
        if hasattr(self, 'editor_scroll_frame'):
            self.editor_scroll_frame.pack_forget()
    
    def add_text_line(self):
        """Add a new text line entry with per-line formatting controls"""
        # Hide placeholder and show scroll frame on first text line
        if not self.text_entry_widgets:
            if hasattr(self, 'editor_placeholder'):
                self.editor_placeholder.pack_forget()
            if hasattr(self, 'editor_scroll_frame'):
                self.editor_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        line_frame = ttk.Frame(self.text_entries_container, relief=tk.GROOVE, borderwidth=1)
        line_frame.pack(fill=tk.X, pady=3, padx=2)
        
        # Row 1: Text entry and Variable dropdown
        row1 = ttk.Frame(line_frame)
        row1.pack(fill=tk.X, padx=2, pady=(2, 0))
        
        # Text entry
        entry = ttk.Entry(row1, font=("Arial", 10), width=15)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Variable dropdown
        var_label = ttk.Label(row1, text="Var:", font=("Arial", 8))
        var_label.pack(side=tk.LEFT, padx=(0, 2))
        
        variable_var = tk.StringVar(value="None")
        variable_names = ["None"] + [v.name for v in self.variables]
        variable_combo = ttk.Combobox(row1, textvariable=variable_var, 
                                     values=variable_names, state="readonly", width=10)
        variable_combo.pack(side=tk.LEFT, padx=0)
        variable_combo.set("None")
        
        # Note: We'll bind the variable change event after creating sales/unit controls

        
        # Row 2: Formatting controls (Size, Text Color, BG Color, Remove)
        row2 = ttk.Frame(line_frame)
        row2.pack(fill=tk.X, padx=2, pady=(2, 2))
        
        # Font size control - use default
        size_label = ttk.Label(row2, text="Size:", font=("Arial", 8))
        size_label.pack(side=tk.LEFT, padx=(0, 2))
        
        size_var = tk.IntVar(value=self.default_text_size.get() if hasattr(self, 'default_text_size') else 12)
        size_spinner = ttk.Spinbox(row2, from_=6, to=72, textvariable=size_var, width=4)
        size_spinner.pack(side=tk.LEFT, padx=(0, 8))
        
        # Text color picker button - use default
        color_label = ttk.Label(row2, text="Text:", font=("Arial", 8))
        color_label.pack(side=tk.LEFT, padx=(0, 2))
        
        default_text_color = self.default_text_color.get() if hasattr(self, 'default_text_color') else "#000000"
        color_var = tk.StringVar(value=default_text_color)
        color_btn = tk.Button(row2, text="⬛", bg=default_text_color, fg="white", 
                             width=2, relief=tk.RAISED, bd=1,
                             command=lambda: self.pick_line_color(color_var, color_btn))
        color_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Background color picker button - use default
        bg_label = ttk.Label(row2, text="BG:", font=("Arial", 8))
        bg_label.pack(side=tk.LEFT, padx=(0, 2))
        
        default_bg_color = self.default_bg_color.get() if hasattr(self, 'default_bg_color') else "#FFFFFF"
        bg_color_var = tk.StringVar(value=default_bg_color)
        bg_color_btn = tk.Button(row2, text="⬛", bg=default_bg_color, fg="black", 
                                width=2, relief=tk.RAISED, bd=1,
                                command=lambda: self.pick_line_bg_color(bg_color_var, bg_color_btn))
        bg_color_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Remove button
        remove_btn = ttk.Button(row2, text="× Remove", width=8, 
                               command=lambda: self.remove_text_line(line_frame))
        
        # Store references: frame contains entry, size_var, color_var, bg_color_var, and variable_var
        line_frame.entry = entry
        line_frame.size_var = size_var
        line_frame.color_var = color_var
        line_frame.color_btn = color_btn
        line_frame.bg_color_var = bg_color_var
        line_frame.bg_color_btn = bg_color_btn
        line_frame.variable_var = variable_var
        line_frame.variable_combo = variable_combo

        
        self.text_entry_widgets.append(line_frame)
        
        # Bind change events to highlight Apply button
        entry.bind("<KeyRelease>", lambda e: self.mark_changes_pending())
        size_var.trace_add("write", lambda *args: self.mark_changes_pending())
        color_var.trace_add("write", lambda *args: self.mark_changes_pending())
        bg_color_var.trace_add("write", lambda *args: self.mark_changes_pending())
        variable_var.trace_add("write", lambda *args: self.mark_changes_pending())
        
        # Bind variable change to auto-enable sales/area checkbox and unit
        def on_variable_change(*args):
            selected_var_name = variable_var.get()
            if selected_var_name != "None":
                # Find the variable object
                for var in self.variables:
                    if var.name == selected_var_name:
                        # Check if this variable has auto-enable sales
                        if var.auto_enable_sales:
                            # Auto-enable is handled, but user must manually apply
                            pass  # Removed auto-apply - user must click Apply All Changes
                        break
        
        variable_var.trace_add("write", on_variable_change)


        
        # Focus on new entry
        entry.focus_set()
    
    def remove_text_line(self, line_frame):
        """Remove a text line entry"""
        if len(self.text_entry_widgets) > 1:
            line_frame.destroy()
            self.text_entry_widgets.remove(line_frame)
        else:
            messagebox.showinfo("Info", "At least one text line is required")
    
    def toggle_unit_dropdown(self, is_sales_var, unit_combo):
        """Enable or disable unit dropdown based on sales checkbox"""
        if is_sales_var.get():
            unit_combo.config(state="readonly")
        else:
            unit_combo.config(state="disabled")
            unit_combo.set("None")

    
    def load_label_to_editor(self, label: TextLabel):
        """Load label data into the text editor with per-line formatting"""
        self.clear_text_editor()
        
        # Load leader line properties into controls
        if hasattr(self, 'leader_style_var'):
            self.leader_style_var.set(label.leader_style)
        if hasattr(self, 'leader_width_var'):
            self.leader_width_var.set(label.leader_width)
        if hasattr(self, 'leader_color_var'):
            self.leader_color_var.set(label.leader_color)
            if hasattr(self, 'leader_color_btn'):
                self.leader_color_btn.config(bg=label.leader_color)
                # Update foreground color for visibility
                r, g, b = tuple(int(label.leader_color[j:j+2], 16) for j in (1, 3, 5))
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                fg_color = "black" if brightness > 128 else "white"
                self.leader_color_btn.config(fg=fg_color)
        
        # Add text lines with per-line formatting
        for i, text in enumerate(label.text_lines):
            self.add_text_line()
            line_frame = self.text_entry_widgets[-1]
            
            # Set text
            line_frame.entry.insert(0, text)
            
            # Set per-line formatting
            if i < len(label.line_font_sizes):
                line_frame.size_var.set(label.line_font_sizes[i])
            if i < len(label.line_font_colors):
                color = label.line_font_colors[i]
                line_frame.color_var.set(color)
                line_frame.color_btn.config(bg=color)
            if i < len(label.line_bg_colors):
                bg_color = label.line_bg_colors[i]
                line_frame.bg_color_var.set(bg_color)
                line_frame.bg_color_btn.config(bg=bg_color)
                # Update foreground color for visibility
                r, g, b = tuple(int(bg_color[j:j+2], 16) for j in (1, 3, 5))
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                fg_color = "black" if brightness > 128 else "white"
                line_frame.bg_color_btn.config(fg=fg_color)
            
            # Set sales checkbox and unit metric (always load saved values)
            # Ensure label has sales/unit lists (for backward compatibility)
            if not hasattr(label, 'line_is_sales') or label.line_is_sales is None:
                label.line_is_sales = [False] * len(label.text_lines)
            if not hasattr(label, 'line_unit_metric') or label.line_unit_metric is None:
                label.line_unit_metric = ["None"] * len(label.text_lines)
            
            # Get the variable name for this line (if any)
            var_name = "None"
            if i < len(label.line_variables):
                var_name = label.line_variables[i]
            
            # Set variable assignment
            line_frame.variable_var.set(var_name)
            # Update dropdown values in case new variables were added
            variable_names = ["None"] + [v.name for v in self.variables]
            line_frame.variable_combo.config(values=variable_names)


    
    
    def mark_changes_pending(self):
        """Highlight the Apply button to indicate pending changes"""
        if hasattr(self, 'apply_button'):
            self.changes_pending = True
            self.apply_button.config(bg="#FF9800", text="⚠ Apply All Changes (Unsaved)")
    
    def reset_apply_button(self):
        """Reset the Apply button to normal state after applying changes"""
        if hasattr(self, 'apply_button'):
            self.changes_pending = False
            self.apply_button.config(bg="#4CAF50", text="✓ Apply All Changes")
    
    def pick_line_color(self, color_var, color_btn):
        """Open color picker for individual line text color"""
        color = colorchooser.askcolor(title="Choose Text Color", initialcolor=color_var.get())
        if color[1]:
            color_var.set(color[1])
            color_btn.config(bg=color[1])
            self.mark_changes_pending()
    
    def pick_line_bg_color(self, bg_color_var, bg_color_btn):
        """Open color picker for individual line background color"""
        color = colorchooser.askcolor(title="Choose Background Color", initialcolor=bg_color_var.get())
        if color[1]:
            bg_color_var.set(color[1])
            bg_color_btn.config(bg=color[1])
            # Update foreground color for visibility
            r, g, b = tuple(int(color[1][j:j+2], 16) for j in (1, 3, 5))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            fg_color = "black" if brightness > 128 else "white"
            bg_color_btn.config(fg=fg_color)
            self.mark_changes_pending()
    
    def pick_leader_color(self):
        """Open color picker for leader line color"""
        color = colorchooser.askcolor(title="Choose Leader Line Color", initialcolor=self.leader_color_var.get())
        if color[1]:
            self.leader_color_var.set(color[1])
            self.leader_color_btn.config(bg=color[1])
            # Update foreground color for visibility
            r, g, b = tuple(int(color[1][j:j+2], 16) for j in (1, 3, 5))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            fg_color = "black" if brightness > 128 else "white"
            self.leader_color_btn.config(fg=fg_color)
            self.mark_changes_pending()
    
    def update_leader_line(self):
        """Update the leader line properties for the selected label (called by apply_text)"""
        if self.selected_label and self.selected_label.has_leader:
            self.selected_label.leader_style = self.leader_style_var.get()
            self.selected_label.leader_width = self.leader_width_var.get()
            self.selected_label.leader_color = self.leader_color_var.get()
    
    def pick_bg_color(self):
        """Open color picker for background color"""
        color = colorchooser.askcolor(title="Choose Background Color", initialcolor=self.bg_color_var.get())
        if color[1]:
            self.bg_color_var.set(color[1])
            self.bg_color_display.config(bg=color[1])
            self.mark_changes_pending()
    
    
    
    def apply_text(self):
        """Apply text changes with per-line formatting to the selected label"""
        if self.selected_label is None:
            messagebox.showwarning("Warning", "No shape selected")
            return
        
        # Collect text and per-line formatting from entries
        text_lines = []
        line_font_sizes = []
        line_font_colors = []
        line_bg_colors = []
        line_variables = []
        line_is_sales = []
        line_unit_metric = []
        
        for i, line_frame in enumerate(self.text_entry_widgets):
            text = line_frame.entry.get()
            var_name = line_frame.variable_var.get()
            
            # Check if this variable has auto-enable sales/area
            has_auto_sales = False
            unit_to_append = None
            if var_name != "None":
                for var in self.variables:
                    if var.name == var_name and var.auto_enable_sales:
                        has_auto_sales = True
                        if var.default_unit != "None":
                            # Extract unit symbol
                            unit_str = var.default_unit
                            if "(" in unit_str:
                                unit_to_append = unit_str.split("(")[0].strip()
                            else:
                                unit_to_append = unit_str
                        break
            
            # Append unit to text if variable has auto-enable sales
            if has_auto_sales and unit_to_append:
                # Check if unit is already in the text to avoid duplicates
                if not text.endswith(unit_to_append):
                    text = f"{text} {unit_to_append}"
                    # Update the text entry to show the unit
                    line_frame.entry.delete(0, tk.END)
                    line_frame.entry.insert(0, text)
            
            text_lines.append(text)
            line_font_sizes.append(line_frame.size_var.get())
            line_font_colors.append(line_frame.color_var.get())
            line_bg_colors.append(line_frame.bg_color_var.get())
            line_variables.append(var_name)
            # Store sales/area info based on variable settings
            line_is_sales.append(has_auto_sales)
            line_unit_metric.append(var.default_unit if has_auto_sales and var_name != "None" else "None")
        
        # Update label with per-line formatting and variable assignments
        self.selected_label.text_lines = text_lines
        self.selected_label.line_font_sizes = line_font_sizes
        self.selected_label.line_font_colors = line_font_colors
        self.selected_label.line_bg_colors = line_bg_colors
        self.selected_label.line_variables = line_variables
        self.selected_label.line_is_sales = line_is_sales
        self.selected_label.line_unit_metric = line_unit_metric
        
        # Update leader line properties
        self.update_leader_line()
        
        # Redraw canvas
        self.display_canvas()
        
        # Update shape list
        self.update_shape_list()
        
        # Reset Apply button state
        self.reset_apply_button()
        
        self.status_var.set("Text applied successfully")
    
    def apply_all_changes(self):
        """Apply all changes: text, formatting, and conditional colors to ALL labels"""
        # Save state before applying changes
        self.save_state_for_undo()
        
        # First apply text changes to selected label if any
        if self.selected_label:
            self.apply_text()
        
        # Then update ALL labels to append units if they have variables with auto-enable
        for label in self.labels:
            updated = False
            for i in range(len(label.text_lines)):
                # Get variable for this line
                var_name = label.line_variables[i] if i < len(label.line_variables) else "None"
                
                if var_name != "None":
                    # Check if variable has auto-enable sales
                    for var in self.variables:
                        if var.name == var_name and var.auto_enable_sales:
                            # Extract unit symbol
                            unit_to_append = None
                            if var.default_unit != "None":
                                unit_str = var.default_unit
                                if "(" in unit_str:
                                    unit_to_append = unit_str.split("(")[0].strip()
                                else:
                                    unit_to_append = unit_str
                            
                            # Append unit to text if not already there
                            if unit_to_append:
                                text = label.text_lines[i]
                                if not text.endswith(unit_to_append):
                                    label.text_lines[i] = f"{text} {unit_to_append}"
                                    updated = True
                                
                                # Update sales/area metadata
                                if i < len(label.line_is_sales):
                                    label.line_is_sales[i] = True
                                if i < len(label.line_unit_metric):
                                    label.line_unit_metric[i] = var.default_unit
                            break
            
            # If this label was updated and it's the selected label, update the text entries
            if updated and label == self.selected_label:
                # Reload the label into editor to show updated text
                self.load_label_to_editor(label)
        
        # Always apply variable colors when Apply button is clicked
        if self.variables:
            self.apply_variable_colors()
        
        # Redraw canvas to show all updates
        self.display_canvas()
        
        self.status_var.set("All changes applied successfully to all labels")
        
        # Update undo button state
        self.update_undo_button_state()
    
    def delete_label(self):
        """Delete the selected label"""
        if self.selected_label:
            # Save state before deleting
            self.save_state_for_undo()
            
            self.labels.remove(self.selected_label)
            self.selected_label = None
            self.clear_text_editor()
            self.display_canvas()
            self.update_shape_list()
            self.status_var.set("Label deleted")
            
            # Update undo button state
            self.update_undo_button_state()
        else:
            messagebox.showinfo("Info", "No label selected to delete")
    
    def save_state_for_undo(self):
        """Save current state to undo stack before making changes"""
        import copy
        
        # Create deep copy of labels
        labels_copy = []
        for label in self.labels:
            label_copy = TextLabel(label.shape_index, label.position)
            label_copy.text_lines = label.text_lines.copy()
            label_copy.line_font_sizes = label.line_font_sizes.copy()
            label_copy.line_font_colors = label.line_font_colors.copy()
            label_copy.line_bg_colors = label.line_bg_colors.copy()
            label_copy.line_variables = label.line_variables.copy()
            label_copy.line_is_sales = label.line_is_sales.copy()
            label_copy.line_unit_metric = label.line_unit_metric.copy()
            label_copy.has_leader = label.has_leader
            label_copy.leader_points = copy.deepcopy(label.leader_points)
            label_copy.leader_style = label.leader_style
            label_copy.leader_width = label.leader_width
            label_copy.leader_color = label.leader_color
            label_copy.use_custom_text = label.use_custom_text
            labels_copy.append(label_copy)
        
        # Create deep copy of shapes (for conditional coloring)
        shapes_copy = copy.deepcopy(self.shapes)
        
        # Save state
        state = {
            'labels': labels_copy,
            'shapes': shapes_copy,
            'selected_shape_index': self.selected_shape_index
        }
        
        self.undo_stack.append(state)
        
        # Limit stack size
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)
        
        # Update undo button state
        self.update_undo_button_state()
    
    def undo_last_change(self):
        """Undo the last change by restoring previous state"""
        if not self.undo_stack:
            messagebox.showinfo("Info", "Nothing to undo")
            return
        
        # Pop last state from stack
        state = self.undo_stack.pop()
        
        # Restore labels
        self.labels = state['labels']
        
        # Restore shapes
        self.shapes = state['shapes']
        
        # Restore selected shape index
        self.selected_shape_index = state['selected_shape_index']
        
        # Clear selected label
        self.selected_label = None
        
        # Update UI
        self.clear_text_editor()
        self.update_shape_list()
        self.display_canvas()
        
        # Update status
        self.status_var.set("Undo successful")
        
        # Update undo button state
        self.update_undo_button_state()
    
    def update_undo_button_state(self):
        """Enable or disable undo button based on undo stack state"""
        if hasattr(self, 'undo_button'):
            if self.undo_stack:
                self.undo_button.config(state='normal')
            else:
                self.undo_button.config(state='disabled')

    
    def pick_default_text_color(self):
        """Pick default text color"""
        color = colorchooser.askcolor(title="Choose Default Text Color", initialcolor=self.default_text_color.get())
        if color[1]:
            self.default_text_color.set(color[1])
            self.default_text_color_btn.config(bg=color[1])
            # Update foreground for visibility
            r, g, b = tuple(int(color[1][j:j+2], 16) for j in (1, 3, 5))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            fg_color = "black" if brightness > 128 else "white"
            self.default_text_color_btn.config(fg=fg_color)
    
    def pick_default_bg_color(self):
        """Pick default background color"""
        color = colorchooser.askcolor(title="Choose Default Background Color", initialcolor=self.default_bg_color.get())
        if color[1]:
            self.default_bg_color.set(color[1])
            self.default_bg_color_btn.config(bg=color[1])
            # Update foreground for visibility
            r, g, b = tuple(int(color[1][j:j+2], 16) for j in (1, 3, 5))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            fg_color = "black" if brightness > 128 else "white"
            self.default_bg_color_btn.config(fg=fg_color)
    
    def clear_all_labels(self):
        """Clear all labels"""
        if not self.labels:
            messagebox.showinfo("Info", "No labels to clear")
            return
        
        response = messagebox.askyesno(
            "Confirm Clear",
            "Are you sure you want to clear all labels?\n\n"
            "You can use Undo to restore them."
        )
        
        if response:
            # Save state before clearing
            self.save_state_for_undo()
            
            self.labels.clear()
            self.selected_label = None
            self.clear_text_editor()
            self.display_canvas()
            self.update_shape_list()
            self.status_var.set("All labels cleared")
            messagebox.showinfo("Success", "All labels cleared")
            
            # Update undo button state
            self.update_undo_button_state()
    
    def new_file(self):
        """Clear everything and start fresh with a new file"""
        if self.labels or self.pdf_image or self.shapes:
            response = messagebox.askyesno(
                "New File",
                "This will clear all current work (PDF, shapes, and labels).\n\nAre you sure you want to start over?"
            )
            
            if not response:
                return
        
        # Clear all data
        self.current_pdf_path = None
        self.current_json_path = None
        self.pdf_image = None
        self.canvas_image = None
        self.shapes.clear()
        self.labels.clear()
        self.selected_label = None
        self.selected_shape_index = None
        
        # Reset zoom
        self.zoom_factor = 1.0
        self.original_image_size = None
        
        # Clear UI
        self.clear_text_editor()
        self.shape_listbox.delete(0, tk.END)
        self.canvas.delete("all")
        
        # Reset display
        instruction_text = "Load a PDF file and JSON shapes file to begin labeling"
        self.canvas.create_text(500, 300, text=instruction_text, font=("Arial", 16), fill="gray", tags="instruction")
        
        # Update status
        self.file_info_var.set("No files loaded")
        self.status_var.set("Ready - Load PDF and JSON files to begin")
        self.zoom_var.set("Zoom: 100%")
        
        messagebox.showinfo("New File", "All data cleared. Ready to start fresh!")
    
    def display_canvas(self):
        """Display PDF, shapes, and labels on canvas"""
        if not self.pdf_image:
            return
        
        # Clear canvas
        self.canvas.delete("all")
        
        # Store original size
        if self.original_image_size is None:
            self.original_image_size = self.pdf_image.size
        
        # Calculate new size based on zoom
        original_width, original_height = self.original_image_size
        new_width = int(original_width * self.zoom_factor)
        new_height = int(original_height * self.zoom_factor)
        
        # Resize image
        if self.zoom_factor != 1.0:
            display_image = self.pdf_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            display_image = self.pdf_image.copy()
        
        # Draw shapes on image (semi-transparent)
        if self.shapes:
            display_image = self.draw_shapes_on_image(display_image)
        
        # Convert to PhotoImage and display
        self.canvas_image = ImageTk.PhotoImage(display_image)
        self.canvas.create_image(10, 10, anchor=tk.NW, image=self.canvas_image, tags="pdf_image")
        
        # Draw labels and leader lines
        self.draw_labels()
        
        # Highlight selected shape (if any)
        self.highlight_selected_shape()
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def draw_shapes_on_image(self, image: Image.Image) -> Image.Image:
        """Draw shapes on the image with semi-transparency"""
        # Create RGBA overlay
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        for idx, shape in enumerate(self.shapes):
            try:
                coords = shape["coordinates"]
                color_hex = shape.get("color", "#FF0000")
                shape_type = shape.get("type", "rectangle")
                
                # Check if this shape has a label with variable assignment
                label = self.find_label_for_shape(idx)
                if label:
                    # Check each text line for variable assignments
                    for i, text_line in enumerate(label.text_lines):
                        # Check if this line has a variable assigned
                        if i < len(label.line_variables):
                            var_name = label.line_variables[i]
                            if var_name and var_name != "None":
                                # Find the variable
                                variable = None
                                for v in self.variables:
                                    if v.name == var_name:
                                        variable = v
                                        break
                                
                                if variable:
                                    # Extract numeric value from text
                                    try:
                                        # Remove commas and extract numbers
                                        cleaned_text = text_line.replace(',', '').strip()
                                        # Try to find a number in the text
                                        import re
                                        numbers = re.findall(r'-?\d+\.?\d*', cleaned_text)
                                        if numbers:
                                            value = float(numbers[0])
                                            # Evaluate variable rules to get color
                                            conditional_color = variable.evaluate(value)
                                            if conditional_color:
                                                color_hex = conditional_color
                                                break  # Use first matching variable
                                    except (ValueError, IndexError):
                                        pass  # Keep default color if parsing fails
                
                # Convert hex to RGB and add alpha
                color_rgb = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                color_rgba = color_rgb + (80,)  # 80/255 = ~30% opacity
                
                if shape_type == "rectangle":
                    # Scale coordinates
                    scaled_coords = [c * self.zoom_factor for c in coords]
                    draw.rectangle(scaled_coords, fill=color_rgba, outline=color_rgb + (150,), width=2)
                elif shape_type == "polygon":
                    # Scale coordinates
                    scaled_coords = [c * self.zoom_factor for c in coords]
                    points = [(scaled_coords[i], scaled_coords[i+1]) for i in range(0, len(scaled_coords), 2)]
                    draw.polygon(points, fill=color_rgba, outline=color_rgb + (150,), width=2)
                elif shape_type == "oval":
                    # Oval coordinates: [x1, y1, x2, y2] (bounding box)
                    scaled_coords = [c * self.zoom_factor for c in coords]
                    draw.ellipse(scaled_coords, fill=color_rgba, outline=color_rgb + (150,), width=2)
                elif shape_type == "circle":
                    # Circle coordinates: [cx, cy, radius]
                    cx, cy, radius = coords
                    x1 = (cx - radius) * self.zoom_factor
                    y1 = (cy - radius) * self.zoom_factor
                    x2 = (cx + radius) * self.zoom_factor
                    y2 = (cy + radius) * self.zoom_factor
                    draw.ellipse([x1, y1, x2, y2], fill=color_rgba, outline=color_rgb + (150,), width=2)
            except Exception as e:
                # Log error but continue drawing other shapes
                print(f"Error drawing shape {idx} ({shape.get('type', 'unknown')}): {e}")
                continue
        
        # Composite overlay onto image
        image = image.convert('RGBA')
        image = Image.alpha_composite(image, overlay)
        return image.convert('RGB')
    
    def draw_labels(self):
        """Draw text labels and leader lines on canvas"""
        for label in self.labels:
            # Validate shape index before accessing
            if label.shape_index < 0 or label.shape_index >= len(self.shapes):
                # Skip labels that reference non-existent shapes
                continue
            
            # Get canvas position (this scales with zoom)
            canvas_x, canvas_y = self.image_to_canvas_coords(label.position[0], label.position[1])
            
            # Check if label is outside shape and needs leader line
            shape = self.shapes[label.shape_index]
            label.has_leader = not self.is_point_in_shape(label.position, shape)
            
            # We'll draw the leader line AFTER calculating the label box dimensions
            # so we can connect it to the middle of the box
            
            # Draw text lines with per-line background boxes
            text_lines = [line for line in label.text_lines if line.strip()]
            if text_lines:
                # Calculate dimensions for each line with its own font size
                line_heights = []
                line_widths = []
                
                for i, text in enumerate(text_lines):
                    # Get per-line font size, with fallback
                    if i < len(label.line_font_sizes):
                        base_font_size = label.line_font_sizes[i]
                    else:
                        base_font_size = 12
                    
                    # Scale font size with zoom
                    display_font_size = max(1, int(base_font_size * self.zoom_factor))
                    temp_font = tkfont.Font(family="Arial", size=display_font_size)
                    
                    # Use text as-is (unit is already in the text if applicable)
                    display_text = text
                    
                    line_heights.append(temp_font.metrics('linespace'))
                    line_widths.append(temp_font.measure(display_text))

                
                # Calculate max width for alignment
                max_width = max(line_widths) if line_widths else 0
                
                # Scale padding with zoom
                padding_x = int(10 * self.zoom_factor)
                padding_y = int(4 * self.zoom_factor)
                
                # Draw each line with its own background box
                label.canvas_text_ids.clear()
                current_y = canvas_y
                
                for i, text in enumerate(text_lines):
                    # Get per-line formatting
                    if i < len(label.line_font_sizes):
                        base_font_size = label.line_font_sizes[i]
                    else:
                        base_font_size = 12
                    
                    if i < len(label.line_font_colors):
                        text_color = label.line_font_colors[i]
                    else:
                        text_color = "#000000"
                    
                    if i < len(label.line_bg_colors):
                        bg_color = label.line_bg_colors[i]
                    else:
                        bg_color = "#FFFFFF"
                    
                    # Scale font size with zoom
                    display_font_size = max(1, int(base_font_size * self.zoom_factor))
                    
                    # Calculate box dimensions for this line
                    line_box_height = line_heights[i] + (padding_y * 2)
                    line_box_width = max_width + (padding_x * 2)
                    
                    # Draw background box for this line (no border)
                    box_id = self.canvas.create_rectangle(
                        canvas_x, current_y,
                        canvas_x + line_box_width, current_y + line_box_height,
                        fill=bg_color,
                        outline="",
                        tags=f"label_box_{label.shape_index}"
                    )
                    
                    # Use text as-is (unit is already in the text if applicable)
                    display_text = text
                    
                    # Draw text centered on top of background
                    text_id = self.canvas.create_text(
                        canvas_x + line_box_width / 2, current_y + padding_y,
                        text=display_text,
                        anchor=tk.N,
                        font=("Arial", display_font_size),
                        fill=text_color,
                        tags=f"label_text_{label.shape_index}"
                    )
                    label.canvas_text_ids.append(text_id)
                    current_y += line_box_height

                
                # Bind drag events to text box
                self.canvas.tag_bind(f"label_box_{label.shape_index}", "<Button-1>", 
                                    lambda e, lbl=label: self.start_drag_label(e, lbl))
                self.canvas.tag_bind(f"label_text_{label.shape_index}", "<Button-1>", 
                                    lambda e, lbl=label: self.start_drag_label(e, lbl))
                
                # Now draw the leader line connecting to the middle of the label box
                if label.has_leader:
                    # Calculate leader line to shape
                    label.leader_points = self.calculate_leader_line(label.position, shape)
                    
                    if label.leader_points:
                        # Calculate the label box dimensions
                        total_height = sum(line_heights) + (padding_y * 2 * len(text_lines))
                        label_box_width = max_width + (padding_x * 2)
                        
                        # Get the shape connection point (last point in leader_points)
                        if len(label.leader_points) > 1:
                            shape_x, shape_y = label.leader_points[-1]
                            shape_cx, shape_cy = self.image_to_canvas_coords(shape_x, shape_y)
                        else:
                            shape_cx, shape_cy = self.image_to_canvas_coords(label.leader_points[0][0], label.leader_points[0][1])
                        
                        # Calculate which edge of the label box is closest to the shape
                        label_center_x = canvas_x + label_box_width / 2
                        label_center_y = canvas_y + total_height / 2
                        
                        # Determine connection point on label border
                        # Calculate angle from label center to shape
                        import math
                        dx = shape_cx - label_center_x
                        dy = shape_cy - label_center_y
                        
                        # Find intersection with label box border
                        # Check which edge the line intersects
                        if abs(dx) > abs(dy):
                            # Intersects left or right edge
                            if dx > 0:  # Right edge
                                label_connect_x = canvas_x + label_box_width
                                label_connect_y = label_center_y
                            else:  # Left edge
                                label_connect_x = canvas_x
                                label_connect_y = label_center_y
                        else:
                            # Intersects top or bottom edge
                            if dy > 0:  # Bottom edge
                                label_connect_x = label_center_x
                                label_connect_y = canvas_y + total_height
                            else:  # Top edge
                                label_connect_x = label_center_x
                                label_connect_y = canvas_y
                        
                        # Create line from label border to shape
                        line_coords = [label_connect_x, label_connect_y, shape_cx, shape_cy]
                        
                        # Get custom line properties
                        line_width = max(1, int(label.leader_width * min(self.zoom_factor, 1.5)))
                        line_color = label.leader_color
                        
                        # Determine dash pattern based on style
                        dash_pattern = None
                        if label.leader_style == "dashed":
                            dash_pattern = (8, 4)
                        elif label.leader_style == "dotted":
                            dash_pattern = (2, 4)
                        
                        # Draw leader line
                        label.canvas_leader_id = self.canvas.create_line(
                            line_coords,
                            fill=line_color,
                            width=line_width,
                            dash=dash_pattern if dash_pattern else "",
                            arrow=tk.LAST,
                            tags="leader_line"
                        )
    
    def is_point_in_shape(self, point: Tuple[float, float], shape: Dict) -> bool:
        """Check if a point is inside a shape"""
        x, y = point
        coords = shape["coordinates"]
        shape_type = shape.get("type", "rectangle")
        
        if shape_type == "rectangle":
            x1, y1, x2, y2 = coords
            return min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)
        elif shape_type == "polygon":
            # Use ray casting algorithm
            points = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
            return self.point_in_polygon(point, points)
        elif shape_type == "oval":
            # Oval coordinates: [x1, y1, x2, y2] (bounding box)
            x1, y1, x2, y2 = coords
            # Check if point is inside the ellipse
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            rx, ry = abs(x2 - x1) / 2, abs(y2 - y1) / 2
            if rx == 0 or ry == 0:
                return False
            # Ellipse equation: ((x-cx)/rx)^2 + ((y-cy)/ry)^2 <= 1
            return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1
        elif shape_type == "circle":
            # Circle coordinates: [cx, cy, radius]
            cx, cy, radius = coords
            # Check if point is within radius
            distance = math.sqrt((x - cx)**2 + (y - cy)**2)
            return distance <= radius
        
        return False
    
    def point_in_polygon(self, point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
        """Check if point is inside polygon using ray casting"""
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def calculate_leader_line(self, text_pos: Tuple[float, float], shape: Dict) -> List[List[float]]:
        """Calculate leader line from text to shape"""
        # Find nearest point on shape boundary
        nearest_point = self.find_nearest_point_on_shape(text_pos, shape)
        
        if nearest_point:
            return [list(text_pos), list(nearest_point)]
        
        return []
    
    def find_nearest_point_on_shape(self, point: Tuple[float, float], shape: Dict) -> Optional[Tuple[float, float]]:
        """Find the nearest point on shape boundary to given point"""
        x, y = point
        coords = shape["coordinates"]
        shape_type = shape.get("type", "rectangle")
        
        if shape_type == "rectangle":
            x1, y1, x2, y2 = coords
            
            # Clamp point to rectangle boundary
            if x < min(x1, x2):
                nearest_x = min(x1, x2)
            elif x > max(x1, x2):
                nearest_x = max(x1, x2)
            else:
                nearest_x = x
            
            if y < min(y1, y2):
                nearest_y = min(y1, y2)
            elif y > max(y1, y2):
                nearest_y = max(y1, y2)
            else:
                nearest_y = y
            
            # If both are clamped, find closest corner or edge
            if nearest_x != x and nearest_y != y:
                # Point is outside corner, return corner
                return (nearest_x, nearest_y)
            elif nearest_x != x:
                # Point is outside horizontally, clamp to vertical edge
                return (nearest_x, y)
            else:
                # Point is outside vertically, clamp to horizontal edge
                return (x, nearest_y)
        
        elif shape_type == "polygon":
            # Find nearest point on polygon edges
            points = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
            min_dist = float('inf')
            nearest = None
            
            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i + 1) % len(points)]
                
                # Find nearest point on line segment
                nearest_on_segment = self.nearest_point_on_segment(point, p1, p2)
                dist = math.sqrt((nearest_on_segment[0] - x)**2 + (nearest_on_segment[1] - y)**2)
                
                if dist < min_dist:
                    min_dist = dist
                    nearest = nearest_on_segment
            
            return nearest
        
        elif shape_type == "oval":
            # Oval coordinates: [x1, y1, x2, y2] (bounding box)
            x1, y1, x2, y2 = coords
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            rx, ry = abs(x2 - x1) / 2, abs(y2 - y1) / 2
            
            # Calculate angle from center to point
            dx = x - cx
            dy = y - cy
            
            if dx == 0 and dy == 0:
                # Point is at center, return right edge
                return (cx + rx, cy)
            
            # Find point on ellipse boundary
            # Parametric form: x = cx + rx*cos(t), y = cy + ry*sin(t)
            angle = math.atan2(dy, dx)
            nearest_x = cx + rx * math.cos(angle)
            nearest_y = cy + ry * math.sin(angle)
            return (nearest_x, nearest_y)
        
        elif shape_type == "circle":
            # Circle coordinates: [cx, cy, radius]
            cx, cy, radius = coords
            
            # Calculate angle from center to point
            dx = x - cx
            dy = y - cy
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance == 0:
                # Point is at center, return any point on circle
                return (cx + radius, cy)
            
            # Find point on circle boundary in direction of the point
            nearest_x = cx + (dx / distance) * radius
            nearest_y = cy + (dy / distance) * radius
            return (nearest_x, nearest_y)
        
        return None
    
    def nearest_point_on_segment(self, point: Tuple[float, float], 
                                 seg_start: Tuple[float, float], 
                                 seg_end: Tuple[float, float]) -> Tuple[float, float]:
        """Find nearest point on line segment to given point"""
        x, y = point
        x1, y1 = seg_start
        x2, y2 = seg_end
        
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return seg_start
        
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        
        return (x1 + t * dx, y1 + t * dy)
    
    def start_drag_label(self, event, label: TextLabel):
        """Start dragging a label"""
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Calculate offset from label position
        label_canvas_x, label_canvas_y = self.image_to_canvas_coords(label.position[0], label.position[1])
        label.drag_offset = (canvas_x - label_canvas_x, canvas_y - label_canvas_y)
        label.dragging = True
        
        self.selected_label = label
        
        # Bind motion events
        self.canvas.bind("<B1-Motion>", lambda e: self.drag_label(e, label))
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.end_drag_label(e, label))
    
    def drag_label(self, event, label: TextLabel):
        """Drag a label"""
        if not label.dragging:
            return
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Calculate new position
        new_canvas_x = canvas_x - label.drag_offset[0]
        new_canvas_y = canvas_y - label.drag_offset[1]
        
        # Convert to image coordinates
        new_img_x, new_img_y = self.canvas_to_image_coords(new_canvas_x, new_canvas_y)
        label.position = (new_img_x, new_img_y)
        
        # Redraw
        self.display_canvas()
    
    def end_drag_label(self, event, label: TextLabel):
        """End dragging a label"""
        label.dragging = False
        
        # Unbind motion events
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        
        # Rebind original canvas events
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
    
    def highlight_selected_shape(self):
        """Highlight the selected shape on canvas with beautiful modern glow effect"""
        # Remove any existing highlight
        self.canvas.delete("shape_highlight")
        
        if self.selected_shape_index is None or not self.shapes:
            return
        
        if self.selected_shape_index >= len(self.shapes):
            return
        
        shape = self.shapes[self.selected_shape_index]
        coords = shape["coordinates"]
        shape_type = shape.get("type", "rectangle")
        
        # Scale coordinates for current zoom
        scaled_coords = [c * self.zoom_factor for c in coords]
        
        # Offset for canvas position
        offset_coords = [scaled_coords[i] + 10 if i % 2 == 0 else scaled_coords[i] + 10 
                        for i in range(len(scaled_coords))]
        
        # Simple clean red highlight - 5px thick
        glow_layers = [
            {"color": "#FF0000", "width": 5, "offset": 0},  # Red, 5px line
        ]
        
        for layer in glow_layers:
            # Apply offset for shadow effect
            offset = layer.get("offset", 0)
            shadow_coords = [offset_coords[i] + offset for i in range(len(offset_coords))]
            
            if shape_type == "rectangle":
                self.canvas.create_rectangle(
                    shadow_coords,
                    outline=layer["color"],
                    width=layer["width"],
                    tags="shape_highlight"
                )
            elif shape_type == "polygon":
                points = [(shadow_coords[i], shadow_coords[i+1]) 
                         for i in range(0, len(shadow_coords), 2)]
                # Flatten points for canvas.create_polygon
                flat_points = [coord for point in points for coord in point]
                self.canvas.create_polygon(
                    flat_points,
                    outline=layer["color"],
                    fill="",
                    width=layer["width"],
                    tags="shape_highlight"
                )
            elif shape_type in ["circle", "oval"]:
                # Handle circle and oval shapes
                self.canvas.create_oval(
                    shadow_coords,
                    outline=layer["color"],
                    width=layer["width"],
                    tags="shape_highlight"
                )
    
    def on_canvas_click(self, event):
        """Handle canvas click"""
        # Check if clicking on a label
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Find if clicking on any label
        clicked_items = self.canvas.find_overlapping(canvas_x-2, canvas_y-2, canvas_x+2, canvas_y+2)
        
        for item in clicked_items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("label_box_") or tag.startswith("label_text_"):
                    # Extract shape index
                    shape_index = int(tag.split("_")[-1])
                    
                    # Select this shape in listbox
                    self.shape_listbox.selection_clear(0, tk.END)
                    self.shape_listbox.selection_set(shape_index)
                    self.shape_listbox.see(shape_index)
                    
                    # Trigger selection event
                    self.on_shape_select(None)
                    return
    
    def on_canvas_drag(self, event):
        """Handle canvas drag"""
        pass
    
    def on_canvas_release(self, event):
        """Handle canvas release"""
        pass
    
    def start_pan(self, event):
        """Start panning"""
        self.panning = True
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.config(cursor="fleur")
    
    def pan_motion(self, event):
        """Handle panning motion"""
        if self.panning:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def end_pan(self, event):
        """End panning"""
        self.panning = False
        self.canvas.config(cursor="")
    
    def zoom_canvas(self, event):
        """Zoom canvas with mouse wheel"""
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def zoom_in(self):
        """Zoom in"""
        self.zoom_factor *= 1.25
        self.update_zoom()
    
    def zoom_out(self):
        """Zoom out"""
        self.zoom_factor /= 1.25
        if self.zoom_factor < 0.1:
            self.zoom_factor = 0.1
        self.update_zoom()
    
    def fit_to_window(self):
        """Fit image to window"""
        if not self.pdf_image:
            return
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            img_width, img_height = self.pdf_image.size
            
            zoom_x = canvas_width / img_width
            zoom_y = canvas_height / img_height
            
            self.zoom_factor = min(zoom_x, zoom_y) * 0.9
            self.update_zoom()
    
    def update_zoom(self):
        """Update zoom display"""
        self.zoom_var.set(f"Zoom: {int(self.zoom_factor * 100)}%")
        self.display_canvas()
    
    def image_to_canvas_coords(self, img_x: float, img_y: float) -> Tuple[float, float]:
        """Convert image coordinates to canvas coordinates"""
        canvas_x = img_x * self.zoom_factor + 10
        canvas_y = img_y * self.zoom_factor + 10
        return (canvas_x, canvas_y)
    
    def canvas_to_image_coords(self, canvas_x: float, canvas_y: float) -> Tuple[float, float]:
        """Convert canvas coordinates to image coordinates"""
        img_x = (canvas_x - 10) / self.zoom_factor
        img_y = (canvas_y - 10) / self.zoom_factor
        return (img_x, img_y)
    
    def save_labels(self):
        """Save labels to JSON file"""
        if not self.labels:
            messagebox.showwarning("Warning", "No labels to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Labels",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                data = {
                    "pdf_file": self.current_pdf_path,
                    "shape_file": self.current_json_path,
                    "labels": [
                        {
                            "shape_index": label.shape_index,
                            "text_lines": label.text_lines,
                            "position": label.position,
                            "line_font_sizes": label.line_font_sizes,
                            "line_font_colors": label.line_font_colors,
                            "line_bg_colors": label.line_bg_colors,
                            "line_variables": label.line_variables,
                            "has_leader": label.has_leader,
                            "leader_points": label.leader_points
                        }
                        for label in self.labels
                    ]
                }
                
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                messagebox.showinfo("Success", "Labels saved successfully")
                self.status_var.set(f"Labels saved to {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error saving labels: {str(e)}")
    
    def load_labels(self):
        """Load labels from JSON file"""
        file_path = filedialog.askopenfilename(
            title="Load Labels",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Validate that PDF and shapes are loaded
                if not self.pdf_image:
                    messagebox.showwarning(
                        "Warning", 
                        "Please load a PDF file first before loading labels."
                    )
                    return
                
                if not self.shapes:
                    messagebox.showwarning(
                        "Warning", 
                        "Please load a JSON shapes file first before loading labels."
                    )
                    return
                
                # Check if this label file references specific files
                if "pdf_file" in data and data["pdf_file"]:
                    expected_pdf = os.path.basename(data["pdf_file"])
                    current_pdf = os.path.basename(self.current_pdf_path) if self.current_pdf_path else "None"
                    if expected_pdf != current_pdf:
                        response = messagebox.askyesno(
                            "File Mismatch",
                            f"Labels were created for PDF: {expected_pdf}\n"
                            f"Currently loaded: {current_pdf}\n\n"
                            f"Labels may not align correctly. Continue anyway?"
                        )
                        if not response:
                            return
                
                # Clear existing labels
                self.labels.clear()
                
                # Load labels with validation
                labels_data = data.get("labels", [])
                if not labels_data:
                    messagebox.showwarning("Warning", "No labels found in file")
                    return
                
                loaded_count = 0
                for i, label_data in enumerate(labels_data):
                    try:
                        # Validate required fields
                        if "shape_index" not in label_data:
                            print(f"Warning: Label {i} missing shape_index, skipping")
                            continue
                        
                        if "position" not in label_data:
                            print(f"Warning: Label {i} missing position, skipping")
                            continue
                        
                        shape_index = label_data["shape_index"]
                        
                        # Validate shape index
                        if shape_index >= len(self.shapes):
                            print(f"Warning: Label {i} references shape {shape_index} which doesn't exist, skipping")
                            continue
                        
                        # Create label
                        label = TextLabel(
                            shape_index,
                            tuple(label_data["position"])
                        )
                        label.text_lines = label_data.get("text_lines", [""])
                        
                        # Load per-line formatting (new format)
                        if "line_font_sizes" in label_data:
                            label.line_font_sizes = label_data["line_font_sizes"]
                        else:
                            # Backward compatibility: convert old single font_size to array
                            font_size = label_data.get("font_size", 12)
                            label.line_font_sizes = [font_size] * len(label.text_lines)
                        
                        if "line_font_colors" in label_data:
                            label.line_font_colors = label_data["line_font_colors"]
                        else:
                            # Backward compatibility: convert old single font_color to array
                            font_color = label_data.get("font_color", "#000000")
                            label.line_font_colors = [font_color] * len(label.text_lines)
                        
                        if "line_bg_colors" in label_data:
                            label.line_bg_colors = label_data["line_bg_colors"]
                        else:
                            # Default background color for all lines
                            label.line_bg_colors = ["#FFFFFF"] * len(label.text_lines)
                        
                        if "line_variables" in label_data:
                            label.line_variables = label_data["line_variables"]
                        else:
                            # Default: no variable assignment for all lines
                            label.line_variables = ["None"] * len(label.text_lines)
                        
                        label.has_leader = label_data.get("has_leader", False)
                        label.leader_points = label_data.get("leader_points", [])
                        
                        self.labels.append(label)
                        loaded_count += 1
                        
                    except Exception as e:
                        print(f"Error loading label {i}: {str(e)}")
                        continue
                
                # Redraw
                self.display_canvas()
                self.update_shape_list()
                
                messagebox.showinfo(
                    "Success", 
                    f"Loaded {loaded_count} of {len(labels_data)} labels successfully"
                )
                self.status_var.set(f"Loaded {loaded_count} labels from {os.path.basename(file_path)}")
                
            except json.JSONDecodeError as e:
                messagebox.showerror(
                    "Error", 
                    f"Invalid JSON file: {str(e)}\n\nPlease check the file format."
                )
            except KeyError as e:
                messagebox.showerror(
                    "Error", 
                    f"Missing required field in JSON: {str(e)}\n\nFile may be corrupted."
                )
            except Exception as e:
                messagebox.showerror(
                    "Error", 
                    f"Error loading labels: {str(e)}\n\nCheck console for details."
                )
                import traceback
                traceback.print_exc()
    
    def export_image(self):
        """Export final image with labels - includes entire canvas with all labels"""
        if not self.pdf_image:
            messagebox.showwarning("Warning", "No PDF loaded to export")
            return
        
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        file_path = filedialog.asksaveasfilename(
            title="Export Image",
            initialdir=script_dir,
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # CRITICAL FIX: Calculate bounding box that includes ALL labels
                # Start with PDF dimensions
                pdf_width, pdf_height = self.pdf_image.size
                min_x, min_y = 0, 0
                max_x, max_y = pdf_width, pdf_height
                
                # Expand bounding box to include all labels
                for label in self.labels:
                    text_lines = [line for line in label.text_lines if line.strip()]
                    if text_lines:
                        x, y = label.position
                        
                        # Estimate label box size (MUST match draw_labels_on_export calculation)
                        padding_x = 15  # Must match actual drawing code
                        padding_y = 8   # Must match actual drawing code
                        
                        # Create temporary draw to measure text
                        temp_img = Image.new('RGB', (1, 1))
                        temp_draw = ImageDraw.Draw(temp_img)
                        
                        try:
                            line_widths = []
                            line_heights = []
                            for i, line in enumerate(text_lines):
                                # Get per-line font size
                                if i < len(label.line_font_sizes):
                                    font_size = label.line_font_sizes[i]
                                else:
                                    font_size = 12
                                
                                try:
                                    custom_font = ImageFont.truetype("arial.ttf", font_size)
                                except:
                                    try:
                                        custom_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
                                    except:
                                        custom_font = ImageFont.load_default()
                                
                                bbox = temp_draw.textbbox((0, 0), line, font=custom_font)
                                text_width = bbox[2] - bbox[0]
                                # Add 10% safety margin (matching actual drawing)
                                line_widths.append(int(text_width * 1.1))
                                line_heights.append(bbox[3] - bbox[1])
                            
                            max_width = max(line_widths) if line_widths else 0
                            # Calculate total height (boxes stacked with no gaps)
                            total_height = sum(line_heights[i] + (padding_y * 2) for i in range(len(line_heights)))
                        except:
                            max_width = max(len(line) * 10 for line in text_lines)
                            total_height = len(text_lines) * 30
                        
                        box_width = max_width + (padding_x * 2)
                        box_height = total_height
                        
                        # Update bounding box
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x + box_width)
                        max_y = max(max_y, y + box_height)
                        
                        # Also include leader lines
                        if label.has_leader and label.leader_points:
                            for point in label.leader_points:
                                min_x = min(min_x, point[0])
                                min_y = min(min_y, point[1])
                                max_x = max(max_x, point[0])
                                max_y = max(max_y, point[1])
                
                # Add some padding around the entire composition
                padding = 20
                min_x -= padding
                min_y -= padding
                max_x += padding
                max_y += padding
                
                # Calculate canvas size
                canvas_width = int(max_x - min_x)
                canvas_height = int(max_y - min_y)
                
                # Create expanded canvas
                export_image = Image.new('RGB', (canvas_width, canvas_height), 'white')
                
                # Paste PDF at offset position
                pdf_offset_x = int(-min_x)
                pdf_offset_y = int(-min_y)
                export_image.paste(self.pdf_image, (pdf_offset_x, pdf_offset_y))
                
                # Draw shapes (with offset)
                if self.shapes:
                    export_image = self.draw_shapes_on_export(export_image, offset=(pdf_offset_x, pdf_offset_y))
                
                # Draw labels (with offset)
                export_image = self.draw_labels_on_export(export_image, offset=(pdf_offset_x, pdf_offset_y))
                
                export_image.save(file_path)
                messagebox.showinfo("Success", f"Image exported successfully\n\nCanvas size: {canvas_width}x{canvas_height}px")
                self.status_var.set(f"Image exported to {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting image: {str(e)}")
                import traceback
                traceback.print_exc()
    
    def draw_shapes_on_export(self, image: Image.Image, offset=(0, 0)) -> Image.Image:
        """Draw shapes on export image with optional offset"""
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        offset_x, offset_y = offset
        
        for shape in self.shapes:
            coords = shape["coordinates"]
            color_hex = shape.get("color", "#FF0000")
            shape_type = shape.get("type", "rectangle")
            
            color_rgb = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            color_rgba = color_rgb + (80,)
            
            # Apply offset to coordinates
            offset_coords = [coords[i] + (offset_x if i % 2 == 0 else offset_y) for i in range(len(coords))]
            
            if shape_type == "rectangle":
                draw.rectangle(offset_coords, fill=color_rgba, outline=color_rgb + (150,), width=2)
            elif shape_type == "polygon":
                points = [(offset_coords[i], offset_coords[i+1]) for i in range(0, len(offset_coords), 2)]
                draw.polygon(points, fill=color_rgba, outline=color_rgb + (150,), width=2)
            elif shape_type == "oval":
                # Oval coordinates: [x1, y1, x2, y2] (bounding box)
                draw.ellipse(offset_coords, fill=color_rgba, outline=color_rgb + (150,), width=2)
            elif shape_type == "circle":
                # Circle coordinates: [cx, cy, radius]
                cx, cy, radius = coords
                x1 = cx - radius + offset_x
                y1 = cy - radius + offset_y
                x2 = cx + radius + offset_x
                y2 = cy + radius + offset_y
                draw.ellipse([x1, y1, x2, y2], fill=color_rgba, outline=color_rgb + (150,), width=2)
        
        image = image.convert('RGBA')
        image = Image.alpha_composite(image, overlay)
        return image
    
    def draw_labels_on_export(self, image: Image.Image, offset=(0, 0)) -> Image.Image:
        """Draw labels and leader lines on export image with per-line formatting"""
        draw = ImageDraw.Draw(image)
        
        offset_x, offset_y = offset
        
        for label in self.labels:
            # Draw leader line if needed (with offset)
            if label.has_leader and label.leader_points:
                line_coords = []
                for point in label.leader_points:
                    line_coords.append((point[0] + offset_x, point[1] + offset_y))
                
                if len(line_coords) >= 2:
                    draw.line(line_coords, fill="#666666", width=3)
                    
                    # Draw arrowhead
                    end_point = line_coords[-1]
                    start_point = line_coords[-2] if len(line_coords) > 1 else line_coords[0]
                    
                    # Calculate arrow direction
                    dx = end_point[0] - start_point[0]
                    dy = end_point[1] - start_point[1]
                    length = math.sqrt(dx*dx + dy*dy)
                    
                    if length > 0:
                        dx /= length
                        dy /= length
                        
                        # Arrow head size
                        arrow_size = 10
                        arrow_angle = math.pi / 6
                        
                        # Calculate arrow points
                        left_x = end_point[0] - arrow_size * (dx * math.cos(arrow_angle) + dy * math.sin(arrow_angle))
                        left_y = end_point[1] - arrow_size * (dy * math.cos(arrow_angle) - dx * math.sin(arrow_angle))
                        
                        right_x = end_point[0] - arrow_size * (dx * math.cos(arrow_angle) - dy * math.sin(arrow_angle))
                        right_y = end_point[1] - arrow_size * (dy * math.cos(arrow_angle) + dx * math.sin(arrow_angle))
                        
                        draw.polygon([end_point, (left_x, left_y), (right_x, right_y)], fill="#666666")
            
            # Draw text background with per-line formatting (with offset)
            text_lines = [line for line in label.text_lines if line.strip()]
            if text_lines:
                x, y = label.position[0] + offset_x, label.position[1] + offset_y
                
                # Calculate dimensions for each line with its own font size
                padding_x = 10
                padding_y = 8
                line_heights = []
                line_widths = []
                fonts = []
                
                # Store display texts with units for later use
                display_texts = []
                
                for i, text in enumerate(text_lines):
                    # Get per-line font size
                    if i < len(label.line_font_sizes):
                        font_size = label.line_font_sizes[i]
                    else:
                        font_size = 12
                    
                    # Load font
                    try:
                        custom_font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        try:
                            custom_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
                        except:
                            custom_font = ImageFont.load_default()
                    
                    fonts.append(custom_font)
                    
                    # Prepare display text - add unit if Sales/Area is checked
                    display_text = text
                    if i < len(label.line_is_sales) and label.line_is_sales[i]:
                        # Sales/Area is checked, append unit metric
                        if i < len(label.line_unit_metric) and label.line_unit_metric[i] != "None":
                            unit_str = label.line_unit_metric[i]
                            # Extract just the unit symbol (e.g., "m²" from "m² (Square Meter)")
                            if "(" in unit_str:
                                unit_symbol = unit_str.split("(")[0].strip()
                            else:
                                unit_symbol = unit_str
                            display_text = f"{text} {unit_symbol}"
                    
                    # Store the display text for later use
                    display_texts.append(display_text)
                    
                    # Measure text (using display_text which includes unit if applicable)
                    try:
                        bbox = draw.textbbox((0, 0), display_text, font=custom_font)
                        text_width = bbox[2] - bbox[0]
                        # Add 10% safety margin to prevent cutoff
                        line_widths.append(int(text_width * 1.1))
                        line_heights.append(bbox[3] - bbox[1])
                    except:
                        line_widths.append(len(display_text) * (font_size * 0.6))
                        line_heights.append(font_size + 4)

                
                # Calculate box dimensions
                max_width = max(line_widths) if line_widths else 0
                # Auto-scale spacing based on text size (20% of average font size)
                avg_font_size = sum(label.line_font_sizes[:len(text_lines)]) / len(text_lines) if text_lines else 12
                line_spacing_per_line = int(avg_font_size * 0.2)  # 20% of font size
                line_spacing = line_spacing_per_line * (len(line_heights) - 1) if len(line_heights) > 1 else 0
                total_height = sum(line_heights) + line_spacing if line_heights else 0
                box_width = max_width + (padding_x * 2)
                box_height = total_height + (padding_y * 2)
                
                # Draw per-line background boxes and text
                current_y = y
                for i, text in enumerate(text_lines):
                    # Get per-line background color
                    if i < len(label.line_bg_colors):
                        bg_color = label.line_bg_colors[i]
                    else:
                        bg_color = "#FFFFFF"
                    
                    # Calculate box dimensions (UNIFORM width for all lines - matching canvas)
                    padding_x = 15  # Increased padding for more space
                    padding_y = 8  # Increased vertical padding to prevent text cutoff
                    line_box_width = max_width + (padding_x * 2)  # Same width for all lines
                    line_box_height = line_heights[i] + (padding_y * 2)
                    
                    # Draw background box for this line WITHOUT BORDER
                    draw.rectangle(
                        [x, current_y, x + line_box_width, current_y + line_box_height],
                        fill=bg_color,
                        outline=None,
                        width=0
                    )
                    
                    # Get per-line text color
                    if i < len(label.line_font_colors):
                        text_color = label.line_font_colors[i]
                    else:
                        text_color = "#000000"
                    
                    # Use the pre-calculated display text (already includes unit if applicable)
                    display_text = display_texts[i]
                    
                    # Draw text centered horizontally, with padding from top
                    # (Vertical centering calculation can cause cutoff issues)
                    text_x = x + (line_box_width - line_widths[i]) / 2
                    text_y = current_y + padding_y
                    draw.text((text_x, text_y), display_text, fill=text_color, font=fonts[i])
                    
                    # Move to next line (boxes touch each other - matching preview)
                    current_y += line_box_height

        
        return image
    
    # ===== Conditional Coloring Methods =====
    
    def toggle_conditional_coloring(self):
        """Toggle conditional coloring on/off"""
        self.conditional_coloring_enabled = self.cond_enabled_var.get()
        if self.conditional_coloring_enabled:
            self.status_var.set("Conditional coloring enabled")
        else:
            self.status_var.set("Conditional coloring disabled")
    
    def add_color_rule_ui(self):
        """Add a new color rule to the UI"""
        rule = ColorRule(operator=">", threshold=0, color="#FF0000")
        self.color_rules.append(rule)
        self.create_rule_widget(rule, len(self.color_rules) - 1)
    
    def create_rule_widget(self, rule: ColorRule, index: int):
        """Create a widget for a color rule"""
        rule_frame = ttk.Frame(self.rules_container, relief=tk.GROOVE, borderwidth=1)
        rule_frame.pack(fill=tk.X, pady=2, padx=2)
        
        # Operator dropdown
        operator_var = tk.StringVar(value=rule.operator)
        operator_combo = ttk.Combobox(
            rule_frame,
            textvariable=operator_var,
            values=[">", ">=", "<", "<=", "==", "!="],
            state="readonly",
            width=4
        )
        operator_combo.pack(side=tk.LEFT, padx=2)
        operator_combo.set(rule.operator)
        
        # Threshold entry
        threshold_var = tk.DoubleVar(value=rule.threshold)
        threshold_entry = ttk.Entry(rule_frame, textvariable=threshold_var, width=10)
        threshold_entry.pack(side=tk.LEFT, padx=2)
        
        # Color button
        color_btn = tk.Button(
            rule_frame,
            text="■",
            bg=rule.color,
            fg="white",
            width=3,
            relief=tk.RAISED,
            bd=1,
            command=lambda: self.pick_rule_color(rule, color_btn)
        )
        color_btn.pack(side=tk.LEFT, padx=2)
        
        # Remove button
        remove_btn = ttk.Button(
            rule_frame,
            text="×",
            width=3,
            command=lambda: self.remove_color_rule(index, rule_frame)
        )
        remove_btn.pack(side=tk.LEFT, padx=2)
        
        # Store references
        rule_frame.operator_var = operator_var
        rule_frame.threshold_var = threshold_var
        rule_frame.color_btn = color_btn
        rule_frame.rule_index = index
        
        # Bind changes to update rule
        operator_var.trace_add("write", lambda *args: self.update_rule_from_widget(rule, rule_frame))
        threshold_var.trace_add("write", lambda *args: self.update_rule_from_widget(rule, rule_frame))
    
    def update_rule_from_widget(self, rule: ColorRule, rule_frame):
        """Update rule object from widget values"""
        try:
            rule.operator = rule_frame.operator_var.get()
            rule.threshold = rule_frame.threshold_var.get()
        except:
            pass  # Ignore invalid values during editing
    
    def pick_rule_color(self, rule: ColorRule, color_btn):
        """Open color picker for a rule"""
        color = colorchooser.askcolor(title="Choose Rule Color", initialcolor=rule.color)
        if color[1]:
            rule.color = color[1]
            color_btn.config(bg=color[1])
    
    def remove_color_rule(self, index: int, rule_frame):
        """Remove a color rule"""
        if index < len(self.color_rules):
            self.color_rules.pop(index)
            rule_frame.destroy()
            # Rebuild all rule widgets to update indices
            self.rebuild_rules_ui()
    
    def rebuild_rules_ui(self):
        """Rebuild all rule widgets"""
        # Clear existing widgets
        for widget in self.rules_container.winfo_children():
            widget.destroy()
        
        # Recreate widgets
        for i, rule in enumerate(self.color_rules):
            self.create_rule_widget(rule, i)
    
    def extract_number_from_text(self, text: str) -> Optional[float]:
        """Extract a number from text string"""
        if not text:
            return None
        
        # Remove common currency symbols and commas
        cleaned = text.replace('$', '').replace(',', '').replace('฿', '').replace('€', '').replace('£', '')
        
        # Try to find a number (including decimals)
        match = re.search(r'-?\d+\.?\d*', cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None
    
    def evaluate_rules_for_value(self, value: float) -> Optional[str]:
        """Evaluate all rules and return the color for the first matching rule"""
        for rule in self.color_rules:
            if rule.evaluate(value):
                return rule.color
        return None
    
    def apply_conditional_colors(self):
        """Apply conditional colors to all shapes based on label values"""
        if not self.conditional_coloring_enabled:
            messagebox.showinfo("Info", "Please enable conditional coloring first")
            return
        
        if not self.labels:
            messagebox.showinfo("Info", "No labels to process")
            return
        
        if not self.color_rules:
            messagebox.showinfo("Info", "Please add at least one color rule")
            return
        
        # Backup original colors if not already done
        if not self.original_shape_colors:
            for i, shape in enumerate(self.shapes):
                self.original_shape_colors[i] = shape.get("color", "#CCCCCC")
        
        # Get value line index
        value_line_idx = self.value_line_var.get()
        
        # Process each label
        colored_count = 0
        for label in self.labels:
            # Get the value from the specified line
            if value_line_idx < len(label.text_lines):
                value_text = label.text_lines[value_line_idx]
                value = self.extract_number_from_text(value_text)
                
                if value is not None:
                    # Evaluate rules
                    color = self.evaluate_rules_for_value(value)
                    
                    if color and label.shape_index < len(self.shapes):
                        # Apply color to shape
                        self.shapes[label.shape_index]["color"] = color
                        colored_count += 1
        
        # Redraw canvas
        self.display_canvas()
        
        self.status_var.set(f"Applied conditional colors to {colored_count} shapes")
        messagebox.showinfo("Success", f"Applied colors to {colored_count} shapes")
    
    def clear_shape_colors(self):
        """Clear conditional colors and restore original colors"""
        if not self.original_shape_colors:
            messagebox.showinfo("Info", "No colors to clear")
            return
        
        # Restore original colors
        for i, original_color in self.original_shape_colors.items():
            if i < len(self.shapes):
                self.shapes[i]["color"] = original_color
        
        # Clear backup
        self.original_shape_colors.clear()
        
        # Redraw canvas
        self.display_canvas()
        
        self.status_var.set("Cleared conditional colors")
        messagebox.showinfo("Success", "Cleared all conditional colors")
    
    # ===== Variable Manager Methods =====
    
    def open_variable_manager(self):
        """Open the Variable Manager dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Variable Manager")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Variables list
        list_frame = ttk.LabelFrame(dialog, text="Variables", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        var_listbox = tk.Listbox(list_container, yscrollcommand=scrollbar.set, font=("Arial", 10))
        var_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=var_listbox.yview)
        
        # Populate listbox
        def refresh_list():
            var_listbox.delete(0, tk.END)
            for var in self.variables:
                rule_count = len(var.rules)
                var_listbox.insert(tk.END, f"{var.name} ({rule_count} rules)")
        
        refresh_list()
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def add_variable():
            self.create_variable_dialog(dialog, refresh_list)
        
        def edit_variable():
            selection = var_listbox.curselection()
            if selection:
                var_index = selection[0]
                self.edit_variable_dialog(dialog, self.variables[var_index], refresh_list)
            else:
                messagebox.showinfo("Info", "Please select a variable to edit")
        
        def delete_variable():
            selection = var_listbox.curselection()
            if selection:
                var_index = selection[0]
                var_name = self.variables[var_index].name
                if messagebox.askyesno("Confirm Delete", f"Delete variable '{var_name}'?"):
                    self.variables.pop(var_index)
                    refresh_list()
                    self.update_variables_summary()
            else:
                messagebox.showinfo("Info", "Please select a variable to delete")
        
        ttk.Button(btn_frame, text="+ New Variable", command=add_variable, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Edit", command=edit_variable, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete", command=delete_variable, width=10).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(dialog, text="Close", command=dialog.destroy, width=15).pack(pady=10)
    
    def create_variable_dialog(self, parent, refresh_callback):
        """Create a new variable"""
        dialog = tk.Toplevel(parent)
        dialog.title("New Variable")
        dialog.geometry("550x650")  # Increased size to fit all sections
        dialog.transient(parent)
        dialog.grab_set()
        
        # Variable name
        name_frame = ttk.Frame(dialog)
        name_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(name_frame, text="Variable Name:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var, font=("Arial", 10), width=30)
        name_entry.pack(side=tk.LEFT)
        name_entry.focus()
        
        # Text Formatting Section
        format_frame = ttk.LabelFrame(dialog, text="Text Formatting (Optional)", padding=10)
        format_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Text Color
        text_color_frame = ttk.Frame(format_frame)
        text_color_frame.pack(fill=tk.X, pady=2)
        ttk.Label(text_color_frame, text="Text Color:", width=12).pack(side=tk.LEFT)
        text_color_var = tk.StringVar(value="")
        text_color_btn = tk.Button(text_color_frame, text="⬛", 
                                   bg="#CCCCCC",
                                   width=3, relief=tk.RAISED, bd=1,
                                   command=lambda: self.pick_color_for_rule(text_color_var, text_color_btn))
        text_color_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(text_color_frame, text="Clear", width=6,
                  command=lambda: [text_color_var.set(""), text_color_btn.config(bg="#CCCCCC")]).pack(side=tk.LEFT)
        
        # BG Color
        bg_color_frame = ttk.Frame(format_frame)
        bg_color_frame.pack(fill=tk.X, pady=2)
        ttk.Label(bg_color_frame, text="BG Color:", width=12).pack(side=tk.LEFT)
        bg_color_var = tk.StringVar(value="")
        bg_color_btn = tk.Button(bg_color_frame, text="⬛",
                                bg="#CCCCCC",
                                width=3, relief=tk.RAISED, bd=1,
                                command=lambda: self.pick_color_for_rule(bg_color_var, bg_color_btn))
        bg_color_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(bg_color_frame, text="Clear", width=6,
                  command=lambda: [bg_color_var.set(""), bg_color_btn.config(bg="#CCCCCC")]).pack(side=tk.LEFT)
        
        # Text Size
        size_frame = ttk.Frame(format_frame)
        size_frame.pack(fill=tk.X, pady=2)
        ttk.Label(size_frame, text="Font Size:", width=12).pack(side=tk.LEFT)
        text_size_var = tk.IntVar(value=0)
        ttk.Spinbox(size_frame, from_=0, to=72, textvariable=text_size_var, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(size_frame, text="(0 = no change)", font=("Arial", 8), foreground="gray").pack(side=tk.LEFT)
        
        # Auto Unit Settings Section
        auto_sales_frame = ttk.LabelFrame(dialog, text="Auto Unit Settings", padding=10)
        auto_sales_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Auto-enable Area checkbox
        auto_enable_frame = ttk.Frame(auto_sales_frame)
        auto_enable_frame.pack(fill=tk.X, pady=2)
        auto_enable_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(auto_enable_frame, text="Auto-enable Area when variable is selected",
                       variable=auto_enable_var).pack(side=tk.LEFT)
        
        # Default unit dropdown
        unit_frame = ttk.Frame(auto_sales_frame)
        unit_frame.pack(fill=tk.X, pady=2)
        ttk.Label(unit_frame, text="Default Unit:", width=12).pack(side=tk.LEFT)
        default_unit_var = tk.StringVar(value="None")
        unit_options = ["None", "m² (Square Meter)", "m³ (Cubic Meter)", "ft² (Square Feet)", 
                       "ft³ (Cubic Feet)", "ha (Hectare)", "acre"]
        ttk.Combobox(unit_frame, textvariable=default_unit_var, values=unit_options, 
                    state="readonly", width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(unit_frame, text="(used when auto-enabled)", font=("Arial", 8), 
                 foreground="gray").pack(side=tk.LEFT)
        
        # Rules list
        rules_frame = ttk.LabelFrame(dialog, text="Color Rules", padding=10)
        rules_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        rules_container = ttk.Frame(rules_frame)
        rules_container.pack(fill=tk.BOTH, expand=True)
        
        temp_rules = []
        
        def add_rule():
            rule_frame = ttk.Frame(rules_container, relief=tk.GROOVE, borderwidth=1)
            rule_frame.pack(fill=tk.X, pady=2)
            
            operator_var = tk.StringVar(value=">")
            ttk.Combobox(rule_frame, textvariable=operator_var, values=[">", ">=", "<", "<=", "==", "!="], state="readonly", width=4).pack(side=tk.LEFT, padx=2)
            
            threshold_var = tk.DoubleVar(value=0)
            ttk.Entry(rule_frame, textvariable=threshold_var, width=10).pack(side=tk.LEFT, padx=2)
            
            color_var = tk.StringVar(value="#FF0000")
            color_btn = tk.Button(rule_frame, text="■", bg="#FF0000", width=3,
                                 command=lambda: self.pick_color_for_rule(color_var, color_btn))
            color_btn.pack(side=tk.LEFT, padx=2)
            
            ttk.Button(rule_frame, text="×", width=3, command=rule_frame.destroy).pack(side=tk.LEFT, padx=2)
            
            temp_rules.append((operator_var, threshold_var, color_var, rule_frame))
        
        ttk.Button(rules_frame, text="+ Add Rule", command=add_rule).pack(pady=5)
        
        # Save button
        def save_variable():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Please enter a variable name")
                return
            
            # Check for duplicate names
            if any(v.name == name for v in self.variables):
                messagebox.showwarning("Warning", f"Variable '{name}' already exists")
                return
            
            var = Variable(name)
            
            # Add color rules
            for operator_var, threshold_var, color_var, _ in temp_rules:
                try:
                    var.add_rule(operator_var.get(), threshold_var.get(), color_var.get())
                except:
                    pass
            
            # Save text formatting properties
            var.text_color = text_color_var.get() if text_color_var.get() else None
            var.bg_color = bg_color_var.get() if bg_color_var.get() else None
            var.text_size = text_size_var.get() if text_size_var.get() > 0 else None
            
            # Save auto Unit settings
            var.auto_enable_sales = auto_enable_var.get()
            var.default_unit = default_unit_var.get()
            
            self.variables.append(var)
            self.update_variables_summary()
            refresh_callback()
            dialog.destroy()
            messagebox.showinfo("Success", f"Variable '{name}' created")
        
        ttk.Button(dialog, text="Save Variable", command=save_variable, width=15).pack(pady=10)
    
    def edit_variable_dialog(self, parent, variable, refresh_callback):
        """Edit an existing variable"""
        dialog = tk.Toplevel(parent)
        dialog.title(f"Edit Variable: {variable.name}")
        dialog.geometry("550x650")  # Increased height to show all controls
        dialog.transient(parent)
        dialog.grab_set()
        
        # Variable name (now editable)
        name_frame = ttk.Frame(dialog)
        name_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(name_frame, text="Variable Name:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        name_var = tk.StringVar(value=variable.name)
        name_entry = ttk.Entry(name_frame, textvariable=name_var, font=("Arial", 10), width=30)
        name_entry.pack(side=tk.LEFT)

        
        # Text Formatting Section (NEW)
        format_frame = ttk.LabelFrame(dialog, text="Text Formatting (Optional)", padding=10)
        format_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Text Color
        text_color_frame = ttk.Frame(format_frame)
        text_color_frame.pack(fill=tk.X, pady=2)
        ttk.Label(text_color_frame, text="Text Color:", width=12).pack(side=tk.LEFT)
        text_color_var = tk.StringVar(value=variable.text_color if variable.text_color else "")
        text_color_display = variable.text_color if variable.text_color else "#CCCCCC"
        text_color_btn = tk.Button(text_color_frame, text="⬛", 
                                   bg=text_color_display,
                                   width=3, relief=tk.RAISED, bd=1,
                                   command=lambda: self.pick_color_for_rule(text_color_var, text_color_btn))
        text_color_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(text_color_frame, text="Clear", width=6,
                  command=lambda: [text_color_var.set(""), text_color_btn.config(bg="#CCCCCC")]).pack(side=tk.LEFT)
        
        # BG Color
        bg_color_frame = ttk.Frame(format_frame)
        bg_color_frame.pack(fill=tk.X, pady=2)
        ttk.Label(bg_color_frame, text="BG Color:", width=12).pack(side=tk.LEFT)
        bg_color_var = tk.StringVar(value=variable.bg_color if variable.bg_color else "")
        bg_color_display = variable.bg_color if variable.bg_color else "#CCCCCC"
        bg_color_btn = tk.Button(bg_color_frame, text="⬛",
                                bg=bg_color_display,
                                width=3, relief=tk.RAISED, bd=1,
                                command=lambda: self.pick_color_for_rule(bg_color_var, bg_color_btn))
        bg_color_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(bg_color_frame, text="Clear", width=6,
                  command=lambda: [bg_color_var.set(""), bg_color_btn.config(bg="#CCCCCC")]).pack(side=tk.LEFT)
        
        # Text Size
        size_frame = ttk.Frame(format_frame)
        size_frame.pack(fill=tk.X, pady=2)
        ttk.Label(size_frame, text="Font Size:", width=12).pack(side=tk.LEFT)
        text_size_var = tk.IntVar(value=variable.text_size if variable.text_size else 0)
        ttk.Spinbox(size_frame, from_=0, to=72, textvariable=text_size_var, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(size_frame, text="(0 = no change)", font=("Arial", 8), foreground="gray").pack(side=tk.LEFT)
        
        # Auto Unit Settings Section (NEW)
        auto_sales_frame = ttk.LabelFrame(dialog, text="Auto Unit Settings", padding=10)
        auto_sales_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Auto-enable Area checkbox
        auto_enable_frame = ttk.Frame(auto_sales_frame)
        auto_enable_frame.pack(fill=tk.X, pady=2)
        auto_enable_var = tk.BooleanVar(value=variable.auto_enable_sales)
        ttk.Checkbutton(auto_enable_frame, text="Auto-enable Area when variable is selected",
                       variable=auto_enable_var).pack(side=tk.LEFT)
        
        # Default unit dropdown
        unit_frame = ttk.Frame(auto_sales_frame)
        unit_frame.pack(fill=tk.X, pady=2)
        ttk.Label(unit_frame, text="Default Unit:", width=12).pack(side=tk.LEFT)
        default_unit_var = tk.StringVar(value=variable.default_unit)
        unit_options = ["None", "m² (Square Meter)", "m³ (Cubic Meter)", "ft² (Square Feet)", 
                       "ft³ (Cubic Feet)", "ha (Hectare)", "acre"]
        ttk.Combobox(unit_frame, textvariable=default_unit_var, values=unit_options, 
                    state="readonly", width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(unit_frame, text="(used when auto-enabled)", font=("Arial", 8), 
                 foreground="gray").pack(side=tk.LEFT)

        
        # Rules list
        rules_frame = ttk.LabelFrame(dialog, text="Color Rules", padding=10)
        rules_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        rules_container = ttk.Frame(rules_frame)
        rules_container.pack(fill=tk.BOTH, expand=True)
        
        temp_rules = []
        
        # Load existing rules
        for rule in variable.rules:
            rule_frame = ttk.Frame(rules_container, relief=tk.GROOVE, borderwidth=1)
            rule_frame.pack(fill=tk.X, pady=2)
            
            operator_var = tk.StringVar(value=rule.operator)
            ttk.Combobox(rule_frame, textvariable=operator_var, values=[">", ">=", "<", "<=", "==", "!="], state="readonly", width=4).pack(side=tk.LEFT, padx=2)
            
            threshold_var = tk.DoubleVar(value=rule.threshold)
            ttk.Entry(rule_frame, textvariable=threshold_var, width=10).pack(side=tk.LEFT, padx=2)
            
            color_var = tk.StringVar(value=rule.color)
            color_btn = tk.Button(rule_frame, text="■", bg=rule.color, width=3)
            
            # Fix lambda scoping by creating a helper function
            def make_color_picker(cv, cb):
                return lambda: self.pick_color_for_rule(cv, cb)
            
            color_btn.config(command=make_color_picker(color_var, color_btn))
            color_btn.pack(side=tk.LEFT, padx=2)
            
            ttk.Button(rule_frame, text="×", width=3, command=rule_frame.destroy).pack(side=tk.LEFT, padx=2)
            
            temp_rules.append((operator_var, threshold_var, color_var, rule_frame))
        
        def add_rule():
            rule_frame = ttk.Frame(rules_container, relief=tk.GROOVE, borderwidth=1)
            rule_frame.pack(fill=tk.X, pady=2)
            
            operator_var = tk.StringVar(value=">")
            ttk.Combobox(rule_frame, textvariable=operator_var, values=[">", ">=", "<", "<=", "==", "!="], state="readonly", width=4).pack(side=tk.LEFT, padx=2)
            
            threshold_var = tk.DoubleVar(value=0)
            ttk.Entry(rule_frame, textvariable=threshold_var, width=10).pack(side=tk.LEFT, padx=2)
            
            color_var = tk.StringVar(value="#FF0000")
            color_btn = tk.Button(rule_frame, text="■", bg="#FF0000", width=3,
                                 command=lambda: self.pick_color_for_rule(color_var, color_btn))
            color_btn.pack(side=tk.LEFT, padx=2)
            
            ttk.Button(rule_frame, text="×", width=3, command=rule_frame.destroy).pack(side=tk.LEFT, padx=2)
            
            temp_rules.append((operator_var, threshold_var, color_var, rule_frame))
        
        ttk.Button(rules_frame, text="+ Add Rule", command=add_rule).pack(pady=5)
        
        # Save button
        def save_changes():
            # Get new name and validate
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showerror("Error", "Variable name cannot be empty")
                return
            
            # Check if name changed and if new name already exists
            old_name = variable.name
            if new_name != old_name:
                # Check for duplicate name
                for v in self.variables:
                    if v != variable and v.name == new_name:
                        messagebox.showerror("Error", f"Variable '{new_name}' already exists")
                        return
                
                # Update variable name
                variable.name = new_name
                
                # Update all label references from old name to new name
                for label in self.labels:
                    for i, var_name in enumerate(label.line_variables):
                        if var_name == old_name:
                            label.line_variables[i] = new_name
            
            variable.rules.clear()
            for operator_var, threshold_var, color_var, frame in temp_rules:
                if frame.winfo_exists():
                    try:
                        variable.add_rule(operator_var.get(), threshold_var.get(), color_var.get())
                    except:
                        pass
            
            # Save text formatting properties
            variable.text_color = text_color_var.get() if text_color_var.get() else None
            variable.bg_color = bg_color_var.get() if bg_color_var.get() else None
            variable.text_size = text_size_var.get() if text_size_var.get() > 0 else None
            
            # Save auto Sales/Area settings
            variable.auto_enable_sales = auto_enable_var.get()
            variable.default_unit = default_unit_var.get()
            
            self.update_variables_summary()
            refresh_callback()
            dialog.destroy()
            messagebox.showinfo("Success", f"Variable '{variable.name}' updated")


        
        ttk.Button(dialog, text="Save Changes", command=save_changes, width=15).pack(pady=10)
    
    def pick_color_for_rule(self, color_var, color_btn):
        """Pick color for a rule"""
        # Get current color, use default if empty
        current_color = color_var.get() if color_var.get() else "#FF0000"
        color = colorchooser.askcolor(title="Choose Color", initialcolor=current_color)
        if color[1]:
            color_var.set(color[1])
            color_btn.config(bg=color[1])
    
    def update_variables_summary(self):
        """Update the variables summary label"""
        if not self.variables:
            self.variables_summary_var.set("No variables defined")
        else:
            var_names = [v.name for v in self.variables]
            if len(var_names) <= 3:
                self.variables_summary_var.set(f"Variables: {', '.join(var_names)}")
            else:
                self.variables_summary_var.set(f"{len(var_names)} variables defined")
    
    def export_conditions(self):
        """Export all variables and their rules to a JSON file"""
        if not self.variables:
            messagebox.showinfo("Info", "No variables to export")
            return
        
        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            title="Export Conditions",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Build export data
            export_data = {
                "variables": []
            }
            
            for var in self.variables:
                var_dict = {
                    "name": var.name,
                    "text_color": var.text_color,
                    "bg_color": var.bg_color,
                    "text_size": var.text_size,
                    "auto_enable_sales": var.auto_enable_sales,
                    "default_unit": var.default_unit,
                    "rules": []
                }
                
                for rule in var.rules:
                    rule_dict = {
                        "operator": rule.operator,
                        "threshold": rule.threshold,
                        "color": rule.color
                    }
                    var_dict["rules"].append(rule_dict)
                
                export_data["variables"].append(var_dict)

            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            messagebox.showinfo("Success", f"Exported {len(self.variables)} variable(s) to:\n{os.path.basename(file_path)}")
            self.status_var.set(f"Conditions exported to {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export conditions:\n{str(e)}")
    
    def import_conditions(self):
        """Import variables and their rules from a JSON file"""
        # Ask for file location
        file_path = filedialog.askopenfilename(
            title="Import Conditions",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Read from file
            with open(file_path, 'r') as f:
                import_data = json.load(f)
            
            if "variables" not in import_data:
                messagebox.showerror("Error", "Invalid conditions file format")
                return
            
            # Ask if user wants to replace or merge
            if self.variables:
                response = messagebox.askyesnocancel(
                    "Import Mode",
                    f"You have {len(self.variables)} existing variable(s).\n\n"
                    "Yes = Replace all variables\n"
                    "No = Merge (add new variables)\n"
                    "Cancel = Cancel import"
                )
                
                if response is None:  # Cancel
                    return
                elif response:  # Yes - Replace
                    self.variables.clear()
            
            # Import variables
            imported_count = 0
            for var_dict in import_data["variables"]:
                # Check if variable with same name exists
                existing_var = None
                for v in self.variables:
                    if v.name == var_dict["name"]:
                        existing_var = v
                        break
                
                if existing_var:
                    # Update existing variable
                    existing_var.text_color = var_dict.get("text_color")
                    existing_var.bg_color = var_dict.get("bg_color")
                    existing_var.text_size = var_dict.get("text_size")
                    existing_var.auto_enable_sales = var_dict.get("auto_enable_sales", False)
                    existing_var.default_unit = var_dict.get("default_unit", "None")
                    existing_var.rules.clear()
                    var = existing_var
                else:
                    # Create new variable
                    var = Variable(var_dict["name"])
                    var.text_color = var_dict.get("text_color")
                    var.bg_color = var_dict.get("bg_color")
                    var.text_size = var_dict.get("text_size")
                    var.auto_enable_sales = var_dict.get("auto_enable_sales", False)
                    var.default_unit = var_dict.get("default_unit", "None")
                    self.variables.append(var)

                
                # Import rules
                for rule_dict in var_dict.get("rules", []):
                    var.add_rule(
                        rule_dict["operator"],
                        rule_dict["threshold"],
                        rule_dict["color"]
                    )
                
                imported_count += 1
            
            # Update UI
            self.update_variables_summary()
            
            # Update variable dropdowns in text entries
            for line_frame in self.text_entry_widgets:
                variable_names = ["None"] + [v.name for v in self.variables]
                line_frame.variable_combo.config(values=variable_names)
            
            messagebox.showinfo("Success", f"Imported {imported_count} variable(s) from:\n{os.path.basename(file_path)}")
            self.status_var.set(f"Conditions imported from {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import conditions:\n{str(e)}")

    
    def apply_variable_colors(self):
        """Apply colors and text formatting based on variable assignments"""
        if not self.cond_enabled_var.get():
            messagebox.showinfo("Info", "Please enable conditional coloring first")
            return
        
        if not self.variables:
            messagebox.showinfo("Info", "Please create at least one variable first")
            return
        
        if not self.labels:
            messagebox.showinfo("Info", "No labels to process")
            return
        
        # Backup original colors
        if not self.original_shape_colors:
            for i, shape in enumerate(self.shapes):
                self.original_shape_colors[i] = shape.get("color", "#CCCCCC")
        
        colored_count = 0
        formatted_count = 0
        
        # Process each label
        for label in self.labels:
            # Check each line for variable assignments
            for line_idx, var_name in enumerate(label.line_variables):
                if var_name != "None" and line_idx < len(label.text_lines):
                    # Find the variable
                    variable = next((v for v in self.variables if v.name == var_name), None)
                    
                    if variable:
                        # Extract value from text
                        value = self.extract_number_from_text(label.text_lines[line_idx])
                        
                        if value is not None:
                            # Evaluate variable's rules for shape color
                            color = variable.evaluate(value)
                            
                            if color and label.shape_index < len(self.shapes):
                                self.shapes[label.shape_index]["color"] = color
                                colored_count += 1
                        
                        # Apply text formatting from variable (regardless of value)
                        if variable.text_color:
                            if line_idx < len(label.line_font_colors):
                                label.line_font_colors[line_idx] = variable.text_color
                                formatted_count += 1
                        
                        if variable.bg_color:
                            if line_idx < len(label.line_bg_colors):
                                label.line_bg_colors[line_idx] = variable.bg_color
                                formatted_count += 1
                        
                        if variable.text_size:
                            if line_idx < len(label.line_font_sizes):
                                label.line_font_sizes[line_idx] = variable.text_size
                                formatted_count += 1
        
        # Redraw canvas
        self.display_canvas()
        
        result_msg = f"Applied colors to {colored_count} shapes"
        if formatted_count > 0:
            result_msg += f" and formatting to {formatted_count} text lines"
        
        self.status_var.set(result_msg)
        messagebox.showinfo("Success", result_msg)
    
    def toggle_conditional_coloring(self):
        """Toggle conditional coloring on/off"""
        self.conditional_coloring_enabled = self.cond_enabled_var.get()
        if self.conditional_coloring_enabled:
            self.status_var.set("Conditional coloring enabled")
        else:
            self.status_var.set("Conditional coloring disabled")
    
    def import_excel_csv(self):
        """Import Excel/CSV file to automatically create labels"""
        # Check if shapes are loaded
        if not self.shapes:
            messagebox.showwarning("Warning", "Please load shapes first (Load JSON Shapes)")
            return
        
        # Check if labels already exist
        if self.labels:
            response = messagebox.askyesnocancel(
                "Import Options",
                f"You have {len(self.labels)} existing label(s).\n\n"
                "Do you want to REPLACE them with the imported data?\n\n"
                "• Yes = Replace all existing labels\n"
                "• No = Add to existing labels\n"
                "• Cancel = Cancel import"
            )
            
            if response is None:  # Cancel
                return
            elif response:  # Yes - Replace
                self.labels.clear()
                self.selected_label = None
                self.clear_text_editor()
        
        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select Excel or CSV File",
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.parse_and_apply_import_data(file_path)
    
    def remap_shapes(self):
        """Remap existing labels to different shapes - shows current mapping and rebuilds labels"""
        # Check if shapes are loaded
        if not self.shapes:
            messagebox.showwarning("Warning", "Please load shapes first from Heatmap Generator")
            return
        
        # Check if we have last imported data
        if self.last_imported_df is None:
            messagebox.showinfo(
                "Info", 
                "No Excel/CSV data found.\n\n"
                "Please use 'Import Excel/CSV' first to import data,\n"
                "then you can use 'Remap' to change the mapping."
            )
            return
        
        # Show mapping dialog with CURRENT mapping pre-selected
        mapping = self.show_mapping_dialog(
            self.last_imported_df, 
            self.shapes,
            current_mapping=self.current_mapping  # Pass current mapping
        )
        
        if mapping is None:
            self.status_var.set("Remapping cancelled")
            return
        
        if not mapping:
            messagebox.showinfo("Info", "No shapes were mapped")
            return
        
        # COMPLETELY REBUILD labels from scratch with new mapping
        # Clear all existing labels
        self.labels.clear()
        self.selected_label = None
        self.clear_text_editor()
        
        # Store the new mapping
        self.current_mapping = mapping
        
        # Re-import data with new mapping (reuse the import logic)
        self.apply_import_data_with_mapping(self.last_imported_df, mapping)
        
        messagebox.showinfo("Success", f"Remapped and rebuilt {len(mapping)} label(s)")
        self.status_var.set(f"Remapped {len(mapping)} labels")
    
    
    def show_mapping_dialog(self, df, shapes, current_mapping=None):
        """Show dialog to manually map shapes to Excel rows with visual preview
        
        Args:
            df: pandas DataFrame with Excel/CSV data
            shapes: list of shape dictionaries from Heatmap Generator
            
        Returns:
            dict: mapping of shape_index to excel_row_index, or None if cancelled
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Shape Mapping Tool")
        dialog.geometry("1300x750")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#f5f7fa")
        
        # Result variable
        mapping_result = {"cancelled": True, "mapping": {}}
        
        # Currently highlighted shape
        current_highlight = {"shape_idx": None, "canvas_ids": []}
        
        # Header bar with modern styling
        header_bar = tk.Frame(dialog, bg="#2c3e50", height=60)
        header_bar.pack(fill=tk.X, side=tk.TOP)
        header_bar.pack_propagate(False)
        
        title_label = tk.Label(
            header_bar,
            text="📍 Shape Mapping Tool",
            font=("Segoe UI", 18, "bold"),
            fg="white",
            bg="#2c3e50"
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        subtitle_label = tk.Label(
            header_bar,
            text="Map Excel data to shapes visually",
            font=("Segoe UI", 10),
            fg="#bdc3c7",
            bg="#2c3e50"
        )
        subtitle_label.pack(side=tk.LEFT, padx=(0, 20), pady=15)
        
        # Main container with two panels
        main_container = tk.Frame(dialog, bg="#f5f7fa")
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # LEFT PANEL: PDF Preview
        left_panel = ttk.LabelFrame(main_container, text="PDF Preview (Mouse wheel to zoom, click shape to highlight)", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Canvas for PDF preview with scrollbars
        preview_frame = ttk.Frame(left_panel)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        preview_h_scroll = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL)
        preview_h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        preview_v_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL)
        preview_v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        preview_canvas = tk.Canvas(
            preview_frame, 
            bg="white", 
            highlightthickness=1, 
            highlightbackground="gray",
            xscrollcommand=preview_h_scroll.set,
            yscrollcommand=preview_v_scroll.set
        )
        preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        preview_h_scroll.config(command=preview_canvas.xview)
        preview_v_scroll.config(command=preview_canvas.yview)
        
        # Zoom state
        preview_zoom = {"scale": 1.0, "base_scale": 1.0}
        
        # Draw PDF and shapes on preview canvas
        def draw_preview():
            preview_canvas.delete("all")
            
            # Get canvas size
            canvas_width = preview_canvas.winfo_width()
            canvas_height = preview_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                # Canvas not ready yet, try again
                preview_canvas.after(100, draw_preview)
                return
            
            # Draw PDF image if available
            if hasattr(self, 'pdf_image') and self.pdf_image:
                # Calculate base scaling to fit canvas
                img_width = self.pdf_image.width
                img_height = self.pdf_image.height
                
                scale_x = canvas_width / img_width
                scale_y = canvas_height / img_height
                base_scale = min(scale_x, scale_y) * 0.95  # 95% to leave margin
                
                # Store base scale
                preview_zoom["base_scale"] = base_scale
                
                # Apply zoom
                scale = base_scale * preview_zoom["scale"]
                
                # Resize image
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                from PIL import ImageTk
                resized_img = self.pdf_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(resized_img)
                
                # Center image (or place at 0,0 for scrolling)
                x_offset = max(0, (canvas_width - new_width) // 2)
                y_offset = max(0, (canvas_height - new_height) // 2)
                
                preview_canvas.create_image(x_offset, y_offset, image=photo, anchor=tk.NW)
                preview_canvas.image = photo  # Keep reference
                
                # Store scale and offset for shape drawing
                preview_canvas.scale = scale
                preview_canvas.x_offset = x_offset
                preview_canvas.y_offset = y_offset
                
                # Update scroll region
                preview_canvas.config(scrollregion=(0, 0, new_width + x_offset * 2, new_height + y_offset * 2))
                
                # Draw all shapes
                for idx, shape in enumerate(shapes):
                    draw_shape_on_preview(shape, idx, scale, x_offset, y_offset, highlighted=False)
                
                # Restore highlight if there was one
                if current_highlight["shape_idx"] is not None:
                    highlight_shape(current_highlight["shape_idx"])
        
        # Zoom function
        def on_preview_zoom(event):
            # Get mouse position
            x = preview_canvas.canvasx(event.x)
            y = preview_canvas.canvasy(event.y)
            
            # Determine zoom direction
            if event.delta > 0 or event.num == 4:  # Zoom in
                preview_zoom["scale"] *= 1.1
            elif event.delta < 0 or event.num == 5:  # Zoom out
                preview_zoom["scale"] /= 1.1
            
            # Limit zoom range
            preview_zoom["scale"] = max(0.5, min(5.0, preview_zoom["scale"]))
            
            # Redraw with new zoom
            draw_preview()
        
        # Bind mouse wheel for zoom
        preview_canvas.bind("<MouseWheel>", on_preview_zoom)  # Windows
        preview_canvas.bind("<Button-4>", on_preview_zoom)    # Linux scroll up
        preview_canvas.bind("<Button-5>", on_preview_zoom)    # Linux scroll down
        
        # Pan functionality with right-click drag
        pan_data = {"x": 0, "y": 0}
        
        def on_pan_start(event):
            preview_canvas.scan_mark(event.x, event.y)
            pan_data["x"] = event.x
            pan_data["y"] = event.y
        
        def on_pan_move(event):
            preview_canvas.scan_dragto(event.x, event.y, gain=1)
        
        preview_canvas.bind("<ButtonPress-3>", on_pan_start)   # Right-click press
        preview_canvas.bind("<B3-Motion>", on_pan_move)        # Right-click drag
        
        def draw_shape_on_preview(shape, shape_idx, scale, x_offset, y_offset, highlighted=False):
            """Draw a single shape on the preview canvas"""
            shape_type = shape["type"]
            coords = shape["coordinates"]
            
            # Scale coordinates
            if shape_type == "rectangle":
                x1, y1, x2, y2 = coords
                scaled_coords = [
                    x1 * scale + x_offset, y1 * scale + y_offset,
                    x2 * scale + x_offset, y2 * scale + y_offset
                ]
                
                if highlighted:
                    # Draw beautiful cyan highlight with glow effect
                    # Outer glow
                    preview_canvas.create_rectangle(
                        scaled_coords[0]-3, scaled_coords[1]-3,
                        scaled_coords[2]+3, scaled_coords[3]+3,
                        outline="#00d4ff",
                        width=6,
                        tags="highlight"
                    )
                    # Main highlight
                    preview_canvas.create_rectangle(
                        *scaled_coords,
                        outline="#00bfff",
                        fill="#00ffff",
                        stipple="gray25",
                        width=3,
                        tags="highlight"
                    )
                else:
                    # Draw normal shape
                    preview_canvas.create_rectangle(
                        *scaled_coords,
                        outline=shape.get("color", "#0000FF"),
                        width=2,
                        fill="",
                        tags=f"shape_{shape_idx}"
                    )
                    
            elif shape_type == "polygon":
                scaled_coords = []
                for i in range(0, len(coords), 2):
                    scaled_coords.append(coords[i] * scale + x_offset)
                    scaled_coords.append(coords[i+1] * scale + y_offset)
                
                if highlighted:
                    # Draw beautiful cyan highlight for polygon
                    preview_canvas.create_polygon(
                        *scaled_coords,
                        outline="#00bfff",
                        fill="#00ffff",
                        stipple="gray25",
                        width=3,
                        tags="highlight"
                    )
                    # Outer glow
                    preview_canvas.create_polygon(
                        *scaled_coords,
                        outline="#00d4ff",
                        width=6,
                        tags="highlight"
                    )
                else:
                    preview_canvas.create_polygon(
                        *scaled_coords,
                        outline=shape.get("color", "#0000FF"),
                        width=2,
                        fill="",
                        tags=f"shape_{shape_idx}"
                    )
                    
            elif shape_type == "circle":
                cx, cy, radius = coords
                x1 = (cx - radius) * scale + x_offset
                y1 = (cy - radius) * scale + y_offset
                x2 = (cx + radius) * scale + x_offset
                y2 = (cy + radius) * scale + y_offset
                
                if highlighted:
                    # Draw beautiful cyan highlight for circle
                    # Outer glow
                    preview_canvas.create_oval(
                        x1-3, y1-3, x2+3, y2+3,
                        outline="#00d4ff",
                        width=6,
                        tags="highlight"
                    )
                    # Main highlight
                    preview_canvas.create_oval(
                        x1, y1, x2, y2,
                        outline="#00bfff",
                        fill="#00ffff",
                        stipple="gray25",
                        width=3,
                        tags="highlight"
                    )
                else:
                    preview_canvas.create_oval(
                        x1, y1, x2, y2,
                        outline=shape.get("color", "#0000FF"),
                        width=2,
                        fill="",
                        tags=f"shape_{shape_idx}"
                    )
        
        def highlight_shape(shape_idx):
            """Highlight a specific shape on the preview"""
            # Update current highlight state
            current_highlight["shape_idx"] = shape_idx
            
            # Clear previous highlight
            preview_canvas.delete("highlight")
            
            if shape_idx is not None and hasattr(preview_canvas, 'scale'):
                # Draw highlighted version
                shape = shapes[shape_idx]
                draw_shape_on_preview(
                    shape, shape_idx,
                    preview_canvas.scale,
                    preview_canvas.x_offset,
                    preview_canvas.y_offset,
                    highlighted=True
                )
        
        # Schedule initial draw
        preview_canvas.after(100, draw_preview)
        
        # RIGHT PANEL: Mapping controls
        right_panel = tk.Frame(main_container, bg="#ffffff", relief=tk.FLAT, bd=0)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(10, 0))
        
        # Add subtle shadow
        shadow_frame = tk.Frame(main_container, bg="#d0d0d0")
        shadow_frame.place(in_=right_panel, x=2, y=2, relwidth=1, relheight=1)
        right_panel.lift()
        
        # Header
        header_frame = tk.Frame(right_panel, bg="#ffffff")
        header_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        tk.Label(
            header_frame,
            text="Shape Mappings",
            font=("Segoe UI", 14, "bold"),
            fg="#2c3e50",
            bg="#ffffff"
        ).pack(anchor=tk.W)
        
        tk.Label(
            header_frame,
            text=f"📊 {len(df)} Excel rows available • Click shape to highlight",
            font=("Segoe UI", 9),
            fg="#7f8c8d",
            bg="#ffffff"
        ).pack(anchor=tk.W, pady=(3, 0))
        
        # Scrollable frame for mappings
        mapping_canvas_frame = tk.Frame(right_panel, bg="#ffffff")
        mapping_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        mapping_canvas = tk.Canvas(mapping_canvas_frame, bg="#f8f9fa", width=420, highlightthickness=0)
        mapping_scrollbar = ttk.Scrollbar(mapping_canvas_frame, orient="vertical", command=mapping_canvas.yview)
        scrollable_frame = tk.Frame(mapping_canvas, bg="#f8f9fa")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: mapping_canvas.configure(scrollregion=mapping_canvas.bbox("all"))
        )
        
        mapping_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        mapping_canvas.configure(yscrollcommand=mapping_scrollbar.set)
        
        mapping_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mapping_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create mapping rows
        mapping_vars = {}  # {shape_index: StringVar}
        
        # Prepare Excel row options
        first_col = df.columns[0]
        excel_options = ["<None - Skip>"]
        for idx, row in df.iterrows():
            row_preview = str(row[first_col])[:40]
            excel_options.append(f"Row {idx + 2}: {row_preview}")
        
        for shape_idx, shape in enumerate(shapes):
            shape_name = shape.get("name", f"Shape {shape_idx + 1}")
            
            # Row frame with modern card styling
            row_frame = tk.Frame(scrollable_frame, bg="#ffffff", relief=tk.FLAT, bd=0)
            row_frame.pack(fill=tk.X, padx=8, pady=4)
            
            # Inner frame for border effect
            inner_frame = tk.Frame(row_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#e0e0e0")
            inner_frame.pack(fill=tk.BOTH, expand=True)
            
            # Make row clickable to highlight shape
            def make_click_handler(idx):
                def on_click(event=None):
                    highlight_shape(idx)
                return on_click
            
            # Hover effect
            def make_hover_handlers(frame, inner):
                def on_enter(e):
                    inner.config(highlightbackground="#3498db", highlightthickness=2)
                def on_leave(e):
                    inner.config(highlightbackground="#e0e0e0", highlightthickness=1)
                return on_enter, on_leave
            
            on_enter, on_leave = make_hover_handlers(row_frame, inner_frame)
            inner_frame.bind("<Enter>", on_enter)
            inner_frame.bind("<Leave>", on_leave)
            inner_frame.bind("<Button-1>", make_click_handler(shape_idx))
            
            # Shape name label (clickable)
            name_label = tk.Label(
                inner_frame,
                text=f"🔷 {shape_name}",
                font=("Segoe UI", 10, "bold"),
                fg="#2c3e50",
                bg="#ffffff",
                cursor="hand2",
                anchor="w"
            )
            name_label.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 5))
            name_label.bind("<Button-1>", make_click_handler(shape_idx))
            name_label.bind("<Enter>", on_enter)
            name_label.bind("<Leave>", on_leave)
            
            # Excel row dropdown
            var = tk.StringVar(value="<None - Skip>")
            mapping_vars[shape_idx] = var
            
            # Pre-select current mapping if provided
            if current_mapping and shape_idx in current_mapping:
                excel_row_idx = current_mapping[shape_idx]
                # Set to the corresponding option (add 1 because index 0 is "<None - Skip>")
                if excel_row_idx < len(excel_options) - 1:
                    var.set(excel_options[excel_row_idx + 1])
            
            combo = ttk.Combobox(
                inner_frame,
                textvariable=var,
                values=excel_options,
                state="readonly",
                width=38,
                font=("Segoe UI", 9)
            )
            combo.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))
        
        # Buttons at bottom with modern styling
        btn_frame = tk.Frame(right_panel, bg="#ffffff")
        btn_frame.pack(fill=tk.X, padx=15, pady=(5, 15))
        
        def create_modern_button(parent, text, command, bg_color, hover_color, icon=""):
            btn = tk.Button(
                parent,
                text=f"{icon} {text}",
                command=command,
                bg=bg_color,
                fg="white",
                font=("Segoe UI", 10, "bold"),
                relief=tk.FLAT,
                bd=0,
                padx=20,
                pady=12,
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
        
        def on_ok():
            # Build mapping from selections
            mapping = {}
            for shape_idx, var in mapping_vars.items():
                selection = var.get()
                if selection != "<None - Skip>":
                    try:
                        row_num_str = selection.split(":")[0].replace("Row ", "")
                        excel_row_idx = int(row_num_str) - 2
                        mapping[shape_idx] = excel_row_idx
                    except:
                        pass
            
            mapping_result["cancelled"] = False
            mapping_result["mapping"] = mapping
            dialog.destroy()
        
        def on_cancel():
            mapping_result["cancelled"] = True
            dialog.destroy()
        
        # Create modern buttons
        ok_btn = create_modern_button(btn_frame, "Apply Mapping", on_ok, "#27ae60", "#229954", "✓")
        ok_btn.pack(fill=tk.X, pady=(0, 8))
        
        cancel_btn = create_modern_button(btn_frame, "Cancel", on_cancel, "#95a5a6", "#7f8c8d", "✕")
        cancel_btn.pack(fill=tk.X)
        
        # Wait for dialog to close
        dialog.wait_window()
        
        if mapping_result["cancelled"]:
            return None
        return mapping_result["mapping"]
    
    
    def parse_and_apply_import_data(self, file_path: str):
        """Parse Excel/CSV file and apply data to create labels using manual mapping
        
        Format: Name, Var_Name, Value1, Var1, Value2, Var2, ...
        - Column 1: Name/identifier (for user reference in mapping dialog)
        - Column 2: Variable for shape name line
        - Columns 3+: Value/Variable pairs
        
        Example: Name, Var_Name, Sale_Value, Sale_Var, Profit_Value, Profit_Var
        """
        try:
            # Read file based on extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                messagebox.showerror("Error", "Unsupported file format. Please use .csv or .xlsx files")
                return
            
            # Validate we have at least 2 columns
            if len(df.columns) < 2:
                messagebox.showerror("Error", "File must have at least 2 columns (Name, Var_Name)")
                return
            
            # Show mapping dialog
            mapping = self.show_mapping_dialog(df, self.shapes)
            
            if mapping is None:
                # User cancelled
                self.status_var.set("Import cancelled")
                return
            
            if not mapping:
                messagebox.showinfo("Info", "No shapes were mapped. Import cancelled.")
                return
            
            # Store the imported data and mapping for remap functionality
            self.last_imported_df = df
            self.current_mapping = mapping
            
            # Apply the import with the mapping
            self.apply_import_data_with_mapping(df, mapping)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error importing file: {str(e)}")
            self.status_var.set("Import failed")
    
    def apply_import_data_with_mapping(self, df, mapping):
        """Apply imported Excel/CSV data using the provided mapping
        
        This is used by both initial import and remap operations
        """
        try:
            
            # First two columns are name and variable for name
            name_column = df.columns[0]
            name_var_column = df.columns[1]
            
            # Remaining columns should be value/variable pairs
            data_columns = df.columns[2:]
            
            if len(data_columns) % 2 != 0:
                messagebox.showwarning(
                    "Warning",
                    f"Expected even number of data columns (value/variable pairs).\n"
                    f"Found {len(data_columns)} columns after Name and Var_Name.\n"
                    f"Last column will be ignored."
                )
            
            # Process each mapped shape
            success_count = 0
            total_lines_added = 0
            
            for shape_index, excel_row_idx in mapping.items():
                try:
                    # Get the Excel row
                    row = df.iloc[excel_row_idx]
                    
                    shape_name = str(row[name_column]).strip()
                    name_var = str(row[name_var_column]).strip() if not pd.isna(row[name_var_column]) else "None"
                    
                    # Find or create label
                    label = self.find_label_for_shape(shape_index)
                    
                    if label is None:
                        # Create new label OUTSIDE PDF bounds on closest side
                        shape = self.shapes[shape_index]
                        
                        # Get shape center
                        center = self.get_shape_center(shape)
                        shape_x, shape_y = center
                        
                        # Get shape bounds to determine closest edge
                        if shape["type"] == "rectangle":
                            coords = shape["coordinates"]
                            x1, y1, x2, y2 = coords
                            shape_left = min(x1, x2)
                            shape_right = max(x1, x2)
                            shape_top = min(y1, y2)
                            shape_bottom = max(y1, y2)
                        elif shape["type"] == "polygon":
                            coords = shape["coordinates"]
                            x_coords = coords[::2]
                            y_coords = coords[1::2]
                            shape_left = min(x_coords)
                            shape_right = max(x_coords)
                            shape_top = min(y_coords)
                            shape_bottom = max(y_coords)
                        elif shape["type"] == "circle":
                            coords = shape["coordinates"]
                            cx, cy, radius = coords
                            shape_left = cx - radius
                            shape_right = cx + radius
                            shape_top = cy - radius
                            shape_bottom = cy + radius
                        else:
                            # Fallback
                            shape_left = shape_right = shape_x
                            shape_top = shape_bottom = shape_y
                        
                        # Get PDF bounds
                        if hasattr(self, 'pdf_image') and self.pdf_image:
                            pdf_width = self.pdf_image.width
                            pdf_height = self.pdf_image.height
                        else:
                            # Default PDF size estimate
                            pdf_width = 800
                            pdf_height = 1000
                        
                        # Calculate distances to each edge
                        dist_to_left = shape_left
                        dist_to_right = pdf_width - shape_right
                        dist_to_top = shape_top
                        dist_to_bottom = pdf_height - shape_bottom
                        
                        # Find closest edge
                        min_dist = min(dist_to_left, dist_to_right, dist_to_top, dist_to_bottom)
                        
                        # Place label outside PDF on closest side
                        margin = 50  # Distance outside PDF
                        
                        if min_dist == dist_to_left:
                            # Place to the left of PDF
                            label_x = -margin
                            label_y = shape_y
                        elif min_dist == dist_to_right:
                            # Place to the right of PDF
                            label_x = pdf_width + margin
                            label_y = shape_y
                        elif min_dist == dist_to_top:
                            # Place above PDF
                            label_x = shape_x
                            label_y = -margin
                        else:  # dist_to_bottom
                            # Place below PDF
                            label_x = shape_x
                            label_y = pdf_height + margin
                        
                        label = TextLabel(shape_index, (label_x, label_y))
                        
                        # Set imported name from Excel as first line with its variable
                        label.text_lines = [shape_name]  # Use imported name from Excel, not shape name
                        label.line_font_sizes = [self.default_text_size.get() if hasattr(self, 'default_text_size') else 30]
                        label.line_font_colors = [self.default_text_color.get() if hasattr(self, 'default_text_color') else "#000000"]
                        label.line_bg_colors = [self.default_bg_color.get() if hasattr(self, 'default_bg_color') else "#FFFFFF"]
                        label.line_variables = [name_var]  # Assign variable to name line
                        
                        # Set default leader line width
                        if hasattr(self, 'default_leader_width'):
                            label.leader_width = self.default_leader_width.get()
                        
                        # Always add leader line since label is outside shape
                        label.has_leader = True
                        label.leader_points = self.calculate_leader_line((label_x, label_y), shape)
                        
                        self.labels.append(label)
                    else:
                        # Update existing label's name variable
                        if len(label.line_variables) > 0:
                            label.line_variables[0] = name_var
                    
                    # Process value/variable pairs
                    lines_added = 0
                    for i in range(0, len(data_columns) - 1, 2):
                        value_col = data_columns[i]
                        var_col = data_columns[i + 1]
                        
                        value = str(row[value_col]).strip() if not pd.isna(row[value_col]) else ""
                        var_name = str(row[var_col]).strip() if not pd.isna(row[var_col]) else "None"
                        
                        # Skip if value is empty
                        if not value:
                            continue
                        
                        # Format number with thousand separators (accounting style)
                        try:
                            # Try to parse as number
                            num_value = float(value.replace(',', ''))  # Remove existing commas
                            # Format with thousand separators, no decimals
                            formatted_value = f"{int(num_value):,}"
                        except (ValueError, AttributeError):
                            # If not a number, use as-is
                            formatted_value = value
                        
                        # Add new text line with formatted value and variable
                        label.text_lines.append(formatted_value)
                        label.line_font_sizes.append(self.default_text_size.get() if hasattr(self, 'default_text_size') else 30)
                        label.line_font_colors.append(self.default_text_color.get() if hasattr(self, 'default_text_color') else "#000000")
                        label.line_bg_colors.append(self.default_bg_color.get() if hasattr(self, 'default_bg_color') else "#FFFFFF")
                        label.line_variables.append(var_name)
                        lines_added += 1
                    
                    # Check if text is outside shape and update leader line
                    if lines_added > 0 or label not in self.labels:
                        shape = self.shapes[shape_index]
                        if not self.is_point_in_shape(label.position, shape):
                            label.has_leader = True
                            label.leader_points = self.calculate_leader_line(label.position, shape)
                        
                        success_count += 1
                        total_lines_added += lines_added
                        
                except Exception as e:
                    print(f"Error processing shape {shape_index}: {e}")
                    continue
            
            # Show results
            result_message = f"Successfully imported {success_count} label(s)\n"
            result_message += f"Added {total_lines_added} text line(s)"
            
            # Update display
            self.display_canvas()
            self.update_shape_list()
            
            messagebox.showinfo("Import Complete", result_message)
            self.status_var.set(f"Imported {success_count} labels successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import file:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def find_shape_by_name(self, shape_name: str) -> Optional[int]:
        """Find shape index by name (case-insensitive)"""
        shape_name_lower = shape_name.lower()
        
        for i, shape in enumerate(self.shapes):
            current_name = shape.get("name", "").lower()
            if current_name == shape_name_lower:
                return i
        
        return None
    
    def create_or_update_label_from_import(self, shape_index: int, number_value: str, var_name: str):
        """Create or update label for a shape from import data"""
        # Validate shape index
        if shape_index < 0 or shape_index >= len(self.shapes):
            print(f"Warning: Cannot create label for invalid shape index {shape_index}")
            return
        
        # Find existing label or create new one
        label = self.find_label_for_shape(shape_index)
        
        if label is None:
            # Create new label at shape center
            shape = self.shapes[shape_index]
            center = self.get_shape_center(shape)
            
            label = TextLabel(shape_index, center)
            
            # Set shape name as first line
            shape_name = shape.get("name", f"Shape {shape_index + 1}")
            label.text_lines = [shape_name]
            label.line_font_sizes = [self.default_text_size.get() if hasattr(self, 'default_text_size') else 30]
            label.line_font_colors = [self.default_text_color.get() if hasattr(self, 'default_text_color') else "#000000"]
            label.line_bg_colors = [self.default_bg_color.get() if hasattr(self, 'default_bg_color') else "#FFFFFF"]
            label.line_variables = ["None"]
            
            # Set default leader line width
            if hasattr(self, 'default_leader_width'):
                label.leader_width = self.default_leader_width.get()
            
            self.labels.append(label)
        
        # Add new text line with number value
        label.text_lines.append(number_value)
        label.line_font_sizes.append(self.default_text_size.get() if hasattr(self, 'default_text_size') else 30)
        label.line_font_colors.append(self.default_text_color.get() if hasattr(self, 'default_text_color') else "#000000")
        label.line_bg_colors.append(self.default_bg_color.get() if hasattr(self, 'default_bg_color') else "#FFFFFF")
        label.line_variables.append(var_name)
        
        # Check if text is outside shape and update leader line
        shape = self.shapes[shape_index]
        if not self.is_point_in_shape(label.position, shape):
            label.has_leader = True
            label.leader_points = self.calculate_leader_line(label.position, shape)



def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = LayoutTextLabeler(root)
    root.mainloop()


if __name__ == "__main__":
    main()
