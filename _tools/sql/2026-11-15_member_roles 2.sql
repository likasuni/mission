-- 회원 구분 (학생·선생님·학부모): 분석노트 첫 요청 때 한 번 고름 (2026-11-15 원장님 확정)
-- 본인 것만 읽고 한 번만 넣을 수 있음 (고치기·지우기 없음). 관리자는 모두 읽음. 화면(lib.js)이 요청 전에 확인
create table if not exists public.member_roles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null check (role in ('student', 'teacher', 'parent')),
  created_at timestamptz not null default now()
);
alter table public.member_roles enable row level security;
create policy member_roles_read on public.member_roles for select using (user_id = auth.uid() or is_admin());
create policy member_roles_insert on public.member_roles for insert with check (user_id = auth.uid());
grant select, insert on public.member_roles to authenticated;
