-- 2026-10-31: 연락이 안 되는 요청 정리용 상태 'expired' 추가
-- (완성됐지만 카톡 받기 동의가 없어 못 보내고 3일 동안 받으러 오지 않은 요청 → note-deliver 가 expired 로 바꾸고 목록에서 뺌)
alter table public.note_orders drop constraint note_orders_status_check;
alter table public.note_orders add constraint note_orders_status_check check (status = any (array['sent','missing','resolved','done','expired']));
