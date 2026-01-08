# 📚 Layout Heatmap - Complete Feature Guide

> **Welcome!** This guide will help you understand all the powerful features in Layout Heatmap. Whether you're creating store layouts, analyzing floor plans, or adding professional labels, we've got you covered! 🎨

---

## 🗂️ Project Management

Organize all your work into projects - each project keeps your layouts, labels, and settings together in one place.

| Feature | What It Does | How to Use It |
|---------|-------------|---------------|
| **➕ New Project** | Start fresh with a new project | Click "New Project" → Enter a name → Start working! |
| **📂 Open Project** | Continue working on saved projects | Select a project from the list → Click "Open" |
| **💾 Save Project** | Save all your work automatically | Click "Save" button or press **Ctrl+S** |
| **✏️ Rename Project** | Change your project's name | Select project → Click "Rename" → Enter new name |
| **🗑️ Delete Project** | Remove a project permanently | Select project → Click "Delete" → Confirm ⚠️ |
| **🔙 Close Project** | Return to project selection | Click "Close" → Choose to save or not |

> 💡 **Pro Tip:** Save your project regularly with **Ctrl+S** to never lose your work!

---

## 🎨 Heatmap Generator

Create beautiful visual heatmaps by drawing shapes on your floor plan.

### 📄 Getting Started

**Step 1: Load Your Floor Plan**
- Click **"Load PDF"** in the File menu
- Select your floor plan PDF file
- The layout appears on your canvas ✨

### 🖌️ Drawing Tools

Draw different shapes to highlight areas on your layout:

| Tool | Icon | How to Draw | Best For |
|------|------|-------------|----------|
| **Rectangle** | ▭ | Click and drag from corner to corner | Rooms, sections, rectangular areas |
| **Circle/Oval** | ⭕ | Click and drag to create oval shapes | Round tables, circular zones |
| **Polygon** | ⬡ | Click each corner point, double-click to finish | Irregular areas, custom shapes |

> 💡 **Quick Tip:** Use the **Polygon Tool** for L-shaped rooms or irregular spaces!

### 🎯 Working with Shapes

**Managing Your Shapes:**

```
📋 Shape List (Left Panel)
├─ 🏪 Store Entrance
├─ 🛒 Shopping Area 1
├─ 🛒 Shopping Area 2
└─ 💰 Checkout Counter
```

| Action | How to Do It |
|--------|-------------|
| **Select a Shape** | Click the shape name in the list |
| **Rename a Shape** | Double-click the shape name or use "Rename" button |
| **Delete a Shape** | Select shape → Click "Delete" |
| **Clear Everything** | Click "Clear All" to start over |

### 🎨 Coloring Your Shapes

Make your heatmap meaningful with colors!

**How to Assign Colors:**
1. Select a shape from the list
2. Choose a color from the color picker
3. Adjust opacity (0-100%) for transparency
4. The shape updates instantly! 🌈

**Popular Color Schemes:**
- 🔴 **Red** = High sales / Hot zones
- 🟠 **Orange** = Good performance
- 🟡 **Yellow** = Average areas
- 🟢 **Green** = Low activity / Cool zones
- 🔵 **Blue** = Very low / Special zones

### 💾 Save & Export

| Feature | What You Get | When to Use |
|---------|-------------|-------------|
| **Save Layout** | JSON file with all shapes | To continue editing later |
| **Load Layout** | Restore saved shapes | To reopen previous work |
| **Export Image** | PNG/JPEG picture | For presentations, reports, printing |

---

## 📝 Text Labeler

Add professional text labels to your shapes with full formatting control.

### 🎯 Quick Start Guide

**Adding Labels in 3 Easy Steps:**

1. **Select a Shape** 📍
   - Click any shape from the list
   - The text editor opens automatically

2. **Type Your Text** ✍️
   - Enter text in the text box
   - Click "+ Add Text Line" for multiple lines

3. **Apply Changes** ✅
   - Click "Apply All Changes" button
   - Your label appears on the canvas!

### ✨ Text Formatting Options

Make your labels look professional with these formatting tools:

| Format Option | Range | What It Does |
|--------------|-------|-------------|
| **📏 Font Size** | 8 - 72 pt | Make text bigger or smaller |
| **🎨 Text Color** | Any color | Change the text color |
| **🖍️ Background Color** | Any color | Add colored background behind text |
| **📊 Variable** | Your variables | Enable automatic color-coding |

