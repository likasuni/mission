-- 관리자 '요청자' 탭 (2026-11-17): 회원별 요청 기록을 한 번에 돌려줌.
-- 관리자(admins)만 부를 수 있음. 이메일·전화번호는 돌려주지 않음 (닉네임만).
create or replace function public.admin_requesters()
returns jsonb
language plpgsql
stable
security definer
set search_path to 'public'
as $$
begin
  if not public.is_admin() then
    raise exception 'not admin';
  end if;
  return coalesce((
    select jsonb_agg(x order by x->>'last_req' desc nulls last, x->>'last_in' desc nulls last)
    from (
      select jsonb_build_object(
        'id', u.id,
        'name', coalesce(nullif(u.raw_user_meta_data->>'name',''), nullif(u.raw_user_meta_data->>'full_name',''),
                         nullif(u.raw_user_meta_data->>'user_name',''), (select o.author_name from note_orders o where o.user_id = u.id and o.author_name is not null limit 1), '이름 없음'),
        'via', u.raw_app_meta_data->>'provider',
        'joined', u.created_at,
        'last_in', u.last_sign_in_at,
        'role', (select r.role from member_roles r where r.user_id = u.id),
        'academy', exists (select 1 from naesin_members n where n.user_id = u.id and n.status = 'approved'),
        'admin', exists (select 1 from admins a where a.user_id = u.id),
        'comments', (select count(*) from comments c where c.user_id = u.id),
        'first_req', (select min(o.created_at) from note_orders o where o.user_id = u.id),
        'last_req', (select max(o.created_at) from note_orders o where o.user_id = u.id),
        'days', (select count(distinct (o.created_at at time zone 'Asia/Seoul')::date) from note_orders o where o.user_id = u.id),
        'orders', coalesce((select jsonb_agg(jsonb_build_object('k', o.kind, 'l', o.label, 's', o.status, 'q', o.query, 't', o.created_at) order by o.created_at desc)
                            from note_orders o where o.user_id = u.id), '[]'::jsonb)
      ) x
      from auth.users u
    ) t
  ), '[]'::jsonb);
end;
$$;

revoke all on function public.admin_requesters() from public, anon;
grant execute on function public.admin_requesters() to authenticated;
