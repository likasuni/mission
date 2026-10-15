/* =========================================
   자료실 페이지 공통: 로그인 표시 + 페이지 댓글
   (댓글은 어느 페이지에 달든 미션 개수에 합산)
   ========================================= */
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
})();
