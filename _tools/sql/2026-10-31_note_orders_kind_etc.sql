-- 기타 자료 요청도 분석노트처럼 파일 하나짜리 열기 링크(/get/?t=)로 보내려고 kind 'etc' 추가 (함수 etc-notify)
alter table public.note_orders drop constraint note_orders_kind_check;
alter table public.note_orders add constraint note_orders_kind_check check (kind = any (array['moe','book','etc']));
