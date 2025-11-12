@echo off
chcp 65001 >nul 2>nul
echo ================================================
echo     RouteManager 打包结果测试
echo ================================================
echo.

cd /d "%~dp0"

set "PKG_DIR=dist\RouteManager-Portable"

rem 检查打包目录是否存在
if not exist "%PKG_DIR%" (
    echo ✗ 错误: 找不到打包目录 %PKG_DIR%
    echo.
    echo 请先运行 package.bat 进行打包
    echo.
    pause
    exit /b 1
)

echo [1/4] 检查主程序...
if exist "%PKG_DIR%\RouteManager.exe" (
    echo     ✓ RouteManager.exe 存在
) else (
    echo     ✗ RouteManager.exe 不存在
    goto :error
)
echo.

echo [2/4] 检查目录结构...
set "MISSING_DIRS="
if not exist "%PKG_DIR%\profiles" set "MISSING_DIRS=!MISSING_DIRS! profiles"
if not exist "%PKG_DIR%\snapshots" set "MISSING_DIRS=!MISSING_DIRS! snapshots"
if not exist "%PKG_DIR%\logs" set "MISSING_DIRS=!MISSING_DIRS! logs"

if "%MISSING_DIRS%"=="" (
    echo     ✓ 所有必需目录都存在
    echo       - profiles\
    echo       - snapshots\
    echo       - logs\
) else (
    echo     ⚠ 缺少目录: %MISSING_DIRS%
)
echo.

echo [3/4] 检查文档文件...
set "FILE_COUNT=0"
if exist "%PKG_DIR%\README.md" (
    echo     ✓ README.md
    set /a FILE_COUNT+=1
)
if exist "%PKG_DIR%\LICENSE" (
    echo     ✓ LICENSE
    set /a FILE_COUNT+=1
)
if exist "%PKG_DIR%\使用说明.txt" (
    echo     ✓ 使用说明.txt
    set /a FILE_COUNT+=1
)
if exist "%PKG_DIR%\CHANGELOG.md" (
    echo     ✓ CHANGELOG.md
    set /a FILE_COUNT+=1
)
if %FILE_COUNT% equ 0 (
    echo     ⚠ 未找到文档文件
)
echo.

echo [4/4] 获取文件信息...
for %%F in ("%PKG_DIR%\RouteManager.exe") do (
    echo     文件名: %%~nxF
    echo     大小: %%~zF 字节
    echo     修改时间: %%~tF
)
echo.

echo ================================================
echo     测试完成
echo ================================================
echo.
echo 打包目录内容列表:
echo.
dir /b "%PKG_DIR%"
echo.
echo 如需运行程序，请执行:
echo   cd %PKG_DIR%
echo   RouteManager.exe
echo.
echo 或直接打开目录:
echo   explorer %PKG_DIR%
echo.

choice /c YN /n /m "是否打开打包目录？(Y/N) "
if %errorlevel% equ 1 (
    explorer "%PKG_DIR%"
)

echo.
pause
exit /b 0

:error
echo.
echo ================================================
echo     测试失败
echo ================================================
echo.
pause
exit /b 1

