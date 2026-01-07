"""
Convert PNG image to ICO format for use as application icon
Requires Pillow library
"""

from PIL import Image
import sys
import os

def png_to_ico(png_path, ico_path=None):
    """
    Convert PNG to ICO format
    
    Args:
        png_path: Path to input PNG file
        ico_path: Path to output ICO file (optional, defaults to same name with .ico)
    """
    if not ico_path:
        ico_path = os.path.splitext(png_path)[0] + '.ico'
    
    try:
        # Open the PNG image
        img = Image.open(png_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create multiple sizes for the icon (Windows standard sizes)
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        # Save as ICO with multiple sizes
        img.save(ico_path, format='ICO', sizes=icon_sizes)
        
        print(f"✓ Successfully converted {png_path} to {ico_path}")
        print(f"  Icon sizes included: {', '.join([f'{w}x{h}' for w, h in icon_sizes])}")
        return ico_path
        
    except Exception as e:
        print(f"✗ Error converting image: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_icon.py <input.png> [output.ico]")
        print("\nExample:")
        print("  python convert_icon.py icon.png")
        print("  python convert_icon.py icon.png app_icon.ico")
        sys.exit(1)
    
    png_path = sys.argv[1]
    ico_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(png_path):
        print(f"Error: File '{png_path}' not found")
        sys.exit(1)
    
    result = png_to_ico(png_path, ico_path)
    
    if result:
        print(f"\nNext steps:")
        print(f"1. Update build_exe.py line 31:")
        print(f'   "--icon={result}",')
        print(f"2. Rebuild: python build_exe.py")
    else:
        sys.exit(1)
