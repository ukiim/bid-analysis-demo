#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  비드스타 — DB 백업 cron 자동 등록 스크립트
#
#  대상 환경:
#    A. Synology DSM 7.x  → DSM 작업 스케줄러 안내 (수동, 1회)
#    B. 일반 Linux       → 사용자 crontab 자동 등록
#
#  사용법:
#    chmod +x scripts/install_backup_cron.sh
#    ./scripts/install_backup_cron.sh                # 자동 감지
#    ./scripts/install_backup_cron.sh --linux        # Linux crontab 강제
#    ./scripts/install_backup_cron.sh --synology     # Synology 안내만
#    ./scripts/install_backup_cron.sh --uninstall    # crontab 항목 제거
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

# 스크립트 위치 절대 경로
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_SCRIPT="$SCRIPT_DIR/backup_db.py"
BACKUP_DIR="${BACKUP_DIR:-$BACKEND_DIR/backups}"
LOG_FILE="${BACKUP_LOG:-$BACKEND_DIR/data/backup.log}"
RETAIN="${BACKUP_RETAIN:-30}"

# 색상
G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; D='\033[0;36m'; X='\033[0m'

usage() {
  sed -n '2,15p' "$0"
  exit 0
}

mode="auto"
case "${1:-}" in
  --linux) mode="linux" ;;
  --synology) mode="synology" ;;
  --uninstall) mode="uninstall" ;;
  --help|-h) usage ;;
esac

[[ -f "$BACKUP_SCRIPT" ]] || { echo -e "${R}[ERR]${X} backup_db.py 누락: $BACKUP_SCRIPT"; exit 2; }

# 자동 감지
if [[ "$mode" == "auto" ]]; then
  if [[ -d /volume1 || -f /usr/syno/bin/synouser ]]; then
    mode="synology"
  else
    mode="linux"
  fi
fi

CRON_LINE="0 3 * * * /usr/bin/env python3 $BACKUP_SCRIPT --output $BACKUP_DIR --retain $RETAIN --verify >> $LOG_FILE 2>&1"
CRON_TAG="# bidstar-backup-cron"

# 데이터 정리 (주간 일요일 04:00) — DATA_RETAIN_YEARS / SYNC_LOG_RETAIN_DAYS 환경변수 적용
PURGE_SCRIPT="$SCRIPT_DIR/purge_old_data.py"
PURGE_LOG="${PURGE_LOG:-$BACKEND_DIR/data/purge.log}"
PURGE_LINE="0 4 * * 0 /usr/bin/env python3 $PURGE_SCRIPT >> $PURGE_LOG 2>&1"
PURGE_TAG="# bidstar-purge-cron"

install_linux() {
  echo -e "${D}== Linux crontab 자동 등록 ==${X}"
  echo "  백업 명령: $CRON_LINE"
  echo "  정리 명령: $PURGE_LINE"
  # 기존 항목 제거 후 추가
  ( crontab -l 2>/dev/null | grep -v "$CRON_TAG" | grep -v "$PURGE_TAG" ; \
    echo "$CRON_TAG"; echo "$CRON_LINE"; \
    echo "$PURGE_TAG"; echo "$PURGE_LINE" ) | crontab -
  echo -e "${G}[OK]${X} crontab 등록 완료 (백업 매일 03:00 + 정리 일요일 04:00). 확인:"
  echo "    crontab -l | grep bidstar-"
  echo
  echo "백업/로그 폴더 준비:"
  mkdir -p "$BACKUP_DIR" "$(dirname "$LOG_FILE")" "$(dirname "$PURGE_LOG")"
  echo -e "${G}[OK]${X} $BACKUP_DIR / 로그 디렉토리 생성"
}

uninstall_linux() {
  echo -e "${D}== Linux crontab 제거 ==${X}"
  if crontab -l 2>/dev/null | grep -qE "$CRON_TAG|$PURGE_TAG|bidstar-"; then
    crontab -l 2>/dev/null | grep -v "$CRON_TAG" | grep -v "$PURGE_TAG" | grep -v "bidstar-" | crontab -
    echo -e "${G}[OK]${X} 백업/정리 cron 제거 완료"
  else
    echo -e "${Y}[SKIP]${X} 등록된 항목 없음"
  fi
}

show_synology_guide() {
  printf "%b" "
${D}== Synology DSM 7.x — 작업 스케줄러 안내 ==${X}"
  cat <<EOF

DSM에서 cron은 직접 편집하지 않고 GUI로 등록합니다.

  1. DSM 제어판 → 작업 스케줄러 → 생성 → 예약된 작업 → 사용자 정의 스크립트
  2. 일반 탭:
     - 작업 이름:  비드스타 DB 백업
     - 사용자:    root (또는 docker 그룹 사용자)
  3. 일정 탭:
     - 매일 03:00 실행
  4. 작업 설정 탭 → 사용자 정의 스크립트:

  ─────────────────────── 복사해서 붙여넣기 ───────────────────────
  docker exec bid-backend python3 /app/scripts/backup_db.py \\
      --output /app/backups --retain $RETAIN --verify \\
      >> /app/data/backup.log 2>&1
  ─────────────────────────────────────────────────────────────────

  5. 저장 → 항목 우클릭 → 실행 으로 즉시 1회 테스트

  ※ Hyper Backup으로 /volume1/docker/bid-insight/backups 을
     외부 USB·NAS·클라우드에 주기 동기화하면 더 안전합니다.

EOF
}

case "$mode" in
  linux)     install_linux ;;
  uninstall) uninstall_linux ;;
  synology)  show_synology_guide ;;
esac
