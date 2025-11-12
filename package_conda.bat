@echo off
chcp 65001 >nul 2>nul
setlocal EnableExtensions EnableDelayedExpansion

echo ================================================
echo     RouteManager 打包脚本 (Conda 版本)
echo ================================================
echo.

cd /d "%~dp0"

rem 设置变量
set "PACKAGE_NAME=RouteManager-Portable"
set "PACKAGE_DIR=dist\%PACKAGE_NAME%"
set "BUILD_DATE=%date:~0,4%%date:~5,2%%date:~8,2%"

rem 设置要使用的 Conda 环境名称
set "CONDA_ENV=p311"

rem 如果传入了参数，使用参数作为环境名
if not "%~1"=="" set "CONDA_ENV=%~1"

rem 1. 激活 Conda 环境
echo [1/7] 激活 Conda 环境: %CONDA_ENV%
call conda activate %CONDA_ENV% 2>nul
if %errorlevel% neq 0 (
    echo     ✗ 激活失败，请检查环境名称是否正确
    echo     可用的环境列表：
    conda env list
    pause
    exit /b 1
)
echo     ✓ Conda 环境已激活
echo.

rem 2. 安装/更新依赖
echo [2/7] 安装依赖包
echo     安装 PyQt6...
pip install PyQt6==6.6.1 --quiet --no-warn-script-location
echo     安装 PyInstaller...
pip install pyinstaller==6.3.0 --quiet --no-warn-script-location
echo     依赖安装完成
echo.

rem 3. 清理旧的构建文件
echo [3/7] 清理旧的构建文件
if exist "build" (
    rmdir /s /q "build" >nul 2>&1
)
if exist "dist" (
    rmdir /s /q "dist" >nul 2>&1
)
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
echo     清理完成
echo.

rem 4. 使用 PyInstaller 打包
echo [4/7] 正在使用 PyInstaller 打包
if exist "RouteManager.spec" (
    echo     使用 RouteManager.spec 配置文件
    pyinstaller --clean --noconfirm "RouteManager.spec"
) else (
    echo     使用默认配置
    pyinstaller --clean --noconfirm -F -w --name RouteManager --uac-admin src\main.py
)

if %errorlevel% neq 0 goto :error
echo     ✓ PyInstaller 打包完成
echo.

rem 5. 创建完整的应用程序包目录
echo [5/7] 创建应用程序包目录结构
if not exist "%PACKAGE_DIR%" mkdir "%PACKAGE_DIR%"

rem 创建必要的子目录
if not exist "%PACKAGE_DIR%\profiles" mkdir "%PACKAGE_DIR%\profiles"
if not exist "%PACKAGE_DIR%\snapshots" mkdir "%PACKAGE_DIR%\snapshots"
if not exist "%PACKAGE_DIR%\logs" mkdir "%PACKAGE_DIR%\logs"
if not exist "%PACKAGE_DIR%\docs" mkdir "%PACKAGE_DIR%\docs"

rem 复制可执行文件
if exist "dist\RouteManager.exe" (
    copy "dist\RouteManager.exe" "%PACKAGE_DIR%\" >nul
    echo     ✓ 复制 RouteManager.exe
) else (
    echo     ✗ 未找到 RouteManager.exe
    goto :error
)

rem 复制文档文件
if exist "README.md" (
    copy "README.md" "%PACKAGE_DIR%\" >nul
    echo     ✓ 复制 README.md
)
if exist "LICENSE" (
    copy "LICENSE" "%PACKAGE_DIR%\" >nul
    echo     ✓ 复制 LICENSE
)
if exist "CHANGELOG.md" (
    copy "CHANGELOG.md" "%PACKAGE_DIR%\" >nul
    echo     ✓ 复制 CHANGELOG.md
)

rem 复制用户指南
if exist "docs\USER_GUIDE.md" (
    copy "docs\USER_GUIDE.md" "%PACKAGE_DIR%\docs\" >nul
    echo     ✓ 复制 USER_GUIDE.md
)
if exist "docs\路由掩码使用说明.md" (
    copy "docs\路由掩码使用说明.md" "%PACKAGE_DIR%\docs\" >nul
    echo     ✓ 复制 路由掩码使用说明.md
)

