/* =========================================
   자료실 페이지 공통: 로그인 표시 + 페이지 댓글 + 분석노트 요청
   - 댓글은 어느 페이지에 달든 미션 개수에 합산
   - 분석노트 요청: 카카오 회원, 하루 모의고사 2개 · 부교재 1개, 24시간 링크를 카톡으로 자동 발송
   ========================================= */
// 부교재 목록: 이름은 드라이브 '부교재 분석노트' 안 폴더 이름과 같게 (note-request 함수의 BOOKS, build.py BOOKS와 같게)
// u: 단위(강/회), max: 마지막 강·회, n: 문항 수, gw: Gateway 있음, ex: 1번 앞 예시문제 있음 (둘 다 번호 0, 파일 이름 '강-0.pdf')
const NOTE_BOOK_CFG = {
  '수능특강 라이트': { u: '강', max: 22, n: 10, gw: true },
  '리딩파워 기본': { u: '강', max: 30, n: 10, ex: true },
  '리딩파워 완성': { u: '강', max: 30, n: 10, ex: true },
  '올림포스 영어독해 기본1': { u: '강', max: 30, n: 10, ex: true },
  '하루 6개 1등급 모의고사 고1': { u: '회', max: 40, n: 6 },
  '하루 6개 1등급 모의고사 고2': { u: '회', max: 40, n: 6 },
  '올림포스 전국연합학력평가 기출문제집 고1': { u: '강', max: 20, n: 12, ex: true },
  '올림포스 전국연합학력평가 기출문제집 고2': { u: '강', max: 20, n: 12, ex: true },
};
const NOTE_BOOKS = Object.keys(NOTE_BOOK_CFG);
const zeroName = b => { const c = NOTE_BOOK_CFG[b] || {}; return c.gw ? 'Gateway' : c.ex ? '예시문제' : ''; }; // 번호 0 이름
const NOTE_LIMIT = { moe: 2, book: 1 }; // 하루에 받을 수 있는 개수 (note-request 함수 LIMIT 와 같게)

(async function () {
  const user = await getUser();
  renderAuth(user);
  noteRequest(user);
  readyBanner(user);
  recentComments();
  talkBoard(user);
  naesinMember(user);

  const box = document.getElementById('comments');
  if (!box) return;
  const key = box.dataset.pageKey;
  const title = box.dataset.pageTitle;

  async function load() {
    const { data } = await sb.from('comments')
      .select('id,author_name,content,approved,created_at,user_id,reply')
      .eq('page_key', key).order('created_at', { ascending: true });
    const list = (data || []).filter(c => c.approved || (user && c.user_id === user.id));
    const items = list.map(c => `
      <div class="comment">
        <div class="row">
          <strong>${OWNER_IDS.includes(c.user_id) ? '리카수니 원장 <span class="rc-badge">운영자</span>' : esc(maskName(c.author_name))}</strong>
          ${!c.approved ? '<span class="tag wait">비공개</span>' : ''}
          ${c.content.startsWith('[자료 요청]') ? (/보내 드렸어요/.test(c.reply || '') ? '<span class="rq-st ok">완료 · 카톡 발송</span>' : /준비됐어요/.test(c.reply || '') ? '<span class="rq-st rd">준비 완료</span>' : '<span class="rq-st">진행 중</span>') : ''}
          <span class="meta">${fmtDate(c.created_at)}</span>
        </div>
        <p class="body">${esc(c.content)}</p>
        ${c.reply ? `<div class="reply"><b>리카수니 원장</b><br>${esc(c.reply)}</div>` : ''}
      </div>`).join('') || '<p class="muted">아직 댓글이 없어요. 첫 댓글을 남겨 주세요!</p>';

    const form = user ? `
      <p class="muted">이 시험에 대한 질문이나 공부 후기를 <b>댓글</b>로 남겨 주세요. 짧은 질문도 괜찮아요. 원장님이 확인하고 답글을 달아 드려요.<br>
      분석노트를 받고 싶다면 댓글 대신 <a href="/notes/"><b>분석노트 요청</b></a>을 이용해 주세요.</p>
      <textarea id="cbody" maxlength="1000" placeholder="댓글 예) 31번 빈칸이 어려웠는데 해설을 보고 근거를 찾았어요. 다음엔 시간 배분을 더 신경 써야겠어요."></textarea>
      <div class="row between mt"><span class="meta"><span id="ccount">0</span>자</span>
      <button class="btn btn-navy" id="cbtn">댓글 등록</button></div>`
      : `<p class="muted">카카오로 로그인하면 이 시험에 대한 질문이나 공부 후기를 댓글로 남길 수 있어요.<br>분석노트는 댓글이 아니라 <a href="/notes/"><b>분석노트 요청</b></a>에서 받을 수 있어요.</p>${loginButtons()}`;

    box.innerHTML = `<h2>댓글 <span class="meta">${list.filter(c => c.approved).length}개</span></h2>${form}<div class="mt">${items}</div>`;
    if (user) {
      const t = document.getElementById('cbody');
      t.oninput = () => (document.getElementById('ccount').textContent = t.value.trim().length);
      document.getElementById('cbtn').onclick = submit;
    }
  }

  async function submit() {
    const content = document.getElementById('cbody').value.trim();
    if (content.length < 2) return toast('댓글 내용을 입력해 주세요.');
    const btn = document.getElementById('cbtn'); btn.disabled = true;
    const { error } = await sb.from('comments').insert({
      page_key: key, page_title: title, author_name: displayName(user), content
    });
    if (error) { btn.disabled = false; return toast('등록 실패: ' + error.message); }
    toast('댓글이 등록됐어요!');
    load();
  }
  window.reloadComments = load;
  load();
})();

