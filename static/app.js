let currentEnrolledCourses = [];
let currentUserEmail = '';
let currentTaskContext = null;
let chatHistory = [];
const sessionTaskHistories = {};

const tasksMap = new Map();

let allUpcomingTasks = [];
let allOverdueTasks = [];
let allNoDateTasks = [];
let allCompletedTasks = [];
let cachedAnnouncements = [];

let selectedCourses = new Set();
let currentMissionFilter = 'all';
let currentSortMode = 'urgency';
let selectedCalendarDay = null;
let metricMode = 'tasks';

let currentTaskDocs = [];
let currentDocIndex = 0;
let docViewMode = 'pdf';

// Temporizador de 2 Fases (Foco y Descanso)
let timerInterval = null;
let timerSeconds = 25 * 60;
let timerRunning = false;
let timerPhase = 'focus';

const TIMER_PRESETS = {
    'pomodoro': { label: 'Pomodoro 25/5', focus: 25, break: 5 },
    '52-17': { label: 'Regla 52/17', focus: 52, break: 17 },
    'ultradiano': { label: 'Ultradiano 90/20', focus: 90, break: 20 },
    '5min': { label: '5 Minutos', focus: 5, break: 0 }
};
let activePresetKey = 'pomodoro';

function initApp() {
    renderMiniCalendar();
    loadTasks();
    loadAnnouncements();
    initTheme();
    initLiveClock();
    loadPreferences();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

// Control del Tema (Helios y Selene)
function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.classList.toggle('dark');
    localStorage.setItem('agora-theme', isDark ? 'dark' : 'light');
}

function initTheme() {
    const saved = localStorage.getItem('agora-theme');
    if (saved === 'light') {
        document.documentElement.classList.remove('dark');
    } else {
        document.documentElement.classList.add('dark');
    }
}

// Reloj en Vivo
function initLiveClock() {
    function tick() {
        const now = new Date();
        const timeEl = document.getElementById('live-clock-time');
        const dateEl = document.getElementById('live-clock-date');
        if (timeEl) {
            timeEl.textContent = now.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
        }
        if (dateEl) {
            dateEl.textContent = now.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' });
        }
    }
    setInterval(tick, 1000);
    tick();
}

function getAcademicDateString(d = new Date()) {
    const copy = new Date(d);
    if (copy.getHours() < 7) {
        copy.setDate(copy.getDate() - 1);
    }
    return copy.toISOString().split('T')[0];
}

// Temporizador
function setTimerPreset(arg) {
    clearInterval(timerInterval);
    timerRunning = false;
    timerPhase = 'focus';
    
    if (arg === 52 || arg === '52-17' || arg === '52/17') {
        activePresetKey = '52-17';
        timerSeconds = 52 * 60;
    } else if (arg === 90 || arg === 'ultradiano') {
        activePresetKey = 'ultradiano';
        timerSeconds = 90 * 60;
    } else if (arg === 5 || arg === '5min') {
        activePresetKey = '5min';
        timerSeconds = 5 * 60;
    } else {
        activePresetKey = 'pomodoro';
        timerSeconds = 25 * 60;
    }
    
    updateTimerDisplay();
}

function updateTimerDisplay() {
    const mins = Math.floor(timerSeconds / 60);
    const secs = timerSeconds % 60;
    const el = document.getElementById('timer-display');
    const badge = document.getElementById('timer-phase-badge');
    const startBtn = document.getElementById('timer-start-btn');

    if (el) {
        el.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        if (timerPhase === 'break') {
            el.className = "text-3xl font-mono font-extrabold tracking-wider text-emerald-600 dark:text-emerald-400 transition-colors";
        } else {
            el.className = "text-3xl font-mono font-extrabold tracking-wider text-cantera-900 dark:text-white transition-colors";
        }
    }

    if (badge) {
        const preset = TIMER_PRESETS[activePresetKey] || TIMER_PRESETS['pomodoro'];
        if (timerPhase === 'break') {
            badge.textContent = `Descanso (${preset.break}m)`;
            badge.className = "text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-0.5";
        } else {
            badge.textContent = `Foco • ${preset.label}`;
            badge.className = "text-[10px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-0.5";
        }
    }

    if (startBtn && !timerRunning) {
        startBtn.textContent = timerPhase === 'break' ? 'Iniciar Descanso' : 'Iniciar Foco';
    }
}

function startTimer() {
    if (timerRunning) return;
    timerRunning = true;
    const btn = document.getElementById('timer-start-btn');
    if (btn) btn.textContent = 'Corriendo';

    timerInterval = setInterval(() => {
        if (timerSeconds > 0) {
            timerSeconds--;
            updateTimerDisplay();
        } else {
            clearInterval(timerInterval);
            timerRunning = false;
            triggerAlarmChime();

            const preset = TIMER_PRESETS[activePresetKey] || TIMER_PRESETS['pomodoro'];
            if (timerPhase === 'focus' && preset.break > 0) {
                timerPhase = 'break';
                timerSeconds = preset.break * 60;
                updateTimerDisplay();
                alert(`¡Foco completado! Tu descanso de ${preset.break} minutos está listo. Presiona "Iniciar Descanso" cuando quieras levantarte.`);
            } else {
                timerPhase = 'focus';
                timerSeconds = preset.focus * 60;
                updateTimerDisplay();
                alert("¡Descanso concluido! ¿Listo para otro bloque de foco?");
            }
        }
    }, 1000);
}