**Example Label:**
```
┌─────────────────────┐
│ Electronics Section │  ← Line 1: Large, bold
│ Sales: $45,000      │  ← Line 2: With variable
│ Area: 250 m²        │  ← Line 3: With unit
└─────────────────────┘
```

### 🎯 Positioning Labels

**Moving Labels Around:**
- **Click and Drag** the label to move it anywhere
- Labels automatically create **leader lines** when moved outside shapes
- Leader lines point from label to shape 📍

**Leader Line Styles:**

| Style | Appearance | Best For |
|-------|-----------|----------|
| **Solid** | ━━━━━ | Professional, clean look |
| **Dashed** | ╌╌╌╌╌ | Temporary or secondary info |
| **Dotted** | ┄┄┄┄┄ | Subtle connections |

**Customizing Leader Lines:**
1. Select a labeled shape
2. Choose style, width (1-10), and color
3. Click "Apply Changes" ✅

### ⚙️ Default Settings

Save time by setting defaults for all new labels:

```
Default Settings Panel
├─ Text Size: 30 pt
├─ Text Color: Black ⬛
├─ Background: White ⬜
└─ Line Width: 5 px
```

> 💡 **Time Saver:** Set your defaults once, and all new labels will use these settings!

### 🗑️ Managing Labels

| Action | Button | Result |
|--------|--------|--------|
| Delete One Label | "Delete Label" | Removes current label only |
| Clear All Labels | "Clear All" | Removes ALL labels at once ⚠️ |

---

## 🎨 Conditional Coloring

**Automatically color shapes based on data values!** Perfect for sales analysis, performance tracking, and data visualization.

### 🌟 How It Works

**The Magic Formula:**
```
Your Data → Variable Rules → Automatic Colors! 🎨
```

**Example:**
- Sales > $50,000 → 🟢 Green (Excellent!)
- Sales > $30,000 → 🟡 Yellow (Good)
- Sales < $30,000 → 🔴 Red (Needs attention)

### 📊 Variable Manager

**Creating a Variable:**

**Step-by-Step:**
1. Click **"📊 Manage Variables"**
2. Click **"Add Variable"**
3. Name it (e.g., "Monthly Sales")
4. Add color rules (see below)
5. Click **"Save"** ✅

**Adding Color Rules:**

| Operator | Meaning | Example | Color |
|----------|---------|---------|-------|
| **>** | Greater than | Sales > 50000 | 🟢 Green |
| **>=** | Greater or equal | Sales >= 30000 | 🟡 Yellow |
| **<** | Less than | Sales < 20000 | 🔴 Red |
| **<=** | Less or equal | Sales <= 10000 | 🔵 Blue |
| **==** | Exactly equal | Sales == 0 | ⚫ Gray |
| **!=** | Not equal | Sales != 0 | 🟠 Orange |

**Real-World Example:**

```
Variable: "Store Performance"

Rules:
✅ If sales > $100,000  → Dark Green  (Outstanding!)
✅ If sales > $75,000   → Light Green (Excellent)
✅ If sales > $50,000   → Yellow      (Good)
✅ If sales > $25,000   → Orange      (Fair)
✅ If sales < $25,000   → Red         (Needs Help)
```

### 🎯 Using Variables

**Assigning Variables to Labels:**

1. Select a shape
2. In the text editor, find the **Variable dropdown**
3. Choose your variable (e.g., "Monthly Sales")
4. Type a number value
5. Click **"Apply All Changes"**
6. Watch the magic! The shape changes color automatically! ✨

### 💾 Save & Share Variables

| Feature | What It Does | File Type |
|---------|-------------|-----------|
| **📤 Export Conditions** | Save all variables and rules | JSON file |
| **📥 Import Conditions** | Load variables from file | JSON file |

> 💡 **Pro Tip:** Create a master variable file and reuse it across all your projects!

### 🎨 Variable Properties

**Advanced Settings:**

