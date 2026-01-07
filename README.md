# Store Layout Heatmap Generator

A Python application for creating interactive store layout heatmaps based on sales criteria. This tool allows you to load PDF store layouts and overlay colored shapes to represent different sales performance areas.

## Features

### Step 1: PDF File Browser ✅
- **Browse PDF File**: Click to select any PDF file from your computer
- **File Display**: Shows the selected file name and status
- **Process Button**: Converts and displays the PDF on the canvas

### Step 2: Interactive Drawing Tools ✅
The application provides several drawing tools that you can drag freely on the PDF:

- **Rectangle Tool**: Draw rectangular areas
- **Circle Tool**: Draw circular/oval areas  
- **Triangle Tool**: Draw triangular sections
- **Line Tool**: Draw linear boundaries

### Step 3: Sales Performance Color Mapping ✅
Each shape can be assigned a sales performance level with corresponding colors:

- **Excellent Sales** (Red): High-performing areas
- **Good Sales** (Orange): Above-average performance
- **Average Sales** (Yellow): Standard performance  
- **Poor Sales** (Light Green): Below-average performance
- **Very Poor Sales** (Blue): Lowest performance areas

### Step 4: Save and Export Functions ✅
- **Save Layout**: Save your layout as JSON for future editing
- **Load Layout**: Reload previously saved layouts
- **Export Image**: Export the final heatmap as PNG/JPEG
- **Clear All**: Remove all drawn shapes

## Installation

1. Make sure you have Python 3.7+ installed

2. Install required packages:
```bash
pip install -r requirements.txt
```

**That's it!** 🎉 

PyMuPDF is a self-contained library that doesn't require any external dependencies like poppler. No admin rights needed!

3. **Verify Installation:**
   ```bash
   python test_imports.py
   ```

## Quick Start

1. **Launch the Application**:
   ```bash
   python layout_heatmap.py
   ```
   *Or double-click `run_app.bat` on Windows*

2. **Create Your Heatmap**:
   - Browse and select your PDF store layout
   - Click "Process PDF" 
   - Select drawing tool and performance level
   - Drag to create colored areas on your layout
   - Save or export your heatmap

## Application Interface

The interface is divided into three main sections:

### Control Panel (Left Side)
- **File Operations**: Browse and process PDF files
- **Drawing Tools**: Select shape tools for drawing
- **Sales Performance**: Choose performance levels with color coding
- **Actions**: Save, load, clear, and export functions

### Canvas Area (Right Side)
- **PDF Display**: Shows the loaded PDF document
- **Interactive Drawing**: Click and drag to create shapes
- **Scrollable View**: Navigate large PDF documents

### Status Bar (Bottom)
- **Real-time Updates**: Shows current status and coordinates
- **User Guidance**: Provides helpful instructions

## File Formats Supported

- **Input**: PDF files (store layouts, floor plans)
- **Save**: JSON files (editable layout data)
- **Export**: PNG, JPEG images (final heatmap)

## Technical Features

- **PDF Processing**: Converts PDF pages to images for overlay
- **Real-time Drawing**: Interactive shape creation with mouse
- **Color Coding**: Automatic color assignment based on performance
- **Data Persistence**: Save and reload layouts for editing
- **High Quality Export**: Export publication-ready images

This application provides a complete solution for creating store layout heatmaps, allowing retail managers to visualize sales performance across different areas of their stores.