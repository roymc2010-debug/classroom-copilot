// Ágora PWA Service Worker (RFC 8291 / RFC 8292 Web Push Protocol)
const CACHE_NAME = 'agora-sw-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
    let payload = {};
    if (event.data) {
        try {
            payload = event.data.json();
        } catch(e) {
            payload = {
                title: 'Ágora - Alerta',
                body: event.data.text()
            };
        }
    }

    const title = payload.title || 'Ágora - Nueva Notificación';
    const isSilent = Boolean(payload.silent);
    const options = {
        body: payload.body || 'Tienes una nueva actualización en tus materias.',
        icon: payload.icon || '/static/agora_logo_192.png?v=4',
        badge: payload.badge || '/static/agora_logo_light_32.png?v=4',
        silent: isSilent,
        vibrate: isSilent ? [] : (payload.vibrate || [300, 150, 300, 150, 400]),
        tag: payload.tag || 'agora-notice',
        renotify: true,
        data: payload.data || { url: '/' }
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/';

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (const client of clientList) {
                if (client.url.includes(self.location.origin) && 'focus' in client) {
                    return client.focus();
                }
            }
            if (self.clients.openWindow) {
                return self.clients.openWindow(targetUrl);
            }
        })
    );
});
