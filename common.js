/* =========================================
   리카수니 자료실 - 공통 설정
   ========================================= */
const SUPABASE_URL = 'https://iiyhmskvdjgstoikonwu.supabase.co';
const SUPABASE_KEY = 'sb_publishable_JHxdlqWVh26TqD36jLflYQ_KoUmeuUj';
const MISSION_GOAL = 10; // 화면에 표시할 기본 미션 목표(댓글 수)

const sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

const $ = (sel) => document.querySelector(sel);

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function fmtDate(t) {
  const d = new Date(t);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}.${p(d.getMonth() + 1)}.${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

async function getUser() {
  const { data: { session } } = await sb.auth.getSession();
  saveKakaoToken(session);
  // 로그인 후 주소창에 남는 토큰 정리
  if (location.hash.includes('access_token')) {
    history.replaceState(null, '', location.pathname + location.search);
  }
  return session?.user ?? null;
}

// 카카오 로그인 직후 받은 토큰을 서버에 보관 → 요청한 자료가 나중에 준비되면 카톡으로 자동 발송 (자동 발송은 하루 1개)
function saveKakaoToken(session) {
  const rt = session?.provider_refresh_token;
  const prov = session?.user?.app_metadata || {};
  if (!rt || !((prov.providers || [prov.provider]).includes('kakao'))) return;
  const mark = rt.slice(-12);
  try { if (localStorage.getItem('kakao-saved') === mark) return; } catch (e) { /* 저장소 사용 불가 */ }
  fetch(`${SUPABASE_URL}/functions/v1/kakao-token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', apikey: SUPABASE_KEY, Authorization: `Bearer ${session.access_token}` },
    body: JSON.stringify({ refresh_token: rt, access_token: session.provider_token || '' })
  }).then(r => { if (r.ok) { try { localStorage.setItem('kakao-saved', mark); } catch (e) { /* 무시 */ } } }).catch(() => {});
}

function displayName(user) {
  const m = user?.user_metadata || {};
  return m.full_name || m.name || m.nickname || m.preferred_username
    || (user?.email || '').split('@')[0] || '회원';
}

/* ---------- 로그인 ---------- */
async function login(provider = 'kakao', scopes) {
  const redirectTo = location.origin + location.pathname + location.search;
  const { error } = await sb.auth.signInWithOAuth({
    provider,
    options: { redirectTo, ...(scopes ? { scopes } : {}) }
  });
  if (error) toast('로그인 오류: ' + error.message);
}

// 로그인 버튼 (회원은 카카오만, 관리자 페이지에서만 구글 버튼 추가)
function loginButtons(withGoogle = false) {
  return `
    <div class="login-btns">
      <button class="btn btn-kakao" onclick="login('kakao', 'talk_message')">
        <span class="ico">💬</span> 카카오로 시작하기
      </button>
      ${withGoogle ? `<button class="btn btn-google" onclick="login('google')">
        <span class="ico g">G</span> 구글로 시작하기
      </button>` : ''}
    </div>`;
}

// 로그인 방법 선택 창
function showLogin() {
  closeLogin();
  const wrap = document.createElement('div');
  wrap.id = 'login-modal';
  wrap.className = 'modal';
  wrap.innerHTML = `
    <div class="modal-box" role="dialog" aria-label="로그인">
      <button class="modal-x" onclick="closeLogin()" aria-label="닫기">×</button>
      <h2>로그인</h2>
      <p class="muted">카카오 계정으로 간편하게 로그인하세요.</p>
      ${loginButtons()}
    </div>`;
  wrap.addEventListener('click', (e) => { if (e.target === wrap) closeLogin(); });
  document.body.appendChild(wrap);
}

function closeLogin() {
  const m = document.getElementById('login-modal');
  if (m) m.remove();
}

async function logout() {
  await sb.auth.signOut();
  location.reload();
}

function renderAuth(user) {
  const el = $('#auth');
  if (!el) return;
  if (!user) {
    el.innerHTML = `<button class="btn btn-gold btn-sm" onclick="showLogin()">로그인</button>`;
    return;
  }
  const pic = user.user_metadata?.avatar_url || user.user_metadata?.picture;
  el.innerHTML = `
    ${pic ? `<img class="avatar" src="${esc(pic)}" alt="">` : ''}
    <span class="name">${esc(displayName(user))}</span>
    <button class="btn btn-line btn-sm" onclick="logout()">로그아웃</button>`;
  adminLink(user, el);
}

// 관리자 계정으로 로그인하면 머리글에 '관리자' 버튼 (관리자 페이지 바로 가기). 확인 결과는 탭을 닫을 때까지 기억
async function adminLink(user, el) {
  if (location.pathname.startsWith('/admin')) return;
  const key = 'is-admin-' + user.id;
  let v = null;
  try { v = sessionStorage.getItem(key); } catch (e) { /* 저장소 사용 불가 */ }
  if (v === null) {
    let data = false;
    try { ({ data } = await sb.rpc('is_admin')); } catch (e) { /* 무시 */ }
    v = data ? '1' : '0';
    try { sessionStorage.setItem(key, v); } catch (e) { /* 무시 */ }
  }
  if (v === '1' && !el.querySelector('.admin-go')) el.insertAdjacentHTML('afterbegin', '<a class="btn btn-gold btn-sm admin-go" href="/admin.html">관리자</a>');
}

/* ---------- 알림 ---------- */
let toastTimer;
function toast(msg) {
  let el = $('#toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2800);
}
