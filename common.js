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
  // 로그인 후 주소창에 남는 토큰 정리
  if (location.hash.includes('access_token')) {
    history.replaceState(null, '', location.pathname + location.search);
  }
  return session?.user ?? null;
}

function displayName(user) {
  const m = user?.user_metadata || {};
  return m.full_name || m.name || m.nickname || m.preferred_username
    || (user?.email || '').split('@')[0] || '회원';
}

/* ---------- 로그인 ---------- */
async function login(provider = 'google') {
  const redirectTo = location.origin + location.pathname + location.search;
  const { error } = await sb.auth.signInWithOAuth({
    provider,
    options: { redirectTo }
  });
  if (error) toast('로그인 오류: ' + error.message);
}

// 구글·카카오 로그인 버튼 묶음 (본문 안에 넣을 때 사용)
function loginButtons() {
  return `
    <div class="login-btns">
      <button class="btn btn-kakao" onclick="login('kakao')">
        <span class="ico">💬</span> 카카오로 시작하기
      </button>
      <button class="btn btn-google" onclick="login('google')">
        <span class="ico g">G</span> 구글로 시작하기
      </button>
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
      <p class="muted">사용하시는 계정으로 간편하게 로그인하세요.</p>
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