rem 复制示例配置文件
if exist "profiles\home.json" (
    copy "profiles\home.json" "%PACKAGE_DIR%\profiles\home.example.json" >nul
    echo     ✓ 复制示例配置
)

rem 创建启动说明文件
echo 路由管理工具 - 使用说明 > "%PACKAGE_DIR%\使用说明.txt"
echo. >> "%PACKAGE_DIR%\使用说明.txt"
echo 1. 本程序是一个便携版应用，无需安装 >> "%PACKAGE_DIR%\使用说明.txt"
echo 2. 双击 RouteManager.exe 即可运行 >> "%PACKAGE_DIR%\使用说明.txt"
echo 3. 程序需要管理员权限来管理系统路由 >> "%PACKAGE_DIR%\使用说明.txt"
echo 4. 首次运行时会自动创建必要的配置目录 >> "%PACKAGE_DIR%\使用说明.txt"
echo. >> "%PACKAGE_DIR%\使用说明.txt"
echo 目录说明： >> "%PACKAGE_DIR%\使用说明.txt"
echo   - profiles\  : 配置文件存储目录 >> "%PACKAGE_DIR%\使用说明.txt"
echo   - snapshots\ : 快照文件存储目录 >> "%PACKAGE_DIR%\使用说明.txt"
echo   - logs\      : 日志文件存储目录 >> "%PACKAGE_DIR%\使用说明.txt"
echo   - docs\      : 使用文档目录 >> "%PACKAGE_DIR%\使用说明.txt"
echo. >> "%PACKAGE_DIR%\使用说明.txt"
echo 详细使用说明请参考 docs\USER_GUIDE.md >> "%PACKAGE_DIR%\使用说明.txt"
echo. >> "%PACKAGE_DIR%\使用说明.txt"
echo 版本信息： >> "%PACKAGE_DIR%\使用说明.txt"
echo   打包日期: %BUILD_DATE% >> "%PACKAGE_DIR%\使用说明.txt"
echo   打包环境: Conda %CONDA_ENV% >> "%PACKAGE_DIR%\使用说明.txt"

echo     ✓ 应用程序包创建完成
echo.

rem 6. 创建压缩包
echo [6/7] 创建压缩包
set "ZIP_FILE=dist\%PACKAGE_NAME%-%BUILD_DATE%.zip"

powershell -Command "Compress-Archive -Path '%PACKAGE_DIR%\*' -DestinationPath '%ZIP_FILE%' -Force" 2>nul
if exist "%ZIP_FILE%" (
    echo     压缩包创建成功
) else (
    echo     压缩包创建失败，不影响主包
)
echo.

rem 7. 验证并显示结果
echo [7/7] 验证打包结果
if exist "%PACKAGE_DIR%\RouteManager.exe" (
    echo.
    echo ================================================
    echo     打包成功！
    echo ================================================
    echo.
    echo 应用程序包位置:
    echo   %CD%\%PACKAGE_DIR%
    echo.
    if exist "%ZIP_FILE%" (
        echo 压缩包位置:
        echo   %CD%\%ZIP_FILE%
        echo.
    )
    echo 使用方法:
    echo   1. 直接运行: %PACKAGE_DIR%\RouteManager.exe
    echo   2. 复制整个文件夹到其他位置使用
    if exist "%ZIP_FILE%" (
        echo   3. 解压 ZIP 文件到任意位置使用
    )
    echo.
    echo 目录内容:
    dir /b "%PACKAGE_DIR%"
    echo.
    
    rem 获取文件大小
    for %%F in ("%PACKAGE_DIR%\RouteManager.exe") do (
        set "FILE_SIZE=%%~zF"
        set /a FILE_SIZE_MB=!FILE_SIZE! / 1024 / 1024
        echo 程序大小: !FILE_SIZE_MB! MB
    )
    echo.
    
    rem 询问是否打开文件夹
    echo.
    echo 是否打开打包目录？(Y/N，10秒后自动选择N)
    choice /c YN /n /t 10 /d N
    if !errorlevel! equ 1 (
        start explorer "%PACKAGE_DIR%"
    )
    
    goto :success
) else (
    goto :error
)

:error
echo.
echo ================================================
echo     打包失败！
echo ================================================
echo.
echo 请检查上面的错误信息
echo.
pause
exit /b 1

:success
echo 按任意键退出...
pause >nul
exit /b 0
