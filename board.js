/* 리카수니 블로그(www.likasuni.com) '자료 요청 · 소통하기' 상자 — 블로그 위젯은 이 파일을 불러오기만 해요 (_tools/blogger_widgets/request-board.html).
   자료실을 고치면 이 파일만 바꾸면 블로그도 같이 바뀌어요. 자료실 첫 화면(lib.js recentComments·talkBoard)과 같은 규칙. */
(function () {
  var CSS = "/* 가젯 제목(관리용 이름)은 블로그 화면에서 숨김 */\n.widget:has(#lks-rc) > h2, .widget:has(#lks-rc) > h3, .widget:has(#lks-rc) > .title { display: none !important; }\n#lks-rc .lks-head { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }\n/* 자동광고가 머리 줄 안에 들어와도 제목을 밀지 않게: 광고는 맨 위 한 줄을 따로 차지 */\n#lks-rc .lks-head > :not(.lks-live):not(.lks-title) { flex: 0 0 100%; order: -1; max-width: 100%; }\n#lks-rc .lks-live i { width: 8px; height: 8px; border-radius: 50%; background: #4ade80; animation: lkspulse 1.6s infinite; }\n@keyframes lkspulse { 0% { box-shadow: 0 0 0 0 rgba(74,222,128,.7); } 70% { box-shadow: 0 0 0 8px rgba(74,222,128,0); } 100% { box-shadow: 0 0 0 0 rgba(74,222,128,0); } }\n#lks-rc .lks-rq { list-style: none; margin: 0; padding: 0; }\n#lks-rc .lks-rq li { display: flex; align-items: center; gap: 8px; padding: 7px 0; border-top: 1px dashed #ead9ad; font-size: 14px; margin: 0; }\n#lks-rc .lks-rq li:first-child { border-top: 0; }\n#lks-rc .lks-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: start; }\n#lks-rc .lks-cols .lks-rd .lks-rq li { border-top-color: #d3e0fb; }\n#lks-rc .lks-cols .lks-rd .lks-rq li:first-child { border-top: 0; }\n#lks-rc .lks-chip { border: 1px solid #e5d3a1; background: #fff; color: #7a4b00; border-radius: 999px; padding: 3px 11px; font-size: 13px; font-weight: 700; cursor: pointer; margin: 0 6px 6px 0; }\n#lks-rc .lks-chip.on { background: #7a4b00; border-color: #7a4b00; color: #fff; }\n#lks-rc a { text-decoration: none; }\n#lks-rc .lks-more { display: block; width: 100%; margin: 6px 0 4px; padding: 6px; border: 0; border-radius: 8px; background: rgba(30,58,138,.06); color: #1e3a8a; font-size: 13px; font-weight: 700; cursor: pointer; }\n@media (max-width: 640px) {\n  #lks-rc .lks-cols { grid-template-columns: 1fr; }\n  #lks-rc .lks-title { font-size: 16px !important; }\n}";
  var ROOTSTYLE = "box-sizing: border-box; width: 100%; max-width: 100%; overflow: hidden; margin: 20px 0; border: 2px solid #1e3a8a; border-radius: 16px; background: #fff; box-shadow: 0 8px 24px rgba(30,58,138,.12); font-family: 'Pretendard', 'Noto Sans KR', sans-serif; color: #1f2937; line-height: 1.5;";
  var INNER = "<div class=\"lks-head\" style=\"box-sizing: border-box; width: 100%; max-width: 100%; overflow: hidden; padding: 16px 20px; background: linear-gradient(135deg, #172554, #1e3a8a); color: #fff;\">\n    <span class=\"lks-live\" style=\"display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; background: rgba(255,255,255,.14); font-size: 12px; font-weight: 800; color: #fff;\"><i style=\"display: inline-block;\"></i>실시간</span>\n    <b class=\"lks-title\" style=\"color: #fff; font-size: 18px; font-weight: 800;\">자료 요청 · 소통하기</b>\n  </div>\n  <div style=\"box-sizing: border-box; width: 100%; max-width: 100%; overflow: hidden; padding: 4px 20px 10px;\">\n    <div style=\"box-sizing: border-box; width: 100%; max-width: 100%; overflow: hidden; margin: 12px 0 4px; padding: 8px 12px; border-radius: 10px; background: #fff8e6; border: 1px solid #f3d48a; color: #6b4e00; font-size: 13px;\">\n      없는 분석노트도 <b>요청</b>하면 원장님이 만들어 <b>카톡으로</b> 보내 드려요. 요청과 질문은 <a href=\"https://data.likasuni.com/\" style=\"color: #6b4e00; font-weight: 800; text-decoration: underline;\">리카수니 자료실</a>에서 할 수 있어요.\n    </div>\n    <div class=\"lks-list\" style=\"box-sizing: border-box; width: 100%; max-width: 100%; overflow: hidden;\"><p style=\"color: #8a93a8; font-size: 14px;\">불러오는 중...</p></div>\n  </div>";
(function () {
  var URL = 'https://iiyhmskvdjgstoikonwu.supabase.co', KEY = 'sb_publishable_JHxdlqWVh26TqD36jLflYQ_KoUmeuUj';
  var SITE = 'https://data.likasuni.com/';
  var OWNER_IDS = ['6363d675-9fa4-4539-af39-0028444f80f0']; // 원장님 카카오 계정
  var BOX = 'box-sizing: border-box; width: 100%; max-width: 100%; overflow: hidden;';
  var root = document.getElementById('lks-rc'); if (!root || root.getAttribute('data-on')) return;
  root.setAttribute('data-on', '1');
  var css = document.createElement('style'); css.textContent = CSS; document.head.appendChild(css);
  root.setAttribute('style', ROOTSTYLE);
  root.innerHTML = INNER;
  // 가젯 제목 숨기기 (:has 를 모르는 옛 브라우저용)
  var w = root.closest ? root.closest('.widget') : null;
  if (w) for (var j = 0; j < w.children.length; j++) { var ch = w.children[j]; if (/^H[23]$/.test(ch.tagName) || ch.classList.contains('title')) ch.style.display = 'none'; }
  var list = root.querySelector('.lks-list');
  var shown = { pre: 6, rdy: 6, cmt: 3 }, cache = [], talk = [], gf = 'all'; // gf: 학년 필터 (all·1·2·3·b=부교재)
  function gradeOf(c) { var m = c.content.match(/ 고(\d) /); return m ? m[1] : 'b'; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function mask(n) { n = String(n || '회원').trim(); if (n === '리카수니' || n.length < 2) return n; return n.length === 2 ? n[0] + '*' : n[0] + new Array(n.length - 1).join('*') + n[n.length - 1]; }
  function ago(t) {
    var m = Math.floor((Date.now() - new Date(t)) / 60000);
    if (m < 1) return '방금'; if (m < 60) return m + '분 전';
    var h = Math.floor(m / 60); if (h < 24) return h + '시간 전';
    var d = new Date(t); return (d.getMonth() + 1) + '월 ' + d.getDate() + '일';
  }
  function isReq(c) { return c.content.indexOf('[자료 요청]') === 0 && !/다시 요청해 주세요/.test(c.reply || ''); } // 연락이 안 돼 정리된 요청(3일)은 뺌
  // 상태 3단계 (자료실 lib.js 와 같게): 진행 중(주황, '접수했어요') → 준비 완료(파랑, '준비됐어요') → 카톡 발송(초록, '보내 드렸어요')
  function isDone(c) { return /보내 드렸어요/.test(c.reply || ''); }
  function isReady(c) { return !isDone(c) && /준비됐어요/.test(c.reply || ''); }
  // '나도 받기': 자료실 요청 칸에 같은 회차·번호가 미리 골라져 있게
  function reqLink(c) {
    var t = c.content.replace('[자료 요청] ', '').replace(' 분석노트 부탁드려요.', ''), q = '';
    var m = t.match(/^(\d{4})년 (\d{1,2})월 고(\d) 영어 모의고사 (\d+)번$/);
    if (m) q = '?y=' + m[1] + '&m=' + m[2] + '&g=' + m[3] + '&n=' + m[4];
    else if ((m = t.match(/^(.+) (\d+)(?:강|회) (?:Gateway|(\d+)번)$/))) q = '?book=' + encodeURIComponent(m[1]) + '&unit=' + m[2] + '&n=' + (m[3] || 0);
    return SITE + c.page_key + '/' + q + '#note-req';
  }
  // 미리보기 (자료실 notes/pv/index.json 에 있는 번호만): 모의고사 moe-g2-2026-10-37 · 부교재 bk-수능특강라이트-20-1
  var pv = {};
  fetch(SITE + 'notes/pv/index.json').then(function (r) { return r.ok ? r.json() : []; }).then(function (a) { pv = {}; a.forEach(function (k) { pv[k] = 1; }); render(); }).catch(function () {});
  function pvKey(c) {
    var t = c.content.replace('[자료 요청] ', '').replace(' 분석노트 부탁드려요.', '');
    var m = t.match(/^(\d{4})년 (\d{1,2})월 고(\d) 영어 모의고사 (\d+)번$/);
    if (m) return 'moe-g' + m[3] + '-' + m[1] + '-' + (+m[2]) + '-' + (+m[4]);
    m = t.match(/^(.+) (\d+)(?:강|회) (?:Gateway|예시문제|(\d+)번)$/);
    return m ? 'bk-' + m[1].replace(/ /g, '') + '-' + (+m[2]) + '-' + (+(m[3] || 0)) : '';
  }
  function showPreview(k, title, go) {
    var d = document.createElement('div');
    d.setAttribute('style', 'position: fixed; inset: 0; z-index: 99999; background: rgba(15,23,42,.55); display: flex; align-items: center; justify-content: center; padding: 16px;');
    d.innerHTML = '<div style="' + BOX + ' background: #fff; border-radius: 14px; max-width: 760px; max-height: 92vh; overflow: auto; padding: 14px 16px 16px; font-family: inherit;">' +
      '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 10px; color: #172554;"><b>' + esc(title) + ' 분석노트 미리보기</b><button type="button" data-x style="border: 0; background: #f1f5f9; border-radius: 8px; width: 34px; height: 34px; cursor: pointer;">✕</button></div>' +
      '<img src="' + SITE + 'notes/pv/' + encodeURIComponent(k) + '.jpg" alt="' + esc(title) + ' 분석노트 첫 쪽 미리보기" style="display: block; width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px;">' +
      '<p style="margin: 10px 0; font-size: 13px; color: #6b7280;">첫 쪽 윗부분만 보여 드려요. 전체 PDF는 리카수니 자료실에서 카카오로 로그인해 카톡으로 받아요.</p>' +
      '<a href="' + esc(go) + '" style="display: block; text-align: center; padding: 11px; border-radius: 10px; background: #1e3a8a; color: #fff; font-weight: 800;">나도 받기 →</a></div>';
    d.onclick = function (e) { if (e.target === d || e.target.hasAttribute('data-x')) d.remove(); };
    document.body.appendChild(d);
  }
  function short(c) { return c.content.replace('[자료 요청] ', '').replace(' 분석노트 부탁드려요.', '').replace(' 영어 모의고사', ''); }
  function reqItem(c) {
    var done = isDone(c), ready = isReady(c);
    var st = done ? ['카톡 발송', '#16a34a', '#a7dcb8', '#166534'] : ready ? ['준비 완료', '#2563eb', '#93b4f5', '#1d4ed8'] : ['진행 중', '#f59e0b', '#e5d3a1', '#7a4b00'];
    return '<li><span style="flex: none; padding: 2px 7px; border-radius: 6px; background: ' + st[1] + '; color: #fff; font-size: 11px; font-weight: 800;">' + st[0] + '</span>' +
      '<span style="flex: 1; min-width: 0; display: flex; flex-direction: column; line-height: 1.35;"><b style="font-weight: 700; overflow-wrap: anywhere;">' + esc(short(c)) + '</b>' +
      '<span style="font-size: 12px; color: #8a93a8;">' + esc(mask(c.author_name)) + ' · ' + ago(c.created_at) + '</span></span>' +
      ((ready || done) && pv[pvKey(c)] ? '<button type="button" class="lks-pv" data-pv="' + esc(pvKey(c)) + '" data-t="' + esc(short(c)) + '" data-go="' + esc(reqLink(c)) + '" style="flex: none; padding: 3px 8px; border-radius: 6px; background: #fff; border: 1px solid ' + st[2] + '; font-size: 12px; font-weight: 700; color: ' + st[3] + '; cursor: pointer;">미리보기</button>' : '') +
      (c.page_key ? '<a href="' + esc(reqLink(c)) + '"' + (ready ? ' title="요청하면 기다리지 않고 바로 카톡으로 받아요"' : '') + ' style="flex: none; padding: 3px 8px; border-radius: 6px; background: #fff; border: 1px solid ' + st[2] + '; font-size: 12px; font-weight: 700; color: ' + st[3] + ';">나도 받기</a>' : '') + '</li>';
  }
  // 소통하기 글 (talk_list: 비밀글은 내용이 비어 옴, 고정 공지가 맨 위)
  function talkItem(p) {
    var hidden = p.secret && p.content == null, nm = p.staff ? '리카수니 원장' : mask(p.author_name);
    var tx = hidden ? '비밀글이에요. 글쓴이와 원장님만 볼 수 있어요.' : (p.content.length > 120 ? p.content.slice(0, 120) + '...' : p.content);
    var rp = p.reply ? (p.reply.length > 120 ? p.reply.slice(0, 120) + '...' : p.reply) : '';
    var st = p.staff ? '' : '<span style="padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 800; ' + (p.reply ? 'background: #16a34a; color: #fff;' : 'background: #e5e7eb; color: #4b5563;') + '">' + (p.reply ? '답변 완료' : '답변 대기') + '</span>';
    return '<div style="' + BOX + ' padding: 11px ' + (p.pinned ? '12px; margin: 6px 0; border: 1px solid #f3d48a; border-radius: 10px; background: #fffbf0;' : '0; border-bottom: 1px solid #e5e7eb;') + '">' +
      '<div style="display: flex; gap: 6px 8px; align-items: center; flex-wrap: wrap; font-size: 14px;">' + (p.pinned ? '<span style="padding: 2px 8px; border-radius: 6px; background: #f59e0b; color: #fff; font-size: 11px; font-weight: 800;">📌 공지</span>' : '') + st + '<b>' + esc(nm) + '</b>' +
      (p.staff ? '<span style="padding: 2px 8px; border-radius: 999px; background: #ffc857; color: #4a3000; font-size: 11px; font-weight: 800;">운영자</span>' : '') +
      (p.secret ? '<span style="font-size: 12px; color: #64748b; font-weight: 700;">🔒 비밀글</span>' : '') +
      '<span style="font-size: 12px; color: #8a93a8;">' + ago(p.created_at) + '</span></div>' +
      '<div style="' + BOX + ' margin: 4px 0 0; font-size: 15px; overflow-wrap: anywhere;' + (hidden ? ' color: #94a3b8; font-style: italic;' : '') + (p.staff ? ' padding: 10px 12px; border-radius: 10px; background: #f3f6ff;' : '') + '">' + esc(tx) + '</div>' +
      (rp ? '<div style="' + BOX + ' margin: 6px 0 0 10px; padding: 8px 10px; border-left: 3px solid #1e3a8a; border-radius: 0 8px 8px 0; background: #f3f6ff; font-size: 13px;"><b style="color: #1e3a8a; margin-right: 4px;">리카수니 원장</b>' + esc(rp) + '</div>' : '') +
      '</div>';
  }
  function more(k, total) { return total > shown[k] ? '<button class="lks-more" data-k="' + k + '">더보기 (' + (total - shown[k]) + '개)</button>' : ''; }
  function col(title, items, key, empty, rd) {
    var c = rd ? ['#bcd0fa', '#f3f7ff', '#1d4ed8', '#2563eb'] : ['#f3d48a', '#fffbf0', '#7a4b00', '#f59e0b'];
    return '<div class="lks-col' + (rd ? ' lks-rd' : '') + '" style="' + BOX + ' border: 1px solid ' + c[0] + '; border-radius: 12px; background: ' + c[1] + '; padding: 10px 12px;">' +
      '<div style="margin: 0 0 6px; font-size: 15px; font-weight: 800; color: ' + c[2] + ';">' + title + ' <span style="display: inline-block; padding: 1px 8px; border-radius: 999px; background: ' + c[3] + '; color: #fff; font-size: 12px;">' + items.length + '</span></div>' +
      '<ul class="lks-rq"' + (shown[key] > 6 ? ' style="max-height: 330px; overflow-y: auto;"' : '') + '>' + (items.slice(0, shown[key]).map(reqItem).join('') || '<li style="font-size: 13px; color: #8a93a8;">' + empty + '</li>') + '</ul>' + more(key, items.length) + '</div>';
  }
  function render() {
    var reqs = cache.filter(isReq), cm = talk, total = talk.length ? Number(talk[0].total) : 0;
    function cnt(k) { return k === 'all' ? reqs.length : reqs.filter(function (c) { return gradeOf(c) === k; }).length; }
    var chips = [['all', '전체'], ['1', '고1'], ['2', '고2'], ['3', '고3'], ['b', '부교재']].filter(function (x) { return x[0] === 'all' || cnt(x[0]); })
      .map(function (x) { return '<button class="lks-chip' + (gf === x[0] ? ' on' : '') + '" data-g="' + x[0] + '">' + x[1] + ' ' + cnt(x[0]) + '</button>'; }).join('');
    var rf = reqs.filter(function (c) { return gf === 'all' || gradeOf(c) === gf; });
    var pre = rf.filter(function (c) { return !isDone(c) && !isReady(c); });          // 만드는 중 (진행 중)
    var rdy = rf.filter(function (c) { return isReady(c) || isDone(c); }).sort(function (a, b) { return new Date(b.replied_at || b.created_at) - new Date(a.replied_at || a.created_at); }); // 받을 수 있어요: 방금 완성된 자료가 위로
    list.innerHTML =
      '<div style="margin: 12px 0 6px; font-size: 16px; font-weight: 800; color: #1e3a8a;">최근 자료 요청</div>' +
      '<div>' + chips + '</div>' +
      '<div class="lks-cols">' + col('만드는 중', pre, 'pre', '기다리는 요청이 없어요.', false) + col('받을 수 있어요', rdy, 'rdy', '아직 준비된 자료가 없어요. 필요한 분석노트를 요청해 주세요.', true) + '</div>' +
      '<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 16px 0 0;"><span style="font-size: 16px; font-weight: 800; color: #1e3a8a;">소통하기</span><span style="font-size: 13px; color: #6b7280;">원장님께 무엇이든 물어보세요</span>' +
        '<a href="' + SITE + '#talk" style="margin-left: auto; padding: 5px 12px; border-radius: 8px; background: #1e3a8a; color: #fff; font-size: 13px; font-weight: 800;">질문하러 가기 →</a></div>' +
      '<div style="' + BOX + (shown.cmt > 3 ? ' max-height: 420px; overflow-y: auto;' : '') + '">' + (cm.slice(0, shown.cmt).map(talkItem).join('') || '<p style="color: #8a93a8; font-size: 14px;">아직 글이 없어요. 자료실에서 첫 질문을 남겨 주세요!</p>') + '</div>' +
      (total > shown.cmt ? '<a href="' + SITE + '#talk" class="lks-more" style="text-align: center;">소통하기 전체 보기 (' + total + '개) →</a>' : '');
    var cs = list.querySelectorAll('.lks-chip');
    for (var k = 0; k < cs.length; k++) cs[k].onclick = function () { gf = this.getAttribute('data-g'); shown.pre = shown.rdy = 6; render(); };
    var ps = list.querySelectorAll('.lks-pv');
    for (var p = 0; p < ps.length; p++) ps[p].onclick = function () { showPreview(this.getAttribute('data-pv'), this.getAttribute('data-t'), this.getAttribute('data-go')); };
    var bs = list.querySelectorAll('button.lks-more');
    for (var i = 0; i < bs.length; i++) bs[i].onclick = function () { shown[this.getAttribute('data-k')] += 6; render(); };
  }
  function load() {
    fetch(URL + '/rest/v1/comments?select=id,user_id,author_name,content,created_at,reply,replied_at,page_key,page_title&approved=eq.true&content=like.' + encodeURIComponent('[자료 요청]*') + '&order=created_at.desc&limit=80',
      { headers: { apikey: KEY } })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (d) { cache = Array.isArray(d) ? d : []; render(); })
      .catch(function () { if (!cache.length) render(); });
  }
  function loadTalk() {
    fetch(URL + '/rest/v1/rpc/talk_list', { method: 'POST', headers: { apikey: KEY, 'Content-Type': 'application/json' }, body: JSON.stringify({ p_limit: 5, p_offset: 0 }) })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (d) { talk = Array.isArray(d) ? d : []; render(); })
      .catch(function () {});
  }
  load(); loadTalk();
  setInterval(function () { if (!document.hidden) load(); }, 30000);
  setInterval(function () { if (!document.hidden) loadTalk(); }, 60000);
})();
})();