/* ---------- 이름 가리기: 김나윤 → 김*윤, 홍길 → 홍*, 운영자는 그대로 ---------- */
const OWNER_IDS = ['6363d675-9fa4-4539-af39-0028444f80f0']; // 원장님 카카오 계정 (댓글에 '리카수니 원장'으로 표시)
function maskName(n) {
  n = String(n || '회원').trim();
  if (n === '리카수니' || n.length < 2) return n;
  return n.length === 2 ? n[0] + '*' : n[0] + '*'.repeat(n.length - 2) + n[n.length - 1];
}

/* ---------- 상자 안 자동 광고 밖으로 ----------
   자동 광고(관련 검색 '자세히 알아보기' 등)가 '자료 요청'·'소통하기' 상자 안에 끼어들면 목록이 찌그러지고 30초마다 다시 그릴 때 지워짐
   → 상자 안에 들어온 자동 광고는 바로 상자 바로 아래로 옮김 (광고는 그대로 보임, 수익 유지) */
function keepAdsOut(sec) {
  if (!sec || sec.dataset.adsOut) return;
  sec.dataset.adsOut = '1';
  const sweep = () => sec.querySelectorAll('.google-auto-placed, ins.adsbygoogle').forEach(ad => {
    const w = ad.closest('.google-auto-placed') || ad;
    if (sec.contains(w)) sec.after(w);
  });
  sweep();
  new MutationObserver(sweep).observe(sec, { childList: true, subtree: true });
}

/* ---------- 최근 댓글 (첫 화면): 30초마다 새로 불러옴 ---------- */
function recentComments() {
  const box = document.getElementById('recent-cmt');
  if (!box) return;
  const list = box.querySelector('.rc-list');
  const ago = t => {
    const m = Math.floor((Date.now() - new Date(t)) / 60000);
    if (m < 1) return '방금'; if (m < 60) return m + '분 전';
    const h = Math.floor(m / 60); if (h < 24) return h + '시간 전';
    const d = new Date(t); return `${d.getMonth() + 1}월 ${d.getDate()}일`;
  };
  // 자료 요청 댓글: [자료 요청] … 부탁드려요. 상태 3단계 (답글 문구로 구분)
  // 진행 중(주황, '접수했어요') → 준비 완료(파랑, '준비됐어요' — 드라이브에 올라옴, 요청하면 바로 카톡) → 카톡 발송(초록, '보내 드렸어요')
  const isReq = c => c.content.startsWith('[자료 요청]');
  const isDone = c => /보내 드렸어요/.test(c.reply || '');
  const isReady = c => !isDone(c) && /준비됐어요/.test(c.reply || '');
  // '나도 받기' 링크: 요청 칸에 같은 회차·번호가 미리 골라져 있게 (y·m·g·n 또는 book·unit·n)
  const reqLink = c => {
    const t = c.content.replace('[자료 요청] ', '').replace(' 분석노트 부탁드려요.', '');
    let m = t.match(/^(\d{4})년 (\d{1,2})월 고(\d) 영어 모의고사 (\d+)번$/), q = '';
    if (m) q = `?y=${m[1]}&m=${m[2]}&g=${m[3]}&n=${m[4]}`;
    else if ((m = t.match(/^(.+) (\d+)(?:강|회) (?:Gateway|예시문제|(\d+)번)$/))) q = `?book=${encodeURIComponent(m[1])}&unit=${m[2]}&n=${m[3] || 0}`;
    return `/${c.page_key}/${q}#note-req`;
  };
  const short = c => c.content.replace('[자료 요청] ', '').replace(' 분석노트 부탁드려요.', '').replace(' 영어 모의고사', '');
  const shown = { pre: 6, rdy: 6 };
  let cache = null, gf = 'all';  // gf: 학년 필터 (all·1·2·3·b=부교재)
  const gradeOf = c => { const m = c.content.match(/ 고(\d) /); return m ? m[1] : 'b'; };
  function reqItem(c) {
    const done = isDone(c), ready = isReady(c);
    return `<li class="rq${done || ready ? ' ok' : ''}"><span class="rq-st">${done ? '카톡 발송' : ready ? '준비 완료' : '진행 중'}</span>
      <span class="rq-tx"><b>${esc(short(c))}</b><span class="meta">${esc(maskName(c.author_name))} · ${done || ready ? ago(c.replied_at || c.created_at) + ' 완성' : ago(c.created_at)}</span></span>
      ${c.page_key ? `<a class="rq-go" href="${esc(reqLink(c))}"${ready || done ? ' title="요청하면 기다리지 않고 바로 받아요"' : ''}>나도 받기</a>` : ''}</li>`;
  }
  const more = (key, total) => total > shown[key] ? `<button class="rc-more" data-k="${key}">더보기 (${total - shown[key]}개)</button>` : '';
  function render() {
    const all = cache || [];
    const reqs = all.filter(isReq);
    const cnt = k => k === 'all' ? reqs.length : reqs.filter(c => gradeOf(c) === k).length;
    const chips = [['all', '전체'], ['1', '고1'], ['2', '고2'], ['3', '고3'], ['b', '부교재']].filter(([k]) => k === 'all' || cnt(k))
      .map(([k, t]) => `<button class="rq-chip${gf === k ? ' on' : ''}" data-g="${k}">${t} <small>${cnt(k)}</small></button>`).join('');
    const rf = reqs.filter(c => gf === 'all' || gradeOf(c) === gf);
    // 두 칸: 만드는 중(진행 중) · 받을 수 있어요(드라이브에 올라옴 — 준비 완료·카톡 발송 합침, 최근 완성 순)
    const pre = rf.filter(c => !isDone(c) && !isReady(c));
    const rdy = rf.filter(c => isDone(c) || isReady(c)).sort((a, b) => ((b.replied_at || b.created_at) > (a.replied_at || a.created_at) ? 1 : -1));
    const col = (cls, title, items, key, empty) => `<div class="rq-col ${cls}"><h3>${title} <span>${items.length}</span></h3><ul${shown[key] > 6 ? ' class="open"' : ''}>${items.slice(0, shown[key]).map(reqItem).join('') || `<li class="rq-empty">${empty}</li>`}</ul>${more(key, items.length)}</div>`;
    list.innerHTML = `<div class="rq-top"><h3 class="rc-sub">최근 자료 요청</h3><div class="rq-chips">${chips}</div></div>
      <div class="rq-cols">${col('', '만드는 중', pre, 'pre', '기다리는 요청이 없어요.')}${col('ok', '받을 수 있어요', rdy, 'rdy', '아직 준비된 자료가 없어요. 필요한 분석노트를 요청해 주세요.')}</div>`;
    list.querySelectorAll('.rq-chip').forEach(b => b.onclick = () => { gf = b.dataset.g; shown.pre = shown.rdy = 6; render(); });
    list.querySelectorAll('.rc-more').forEach(btn => btn.onclick = () => { shown[btn.dataset.k] += 6; render(); });
  }
  async function load() {
    const { data } = await sb.from('comments')
      .select('id,user_id,author_name,content,created_at,reply,replied_at,page_key,page_title')
      .eq('approved', true).like('content', '[자료 요청]%').order('created_at', { ascending: false }).limit(80);
    cache = data || [];
    render();
  }
  // 자동 광고가 요청 목록 칸 사이(첫 줄 옆)에 끼어들면 줄이 한 글자 폭으로 찌그러지고, 30초마다 다시 그릴 때 광고도 지워짐
  // → 목록 안에 들어온 자동 광고는 바로 목록 아래로 옮김 (광고는 그대로 보임)
  keepAdsOut(box);
  load();
  setInterval(() => { if (!document.hidden) load(); }, 30000);
  // 이미 로그인한 회원에게는 로그인 버튼을 숨김
  getUser().then(u => { const b = box.querySelector('.rc-login'); if (u && b) b.remove(); }).catch(() => {});
}