| Property | What It Does | Example |
|----------|-------------|---------|
| **Text Color** | Default text color for this variable | Black for sales data |
| **Background Color** | Default background color | Light yellow for highlights |
| **Font Size** | Default text size | 24pt for important numbers |
| **Auto Sales/Area** | Auto-enable area calculations | ✅ For "Square Footage" variable |
| **Default Unit** | Automatic unit suffix | m², ft², $, etc. |

---

## 📊 Excel/CSV Import & Mapping

**Import data from spreadsheets and automatically create labels!** No more manual typing! 🎉

### 📥 Importing Data

**Step-by-Step Guide:**

1. **Prepare Your Spreadsheet**
   ```
   Excel/CSV File:
   ┌──────────┬───────────┬─────────┐
   │ Store    │ Sales     │ Area    │
   ├──────────┼───────────┼─────────┤
   │ Section A│ $45,000   │ 250 m²  │
   │ Section B│ $62,000   │ 300 m²  │
   │ Section C│ $38,000   │ 180 m²  │
   └──────────┴───────────┴─────────┘
   ```

2. **Import the File**
   - Click **"📊 Import Excel/CSV"**
   - Select your file
   - Choose which columns to use

3. **Map Shapes to Data**
   - Match each shape to a row in your data
   - The mapping dialog shows you all options
   - Click **"Apply"** ✅

**What Gets Imported:**
- ✅ Text values
- ✅ Numbers (for conditional coloring)
- ✅ Multiple columns as separate text lines
- ✅ Automatic formatting

### 🔄 Remapping Data

**Need to change the mapping?**

1. Click **"🔄 Remap"**
2. See current mappings for all shapes
3. Reassign shapes to different data rows
4. Click **"Apply"** to rebuild labels

> 💡 **Use Case:** Perfect when you reorganize your spreadsheet or add new data!

---

## 🔍 View Controls

Navigate and zoom like a pro!

### 🔎 Zoom Features

| Control | How to Use | Shortcut |
|---------|-----------|----------|
| **Zoom In** | Click "Zoom In" button | Mouse wheel up ⬆️ |
| **Zoom Out** | Click "Zoom Out" button | Mouse wheel down ⬇️ |
| **Fit to Window** | Click "Fit to Window" | Auto-adjusts to screen |
| **Zoom Display** | Shows current zoom % | Example: "Zoom: 150%" |

### 🖱️ Navigation

**Moving Around:**
- **Right-Click + Drag** = Pan around the canvas
- **Scrollbars** = Navigate horizontally/vertically
- **Mouse Wheel** = Zoom in/out smoothly

### ✨ Special Feature: Zoom-Independent Text

**What does this mean?**
- Text labels stay the **same size** no matter how much you zoom
- Always readable, never pixelated
- Professional quality at any zoom level! 📏

**Example:**
```
Zoom: 50%  → Text: 12pt ✅
Zoom: 100% → Text: 12pt ✅
Zoom: 200% → Text: 12pt ✅
```

---

## 💾 File Operations

Save, load, and export your work in multiple formats.

### 📁 File Types Explained

| File Type | Extension | What It Contains | When to Use |
|-----------|-----------|------------------|-------------|
| **Project** | `.db` (database) | Everything! Shapes, labels, variables | Auto-saved, don't worry about it |
| **Labels** | `.json` | All labels and formatting | Share labels with others |
| **Shapes** | `.json` | Shape coordinates and colors | Share layouts with others |
| **Image** | `.png` | Final visual output | Presentations, reports, printing |

### 💾 Save Options

**Save Labels:**
- Saves all text labels, formatting, and settings
- Can be loaded into any project
- Great for templates!

**Export Image:**
- High-quality PNG output
- Includes everything visible:
  - ✅ PDF background
  - ✅ Colored shapes
  - ✅ Text labels with formatting
  - ✅ Leader lines
  - ✅ Units (m², $, etc.)
- Perfect for presentations! 📊

### 📂 Load Options

**Load Labels:**
- Import previously saved labels
- Automatically handles missing shapes
- Warns you about any issues

> ⚠️ **Important:** Make sure your shapes match before loading labels!

---

## 🔄 Auto-Update System

**Stay up-to-date automatically!** No manual downloads needed! 🚀

### ✨ How It Works

**Automatic Updates:**
```
App Starts → Checks for Updates (once/day) → Notifies You → One-Click Install!
```

