#!/bin/zsh
# 새벽 자동 작업 (이 Mac 에서 실행). GitHub Actions 를 대신해요.
# 쓰는 법: _tools/auto/run.sh sync|backup|coupang|booknew [--no-deploy]
#   sync    드라이브 → 분류 → 빌드 → 블로그 요약 글 → 커밋 → 올리기   (매일 새벽 3:07)
#   backup  댓글·요청 데이터(Supabase) 암호화 백업 → 커밋                  (일요일 새벽 4:17)
#   booknew 고등 영어 신간 후보 모으기 → 커밋                             (월요일 새벽 4:37)
#   coupang 부교재 쿠팡 링크 채우기 → 빌드 → 커밋 → 올리기                (월요일 새벽 5:07)
# 열쇠(Secrets)는 맥 키체인에 'likasuni-<이름>' 으로 넣어 두고 여기서 꺼내 써요 (_tools/auto/README.md).
set -u
JOB=${1:-}; NODEPLOY=${2:-}
ROOT=$(cd "$(dirname "$0")/../.." && pwd); cd "$ROOT" || exit 1
PY=${LIKASUNI_PY:-$HOME/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12}
LOG=$HOME/Library/Logs/likasuni-auto.log
say() { print -r -- "$(date '+%F %T') [$JOB] $*" | tee -a "$LOG"; }
fail() { say "실패: $*"; osascript -e "display notification \"$*\" with title \"리카수니 자동 작업 실패 ($JOB)\"" 2>/dev/null; exit 1; }
sec() { security find-generic-password -s "likasuni-$1" -w 2>/dev/null; }   # 키체인에서 열쇠 꺼내기 (없으면 빈 값)
[[ -x $PY ]] || fail "파이썬 3.12 를 못 찾았어요 ($PY)"

# 작업 시작 전: 작업 중이던 고친 파일이 있으면 섞이지 않게 멈춰요
git diff --quiet && git diff --cached --quiet || fail "저장하지 않은 수정이 있어서 멈췄어요 (git status 확인)"
git pull --no-rebase -q 2>&1 | tail -1 | tee -a "$LOG" >/dev/null   # 다른 곳에서 올라온 변경 받기 (실패해도 계속)
SKIPDEPLOY=0
BEFORE=$(mktemp); git ls-files --others --exclude-standard | sort > "$BEFORE"

case $JOB in
  sync)
    cd _tools
    $PY sync_drive.py            || fail "드라이브 동기화"
    $PY classify.py | tee classify.log >/dev/null || fail "분류"
    $PY build.py | tail -1       || fail "빌드"
    BID=$(sec BLOGGER_CLIENT_ID)
    if [[ -n $BID ]]; then
      BLOGGER_CLIENT_ID=$BID BLOGGER_CLIENT_SECRET=$(sec BLOGGER_CLIENT_SECRET) \
      BLOGGER_REFRESH_TOKEN=$(sec BLOGGER_REFRESH_TOKEN) BLOGGER_BLOG_ID=$(sec BLOGGER_BLOG_ID) \
        $PY blogger_post.py || say "블로그 요약 글 실패 (계속)"
    else say "블로그 열쇠가 키체인에 없어서 블로그 요약 글은 건너뜀"; fi
    cd ..
    MSG="드라이브 기출 자동 반영 ($(date -u +%F))" ;;
  backup)
    BK=$(sec BACKUP_KEY); [[ -n $BK ]] || fail "백업 열쇠(BACKUP_KEY)가 키체인에 없어요"
    BACKUP_KEY=$BK $PY _tools/auto/backup.py || fail "백업"
    MSG="댓글·요청 데이터 주간 백업 ($(date -u +%F))"; SKIPDEPLOY=1 ;;
  booknew)
    cd _tools
    KAKAO_REST_API_KEY=$(sec KAKAO_REST_API_KEY) NAVER_CLIENT_ID=$(sec NAVER_CLIENT_ID) NAVER_CLIENT_SECRET=$(sec NAVER_CLIENT_SECRET) \
      $PY book_new.py || fail "신간 모으기"
    cd ..
    MSG="교재 신간 후보 모으기"; SKIPDEPLOY=1 ;;
  coupang)
    AK=$(sec COUPANG_ACCESS_KEY); [[ -n $AK ]] || fail "쿠팡 열쇠(COUPANG_ACCESS_KEY)가 키체인에 없어요"
    COUPANG_ACCESS_KEY=$AK COUPANG_SECRET_KEY=$(sec COUPANG_SECRET_KEY) DRY_RUN=0 $PY _tools/coupang_links.py || fail "쿠팡 링크"
    if git diff --quiet -- _tools/coupang.json '_tools/news/*/coupang.json'; then say "링크 바뀐 것 없음"; else
      $PY _tools/build.py | tail -1 || fail "빌드"
    fi
    MSG="쿠팡 부교재 링크 갱신" ;;
  *) fail "알 수 없는 작업: $JOB (sync|backup|booknew|coupang)" ;;
esac

# 이번 작업이 만든 것만 저장: 고친 파일 + 새로 생긴 파일 (작업 전부터 있던 낯선 파일은 건드리지 않아요)
git add -u
git ls-files --others --exclude-standard | sort | comm -13 "$BEFORE" - | while IFS= read -r f; do git add -- "$f"; done
rm -f "$BEFORE"
if git diff --cached --quiet; then say "바뀐 것 없음"; else
  git commit -q -m "$MSG" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" || fail "커밋"
  say "커밋: $MSG"
  git push -q 2>&1 | tail -1 | tee -a "$LOG" >/dev/null   # GitHub 는 백업용 (실패해도 계속)
  [[ $NODEPLOY == --no-deploy || $SKIPDEPLOY == 1 ]] || { _tools/deploy.sh >> "$LOG" 2>&1 && say "Cloudflare 에 올림" || fail "Cloudflare 올리기"; }
fi
say "끝"
