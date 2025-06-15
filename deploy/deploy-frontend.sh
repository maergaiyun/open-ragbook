#!/bin/bash

# Vue3前端项目nginx部署脚本
# 作者: AI Assistant
# 日期: $(date +%Y-%m-%d)

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_ROOT="/root/project/open-ragbook"
FRONTEND_DIR="$PROJECT_ROOT/open_ragbook_ui"
DEPLOY_DIR="$PROJECT_ROOT/deploy"
NGINX_CONFIG="$DEPLOY_DIR/nginx-frontend.conf"

echo -e "${BLUE}=== Vue3前端项目nginx部署脚本 ===${NC}"

# 检查必要的目录和文件
check_prerequisites() {
    echo -e "${YELLOW}检查前置条件...${NC}"

    if [ ! -d "$FRONTEND_DIR" ]; then
        echo -e "${RED}错误: 前端项目目录不存在: $FRONTEND_DIR${NC}"
        exit 1
    fi

    if [ ! -f "$FRONTEND_DIR/package.json" ]; then
        echo -e "${RED}错误: package.json文件不存在${NC}"
        exit 1
    fi

    if ! command -v node &> /dev/null; then
        echo -e "${RED}错误: Node.js未安装${NC}"
        exit 1
    fi

    if ! command -v npm &> /dev/null; then
        echo -e "${RED}错误: npm未安装${NC}"
        exit 1
    fi

    if ! command -v nginx &> /dev/null; then
        echo -e "${RED}错误: nginx未安装${NC}"
        echo -e "${YELLOW}请先安装nginx: sudo apt-get install nginx${NC}"
        exit 1
    fi

    echo -e "${GREEN}前置条件检查通过${NC}"
}

# 安装依赖
install_dependencies() {
    echo -e "${YELLOW}安装前端依赖...${NC}"
    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        echo -e "${BLUE}首次安装依赖...${NC}"
        npm install
    else
        echo -e "${BLUE}更新依赖...${NC}"
        npm ci
    fi

    echo -e "${GREEN}依赖安装完成${NC}"
}

# 构建前端项目
build_frontend() {
    echo -e "${YELLOW}构建前端项目...${NC}"
    cd "$FRONTEND_DIR"

    # 清理旧的构建文件
    if [ -d "dist" ]; then
        rm -rf dist
        echo -e "${BLUE}已清理旧的构建文件${NC}"
    fi

    # 执行构建
    npm run build

    if [ ! -d "dist" ]; then
        echo -e "${RED}错误: 构建失败，dist目录不存在${NC}"
        exit 1
    fi

    echo -e "${GREEN}前端项目构建完成${NC}"
}

# 配置nginx
configure_nginx() {
    echo -e "${YELLOW}配置nginx...${NC}"

    # 检查nginx配置文件语法
    if ! nginx -t -c "$NGINX_CONFIG" 2>/dev/null; then
        echo -e "${RED}错误: nginx配置文件语法错误${NC}"
        nginx -t -c "$NGINX_CONFIG"
        exit 1
    fi

    echo -e "${GREEN}nginx配置文件语法检查通过${NC}"
}

# 启动nginx服务
start_nginx() {
    echo -e "${YELLOW}启动nginx服务...${NC}"

    # 检查8080端口是否被占用
    if netstat -tuln | grep -q ":8080 "; then
        echo -e "${YELLOW}端口8080已被占用，尝试停止现有nginx进程...${NC}"

        # 更强力的停止方式
        pkill -f nginx || true
        sleep 2

        # 如果还有进程，强制杀死
        if pgrep nginx > /dev/null; then
            echo -e "${YELLOW}强制停止nginx进程...${NC}"
            pkill -9 nginx || true
            sleep 2
        fi

        # 再次检查端口
        if netstat -tuln | grep -q ":8080 "; then
            echo -e "${RED}错误: 无法释放8080端口${NC}"
            echo -e "${YELLOW}占用端口的进程:${NC}"
            lsof -i :8080
            exit 1
        fi
    fi

    # 启动nginx
    nginx -c "$NGINX_CONFIG"

    # 检查nginx是否启动成功
    sleep 2
    if ! pgrep nginx > /dev/null; then
        echo -e "${RED}错误: nginx启动失败${NC}"
        echo -e "${YELLOW}查看错误日志:${NC}"
        tail -10 /var/log/nginx/error.log
        exit 1
    fi

    echo -e "${GREEN}nginx服务启动成功${NC}"
}

# 验证部署
verify_deployment() {
    echo -e "${YELLOW}验证部署...${NC}"

    # 检查前端页面
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/ | grep -q "200"; then
        echo -e "${GREEN}✓ 前端页面访问正常${NC}"
    else
        echo -e "${RED}✗ 前端页面访问失败${NC}"
    fi

    # 检查健康检查接口
    if curl -s http://127.0.0.1:8080/health | grep -q "healthy"; then
        echo -e "${GREEN}✓ 健康检查接口正常${NC}"
    else
        echo -e "${RED}✗ 健康检查接口异常${NC}"
    fi

    echo -e "${GREEN}部署验证完成${NC}"
}

# 显示部署信息
show_deployment_info() {
    echo -e "${BLUE}=== 部署完成 ===${NC}"
    echo -e "${GREEN}前端访问地址: http://127.0.0.1:8080/${NC}"
    echo -e "${GREEN}健康检查: http://127.0.0.1:8080/health${NC}"
    echo -e "${YELLOW}nginx配置文件: $NGINX_CONFIG${NC}"
    echo -e "${YELLOW}前端构建目录: $FRONTEND_DIR/dist${NC}"
    echo ""
    echo -e "${BLUE}常用命令:${NC}"
    echo -e "${YELLOW}  重启nginx: nginx -s reload -c $NGINX_CONFIG${NC}"
    echo -e "${YELLOW}  停止nginx: pkill -f 'nginx.*8080'${NC}"
    echo -e "${YELLOW}  查看nginx进程: ps aux | grep nginx${NC}"
    echo -e "${YELLOW}  查看nginx日志: tail -f /var/log/nginx/access.log${NC}"
}

# 主函数
main() {
    check_prerequisites
    install_dependencies
    build_frontend
    configure_nginx
    start_nginx
    verify_deployment
    show_deployment_info
}

# 执行主函数
main "$@"