# 리카수니 작업 규칙

원장님(리카수니, 이매동 코코스학원)과 작업할 때 먼저 읽는 파일이에요. 답은 한국어로, 쉽고 짧은 존댓말로 해요.

## 사이트 두 곳: "자료실"과 "블로그"

| 원장님이 말하면 | 주소 | 무엇 | 올리는 방법 |
|---|---|---|---|
| **자료실** | data.likasuni.com | 이 저장소 (GitHub Pages, `CNAME`) | 저장소에 쓰고 main 에 합치면 바로 반영 |
| **블로그** | www.likasuni.com | 구글 블로그(Blogger), 이름 '리카수니 영어' 예정 | `_tools/blogger_post.py` 자동 발행 통로, 또는 붙여 넣을 HTML 전달 |
| **둘 다** | 두 곳 | 자료실엔 상세 글, 블로그엔 구성이 다른 요약 글 | 같은 내용을 통째로 복사하지 않음 (검색 중복 방지) |

"자료실"/"블로그" 말이 없으면 어느 쪽인지 먼저 물어봐요. 자료실 이름 '리카수니 자료실'은 바꾸지 않아요 (모든 페이지 제목·검색에 쓰임).

## 자료실 구조

- `_tools/build.py` 가 사이트 전체를 만들어요. `suneung/`, `moe/` 는 빌드할 때마다 지우고 새로 만들어요. 만든 결과(HTML)도 함께 커밋해요.
- 공통 스타일 `style.css` 는 모든 페이지에 들어가서, 스타일을 바꾸면 페이지 파일이 수천 개 함께 바뀌어요. 정상이에요.
- `.github/workflows/drive-sync.yml`: 매일 새벽 3시 7분(한국 시간)에 드라이브 동기화 → 분류 → 빌드 → 블로그 요약 글 발행 → 커밋.
- 기출 PDF 목록은 `_tools/catalog.json` (드라이브 파일 id 포함). 이 환경에선 드라이브 직접 다운로드가 막혀 있어서, 문제지·정답표는 Google Drive 커넥터(`read_file_content`)로 읽어요. 정답은 정답표 **홀수형** 기준.
- **데이터 백업**: 댓글·회원·분석노트 요청(Supabase)은 Actions `db-backup` 이 매주 일요일 새벽 4시 17분에 암호화해서 `_backup/supabase.json.enc` 에 저장 (저장소가 공개라 평문 금지). 열쇠는 Secret `BACKUP_KEY` = Supabase `private_config.backup_key`. 푸는 법은 `_backup/README.md`.
- 이 환경에선 data.likasuni.com 접속이 막혀 있어요. 확인은 로컬 빌드 + playwright 화면 캡처(`/opt/pw-browsers/chromium`)로 해요.

## 문항별 해설 (자료실 '수업자료')

- 파일: `_tools/posts/<시험>-eng-<번호>.json`. 시험 키는 `sn-2022`(수능, 학년도 기준) 또는 `moe-<학년>-<연도>-<월>`.
- 형식은 기존 파일(예: `sn-2022-eng-32.json`)과 똑같이: type, points, answer, topic, date, keywords, lead, flow, evidence, choices(5개), grammar, vocab, summary, writing, tip, faq.
- **장문 세트(41~42, 43~45)는 한 페이지**: `sn-2022-eng-41-42.json` 에 `n`, `n2`, 문항별 `qs`(n·type·points·answer·evidence·choices). 주소는 `…/41-42/`.
- **예약 공개**: `date` 가 공개일(한국 시간). 미래 날짜면 그날 새벽 빌드 때 공개돼요. 기본은 **하루 5개**, 장문 세트는 1개로 셈. 수정하면 `updated` 에 날짜를 넣어요 (사이트맵 lastmod).
- **원장님 한마디**: `note` 칸. 수업에서 짚을 포인트가 있는 문항에만 원장님 말투로. **확인할 수 없는 통계·학생 사례는 쓰지 않아요.**
- 회차는 18~45번을 끝까지 채우는 게 목표. 최근 수능 → 고3 6·9월 모평 → 고1·고2 학평 순서를 추천했어요.

## 블로그 자동 발행

- `_tools/blogger_post.py`: 그날 공개된 자료실 해설을 회차별로 묶어 **심플 요약 글**(번호·유형·정답, 핵심 한 줄, 원장님/풀이 포인트, 전체 해설 버튼, 내일 예고)을 Blogger 에 발행. 발행 기록은 `_tools/blogger_posted.json`.
- 블로그용 HTML 박스에는 애드센스가 뚫고 나가지 않게 `box-sizing:border-box; overflow:hidden; width:100%; max-width:100%` 를 모든 박스(중첩 포함)에 넣어요.
- 연결 정보는 GitHub Secrets `BLOGGER_CLIENT_ID`, `BLOGGER_CLIENT_SECRET`, `BLOGGER_REFRESH_TOKEN`, `BLOGGER_BLOG_ID` (Google Cloud 프로젝트 likasuni-mission, OAuth 클라이언트 '블로그 자동 발행', 2026-10-18 연결).
- 연결 테스트: Actions → `blog-test` → 날짜 입력 → 블로그에 **임시저장(비공개)** 으로 올라감. 확인 뒤 임시저장 글은 지워 달라고 안내.
- 자유 형식 글(업데이트 소식, 내신 분석 등): `_tools/blog_queue/<파일>.html` 에 글을 쓰고 main 에 합친 뒤 Actions → `blog-post` (file·title·labels·draft) 로 발행. `_tools/blogger_publish_file.py` 가 올리고 `blogger_posted.json` 에 `file:<파일>` 로 기록해서 같은 글은 두 번 안 올라가요.

## 진행 방식

- 작업 브랜치에서 커밋 → PR → main 에 합치기까지 해요 (원장님이 이 흐름에 동의함). 바꾼 뒤엔 로컬 빌드와 화면 캡처로 확인하고 결과 이미지를 보여 드려요.
- 아침 6시 48분 알림(예약 작업 '자료 요청·댓글 아침 알림'): 오늘 공개된 해설, 없는 자료 요청, 새 댓글을 휴대폰으로 알려요. 공개 확인은 GitHub 의 사이트 파일로 해요.
- **비밀값(보안 비밀번호, refresh token, 비밀번호)은 채팅에 붙여 넣거나 캡처하지 않게** 매번 안내해요. 클라이언트 ID·블로그 ID 는 비밀이 아니에요.
- 학교 내신 시험지는 저작권이 학교에 있어요. 사진을 통째로 올리지 말고 문항을 다시 타이핑하고 원장님 분석 중심으로 써요. (자료실 '내신 분석' 칸은 아직 없어요. 처음 요청 때 만들어요.)
- 목표: 좋은 영어 자료, 코코스학원 홍보, 블로그·자료실 애드센스 수익.
