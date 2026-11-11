# 새벽 자동 작업 (이 Mac)

GitHub Actions 대신 이 Mac 이 돌려요. 스크립트 `run.sh <작업>`, 로그 `~/Library/Logs/likasuni-auto.log`.

| 작업 | 시간 (한국) | 하는 일 | 필요한 열쇠(키체인 `likasuni-<이름>`) |
|---|---|---|---|
| sync | 매일 03:07 | 드라이브 → 분류 → 빌드 → 블로그 요약 글 → 커밋 → Cloudflare 올리기 | BLOGGER_CLIENT_ID · BLOGGER_CLIENT_SECRET · BLOGGER_REFRESH_TOKEN · BLOGGER_BLOG_ID (없으면 블로그 글만 건너뜀) |

- 열쇠 넣기 (값은 물어볼 때 터미널에 직접 입력, 채팅에 붙여 넣지 않아요): `security add-generic-password -s likasuni-<이름> -a "$USER" -w`
- 켜기/끄기: `~/Library/LaunchAgents/com.likasuni.<작업>.plist` 를 `launchctl bootstrap gui/$(id -u) <파일>` / `launchctl bootout gui/$(id -u) <파일>`
- 지금 바로 한 번 돌리기: `launchctl kickstart gui/$(id -u)/com.likasuni.sync`
- Mac 이 잠자는 시간이면 깨어난 뒤에 돌아요. 켜 두려면 `sudo pmset repeat wakeorpoweron MTWRFSU 03:00:00`
- 저장하지 않은 수정이 있으면 안전하게 멈추고 알림을 띄워요.
