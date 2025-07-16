@echo off

rem Load environment variable assignments from `.env`, and set them in the caller's context
for /f "usebackq tokens=*" %%A in (".env") do (
    set "%%A"
)

where draw.io >nul 2>&1
if %errorlevel%==0 goto found
if exist "%ProgramFiles%\draw.io\draw.io.exe" set PATH=%PATH%;%ProgramFiles%\draw.io
:found
