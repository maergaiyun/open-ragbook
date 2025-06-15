#!/bin/bash

echo "========================================"
echo "Open RAGBook 依赖安装工具"
echo "========================================"
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "错误: 未找到Python，请先安装Python 3.12+"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# 显示Python版本
echo "使用Python: $($PYTHON_CMD --version)"

# 升级pip
echo "升级pip..."
$PYTHON_CMD -m pip install --upgrade pip

# 运行安装脚本
echo
echo "开始依赖安装..."
$PYTHON_CMD install_requirements.py

if [ $? -ne 0 ]; then
    echo
    echo "安装过程中出现错误，请检查上面的错误信息"
    exit 1
fi

echo
echo "========================================"
echo "安装完成！"
echo "========================================" 