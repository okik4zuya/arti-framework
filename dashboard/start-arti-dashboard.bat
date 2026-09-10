@echo off
rem Windows, visible console -- manual/debug entry point. Launches the same
rem native-window app.py the Desktop shortcut uses (see app.py), just with a
rem console attached instead of pythonw.exe's windowless run.
cd /d "%~dp0"
"%USERPROFILE%\.arti\python\python.exe" app.py
