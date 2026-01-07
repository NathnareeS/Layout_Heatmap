# Changelog

All notable changes to Layout Heatmap Generator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-07

### Added
- Initial release of Layout Heatmap Generator
- **Heatmap Generator**: Create interactive store layout heatmaps
  - Draw rectangles, circles, and polygons on PDF layouts
  - Color-code areas based on sales performance
  - Save and load layouts as JSON
  - Export heatmaps as PNG/JPEG images
- **Text Labeler**: Add custom text labels to layouts
  - Assign variables to labels with conditional coloring
  - Import data from Excel/CSV files
  - Auto-enable sales/area metrics
  - Leader lines for better label positioning
- **Project Management**: SQLite database for organizing projects
  - Create, open, rename, and delete projects
  - Auto-save functionality
  - Project selection screen
- **Auto-Update System**: Automatic update checking and installation
  - Checks GitHub releases for new versions
  - One-click update installation
  - Automatic application restart after update
- **Standalone Executable**: No Python installation required
  - PyInstaller build system
  - All dependencies bundled
  - Simple double-click to run

### Technical Features
- PDF processing with PyMuPDF
- Excel/CSV data import with pandas
- Conditional coloring based on variables
- Shape mapping and synchronization
- Modern UI with Tkinter

---

## How to Update

### For Users
1. Open the application
2. Go to **Help** → **Check for Updates**
3. If an update is available, click **Update Now**
4. The app will download, install, and restart automatically

### For Developers
1. Update version number in `src/version.py`
2. Add changes to this CHANGELOG.md
3. Commit changes: `git commit -am "Release vX.X.X"`
4. Create tag: `git tag vX.X.X`
5. Push with tags: `git push && git push --tags`
6. Create GitHub release with the tag
7. Attach ZIP file of the built executable
