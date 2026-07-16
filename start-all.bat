@echo off
title J.A.R.V.I.S. Launcher
echo Initializing J.A.R.V.I.S. Assistant systems...
cd %~dp0
start cmd /k start-backend.bat
start cmd /k start-frontend.bat
echo Launch processes dispatched. Jarvis is online, Sir.
exit