/* ---------- 소통하기 게시판 (첫 화면): 회원 질문 + 원장 답변, 비밀글은 글쓴이·관리자만 ---------- */
// 글은 comments 의 page_key='talk'. 목록은 talk_list RPC (비밀글 내용 가림, 고정 공지가 맨 위). 답변은 관리자 페이지 '댓글 → 소통하기'에서
// 관리자 계정으로 로그인하면 '공지로 고정'으로 쓰고, 목록에서 고정/해제할 수 있음 (해제하면 날짜 순서로 내려감)
async function talkBoard(user) {
  const box = document.getElementById('talk');
  if (!box) return;
  keepAdsOut(box);
  const formEl = box.querySelector('.tk-form'), listEl = box.querySelector('.tk-list');
  const ago = t => {
    const m = Math.floor((Date.now() - new Date(t)) / 60000);
    if (m < 1) return '방금'; if (m < 60) return m + '분 전';
    const h = Math.floor(m / 60); if (h < 24) return h + '시간 전';
    const d = new Date(t); return `${d.getMonth() + 1}월 ${d.getDate()}일`;
  };
  let limit = 10;
  const admin = user ? !!(await sb.rpc('is_admin')).data : false;
  formEl.innerHTML = user ? `
    <textarea id="tk-body" maxlength="1000" placeholder="예) 고1 9월 모의고사 32번 빈칸 근거를 어디서 찾아야 할지 모르겠어요. / 분석노트는 어떻게 공부하면 좋을까요?"></textarea>
    <div class="row between mt tk-bar">${admin ? '<label class="tk-secret"><input type="checkbox" id="tk-pin" checked> 📌 공지로 고정</label>' : ''}<label class="tk-secret"><input type="checkbox" id="tk-secret"> 🔒 비밀글 <span class="meta">(나와 원장님만 볼 수 있어요)</span></label>
    <span class="row" style="gap:8px"><span class="meta"><span id="tk-count">0</span>/1000</span><button class="btn btn-navy" id="tk-btn">${admin ? '글 올리기' : '질문 올리기'}</button></span></div>
    <p class="meta tk-note">분석노트가 필요하면 질문 대신 위 <b>자료 요청</b>을 이용해 주세요. 욕설·광고 글은 지워질 수 있어요.</p>`
    : `<p class="muted tk-login">카카오로 로그인하면 원장님께 질문을 남길 수 있어요. 성적·진로 같은 개인 고민은 <b>비밀글</b>로 남길 수 있어요.</p>${loginButtons()}`;
  if (user) {
    const t = document.getElementById('tk-body');
    t.oninput = () => (document.getElementById('tk-count').textContent = t.value.trim().length);
    document.getElementById('tk-btn').onclick = async () => {
      const content = t.value.trim();
      if (content.length < 2) return toast('질문 내용을 입력해 주세요.');
      const btn = document.getElementById('tk-btn'); btn.disabled = true;
      const { error } = await sb.from('comments').insert({
        page_key: 'talk', page_title: '소통하기', author_name: displayName(user), content,
        secret: document.getElementById('tk-secret').checked, pinned: admin && document.getElementById('tk-pin').checked
      });
      btn.disabled = false;
      if (error) return toast('등록 실패: ' + error.message);
      t.value = ''; document.getElementById('tk-count').textContent = '0'; document.getElementById('tk-secret').checked = false;
      toast('질문을 올렸어요! 원장님이 확인하고 답변해 드려요.');
      load();
    };
  }
  function item(p) {
    const hidden = p.secret && p.content == null;
    const nm = p.staff ? '리카수니 원장' : maskName(p.author_name);
    const st = p.staff ? '' : p.reply ? '<span class="tk-st ok">답변 완료</span>' : '<span class="tk-st">답변 대기</span>';
    return `<div class="tk-item${p.staff ? ' own' : ''}${p.pinned ? ' pin' : ''}">
      <div class="tk-top">${p.pinned ? '<span class="tk-pin">📌 공지</span>' : ''}${st}<b>${esc(nm)}</b>${p.staff ? '<span class="rc-badge">운영자</span>' : ''}${p.mine ? '<span class="tk-mine">내 글</span>' : ''}${p.secret ? '<span class="tk-lock">🔒 비밀글</span>' : ''}<span class="meta">${ago(p.created_at)}</span>${admin ? `<button class="tk-pbtn" data-id="${p.id}" data-p="${p.pinned ? 1 : 0}">${p.pinned ? '고정 해제' : '📌 고정'}</button>` : ''}</div>
      <p class="tk-tx${hidden ? ' tk-hid' : ''}">${hidden ? '비밀글이에요. 글쓴이와 원장님만 볼 수 있어요.' : esc(p.content)}</p>
      ${p.reply ? `<div class="tk-rp"><b>리카수니 원장</b><span class="meta">${p.replied_at ? ago(p.replied_at) : ''}</span><p>${esc(p.reply)}</p></div>` : ''}
    </div>`;
  }
  async function load() {
    const { data, error } = await sb.rpc('talk_list', { p_limit: limit, p_offset: 0 });
    if (error) { listEl.innerHTML = '<p class="muted">게시판을 불러오지 못했어요. 잠시 후 다시 열어 주세요.</p>'; return; }
    const rows = data || [], total = rows.length ? Number(rows[0].total) : 0;
    listEl.innerHTML = (rows.map(item).join('') || '<p class="muted">아직 글이 없어요. 첫 질문을 남겨 주세요!</p>') +
      (total > rows.length ? `<button class="rc-more" id="tk-more">더보기 (${total - rows.length}개)</button>` : '');
    const mb = document.getElementById('tk-more');
    if (mb) mb.onclick = () => { limit += 10; load(); };
    listEl.querySelectorAll('.tk-pbtn').forEach(b => b.onclick = async () => {
      const { error } = await sb.from('comments').update({ pinned: b.dataset.p !== '1' }).eq('id', +b.dataset.id);
      if (error) return toast('오류: ' + error.message);
      toast(b.dataset.p === '1' ? '고정을 풀었어요. 날짜 순서로 내려가요.' : '맨 위에 공지로 고정했어요.');
      load();
    });
  }
  load();
  setInterval(() => { if (!document.hidden) load(); }, 60000);
}

