@echo off
echo Installing required Python packages...
pip install PySide6 keyring neuprint-python pandas

echo.
echo Starting the Fly Brain App...
python fly_brain_app.py

echo.
pause