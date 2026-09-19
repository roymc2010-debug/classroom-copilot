// Ágora PWA Service Worker (RFC 8291 / RFC 8292 Web Push Protocol)
const CACHE_NAME = 'agora-sw-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

let activeTimerTarget = null;
let activeTimerTimeout = null;
let activeTimerBreakMinutes = 5;

function getTimerActions(breakMinutes) {
    const bMin = Number(breakMinutes) || 5;
    return [
        { action: 'stop_alarm', title: '⏹ Detener Alarma' },
        { action: 'start_break', title: `☕ Iniciar Descanso (${bMin} min)` }
    ];
}

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
    const breakMinutes = Number(payload.breakMinutes || (payload.data && payload.data.breakMinutes)) || activeTimerBreakMinutes || 5;

    const options = {
        body: payload.body || 'Tienes una nueva actualización en tus materias.',
        icon: payload.icon || '/static/agora_logo_192.png?v=4',
        badge: '/static/img/badge.png',
        silent: isAlarm ? false : isSilent,
        vibrate: (isSilent && !isAlarm) ? [] : (isAlarm ? [300, 150, 300, 150, 300] : (payload.vibrate || [300, 150, 300, 150, 400])),
        tag: isAlarm ? (payload.tag || 'agora-study-mission-done') : (payload.tag || 'agora-notice'),
        renotify: true,
        requireInteraction: isAlarm || Boolean(payload.requireInteraction),
        data: payload.data || { url: isAlarm ? '/?openTimer=1' : '/', breakMinutes: breakMinutes, alarm: isAlarm },
        actions: isAlarm ? getTimerActions(breakMinutes) : (payload.actions || [])
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

function triggerTimerCompleteNotification(breakMinutes) {
    activeTimerTarget = null;
    activeTimerTimeout = null;
    const bMin = Number(breakMinutes) || activeTimerBreakMinutes || 5;
    self.registration.showNotification('¡Misión Cumplida! ⏰', {
        body: 'Tu bloque de estudio ha finalizado.',
        icon: '/static/agora_logo_192.png?v=4',
        badge: '/static/img/badge.png',
        silent: false,
        vibrate: [300, 150, 300, 150, 300],
        tag: 'agora-study-mission-done',
        renotify: true,
        requireInteraction: true,
        data: { url: '/?openTimer=1', alarm: true, breakMinutes: bMin },
        actions: getTimerActions(bMin)
    });
}

self.addEventListener('message', (event) => {
    if (!event.data) return;

    if (event.data.type === 'SET_TIMER_TARGET') {
        const targetTime = Number(event.data.targetTime);
        if (!targetTime) return;
        activeTimerTarget = targetTime;
        if (event.data.breakMinutes) {
            activeTimerBreakMinutes = Number(event.data.breakMinutes) || 5;
        }
        if (activeTimerTimeout) {
            clearTimeout(activeTimerTimeout);
            activeTimerTimeout = null;
        }

        const delay = Math.max(0, targetTime - Date.now());
        activeTimerTimeout = setTimeout(() => {
            triggerTimerCompleteNotification(activeTimerBreakMinutes);
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
        const bMin = Number(event.data.breakMinutes) || activeTimerBreakMinutes || 5;
        self.registration.showNotification(title, {
            body: body,
            icon: '/static/agora_logo_192.png?v=4',
            badge: '/static/img/badge.png',
            silent: false,
            vibrate: [300, 150, 300, 150, 300],
            tag: 'agora-study-mission-done',
            renotify: true,
            requireInteraction: true,
            data: { url: '/?openTimer=1', alarm: true, breakMinutes: bMin },
            actions: getTimerActions(bMin)
        });
    }
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const action = event.action;
    const notifData = event.notification.data || {};
    const breakMinutes = Number(notifData.breakMinutes) || activeTimerBreakMinutes || 5;
    const targetUrl = notifData.url || '/?openTimer=1';

    // 1. Silenciar inmediatamente si pulsa 'stop_alarm' sin abrir la app
    if (action === 'stop_alarm') {
        event.waitUntil(
            self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
                for (const client of clientList) {
                    client.postMessage({ type: 'STOP_ALARM', action: 'stop_alarm' });
                }
            })
        );
        return;
    }

    // 2. Iniciar descanso directamente si pulsa 'start_break'
    if (action === 'start_break') {
        event.waitUntil(
            self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
                let clientFound = false;
                for (const client of clientList) {
                    client.postMessage({
                        type: 'START_BREAK',
                        breakMinutes: breakMinutes
                    });
                    clientFound = true;
                }
                if (!clientFound && self.clients.openWindow) {
                    return self.clients.openWindow(`/?openTimer=1&startBreak=1&breakMinutes=${breakMinutes}`);
                }
            })
        );
        return;
    }

    // 3. Clic general en la notificación: detener sonido y enfocar/abrir el temporizador
    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (const client of clientList) {
                client.postMessage({ type: 'STOP_ALARM', action: action });
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

