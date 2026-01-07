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

### For End Users (Recommended)

**No Python installation required!** Just download and run.

1. **Download the latest release:**
   - Go to [Releases](https://github.com/YOUR_USERNAME/Layout-Heatmap/releases)
   - Download the latest `LayoutHeatmap-vX.X.X.zip` file

2. **Extract the ZIP file:**
   - Right-click → Extract All
   - Choose a location (e.g., `C:\Program Files\LayoutHeatmap`)

3. **Run the application:**
   - Double-click `LayoutHeatmap.exe`
   - That's it! 🎉

### For Developers

If you want to run from source code or contribute:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Layout-Heatmap.git
   cd Layout-Heatmap
   ```

2. **Install Python 3.7+ and dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python src/layout_combined.py
   ```
   *Or double-click `run_app.bat` on Windows*

4. **Build executable (optional):**
   ```bash
   pip install pyinstaller
   python build_exe.py
   ```

## Auto-Update System

The application automatically checks for updates once per day when you launch it.

**To manually check for updates:**
1. Open the application
2. Go to **Help** → **Check for Updates**
3. If an update is available, click **Update Now**
4. The app will download, install, and restart automatically

**No manual downloading or file replacement needed!** ✨

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