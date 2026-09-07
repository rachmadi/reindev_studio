@echo off
echo Membuka ReinDev Studio di Browser dan Windows Desktop...
start http://localhost:8085
start "" "%~dp0frontend\build\windows\x64\runner\Release\reindev_studio.exe"