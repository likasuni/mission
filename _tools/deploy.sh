#!/bin/zsh
# 지금 저장소(main 의 마지막 커밋) 내용을 Cloudflare Pages(likasuni-data)에 바로 올려요.
# 커밋된 파일만 올리므로 작업 중인 파일은 섞이지 않아요. 쓰는 법: _tools/deploy.sh
set -e
cd "$(dirname "$0")/.."
D=$(mktemp -d)
git archive HEAD | tar -x -C "$D"
npx --yes wrangler@4.160.0 pages deploy "$D" --project-name likasuni-data --branch main \
  --commit-message "$(git log -1 --format=%s | cut -c1-100)" --commit-dirty=true
rm -rf "$D"
