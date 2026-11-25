-- 회차 페이지 '많이 본 해설' 칩 (2026-11-26 원장님): 최근 N일 해설 페이지 조회 수 상위 몇 개 (경로·조회 수만, 개인 정보 없음)
create or replace function public.popular_posts(p_prefix text, p_days int default 7, p_limit int default 3)
returns table(path text, n bigint)
language sql stable security definer set search_path = public as $$
  select vp.path, sum(vp.n)::bigint
  from public.visit_pages vp
  where p_prefix ~ '^/(moe|suneung)/[a-z0-9/-]+/eng/$'
    and vp.path like p_prefix || '%'
    and vp.path ~ '/eng/[0-9]+(-[0-9]+)?/$'
    and vp.day >= (now() at time zone 'Asia/Seoul')::date - least(greatest(p_days, 1), 30)
  group by vp.path
  order by 2 desc
  limit least(greatest(p_limit, 1), 10);
$$;
grant execute on function public.popular_posts(text, int, int) to anon, authenticated;
