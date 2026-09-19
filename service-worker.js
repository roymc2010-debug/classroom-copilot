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
    const isAlarm = Boolean(payload.alarm || (payload.data && payload.data.alarm) || payload.tag === 'agora-timer-alarm' || payload.tag === 'agora-study-mission-done');

    const options = {
        body: payload.body || 'Tienes una nueva actualización en tus materias.',
        icon: payload.icon || '/static/agora_logo_192.png?v=4',
        badge: payload.badge || '/static/agora_logo_light_32.png?v=4',
        silent: isAlarm ? false : isSilent,
        vibrate: (isSilent && !isAlarm) ? [] : (isAlarm ? [300, 150, 300, 150, 300] : (payload.vibrate || [300, 150, 300, 150, 400])),
        tag: isAlarm ? (payload.tag || 'agora-study-mission-done') : (payload.tag || 'agora-notice'),
        renotify: true,
        requireInteraction: isAlarm || Boolean(payload.requireInteraction),
        data: payload.data || { url: isAlarm ? '/?openTimer=1' : '/' },
        actions: isAlarm ? [
            { action: 'stop_alarm', title: '🔕 Detener Alarma' },
            { action: 'open_timer', title: '📱 Abrir Ágora' }
        ] : []
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

let activeTimerTarget = null;
let activeTimerTimeout = null;

function triggerTimerCompleteNotification() {
    activeTimerTarget = null;
    activeTimerTimeout = null;
    self.registration.showNotification('¡Misión Cumplida! ⏰', {
        body: 'Tu bloque de estudio ha finalizado.',
        icon: '/static/agora_logo_192.png?v=4',
        badge: '/static/agora_logo_light_32.png?v=4',
        silent: false,
        vibrate: [300, 150, 300, 150, 300],
        tag: 'agora-study-mission-done',
        renotify: true,
        requireInteraction: true,
        data: { url: '/?openTimer=1', alarm: true },
        actions: [
            { action: 'stop_alarm', title: '🔕 Detener Alarma' },
            { action: 'open_timer', title: '📱 Abrir Ágora' }
        ]
    });
}

self.addEventListener('message', (event) => {
    if (!event.data) return;

    if (event.data.type === 'SET_TIMER_TARGET') {
        const targetTime = Number(event.data.targetTime);
        if (!targetTime) return;
        activeTimerTarget = targetTime;
        if (activeTimerTimeout) {
            clearTimeout(activeTimerTimeout);
            activeTimerTimeout = null;
        }

        const delay = Math.max(0, targetTime - Date.now());
        activeTimerTimeout = setTimeout(() => {
            triggerTimerCompleteNotification();
        }, delay);
    }

    if (event.data.type === 'CLEAR_TIMER_TARGET') {
        activeTimerTarget = null;
        if (activeTimerTimeout) {
            clearTimeout(activeTimerTimeout);
            activeTimerTimeout = null;
        }
    }

    if (event.data.type === 'SHOW_TIMER_ALARM_NOTIFICATION') {
        const title = event.data.title || '¡Misión Cumplida! ⏰';
        const body = event.data.body || 'Tu bloque de estudio ha finalizado.';
        self.registration.showNotification(title, {
            body: body,
            icon: '/static/agora_logo_192.png?v=4',
            badge: '/static/agora_logo_light_32.png?v=4',
            silent: false,
            vibrate: [300, 150, 300, 150, 300],
            tag: 'agora-study-mission-done',
            renotify: true,
            requireInteraction: true,
            data: { url: '/?openTimer=1', alarm: true },
            actions: [
                { action: 'stop_alarm', title: '🔕 Detener Alarma' },
                { action: 'open_timer', title: '📱 Abrir Ágora' }
            ]
        });
    }
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const action = event.action;
    const targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/?openTimer=1';

    // Notificar a pestañas activas para detener el sonido de alarma
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
        for (const client of clientList) {
            client.postMessage({ type: 'STOP_ALARM', action: action });
        }
    });

    if (action === 'stop_alarm') {
        return;
    }

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (const client of clientList) {
                if (client.url.includes(self.location.origin) && 'focus' in client) {
                    client.postMessage({ type: 'ALARM_CLICKED', action: action });
                    return client.focus();
                }
            }
            if (self.clients.openWindow) {
                return self.clients.openWindow(targetUrl);
            }
        })
    );
});
