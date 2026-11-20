/* 코코스학원 홈페이지(www.cocosedu.co.kr) 첫 화면 '학교별 학부모 정보' 가젯 (2026-11-21 원장님 요청)
   Blogger 가젯에는 _tools/blogger_widgets/cocos-schools.html 두 줄만 있고, 내용은 이 파일이 그려요.
   제목에 학교 이름이 들어간 글을 블로그 글 목록(feed)에서 찾아 학교별로 묶어요. 새 글은 자동으로 들어가요.
   학교를 더하려면 아래 SCHOOLS 에 한 줄 추가 → main 에 합치고 deploy.sh (원장님이 다시 붙여 넣을 필요 없음). */
(function () {
  var box = document.getElementById('cocos-schools');
  if (!box) return;
  // 첫 화면에서만 보여요 (가젯이 모든 페이지에 들어가도 글 페이지에선 숨김)
  if (location.pathname !== '/' && location.pathname !== '/index.html') { box.style.display = 'none'; return; }

  // [구분, 학교 이름(버튼), 제목에서 찾을 말]
  var SCHOOLS = [
    ['초등', '하탑초', /하탑초/],
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
  var SHOW = 8; // 처음 보여 줄 글 수

  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var B = 'box-sizing:border-box;max-width:100%;';
  // 글 목록 날짜는 미국 시간으로 와서 한국 날짜로 바꿔요
  var kst = function (t) { var d = new Date(t); return isNaN(d) ? '' : new Date(d.getTime() + 9 * 3600e3).toISOString().slice(0, 10); };
  box.innerHTML = '<div style="' + B + 'width:100%;overflow:hidden;border:1px solid #dbe3ec;border-top:4px solid #2456c7;background:#fff;padding:20px 18px;margin:18px 0;color:#142943;line-height:1.7;word-break:keep-all">'
    + '<h2 style="margin:0 0 4px;font-size:21px;color:#142943">🏫 학교별 학부모 정보</h2>'
    + '<p style="margin:0 0 14px;font-size:14px;color:#53647a">우리 아이 학교 글만 모아 보세요. 내신 분석 · 시험 일정 · 교과서 · 방학 준비</p>'
    + '<div class="cs-groups">불러오는 중...</div><div class="cs-list" style="' + B + 'width:100%"></div></div>';

  function load(start, acc) {
    return fetch('/feeds/posts/summary?alt=json&max-results=150&start-index=' + start)
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var es = (j.feed && j.feed.entry) || [];
        es.forEach(function (e) {
          var a = (e.link || []).filter(function (l) { return l.rel === 'alternate'; })[0];
          if (a) acc.push({ t: e.title.$t, u: a.href, d: kst(e.published.$t) });
        });
        return es.length === 150 && start < 1500 ? load(start + 150, acc) : acc;
      });
  }

  load(1, []).then(function (posts) {
    var by = {};
    SCHOOLS.forEach(function (s) { by[s[1]] = posts.filter(function (p) { return s[2].test(p.t); }); });
    var groups = ['초등', '중등', '고등'].map(function (g) {
      var chips = SCHOOLS.filter(function (s) { return s[0] === g && by[s[1]].length; }).map(function (s) {
        return '<button type="button" data-s="' + esc(s[1]) + '" style="' + B + 'margin:0 6px 6px 0;padding:6px 12px;border:1px solid #c9d6ea;border-radius:18px;background:#f4f7fb;color:#142943;font-size:15px;font-weight:700;cursor:pointer">'
          + esc(s[1]) + ' <small style="color:#53647a;font-weight:400">' + by[s[1]].length + '</small></button>';
      }).join('');
      return chips ? '<div style="margin:0 0 6px"><b style="display:inline-block;width:44px;font-size:14px;color:#2456c7">' + g + '</b>' + chips + '</div>' : '';
    }).join('');
    box.querySelector('.cs-groups').innerHTML = groups || '<p style="margin:0;color:#53647a">아직 학교별 글이 없어요.</p>';
    var list = box.querySelector('.cs-list'), cur = '';

    function show(name, all) {
      cur = name;
      box.querySelectorAll('.cs-groups button').forEach(function (b) {
        var on = b.getAttribute('data-s') === name;
        b.style.background = on ? '#2456c7' : '#f4f7fb'; b.style.color = on ? '#fff' : '#142943';
        var sm = b.querySelector('small'); if (sm) sm.style.color = on ? '#dbe6ff' : '#53647a';
      });
      var ps = by[name] || [], vis = all ? ps : ps.slice(0, SHOW);
      list.innerHTML = '<div style="' + B + 'width:100%;margin-top:10px;padding-top:12px;border-top:1px dashed #c9d6ea">'
        + '<p style="margin:0 0 8px;font-weight:700">' + esc(name) + ' 글 ' + ps.length + '개</p>'
        + '<ul style="margin:0;padding:0;list-style:none">' + vis.map(function (p) {
          return '<li style="margin:0 0 6px;padding-left:12px;border-left:3px solid #ffc857"><a href="' + esc(p.u) + '" style="color:#142943;text-decoration:none;font-size:15px">' + esc(p.t) + '</a> <span style="color:#8a97a8;font-size:12px">' + esc(p.d) + '</span></li>';
        }).join('') + '</ul>'
        + (ps.length > vis.length ? '<button type="button" class="cs-more" style="' + B + 'margin-top:6px;padding:6px 14px;border:1px solid #c9d6ea;border-radius:6px;background:#fff;color:#2456c7;font-size:14px;cursor:pointer">더보기 (' + (ps.length - vis.length) + '개)</button>' : '')
        + '</div>';
      var m = list.querySelector('.cs-more');
      if (m) m.onclick = function () { show(name, true); };
    }
    box.querySelectorAll('.cs-groups button').forEach(function (b) {
      b.onclick = function () { var n = b.getAttribute('data-s'); if (n === cur) { cur = ''; list.innerHTML = ''; show_off(); } else show(n); };
    });
    function show_off() {
      box.querySelectorAll('.cs-groups button').forEach(function (b) {
        b.style.background = '#f4f7fb'; b.style.color = '#142943';
        var sm = b.querySelector('small'); if (sm) sm.style.color = '#53647a';
      });
    }
  }).catch(function () {
    box.querySelector('.cs-groups').innerHTML = '<p style="margin:0;color:#53647a">글 목록을 불러오지 못했어요. 잠시 뒤 새로고침해 주세요.</p>';
  });
})();