function pauseTimer() {
    clearInterval(timerInterval);
    timerRunning = false;
    const btn = document.getElementById('timer-start-btn');
    if (btn) btn.textContent = 'Continuar';
}

function resetTimer() {
    clearInterval(timerInterval);
    timerRunning = false;
    const preset = TIMER_PRESETS[activePresetKey] || TIMER_PRESETS['pomodoro'];
    timerSeconds = (timerPhase === 'break' ? preset.break : preset.focus) * 60;
    updateTimerDisplay();
}

document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        if (timerRunning) pauseTimer();
        else startTimer();
    }
    if (e.key === 'Escape') {
        closeIgnisWorkspace();
        closeMentorsModal();
        closeTechniquesModal();
        closeGradesModal();
        closeSettingsModal();
    }
});

function triggerAlarmChime() {
    const chimeEnabled = localStorage.getItem('setting-chime') !== 'false';
    if (!chimeEnabled) return;

    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 1.2);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 1.2);
    } catch(e) {}
}

function toggleSettingChime() {
    const current = localStorage.getItem('setting-chime') !== 'false';
    const next = !current;
    localStorage.setItem('setting-chime', next ? 'true' : 'false');
    updateSettingsSwitches();
}

function toggleSettingAutofocus() {
    const current = localStorage.getItem('setting-autofocus') !== 'false';
    const next = !current;
    localStorage.setItem('setting-autofocus', next ? 'true' : 'false');
    updateSettingsSwitches();
}

function updateSettingsSwitches() {
    const chime = localStorage.getItem('setting-chime') !== 'false';
    const autofocus = localStorage.getItem('setting-autofocus') !== 'false';

    const sChime = document.getElementById('switch-chime');
    const tChime = document.getElementById('thumb-chime');
    if (sChime && tChime) {
        sChime.className = `relative w-12 h-6 rounded-full transition-colors p-0.5 ${chime ? 'bg-indigo-600' : 'bg-cantera-300 dark:bg-slate-700'}`;
        tChime.className = `w-5 h-5 rounded-full bg-white shadow-sm transform transition-transform ${chime ? 'translate-x-6' : 'translate-x-0'}`;
    }

    const sAuto = document.getElementById('switch-autofocus');
    const tAuto = document.getElementById('thumb-autofocus');
    if (sAuto && tAuto) {
        sAuto.className = `relative w-12 h-6 rounded-full transition-colors p-0.5 ${autofocus ? 'bg-indigo-600' : 'bg-cantera-300 dark:bg-slate-700'}`;
        tAuto.className = `w-5 h-5 rounded-full bg-white shadow-sm transform transition-transform ${autofocus ? 'translate-x-6' : 'translate-x-0'}`;
    }
}

function loadPreferences() {
    updateSettingsSwitches();
    const g = localStorage.getItem('key-gemini');
    const gr = localStorage.getItem('key-groq');
    const op = localStorage.getItem('key-openrouter');
    if (g && document.getElementById('key-gemini')) document.getElementById('key-gemini').value = g;
    if (gr && document.getElementById('key-groq')) document.getElementById('key-groq').value = gr;
    if (op && document.getElementById('key-openrouter')) document.getElementById('key-openrouter').value = op;
}

function saveApiKeys() {
    const g = document.getElementById('key-gemini').value.trim();
    const gr = document.getElementById('key-groq').value.trim();
    const op = document.getElementById('key-openrouter').value.trim();
    if (g) localStorage.setItem('key-gemini', g);
    if (gr) localStorage.setItem('key-groq', gr);
    if (op) localStorage.setItem('key-openrouter', op);
    alert("¡Configuración guardada en este dispositivo!");
    closeSettingsModal();
}

