-- 2026-11-27 원장님: 방문자 탭 '어디서 왔나'에 스레드를 따로 세기
-- 페이지 코드(VISIT_JS)가 ?from=threads 주소·threads 사이트·스레드 앱 브라우저를 'threads' 로 보냄
create or replace function public.hit(p_path text, p_vid text, p_src text)
returns void language plpgsql security definer set search_path = public as $$
declare d date := (now() at time zone 'Asia/Seoul')::date; ins int;
begin
  if p_vid is null or length(p_vid) < 8 or length(p_vid) > 40 then return; end if;
  p_path := left(coalesce(nullif(p_path, ''), '/'), 120);
  p_src := case when p_src in ('naver','google','daum','kakao','blog','bing','threads','other','direct','inside') then p_src else 'other' end;
  insert into visit_days(day, vid) values (d, p_vid) on conflict do nothing;
  get diagnostics ins = row_count;
  if ins > 0 then
    insert into visit_srcs(day, src, n) values (d, p_src, 1)
      on conflict (day, src) do update set n = visit_srcs.n + 1;
  end if;
  insert into visit_pages(day, path, n) values (d, p_path, 1)
    on conflict (day, path) do update set n = visit_pages.n + 1;
end $$;
