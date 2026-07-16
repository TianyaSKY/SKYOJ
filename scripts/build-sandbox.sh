#!/usr/bin/env bash
# 构建 SKYOJ 评测与测例生成沙箱镜像：
#   - skyoj-runner    判题运行环境（GCC / Java / Python）
#   - skyoj-generator 测试数据生成环境
#
# 用法：
#   ./scripts/build-sandbox.sh
#   ./scripts/build-sandbox.sh --no-cache
#   ./scripts/build-sandbox.sh runner
#   ./scripts/build-sandbox.sh generator

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

NO_CACHE=0
TARGET="all"

for arg in "$@"; do
  case "${arg}" in
    --no-cache)
      NO_CACHE=1
      ;;
    runner|generator|all)
      TARGET="${arg}"
      ;;
    -h|--help)
      cat <<'EOF'
构建 SKYOJ 沙箱镜像

用法:
  ./scripts/build-sandbox.sh [all|runner|generator] [--no-cache]

镜像:
  skyoj-runner     判题沙箱（docker/runner）
  skyoj-generator  测例生成沙箱（docker/generator）
EOF
      exit 0
      ;;
    *)
      echo "[错误] 未知参数: ${arg}" >&2
      echo "使用 --help 查看帮助" >&2
      exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "[错误] 未找到 docker 命令，请先安装并启动 Docker。" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "[错误] Docker 守护进程不可用，请确认 Docker 已启动。" >&2
  exit 1
fi

BUILD_FLAGS=()
if [[ "${NO_CACHE}" -eq 1 ]]; then
  BUILD_FLAGS+=(--no-cache)
fi

build_image() {
  local name="$1"
  local context="$2"

  if [[ ! -f "${context}/Dockerfile" ]]; then
    echo "[错误] 找不到 Dockerfile: ${context}/Dockerfile" >&2
    exit 1
  fi

  echo "========================================"
  echo " 构建镜像: ${name}"
  echo " 上下文:   ${context}"
  echo "========================================"
  docker build "${BUILD_FLAGS[@]}" -t "${name}" "${context}"
  echo "[完成] ${name}"
  echo
}

cd "${ROOT_DIR}"

echo "项目根目录: ${ROOT_DIR}"
echo "构建目标:   ${TARGET}"
echo

case "${TARGET}" in
  all)
    build_image "skyoj-runner" "${ROOT_DIR}/docker/runner"
    build_image "skyoj-generator" "${ROOT_DIR}/docker/generator"
    ;;
  runner)
    build_image "skyoj-runner" "${ROOT_DIR}/docker/runner"
    ;;
  generator)
    build_image "skyoj-generator" "${ROOT_DIR}/docker/generator"
    ;;
esac

echo "当前相关镜像："
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" \
  | awk 'NR==1 || $1=="skyoj-runner" || $1=="skyoj-generator"'

echo
echo "沙箱构建完成。可继续执行: docker compose up -d --build"
