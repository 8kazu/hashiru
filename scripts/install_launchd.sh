#!/usr/bin/env bash
# launchdエージェントのインストール/アンインストール
# usage: ./scripts/install_launchd.sh [uninstall]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_DIR="$HOME/Library/LaunchAgents"
UID_NUM="$(id -u)"
LABELS=(com.hashiru.morning com.hashiru.evening)

if [[ "${1:-}" == "uninstall" ]]; then
  for label in "${LABELS[@]}"; do
    launchctl bootout "gui/${UID_NUM}/${label}" 2>/dev/null || true
    rm -f "${AGENTS_DIR}/${label}.plist"
    echo "removed: ${label}"
  done
  exit 0
fi

mkdir -p "$AGENTS_DIR"
for label in "${LABELS[@]}"; do
  cp "${ROOT}/launchd/${label}.plist" "${AGENTS_DIR}/"
  # 再インストール時のために一度外してから登録
  launchctl bootout "gui/${UID_NUM}/${label}" 2>/dev/null || true
  launchctl bootstrap "gui/${UID_NUM}" "${AGENTS_DIR}/${label}.plist"
  echo "installed: ${label}"
done

echo ""
echo "登録状況の確認: launchctl list | grep hashiru"
echo "手動テスト実行:  launchctl kickstart gui/${UID_NUM}/com.hashiru.morning"
echo "ログ:           tail -f ${ROOT}/reports/launchd.log"