// -------------------------------------------------------------
// CARGA Y SEPARACIÓN DE TAREAS
// -------------------------------------------------------------
async function loadTasks() {
    const loading = document.getElementById('loading');
    const authWarning = document.getElementById('auth-warning');
    const timelineView = document.getElementById('timeline-view');

    if (loading) loading.style.display = 'block';
    if (authWarning) authWarning.style.display = 'none';

    try {
        const response = await fetch('/api/tasks');
        if (response.status === 401) {
            if (authWarning) authWarning.style.display = 'flex';
            if (loading) loading.style.display = 'none';
            return;
        }

        if (!response.ok) throw new Error('Error fetching tasks');

        const data = await response.json();
        currentUserEmail = data.user_email || '';
        currentEnrolledCourses = data.enrolled_courses || [];
        const userEmailEl = document.getElementById('user-email-display');
        if (userEmailEl) userEmailEl.textContent = currentUserEmail;
        const now = new Date();
        allUpcomingTasks = [];
        allOverdueTasks = [];
        allNoDateTasks = [];
        allCompletedTasks = [];
        tasksMap.clear();

        (data.tasks_with_dates || []).forEach(task => {
            const dueDate = new Date(task.due_date);
            
            if (task.classroom_status === 'ENTREGADA' || task.classroom_status === 'CALIFICADA') {
                task.status = 'done';
            }

            const isDone = task.status === 'done';
            classifyTaskMission(task, dueDate, now);
            tasksMap.set(String(task.id), task);

            if (isDone) {
                allCompletedTasks.push(task);
            } else if (dueDate < now) {
                task.mission_type = 'rescue';
                allOverdueTasks.push(task);
            } else {
                allUpcomingTasks.push(task);
            }
        });

        (data.tasks_without_dates || []).forEach(task => {
            if (task.classroom_status === 'ENTREGADA' || task.classroom_status === 'CALIFICADA') {
                task.status = 'done';
            }

            const isDone = task.status === 'done';
            classifyTaskMission(task, null, now);
            tasksMap.set(String(task.id), task);

            if (isDone) {
                allCompletedTasks.push(task);
            } else {
                task.mission_type = 'open';
                allNoDateTasks.push(task);
            }
        });

        renderCoursesFilter();
        applyAllFilters();
        renderTasks(allCompletedTasks, 'completed-tasks');
        renderTasks(allOverdueTasks, 'overdue-tasks');
        renderTasks(allNoDateTasks, 'no-date-tasks');

        const completedCountEl = document.getElementById('completed-count');
        if (completedCountEl) completedCountEl.textContent = allCompletedTasks.length;

        const overdueCountEl = document.getElementById('overdue-count');
        if (overdueCountEl) overdueCountEl.textContent = allOverdueTasks.length;

        const overdueSection = document.getElementById('overdue-section');
        if (overdueSection) {
            overdueSection.style.display = allOverdueTasks.length === 0 ? 'none' : 'block';
        }

        const noDateCount = document.getElementById('no-date-count');
        if (noDateCount) noDateCount.textContent = allNoDateTasks.length;

        updateProgressBars();
        updateMissionCounts();
        renderMiniCalendar();

        if (timelineView) timelineView.style.display = 'block';

    } catch (error) {
        console.error("Error loading tasks:", error);
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

function classifyTaskMission(task, dueDate, now) {
    const titleLower = (task.title || '').toLowerCase();
    const descLower = (task.description || '').toLowerCase();

    if (task.classroom_status === 'DEVUELTA' || (task.assigned_grade !== null && task.assigned_grade !== undefined && task.assigned_grade < 70)) {
        task.mission_type = 'special';
        task.estimated_hours = 1.0;
        return;
    }

    if (!dueDate) {
        task.mission_type = 'open';
        task.estimated_hours = 1.0;
        return;
    }

    if (titleLower.includes('trámite') || titleLower.includes('comprobante') || titleLower.includes('imss') || descLower.includes('subir el comprobante')) {
        task.mission_type = 'daily';
        task.estimated_hours = 0.2;
        return;
    }

    if (titleLower.includes('proyecto') || titleLower.includes('final') || titleLower.includes('act apre s 1 b') || titleLower.includes('act apre s 1 c') || titleLower.includes('act apre s 4 a')) {
        task.mission_type = 'main';
        task.estimated_hours = 4.0;
        return;
    }

    task.mission_type = 'secondary';
    task.estimated_hours = 1.5;
}

// -------------------------------------------------------------
// CAMPANA DE NOTIFICACIONES
// -------------------------------------------------------------
function toggleAnnouncementsDropdown() {
    const dd = document.getElementById('bell-dropdown');
    if (!dd) return;
    dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
}

document.addEventListener('mousedown', (e) => {
    const dd = document.getElementById('bell-dropdown');
    const btn = document.getElementById('btn-bell');
    if (dd && dd.style.display !== 'none') {
        if (!dd.contains(e.target) && !btn.contains(e.target) && !btn.closest('button')) {
            dd.style.display = 'none';
        }
    }
});

async function loadAnnouncements() {
    try {
        const res = await fetch('/api/announcements');
        if (!res.ok) return;
        const data = await res.json();
        const list = data.announcements || [];
        cachedAnnouncements = list;
        const badge = document.getElementById('bell-badge');
        const container = document.getElementById('bell-announcements-list');

        if (!badge || !container) return;

        if (list.length > 0) {
            badge.textContent = list.length;
            badge.style.display = 'flex';
            container.innerHTML = '';
            list.forEach(a => {
                container.innerHTML += `
                    <div class="p-2.5 rounded-xl bg-cantera-50 dark:bg-slate-800/80 border border-cantera-200 dark:border-slate-700 flex flex-col gap-1 shadow-sm">
                        <div class="flex justify-between items-center">
                            <span class="font-bold text-amber-700 dark:text-amber-300 truncate pr-1">${a.course_name}</span>
                            <span class="text-[10px] text-slate-400 shrink-0">${a.source}</span>
                        </div>
                        <p class="text-cantera-800 dark:text-slate-200 text-xs leading-relaxed">${a.content}</p>${a.link ? `<a href="${a.link}" target="_blank" class="self-end text-indigo-600 dark:text-indigo-400 hover:underline text-[10px] font-semibold mt-0.5 flex items-center gap-1">Ver aviso <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a>` : ''}
                    </div>
                `;
            });
        } else {
            badge.style.display = 'none';
            container.innerHTML = `<p class="text-slate-500 italic text-center py-3">No hay avisos recientes</p>`;
        }
        renderMiniCalendar();
    } catch(e) {}
}

// -------------------------------------------------------------
// FILTROS Y CALENDARIO INTERACTIVO
// -------------------------------------------------------------
function filterByCalendarDay(day) {
    if (selectedCalendarDay === day) {
        selectedCalendarDay = null;
    } else {
        selectedCalendarDay = day;
    }
    renderMiniCalendar();
    applyAllFilters();
}

function clearCalendarDayFilter() {
    selectedCalendarDay = null;
    renderMiniCalendar();
    applyAllFilters();
}

function changeTimelineSort(mode) {
    currentSortMode = mode;
    applyAllFilters();
}

function applyAllFilters() {
    let filtered = [...allUpcomingTasks];

    if (currentMissionFilter === 'open') {
        filtered = [...allNoDateTasks];
    }

    const titleEl = document.getElementById('current-view-title');
    const clearBtn = document.getElementById('btn-clear-day-filter');

    if (selectedCalendarDay !== null) {
        filtered = filtered.filter(t => {
            if (!t.due_date) return false;
            return new Date(t.due_date).getDate() === selectedCalendarDay;
        });
        if (titleEl) titleEl.textContent = `Misiones del día ${selectedCalendarDay}`;
        if (clearBtn) clearBtn.style.display = 'inline-flex';
    } else {
        if (clearBtn) clearBtn.style.display = 'none';
        if (titleEl) {
            if (currentMissionFilter === 'main') titleEl.textContent = "Misión Principal (Bloques)";
            else if (currentMissionFilter === 'secondary') titleEl.textContent = "Misiones Secundarias";
            else if (currentMissionFilter === 'daily') titleEl.textContent = "Misiones Diarias (Rápidas)";
            else if (currentMissionFilter === 'special') titleEl.textContent = "Misiones Especiales (Mejora)";
            else if (currentMissionFilter === 'rescue') titleEl.textContent = "Misiones de Rescate (Tardías)";
            else if (currentMissionFilter === 'open') titleEl.textContent = "Misiones Abiertas (A tu ritmo)";
            else titleEl.textContent = "Próximas entregas";
        }
    }

    if (selectedCourses.size > 0) {
        filtered = filtered.filter(t => selectedCourses.has(t.course_name));
    }

    if (currentMissionFilter !== 'all' && currentMissionFilter !== 'open') {
        filtered = filtered.filter(t => t.mission_type === currentMissionFilter);
    }

    if (currentSortMode === 'urgency') {
        filtered.sort((a, b) => {
            if (!a.due_date) return 1;
            if (!b.due_date) return -1;
            return new Date(a.due_date) - new Date(b.due_date);
        });
    } else if (currentSortMode === 'importance') {
        const priority = { 'main': 1, 'daily': 2, 'secondary': 3, 'special': 4, 'rescue': 5, 'open': 6 };
        filtered.sort((a, b) => (priority[a.mission_type] || 3) - (priority[b.mission_type] || 3));
    } else if (currentSortMode === 'course') {
        filtered.sort((a, b) => (a.course_name || '').localeCompare(b.course_name || ''));
    }

    renderTasks(filtered, 'timeline');
}

function renderCoursesFilter() {
    const listEl = document.getElementById('courses-filter-list');
    if (!listEl) return;
    listEl.innerHTML = '';

    // Priorizar materias inscritas reales devueltas por Google Classroom
    let courses = [];
    if (currentEnrolledCourses && currentEnrolledCourses.length > 0) {
        courses = currentEnrolledCourses.map(c => typeof c === 'string' ? c : (c.name || '')).filter(Boolean);
    } else {
        const all = [...allUpcomingTasks, ...allCompletedTasks, ...allOverdueTasks, ...allNoDateTasks];
        courses = [...new Set(all.map(t => t.course_name).filter(Boolean))];
    }

    if (courses.length === 0) {
        listEl.innerHTML = `<p class="text-cantera-600 dark:text-slate-500 italic text-[11px] py-1">Sin materias registradas</p>`;
        return;
    }

    courses.forEach(course => {
        const isSelected = selectedCourses.has(course);
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center justify-between ${
            isSelected 
                ? 'bg-indigo-900/30 text-indigo-700 dark:text-indigo-200 border border-indigo-500 shadow-sm' 
                : 'text-cantera-700 dark:text-slate-400 hover:text-cantera-900 dark:hover:text-slate-200 hover:bg-cantera-200/50 dark:hover:bg-slate-800/60'
        }`;

        btn.innerHTML = `
            <span class="truncate pr-2">${course}</span>${isSelected ? '<i class="fa-solid fa-check text-indigo-600 dark:text-indigo-400 text-[10px]"></i>' : ''}
        `;

        btn.onclick = () => toggleCourseSelection(course);
        listEl.appendChild(btn);
    });
}

function toggleCourseSelection(course) {
    if (selectedCourses.has(course)) selectedCourses.delete(course);
    else selectedCourses.add(course);
    renderCoursesFilter();
    applyAllFilters();
}

function clearCourseSelection() {
    selectedCourses.clear();
    renderCoursesFilter();
    applyAllFilters();
}

function setMissionFilter(filter) {
    currentMissionFilter = filter;
    ['all', 'main', 'secondary', 'daily', 'special', 'rescue', 'open'].forEach(f => {
        const btn = document.getElementById(`btn-filter-${f}`);
        if (!btn) return;
        if (f === filter) {
            btn.className = "w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-cantera-200 dark:bg-slate-800 text-indigo-700 dark:text-indigo-300 border border-cantera-300 dark:border-slate-700 font-semibold";
        } else {
            btn.className = "w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-cantera-700 dark:text-slate-400 hover:bg-cantera-100 dark:hover:bg-slate-800/50";
        }
    });
    applyAllFilters();
}

function updateMissionCounts() {
    let base = allUpcomingTasks;
    if (selectedCourses.size > 0) {
        base = base.filter(t => selectedCourses.has(t.course_name));
    }
    const cAll = document.getElementById('count-all');
    const cMain = document.getElementById('count-main');
    const cSec = document.getElementById('count-secondary');
    const cDaily = document.getElementById('count-daily');
    const cSpecial = document.getElementById('count-special');
    const cRescue = document.getElementById('count-rescue');
    const cOpen = document.getElementById('count-open');

    if (cAll) cAll.textContent = base.length;
    if (cMain) cMain.textContent = base.filter(t => t.mission_type === 'main').length;
    if (cSec) cSec.textContent = base.filter(t => t.mission_type === 'secondary').length;
    if (cDaily) cDaily.textContent = base.filter(t => t.mission_type === 'daily').length;
    if (cSpecial) cSpecial.textContent = base.filter(t => t.mission_type === 'special').length;
    if (cRescue) cRescue.textContent = allOverdueTasks.length;
    if (cOpen) cOpen.textContent = allNoDateTasks.length;
}

function toggleProgressMetric() {
    metricMode = metricMode === 'tasks' ? 'hours' : 'tasks';
    const label = document.getElementById('metric-btn-label');
    if (label) label.textContent = metricMode === 'tasks' ? 'Por Tareas' : 'Por Horas';
    updateProgressBars();
}

// -------------------------------------------------------------
// REGLA ESTRICTA DE RACHA
// -------------------------------------------------------------
function updateProgressBars() {
    const all = [...allUpcomingTasks, ...allCompletedTasks, ...allOverdueTasks, ...allNoDateTasks];
    if (all.length === 0) return;

    let todayDone = 0;
    let todayTotal = 0;

    let countGraded = 0;
    let countSubmitted = 0;
    let countPending = 0;

    const academicToday = getAcademicDateString();

    all.forEach(t => {
        const isGraded = t.classroom_status === 'CALIFICADA';
        const isSubmitted = t.classroom_status === 'ENTREGADA' || t.status === 'done';
        const isDone = isGraded || isSubmitted;

        const taskDay = t.due_date ? t.due_date.split('T')[0] : '';
        const isToday = taskDay === academicToday && t.mission_type !== 'rescue';
        
        if (isToday) {
            todayTotal++;
            if (isDone) todayDone++;
        }

        if (isGraded) countGraded++;
        else if (isSubmitted) countSubmitted++;
        else countPending++;
    });

    let todayPct = 0;
    if (todayTotal > 0) {
        todayPct = Math.min(100, Math.round((todayDone / todayTotal) * 100));
    }

    const pBar = document.getElementById('progress-today-bar');
    const pText = document.getElementById('progress-today-text');
    if (pBar) pBar.style.width = `${todayPct}%`;
    if (pText) pText.textContent = `${todayPct}%`;

    const totalAll = all.length || 1;
    const pctGraded = Math.round((countGraded / totalAll) * 100);
    const pctSubmitted = Math.round((countSubmitted / totalAll) * 100);
    const pctTotalCompleted = Math.min(100, pctGraded + pctSubmitted);

    const barGraded = document.getElementById('bar-seg-graded');
    const barSub = document.getElementById('bar-seg-submitted');
    const triText = document.getElementById('progress-tri-text');
    const lblGraded = document.getElementById('tri-graded-label');
    const lblSub = document.getElementById('tri-submitted-label');

    if (barGraded) barGraded.style.width = `${pctGraded}%`;
    if (barSub) barSub.style.width = `${pctSubmitted}%`;
    if (triText) triText.textContent = `${pctTotalCompleted}%`;
    if (lblGraded) lblGraded.textContent = `${countGraded} calificadas`;
    if (lblSub) lblSub.textContent = `${countSubmitted} en revisión`;

    const flameEl = document.getElementById('torch-flame');
    const streakText = document.getElementById('streak-text');
    if (flameEl && streakText) {
        if (todayTotal > 0 && todayPct === 100) {
            flameEl.setAttribute('fill', 'url(#flame-gradient)');
            streakText.textContent = '1 día de racha';
            streakText.className = 'text-xs font-bold text-amber-600 dark:text-amber-400 tracking-tight';
        } else {
            flameEl.setAttribute('fill', '#A8A29E');
            streakText.textContent = '0 días de racha';
            streakText.className = 'text-xs font-bold text-cantera-600 dark:text-slate-400 tracking-tight';
        }
    }
}

// -------------------------------------------------------------
// CALENDARIO INTERACTIVO CON 4 PUNTOS SEMÁNTICOS
// -------------------------------------------------------------
function renderMiniCalendar() {
    const calEl = document.getElementById('mini-calendar');
    if (!calEl) return;
    calEl.innerHTML = '';

    const daysOfWeek = ['D', 'L', 'M', 'M', 'J', 'V', 'S'];
    daysOfWeek.forEach(d => {
        calEl.innerHTML += `<span class="text-[11px] text-cantera-600 dark:text-slate-500 font-bold">${d}</span>`;
    });

    const now = new Date();
    const mLabel = document.getElementById('cal-month-label');
    if (mLabel) mLabel.textContent = now.toLocaleString('es-ES', { month: 'short' }).toUpperCase();

    const year = now.getFullYear();
    const month = now.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const totalDays = new Date(year, month + 1, 0).getDate();

    for (let i = 0; i < firstDay; i++) {
        calEl.innerHTML += `<span></span>`;
    }

    const dayStatus = {};

    [...allUpcomingTasks, ...allCompletedTasks, ...allOverdueTasks].forEach(t => {
        if (t.due_date) {
            const d = new Date(t.due_date).getDate();
            if (!dayStatus[d]) dayStatus[d] = { pending: false, done: false, exam: false, announcement: false };
            
            const titleLower = (t.title || '').toLowerCase();
            const isExam = titleLower.includes('examen') || titleLower.includes('parcial') || titleLower.includes('evaluac') || titleLower.includes('departamental');
            if (isExam) dayStatus[d].exam = true;

            const isDone = t.status === 'done' || t.classroom_status === 'ENTREGADA' || t.classroom_status === 'CALIFICADA';
            if (isDone) dayStatus[d].done = true;
            else dayStatus[d].pending = true;
        }
    });

    cachedAnnouncements.forEach(a => {
        if (a.date) {
            const d = new Date(a.date).getDate();
            if (!dayStatus[d]) dayStatus[d] = { pending: false, done: false, exam: false, announcement: false };
            dayStatus[d].announcement = true;
        }
    });

    for (let day = 1; day <= totalDays; day++) {
        const info = dayStatus[day];
        const isToday = day === now.getDate();
        const isSelected = selectedCalendarDay === day;

        let dotsHtml = '';
        if (info) {
            dotsHtml = `<div class="flex items-center justify-center gap-0.5 mt-0.5">`;
            if (info.pending) dotsHtml += `<span class="w-1.5 h-1.5 rounded-full bg-amber-500" title="Pendiente"></span>`;
            if (info.done) dotsHtml += `<span class="w-1.5 h-1.5 rounded-full bg-emerald-500" title="Entregada"></span>`;
            if (info.exam) dotsHtml += `<span class="w-1.5 h-1.5 rounded-full bg-indigo-500" title="Examen"></span>`;
            if (info.announcement) dotsHtml += `<span class="w-1.5 h-1.5 rounded-full bg-rose-500" title="Aviso"></span>`;
            dotsHtml += `</div>`;
        }

        let selectRing = isSelected ? 'ring-2 ring-indigo-500 font-extrabold bg-indigo-50 dark:bg-indigo-950/60' : '';
        let todayClass = isToday ? 'bg-indigo-600 text-white font-bold' : 'text-cantera-800 dark:text-slate-400 hover:bg-cantera-200 dark:hover:bg-slate-800/60';

        calEl.innerHTML += `
            <button onclick="filterByCalendarDay(${day})" class="h-8 flex flex-col items-center justify-center rounded-lg ${todayClass}${selectRing} transition-all cursor-pointer">
                <span class="leading-none">${day}</span>${dotsHtml}
            </button>
        `;
    }
}

// -------------------------------------------------------------
// RENDER DE TARJETAS
// -------------------------------------------------------------
function renderTasks(tasks, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    if (!tasks || tasks.length === 0) {
        if (containerId === 'timeline') {
            const allTotal = allUpcomingTasks.length + allCompletedTasks.length + allOverdueTasks.length + allNoDateTasks.length;
            if (allTotal === 0) {
                if (currentEnrolledCourses && currentEnrolledCourses.length > 0) {
                    container.innerHTML = `
                        <div class="p-8 text-center bg-white dark:bg-night-900 border border-cantera-300 dark:border-slate-800 rounded-2xl max-w-lg mx-auto shadow-sm my-6">
                            <div class="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 flex items-center justify-center mx-auto mb-3 text-2xl">
                                <i class="fa-solid fa-circle-check"></i>
                            </div>
                            <h3 class="text-lg font-bold text-cantera-900 dark:text-white">¡Estás al día!</h3>
                            <p class="text-xs text-cantera-600 dark:text-slate-400 mt-2 leading-relaxed">
                                No se encontraron tareas pendientes asignadas en Google Classroom para tus <strong>${currentEnrolledCourses.length} materias inscritas</strong>.
                            </p>
                            <div class="mt-4 flex flex-wrap justify-center gap-1.5">
                                ${currentEnrolledCourses.map(c => `<span class="px-2.5 py-1 rounded-lg text-xs bg-cantera-200 dark:bg-slate-800 text-cantera-800 dark:text-slate-300 font-medium">${typeof c === 'string' ? c : c.name}</span>`).join('')}
                            </div>
                        </div>
                    `;
                    return;
                } else {
                    container.innerHTML = `
                        <div class="p-8 text-center bg-white dark:bg-night-900 border border-amber-500/30 rounded-2xl max-w-lg mx-auto shadow-sm my-6">
                            <div class="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-500 flex items-center justify-center mx-auto mb-3 text-2xl">
                                <i class="fa-solid fa-graduation-cap"></i>
                            </div>
                            <h3 class="text-lg font-bold text-cantera-900 dark:text-white">No se encontraron materias en esta cuenta</h3>
                            <p class="text-xs text-slate-400 mt-2 leading-relaxed">
                                Iniciaste sesión con la cuenta de Google:<br>
                                <span class="inline-block px-3 py-1 mt-1 font-mono text-xs font-semibold text-amber-500 dark:text-amber-400 bg-amber-500/10 rounded-lg border border-amber-500/20">${currentUserEmail || 'Cuenta activa'}</span>
                            </p>
                            <div class="p-4 mt-4 text-left bg-slate-950/40 border border-slate-800 rounded-xl text-xs text-slate-300 space-y-2">
                                <p class="font-semibold text-white flex items-center gap-1.5">
                                    <i class="fa-solid fa-circle-info text-amber-400"></i> ¿Por qué no aparecen materias?
                                </p>
                                <p>• Muchas instituciones educativas asignan Google Classroom en un <strong>correo escolar o institucional</strong> (ej. <code>@alumno.ipn.mx</code>, <code>@escuela.edu.mx</code>) y no en tu Gmail personal.</p>
                                <p>• Si tus materias están en otra cuenta de Google, cierra sesión e inicia con la cuenta institucional correcta.</p>
                            </div>
                            <a href="/logout" class="inline-flex items-center gap-2 mt-5 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md transition-all">
                                <i class="fa-solid fa-arrow-right-from-bracket"></i> Cambiar de cuenta de Google
                            </a>
                        </div>
                    `;
                    return;
                }
            }
        }
        container.innerHTML = `<p class="text-cantera-600 dark:text-slate-500 italic text-sm py-4 text-center">No hay misiones en esta vista</p>`;
        return;
    }

    tasks.forEach(task => {
        const taskId = String(task.id);
        tasksMap.set(taskId, task);

        const isDone = task.status === 'done' || task.classroom_status === 'ENTREGADA' || task.classroom_status === 'CALIFICADA';
        const card = document.createElement('div');
        
        let classroomBadge = '';
        if (task.classroom_status === 'CALIFICADA') {
            const gradeStr = task.assigned_grade !== null ? `${task.assigned_grade}/${task.max_points || 100}` : 'Calificada';
            classroomBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800"><i class="fa-solid fa-check-double mr-1"></i>${gradeStr}</span>`;
        } else if (task.classroom_status === 'ENTREGADA') {
            classroomBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-800"><i class="fa-solid fa-clock mr-1"></i>En revisión</span>`;
        } else if (task.classroom_status === 'SUBIDA_SIN_ENTREGAR') {
            classroomBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 animate-pulse"><i class="fa-solid fa-triangle-exclamation mr-1"></i>¡Subida! Falta entregar</span>`;
        } else if (task.classroom_status === 'DEVUELTA') {
            classroomBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-800"><i class="fa-solid fa-rotate-left mr-1"></i>Devuelta para corregir</span>`;
        } else {
            classroomBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-cantera-100 dark:bg-slate-800 text-cantera-600 dark:text-slate-400 border border-cantera-300 dark:border-slate-700">Sin entregar</span>`;
        }

        let borderHex = '#6366F1';
        let missionBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-800"><i class="fa-solid fa-shield-halved mr-1"></i>Secundaria</span>`;

        if (task.mission_type === 'main') {
            borderHex = '#F59E0B';
            missionBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800"><i class="fa-solid fa-khanda mr-1"></i>Principal</span>`;
        } else if (task.mission_type === 'daily') {
            borderHex = '#0EA5E9';
            missionBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-sky-100 dark:bg-sky-950 text-sky-800 dark:text-sky-300 border border-sky-300 dark:border-sky-800"><i class="fa-solid fa-bolt mr-1"></i>Diaria</span>`;
        } else if (task.mission_type === 'special') {
            borderHex = '#A855F7';
            missionBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-800"><i class="fa-solid fa-wand-magic-sparkles mr-1"></i>Especial</span>`;
        } else if (task.mission_type === 'rescue') {
            borderHex = '#F97316';
            missionBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-orange-100 dark:bg-orange-950 text-orange-800 dark:text-orange-300 border border-orange-300 dark:border-orange-800"><i class="fa-solid fa-life-ring mr-1"></i>Rescate</span>`;
        } else if (task.mission_type === 'open') {
            borderHex = '#14B8A6';
            missionBadge = `<span class="text-xs font-semibold px-2 py-0.5 rounded bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-300 dark:border-teal-800"><i class="fa-solid fa-compass mr-1"></i>Abierta</span>`;
        }

        const dateStr = formatRelativeDate(task.due_date);

        if (isDone) {
            card.className = "bg-cantera-50/80 dark:bg-night-950/60 border border-cantera-300 dark:border-slate-800 rounded-lg px-4 py-3 flex items-center justify-between text-cantera-600 dark:text-slate-400 shadow-sm opacity-85 hover:opacity-100 transition-opacity";
            card.style.borderLeft = `5px solid #10B981`;
            card.innerHTML = `
                <divimport os
import json
import uuid
import urllib.request
import urllib.parse
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

try:
    from services.classroom_service import fetch_tasks, get_announcements_and_alerts
except ImportError:
    from classroom_service import fetch_tasks, get_announcements_and_alerts

from services.ai_service import ask_copilot

user_sessions = {}

SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.me.readonly',
    'https://www.googleapis.com/auth/classroom.student-submissions.me.readonly',
    'https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly',
    'https://www.googleapis.com/auth/classroom.announcements.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def load_client_secrets():
    with open('credentials.json', 'r') as f:
        data = json.load(f)
        cfg = data.get('web') or data.get('installed') or {}
        return cfg.get('client_id'), cfg.get('client_secret')

def restore_and_refresh_credentials(creds_json: str):
    if not creds_json:
        return None
    try:
        data = json.loads(creds_json)
        creds = Credentials.from_authorized_user_info(data, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleRequest())
            except Exception as e:
                print(f"No se pudo refrescar token: {e}")
        return creds
    except Exception as e:
        print(f"Error restaurando credenciales: {e}")
        return None

app = FastAPI(title="Agora")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# Rutas OAuth
@app.get("/auth/login")
async def auth_login(request: Request):
    client_id, _ = load_client_secrets()
    base = str(request.base_url).rstrip('/')
    redirect_uri = "https://agora-app-leox.onrender.com/auth/callback" if "onrender.com" in base else f"{base}/auth/callback"
    
    scopes_str = "%20".join(SCOPES)
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"response_type=code&"
        f"scope={scopes_str}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = None, error: str = None):
    if error or not code:
        print(f"Error de Google OAuth: {error}")
        return RedirectResponse(url="/")

    client_id, client_secret = load_client_secrets()
    base = str(request.base_url).rstrip('/')
    redirect_uri = "https://agora-app-leox.onrender.com/auth/callback" if "onrender.com" in base else f"{base}/auth/callback"

    try:
        token_url = "https://oauth2.googleapis.com/token"
        payload = urllib.parse.urlencode({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }).encode("utf-8")

        req = urllib.request.Request(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))

        creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )

        session_id = str(uuid.uuid4())
        user_sessions[session_id] = creds.to_json()

        try:
            with open("token.json", "w") as f:
                f.write(creds.to_json())
        except Exception:
            pass

        print(f"Autenticacion completada con exito en Render: {session_id}")

        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="agora_session",
            value=session_id,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
        return response
    except Exception as e:
        print(f"Error en canje directo de token: {e}")
        traceback.print_exc()
        return RedirectResponse(url="/", status_code=303)

@app.get("/auth/logout")
async def auth_logout(request: Request):
    session_id = request.cookies.get("agora_session")
    if session_id in user_sessions:
        del user_sessions[session_id]
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("agora_session")
    return response

# API Tasks universal con auto-refresco
@app.get("/api/tasks")
async def get_tasks(request: Request):
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json)

    if not creds:
        if os.path.exists('token.json'):
            try:
                creds = restore_and_refresh_credentials(open('token.json').read())
            except Exception:
                creds = None

    if not creds:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    try:
        try:
            tasks = fetch_tasks(creds=creds)
        except TypeError:
            tasks = fetch_tasks()

        tasks_with_dates = [t for t in tasks if t.get('due_date')]
        tasks_without_dates = [t for t in tasks if not t.get('due_date')]
        return {
            "tasks_with_dates": tasks_with_dates,
            "tasks_without_dates": tasks_without_dates
        }
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/announcements")
async def api_announcements(request: Request):
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json)

    try:
        try:
            alerts = get_announcements_and_alerts(creds=creds)
        except TypeError:
            alerts = get_announcements_and_alerts()
        return {"announcements": alerts}
    except Exception:
        return {"announcements": []}

@app.post("/api/copilot/ask")
async def ask_ai(request: Request):
    data = await request.json()
    provider = data.get("provider", "gemini")
    mentor = data.get("mentor", "newton")
    task_context = data.get("task_context", {})
    messages = data.get("messages", [])

    response_text = ask_copilot(
        provider=provider,
        mentor=mentor,
        task_context=task_context,
        messages=messages
    )
    return {"response": response_text}
