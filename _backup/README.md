# 자료실 데이터 백업

- `supabase.json.enc`: 자료실 댓글·로그인 회원·분석노트 요청 데이터(Supabase). 매주 일요일 새벽 4시 17분(한국 시간)에 Actions `db-backup` 이 새로 받아 덮어써요. 이전 주 파일은 커밋 기록에 남아요.
- 저장소가 공개라서 **암호화된 파일만** 올려요. 열쇠는 GitHub Secret `BACKUP_KEY` (Supabase `private_config` 표의 `backup_key` 값과 같음). 열쇠는 채팅에 붙여 넣지 않아요.
- 빠진 것: `kakao_tokens`, `private_config` (비밀값이라 백업하지 않음, 문제가 생기면 다시 연결), 회원 비밀번호(구글·카카오 로그인이라 없음).

## 푸는 방법

```
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass pass:<열쇠> -in _backup/supabase.json.enc -out db.json
```

`db.json` 안에 표 이름별(comments, note_orders …)로 데이터가 들어 있어요. 되살릴 때는 Claude 에게 "백업으로 댓글 복구해 줘"라고 하면 표에 다시 넣어 줘요. 다 쓴 `db.json` 은 지워요 (개인정보).
