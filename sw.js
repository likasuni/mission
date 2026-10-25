/* 리카수니 자료실 알림 (새 자료 웹 푸시) */
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('push', function (e) {
  var d = {};
  try { d = e.data ? e.data.json() : {}; } catch (x) { d = { body: e.data && e.data.text() }; }
  e.waitUntil(self.registration.showNotification(d.title || '리카수니 자료실', {
    body: d.body || '새 자료가 올라왔어요', icon: '/img/icon-192.png', badge: '/favicon.png',
    data: { url: d.url || 'https://data.likasuni.com/' }, tag: 'likasuni-new'
  }));
});
self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var url = (e.notification.data && e.notification.data.url) || '/';
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (cs) {
    for (var i = 0; i < cs.length; i++) if (cs[i].url === url && 'focus' in cs[i]) return cs[i].focus();
    return self.clients.openWindow(url);
  }));
});
