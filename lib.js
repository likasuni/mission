/* =========================================
   자료실 페이지 공통: 로그인 표시 + 페이지 댓글 + 분석노트 요청
   - 댓글은 어느 페이지에 달든 미션 개수에 합산
   - 분석노트 요청: 카카오 회원, 1인 하루 1개, 24시간 링크를 카톡으로 자동 발송
   ========================================= */
const NOTE_BOOKS = ['수능특강 라이트']; // note-request 함수의 BOOKS와 같게

(async function () {
  const user = await getUser();
  renderAuth(user);
  noteRequest(user);

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
          <strong>${esc(c.author_name || '익명')}</strong>
          ${!c.approved ? '<span class="tag wait">승인 대기</span>' : ''}
          <span class="meta">${fmtDate(c.created_at)}</span>
        </div>
        <p class="body">${esc(c.content)}</p>
        ${c.reply ? `<div class="reply"><b>리카수니 원장</b><br>${esc(c.reply)}</div>` : ''}
      </div>`).join('') || '<p class="muted">첫 질문이나 학습 후기를 남겨주세요!</p>';

    const form = user ? `
      <p class="muted">질문·학습 후기를 <b>20자 이상</b> 남겨주세요. 승인된 댓글은 <a href="/mission/">댓글 미션</a> 개수에 합산돼요.</p>
      <textarea id="cbody" maxlength="1000" placeholder="예) 이 회차 31번이 어려웠는데 해설로 정리했어요. 빈칸 근거 찾는 연습을 더 해야겠어요."></textarea>
      <div class="row between mt"><span class="meta"><span id="ccount">0</span>자</span>
      <button class="btn btn-navy" id="cbtn">댓글 등록</button></div>`
      : `<p class="muted">카카오로 로그인하면 질문을 남기고 댓글 미션에 참여할 수 있어요.</p>${loginButtons()}`;

    box.innerHTML = `<h2>💬 질문·후기 <span class="meta">${list.filter(c => c.approved).length}</span></h2>${form}<div class="mt">${items}</div>`;
    if (user) {
      const t = document.getElementById('cbody');
      t.oninput = () => (document.getElementById('ccount').textContent = t.value.trim().length);
      document.getElementById('cbtn').onclick = submit;
    }
  }

  async function submit() {
    const content = document.getElementById('cbody').value.trim();
    if (content.length < 20) return toast('20자 이상 작성해 주세요.');
    const btn = document.getElementById('cbtn'); btn.disabled = true;
    const { error } = await sb.from('comments').insert({
      page_key: key, page_title: title, author_name: displayName(user), content
    });
    if (error) { btn.disabled = false; return toast('등록 실패: ' + error.message); }
    toast('등록됐어요! 승인 후 공개되고 미션에 반영돼요.');
    load();
  }
  load();
})();

/* ---------- 분석노트 요청 ---------- */
async function noteRequest(user) {
  const card = document.getElementById('note-req');
  if (!card) return;
  const d = card.dataset; // data-y, data-m, data-g 가 있으면 그 회차로 미리 채움
  const isKakao = user && ((user.app_metadata?.providers || [user.app_metadata?.provider]).includes('kakao'));
  const head = `<h2>📘 분석노트 요청</h2>
    <p class="muted">원하는 문항의 분석노트를 <b>카카오톡으로 바로</b> 보내드려요. <b>1인 하루 1개</b>, 받은 링크는 <b>24시간</b> 동안 열 수 있어요.</p>`;

  if (!isKakao) {
    card.innerHTML = head + `<p class="muted">카카오로 로그인한 회원만 요청할 수 있어요.</p>${loginButtons()}`;
    return;
  }

  // 오늘 받은 기록
  const kst = new Date(Date.now() + 9 * 3600e3);
  const dayStart = new Date(Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate()) - 9 * 3600e3).toISOString();
  const { data: today } = await sb.from('note_orders').select('label,status,link_token,expires_at,kakao_sent')
    .eq('status', 'sent').gte('created_at', dayStart).order('created_at', { ascending: false }).limit(1);
  if (today && today.length) {
    const o = today[0];
    card.innerHTML = head + `<div class="info-box">✅ 오늘은 <b>${esc(o.label)}</b>를 받았어요.<br>
      <span class="meta">${o.kakao_sent ? '카카오톡 \'나와의 채팅\'을 확인해 주세요. ' : ''}링크는 ${fmtDate(o.expires_at)}까지 열려요.</span>
      <p class="mt"><a class="btn btn-gold btn-sm" href="/get/?t=${o.link_token}" target="_blank" rel="noopener">지금 열기</a></p>
      <p class="meta">내일 다시 1개를 요청할 수 있어요.</p></div>`;
    return;
  }

  const y0 = new Date().getFullYear();
  const opt = (arr, sel) => arr.map(v => `<option value="${v}"${String(v) === String(sel) ? ' selected' : ''}>${v}</option>`).join('');
  const range = (a, b) => Array.from({ length: b - a + 1 }, (_, i) => a + i);
  card.innerHTML = head + `
    <div class="tabs mt"><button class="tab on" data-k="moe">모의고사</button><button class="tab" data-k="book">부교재</button></div>
    <div id="nr-moe" class="row">
      <select id="nr-y">${opt(range(2020, y0).reverse(), d.y || y0)}</select>
      <select id="nr-m">${opt([3, 4, 5, 6, 7, 9, 10, 11], d.m || 9)}</select><span>월</span>
      <select id="nr-g">${opt([1, 2, 3], d.g || 1)}</select><span>학년 영어</span>
    </div>
    <div id="nr-book" class="row" style="display:none">
      <select id="nr-b">${opt(NOTE_BOOKS)}</select>
      <select id="nr-u">${opt(range(1, 30), 1)}</select><span>강</span>
    </div>
    <div class="row mt"><select id="nr-n">${opt(range(1, 45), 30)}</select><span>번 분석노트</span>
      <button class="btn btn-navy" id="nr-go">카톡으로 받기</button></div>
    <p class="meta mt" id="nr-preview"></p>`;

  let kind = 'moe';
  const $v = id => document.getElementById(id).value;
  const preview = () => {
    document.getElementById('nr-preview').textContent = kind === 'moe'
      ? `요청: ${$v('nr-y')}년 ${$v('nr-m')}월 고${$v('nr-g')} 영어 모의고사 ${$v('nr-n')}번 분석노트`
      : `요청: ${$v('nr-b')} ${$v('nr-u')}강 ${$v('nr-n')}번 분석노트`;
  };
  card.querySelectorAll('.tab').forEach(t => t.onclick = () => {
    kind = t.dataset.k;
    card.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === t));
    document.getElementById('nr-moe').style.display = kind === 'moe' ? '' : 'none';
    document.getElementById('nr-book').style.display = kind === 'book' ? '' : 'none';
    preview();
  });
  card.querySelectorAll('select').forEach(s => s.onchange = preview);
  preview();

  const body = () => kind === 'moe'
    ? { kind, y: +$v('nr-y'), m: +$v('nr-m'), g: +$v('nr-g'), n: +$v('nr-n') }
    : { kind, book: $v('nr-b'), unit: +$v('nr-u'), n: +$v('nr-n') };

  document.getElementById('nr-go').onclick = () => send(body());

  // 카카오 메시지 권한을 받으러 다녀온 경우 이어서 요청
  try {
    const pending = sessionStorage.getItem('note-pending');
    if (pending) { sessionStorage.removeItem('note-pending'); send(JSON.parse(pending), true); }
  } catch (e) { /* 저장소 사용 불가 */ }

  async function send(b, retried) {
    const btn = document.getElementById('nr-go'); btn.disabled = true; btn.textContent = '찾는 중...';
    const { data: { session } } = await sb.auth.getSession();
    if (!session.provider_token && !retried) {
      // 카톡 발송에 필요한 카카오 권한(메시지 전송)을 받아옴 → 돌아오면 자동으로 이어서 요청
      try { sessionStorage.setItem('note-pending', JSON.stringify(b)); } catch (e) { /* 무시 */ }
      return login('kakao', 'talk_message');
    }
    let r = {};
    try {
      const res = await fetch(`${SUPABASE_URL}/functions/v1/note-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', apikey: SUPABASE_KEY, Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ ...b, kakao_token: session.provider_token || '' })
      });
      r = await res.json();
    } catch (e) { r = { error: '요청 중 오류가 났어요. 잠시 후 다시 시도해 주세요.' }; }
    btn.disabled = false; btn.textContent = '카톡으로 받기';

    const box = document.getElementById('nr-preview');
    if (r.error) { box.innerHTML = `<span style="color:var(--danger)">${esc(r.error)}</span>`; return; }
    if (r.missing) {
      const d = new Date(Date.now() + 2 * 86400e3);
      const when = `${d.getMonth() + 1}월 ${d.getDate()}일(${'일월화수목금토'[d.getDay()]})`;
      box.innerHTML = `📝 <b>${esc(r.label)}</b>는 지금 원장님이 준비하고 있어요. 자료 준비에 1~2일 걸리니 <b>${when} 이후에 다시 요청</b>해 주세요. (오늘 요청 횟수는 차감되지 않아요)`;
      return;
    }
    card.innerHTML = head + `<div class="info-box">✅ <b>${esc(r.label)}</b>
      ${r.kakao ? '를 카카오톡 <b>\'나와의 채팅\'</b>으로 보냈어요!' : '가 준비됐어요. (카톡 발송이 안 돼서 아래 버튼으로 바로 열어 주세요)'}
      <br><span class="meta">링크는 ${fmtDate(r.expires_at)}까지(24시간) 열려요.</span>
      <p class="mt"><a class="btn btn-gold btn-sm" href="${esc(r.link)}" target="_blank" rel="noopener">지금 열기</a></p></div>`;
  }
}
