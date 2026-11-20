-- 자료실 방문자 수 (2026-11-20 원장님 요청: 자료실 관리자 페이지에서 바로 보기)
-- 페이지마다 /rest/v1/rpc/hit 한 번 (build.py 바닥 스크립트). 방문자는 브라우저마다 만든 임의 번호(vid)로 하루 한 번만 셈.
-- 표는 아무도 직접 못 읽고(RLS, 정책 없음) 관리자 함수 admin_visits 로만 봄. 90일 지난 방문자 번호는 지움.

create table if not exists public.visit_days (
  day date not null,
  vid text not null,
  primary key (day, vid)
);
create table if not exists public.visit_pages (
  day date not null,
  path text not null,
  n int not null default 0,
  primary key (day, path)
);
create table if not exists public.visit_srcs (
  day date not null,
  src text not null,
  n int not null default 0,
  primary key (day, src)
);
alter table public.visit_days enable row level security;
alter table public.visit_pages enable row level security;
alter table public.visit_srcs enable row level security;

create or replace function public.hit(p_path text, p_vid text, p_src text)
returns void language plpgsql security definer set search_path = public as $$
declare d date := (now() at time zone 'Asia/Seoul')::date; ins int;
begin
  if p_vid is null or length(p_vid) < 8 or length(p_vid) > 40 then return; end if;
  p_path := left(coalesce(nullif(p_path, ''), '/'), 120);
  p_src := case when p_src in ('naver','google','daum','kakao','blog','bing','other','direct','inside') then p_src else 'other' end;
  insert into visit_days(day, vid) values (d, p_vid) on conflict do nothing;
  get diagnostics ins = row_count;
  if ins > 0 then
    insert into visit_srcs(day, src, n) values (d, p_src, 1)
      on conflict (day, src) do update set n = visit_srcs.n + 1;
  end if;
  insert into visit_pages(day, path, n) values (d, p_path, 1)
    on conflict (day, path) do update set n = visit_pages.n + 1;
end $$;
revoke all on function public.hit(text, text, text) from public;
grant execute on function public.hit(text, text, text) to anon, authenticated;

-- 관리자용: 최근 p_days 일 일별 방문자·조회수, 최근 7일 유입·많이 본 페이지
create or replace function public.admin_visits(p_days int default 30)
returns jsonb language plpgsql security definer set search_path = public as $$
declare d0 date := (now() at time zone 'Asia/Seoul')::date; r jsonb;
begin
  if not public.is_admin() then raise exception 'not admin'; end if;
  delete from visit_days where day < d0 - 90;
  select jsonb_build_object(
    'days', (select coalesce(jsonb_agg(x order by x.day desc), '[]') from (
      select g::date as day,
        (select count(*) from visit_days v where v.day = g::date) as users,
        (select coalesce(sum(n), 0) from visit_pages p where p.day = g::date) as views
      from generate_series(d0 - (p_days - 1), d0, interval '1 day') g) x),
    'srcs', (select coalesce(jsonb_agg(x order by x.n desc), '[]') from (
      select src, sum(n)::int n from visit_srcs where day > d0 - 7 group by src) x),
    'pages', (select coalesce(jsonb_agg(x order by x.n desc), '[]') from (
      select path, sum(n)::int n from visit_pages where day > d0 - 7 group by path order by 2 desc limit 20) x),
    'today_pages', (select coalesce(jsonb_agg(x order by x.n desc), '[]') from (
      select path, n from visit_pages where day = d0 order by n desc limit 10) x)
  ) into r;
  return r;
end $$;
revoke all on function public.admin_visits(int) from public, anon;
grant execute on function public.admin_visits(int) to authenticated;
