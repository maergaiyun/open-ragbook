#!/bin/bash

# 停止前端nginx服务脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}停止前端nginx服务...${NC}"

# 停止nginx进程
if pgrep nginx > /dev/null; then
    echo -e "${YELLOW}停止nginx进程...${NC}"
    pkill -f nginx || true
    sleep 2

    # 如果还有进程，强制杀死
    if pgrep nginx > /dev/null; then
        echo -e "${YELLOW}强制停止nginx进程...${NC}"
        pkill -9 nginx || true
        sleep 1
    fi

    echo -e "${GREEN}nginx服务已停止${NC}"
else
    echo -e "${YELLOW}nginx服务未运行${NC}"
fi

# 检查端口是否释放
sleep 1
if netstat -tuln | grep -q ":8080 "; then
    echo -e "${RED}警告: 端口8080仍被占用${NC}"
    echo -e "${YELLOW}占用端口的进程:${NC}"
    netstat -tuln | grep ":8080"
else
    echo -e "${GREEN}端口8080已释放${NC}"
fi