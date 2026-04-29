#!/bin/bash
# ODMS 部署辅助脚本
# 解决 docker-compose v1.29.2 与 Docker 29.x 的 ContainerConfig 兼容性问题
# 用法: ./deploy.sh [backend|frontend|all]

set -e

cd "$(dirname "$0")"

deploy_backend() {
    echo "=== 更新后端服务 ==="
    docker stop odms-backend odms-celery-worker odms-celery-beat 2>/dev/null || true
    docker rm odms-backend odms-celery-worker odms-celery-beat 2>/dev/null || true
    docker-compose up -d backend celery-worker celery-beat
    echo "后端服务已更新"
}

deploy_frontend() {
    echo "=== 重新构建前端 ==="
    docker stop odms-frontend 2>/dev/null || true
    docker rm odms-frontend 2>/dev/null || true
    docker-compose build frontend
    docker-compose up -d frontend
    echo "前端已重新构建并启动"
}

deploy_all() {
    echo "=== 重新部署全部服务 ==="
    docker stop odms-backend odms-celery-worker odms-celery-beat odms-frontend 2>/dev/null || true
    docker rm odms-backend odms-celery-worker odms-celery-beat odms-frontend 2>/dev/null || true
    docker-compose up -d
    echo "全部服务已重新部署"
}

case "${1:-backend}" in
    backend)  deploy_backend ;;
    frontend) deploy_frontend ;;
    all)      deploy_all ;;
    *)
        echo "用法: $0 {backend|frontend|all}"
        exit 1
        ;;
esac
