#!/bin/bash
# ODMS 部署辅助脚本
# 解决 docker-compose v1.29.2 与 Docker 29.x 的 ContainerConfig 兼容性问题
# 用法: ./deploy.sh [backend|frontend|all]
#
# 说明:
#   Docker Compose v1.29.2 独立版与 Docker Engine 29.x 存在兼容性 bug,
#   rebuild 已有容器时会报 KeyError: 'ContainerConfig'。
#   本脚本通过先 stop+rm 再 up 的方式绕过该问题。

set -euo pipefail

cd "$(dirname "$0")"

# ── 预检 ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

preflight_check() {
    if ! command -v docker &>/dev/null; then
        log_error "docker 未安装或不在 PATH 中"
        exit 1
    fi
    if ! command -v docker-compose &>/dev/null; then
        log_error "docker-compose 未安装或不在 PATH 中"
        exit 1
    fi
    if ! docker info &>/dev/null; then
        log_error "Docker daemon 未运行或当前用户没有权限"
        exit 1
    fi
}

health_wait() {
    local container="$1"
    local max_wait="${2:-60}"
    local elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        local status
        status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "missing")
        case "$status" in
            healthy)    log_info "$container 健康检查通过"; return 0 ;;
            starting)   ;;
            "")         ;;  # 无健康检查，视为就绪
            missing)    log_warn "$container 容器不存在，跳过健康检查"; return 0 ;;
            unhealthy)  ;;
        esac
        sleep 2
        elapsed=$((elapsed + 2))
    done
    log_warn "$container 在 ${max_wait}s 内未变为 healthy, 继续..."
}

stop_and_remove() {
    local containers=("$@")
    for c in "${containers[@]}"; do
        docker stop "$c" 2>/dev/null || true
        docker rm "$c" 2>/dev/null || true
    done
}

# ── 部署函数 ──────────────────────────────────────────────────────
deploy_backend() {
    log_info "停止并移除后端容器..."
    stop_and_remove odms-backend odms-celery-worker odms-celery-beat

    log_info "启动后端服务..."
    if ! docker-compose up -d backend celery-worker celery-beat; then
        log_error "docker-compose up 失败, 后端部署未完成"
        exit 1
    fi

    health_wait odms-backend 90
    log_info "后端服务已更新"
}

deploy_frontend() {
    log_info "停止并移除前端容器..."
    stop_and_remove odms-frontend

    log_info "构建前端镜像..."
    if ! docker-compose build frontend; then
        log_error "前端镜像构建失败"
        exit 1
    fi

    log_info "启动前端服务..."
    if ! docker-compose up -d frontend; then
        log_error "docker-compose up 失败, 前端部署未完成"
        exit 1
    fi

    log_info "前端已重新构建并启动"
}

deploy_all() {
    log_info "停止并移除应用容器..."
    stop_and_remove odms-backend odms-celery-worker odms-celery-beat odms-frontend

    log_info "启动全部服务..."
    if ! docker-compose up -d; then
        log_error "docker-compose up 失败, 部署未完成"
        exit 1
    fi

    health_wait odms-db 60
    health_wait odms-redis 30
    health_wait odms-minio 45
    health_wait odms-backend 90
    log_info "全部服务已重新部署"
}

# ── 主入口 ────────────────────────────────────────────────────────
preflight_check

case "${1:-backend}" in
    backend)  deploy_backend ;;
    frontend) deploy_frontend ;;
    all)      deploy_all ;;
    *)
        echo "用法: $0 {backend|frontend|all}"
        exit 1
        ;;
esac
