@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo Starting two Phone Agent sessions (Device1/Device2)...
echo Edit start_device1.bat and start_device2.bat to set PHONE_AGENT_DEVICE_ID.

start "PhoneAgent Device1" cmd /k "\"%~dp0start_device1.bat\""
start "PhoneAgent Device2" cmd /k "\"%~dp0start_device2.bat\""

endlocal

