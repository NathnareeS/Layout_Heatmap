@echo off
echo Starting Store Layout Heatmap Generator...
echo.

REM Change to the application directory
cd /d "%~dp0"

REM Test imports first
echo Testing package imports...
python test_imports.py
echo.

echo Using PyMuPDF for PDF processing - No external dependencies needed!
echo.

REM Launch the application
echo Launching application...
python src\layout_combined.py

pause