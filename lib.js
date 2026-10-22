/* =========================================
   자료실 페이지 공통: 로그인 표시 + 페이지 댓글 + 분석노트 요청
   - 댓글은 어느 페이지에 달든 미션 개수에 합산
   - 분석노트 요청: 카카오 회원, 하루 모의고사 2개 · 부교재 1개, 24시간 링크를 카톡으로 자동 발송
   ========================================= */
// 부교재 목록: 이름은 드라이브 '부교재 분석노트' 안 폴더 이름과 같게 (note-request 함수의 BOOKS, build.py BOOKS와 같게)
// u: 단위(강/회), max: 마지막 강·회, n: 문항 수, gw: Gateway 있음
const NOTE_BOOK_CFG = {
  '수능특강 라이트': { u: '강', max: 22, n: 10, gw: true },
  '리딩파워 기본': { u: '강', max: 30, n: 10 },
  '리딩파워 완성': { u: '강', max: 30, n: 10 },
  '올림포스 영어독해 기본1': { u: '강', max: 30, n: 10 },
  '하루 6개 1등급 모의고사 고1': { u: '회', max: 40, n: 6 },
  '하루 6개 1등급 모의고사 고2': { u: '회', max: 40, n: 6 },
  '올림포스 전국연합학력평가 기출문제집 고1': { u: '회', max: 30, from: 18, n: 45 },
  '올림포스 전국연합학력평가 기출문제집 고2': { u: '회', max: 30, from: 18, n: 45 },
};
const NOTE_BOOKS = Object.keys(NOTE_BOOK_CFG);
const NOTE_LIMIT = { moe: 2, book: 1 }; // 하루에 받을 수 있는 개수 (note-request 함수 LIMIT 와 같게)

(async function () {
  const user = await getUser();
  renderAuth(user);
  noteRequest(user);
  recentComments();

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
    else if ((m = t.match(/^(.+) (\d+)(?:강|회) (?:Gateway|(\d+)번)$/))) q = `?book=${encodeURIComponent(m[1])}&unit=${m[2]}&n=${m[3] || 0}`;
    return `/${c.page_key}/${q}#note-req`;
  };
  const short = c => c.content.replace('[자료 요청] ', '').replace(' 분석노트 부탁드려요.', '').replace(' 영어 모의고사', '');
  const shown = { pre: 6, rdy: 6, cmt: 3 };
  let cache = null, gf = 'all';  // gf: 학년 필터 (all·1·2·3·b=부교재)
  const gradeOf = c => { const m = c.content.match(/ 고(\d) /); return m ? m[1] : 'b'; };
  function reqItem(c) {
    const done = isDone(c), ready = isReady(c);
    return `<li class="rq${done ? ' ok' : ready ? ' rd' : ''}"><span class="rq-st">${done ? '카톡 발송' : ready ? '준비 완료' : '진행 중'}</span>
      <span class="rq-tx"><b>${esc(short(c))}</b><span class="meta">${esc(maskName(c.author_name))} · ${ago(c.created_at)}</span></span>
      ${c.page_key ? `<a class="rq-go" href="${esc(reqLink(c))}"${ready ? ' title="요청하면 기다리지 않고 바로 카톡으로 받아요"' : ''}>나도 받기</a>` : ''}</li>`;
  }
  function cmtItem(c) {
    const own = OWNER_IDS.includes(c.user_id);
    return `<div class="rc-item${own ? ' own' : ''}">
        <div class="rc-av">${own ? '리' : esc(maskName(c.author_name)[0])}</div>
        <div class="rc-bd">
          <div class="rc-nm"><b>${own ? '리카수니 원장' : esc(maskName(c.author_name))}</b>${own ? '<span class="rc-badge">운영자</span>' : ''}<span class="meta">${ago(c.created_at)}</span></div>
          <p class="rc-tx">${esc(c.content.length > 80 ? c.content.slice(0, 80) + '...' : c.content)}</p>
          ${c.reply ? `<div class="rc-rp"><b>리카수니 원장</b> ${esc(c.reply.length > 70 ? c.reply.slice(0, 70) + '...' : c.reply)}</div>` : ''}
          ${c.page_key ? `<a class="rc-pg" href="/${esc(c.page_key)}/#comments">${esc(c.page_title || '글 보기')} →</a>` : ''}
        </div>
      </div>`;
  }
  const more = (key, total) => total > shown[key] ? `<button class="rc-more" data-k="${key}">더보기 (${total - shown[key]}개)</button>` : '';
  function render() {
    const all = cache || [];
    const reqs = all.filter(isReq), cm = all.filter(c => !isReq(c));
    const cnt = k => k === 'all' ? reqs.length : reqs.filter(c => gradeOf(c) === k).length;
    const chips = [['all', '전체'], ['1', '고1'], ['2', '고2'], ['3', '고3'], ['b', '부교재']].filter(([k]) => k === 'all' || cnt(k))
      .map(([k, t]) => `<button class="rq-chip${gf === k ? ' on' : ''}" data-g="${k}">${t} <small>${cnt(k)}</small></button>`).join('');
    const rf = reqs.filter(c => gf === 'all' || gradeOf(c) === gf);
    const pre = rf.filter(c => !isDone(c) && !isReady(c));  // 만드는 중 (진행 중)
    const rdy = rf.filter(isReady).concat(rf.filter(isDone));  // 받을 수 있어요 (준비 완료 → 카톡 발송)
    const col = (cls, title, items, key, empty) => `<div class="rq-col ${cls}"><h3>${title} <span>${items.length}</span></h3><ul${shown[key] > 6 ? ' class="open"' : ''}>${items.slice(0, shown[key]).map(reqItem).join('') || `<li class="rq-empty">${empty}</li>`}</ul>${more(key, items.length)}</div>`;
    list.innerHTML = `<div class="rq-top"><h3 class="rc-sub">최근 자료 요청</h3><div class="rq-chips">${chips}</div></div>
      <div class="rq-cols">${col('', '만드는 중', pre, 'pre', '기다리는 요청이 없어요.')}${col('rd', '받을 수 있어요', rdy, 'rdy', '아직 준비된 자료가 없어요. 필요한 분석노트를 요청해 주세요.')}</div>
      <h3 class="rc-sub">최근 댓글</h3>
      <div class="rc-cm${shown.cmt > 3 ? ' open' : ''}">${cm.slice(0, shown.cmt).map(cmtItem).join('') || '<p class="muted">아직 댓글이 없어요. 자료 페이지 아래에서 첫 댓글을 남겨 주세요!</p>'}</div>${more('cmt', cm.length)}`;
    list.querySelectorAll('.rq-chip').forEach(b => b.onclick = () => { gf = b.dataset.g; shown.pre = shown.rdy = 6; render(); });
    list.querySelectorAll('.rc-more').forEach(btn => btn.onclick = () => { shown[btn.dataset.k] += 6; render(); });
  }
  async function load() {
    const { data } = await sb.from('comments')
      .select('id,user_id,author_name,content,created_at,reply,replied_at,page_key,page_title')
      .eq('approved', true).order('created_at', { ascending: false }).limit(80);
    cache = data || [];
    render();
  }
  load();
  setInterval(() => { if (!document.hidden) load(); }, 30000);
  // 이미 로그인한 회원에게는 로그인 버튼을 숨김
  getUser().then(u => { const b = box.querySelector('.rc-login'); if (u && b) b.remove(); }).catch(() => {});
}

