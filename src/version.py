"""
Version information for Layout Heatmap Generator
"""

__version__ = "1.0.1"
__release_date__ = "2026-01-07"
__app_name__ = "Layout Heatmap Generator"
__author__ = "Nathnaree S."
__github_repo__ = "NathnareeS/Layout_Heatmap"  # Update this with your GitHub username/repo

def get_version_string():
    """Returns formatted version string"""
    return f"{__app_name__} v{__version__}"

def get_full_version_info():
    """Returns complete version information"""
    return {
        "version": __version__,
        "release_date": __release_date__,
        "app_name": __app_name__,
        "author": __author__,
        "github_repo": __github_repo__
    }
