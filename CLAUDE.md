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
- **분석노트 요청**(Supabase `note_orders`, 함수 `_tools/functions/note-request`·`note-deliver`): 상태 missing(만들어야 함) → resolved(드라이브에 올라옴·학생 수령 대기) → sent(보냄). 자동 카톡은 한 번에 여러 개 요청해도 첫 1개만, 나머지는 학생이 로그인해서 받음. 하루 한도 모의고사 2개·부교재 1개 (받기도, 새 번호 요청도 같은 한도. 예전에 요청해 둔 자료를 받는 건 요청으로 안 셈). 요청 댓글 답글 문구(접수했어요/준비됐어요/보내 드렸어요)로 자료실 표시(진행 중/준비 완료/카톡 발송)가 정해짐. 자동 카톡 실패 이유는 `note_orders.kakao_issue`(no_consent·no_token·fail)에 기록돼 관리자 페이지에 '직접 안내 필요'로 보이고, 학생이 다시 로그인할 때까지 재시도하지 않음. 함수는 저장소 코드와 똑같이 Supabase 에 배포.
- **소통하기 게시판**(첫 화면 '자료 요청' 아래): `comments` 의 `page_key='talk'` 글. 비밀글(`secret`)은 글쓴이·관리자만 봄, 목록은 RPC `talk_list`(고정 공지 `pinned` 가 맨 위, 관리자만 고정/해제). 원장 답변은 관리자 페이지 댓글 탭의 '소통하기' 필터에서. 회원은 글에 답글을 끼워 넣을 수 없음(트리거 `comments_guard`). SQL 기록은 `_tools/sql/`.
- 관리자 페이지 `admin.html`: 관리자 계정(Supabase `admins` — 원장님 구글 계정 + 카카오 계정, 2026-10-23 카카오 추가)으로 로그인하면 자료실 머리글에 '관리자' 버튼이 보여요.
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

## 자료 완료 알림 (원장님이 "완료"라고 하면)

두 가지를 바로 보내요. Supabase 프로젝트 `iiyhmskvdjgstoikonwu` 에서 `execute_sql` 로 실행해요 (이 환경은 supabase.co 직접 접속이 막혀 있어서 DB 의 `net.http_post` 로 불러요).

1. **요청한 학생 카톡**: `note-deliver` 함수(평소엔 매시 5분 자동)를 바로 실행. 드라이브에 올라온 요청 자료를 그 학생에게 카톡 '나와의 채팅'으로 보내요 (회원당 하루 1개 규칙 그대로).
   `select net.http_post(url := 'https://iiyhmskvdjgstoikonwu.supabase.co/functions/v1/note-deliver', headers := jsonb_build_object('Content-Type','application/json','x-cron-key',(select v from public.private_config where k='cron_key')), body := '{}'::jsonb, timeout_milliseconds := 60000);`
2. **알림 켠 모든 학생 웹 푸시**: `push` 함수 `send`. 제목·내용·주소(자료실 안 경로)는 원장님께 보여 드리고 확인받은 뒤 보내요.
   `select net.http_post(url := 'https://iiyhmskvdjgstoikonwu.supabase.co/functions/v1/push', headers := jsonb_build_object('Content-Type','application/json','x-cron-key',(select v from public.private_config where k='cron_key')), body := jsonb_build_object('action','send','title','리카수니 자료실','body','2025년 10월 고2 영어 분석노트가 올라왔어요','url','/moe/go2/2025-10/eng/'));`
   결과는 `select status_code, content from net._http_response where id = <위 결과 번호>;` 로 확인 (sent·gone·fail 개수). 기록은 `push_log` 테이블.
   보낸 알림은 자료실 첫 화면 '최근 알림'(최근 5개)에 보여요. 시험 발송은 body 에 `'test', true` 를 넣으면 목록에 안 나와요 (`push_log.hidden`).
