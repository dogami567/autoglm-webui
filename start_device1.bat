@echo off
REM Dual-device helper: copy and set your own device id.
REM Use list_devices.bat to find device ids.

set "PHONE_AGENT_DEVICE_ID=YOUR_DEVICE_ID_1"
call "%~dp0start.bat" %*

