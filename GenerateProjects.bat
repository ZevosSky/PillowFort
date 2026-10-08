@echo off
setlocal

pushd "%~dp0"

if not exist "Vendor\premake5\premake5.exe" (
    echo PillowFort: missing Vendor\premake5\premake5.exe
    popd
    exit /b 1
)

"Vendor\premake5\premake5.exe" vs2022
set "pillowfort_exit_code=%ERRORLEVEL%"

popd
exit /b %pillowfort_exit_code%
