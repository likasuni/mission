/* 코코스학원 홈페이지(www.cocosedu.co.kr) 첫 화면 '학교별 글 모아 보기' (2026-11-21 원장님 요청)
   Blogger 가젯에는 _tools/blogger_widgets/cocos-schools.html 두 줄만 있고, 내용은 이 파일이 그려요.
   제목에 학교 이름이 들어간 글을 블로그 글 목록(feed)에서 찾아 학교별로 묶어요. 새 글은 자동으로 들어가요.
   첫 화면 소개의 '03 우리 학교의 시험' 학교 목록(.cx-school-list)이 있으면 그 목록에 합쳐요 (같은 디자인):
   없는 학교 줄은 새로 만들고, 줄마다 [학교정보 N] 칩 → 누르면 그 줄 아래에 글 목록이 펼쳐짐. 목록이 없으면 따로 상자로 그려요.
   학교를 더하려면 아래 SCHOOLS 에 한 줄 추가 → main 에 합치고 deploy.sh (원장님이 다시 붙여 넣을 필요 없음). */
(function () {
  var box = document.getElementById('cocos-schools');
  if (!box) return;
  var path = location.pathname;
  var isLabel = path.indexOf('/search/label/') === 0; // 태그 페이지(예: 이매중 영어내신)는 큰 카드 대신 목록으로 (2026-11-21 원장님)
  // 그 밖의 페이지(글 페이지 등)에선 숨김
  if (!isLabel && path !== '/' && path !== '/index.html') { box.style.display = 'none'; return; }

  // [구분, 학교 이름, 제목에서 찾을 말] — 이 순서로 목록에 놓여요 (초 → 중 → 고)
  var SCHOOLS = [
    ['초등', '하탑초', /하탑초/],
    ['초등', '돌마초', /돌마초/],
    ['중등', '이매중', /이매중/],
    ['중등', '매송중', /매송중/],
    ['중등', '야탑중', /야탑중/],
    ['고등', '태원고', /태원고/],
    ['고등', '송림고', /송림고/],
    ['고등', '이매고', /이매고/],
    ['고등', '돌마고', /돌마고/],
    ['고등', '야탑고', /야탑고/],
    ['고등', '판교고', /판교고/]
  ];

  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  // 글 목록 날짜는 미국 시간으로 와서 한국 날짜로 바꿔요
  var kst = function (t) { var d = new Date(t); return isNaN(d) ? '' : new Date(d.getTime() + 9 * 3600e3).toISOString().slice(0, 10).replace(/-/g, '.'); };
  var B = 'box-sizing:border-box;max-width:100%;';

  function load(start, acc, label) {
    return fetch('/feeds/posts/summary' + (label ? '/-/' + encodeURIComponent(label) : '') + '?alt=json&max-results=150&start-index=' + start)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var es = (j.feed && j.feed.entry) || [];
        es.forEach(function (e) {
          var a = (e.link || []).filter(function (l) { return l.rel === 'alternate'; })[0];
          if (a) acc.push({ t: e.title.$t, u: a.href, d: kst(e.published.$t) });
        });
        return es.length === 150 && start < 1500 ? load(start + 150, acc, label) : acc;
      });
  }

  // 학년: 제목의 '고1·중3·초5' 또는 '2학년' (범위 '3~6학년'·학년 표시 없음은 '기타') — 2026-11-21 원장님: 학년별로 보이게
  var GRADE_RE = /(?:^|[^~\d])(?:고|중|초)\s*([1-6])(?![\d~])|(?:^|[^~\d])([1-6])\s*학년/; // 옛 아이폰 사파리도 되게 뒤보기(?<!) 안 씀
  var gradeOf = function (t) { var m = t.match(GRADE_RE); return m ? (m[1] || m[2]) + '학년' : '기타'; };
  var tabBtn = 'margin:0 6px 6px 0;padding:3px 10px;border:1px solid #e0e6ee;border-radius:4px;font:inherit;font-size:13px;cursor:pointer;';

  // 펼친 학교정보: 학년 탭 + 글 목록 (목록은 높이를 정해 두고 안에서 스크롤 → 페이지가 길게 밀려 내려가지 않게)
  function drawPanel(panel, ps, full) {
    var groups = {}, order = [];
    ps.forEach(function (p) { var g = gradeOf(p.t); if (!groups[g]) { groups[g] = []; order.push(g); } groups[g].push(p); });
    order.sort(function (a, b) { return (a === '기타') - (b === '기타') || a.localeCompare(b); });
    var tabs = order.length > 1 ? ['전체'].concat(order) : [];
    function draw(sel) {
      var list = sel === '전체' ? ps : groups[sel];
      panel.innerHTML = (tabs.length ? '<div style="' + B + 'padding:10px 0 4px">' + tabs.map(function (g) {
        var on = g === sel, n = g === '전체' ? ps.length : groups[g].length;
        return '<button type="button" data-g="' + g + '" style="' + tabBtn + (on ? 'background:#2456c7;color:#fff;border-color:#2456c7' : 'background:#f1f5fb;color:#2456c7') + '">' + g + ' ' + n + '</button>';
      }).join('') + '</div>' : '')
        + '<div style="' + B + 'width:100%;' + (full ? '' : 'max-height:300px;overflow-y:auto;') + 'border-bottom:1px solid #dbe3ec">' + listHtml(list) + '</div>';
      [].forEach.call(panel.querySelectorAll('button[data-g]'), function (b) { b.onclick = function () { draw(b.getAttribute('data-g')); }; });
    }
    draw(tabs.length ? '전체' : order[0]);
  }

  function listHtml(ps) {
    return '<ul style="' + B + 'width:100%;margin:0;padding:0 0 4px;list-style:none">' + ps.map(function (p, i) {
      return '<li style="' + B + 'display:flex;gap:12px;align-items:baseline;padding:9px 0;' + (i ? 'border-top:1px solid #eef2f7' : '') + '">'
        + '<a href="' + esc(p.u) + '" style="flex:1;min-width:0;color:#142943;text-decoration:none;font-size:15px;line-height:1.55">' + esc(p.t) + '</a>'
        + '<span style="flex:none;color:#8a97a8;font-size:12px">' + esc(p.d) + '</span></li>';
    }).join('') + '</ul>';
  }

  // ① 첫 화면 소개의 학교 목록에 합치기
  function merge(list, by) {
    box.style.display = 'none';
    var rows = {};
    [].forEach.call(list.querySelectorAll('.cx-schoolrow'), function (r) {
      var s = r.querySelector('strong'); if (s) rows[s.textContent.trim()] = r;
    });
    var first = list.firstChild;
    SCHOOLS.forEach(function (s) {
      var name = s[1], ps = by[name];
      if (!ps.length) return;
      var row = rows[name];
      if (!row) { // 목록에 없는 학교는 같은 모양으로 새 줄
        row = document.createElement('div');
        row.className = 'cx-schoolrow';
        row.innerHTML = '<strong>' + esc(name) + '</strong><div></div>';
      }
      list.insertBefore(row, first); // SCHOOLS 순서대로 맨 앞부터 다시 세움 (목록에만 있는 학교는 뒤에 그대로)
      var chips = row.querySelector('div') || row.appendChild(document.createElement('div'));
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'cx-chip';
      btn.setAttribute('aria-expanded', 'false');
      btn.style.cssText = 'font:inherit;font-size:13px;cursor:pointer;border-style:solid;margin-left:' + (chips.children.length ? '8px' : '0');
      btn.innerHTML = '학교정보 ' + ps.length + ' <span aria-hidden="true">▾</span>';
      chips.appendChild(btn);
      var panel = document.createElement('div');
      panel.style.cssText = B + 'width:100%;display:none;margin-top:-1px';
      row.parentNode.insertBefore(panel, row.nextSibling);
      btn.onclick = function () {
        var open = panel.style.display === 'none';
        if (open) drawPanel(panel, ps);
        panel.style.display = open ? 'block' : 'none';
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        btn.querySelector('span').textContent = open ? '▴' : '▾';
        btn.style.background = open ? '#2456c7' : ''; btn.style.color = open ? '#fff' : '';
      };
      // 줄 사이에 끼운 패널이 다음 순서 줄보다 먼저 오도록, 다음 학교는 패널 뒤에서 시작
      row.setAttribute('data-lv', s[0]); panel.setAttribute('data-lv', s[0]);
      first = panel.nextSibling;
    });
    // 초등·중등·고등 탭 (2026-11-21 원장님: '출발점으로' 제목 아래 탭으로) — 고른 구분의 학교 줄만 보여요
    var lvs = ['초등', '중등', '고등'].filter(function (g) { return list.querySelector('.cx-schoolrow[data-lv="' + g + '"]'); });
    if (lvs.length < 2) return;
    var tabs = document.createElement('div');
    tabs.setAttribute('role', 'tablist');
    tabs.style.cssText = B + 'width:100%;display:flex;gap:8px;margin:0 0 16px';
    list.parentNode.insertBefore(tabs, list);
    function pick(g) {
      [].forEach.call(tabs.children, function (b) {
        var on = b.getAttribute('data-lv') === g;
        b.setAttribute('aria-selected', on ? 'true' : 'false');
        b.style.background = on ? '#142943' : '#fff'; b.style.color = on ? '#fff' : '#142943'; b.style.borderColor = on ? '#142943' : '#dbe3ec';
      });
      [].forEach.call(list.children, function (el) {
        var lv = el.getAttribute('data-lv');
        if (!lv) return; // 원래 목록에만 있던 줄은 늘 보임
        if (el.classList.contains('cx-schoolrow')) el.style.display = lv === g ? '' : 'none';
        else if (lv !== g && el.style.display !== 'none') { // 다른 구분의 펼친 목록은 접기 (버튼을 눌러 닫아 버튼 모양도 함께 되돌림)
          var b = el.previousSibling && el.previousSibling.querySelector && el.previousSibling.querySelector('button[aria-expanded="true"]');
          if (b) b.click(); else el.style.display = 'none';
        }
      });
      try { sessionStorage.setItem('cocos-lv', g); } catch (e) {}
    }
    lvs.forEach(function (g) {
      var n = list.querySelectorAll('.cx-schoolrow[data-lv="' + g + '"]').length;
      var b = document.createElement('button');
      b.type = 'button'; b.setAttribute('role', 'tab'); b.setAttribute('data-lv', g);
      b.style.cssText = B + 'flex:1 1 0;min-height:44px;padding:8px 10px;border:1px solid #dbe3ec;border-radius:4px;font:inherit;font-size:16px;font-weight:700;cursor:pointer';
      b.innerHTML = g + ' <small style="font-weight:400;opacity:.7">' + n + '</small>';
      b.onclick = function () { pick(g); };
      tabs.appendChild(b);
    });
    var saved = ''; try { saved = sessionStorage.getItem('cocos-lv') || ''; } catch (e) {}
    pick(lvs.indexOf(saved) > -1 ? saved : lvs[0]);
  }

  // ② 목록이 없을 때: 따로 상자
  function standalone(by) {
    box.innerHTML = '<div style="' + B + 'width:100%;overflow:hidden;border:1px solid #dbe3ec;border-top:4px solid #2456c7;background:#fff;padding:20px 18px;margin:18px 0;color:#142943;line-height:1.7;word-break:keep-all">'
      + '<h2 style="margin:0 0 12px;font-size:21px;color:#142943">학교별 글 모아 보기</h2><div class="cs-list"></div></div>';
    var wrap = box.querySelector('.cs-list');
    SCHOOLS.forEach(function (s) {
      var ps = by[s[1]]; if (!ps.length) return;
      var d = document.createElement('details');
      d.style.cssText = B + 'border-top:1px solid #dbe3ec;padding:10px 0';
      d.innerHTML = '<summary style="cursor:pointer;font-weight:700">' + esc(s[1]) + ' <small style="color:#53647a;font-weight:400">학교정보 ' + ps.length + '</small></summary><div></div>';
      drawPanel(d.querySelector('div'), ps);
      wrap.appendChild(d);
    });
  }

  // ③ 태그 페이지: 카드 목록을 숨기고 학년 탭 + 글 목록으로
  function labelPage() {
    box.style.display = 'none';
    var posts = document.querySelector('#Blog1 .blog-posts');
    if (!posts) return;
    var label = decodeURIComponent(path.slice('/search/label/'.length).split('/')[0]);
    load(1, [], label).then(function (ps) {
      if (!ps.length) return; // 못 읽으면 원래 카드 그대로
      var wrap = document.createElement('div');
      wrap.style.cssText = B + 'width:100%;margin:8px 0 28px;color:#142943;line-height:1.7;word-break:keep-all;border-top:2px solid #142943';
      wrap.innerHTML = '<p style="margin:12px 0 0;font-size:14px;color:#53647a">글 ' + ps.length + '개</p><div></div>';
      posts.parentNode.insertBefore(wrap, posts);
      posts.style.display = 'none';
      var pager = document.querySelector('#Blog1 .blog-pager'); if (pager) pager.style.display = 'none';
      drawPanel(wrap.lastChild, ps, true);
    }).catch(function () {});
  }
  if (isLabel) { labelPage(); return; }

  load(1, []).then(function (posts) {
    var by = {};
    SCHOOLS.forEach(function (s) { by[s[1]] = posts.filter(function (p) { return s[2].test(p.t); }); });
    var list = document.querySelector('#cocos-school .cx-school-list');
    if (list) merge(list, by); else standalone(by);
  }).catch(function () { box.style.display = 'none'; });
})();