/* ---------- 분석노트 요청 ---------- */
/* ---------- 재방문 이어 주기 ----------
   ① 알림 권유 칸: 받은 직후·없는 자료 요청 직후·'내일 받기'가 남았을 때 "🔔 알림 켜기"를 권함 (이미 켰으면 안 보임)
   ② 첫 화면 배너: 로그인한 학생에게 '요청하신 자료 N개 준비됐어요 / 만드는 중 N개'를 보여 주고 받으러 가게 함 */
function pushAsk(msg) {
  const P = window.likaPush;
  if (!P || !P.supported || P.isOn()) return '';
  return `<div class="push-ask"><span>🔔 ${msg}</span><button type="button" class="btn btn-navy btn-sm" onclick="window.likaPush && window.likaPush.click()">알림 켜기</button></div>`;
}
function nextResetText() { // 하루 한도는 한국 시간 자정에 다시 채워짐
  return '내일(자정 지나면) 다시 받을 수 있어요';
}
async function myNotes(user) { // 내 요청: 준비된 것(받기 가능) · 만드는 중
  const { data: { session } } = await sb.auth.getSession();
  if (!session) return null;
  let r = {};
  try {
    const res = await fetch(`${SUPABASE_URL}/functions/v1/note-request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', apikey: SUPABASE_KEY, Authorization: `Bearer ${session.access_token}` },
      body: JSON.stringify({ kind: 'check' })
    });
    r = await res.json();
  } catch (e) { return null; }
  const ready = r.ready || [];
  const { data: waits } = await sb.from('note_orders').select('label,status').eq('user_id', user.id).in('status', ['missing', 'resolved']);
  const readySet = new Set(ready.map(x => x.label));
  const making = [...new Set((waits || []).filter(w => !readySet.has(w.label)).map(w => w.label))];
  return { ready, making, today: r.today || {}, limit: r.limit || NOTE_LIMIT };
}
async function readyBanner(user) {
  const hero = document.querySelector('.hero');
  if (!hero || document.getElementById('note-req') || !user) return;
  const isKakao = (user.app_metadata?.providers || [user.app_metadata?.provider]).includes('kakao');
  if (!isKakao) return;
  const m = await myNotes(user);
  if (!m || (!m.ready.length && !m.making.length)) return;
  const short = l => esc(l.replace(' 영어 모의고사', '').replace(/ 분석노트$/, ''));
  const el = document.createElement('section');
  el.className = 'card my-notes';
  el.innerHTML = `<h2>📦 내 분석노트 요청</h2>` +
    (m.ready.length ? `<p class="mn-ready"><b>준비됐어요 ${m.ready.length}개</b> · ${m.ready.slice(0, 3).map(x => short(x.label)).join(', ')}${m.ready.length > 3 ? ' 외' : ''}</p>
      <p><a class="btn btn-gold" href="/notes/#note-req">받으러 가기 →</a> <span class="meta">하루 모의고사 2개 · 부교재 1개씩 받아요</span></p>` : '') +
    (m.making.length ? `<p class="meta">원장님이 만드는 중 ${m.making.length}개 · ${m.making.slice(0, 3).map(short).join(', ')}${m.making.length > 3 ? ' 외' : ''}</p>` : '') +
    pushAsk(m.making.length ? '완성되면 알림으로 바로 알려 드릴까요?' : '새 분석노트가 올라오면 알려 드릴까요?');
  hero.after(el);
}

async function noteRequest(user) {
  const card = document.getElementById('note-req');
  if (!card) return;
  const qs = new URLSearchParams(location.search);
  const d = { y: qs.get('y') || card.dataset.y, m: qs.get('m') || card.dataset.m, g: qs.get('g') || card.dataset.g, book: qs.get('book') }; // 회차·교재 미리 채움
  let startBook = d.book && NOTE_BOOKS.includes(d.book);
  const isKakao = user && ((user.app_metadata?.providers || [user.app_metadata?.provider]).includes('kakao'));
  const head = `<h2>분석노트 요청</h2>
    <p class="muted">원하는 문항의 분석노트를 <b>카카오톡으로 바로</b> 보내드려요. 요청과 받기 모두 <b>하루 모의고사 2개 · 부교재 1개</b>까지예요. 받은 링크는 <b>24시간</b> 동안 열 수 있어요.</p>
    <p class="meta"><b>받는 방법:</b> 번호를 <b>하나씩</b> 골라 받아요. 모의고사는 하나를 받은 뒤 <b>"다른 번호 받기"</b>를 눌러 두 번째 번호를 받을 수 있어요.</p>
    <p class="meta">아직 없는 자료는 원장님이 1~2일 안에 만들어요. 완성되면 <b>처음 요청한 1개는 카톡으로 자동</b> 보내 드리고, 나머지는 다시 로그인했을 때 이 칸 위 <b>"요청하신 자료가 준비됐어요"</b>에서 받아요.</p>
    <div id="nr-ready"></div>`;

  if (!isKakao) {
    card.innerHTML = head + `<p class="muted">카카오로 로그인한 회원만 요청할 수 있어요.</p>${loginButtons()}`;
    return;
  }

  // 오늘 받은 기록 (종류별 개수)
  const kst = new Date(Date.now() + 9 * 3600e3);
  const dayStart = new Date(Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate()) - 9 * 3600e3).toISOString();
  // 내 기록만 (관리자 계정은 모든 회원 기록을 볼 수 있어서, 거르지 않으면 남의 받은 개수까지 세어 요청 칸이 사라짐)
  const { data: todayList } = await sb.from('note_orders').select('kind,label,link_token,expires_at,kakao_sent')
    .eq('user_id', user.id).eq('status', 'sent').gte('created_at', dayStart).order('created_at', { ascending: false });
  const used = { moe: 0, book: 0 };
  (todayList || []).forEach(o => { used[o.kind] = (used[o.kind] || 0) + 1; });
  const leftOf = k => Math.max(0, NOTE_LIMIT[k] - used[k]);
  const gotHtml = (todayList || []).length ? `<div class="info-box"><b>오늘 받은 분석노트</b>` + todayList.map(o => `
      <div class="row between mt" style="gap:8px;flex-wrap:wrap"><span>${esc(o.label)}</span>
      <a class="btn btn-gold btn-sm" href="/get/?t=${o.link_token}" target="_blank" rel="noopener">열기</a></div>`).join('') +
    `<p class="meta mt">오늘 남은 횟수: 모의고사 <b>${leftOf('moe')}개</b> · 부교재 <b>${leftOf('book')}개</b> · 링크는 받은 뒤 24시간 동안 열려요.</p></div>` : '';
  if (!leftOf('moe') && !leftOf('book')) {
    card.innerHTML = head + gotHtml + `<p class="meta mt">오늘 받을 수 있는 분석노트를 모두 받았어요. ${nextResetText()}.</p>` + pushAsk('새 분석노트가 올라오면 알려 드릴까요?');
    showReady(used);
    return;
  }

  if (!startBook && !leftOf('moe') && leftOf('book') && !card.dataset.y) startBook = true;
  const y0 = new Date().getFullYear();
  const opt = (arr, sel) => arr.map(v => `<option value="${v}"${String(v) === String(sel) ? ' selected' : ''}>${v}</option>`).join('');
  const range = (a, b) => Array.from({ length: b - a + 1 }, (_, i) => a + i);
  const bcfg = b => NOTE_BOOK_CFG[b] || { u: '강', max: 30, n: 10 };
  const curBook = () => (document.getElementById('nr-b') || {}).value || d.book || NOTE_BOOKS[0];
  const numOpts = k => {
    if (k !== 'book') return opt(range(30, 40), +qs.get('n') >= 30 && +qs.get('n') <= 40 ? +qs.get('n') : 30); // 모의고사는 30~40번만 요청 (나머지는 페이지에서 바로 보기)
    const c = bcfg(curBook()), qn = qs.get('n'); // 주소의 번호(나도 받기)는 같은 교재일 때만
    const z = zeroName(curBook());
    const sel = qn !== null && curBook() === d.book && (+qn === 0 ? !!z : +qn >= (c.from || 1) && +qn <= c.n) ? +qn : (c.from || 1);
    return (z ? `<option value="0"${sel === 0 ? ' selected' : ''}>${z}</option>` : '') + opt(range(c.from || 1, c.n), sel);
  };
  card.innerHTML = head + gotHtml + `
    <div class="tabs mt"><button class="tab${startBook ? '' : ' on'}" data-k="moe">모의고사</button><button class="tab${startBook ? ' on' : ''}" data-k="book">부교재</button></div>
    <div id="nr-moe" class="row"${startBook ? ' style="display:none"' : ''}>
      <select id="nr-y">${opt(range(2020, y0).reverse(), d.y || y0)}</select>
      <select id="nr-m">${opt([3, 4, 5, 6, 7, 9, 10, 11], d.m || 9)}</select><span>월</span>
      <select id="nr-g">${opt([1, 2, 3], d.g || 1)}</select><span>학년 영어</span>
    </div>
    <div id="nr-book" class="row"${startBook ? '' : ' style="display:none"'}>
      <select id="nr-b">${opt(NOTE_BOOKS, d.book)}</select>
      <select id="nr-u">${opt(range(1, bcfg(startBook ? d.book : NOTE_BOOKS[0]).max), startBook && +qs.get('unit') ? +qs.get('unit') : 1)}</select><span id="nr-ul">${bcfg(startBook ? d.book : NOTE_BOOKS[0]).u}</span>
    </div>
    <div class="row mt"><select id="nr-n">${numOpts(startBook ? 'book' : 'moe')}</select><span id="nr-nl">${startBook ? '' : '번 '}분석노트</span>
      <button class="btn btn-navy" id="nr-go">카톡으로 받기</button></div>
    <p class="meta mt" id="nr-preview"></p>
    <p class="meta">부교재 분석노트 소개·샘플·구매는 <a href="/books/">부교재 요청방 →</a></p>`;

  let kind = startBook ? 'book' : 'moe';
  const $v = id => document.getElementById(id).value;
  const preview = () => {
    const n = $v('nr-n');
    document.getElementById('nr-preview').textContent = kind === 'moe'
      ? `요청: ${$v('nr-y')}년 ${$v('nr-m')}월 고${$v('nr-g')} 영어 모의고사 ${n}번 분석노트`
      : `요청: ${$v('nr-b')} ${$v('nr-u')}${bcfg($v('nr-b')).u} ${n === '0' ? zeroName($v('nr-b')) : n + '번'} 분석노트`;
  };
  card.querySelectorAll('.tab').forEach(t => t.onclick = () => {
    kind = t.dataset.k;
    card.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === t));
    document.getElementById('nr-moe').style.display = kind === 'moe' ? '' : 'none';
    document.getElementById('nr-book').style.display = kind === 'book' ? '' : 'none';
    document.getElementById('nr-n').innerHTML = numOpts(kind);
    document.getElementById('nr-nl').textContent = kind === 'book' ? '분석노트' : '번 분석노트';
    preview();
  });
  card.querySelectorAll('select').forEach(s => s.onchange = preview);
  // 페이지의 주황 번호 버튼(30~40번)을 누르면 요청 칸에 그 번호를 바로 선택
  document.querySelectorAll('a.nb.req[data-n]').forEach(a => a.addEventListener('click', () => {
    if (kind !== 'moe') card.querySelector('.tab[data-k="moe"]').click();
    document.getElementById('nr-n').value = a.dataset.n; preview();
  }));
  document.getElementById('nr-b').onchange = () => { // 교재를 바꾸면 강/회 범위와 번호 목록도 바꿈
    const c = bcfg($v('nr-b'));
    document.getElementById('nr-u').innerHTML = opt(range(1, c.max), 1);
    document.getElementById('nr-ul').textContent = c.u;
    document.getElementById('nr-n').innerHTML = numOpts('book');
    preview();
  };
  preview();

  const body = () => kind === 'moe'
    ? { kind, y: +$v('nr-y'), m: +$v('nr-m'), g: +$v('nr-g'), n: +$v('nr-n') }
    : { kind, book: $v('nr-b'), unit: +$v('nr-u'), n: +$v('nr-n') };

  document.getElementById('nr-go').onclick = () => send(body());
  showReady(used);

  // 카카오 메시지 권한을 받으러 다녀온 경우 이어서 요청
  try {
    const pending = sessionStorage.getItem('note-pending');
    if (pending) { sessionStorage.removeItem('note-pending'); send(JSON.parse(pending), true); }
  } catch (e) { /* 저장소 사용 불가 */ }

  // 예전에 요청했지만 그때 없던 자료가 지금 준비됐으면 알림 (하루 1개씩 받기)
  async function showReady(used) {
    const slot = document.getElementById('nr-ready');
    if (!slot) return;
    const m = await myNotes(user);
    if (!m || (!m.ready.length && !m.making.length)) return;
    const list = m.ready;
    const left = { moe: NOTE_LIMIT.moe - (used.moe || 0), book: NOTE_LIMIT.book - (used.book || 0) };
    const ok = list.map(x => left[x.kind]-- > 0);  // 오늘 남은 횟수만큼만 '받기', 나머지는 '내일 받기'
    const canGet = x => ok[list.indexOf(x)];
    const later = ok.filter(v => !v).length;
    slot.innerHTML = (list.length ? `<div class="ready-box"><b>요청하신 자료가 준비됐어요</b><ul>` + list.map((x, i) =>
      `<li><span>${esc(x.label)}</span>${canGet(x) ? `<button class="btn btn-gold btn-sm" data-i="${i}">받기</button>` : '<span class="meta" style="white-space:nowrap">내일 받기</span>'}</li>`).join('') +
      `</ul><p class="meta">하루에 모의고사 2개 · 부교재 1개까지 받을 수 있어요.${later ? ` 남은 ${later}개는 ${nextResetText()}.` : ''}</p>` +
      (later ? pushAsk('내일 잊지 않게, 새 자료 소식을 알림으로 받아 볼까요?') : '') + `</div>` : '') +
      (m.making.length ? `<div class="making-box"><b>원장님이 만드는 중 ${m.making.length}개</b><ul>${m.making.map(l => `<li>${esc(l)}</li>`).join('')}</ul>
        <p class="meta">완성되면 이 칸 위 '준비됐어요'에 나타나요. (처음 요청한 1개는 카톡으로 자동 발송)</p>${later ? '' : pushAsk('완성되면 알림으로 바로 알려 드릴까요?')}</div>` : '');
    slot.querySelectorAll('button[data-i]').forEach(btn => btn.onclick = () => {
      const x = list[+btn.dataset.i];
      if (!document.getElementById('nr-go')) { // 받은 직후 화면에서 누르면 요청 칸을 다시 열고 이어서 받기
        try { sessionStorage.setItem('note-pending', JSON.stringify({ kind: x.kind, ...x.query })); } catch (e) { /* 무시 */ }
        return location.reload();
      }
      slot.innerHTML = '';
      send({ kind: x.kind, ...x.query });
    });
  }

  async function send(b, retried) {
    const btn = document.getElementById('nr-go'); btn.disabled = true; btn.textContent = '찾는 중...';
    const { data: { session } } = await sb.auth.getSession();
    if (!session.provider_token && !retried) {
      // 카톡 발송에 필요한 카카오 권한(메시지 전송)을 받아옴 → 돌아오면 자동으로 이어서 요청
      try { sessionStorage.setItem('note-pending', JSON.stringify(b)); } catch (e) { /* 무시 */ }
      return login('kakao', 'talk_message');
    }
    const cbox = document.getElementById('comments');
    let r = {};
    try {
      const res = await fetch(`${SUPABASE_URL}/functions/v1/note-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', apikey: SUPABASE_KEY, Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ ...b, kakao_token: session.provider_token || '', page_key: cbox ? cbox.dataset.pageKey : 'notes', page_title: cbox ? cbox.dataset.pageTitle : '분석노트 요청' })
      });
      r = await res.json();
    } catch (e) { r = { error: '요청 중 오류가 났어요. 잠시 후 다시 시도해 주세요.' }; }
    btn.disabled = false; btn.textContent = '카톡으로 받기';

    const box = document.getElementById('nr-preview');
    if (r.error) { box.innerHTML = `<span style="color:var(--danger)">${esc(r.error)}</span>`; return; }
    if (r.missing) {
      const d = new Date(Date.now() + 2 * 86400e3);
      const when = `${d.getMonth() + 1}월 ${d.getDate()}일(${'일월화수목금토'[d.getDay()]})`;
      box.innerHTML = `<b>${esc(r.label)}</b>는 지금 원장님이 준비하고 있어요. 1~2일 뒤(${when}쯤) 다시 로그인하면 이 칸 위에 <b>"준비됐어요"</b> 알림이 떠요. 그때 받기를 눌러 주세요. (오늘 요청 횟수는 차감되지 않아요)<br><span class="meta">아래 댓글 창에도 요청이 접수됐다고 남겨 두었어요.</span>` + pushAsk('완성되면 알림으로 바로 알려 드릴까요?');
      if (window.reloadComments) window.reloadComments();
      return;
    }
    card.innerHTML = head + `<div class="info-box"><b>${esc(r.label)}</b>
      ${r.kakao ? '를 카카오톡 <b>\'나와의 채팅\'</b>으로 보냈어요!' : '가 준비됐어요. (카톡 발송이 안 돼서 아래 버튼으로 바로 열어 주세요)'}
      <br><span class="meta">링크는 ${fmtDate(r.expires_at)}까지(24시간) 열려요.</span>
      <p class="mt"><a class="btn btn-gold btn-sm" href="${esc(r.link)}" target="_blank" rel="noopener">지금 열기</a></p>
      ${r.left && (r.left.moe > 0 || r.left.book > 0) ? `<p class="meta mt">오늘 더 받을 수 있어요: 모의고사 ${r.left.moe}개 · 부교재 ${r.left.book}개 <a href="#" onclick="location.reload();return false"><b>다른 번호 받기 →</b></a></p>` : `<p class="meta mt">오늘 받을 수 있는 분석노트를 모두 받았어요. ${nextResetText()}.</p>`}</div>` + pushAsk('다음 분석노트가 올라오면 바로 알려 드릴까요?');
    showReady({ ...used, [b.kind]: (used[b.kind] || 0) + 1 });
  }
}

