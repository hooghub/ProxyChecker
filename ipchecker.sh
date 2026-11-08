#!/usr/bin/env bash
set -Eeuo pipefail

REPO="https://raw.githubusercontent.com/hooghub/ProxyChecker/main"
APP_DIR="/opt/ipchecker"

echo "======================================"
echo "       HTTP Proxy Checker"
echo "======================================"

if [ "$(id -u)" -ne 0 ]; then
  echo "[错误] 请使用 root 运行"
  exit 1
fi

if [ -f /etc/alpine-release ]; then
  echo "[系统] Alpine Linux"
  apk add --no-cache bash python3 py3-requests ca-certificates curl
elif [ -f /etc/debian_version ]; then
  echo "[系统] Debian / Ubuntu"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y bash python3 python3-requests ca-certificates curl
else
  echo "[错误] 暂不支持此系统（支持 Alpine / Debian / Ubuntu）"
  exit 1
fi

mkdir -p "$APP_DIR"
echo "[下载] 正在获取检测程序..."
curl -fLsS "$REPO/IPcheck.py" -o "$APP_DIR/IPcheck.py"
test -s "$APP_DIR/IPcheck.py" || {
  echo "[错误] IPcheck.py 下载失败或文件为空"
  exit 1
}

echo
read -r -p "请输入 VPS 上代理 TXT 文件路径: " INPUT_FILE
INPUT_FILE="${INPUT_FILE/#\~/$HOME}"

if [ ! -f "$INPUT_FILE" ]; then
  echo "[错误] 找不到文件: $INPUT_FILE"
  exit 1
fi

echo
echo "[启动] 开始检测..."
python3 "$APP_DIR/IPcheck.py" "$INPUT_FILE"
