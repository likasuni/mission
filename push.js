/* 새 자료 알림 버튼 (#push-btn): 구독하면 원장님이 자료를 올릴 때 휴대폰·PC 로 알림이 와요.
   아이폰은 '홈 화면에 추가'한 자료실 아이콘으로 열어야 알림을 켤 수 있어요 (iOS 16.4 이상). */
(function () {
  var FN = 'https://iiyhmskvdjgstoikonwu.supabase.co/functions/v1/push';
  var KEY = 'BNanG8J9rFSAYaR5PEI4VsWkOsWM0rIkSnnPMGzPAL07jte7xwrS3owgePJ1nW5Aetz7zV8ruhV6n9Jort-DXv8'; // 공개키 (비밀 아님)
  var btns = document.querySelectorAll('.push-btn');
  recent();
  if (!btns.length) return;
  var ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var app = navigator.standalone || (window.matchMedia && matchMedia('(display-mode: standalone)').matches);
  var ok = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  if (!ok && !ios) { btns.forEach(function (b) { b.style.display = 'none'; }); return; }

  function set(on) { btns.forEach(function (b) { b.classList.toggle('on', on); b.title = on ? '새 자료 알림 켜짐' : '새 자료 알림 받기'; var t = b.querySelector('.pt'); if (t) t.textContent = on ? '알림 켜짐' : '새 자료 알림 받기'; }); }
  function key(s) { var p = '='.repeat((4 - s.length % 4) % 4), r = atob((s + p).replace(/-/g, '+').replace(/_/g, '/')), a = new Uint8Array(r.length); for (var i = 0; i < r.length; i++) a[i] = r.charCodeAt(i); return a; }
  function post(action, sub) { return fetch(FN, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: action, sub: sub }) }); }
  function mark(v) { try { v ? localStorage.setItem('push-sync', v) : localStorage.removeItem('push-sync'); } catch (e) { /* 무시 */ } }
  function today() { return new Date().toISOString().slice(0, 10); }

  if (ok) navigator.serviceWorker.register('/sw.js').then(function (r) { r.update().catch(function () {}); return r.pushManager.getSubscription(); }).then(function (s) {
    var on = !!s && Notification.permission === 'granted'; set(on);
    var last = ''; try { last = localStorage.getItem('push-sync') || ''; } catch (e) { /* 무시 */ }
    if (on && last !== today()) post('subscribe', s.toJSON()).then(function (r) { if (r.ok) mark(today()); }); // 하루 한 번 서버 구독 정보 확인
  }).catch(function () {});

  async function click() {
    if (!ok || (ios && !app)) {
      alert('아이폰·아이패드는 이렇게 해 주세요.\n\n1. 사파리 아래쪽 공유 버튼(네모 위 화살표)\n2. "홈 화면에 추가"\n3. 홈 화면의 "리카수니" 아이콘으로 열기\n4. 이 알림 버튼 다시 누르기\n\n(iOS 16.4 이상에서 돼요)');
      return;
    }
    var reg = await navigator.serviceWorker.ready, s = await reg.pushManager.getSubscription();
    if (s && Notification.permission === 'granted') {
      if (confirm('새 자료 알림을 끌까요?')) { await post('unsubscribe', s.toJSON()).catch(function () {}); await s.unsubscribe(); mark(''); set(false); }
      return;
    }
    var p = await Notification.requestPermission();
    if (p !== 'granted') { alert('알림이 꺼져 있어요. 브라우저 설정에서 data.likasuni.com 의 알림을 "허용"으로 바꾼 뒤 다시 눌러 주세요.'); return; }
    try {
      s = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key(KEY) });
      var r = await post('subscribe', s.toJSON());
      if (!r.ok) throw new Error(r.status);
      mark(today()); set(true);
      alert('알림을 켰어요! 새 분석노트·해설이 올라오면 바로 알려 드릴게요.');
    } catch (e) { alert('알림을 켜지 못했어요. 잠시 뒤 다시 눌러 주세요.'); }
  }
  btns.forEach(function (b) { b.addEventListener('click', click); });

  // 첫 화면 '최근 알림' (#push-news): 지금까지 보낸 알림 5개. 없으면 칸을 숨긴 채로 둠
  function recent() {
    var box = document.getElementById('push-news');
    if (!box) return;
    fetch(FN, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"action":"recent"}' })
      .then(function (r) { return r.json(); }).then(function (j) {
        var it = (j && j.items) || [];
        if (!it.length) return;
        var esc = function (t) { return String(t || '').replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
        box.querySelector('ul').innerHTML = it.map(function (x) {
          var d = new Date(x.created_at), when = (d.getMonth() + 1) + '/' + d.getDate();
          var href = String(x.url || '/').replace(/^https:\/\/data\.likasuni\.com/, '') || '/';
          return '<li><a href="' + esc(href) + '"><span class="pn-d">' + when + '</span><b>' + esc(x.title) + '</b><span class="pn-b">' + esc(x.body) + '</span></a></li>';
        }).join('');
        box.hidden = false;
      }).catch(function () {});
  }
})();
