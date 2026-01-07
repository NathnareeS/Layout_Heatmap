# How to Create a GitHub Release

This guide explains how to create releases for the Layout Heatmap Generator so users can download and auto-update.

## Prerequisites

1. **GitHub Repository**: Your code should be pushed to GitHub
2. **Built Executable**: Run `python build_exe.py` to create the executable
3. **Version Number**: Update `src/version.py` with the new version

## Step-by-Step Release Process

### 1. Update Version Number

Edit `src/version.py`:
```python
__version__ = "1.0.1"  # Increment version
__release_date__ = "2026-01-15"  # Update date
```

### 2. Update Changelog

Edit `CHANGELOG.md` and add your changes:
```markdown
## [1.0.1] - 2026-01-15

### Added
- New feature X
- Improvement Y

### Fixed
- Bug fix Z
```

### 3. Commit Changes

```bash
git add src/version.py CHANGELOG.md
git commit -m "Release v1.0.1"
git push
```

### 4. Build the Executable

```bash
# Install PyInstaller if not already installed
pip install pyinstaller

# Build the executable
python build_exe.py
```

This creates the executable in `dist/` folder.

### 5. Create ZIP Package

1. Navigate to `dist/LayoutHeatmap/` (or `dist/` if single file)
2. Select all files:
   - `LayoutHeatmap.exe`
   - `update_installer.py`
   - `data/` folder
   - `examples/` folder
   - `README.md`
   - `run.bat`
3. Right-click → Send to → Compressed (zipped) folder
4. Name it: `LayoutHeatmap-v1.0.1.zip`

### 6. Create Git Tag

```bash
# Create annotated tag
git tag -a v1.0.1 -m "Release version 1.0.1"

# Push tag to GitHub
git push origin v1.0.1
```

### 7. Create GitHub Release

1. **Go to your GitHub repository**
   - Navigate to: `https://github.com/YOUR_USERNAME/Layout-Heatmap`

2. **Click on "Releases"** (right sidebar)

3. **Click "Create a new release"** or "Draft a new release"

4. **Fill in the release form:**
   - **Tag**: Select `v1.0.1` (the tag you just created)
   - **Release title**: `Layout Heatmap Generator v1.0.1`
   - **Description**: Copy from CHANGELOG.md or write:
     ```markdown
     ## What's New in v1.0.1
     
     ### Added
     - New feature X
     - Improvement Y
     
     ### Fixed
     - Bug fix Z
     
     ## Installation
     
     1. Download `LayoutHeatmap-v1.0.1.zip` below
     2. Extract the ZIP file
     3. Run `LayoutHeatmap.exe`
     
     ## Auto-Update
     
     Existing users can update via **Help → Check for Updates** in the app.
     ```

5. **Attach the ZIP file:**
   - Drag and drop `LayoutHeatmap-v1.0.1.zip` into the "Attach binaries" area
   - OR click "Attach binaries by dropping them here or selecting them"

6. **Publish release:**
   - Click "Publish release" button

## Verification

After publishing:

1. **Test the download link:**
   - Go to the Releases page
   - Download the ZIP file
   - Extract and test the executable

2. **Test auto-update:**
   - Keep your local version at the old version (e.g., 1.0.0)
   - Run the app
   - Go to Help → Check for Updates
   - Verify it detects v1.0.1 and offers to update

## Important Notes

### Version Numbering (Semantic Versioning)

- **Major** (X.0.0): Breaking changes, major new features
- **Minor** (1.X.0): New features, backwards compatible
- **Patch** (1.0.X): Bug fixes, small improvements

Examples:
- `1.0.0` → `1.0.1`: Bug fix
- `1.0.1` → `1.1.0`: New feature added
- `1.1.0` → `2.0.0`: Major redesign

### GitHub Repository URL

**IMPORTANT**: Update the GitHub repository URL in `src/version.py`:

```python
__github_repo__ = "YOUR_USERNAME/Layout-Heatmap"
```

Replace `YOUR_USERNAME` with your actual GitHub username!

### Auto-Update Requirements

For auto-update to work:
1. Release must have a tag starting with `v` (e.g., `v1.0.1`)
2. ZIP file must be attached to the release
3. `__github_repo__` in `version.py` must be correct

## Quick Reference Commands

```bash
# Update version in src/version.py first, then:

# 1. Commit changes
git add .
git commit -m "Release vX.X.X"
git push

# 2. Create and push tag
git tag -a vX.X.X -m "Release version X.X.X"
git push origin vX.X.X

# 3. Build executable
python build_exe.py

# 4. Create ZIP from dist/ folder

# 5. Create GitHub release and attach ZIP
```

## Troubleshooting

### Auto-update not detecting new version

- Check that `__github_repo__` in `version.py` matches your GitHub repo
- Verify the release tag starts with `v` (e.g., `v1.0.1`)
- Ensure the release is published (not draft)
- Check internet connection

### Executable not running

- Make sure all files from `dist/` are included in the ZIP
- Test on a clean system without Python installed
- Check Windows Defender/antivirus isn't blocking it

### Build errors

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Install PyInstaller: `pip install pyinstaller`
- Try cleaning build folders: delete `build/` and `dist/` directories
