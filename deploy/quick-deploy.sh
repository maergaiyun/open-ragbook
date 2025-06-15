#!/bin/bash

# 快速部署脚本 - 仅重新构建和重启nginx
# 适用于代码更新后的快速部署

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="/root/project/open-ragbook"
FRONTEND_DIR="$PROJECT_ROOT/open_ragbook_ui"
NGINX_CONFIG="$PROJECT_ROOT/deploy/nginx-frontend.conf"

echo -e "${BLUE}=== 快速重新部署前端 ===${NC}"

# 进入前端目录
cd "$FRONTEND_DIR"

# 重新构建
echo -e "${YELLOW}重新构建前端...${NC}"
npm run build

# 重启nginx
echo -e "${YELLOW}重启nginx...${NC}"
pkill -f nginx || true
sleep 2

# 如果还有进程，强制杀死
if pgrep nginx > /dev/null; then
    pkill -9 nginx || true
    sleep 1
fi

nginx -c "$NGINX_CONFIG"

echo -e "${GREEN}快速部署完成！${NC}"
echo -e "${GREEN}访问地址: http://127.0.0.1:8080/${NC}"