/* ---------- 학교별 내신 분석 (코코스 학원생 전용): 카카오 로그인 → 인증 신청 → 원장님 승인 → 분석 글 ---------- */
async function naesinMember(user) {
  const box = document.getElementById('ns-member');
  if (!box) return;
  const school = box.dataset.school;
  const schools = JSON.parse(box.dataset.schools || '[]');
  const short = Object.fromEntries(schools);
  const head = '<h2>🔒 학원생 전용 분석</h2>';
  if (!user) return; // 로그인 전: 빌드 때 넣은 이용 방법·로그인 버튼 그대로
  const grades = ['중1', '중2', '중3', '고1', '고2', '고3'];
  const opt = (v, t, sel) => `<option value="${esc(v)}"${sel ? ' selected' : ''}>${esc(t)}</option>`;
  function form(m, again) {
    box.innerHTML = head + `${again ? '<p class="info-box">신청이 승인되지 않았어요. 이름·학교를 확인하고 다시 신청해 주세요. 궁금하면 원장님께 말씀해 주세요.</p>' : '<p>코코스학원 학생이면 아래 정보를 적어 <b>학원생 인증</b>을 신청해 주세요. 원장님이 확인하고 승인해요.</p>'}
      <div class="ns-form">
        <label>이름 <input id="ns-name" maxlength="20" placeholder="실명" value="${esc(m?.name || displayName(user) || '')}"></label>
        <label>학교 <select id="ns-school">${schools.map(([v, t]) => opt(t, t, (m?.school || short[school]) === t)).join('')}${opt('기타', '기타', m?.school === '기타')}</select></label>
        <label>학년 <select id="ns-grade">${grades.map(g => opt(g, g, m?.grade === g)).join('')}</select></label>
        <button type="button" class="btn btn-gold" id="ns-go">학원생 인증 신청</button>
      </div>`;
    document.getElementById('ns-go').onclick = async () => {
      const row = { name: document.getElementById('ns-name').value.trim(), school: document.getElementById('ns-school').value, grade: document.getElementById('ns-grade').value };
      if (row.name.length < 2) return toast('이름을 2글자 이상 적어 주세요.');
      const btn = document.getElementById('ns-go'); btn.disabled = true;
      const { error } = again
        ? await sb.from('naesin_members').update({ ...row, status: 'pending' }).eq('user_id', user.id)
        : await sb.from('naesin_members').insert(row);
      if (error) { btn.disabled = false; return toast('신청 오류: ' + error.message); }
      toast('신청했어요. 원장님이 승인하면 바로 볼 수 있어요.');
      naesinMember(user);
    };
  }
  async function posts() {
    let q = sb.from('naesin_posts').select('id,school,title,body,items,created_at,updated_at').eq('published', true).order('created_at', { ascending: false });
    if (school) q = q.eq('school', school);
    const { data, error } = await q;
    if (error) { box.innerHTML = head + '<p class="muted">분석을 불러오지 못했어요. 잠시 후 다시 열어 주세요.</p>'; return; }
    const list = data || [];
    if (!school) {
      const cnt = {}; list.forEach(p => (cnt[p.school] = (cnt[p.school] || 0) + 1));
      box.innerHTML = head + '<p class="ok-line">✅ 학원생 인증 완료. 학교를 골라 분석을 보세요.</p><div class="chips">'
        + schools.map(([v, t]) => `<a class="chip" href="/naesin/${esc(v)}/">${esc(t)}<small>${cnt[v] ? '분석 ' + cnt[v] + '개' : '준비 중'}</small></a>`).join('') + '</div>';
      return;
    }
    box.innerHTML = head + '<p class="ok-line">✅ 학원생 인증 완료</p>' + (list.length
      ? list.map((p, i) => `<details class="ns-post"${i === 0 ? ' open' : ''}><summary><b>${esc(p.title)}</b><span class="meta">${fmtDate(p.updated_at || p.created_at)}</span></summary><div class="ns-body">${p.items ? nsExamHTML(p) : p.body}</div></details>`).join('')
      : '<p class="muted">이 학교 분석을 준비하고 있어요. 시험이 끝나면 차례대로 올라와요.</p>')
      + '<p class="muted">분석 내용은 코코스 학원생 수업용이에요. 캡처·외부 공유는 하지 말아 주세요.</p>';
  }
  const { data: isAdmin } = await sb.rpc('is_admin');
  if (isAdmin) return posts().then(nsBind);
  const { data: m } = await sb.from('naesin_members').select('name,school,grade,status,created_at').eq('user_id', user.id).maybeSingle();
  if (!m) return form(null, false);
  if (m.status === 'rejected') return form(m, true);
  if (m.status === 'pending') {
    box.innerHTML = head + `<p class="info-box">⏳ <b>${esc(m.name)}</b> (${esc(m.school)} ${esc(m.grade)}) 학원생 인증을 신청했어요. 원장님이 확인하면 이 칸에서 바로 분석을 볼 수 있어요.<br><span class="meta">신청: ${fmtDate(m.created_at)}</span></p>`;
    return;
  }
  return posts().then(nsBind);
}

