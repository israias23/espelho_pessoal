self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('time-tracker-v1').then((cache) => cache.addAll([
      '/',
      '/static/bootstrap.min.css',  // Adicione mais assets se necessário
    ])),
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => response || fetch(e.request)),
  );
});

self.addEventListener('push', (event) => {
  const data = event.data.json();
  self.registration.showNotification(data.title, {
    body: data.body,
  });
});