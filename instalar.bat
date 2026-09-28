@echo off
cd /d %~dp0
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
if not exist uploads mkdir uploads
if not exist music mkdir music
echo.
echo VIBRA instalado. Ahora ejecuta: python app.py
pause