/* ---------- 분석노트 요청 ---------- */
async function noteRequest(user) {
  const card = document.getElementById('note-req');
  if (!card) return;
  const qs = new URLSearchParams(location.search);
  const d = { y: qs.get('y') || card.dataset.y, m: qs.get('m') || card.dataset.m, g: qs.get('g') || card.dataset.g, book: qs.get('book') }; // 회차·교재 미리 채움
  let startBook = d.book && NOTE_BOOKS.includes(d.book);
  const isKakao = user && ((user.app_metadata?.providers || [user.app_metadata?.provider]).includes('kakao'));
  const head = `<h2>분석노트 요청</h2>
    <p class="muted">원하는 문항의 분석노트를 <b>카카오톡으로 바로</b> 보내드려요. <b>하루 모의고사 2개 · 부교재 1개</b>, 받은 링크는 <b>24시간</b> 동안 열 수 있어요.</p>
    <p class="meta"><b>받는 방법:</b> 번호를 <b>하나씩</b> 골라 받아요. 모의고사는 하나를 받은 뒤 <b>"다른 번호 받기"</b>를 눌러 두 번째 번호를 받을 수 있어요.</p>
    <p class="meta">아직 없는 자료는 원장님이 1~2일 안에 만들어요. 완성되면 다시 로그인했을 때 이 칸 위에 <b>"요청하신 자료가 준비됐어요"</b> 알림이 떠요.</p>
    <div id="nr-ready"></div>`;

  if (!isKakao) {
    card.innerHTML = head + `<p class="muted">카카오로 로그인한 회원만 요청할 수 있어요.</p>${loginButtons()}`;
    return;
  }

  // 오늘 받은 기록 (종류별 개수)
  const kst = new Date(Date.now() + 9 * 3600e3);
  const dayStart = new Date(Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate()) - 9 * 3600e3).toISOString();
  const { data: todayList } = await sb.from('note_orders').select('kind,label,link_token,expires_at,kakao_sent')
    .eq('status', 'sent').gte('created_at', dayStart).order('created_at', { ascending: false });
  const used = { moe: 0, book: 0 };
  (todayList || []).forEach(o => { used[o.kind] = (used[o.kind] || 0) + 1; });
  const leftOf = k => Math.max(0, NOTE_LIMIT[k] - used[k]);
  const gotHtml = (todayList || []).length ? `<div class="info-box"><b>오늘 받은 분석노트</b>` + todayList.map(o => `
      <div class="row between mt" style="gap:8px;flex-wrap:wrap"><span>${esc(o.label)}</span>
      <a class="btn btn-gold btn-sm" href="/get/?t=${o.link_token}" target="_blank" rel="noopener">열기</a></div>`).join('') +
    `<p class="meta mt">오늘 남은 횟수: 모의고사 <b>${leftOf('moe')}개</b> · 부교재 <b>${leftOf('book')}개</b> · 링크는 받은 뒤 24시간 동안 열려요.</p></div>` : '';
  if (!leftOf('moe') && !leftOf('book')) {
    card.innerHTML = head + gotHtml + '<p class="meta mt">오늘 받을 수 있는 분석노트를 모두 받았어요. 내일 다시 요청해 주세요.</p>';
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
    const sel = qn !== null && curBook() === d.book && (+qn === 0 ? c.gw : +qn >= (c.from || 1) && +qn <= c.n) ? +qn : (c.from || 1);
    return (c.gw ? `<option value="0"${sel === 0 ? ' selected' : ''}>Gateway</option>` : '') + opt(range(c.from || 1, c.n), sel);
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
      : `요청: ${$v('nr-b')} ${$v('nr-u')}${bcfg($v('nr-b')).u} ${n === '0' ? 'Gateway' : n + '번'} 분석노트`;
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
    const { data: { session } } = await sb.auth.getSession();
    if (!slot || !session) return;
    let r = {};
    try {
      const res = await fetch(`${SUPABASE_URL}/functions/v1/note-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', apikey: SUPABASE_KEY, Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ kind: 'check' })
      });
      r = await res.json();
    } catch (e) { return; }
    const list = r.ready || [];
    if (!list.length) return;
    slot.innerHTML = `<div class="ready-box"><b>요청하신 자료가 준비됐어요</b><ul>` + list.map((x, i) =>
      `<li><span>${esc(x.label)}</span>${NOTE_LIMIT[x.kind] - (used[x.kind] || 0) > 0 ? `<button class="btn btn-gold btn-sm" data-i="${i}">받기</button>` : '<span class="meta">내일 받기</span>'}</li>`).join('') +
      `</ul><p class="meta">하루에 모의고사 2개 · 부교재 1개까지 받을 수 있어요. 남은 자료는 내일 다시 와서 받아 주세요.</p></div>`;
    slot.querySelectorAll('button[data-i]').forEach(btn => btn.onclick = () => {
      const x = list[+btn.dataset.i];
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
      box.innerHTML = `<b>${esc(r.label)}</b>는 지금 원장님이 준비하고 있어요. 1~2일 뒤(${when}쯤) 다시 로그인하면 이 칸 위에 <b>"준비됐어요"</b> 알림이 떠요. 그때 받기를 눌러 주세요. (오늘 요청 횟수는 차감되지 않아요)<br><span class="meta">아래 댓글 창에도 요청이 접수됐다고 남겨 두었어요.</span>`;
      if (window.reloadComments) window.reloadComments();
      return;
    }
    card.innerHTML = head + `<div class="info-box"><b>${esc(r.label)}</b>
      ${r.kakao ? '를 카카오톡 <b>\'나와의 채팅\'</b>으로 보냈어요!' : '가 준비됐어요. (카톡 발송이 안 돼서 아래 버튼으로 바로 열어 주세요)'}
      <br><span class="meta">링크는 ${fmtDate(r.expires_at)}까지(24시간) 열려요.</span>
      <p class="mt"><a class="btn btn-gold btn-sm" href="${esc(r.link)}" target="_blank" rel="noopener">지금 열기</a></p>
      ${r.left && (r.left.moe > 0 || r.left.book > 0) ? `<p class="meta mt">오늘 더 받을 수 있어요: 모의고사 ${r.left.moe}개 · 부교재 ${r.left.book}개 <a href="#" onclick="location.reload();return false"><b>다른 번호 받기 →</b></a></p>` : '<p class="meta mt">오늘 받을 수 있는 분석노트를 모두 받았어요.</p>'}</div>`;
  }
}
