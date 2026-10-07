@echo off
rem Dedicated Veyr realm (no window, no art). Settings: config\server.cfg. Stop with Ctrl+C.
rem The database (SQLite) lives at %APPDATA%\Godotpp_userdata\Veyr - A Morrowind-style Walkealmeyr.db
cd /d "%~dp0"
set GODOT=..\Godot_v4.7.1-stable_win64_console.exe
if not "%~1"=="" set GODOT=%~1
"%GODOT%" --headless --path . res://server/server.tscn
