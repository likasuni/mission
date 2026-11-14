-- 소통하기 → '자료 문의' (2026-11-14 원장님): 문의마다 원장님 답변 상태
-- ask_status: null = 검토 중(답글 없음)/답변 완료, 'added' = 추가했어요 (ask_link 로 요청하러 가기), 'no' = 어려워요
alter table public.comments add column if not exists ask_status text check (ask_status in ('added', 'no'));
alter table public.comments add column if not exists ask_link text;

-- 회원은 상태·링크를 못 바꿈 (답글·고정과 같게)
create or replace function public.comments_guard()
 returns trigger language plpgsql set search_path to 'public'
as $function$
begin
  if current_user not in ('service_role', 'postgres', 'supabase_admin') and not public.is_admin() then
    new.reply := null;
    new.replied_at := null;
    new.pinned := false;
    new.ask_status := null;
    new.ask_link := null;
  end if;
  return new;
end $function$;

-- 목록에 상태·링크 추가 (반환 모양이 바뀌어서 지우고 다시 만듦)
drop function if exists public.talk_list(integer, integer);
create function public.talk_list(p_limit integer default 10, p_offset integer default 0)
 returns table(id bigint, author_name text, content text, reply text, created_at timestamptz, replied_at timestamptz,
   secret boolean, pinned boolean, mine boolean, staff boolean, total bigint, ask_status text, ask_link text)
 language sql stable security definer set search_path to 'public'
as $function$
  select c.id, c.author_name,
    case when not c.secret or c.user_id = auth.uid() or public.is_admin() then c.content end,
    case when not c.secret or c.user_id = auth.uid() or public.is_admin() then c.reply end,
    c.created_at, c.replied_at, c.secret, c.pinned,
    coalesce(c.user_id = auth.uid(), false),
    (c.user_id = '6363d675-9fa4-4539-af39-0028444f80f0'::uuid or exists (select 1 from public.admins a where a.user_id = c.user_id)),
    count(*) over (),
    c.ask_status,
    case when not c.secret or c.user_id = auth.uid() or public.is_admin() then c.ask_link end
  from public.comments c
  where c.page_key = 'talk' and (c.approved or c.user_id = auth.uid() or public.is_admin())
  order by c.pinned desc, c.created_at desc
  limit least(greatest(p_limit, 1), 50) offset greatest(p_offset, 0)
$function$;
grant execute on function public.talk_list(integer, integer) to anon, authenticated;
