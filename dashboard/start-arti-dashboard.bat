@echo off
cd /d "%~dp0server"
start "" http://127.0.0.1:4174/
"%USERPROFILE%\.arti\python\python.exe" server.py