**What You See:**
1. **Notification**: "New version available! 🎉"
2. **Release Notes**: See what's new
3. **Update Button**: Click "Update Now"
4. **Automatic Install**: Downloads, installs, restarts
5. **Done!** You're on the latest version! ✅

### 🔍 Manual Update Check

**Want to check now?**
1. Go to **Help** menu
2. Click **"🔄 Check for Updates"**
3. See if updates are available
4. Install with one click!

### 🎁 Benefits

- ✅ Always have the latest features
- ✅ Automatic bug fixes
- ✅ Security updates
- ✅ No technical knowledge needed
- ✅ No manual file downloads

---

## 📐 Sales/Area Mode

**Special mode for displaying measurements and sales data with units!**

### 🎯 What It Does

Automatically adds units to your numbers:
- **250** → **250 m²**
- **1500** → **1500 ft²**
- **45000** → **$45,000**

### ⚙️ Setting Up

**Method 1: Variable Auto-Enable**
1. Create a variable (e.g., "Floor Area")
2. Check **"Auto-enable Sales/Area"** ✅
3. Choose default unit (m², ft², etc.)
4. Assign variable to text line
5. Units appear automatically! 🎉

**Method 2: Manual Enable**
1. Add a text line
2. Assign a variable with auto-enable
3. Type your number
4. Unit appears automatically!

### 📏 Available Units

| Category | Units Available |
|----------|----------------|
| **Area** | m², ft², km², sq ft, sq m |
| **Volume** | m³, ft³, liters, gallons |
| **Currency** | $, €, £, ¥ |
| **Custom** | Any text you want! |

> 💡 **Smart Feature:** No duplicate units! If you type "250 m²", it won't add another "m²"!

---

## ⌨️ Keyboard Shortcuts

Work faster with these handy shortcuts!

| Shortcut | Action | Where It Works |
|----------|--------|----------------|
| **Ctrl + S** | Save project | Anywhere in the app |
| **Mouse Wheel** | Zoom in/out | On the canvas |
| **Right-Click + Drag** | Pan canvas | On the canvas |
| **Double-Click** | Rename shape/project | In lists |
| **Delete Key** | Delete selected item | When item selected |

---

## 🎨 Modern User Interface

**Beautiful, intuitive, and easy to use!**

### ✨ Design Features

- **🎨 Color-Coded Buttons**
  - 🟢 Green = Save, Create, Apply
  - 🔵 Blue = Open, Load, Import
  - 🟠 Orange = Edit, Rename
  - 🔴 Red = Delete, Clear, Remove

- **✨ Hover Effects**
  - Buttons light up when you hover
  - Visual feedback for all actions
  - Professional, modern look

- **📱 Responsive Layout**
  - Scrollable panels for long lists
  - Resizable windows
  - Adapts to your screen

- **📑 Tabbed Interface**
  - 🎨 Heatmap Generator tab
  - 📝 Text Labeler tab
  - Easy switching between tools

### 💬 Status Bar

**Always know what's happening:**
- ✅ Success messages in green
- ⚠️ Warnings in yellow
- ❌ Errors in red
- ℹ️ Helpful tips and instructions

---

## 🆘 Quick Tips & Tricks

### 💡 Beginner Tips

1. **Start Simple**
   - Create a project
   - Load a PDF
   - Draw a few shapes
   - Add basic labels
   - Export and admire your work! 🎉

2. **Use Templates**
   - Create one perfect variable setup
   - Export conditions
   - Reuse in all projects

3. **Save Often**
   - Press **Ctrl+S** frequently
   - Projects auto-save, but better safe than sorry!

### 🚀 Advanced Tips

1. **Conditional Coloring Pro**
   - Use multiple rules for detailed analysis
   - Most specific rule wins
   - Test with sample data first

2. **Excel Integration**
   - Keep your Excel file organized
   - Use clear column headers
   - Update Excel and re-import to refresh

3. **Professional Exports**
   - Use high zoom for detailed areas
   - Fit to window for overview shots
   - Export at different zooms for different purposes

---

## 📞 Need Help?

**Remember:**
- 💡 Hover over buttons for tooltips
- 📊 Status bar shows helpful messages
- ⚠️ Warning dialogs explain issues
- 🔄 Updates bring new features and fixes

**Happy Mapping! 🎨📊✨**
