/* =========================================
   자료실 페이지 공통: 로그인 표시 + 페이지 댓글
   (댓글은 어느 페이지에 달든 미션 개수에 합산)
   ========================================= */
const NOTE_DAYS = 7; // 승인 후 다운로드 가능 기간(일) — note-download 함수와 같게
(async function () {
  const user = await getUser();
  renderAuth(user);
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
      : `<p class="muted">로그인하면 질문을 남기고 댓글 미션에 참여할 수 있어요.</p>${loginButtons()}`;

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
  notes();

  /* ---------- 번호별 분석노트 신청 (회차 페이지당 1인 1개, 승인 후 다운로드) ---------- */
  async function notes() {
    const { data: files } = await sb.from('note_files').select('num,title,path').eq('page_key', key).order('num');
    if (!files || !files.length) return;
    let card = document.getElementById('notes');
    if (!card) {
      card = document.createElement('section');
      card.id = 'notes'; card.className = 'card mission';
      box.parentNode.insertBefore(card, box);
    }
    const nums = files.map(f => f.num).join(', ');
    let mine = null;
    if (user) {
      const { data } = await sb.from('note_requests').select('id,num,status,created_at,decided_at')
        .eq('page_key', key).neq('status', 'rejected').maybeSingle();
      mine = data;
    }
    let inner = '';
    if (!user) {
      inner = `<p class="muted">로그인 후 댓글로 신청하면 원하는 번호의 분석노트 PDF를 받을 수 있어요.</p>${loginButtons()}`;
    } else if (mine && mine.status === 'approved') {
      const until = new Date(new Date(mine.decided_at).getTime() + NOTE_DAYS * 86400000);
      inner = Date.now() > until
        ? `<p>⌛ <b>${mine.num}번 분석노트</b> 다운로드 기간(승인 후 ${NOTE_DAYS}일)이 끝났어요.</p>`
        : `<p>✅ <b>${mine.num}번 분석노트</b> 신청이 승인됐어요. <span class="meta">${fmtDate(until)}까지 받을 수 있어요.</span></p>
        <button class="btn btn-gold" id="ndl">${mine.num}번 PDF 다운로드</button>`;
    } else if (mine) {
      inner = `<p>⏳ <b>${mine.num}번 분석노트</b> 신청 완료! 원장님 확인 후 이 자리에 다운로드 버튼이 생겨요.</p>`;
    } else {
      inner = `<p class="muted">이 회차에서 <b>1인 1개 번호</b>를 신청할 수 있어요. 원하는 번호를 고르고, 그 문항에 대한 질문이나 학습 후기를 <b>20자 이상</b> 남겨주세요. 승인되면 PDF를 받을 수 있어요.</p>
        <div class="row mt"><select id="nnum">${files.map(f => `<option value="${f.num}">${f.num}번${f.title ? ' · ' + esc(f.title) : ''}</option>`).join('')}</select></div>
        <textarea id="nbody" class="mt" maxlength="1000" placeholder="예) 30번 빈칸 근거를 못 찾았어요. 분석노트로 구조를 다시 보고 싶어요."></textarea>
        <div class="row between mt"><span class="meta"><span id="ncount">0</span>자</span>
        <button class="btn btn-navy" id="nbtn">분석노트 신청</button></div>`;
    }
    card.innerHTML = `<h2>📘 번호별 분석노트 신청</h2><p class="meta">신청 가능 번호: ${nums}</p>${inner}`;
    const dl = document.getElementById('ndl');
    if (dl) dl.onclick = async () => {
      const f = files.find(x => x.num === mine.num);
      const fname = `${title} ${f.num}번 분석노트.pdf`;
      dl.disabled = true; dl.textContent = '받는 중...';
      try {
        if (f.path) {
          const { data, error } = await sb.storage.from('notes').createSignedUrl(f.path, 600, { download: fname });
          if (error) throw new Error(error.message);
          location.href = data.signedUrl;
        } else {
          const { data: { session } } = await sb.auth.getSession();
          const res = await fetch(`${SUPABASE_URL}/functions/v1/note-download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', apikey: SUPABASE_KEY, Authorization: `Bearer ${session.access_token}` },
            body: JSON.stringify({ page_key: key })
          });
          if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || res.status);
          const blob = await res.blob();
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob); a.download = fname;
          document.body.appendChild(a); a.click(); a.remove();
          setTimeout(() => URL.revokeObjectURL(a.href), 5000);
        }
      } catch (err) { toast('다운로드 오류: ' + err.message); }
      dl.disabled = false; dl.textContent = `${mine.num}번 PDF 다운로드`;
    };
    const t = document.getElementById('nbody');
    if (t) {
      t.oninput = () => (document.getElementById('ncount').textContent = t.value.trim().length);
      document.getElementById('nbtn').onclick = async () => {
        const num = Number(document.getElementById('nnum').value);
        const body = t.value.trim();
        if (body.length < 20) return toast('20자 이상 작성해 주세요.');
        const btn = document.getElementById('nbtn'); btn.disabled = true;
        const { data: c, error: e1 } = await sb.from('comments').insert({
          page_key: key, page_title: title, author_name: displayName(user), content: `[${num}번 분석노트 신청] ${body}`
        }).select('id').single();
        if (e1) { btn.disabled = false; return toast('등록 실패: ' + e1.message); }
        const { error: e2 } = await sb.from('note_requests').insert({ page_key: key, num, comment_id: c.id });
        if (e2) {
          btn.disabled = false;
          return toast(e2.code === '23505' ? '이 회차는 이미 신청하셨어요. (1인 1개)' : '신청 실패: ' + e2.message);
        }
        toast(`${num}번 분석노트 신청 완료! 승인 후 받을 수 있어요.`);
        notes(); load();
      };
    }
  }
})();
