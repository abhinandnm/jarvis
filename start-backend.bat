@echo off
title J.A.R.V.I.S. Backend API
echo Starting J.A.R.V.I.S. backend API...
cd %~dp0
call venv\Scripts\activate.bat
python main.py
pause
