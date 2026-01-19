"""
Layout Heatmap Generator - Store Layout Mapping Application
Author: AI Assistant
Description: A tool for creating store layout heatmaps based on sales criteria
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from tkinter.scrolledtext import ScrolledText
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import json
import os
import io
import random
from typing import Dict, List, Tuple, Optional
from typing import Dict, List, Tuple, Optional

class LayoutHeatmapApp:
    def __init__(self, parent):
        # Parent can be either root window or a frame
        self.root = parent
        
        # Only set title and geometry if parent is a Tk root window
        if isinstance(parent, tk.Tk):
            self.root.title("Store Layout Heatmap Generator")
            self.root.geometry("1400x900")
        
        # Application state
        self.current_pdf_path: Optional[str] = None
        self.pdf_image: Optional[Image.Image] = None
        self.canvas_image: Optional[ImageTk.PhotoImage] = None
        self.shapes: List[Dict] = []
        self.current_tool = "rectangle"
        self.drawing = False
        self.start_x = 0
        self.start_y = 0
        self.preview_shape = None  # For live preview during drawing
        
        # Zoom and pan variables
        self.zoom_factor = 1.0
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.panning = False
        self.original_image_size = None
        
        # Undo/Redo and selection variables
        self.history = []  # For undo functionality
        self.history_index = -1
        self.selected_shape = None
        self.selection_mode = False
        self.moving_shape = False
        self.move_start_x = 0
        self.move_start_y = 0
        
        # Polygon drawing variables
        self.polygon_points = []  # For line-to-polygon drawing
        self.drawing_polygon = False
        self.polygon_lines = []  # Temporary line segments
        self.resize_handles = []  # For resize functionality
        self.resizing = False
        self.resize_handle = None
        
        # Color selector
        self.selected_color = "#FF6B6B"  # Default color
        self.color_var = tk.StringVar(value=self.selected_color)
        self.opacity = 1.0  # Default opacity (0.0 to 1.0)
        self.opacity_var = tk.DoubleVar(value=self.opacity)
        self.use_random_colors = True  # Use random colors by default
        
        # Zoom display
        self.zoom_var = tk.StringVar()
        self.zoom_var.set("Zoom: 100%")
        
        # Callback for PDF loading (to sync with other apps)
        self.on_pdf_loaded = None
        
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
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Setup toolbar at the top
        self.setup_toolbar(main_container)
        
        # Content area (control panel + canvas)
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Setup control panel and canvas
        self.setup_control_panel(content_frame)
        self.setup_canvas_area(content_frame)
        
        # Setup status bar
        self.setup_status_bar()
    
    def setup_toolbar(self, parent):
        """Setup the toolbar with quick access buttons"""
        toolbar = tk.Frame(parent, bg="#f0f0f0", height=50, relief=tk.RAISED, bd=1)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)
        
        # Helper function to create toolbar buttons
        def create_toolbar_button(text, command, icon=""):
            btn = tk.Button(
                toolbar,
                text=f"{icon} {text}" if icon else text,
                command=command,
                bg="#f0f0f0",
                fg="#333",
                font=("Segoe UI", 9),
                padx=15,
                pady=8,
                relief=tk.FLAT,
                bd=0,
                cursor="hand2",
                activebackground="#e0e0e0"
            )
            
            def on_enter(e):
                btn.config(bg="#e0e0e0")
            def on_leave(e):
                btn.config(bg="#f0f0f0")
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            
            return btn
        
        # Undo button
        undo_btn = create_toolbar_button("Undo", self.undo_action, "↶")
        undo_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        # Redo button
        redo_btn = create_toolbar_button("Redo", self.redo_action, "↷")
        redo_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=8)
        
        # Delete button
        delete_btn = create_toolbar_button("Delete", self.delete_selected, "🗑")
        delete_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=8)
        
        # Save Layout button
        save_btn = create_toolbar_button("Save Layout", self.save_layout, "💾")
        save_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        # Clear Layout button
        clear_btn = create_toolbar_button("Clear Layout", self.clear_all, "🗑")
        clear_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        # Export Image button
        export_btn = create_toolbar_button("Export Image", self.export_image, "📷")
        export_btn.pack(side=tk.LEFT, padx=2, pady=5)
    
    def setup_control_panel(self, parent):
        """Setup the control panel with file operations and tools"""
        # Create scrollable control frame
        control_outer = ttk.Frame(parent, width=270)
        control_outer.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        control_outer.pack_propagate(False)  # Maintain fixed width
        
        # Create scrollable frame for controls
        self.control_canvas = tk.Canvas(control_outer, width=250)
        control_scrollbar = ttk.Scrollbar(control_outer, orient="vertical", command=self.control_canvas.yview)
        self.scrollable_control_frame = ttk.Frame(self.control_canvas)
        
        self.scrollable_control_frame.bind(
            "<Configure>",
            lambda e: self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all"))
        )
        
        self.control_canvas.create_window((0, 0), window=self.scrollable_control_frame, anchor="nw")
        self.control_canvas.configure(yscrollcommand=control_scrollbar.set)
        
        self.control_canvas.pack(side="left", fill="both", expand=True)
        control_scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to scroll
        def on_mousewheel(event):
            self.control_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.control_canvas.bind("<MouseWheel>", on_mousewheel)
        # Bind mousewheel to the scrollable frame as well
        self.scrollable_control_frame.bind("<MouseWheel>", on_mousewheel)
        
        # Make sure all child widgets can trigger scroll
        def bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)
        
        # Bind after creating all widgets
        self.root.after(100, lambda: bind_mousewheel_recursive(self.scrollable_control_frame))
        
        # Bind enter/leave events for mousewheel scrolling
        def on_enter_control_area(event):
            # Enable scrolling when mouse enters the control area
            self.control_canvas.focus_set()
        
        def on_leave_control_area(event):
            # Return focus to canvas when mouse leaves control area
            if hasattr(self, 'canvas'):
                self.canvas.focus_set()
        
        self.control_canvas.bind("<Enter>", on_enter_control_area)
        self.control_canvas.bind("<Leave>", on_leave_control_area)
        self.scrollable_control_frame.bind("<Enter>", on_enter_control_area)
        self.scrollable_control_frame.bind("<Leave>", on_leave_control_area)
        
        # File operations section
        file_frame = ttk.LabelFrame(self.scrollable_control_frame, text="File Operations", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Browse PDF button
        self.browse_btn = ttk.Button(
            file_frame, 
            text="Browse PDF File", 
            command=self.browse_pdf_file,
            width=20
        )
        self.browse_btn.pack(pady=5)
        
        # Load JSON Shapes button
        self.load_json_btn = ttk.Button(
            file_frame,
            text="Load JSON Shapes",
            command=self.load_json_shapes,
            width=20
        )
        self.load_json_btn.pack(pady=5)
        
        # File info display
        self.file_info = tk.StringVar()
        self.file_info.set("No file selected")
        ttk.Label(file_frame, textvariable=self.file_info, wraplength=200).pack(pady=5)
        
        # Shape List section
        shape_list_frame = ttk.LabelFrame(self.scrollable_control_frame, text="Shapes", padding=10)
        shape_list_frame.pack(fill=tk.X, pady=(0, 10))  # Changed from BOTH to X to prevent over-expansion
        
        # Shape listbox with scrollbar - fixed height container
        list_container = ttk.Frame(shape_list_frame, height=200)  # Set minimum height
        list_container.pack(fill=tk.BOTH, expand=False)  # Don't expand to prevent overlap
        list_container.pack_propagate(False)  # Maintain the fixed height
        
        # Create scrollbar first
        shape_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        shape_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create listbox with scrollbar
        self.shape_listbox = tk.Listbox(
            list_container,
            yscrollcommand=shape_scrollbar.set,
            font=("Arial", 10),
            selectmode=tk.SINGLE,
            activestyle='dotbox'
        )
        self.shape_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar to control listbox
        shape_scrollbar.config(command=self.shape_listbox.yview)
        
        # Bind selection event
        self.shape_listbox.bind("<<ListboxSelect>>", self.on_shape_list_select)
        
        # Add mousewheel scrolling for shape listbox
        def on_shape_listbox_mousewheel(event):
            self.shape_listbox.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mousewheel to listbox and container
        self.shape_listbox.bind("<MouseWheel>", on_shape_listbox_mousewheel)
        list_container.bind("<MouseWheel>", on_shape_listbox_mousewheel)
        
        # Enable mousewheel when mouse enters the listbox area
        def on_enter_listbox(event):
            self.shape_listbox.bind("<MouseWheel>", on_shape_listbox_mousewheel)
        
        def on_leave_listbox(event):
            # Keep the binding active even when leaving
            pass
        
        self.shape_listbox.bind("<Enter>", on_enter_listbox)
        list_container.bind("<Enter>", on_enter_listbox)
        
        # Buttons frame
        shape_btn_frame = ttk.Frame(shape_list_frame)
        shape_btn_frame.pack(fill=tk.X, pady=5)
        
        # Rename button
        ttk.Button(shape_btn_frame, text="Rename", command=self.rename_selected_shape, width=12).pack(side=tk.LEFT, padx=(0, 5))
        
        # Delete button
        ttk.Button(shape_btn_frame, text="Delete", command=self.delete_selected, width=12).pack(side=tk.LEFT)
        
        # Drawing tools section
        tools_frame = ttk.LabelFrame(self.scrollable_control_frame, text="Drawing Tools", padding=10)
        tools_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Tool selection with bigger icons and smaller text
        self.tool_var = tk.StringVar(value="rectangle")
        tools = [
            ("🖱️", "Select/Move", "select"),
            ("▭", "Rectangle", "rectangle"),
            ("⬭", "Circle/Oval", "oval"),
            ("⬟", "Polygon/Line", "polygon")
        ]
        
        # Use a default background color for ttk widgets
        default_bg = "#f0f0f0"
        
        for icon, label, value in tools:
            # Create frame for each tool
            tool_frame = tk.Frame(tools_frame, bg=default_bg)
            tool_frame.pack(anchor=tk.W, pady=2, fill=tk.X)
            
            # Radio button with big icon
            rb = tk.Radiobutton(
                tool_frame,
                text=f"{icon}  ",
                variable=self.tool_var,
                value=value,
                command=self.change_tool,
                font=("Segoe UI", 14),  # Bigger font for icon
                bg=default_bg,
                activebackground=default_bg,
                selectcolor=default_bg,
                relief=tk.FLAT,
                bd=0,
                padx=0
            )
            rb.pack(side=tk.LEFT)
            
            # Small text label
            tk.Label(
                tool_frame,
                text=label,
                font=("Segoe UI", 8),
                bg=default_bg,
                fg="#555"
            ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Color selection section
        color_frame = ttk.LabelFrame(self.scrollable_control_frame, text="Shape Color", padding=10)
        color_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Current color display
        self.color_display_frame = tk.Frame(color_frame, height=30, bg=self.selected_color, relief=tk.RAISED, bd=2)
        self.color_display_frame.pack(fill=tk.X, pady=2)
        
        # Color picker button
        ttk.Button(color_frame, text="Choose Color", command=self.choose_color, width=20).pack(pady=2)
        
        # Opacity control
        opacity_frame = ttk.Frame(color_frame)
        opacity_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(opacity_frame, text="Opacity:").pack(side=tk.LEFT)
        self.opacity_scale = ttk.Scale(
            opacity_frame, 
            from_=0.1, 
            to=1.0, 
            variable=self.opacity_var,
            command=self.update_opacity,
            orient=tk.HORIZONTAL,
            length=120
        )
        self.opacity_scale.pack(side=tk.LEFT, padx=5)
        
        self.opacity_label = ttk.Label(opacity_frame, text="100%")
        self.opacity_label.pack(side=tk.LEFT, padx=5)
        
        # Random color checkbox
        self.random_color_var = tk.BooleanVar(value=self.use_random_colors)
        self.random_color_checkbox = ttk.Checkbutton(
            color_frame,
            text="Use Random Colors",
            variable=self.random_color_var,
            command=self.toggle_random_colors
        )
        self.random_color_checkbox.pack(anchor=tk.W, pady=5)
        

        

        
        # Instructions
        instruction_frame = ttk.LabelFrame(self.scrollable_control_frame, text="Instructions", padding=10)
        instruction_frame.pack(fill=tk.X)
        
        instructions = [
            "• Select tool: Click and move shapes",
            "• Left click + drag: Draw shapes",
            "• Polygon: Click and drag to draw lines",
            "• Hold Shift: Draw straight polygon lines",
            "• Right click + drag: Pan view",
            "• Mouse wheel: Zoom in/out",
            "• Ctrl+Z: Undo last action",
            "• Delete/Backspace: Delete selected",
            "• ESC: Cancel drawing"
        ]
        
        for instruction in instructions:
            ttk.Label(instruction_frame, text=instruction, font=("Arial", 8)).pack(anchor=tk.W)
    
    def setup_canvas_area(self, parent):
        """Setup the canvas area for PDF display and drawing"""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Canvas with scrollbars
        canvas_container = ttk.Frame(canvas_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.HORIZONTAL)
        
        # Canvas
        self.canvas = tk.Canvas(
            canvas_container,
            bg="white",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            scrollregion=(0, 0, 1000, 1000)
        )
        
        # Configure scrollbars
        v_scrollbar.config(command=self.canvas.yview)
        h_scrollbar.config(command=self.canvas.xview)
        
        # Pack scrollbars and canvas
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.start_pan)  # Right click for pan
        self.canvas.bind("<B3-Motion>", self.pan_motion)
        self.canvas.bind("<ButtonRelease-3>", self.end_pan)
        self.canvas.bind("<MouseWheel>", self.zoom_canvas)  # Mouse wheel zoom
        
        # Bind escape key to cancel drawing (bind to canvas so it works in embedded mode)
        self.canvas.bind("<Escape>", self.cancel_drawing)
        self.canvas.focus_set()  # Allow canvas to receive key events
        
        # Instructions
        instruction_text = "Load a PDF file and click 'Process PDF' to begin mapping your store layout"
        self.canvas.create_text(500, 300, text=instruction_text, font=("Arial", 16), fill="gray")
    
    def setup_status_bar(self):
        """Setup the status bar"""
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Select a PDF file to begin")
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
    
    def browse_pdf_file(self):
        """Open file dialog to select PDF file"""
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if file_path:
            self.current_pdf_path = file_path
            filename = os.path.basename(file_path)
            self.file_info.set(f"Selected: {filename}")
            self.status_var.set(f"PDF selected: {filename}")
            # Automatically process the PDF
            self.process_pdf()
    
    def process_pdf(self):
        """Process the selected PDF file using PyMuPDF"""
        if not self.current_pdf_path:
            messagebox.showerror("Error", "No PDF file selected")
            return
        
        try:
            self.status_var.set("Processing PDF...")
            self.root.update()
            
            # Open PDF with PyMuPDF
            doc = fitz.open(self.current_pdf_path)
            
            if len(doc) == 0:
                messagebox.showerror("Error", "PDF file appears to be empty")
                return
            
            # Get first page
            page = doc[0]
            
            # Convert to image
            # Increase resolution for better quality (default is 72 DPI, we use 150)
            mat = fitz.Matrix(150/72, 150/72)  # Scale factor for higher DPI
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("ppm")
            self.pdf_image = Image.open(io.BytesIO(img_data))
            
            # Close the document
            doc.close()
            
            # Reset zoom and display
            self.zoom_factor = 1.0
            self.original_image_size = None
            self.display_pdf_image()
            
            # Initialize undo system for new PDF
            self.history.clear()
            self.history_index = -1
            self.save_state("Initial PDF load")
            
            # Auto-fit to window on first load
            self.root.after(100, self.fit_to_window)  # Delay to ensure canvas is sized
            
            # Trigger callback to sync PDF to other apps (e.g., Text Labeler)
            if self.on_pdf_loaded:
                self.on_pdf_loaded(self.current_pdf_path)
            
            self.status_var.set("PDF processed successfully - Start drawing shapes")
                
        except Exception as e:
            error_msg = str(e)
            messagebox.showerror("Error", f"Error processing PDF: {error_msg}")
            self.status_var.set("Error processing PDF")
    

    def display_pdf_image(self):
        """Display the PDF image on canvas with zoom"""
        if not self.pdf_image:
            return
        
        # Clear canvas
        self.canvas.delete("all")
        
        # Store original size on first display
        if self.original_image_size is None:
            self.original_image_size = self.pdf_image.size
        
        # Calculate new size based on zoom
        original_width, original_height = self.original_image_size
        new_width = int(original_width * self.zoom_factor)
        new_height = int(original_height * self.zoom_factor)
        
        # Resize image
        if self.zoom_factor != 1.0:
            # Use high-quality resampling
            display_image = self.pdf_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            display_image = self.pdf_image
        
        # Convert to PhotoImage and display
        self.canvas_image = ImageTk.PhotoImage(display_image)
        self.canvas.create_image(10, 10, anchor=tk.NW, image=self.canvas_image, tags="pdf_image")
        
        # Redraw all shapes at new zoom level
        self.redraw_shapes()
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def redraw_shapes(self):
        """Redraw all shapes at current zoom level"""
        # Remove existing shape displays
        for shape in self.shapes:
            if "canvas_id" in shape:
                try:
                    self.canvas.delete(shape["canvas_id"])
                except:
                    pass  # Ignore errors if shape doesn't exist
            if "selection_id" in shape:
                try:
                    self.canvas.delete(shape["selection_id"])
                    del shape["selection_id"]
                except:
                    pass
        
        # Get PDF image bounds for clamping coordinates
        if self.pdf_image:
            img_width, img_height = self.original_image_size if self.original_image_size else self.pdf_image.size
        else:
            img_width, img_height = 1000, 1000  # Default bounds
        
        # Redraw all shapes
        for shape in self.shapes:
            try:
                # Convert image coordinates back to canvas coordinates
                img_coords = shape["coordinates"]
                
                color = shape["color"]
                shape_type = shape["type"]
                
                if shape_type == "rectangle":
                    x1, y1 = self.image_to_canvas_coords(img_coords[0], img_coords[1])
                    x2, y2 = self.image_to_canvas_coords(img_coords[2], img_coords[3])
                    
                    # Normalize coordinates to ensure x1 <= x2 and y1 <= y2
                    x1, x2 = min(x1, x2), max(x1, x2)
                    y1, y2 = min(y1, y2), max(y1, y2)
                    
                    shape_id = self.canvas.create_rectangle(
                        x1, y1, x2, y2,
                        fill=color,
                        outline="",
                        width=0,
                        stipple=shape.get("stipple", "")
                    )
                elif shape_type == "oval":
                    x1, y1 = self.image_to_canvas_coords(img_coords[0], img_coords[1])
                    x2, y2 = self.image_to_canvas_coords(img_coords[2], img_coords[3])
                    
                    # Normalize coordinates to ensure x1 <= x2 and y1 <= y2
                    x1, x2 = min(x1, x2), max(x1, x2)
                    y1, y2 = min(y1, y2), max(y1, y2)
                    
                    shape_id = self.canvas.create_oval(
                        x1, y1, x2, y2,
                        fill=color,
                        outline="",
                        width=0,
                        stipple=shape.get("stipple", "")
                    )
                elif shape_type == "line":
                    x1, y1 = self.image_to_canvas_coords(img_coords[0], img_coords[1])
                    x2, y2 = self.image_to_canvas_coords(img_coords[2], img_coords[3])
                    
                    shape_id = self.canvas.create_line(
                        x1, y1, x2, y2,
                        fill=color,
                        width=5
                    )
                elif shape_type == "polygon":
                    # Convert all polygon points from image to canvas coordinates
                    canvas_points = []
                    for i in range(0, len(img_coords), 2):
                        img_x, img_y = img_coords[i], img_coords[i + 1]
                        canvas_x, canvas_y = self.image_to_canvas_coords(img_x, img_y)
                        canvas_points.extend([canvas_x, canvas_y])
                    
                    shape_id = self.canvas.create_polygon(
                        canvas_points,
                        fill=color,
                        outline="",
                        width=0,
                        stipple=shape.get("stipple", "")
                    )
                else:
                    continue  # Skip unknown shape types
                
                # Store the canvas ID for future reference
                shape["canvas_id"] = shape_id
            except Exception as e:
                # If there's any error drawing a shape, skip it and continue
                print(f"Error drawing shape: {e}")
                continue
    
    def on_canvas_click(self, event):
        """Handle canvas click events"""
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Convert to image coordinates for shape detection
        img_x, img_y = self.canvas_to_image_coords(canvas_x, canvas_y)
        
        # Check if clicking on a shape (regardless of current tool)
        clicked_shape = None
        for shape in reversed(self.shapes):  # Check from top to bottom
            if self.is_point_in_shape((img_x, img_y), shape):
                clicked_shape = shape
                break
        
        # If clicked on a shape, select it in the listbox
        if clicked_shape:
            try:
                shape_index = self.shapes.index(clicked_shape)
                self.shape_listbox.selection_clear(0, tk.END)
                self.shape_listbox.selection_set(shape_index)
                self.shape_listbox.see(shape_index)
                # Trigger the selection event to highlight the shape
                self.on_shape_list_select(None)
            except (ValueError, tk.TclError):
                pass  # Shape not found or listbox error
        
        # Continue with normal tool behavior
        if self.current_tool == "select":
            # Selection mode
            self.handle_selection(canvas_x, canvas_y)
        elif self.current_tool == "polygon":
            # Polygon drawing mode - start drawing on mouse down
            self.start_polygon_point(canvas_x, canvas_y, event)
        else:
            # Regular drawing mode
            if not clicked_shape:  # Only clear selection if not clicking on a shape
                self.clear_selection()
            self.start_drawing(event)
    
    def on_canvas_drag(self, event):
        """Handle canvas drag events"""
        if self.current_tool == "select" and self.resizing:
            self.resize_selected_shape(event)
        elif self.current_tool == "select" and self.moving_shape:
            self.move_selected_shape(event)
        elif self.current_tool == "polygon" and self.drawing_polygon:
            # Show live preview while dragging polygon line
            self.polygon_drag_motion(event)
        elif self.drawing:
            self.draw_motion(event)
    
    def on_canvas_release(self, event):
        """Handle canvas release events"""
        if self.resizing:
            self.finish_resize()
        elif self.moving_shape:
            self.finish_move()
        elif self.current_tool == "polygon" and self.drawing_polygon:
            # Finalize polygon point on mouse release
            self.polygon_drag_release(event)
        elif self.drawing:
            self.end_drawing(event)
    
    def start_pan(self, event):
        """Start panning with right mouse button"""
        self.panning = True
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.config(cursor="fleur")
    
    def pan_motion(self, event):
        """Handle panning motion"""
        if not self.panning:
            return
        
        # Use canvas scan_dragto for smooth panning
        self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def end_pan(self, event):
        """End panning"""
        self.panning = False
        self.canvas.config(cursor="")
    
    def zoom_canvas(self, event):
        """Zoom canvas with mouse wheel"""
        # Get zoom direction
        if event.delta > 0 or event.num == 4:  # Zoom in
            self.zoom_in()
        elif event.delta < 0 or event.num == 5:  # Zoom out
            self.zoom_out()
    
    def zoom_in(self):
        """Zoom in by 25%"""
        self.zoom_factor *= 1.25
        self.update_zoom()
    
    def zoom_out(self):
        """Zoom out by 25%"""
        self.zoom_factor /= 1.25
        if self.zoom_factor < 0.1:  # Minimum zoom
            self.zoom_factor = 0.1
        self.update_zoom()
    
    def actual_size(self):
        """Set zoom to 100%"""
        self.zoom_factor = 1.0
        self.update_zoom()
    
    def fit_to_window(self):
        """Fit image to canvas window"""
        if not self.pdf_image:
            return
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            img_width, img_height = self.pdf_image.size
            
            # Calculate zoom to fit
            zoom_x = canvas_width / img_width
            zoom_y = canvas_height / img_height
            
            self.zoom_factor = min(zoom_x, zoom_y) * 0.9  # 90% to leave some margin
            self.update_zoom()
    
    def update_zoom(self):
        """Update the display with current zoom level"""
        if not self.pdf_image:
            return
        
        # Update zoom display
        self.zoom_var.set(f"Zoom: {int(self.zoom_factor * 100)}%")
        
        # Redisplay image at new zoom level
        self.display_pdf_image()
    
    def handle_selection(self, x, y):
        """Handle shape selection"""
        # Find shape at click position
        clicked_item = self.canvas.find_closest(x, y)[0]
        
        # Check if clicked on a resize handle
        if self.selected_shape and "resize_handles" in self.selected_shape:
            for handle_type, handle_id in self.selected_shape["resize_handles"]:
                if clicked_item == handle_id:
                    # Start resizing
                    self.resizing = True
                    self.resize_handle = handle_type
                    self.move_start_x = x
                    self.move_start_y = y
                    return
        
        # Check if clicked item belongs to a shape
        selected_shape = None
        for shape in self.shapes:
            if shape.get("canvas_id") == clicked_item:
                selected_shape = shape
                break
        
        if selected_shape:
            self.select_shape(selected_shape)
            # Start moving
            self.moving_shape = True
            self.move_start_x = x
            self.move_start_y = y
        else:
            self.clear_selection()
    
    def select_shape(self, shape):
        """Select a shape and highlight it"""
        # Clear previous selection
        self.clear_selection()
        
        self.selected_shape = shape
        
        # Add selection highlight and resize handles
        if "canvas_id" in shape:
            # Get shape bounds
            bbox = self.canvas.bbox(shape["canvas_id"])
            if bbox:
                x1, y1, x2, y2 = bbox
                # Create selection rectangle
                selection_id = self.canvas.create_rectangle(
                    x1-3, y1-3, x2+3, y2+3,
                    outline="blue",
                    width=2,
                    dash=(5, 5),
                    tags="selection"
                )
                shape["selection_id"] = selection_id
                
                # Add resize handles at corners (only for rectangles, ovals, and lines)
                if shape["type"] in ["rectangle", "oval", "line"]:
                    handle_size = 12  # Bigger handles for easier clicking
                    handles = []
                    
                    # Top-left handle
                    h1 = self.canvas.create_rectangle(
                        x1-handle_size/2, y1-handle_size/2,
                        x1+handle_size/2, y1+handle_size/2,
                        fill="red", outline="white", width=2,
                        tags="resize_handle"
                    )
                    handles.append(("nw", h1))
                    
                    # Top-right handle
                    h2 = self.canvas.create_rectangle(
                        x2-handle_size/2, y1-handle_size/2,
                        x2+handle_size/2, y1+handle_size/2,
                        fill="red", outline="white", width=2,
                        tags="resize_handle"
                    )
                    handles.append(("ne", h2))
                    
                    # Bottom-left handle
                    h3 = self.canvas.create_rectangle(
                        x1-handle_size/2, y2-handle_size/2,
                        x1+handle_size/2, y2+handle_size/2,
                        fill="red", outline="white", width=2,
                        tags="resize_handle"
                    )
                    handles.append(("sw", h3))
                    
                    # Bottom-right handle
                    h4 = self.canvas.create_rectangle(
                        x2-handle_size/2, y2-handle_size/2,
                        x2+handle_size/2, y2+handle_size/2,
                        fill="red", outline="white", width=2,
                        tags="resize_handle"
                    )
                    handles.append(("se", h4))
                    
                    shape["resize_handles"] = handles
        
        # Also select the shape in the listbox
        if hasattr(self, 'shape_listbox'):
            # Find the index of this shape in the shapes list
            try:
                shape_index = self.shapes.index(shape)
                # Clear current selection and select this shape
                self.shape_listbox.selection_clear(0, tk.END)
                self.shape_listbox.selection_set(shape_index)
                # Scroll to make it visible
                self.shape_listbox.see(shape_index)
            except (ValueError, tk.TclError):
                pass  # Shape not found in list or listbox error
        
        self.status_var.set(f"Selected {shape['type']} - Drag to move or resize, Delete to remove")
    
    def clear_selection(self):
        """Clear current selection"""
        if self.selected_shape:
            # Remove selection highlight
            if "selection_id" in self.selected_shape:
                self.canvas.delete(self.selected_shape["selection_id"])
                del self.selected_shape["selection_id"]
            
            # Remove resize handles
            if "resize_handles" in self.selected_shape:
                for _, handle_id in self.selected_shape["resize_handles"]:
                    self.canvas.delete(handle_id)
                del self.selected_shape["resize_handles"]
        
        self.selected_shape = None
        self.canvas.delete("selection")
    
    def move_selected_shape(self, event):
        """Move the selected shape"""
        if not self.selected_shape or not self.moving_shape:
            return
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Calculate movement delta
        dx = canvas_x - self.move_start_x
        dy = canvas_y - self.move_start_y
        
        # Move the shape (no bounds checking - allow free movement)
        if "canvas_id" in self.selected_shape:
            self.canvas.move(self.selected_shape["canvas_id"], dx, dy)
            
            # Move selection highlight
            if "selection_id" in self.selected_shape:
                self.canvas.move(self.selected_shape["selection_id"], dx, dy)
        
        # Update start position for next move
        self.move_start_x = canvas_x
        self.move_start_y = canvas_y
    
    def finish_move(self):
        """Finish moving a shape and update its coordinates"""
        if self.selected_shape and self.moving_shape:
            try:
                # Get canvas ID
                canvas_id = self.selected_shape["canvas_id"]
                shape_type = self.selected_shape["type"]
                
                # Save action for undo
                self.save_state(f"Move {shape_type}")
                
                if shape_type == "polygon":
                    # For polygons, get all coordinates from canvas
                    canvas_coords = self.canvas.coords(canvas_id)
                    
                    # Convert all canvas coordinates to image coordinates
                    img_coords = []
                    for i in range(0, len(canvas_coords), 2):
                        canvas_x, canvas_y = canvas_coords[i], canvas_coords[i + 1]
                        img_x, img_y = self.canvas_to_image_coords(canvas_x, canvas_y)
                        img_coords.extend([img_x, img_y])
                    
                    # Update coordinates
                    self.selected_shape["coordinates"] = img_coords
                else:
                    # For rectangles, ovals, and lines - use bounding box
                    bbox = self.canvas.bbox(canvas_id)
                    
                    if bbox:
                        x1, y1, x2, y2 = bbox
                        
                        # Convert to image coordinates
                        img_x1, img_y1 = self.canvas_to_image_coords(x1, y1)
                        img_x2, img_y2 = self.canvas_to_image_coords(x2, y2)
                        
                        # Update coordinates
                        self.selected_shape["coordinates"] = [img_x1, img_y1, img_x2, img_y2]
                
                self.status_var.set(f"Moved {shape_type}")
            except Exception as e:
                # If there's an error, just redraw everything
                print(f"Error finishing move: {e}")
                import traceback
                traceback.print_exc()
                self.redraw_shapes()
        
        self.moving_shape = False
    
    def resize_selected_shape(self, event):
        """Resize the selected shape by dragging a handle"""
        if not self.selected_shape or not self.resizing:
            return
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Get current coordinates
        coords = self.selected_shape["coordinates"]
        img_x1, img_y1, img_x2, img_y2 = coords
        
        # Convert current mouse position to image coordinates
        img_x, img_y = self.canvas_to_image_coords(canvas_x, canvas_y)
        
        # Update coordinates based on which handle is being dragged
        if self.resize_handle == "nw":  # Top-left
            img_x1, img_y1 = img_x, img_y
        elif self.resize_handle == "ne":  # Top-right
            img_x2, img_y1 = img_x, img_y
        elif self.resize_handle == "sw":  # Bottom-left
            img_x1, img_y2 = img_x, img_y
        elif self.resize_handle == "se":  # Bottom-right
            img_x2, img_y2 = img_x, img_y
        
        # Update shape coordinates
        self.selected_shape["coordinates"] = [img_x1, img_y1, img_x2, img_y2]
        
        # Redraw to show the resize
        self.redraw_shapes()
        # Re-select to update handles
        self.select_shape(self.selected_shape)
    
    def finish_resize(self):
        """Finish resizing a shape"""
        if self.selected_shape and self.resizing:
            # Save action for undo
            self.save_state(f"Resize {self.selected_shape['type']}")
            self.status_var.set(f"Resized {self.selected_shape['type']}")
        
        self.resizing = False
        self.resize_handle = None
    
    def delete_selected(self, event=None):
        """Delete the selected shape"""
        if self.selected_shape:
            # Ask for confirmation
            shape_name = self.selected_shape.get("name", f"{self.selected_shape['type']}")
            confirm = messagebox.askyesno(
                "Confirm Deletion",
                f"Are you sure you want to delete '{shape_name}'?\n\nThis will also delete any associated labels.",
                icon='warning'
            )
            
            if not confirm:
                return  # User cancelled
            
            # Get the shape index before deletion (for label cleanup)
            try:
                shape_index = self.shapes.index(self.selected_shape)
            except ValueError:
                # Shape not in list, can't delete
                self.status_var.set("Error: Shape not found in list")
                return
            
            # Save state for undo
            self.save_state(f"Delete {self.selected_shape['type']}")
            
            # Remove from canvas
            if "canvas_id" in self.selected_shape:
                self.canvas.delete(self.selected_shape["canvas_id"])
            
            # Call deletion callback BEFORE removing from list (for label cleanup)
            if hasattr(self, 'on_shape_deleted') and self.on_shape_deleted:
                self.on_shape_deleted(shape_index)
            
            # Remove from shapes list using index (more reliable)
            del self.shapes[shape_index]
            
            # Clear selection
            self.clear_selection()
            
            self.status_var.set("Shape deleted")
            self.update_shape_list()  # Update list after deletion
        else:
            self.status_var.set("No shape selected to delete")
    
    def update_shape_list(self):
        """Update the shape listbox"""
        if not hasattr(self, 'shape_listbox'):
            return
        
        self.shape_listbox.delete(0, tk.END)
        for i, shape in enumerate(self.shapes):
            shape_name = shape.get("name", f"Shape {i+1}")
            shape_type = shape.get("type", "unknown")
            self.shape_listbox.insert(tk.END, f"{shape_name} ({shape_type})")
    
    def on_shape_list_select(self, event):
        """Handle shape selection from listbox"""
        selection = self.shape_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.shapes):
                self.select_shape(self.shapes[index])
    
    def rename_selected_shape(self):
        """Rename the selected shape"""
        if not self.selected_shape:
            messagebox.showinfo("Info", "Please select a shape first")
            return
        
        from tkinter import simpledialog
        current_name = self.selected_shape.get("name", "")
        new_name = simpledialog.askstring(
            "Rename Shape",
            "Enter new name for shape:",
            initialvalue=current_name
        )
        
        if new_name and new_name.strip():
            self.selected_shape["name"] = new_name.strip()
            self.update_shape_list()
            self.status_var.set(f"Renamed shape to '{new_name}'")
    
    def save_state(self, action_name):
        """Save current state for undo functionality"""
        # Remove any states after current index (for redo functionality)
        self.history = self.history[:self.history_index + 1]
        
        # Save current state
        state = {
            "action": action_name,
            "shapes": [shape.copy() for shape in self.shapes],
            "timestamp": len(self.history)
        }
        
        self.history.append(state)
        self.history_index += 1
        
        # Limit history size
        if len(self.history) > 20:
            self.history.pop(0)
            self.history_index -= 1
    
    def undo_action(self, event=None):
        """Undo the last action"""
        if self.history_index > 0:
            self.history_index -= 1
            
            # Restore previous state
            prev_state = self.history[self.history_index]
            
            # Clear current shapes from canvas
            for shape in self.shapes:
                if "canvas_id" in shape:
                    try:
                        self.canvas.delete(shape["canvas_id"])
                    except:
                        pass
                if "selection_id" in shape:
                    try:
                        self.canvas.delete(shape["selection_id"])
                    except:
                        pass
            
            # Clear selection
            self.clear_selection()
            
            # Restore shapes (make deep copies and remove old canvas_ids)
            self.shapes = []
            for shape in prev_state["shapes"]:
                new_shape = shape.copy()
                # Remove old canvas_id and selection_id so redraw creates new ones
                new_shape.pop("canvas_id", None)
                new_shape.pop("selection_id", None)
                self.shapes.append(new_shape)
            
            # Redraw all shapes
            self.redraw_shapes()
            
            # Update shape list
            self.update_shape_list()
            
            self.status_var.set(f"Undone: {prev_state.get('action', 'Unknown action')}")
        else:
            self.status_var.set("Nothing to undo")
    
    def redo_action(self, event=None):
        """Redo the last undone action"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            
            # Restore next state
            next_state = self.history[self.history_index]
            
            # Clear current shapes from canvas
            for shape in self.shapes:
                if "canvas_id" in shape:
                    try:
                        self.canvas.delete(shape["canvas_id"])
                    except:
                        pass
                if "selection_id" in shape:
                    try:
                        self.canvas.delete(shape["selection_id"])
                    except:
                        pass
            
            # Clear selection
            self.clear_selection()
            
            # Restore shapes (make deep copies and remove old canvas_ids)
            self.shapes = []
            for shape in next_state["shapes"]:
                new_shape = shape.copy()
                # Remove old canvas_id and selection_id so redraw creates new ones
                new_shape.pop("canvas_id", None)
                new_shape.pop("selection_id", None)
                self.shapes.append(new_shape)
            
            # Redraw all shapes
            self.redraw_shapes()
            
            # Update shape list
            self.update_shape_list()
            
            self.status_var.set(f"Redone: {next_state.get('action', 'Unknown action')}")
        else:
            self.status_var.set("Nothing to redo")
    
    def cancel_drawing(self, event=None):
        """Cancel current drawing operation"""
        # Cancel regular shape drawing (rectangle, oval)
        if self.drawing:
            self.drawing = False
            if self.preview_shape:
                self.canvas.delete(self.preview_shape)
                self.preview_shape = None
            self.canvas.delete("preview")
            self.status_var.set("Drawing cancelled")
        
        # Cancel polygon drawing
        if self.drawing_polygon:
            # Clear all temporary polygon lines
            self.canvas.delete("temp_polygon")
            
            # Clear preview line
            if hasattr(self, 'polygon_preview_line') and self.polygon_preview_line:
                self.canvas.delete(self.polygon_preview_line)
                self.polygon_preview_line = None
            
            # Reset polygon state
            self.drawing_polygon = False
            self.polygon_points = []
            self.polygon_lines = []
            
            self.status_var.set("Polygon drawing cancelled")
    
    
    
    def change_tool(self):
        """Change the current drawing tool"""
        requested_tool = self.tool_var.get()
        
        # Update current tool
        self.current_tool = requested_tool
        
        # Clear selection when switching tools
        if self.current_tool != "select":
            self.clear_selection()
        
        self.status_var.set(f"Selected tool: {self.current_tool}")
    
    def choose_color(self):
        """Open color chooser dialog"""
        color = colorchooser.askcolor(title="Choose Shape Color", color=self.selected_color)
        if color[1]:  # If a color was selected (not cancelled)
            self.selected_color = color[1]
            self.update_color_display()
            self.color_var.set(self.selected_color)
    
    def set_quick_color(self, color):
        """Set color from quick palette"""
        self.selected_color = color
        self.update_color_display()
        self.color_var.set(self.selected_color)
    
    def toggle_random_colors(self):
        """Toggle between random colors and manual color selection"""
        self.use_random_colors = self.random_color_var.get()
        if self.use_random_colors:
            self.status_var.set("Random colors enabled - each shape gets a unique color")
        else:
            self.status_var.set(f"Manual color selected - using {self.selected_color}")
    
    def get_color_with_opacity(self):
        """Get the current color blended with white based on opacity"""
        try:
            opacity = float(self.opacity_var.get())
        except:
            opacity = 1.0
        
        # Parse the hex color
        color = self.selected_color.lstrip('#')
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
        except:
            r, g, b = 255, 107, 107  # Default color
        
        # Blend with white based on opacity
        # opacity = 1.0 means full color, opacity = 0.0 means white
        r = int(r * opacity + 255 * (1 - opacity))
        g = int(g * opacity + 255 * (1 - opacity))
        b = int(b * opacity + 255 * (1 - opacity))
        
        # Return as hex color
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def get_stipple_pattern(self):
        """Get stipple pattern based on current opacity setting"""
        opacity = self.opacity_var.get()
        
        # Map opacity to stipple patterns with more granular control
        # Tkinter stipple patterns: gray75, gray50, gray25, gray12
        if opacity >= 0.95:
            return ""  # No stipple for very high opacity (95-100%)
        elif opacity >= 0.85:
            return "gray12"  # Very light stipple (85-94%)
        elif opacity >= 0.60:
            return "gray25"  # Light stipple (60-84%) - 80% falls here
        elif opacity >= 0.35:
            return "gray50"  # Medium stipple (35-59%)
        else:
            return "gray75"  # Heavy stipple (0-34%)
    
    def update_opacity(self, value):
        """Update opacity display when slider changes"""
        opacity = self.opacity_var.get()
        self.opacity_label.config(text=f"{int(opacity * 100)}%")
    
    def start_drawing(self, event):
        """Start drawing a shape"""
        if self.current_tool == "polygon":
            return
        
        self.drawing = True
        # Convert screen coordinates to canvas coordinates accounting for zoom
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        # Generate color for this shape - random or selected
        if self.use_random_colors:
            self.current_shape_color = self.get_random_color()
        else:
            self.current_shape_color = self.selected_color
    
    def draw_motion(self, event):
        """Handle drawing motion with live preview"""
        if not self.drawing:
            return
        
        # Remove previous preview shape
        if self.preview_shape:
            self.canvas.delete(self.preview_shape)
            self.preview_shape = None
        
        # Convert screen coordinates to canvas coordinates
        current_x = self.canvas.canvasx(event.x)
        current_y = self.canvas.canvasy(event.y)
        
        # Use the random color generated at start_drawing
        preview_color = self.current_shape_color
        
        if self.current_tool == "rectangle":
            self.preview_shape = self.canvas.create_rectangle(
                self.start_x, self.start_y, current_x, current_y,
                fill=preview_color,
                outline="gray",
                width=2,
                stipple=self.get_stipple_pattern(),
                tags="preview"
            )
        elif self.current_tool == "line":
            self.preview_shape = self.canvas.create_line(
                self.start_x, self.start_y, current_x, current_y,
                fill=preview_color,
                width=3,
                tags="preview"
            )
        elif self.current_tool == "oval":
            self.preview_shape = self.canvas.create_oval(
                self.start_x, self.start_y, current_x, current_y,
                fill=preview_color,
                outline="gray",
                width=2,
                stipple=self.get_stipple_pattern(),
                tags="preview"
            )
        
        # Update status with coordinates
        self.status_var.set(f"Drawing {self.current_tool}: ({int(self.start_x)}, {int(self.start_y)}) to ({int(current_x)}, {int(current_y)})")
    
    
    def end_drawing(self, event):
        """Finish drawing a shape"""
        if not self.drawing:
            return
        
        self.drawing = False
        
        # Remove preview shape
        if self.preview_shape:
            self.canvas.delete(self.preview_shape)
            self.preview_shape = None
        
        # Convert screen coordinates to canvas coordinates
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        
        # Only create shape if there's meaningful movement
        min_distance = 10  # Minimum pixels to consider it a real shape
        if abs(end_x - self.start_x) > min_distance or abs(end_y - self.start_y) > min_distance:
            # Create the final shape
            self.create_shape(self.start_x, self.start_y, end_x, end_y)
        else:
            self.status_var.set("Shape too small - try drawing a larger area")
    
    def lighten_color(self, color):
        """Lighten a color for preview display"""
        # Convert hex to RGB
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        
        # Lighten by adding 50 to each component (max 255)
        lightened = tuple(min(255, c + 50) for c in rgb)
        
        # Convert back to hex
        return f"#{lightened[0]:02x}{lightened[1]:02x}{lightened[2]:02x}"
    
    def canvas_to_image_coords(self, canvas_x, canvas_y):
        """Convert canvas coordinates to image coordinates accounting for zoom"""
        # Adjust for image position (offset by 10, 10)
        img_x = (canvas_x - 10) / self.zoom_factor
        img_y = (canvas_y - 10) / self.zoom_factor
        return img_x, img_y
    
    def image_to_canvas_coords(self, img_x, img_y):
        """Convert image coordinates to canvas coordinates accounting for zoom"""
        canvas_x = img_x * self.zoom_factor + 10
        canvas_y = img_y * self.zoom_factor + 10
        return canvas_x, canvas_y
    
    def is_point_in_shape(self, point, shape):
        """Check if a point is inside a shape"""
        x, y = point
        coords = shape["coordinates"]
        shape_type = shape.get("type", "rectangle")
        
        if shape_type == "rectangle" or shape_type == "oval":
            x1, y1, x2, y2 = coords
            return min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)
        elif shape_type == "polygon":
            # Use ray casting algorithm for polygon
            points = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
            return self.point_in_polygon(point, points)
        elif shape_type == "circle":
            # Circle coordinates: [cx, cy, radius]
            if len(coords) >= 3:
                cx, cy, radius = coords[0], coords[1], coords[2]
                distance = ((x - cx)**2 + (y - cy)**2)**0.5
                return distance <= radius
        
        return False
    
    def point_in_polygon(self, point, polygon):
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
    
    def get_random_color(self):
        """Generate a random vibrant color for shapes"""
        # Predefined palette of vibrant, distinct colors
        color_palette = [
            "#FF6B6B",  # Red
            "#4ECDC4",  # Teal
            "#45B7D1",  # Blue
            "#FFA07A",  # Light Salmon
            "#98D8C8",  # Mint
            "#F7DC6F",  # Yellow
            "#BB8FCE",  # Purple
            "#85C1E2",  # Sky Blue
            "#F8B88B",  # Peach
            "#ABEBC6",  # Light Green
            "#FAD7A0",  # Light Orange
            "#D7BDE2",  # Lavender
            "#A3E4D7",  # Aqua
            "#F9E79F",  # Light Yellow
            "#EDBB99",  # Tan
            "#D98880",  # Rose
            "#85929E",  # Gray Blue
            "#A9DFBF",  # Pale Green
            "#F5B7B1",  # Pink
            "#AED6F1",  # Powder Blue
        ]
        
        # Pick a random color from the palette
        return random.choice(color_palette)
    
    def create_shape(self, x1, y1, x2, y2):
        """Create a shape on the canvas"""
        # Use the random color generated at start_drawing
        random_color = self.current_shape_color
        
        # Store coordinates in image space for saving/loading
        img_x1, img_y1 = self.canvas_to_image_coords(x1, y1)
        img_x2, img_y2 = self.canvas_to_image_coords(x2, y2)
        
        shape_data = {
            "type": self.current_tool,
            "coordinates": (img_x1, img_y1, img_x2, img_y2),  # Store in image coordinates
            "color": random_color,
            "stipple": self.get_stipple_pattern()
        }
        
        # Draw at current canvas coordinates
        if self.current_tool == "rectangle":
            shape_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=random_color,
                outline="",
                width=0,
                stipple=self.get_stipple_pattern()
            )
        elif self.current_tool == "oval":
            stipple = self.get_stipple_pattern()
            print(f"Creating oval with opacity: {self.opacity_var.get()}, stipple: '{stipple}'")
            shape_id = self.canvas.create_oval(
                x1, y1, x2, y2,
                fill=random_color,
                outline="",
                width=0,
                stipple=stipple
            )
        elif self.current_tool == "polygon":
            # This should not be called for polygon - handled separately
            return
        
        shape_data["canvas_id"] = shape_id
    
        # Add shape to list FIRST
        self.shapes.append(shape_data)
        
        # Then save state for undo (after adding shape)
        self.save_state(f"Create {self.current_tool}")
        
        self.update_shape_list()  # Update shape list
        
        self.status_var.set(f"Created {self.current_tool} with random color (opacity: {int(self.opacity * 100)}%)")
    
    def clear_all(self, save_state=True):
        """Clear all drawn shapes"""
        if save_state and self.shapes:
            self.save_state("Clear all shapes")
        
        for shape in self.shapes:
            if "canvas_id" in shape:
                self.canvas.delete(shape["canvas_id"])
        
        self.shapes.clear()
        self.clear_selection()
        self.update_shape_list()  # Update the shape listbox to reflect cleared shapes
        self.status_var.set("All shapes cleared")
    
    def save_layout(self):
        """Save the current layout to a JSON file"""
        if not self.shapes:
            messagebox.showwarning("Warning", "No shapes to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Layout",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                layout_data = {
                    "pdf_file": self.current_pdf_path,
                    "shapes": [
                        {
                            "type": shape["type"],
                            "coordinates": shape["coordinates"],
                            "color": shape["color"],
                            "stipple": shape.get("stipple", "")
                        }
                        for shape in self.shapes
                    ]
                }
                
                with open(file_path, 'w') as f:
                    json.dump(layout_data, f, indent=2)
                
                messagebox.showinfo("Success", "Layout saved successfully")
                self.status_var.set(f"Layout saved to {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error saving layout: {str(e)}")
    
    def load_layout(self):
        """Load a layout from a JSON file"""
        file_path = filedialog.askopenfilename(
            title="Load Layout",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    layout_data = json.load(f)
                
                # Clear current shapes
                self.clear_all()
                
                # Load PDF if specified
                if "pdf_file" in layout_data and layout_data["pdf_file"]:
                    if os.path.exists(layout_data["pdf_file"]):
                        self.current_pdf_path = layout_data["pdf_file"]
                        self.file_info.set(f"Loaded: {os.path.basename(self.current_pdf_path)}")
                        self.process_pdf()
                
                # Recreate shapes
                for shape_data in layout_data.get("shapes", []):
                    shape = {
                        "type": shape_data["type"],
                        "coordinates": shape_data["coordinates"],
                        "color": shape_data["color"],
                        "stipple": shape_data.get("stipple", "")
                    }
                    self.shapes.append(shape)
                
                # Redraw all shapes
                self.redraw_shapes()
                
                messagebox.showinfo("Success", "Layout loaded successfully")
                self.status_var.set(f"Layout loaded from {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error loading layout: {str(e)}")
    
    def load_json_shapes(self):
        """Load shapes from a JSON file without reloading PDF"""
        file_path = filedialog.askopenfilename(
            title="Select JSON Shapes File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Extract shapes from the JSON data
                # Support both formats: {"shapes": [...]} and direct array [...]
                if isinstance(data, dict) and "shapes" in data:
                    shapes_data = data["shapes"]
                elif isinstance(data, list):
                    shapes_data = data
                else:
                    messagebox.showerror("Error", "Invalid JSON format. Expected 'shapes' key or array.")
                    return
                
                # Clear existing shapes
                self.shapes.clear()
                
                # Load shapes from JSON
                for shape_data in shapes_data:
                    shape = {
                        "type": shape_data.get("type", "rectangle"),
                        "coordinates": shape_data.get("coordinates", []),
                        "color": shape_data.get("color", "#FF6B6B"),
                        "stipple": shape_data.get("stipple", ""),
                        "name": shape_data.get("name", "")  # Load name if available
                    }
                    self.shapes.append(shape)
                
                # Update shape list
                self.update_shape_list()
                
                # Redraw canvas
                self.redraw_shapes()
                
                messagebox.showinfo("Success", f"Loaded {len(shapes_data)} shapes from {os.path.basename(file_path)}")
                self.status_var.set(f"Loaded {len(shapes_data)} shapes from {os.path.basename(file_path)}")
                
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON file: {str(e)}")
            except Exception as e:
                messagebox.showerror("Error", f"Error loading JSON: {str(e)}")
    
    def export_image(self):
        """Export the current layout as an image"""
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
                # Create a copy of the original image
                export_image = self.pdf_image.copy()
                draw = ImageDraw.Draw(export_image)
                
                # Draw shapes on the image
                for shape in self.shapes:
                    coords = shape["coordinates"]
                    color = shape["color"]
                    shape_type = shape["type"]
                    stipple = shape.get("stipple", "")
                    
                    # Convert stipple to alpha for export
                    alpha = 255  # Default full opacity
                    if stipple == "gray75":
                        alpha = int(255 * 0.9)  # 90% opacity
                    elif stipple == "gray50":
                        alpha = int(255 * 0.7)  # 70% opacity
                    elif stipple == "gray25":
                        alpha = int(255 * 0.5)  # 50% opacity
                    elif stipple == "gray12":
                        alpha = int(255 * 0.3)  # 30% opacity
                    
                    # Convert hex color to RGB
                    color_rgb = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                    color_with_alpha = color_rgb + (alpha,)
                    
                    if shape_type == "rectangle":
                        # Create a temporary RGBA image for the shape
                        shape_img = Image.new('RGBA', export_image.size, (0, 0, 0, 0))
                        shape_draw = ImageDraw.Draw(shape_img)
                        shape_draw.rectangle(coords, fill=color_with_alpha)
                        export_image = Image.alpha_composite(export_image.convert('RGBA'), shape_img).convert('RGB')
                    elif shape_type == "line":
                        draw.line(coords, fill=color, width=5)
                    elif shape_type == "polygon":
                        # Handle polygon coordinates
                        points = []
                        for i in range(0, len(coords), 2):
                            points.append((coords[i], coords[i+1]))
                        # Create a temporary RGBA image for the polygon
                        shape_img = Image.new('RGBA', export_image.size, (0, 0, 0, 0))
                        shape_draw = ImageDraw.Draw(shape_img)
                        shape_draw.polygon(points, fill=color_with_alpha)
                        export_image = Image.alpha_composite(export_image.convert('RGBA'), shape_img).convert('RGB')
                
                export_image.save(file_path)
                messagebox.showinfo("Success", "Image exported successfully")
                self.status_var.set(f"Image exported to {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting image: {str(e)}")

    def fill_selected_color(self):
        # Fill the selected shape with the current color
        if self.selected_shape:
            # Save state for undo  
            old_color = self.selected_shape.get("color", "#000000")
            self.save_state(f"Fill {self.selected_shape['type']} color")
            
            # Update shape color
            self.selected_shape["color"] = self.get_color_with_opacity()
            self.selected_shape["stipple"] = self.get_stipple_pattern()
            
            # Update canvas object
            if "canvas_id" in self.selected_shape:
                self.canvas.itemconfig(
                    self.selected_shape["canvas_id"], 
                    fill=self.get_color_with_opacity(),
                    stipple=self.get_stipple_pattern()
                )
            
            self.status_var.set(f"Filled {self.selected_shape['type']} with color {self.selected_color} (opacity: {int(self.opacity * 100)}%)")
        else:
            self.status_var.set("No shape selected to fill")
    
    def update_opacity(self, value=None):
        """Update opacity value and refresh color display"""
        self.opacity = self.opacity_var.get()
        self.opacity_label.configure(text=f"{int(self.opacity * 100)}%")
        self.update_color_display()
        
        # Update preview shape if it exists
        if hasattr(self, 'preview_shape') and self.preview_shape:
            try:
                self.canvas.itemconfig(self.preview_shape, stipple=self.get_stipple_pattern())
            except:
                pass
    
    def update_color_display(self):
        """Update the color display frame with current color and opacity"""
        # Convert hex color to RGB
        hex_color = self.selected_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Create background color with opacity simulation
        # Simulate opacity by blending with white background
        bg_r, bg_g, bg_b = 255, 255, 255  # White background
        display_r = int(r * self.opacity + bg_r * (1 - self.opacity))
        display_g = int(g * self.opacity + bg_g * (1 - self.opacity))
        display_b = int(b * self.opacity + bg_b * (1 - self.opacity))
        
        display_color = f"#{display_r:02x}{display_g:02x}{display_b:02x}"
        self.color_display_frame.configure(bg=display_color)
    
    def get_color_with_opacity(self):
        """Get the current color formatted for canvas with opacity"""
        return self.selected_color
    
    def get_stipple_pattern(self):
        """Get stipple pattern based on opacity level"""
        if self.opacity >= 0.95:
            pattern = ""  # Solid fill - most opaque
        elif self.opacity >= 0.8:
            pattern = "gray75"  # Very light stipple - high opacity
        elif self.opacity >= 0.6:
            pattern = "gray50"  # Light stipple
        elif self.opacity >= 0.4:
            pattern = "gray25"  # Medium stipple
        elif self.opacity >= 0.2:
            pattern = "gray12"  # Heavy stipple
        else:
            pattern = "gray12"  # Very heavy stipple - most transparent
        
        return pattern
    
    def start_polygon_point(self, x, y, event):
        """Start drawing a polygon point (on mouse down)"""
        if not self.drawing_polygon:
            # Start new polygon
            self.drawing_polygon = True
            self.polygon_points = [(x, y)]
            self.polygon_lines = []
            self.polygon_preview_line = None  # For live preview during drag
            
            # Generate color for this polygon - random or selected
            if self.use_random_colors:
                self.current_shape_color = self.get_random_color()
            else:
                self.current_shape_color = self.selected_color
            
            self.status_var.set("Drag to draw line, hold Shift for straight lines, click near start to close")
        else:
            # Check if clicking near start point to close polygon
            start_x, start_y = self.polygon_points[0]
            distance = ((x - start_x) ** 2 + (y - start_y) ** 2) ** 0.5
            
            if distance < 20 and len(self.polygon_points) >= 3:
                # Close polygon and fill
                self.close_polygon()
                return
            
            # Otherwise, start dragging for next line
            # (the actual point will be added on mouse release)
    
    def polygon_drag_motion(self, event):
        """Show live preview while dragging polygon line"""
        if not self.drawing_polygon or not self.polygon_points:
            return
        
        # Get current mouse position
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Get the last point
        prev_x, prev_y = self.polygon_points[-1]
        
        # Check if Shift key is held (state & 0x0001 for Shift modifier)
        shift_held = event.state & 0x0001
        
        # If Shift is held, constrain to horizontal or vertical
        if shift_held:
            dx = abs(canvas_x - prev_x)
            dy = abs(canvas_y - prev_y)
            
            # Snap to horizontal or vertical based on which direction is larger
            if dx > dy:
                # More horizontal movement - snap to horizontal line
                canvas_y = prev_y
            else:
                # More vertical movement - snap to vertical line
                canvas_x = prev_x
        
        # Remove previous preview line
        if self.polygon_preview_line:
            self.canvas.delete(self.polygon_preview_line)
        
        # Draw preview line
        self.polygon_preview_line = self.canvas.create_line(
            prev_x, prev_y, canvas_x, canvas_y,
            fill=self.current_shape_color,
            width=3,
            dash=(5, 5),
            tags="polygon_preview"
        )
    
    def polygon_drag_release(self, event):
        """Finalize polygon point on mouse release"""
        if not self.drawing_polygon or not self.polygon_points:
            return
        
        # Get current mouse position
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Get the last point
        prev_x, prev_y = self.polygon_points[-1]
        
        # Check if Shift key is held (state & 0x0001 for Shift modifier)
        shift_held = event.state & 0x0001
        
        # If Shift is held, constrain to horizontal or vertical
        if shift_held:
            dx = abs(canvas_x - prev_x)
            dy = abs(canvas_y - prev_y)
            
            # Snap to horizontal or vertical based on which direction is larger
            if dx > dy:
                # More horizontal movement - snap to horizontal line
                canvas_y = prev_y
            else:
                # More vertical movement - snap to vertical line
                canvas_x = prev_x
        
        # Check if releasing near start point to close polygon
        start_x, start_y = self.polygon_points[0]
        distance = ((canvas_x - start_x) ** 2 + (canvas_y - start_y) ** 2) ** 0.5
        
        if distance < 20 and len(self.polygon_points) >= 3:
            # Remove preview line
            if self.polygon_preview_line:
                self.canvas.delete(self.polygon_preview_line)
                self.polygon_preview_line = None
            
            # Close polygon and fill
            self.close_polygon()
            return
        
        # Add the new point
        self.polygon_points.append((canvas_x, canvas_y))
        
        # Remove preview line
        if self.polygon_preview_line:
            self.canvas.delete(self.polygon_preview_line)
            self.polygon_preview_line = None
        
        # Draw permanent line segment
        line_id = self.canvas.create_line(
            prev_x, prev_y, canvas_x, canvas_y,
            fill="gray",
            width=2,
            dash=(5, 5),
            tags="temp_polygon"
        )
        self.polygon_lines.append(line_id)
    
    
    
    def close_polygon(self):
        """Close the polygon and create filled shape"""
        if len(self.polygon_points) < 3:
            return
        
        # Clear temporary lines
        self.canvas.delete("temp_polygon")
        
        # Convert canvas coordinates to image coordinates for storage
        img_points = []
        for x, y in self.polygon_points:
            img_x, img_y = self.canvas_to_image_coords(x, y)
            img_points.extend([img_x, img_y])
        
        # Use the random color generated when starting the polygon
        random_color = self.current_shape_color
        
        # Create filled polygon
        polygon_id = self.canvas.create_polygon(
            [coord for point in self.polygon_points for coord in point],
            fill=random_color,
            outline="",
            width=0,
            stipple=self.get_stipple_pattern()
        )
        
        # Save shape data
        shape_data = {
            "type": "polygon",
            "coordinates": img_points,
            "color": random_color,
            "stipple": self.get_stipple_pattern(),
            "canvas_id": polygon_id
        }
        
        # Add shape to list FIRST
        self.shapes.append(shape_data)
        
        # Then save state for undo (after adding shape)
        self.save_state("Create polygon")
        
        # Update the shape listbox to show the new polygon
        self.update_shape_list()
        
        # Reset polygon drawing state
        self.drawing_polygon = False
        self.polygon_points = []
        self.polygon_lines = []
        
        self.status_var.set(f"Created polygon with random color (opacity: {int(self.opacity * 100)}%)")


def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = LayoutHeatmapApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()