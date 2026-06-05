@echo off
title Katalog Delova
cd /d "%~dp0"
echo Pokrecem Katalog Delova na http://localhost:5050/
echo Sacekaj 10-30 sekundi za CIAK login...
echo.
echo NE ZATVARAJ ovaj prozor dok koristis aplikaciju!
echo.
timeout /t 2 /nobreak >nul
start "" "http://localhost:5050/"
python app.py
echo.
echo Server je ugasen.
pause