- 웹 푸시 구조: 사이트 `push.js`(🔔 버튼, `.push-btn`) + `sw.js` + `manifest.webmanifest`, 서버 `_tools/functions/push` (구독은 `push_subs`, VAPID 키는 `private_config` 의 vapid_public·vapid_private, 비밀키는 밖으로 꺼내지 않아요).
- 아이폰은 사파리 '홈 화면에 추가' 후 그 아이콘으로 열어야 알림을 켤 수 있어요 (iOS 16.4 이상).
- 알림은 너무 자주 보내지 않아요 (하루 1~2번 정도). 학생이 알림을 끄면 효과가 사라져요.

## 진행 방식

- 작업 브랜치에서 커밋 → PR → main 에 합치기까지 해요 (원장님이 이 흐름에 동의함). 바꾼 뒤엔 로컬 빌드와 화면 캡처로 확인하고 결과 이미지를 보여 드려요.
- 아침 6시 48분 알림(예약 작업 '자료 요청·댓글 아침 알림'): 오늘 공개된 해설, 없는 자료 요청, 새 댓글을 휴대폰으로 알려요. 공개 확인은 GitHub 의 사이트 파일로 해요.
- **비밀값(보안 비밀번호, refresh token, 비밀번호)은 채팅에 붙여 넣거나 캡처하지 않게** 매번 안내해요. 클라이언트 ID·블로그 ID 는 비밀이 아니에요.
- 학교 내신 시험지는 저작권이 학교에 있어요. 사진을 통째로 올리지 말고 문항을 다시 타이핑하고 원장님 분석 중심으로 써요. 
- **내신 분석 (코코스 학원생 전용)**: 공개 페이지 `/naesin/`, `/naesin/<학교>/` 는 학교 목록·시험 제목만 (학원 홍보용, 학교 목록 `_tools/naesin.json`, 학원 홈페이지는 https://www.cocosedu.co.kr/ — www 없으면 인증서 경고). **분석 내용은 저장소에 쓰지 않고** Supabase `naesin_posts`(school=slug, title, body HTML)에 넣어요. 보기는 `naesin_members` 에서 원장님이 **한 명씩 승인**한 학원생만 (RLS, `is_naesin_member()`). 승인은 admin.html '학원생 승인' 탭. 글을 넣으면 `naesin.json` 의 그 학교 `exams` 에 시험 정보(key·title·full·date·info)도 추가해 공개 목록에 보이게 해요.
  - **학원생 전용 글 형식** (원장님 확정, 2026-10-25): 시험 1개 = `naesin_posts` 1줄(school, exam_key, title, body=시험 총평 HTML, items=문항 카드 배열). 문항 카드: n·type·points·answer·**where(시험지에서 볼 곳: 쪽·위치·짧은 근거 구절)**·steps(풀이 흐름)·choices([선택지, 판단, 이유])·points_more(문법·어휘)·**checks(원장님이 새로 만든 확인 문제 3~4개, q·a)**·next(다음 시험 대비). 학생은 자기 시험지를 펴 놓고 봐요. 원문 통째 타이핑 금지(시험지에 학교·교육청 저작권 안내). 페이지에서 '틀린 번호만 보기'·'확인 학습지 인쇄'로 개인별 확인 학습.
  - **어휘 문항 카드** (원장님 요청, 2026-10-25): 선택지 단어마다 **우리말 뜻**을 모두 넣고, 문장·풀이가 있으면 **우리말 해석**까지 붙여요 (학원생 전용·공개 모두).
  - **공개 문항** (검색·학원 홍보용, 시험당 5문항 정도): `_tools/naesin_public/<학교>-<시험key>-<번호>.json` (lead·sections·tip, 논술형은 n=`seo3`·label=`논술형 3`). 문제 원문은 옮기지 않고 분석만. 태원고 2026 2학기 중간 고1: 3·7·10·11·논술형 3 공개. 야탑중 2026 2학기 1차 중3(학교 정답지 없음 → 원장 풀이 기준, 논술형은 예시 답안): 유형별 대표 14 어법·3 독해·6 어휘·18 대화·논술형 1 공개. 학원생 전용은 `naesin_posts` 에 한 번에 insert(on conflict school, exam_key).
- 목표: 좋은 영어 자료, 코코스학원 홍보, 블로그·자료실 애드센스 수익.
