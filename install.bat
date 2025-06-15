@echo off
echo ========================================
echo Open RAGBook 依赖安装工具
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.12+
    pause
    exit /b 1
)

REM 升级pip
echo 升级pip...
python -m pip install --upgrade pip

REM 运行安装脚本
echo.
echo 开始依赖安装...
python install_requirements.py

if errorlevel 1 (
    echo.
    echo 安装过程中出现错误，请检查上面的错误信息
    pause
    exit /b 1
)

echo.
echo ========================================
echo 安装完成！
echo ========================================
pause 