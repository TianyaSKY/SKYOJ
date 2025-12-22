# 第一阶段：构建阶段
FROM node:20-slim AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 第二阶段：生产阶段
FROM nginx:stable-alpine AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
# 暴露 80 端口
EXPOSE 80
# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]