/* 내신 분석 한 시험: 총평(body) + 문항별 카드(items). 학생은 자기 시험지를 펴 놓고 근거 위치를 따라가며 다시 풀어요.
   틀린 번호를 고르면 그 문항만 남기고, '학습지 인쇄'로 개인별 확인 학습지를 만들어요. */
function nsExamHTML(p) {
  const it = p.items || [];
  const li = a => (a || []).map(x => `<li>${x}</li>`).join('');
  const card = q => `<section class="nq" data-n="${esc(q.n)}">
    <div class="nq-h"><b>${esc(q.n)}${/^\d+$/.test(q.n) ? '번' : ''}</b><span>${esc(q.type)}</span><span class="meta">${esc(q.points)}</span>${q.answer.length <= 3 ? `<span class="nq-ans">정답 ${esc(q.answer)}</span>` : ''}</div>
    ${q.answer.length > 3 ? `<div class="nq-model"><b>모범 답안</b> ${esc(q.answer)}</div>` : ''}
    ${q.where ? `<div class="nq-where">📄 <b>시험지에서 볼 곳</b> ${q.where}</div>` : ''}
    ${q.steps ? `<h4>풀이 흐름</h4><ol>${li(q.steps)}</ol>` : ''}
    ${q.choices ? `<h4>선택지 판단</h4><table class="nq-ch">${q.choices.map(([c, ok, why]) => `<tr class="${String(c).trim().startsWith(q.answer) ? 'bad' : ''}"><td>${c}</td><td>${esc(ok)}</td><td>${why}</td></tr>`).join('')}</table>` : ''}
    ${q.points_more ? `<h4>꼭 알아 둘 문법·어휘</h4><ul>${li(q.points_more)}</ul>` : ''}
    ${q.checks ? `<h4>✍️ 확인 문제 <span class="meta">원장님이 새로 만든 문제예요</span></h4><ol class="nq-checks">${q.checks.map(c => `<li>${c.q}<details><summary>정답·해설</summary>${c.a}</details></li>`).join('')}</ol>` : ''}
    ${q.next ? `<div class="nq-next">🎯 <b>다음 시험 대비</b> ${q.next}</div>` : ''}
  </section>`;
  return `${p.body || ''}
    <div class="nq-pick no-print"><b>틀린 번호만 보기</b> <span class="meta">번호를 누르면 그 문항만 남아요. 여러 개 고를 수 있어요.</span>
      <div class="nq-nums">${it.map(q => `<button type="button" class="nq-num" data-n="${esc(q.n)}">${esc(q.n.replace('논술형 ', '서'))}</button>`).join('')}</div>
      <p><button type="button" class="btn btn-line btn-sm nq-all">전체 보기</button> <button type="button" class="btn btn-gold btn-sm nq-print">🖨️ 확인 학습지 인쇄</button></p></div>
    <div class="nq-list">${it.map(card).join('')}</div>`;
}
function nsBind() {
  document.querySelectorAll('.ns-body').forEach(body => {
    const nums = body.querySelectorAll('.nq-num'), cards = body.querySelectorAll('.nq');
    if (!nums.length) return;
    const sel = new Set();
    const apply = () => cards.forEach(c => (c.hidden = sel.size > 0 && !sel.has(c.dataset.n)));
    nums.forEach(b => (b.onclick = () => { sel.has(b.dataset.n) ? sel.delete(b.dataset.n) : sel.add(b.dataset.n); b.classList.toggle('on'); apply(); }));
    body.querySelector('.nq-all').onclick = () => { sel.clear(); nums.forEach(b => b.classList.remove('on')); apply(); };
    body.querySelector('.nq-print').onclick = () => { body.closest('details').open = true; body.querySelectorAll('.nq-checks details').forEach(d => (d.open = false)); document.body.classList.add('ns-printing'); print(); document.body.classList.remove('ns-printing'); };
  });
}
