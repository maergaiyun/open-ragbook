# 使用 Nginx 的 Alpine 版本作为基础镜像
FROM nginx:alpine

# 复制自定义的 Nginx 配置文件到容器中
COPY nginx.conf /etc/nginx/nginx.conf

# 将 Vue 3 编译后的前端文件（dist 目录）复制到 Nginx 网站根目录
COPY dist/ /usr/share/nginx/html/

RUN chmod -R 755 /usr/share/nginx/html

# 暴露 80 端口供外部访问
EXPOSE 80

# 启动 Nginx 服务，容器启动后默认运行 Nginx
CMD ["nginx", "-g", "daemon off;"]

