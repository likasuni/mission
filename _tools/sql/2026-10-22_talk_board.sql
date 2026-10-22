-- 소통하기 게시판 (2026-10-22 Supabase 에 적용함). comments 의 page_key = 'talk' 글을 게시판으로 씀
-- 비밀글(secret)은 글쓴이·관리자만 내용을 봄. 원장 답글은 관리자 페이지 '댓글 → 소통하기'에서 답니다.
alter table public.comments add column if not exists secret boolean not null default false;

alter policy comments_read on public.comments
  using (((approved = true) and (secret = false)) or (user_id = auth.uid()) or is_admin());

-- 회원이 글을 쓸 때 '원장 답글'을 끼워 넣지 못하게 (관리자·서버 함수만 답글을 씀)
create or replace function public.comments_guard() returns trigger
language plpgsql set search_path = public as $$
begin
  if current_user not in ('service_role', 'postgres', 'supabase_admin') and not public.is_admin() then
    new.reply := null;
    new.replied_at := null;
  end if;
  return new;
end $$;
create trigger comments_guard before insert on public.comments for each row execute function public.comments_guard();

-- 게시판 목록: 비밀글은 자리만 보이고 내용은 글쓴이·관리자만
create or replace function public.talk_posts(p_limit int default 10, p_offset int default 0)
returns table(id bigint, author_name text, content text, reply text, created_at timestamptz, replied_at timestamptz,
              secret boolean, mine boolean, staff boolean, total bigint)
language sql stable security definer set search_path = public as $$
  select c.id, c.author_name,
    case when not c.secret or c.user_id = auth.uid() or public.is_admin() then c.content end,
    case when not c.secret or c.user_id = auth.uid() or public.is_admin() then c.reply end,
    c.created_at, c.replied_at, c.secret,
    coalesce(c.user_id = auth.uid(), false),
    (c.user_id = '6363d675-9fa4-4539-af39-0028444f80f0'::uuid or exists (select 1 from public.admins a where a.user_id = c.user_id)),
    count(*) over ()
  from public.comments c
  where c.page_key = 'talk' and (c.approved or c.user_id = auth.uid() or public.is_admin())
  order by c.created_at desc
  limit least(greatest(p_limit, 1), 50) offset greatest(p_offset, 0)
$$;
revoke execute on function public.talk_posts(int, int) from public;
grant execute on function public.talk_posts(int, int) to anon, authenticated;

-- 공지 고정 (2026-10-22 추가). 관리자만 pinned 를 켤 수 있음 (comments_guard 가 회원 글은 false 로)
alter table public.comments add column if not exists pinned boolean not null default false;
create or replace function public.comments_guard() returns trigger
language plpgsql set search_path = public as $$
begin
  if current_user not in ('service_role', 'postgres', 'supabase_admin') and not public.is_admin() then
    new.reply := null;
    new.replied_at := null;
    new.pinned := false;
  end if;
  return new;
end $$;
-- 목록 (talk_posts 대신 talk_list 사용 — talk_posts 는 이제 안 씀)
create or replace function public.talk_list(p_limit int default 10, p_offset int default 0)
returns table(id bigint, author_name text, content text, reply text, created_at timestamptz, replied_at timestamptz,
              secret boolean, pinned boolean, mine boolean, staff boolean, total bigint)
language sql stable security definer set search_path = public as $$
  select c.id, c.author_name,
    case when not c.secret or c.user_id = auth.uid() or public.is_admin() then c.content end,
    case when not c.secret or c.user_id = auth.uid() or public.is_admin() then c.reply end,
    c.created_at, c.replied_at, c.secret, c.pinned,
    coalesce(c.user_id = auth.uid(), false),
    (c.user_id = '6363d675-9fa4-4539-af39-0028444f80f0'::uuid or exists (select 1 from public.admins a where a.user_id = c.user_id)),
    count(*) over ()
  from public.comments c
  where c.page_key = 'talk' and (c.approved or c.user_id = auth.uid() or public.is_admin())
  order by c.pinned desc, c.created_at desc
  limit least(greatest(p_limit, 1), 50) offset greatest(p_offset, 0)
$$;
revoke execute on function public.talk_list(int, int) from public;
grant execute on function public.talk_list(int, int) to anon, authenticated;
