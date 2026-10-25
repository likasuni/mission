/* 리카수니 자료실 알림 (새 자료 웹 푸시) */
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
var FN = 'https://iiyhmskvdjgstoikonwu.supabase.co/functions/v1/push';
function show(d) {
  return self.registration.showNotification(d.title || '리카수니 자료실', {
    body: d.body || '새 자료가 올라왔어요', icon: '/img/icon-192.png', badge: '/favicon.png',
    data: { url: d.url || 'https://data.likasuni.com/' }, tag: 'likasuni-new'
  });
}
self.addEventListener('push', function (e) {
  var d = null;
  try { d = e.data ? e.data.json() : null; } catch (x) { d = null; }
  if (d) { e.waitUntil(show(d)); return; }
  // 내용 없는 알림: 서버에서 가장 최근 알림 내용을 읽어 와서 보여 줌 (실패하면 기본 문구)
  e.waitUntil(fetch(FN, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"action":"last"}' })
    .then(function (r) { return r.json(); }).catch(function () { return {}; }).then(show));
});
self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var url = (e.notification.data && e.notification.data.url) || '/';
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (cs) {
    for (var i = 0; i < cs.length; i++) if (cs[i].url === url && 'focus' in cs[i]) return cs[i].focus();
    return self.clients.openWindow(url);
  }));
});
