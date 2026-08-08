@echo off
cd /d "%~dp0"
echo === OMNI Guard MVP ===
echo Abriendo http://localhost:8030 ...
start "" http://localhost:8030
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8030
pause
