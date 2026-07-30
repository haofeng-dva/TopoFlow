@echo off
cd /d "%~dp0.."
if exist "dist\TopoFlow\TopoFlow.exe" (start "TopoFlow" "dist\TopoFlow\TopoFlow.exe") else if exist ".venv\Scripts\python.exe" (start "TopoFlow" ".venv\Scripts\python.exe" "topoflow.py") else (echo TopoFlow runtime not found. & pause)

