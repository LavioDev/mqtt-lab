#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Docker Desktop may expose only the Windows CLI when WSL Integration is off.
if ! command -v docker >/dev/null 2>&1; then
  docker_exe="$(command -v docker.exe || true)"
  if [[ -z "$docker_exe" && -x "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe" ]]; then
    docker_exe="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
  fi
  if [[ -n "$docker_exe" ]]; then
    mkdir -p "$ROOT/.runtime/bin"
    cat > "$ROOT/.runtime/bin/docker" <<'EOF'
#!/usr/bin/env bash
exec docker.exe "$@"
EOF
    chmod 700 "$ROOT/.runtime/bin/docker"
    PATH="$ROOT/.runtime/bin:$PATH"
    export PATH
  fi
fi

group_mode=false
if [[ "${1:-}" == "--docker-group" ]]; then
  group_mode=true
  shift
fi

if ! command -v docker >/dev/null 2>&1; then
  printf 'Docker CLI chưa có trong Debian. Mở Docker Desktop và bật WSL Integration cho Debian.\n' >&2
  exit 1
fi

if ! docker version >/dev/null 2>&1; then
  if [[ "$group_mode" == false ]] && command -v sg >/dev/null 2>&1 \
      && getent group docker | cut -d: -f4 | tr ',' '\n' | grep -Fxq "$(id -un)"; then
    printf 'Dùng nhóm docker cho phiên terminal hiện tại...\n'
    printf -v quoted_root '%q' "$ROOT"
    printf -v quoted_args '%q ' "$@"
    exec sg docker -c "cd $quoted_root && exec bash $quoted_root/run.sh --docker-group $quoted_args"
  fi
  printf 'Không kết nối được Docker Engine. Mở Docker Desktop và bật Linux containers.\n' >&2
  exit 1
fi

if [[ "$group_mode" == true ]]; then
  printf 'Docker Engine sẵn sàng qua nhóm docker.\n'
fi

if [[ "${1:-}" == "dashboard" ]]; then
  action="${2:-start}"
  firmware=false
  if [[ "$action" == "--firmware" ]]; then
    firmware=true
    action=start
  elif [[ "${3:-}" == "--firmware" ]]; then
    firmware=true
  fi
  if [[ "$action" != "start" && "$action" != "stop" ]]; then
    printf 'Cách dùng: ./run.sh dashboard [stop] [--firmware]\n' >&2
    exit 2
  fi

  compose=(docker compose --profile dashboard -f compose.yaml)
  if [[ "$firmware" == true ]]; then
    if [[ ! -f .env.firmware ]]; then
      printf 'Thiếu .env.firmware; điền cấu hình ESP32 trước.\n' >&2
      exit 1
    fi
    compose+=(--env-file .env --env-file .env.firmware -f compose.firmware.yaml)
  fi

  if [[ "$action" == "stop" ]]; then
    "${compose[@]}" stop dashboard_proxy dashboard
    printf 'Đã dừng dashboard. Broker vẫn chạy.\n'
    exit 0
  fi

  python3 scripts/init_lab.py
  "${compose[@]}" config --quiet
  if docker ps -aq --filter label=com.docker.compose.project=mqtt-sentinel | grep -q .; then
    printf 'Dọn stack MQTT Sentinel cũ để nhường cổng dashboard...\n'
    docker compose -p mqtt-sentinel --profile dashboard -f compose.yaml down --remove-orphans
  fi
  "${compose[@]}" up -d --build --force-recreate broker dashboard dashboard_proxy
  stop_hint="./run.sh dashboard stop"
  if [[ "$firmware" == true ]]; then stop_hint+=" --firmware"; fi
  dashboard_port="${DASHBOARD_PORT:-8081}"
  printf '\nDashboard: http://localhost:%s\nDừng dashboard bằng: %s\n' "$dashboard_port" "$stop_hint"
  exit 0
fi

if [[ -n "${1:-}" && "$1" != "baseline" ]]; then
  printf 'Cách dùng: ./run.sh [baseline] | ./run.sh dashboard [stop] [--firmware]\n' >&2
  exit 2
fi

if [[ ! -f .env.firmware ]]; then
  printf 'Thiếu .env.firmware; điền cấu hình ESP32 trước khi chạy baseline.\n' >&2
  exit 1
fi

python3 scripts/init_lab.py
python3 scripts/verify_lab.py

run_id="E00-$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
python3 scripts/run_baseline.py --run-id "$run_id"
python3 scripts/analyze_pcap.py "$run_id"

printf '\nHoàn tất. Artifact: data/raw/%s\n' "$run_id"
