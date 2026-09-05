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
// CARGA Y SEPARACIÓN DE TAREAS (Activas vs Entregadas)
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
        const now = new Date();
        allUpcomingTasks = [];
        allOverdueTasks = [];
        allNoDateTasks = [];
        allCompletedTasks = [];
        tasksMap.clear();

        // Tareas con fecha
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

        // Tareas sin fecha (Misiones Abiertas)
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
                        <p class="text-cantera-800 dark:text-slate-200 text-xs leading-relaxed">${a.content}</p>
                        ${a.link ? `<a href="${a.link}" target="_blank" class="self-end text-indigo-600 dark:text-indigo-400 hover:underline text-[10px] font-semibold mt-0.5 flex items-center gap-1">Ver aviso <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a>` : ''}
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
// FILTROS Y ORDENAMIENTO (Con Filtro de Día)
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

    // Si se seleccionó un día en el calendario, incluye también las sin fecha que apliquen
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

    const all = [...allUpcomingTasks, ...allCompletedTasks, ...allOverdueTasks, ...allNoDateTasks];
    const courses = [...new Set(all.map(t => t.course_name).filter(Boolean))];

    if (courses.length === 0) {
        listEl.innerHTML = `<p class="text-cantera-600 dark:text-slate-500 italic text-[11px] py-1">Sin materias activas</p>`;
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
            <span class="truncate pr-2">${course}</span>
            ${isSelected ? '<i class="fa-solid fa-check text-indigo-600 dark:text-indigo-400 text-[10px]"></i>' : ''}
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

    // Barra Tripartita Global
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

    // Antorcha de Prometeo
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

    // Mapa de los 4 estados por día
    const dayStatus = {};

    // 1. Tareas (Pendientes, Entregadas, Exámenes)
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

    // 2. Avisos de profesores
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
            <button onclick="filterByCalendarDay(${day})" class="h-8 flex flex-col items-center justify-center rounded-lg ${todayClass} ${selectRing} transition-all cursor-pointer">
                <span class="leading-none">${day}</span>
                ${dotsHtml}
            </button>
        `;
    }
}

// -------------------------------------------------------------
// RENDER DE TARJETAS (Borde de 5px Inquebrantable)
// -------------------------------------------------------------
function renderTasks(tasks, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    if (!tasks || tasks.length === 0) {
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

        // Fila compacta de entregada
        if (isDone) {
            card.className = "bg-cantera-50/80 dark:bg-night-950/60 border border-cantera-300 dark:border-slate-800 rounded-lg px-4 py-3 flex items-center justify-between text-cantera-600 dark:text-slate-400 shadow-sm opacity-85 hover:opacity-100 transition-opacity";
            card.style.borderLeft = `5px solid #10B981`;
            card.innerHTML = `
                <div class="flex items-center gap-3 min-w-0 pr-4">
                    <input type="checkbox" checked onchange="toggleStatus('${taskId}', false)" class="w-4 h-4 accent-emerald-500 rounded cursor-pointer" title="Marcar como pendiente">
                    <span class="text-xs px-2 py-0.5 rounded bg-cantera-200 dark:bg-slate-800 text-cantera-700 dark:text-slate-400 truncate">${task.course_name}</span>
                    <span class="text-sm line-through text-cantera-500 dark:text-slate-500 truncate">${task.title}</span>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                    ${classroomBadge}
                    <button onclick="openIgnisWorkspace('${taskId}')" class="text-xs text-cantera-700 dark:text-slate-400 hover:text-indigo-600 px-2.5 py-1 rounded bg-cantera-100 dark:bg-slate-800 border border-cantera-300 dark:border-slate-700 flex items-center gap-1.5">
                        <i class="fa-solid fa-fire text-amber-500"></i> Ignis
                    </button>
                </div>
            `;
            container.appendChild(card);
            return;
        }

        // Tarea activa
        card.className = "bg-white dark:bg-night-800/90 border border-cantera-300 dark:border-slate-700/80 rounded-xl p-5 flex flex-col gap-4 shadow-sm hover:shadow-md transition-all";
        card.style.borderLeft = `5px solid ${borderHex}`;

        card.innerHTML = `
            <div class="flex-1 w-full flex flex-col">
                <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-semibold px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">${task.course_name}</span>
                        ${missionBadge}
                        ${classroomBadge}
                    </div>
                    <span class="text-xs font-semibold text-cantera-700 dark:text-slate-300"><i class="fa-regular fa-clock mr-1 text-slate-400"></i>${dateStr}</span>
                </div>

                <h3 class="text-xl font-bold text-cantera-900 dark:text-slate-100 mb-2">
                    <a href="${task.link}" target="_blank" class="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors flex items-center gap-1.5">
                        ${task.title}
                        <i class="fa-solid fa-arrow-up-right-from-square text-xs opacity-50"></i>
                    </a>
                </h3>

                <p class="text-sm text-cantera-700 dark:text-slate-300 whitespace-pre-line line-clamp-3 mb-4 leading-relaxed">${task.description || 'Sin descripción.'}</p>

                <details class="mb-4 group">
                    <summary class="cursor-pointer text-xs font-medium text-cantera-600 dark:text-slate-400 hover:text-cantera-900 dark:hover:text-slate-200 list-none flex items-center gap-1">
                        <i class="fa-solid fa-pen-to-square"></i>
                        <span>Notas personales</span>
                    </summary>
                    <div class="mt-2 flex flex-col gap-2">
                        <textarea id="notes-${taskId}" rows="2" class="w-full bg-cantera-50 dark:bg-slate-900 border border-cantera-300 dark:border-slate-700 rounded-lg p-2 text-sm text-cantera-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500 resize-none">${task.notes || ''}</textarea>
                        <button onclick="saveNotes('${taskId}')" class="self-end text-xs bg-cantera-100 dark:bg-slate-700 hover:bg-cantera-200 text-cantera-800 dark:text-slate-200 px-3 py-1.5 rounded border border-cantera-300 dark:border-slate-600 font-medium">
                            Guardar notas
                        </button>
                    </div>
                </details>

                <div class="flex items-center justify-between gap-3 pt-3 border-t border-cantera-200 dark:border-slate-700/60 mt-auto">
                    <button onclick="openIgnisWorkspace('${taskId}')" class="text-sm font-semibold bg-indigo-50 dark:bg-indigo-600/20 hover:bg-indigo-100 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30 px-4 py-2 rounded-lg flex items-center gap-2 transition-all">
                        <i class="fa-solid fa-fire text-amber-500"></i> Abrir en Ignis
                    </button>

                    <label class="flex items-center gap-2 cursor-pointer text-sm text-cantera-800 dark:text-slate-300 select-none font-medium">
                        <span>Pendiente</span>
                        <input type="checkbox" onchange="toggleStatus('${taskId}', true)" class="w-5 h-5 accent-emerald-500 rounded cursor-pointer">
                    </label>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function formatRelativeDate(dueStr) {
    if (!dueStr) return 'Sin fecha';
    const due = new Date(dueStr);
    const now = new Date();
    const diffMs = due - now;
    const diffHours = Math.round(diffMs / (1000 * 60 * 60));

    if (diffHours > 0 && diffHours <= 12) {
        return `Vence en ${diffHours}h`;
    }
    if (diffHours > 12 && diffHours <= 24) {
        return `Vence hoy a las ${due.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`;
    }
    return due.toLocaleString('es-ES', { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

async function toggleStatus(taskId, isChecked) {
    const newStatus = isChecked ? 'done' : 'pending';
    try {
        await fetch(`/api/tasks/${taskId}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        setTimeout(loadTasks, 200);
    } catch (error) {
        console.error("Error toggling status:", error);
    }
}

async function saveNotes(taskId) {
    const textarea = document.getElementById(`notes-${taskId}`);
    if (!textarea) return;
    const notesContent = textarea.value;
    const btn = textarea.nextElementSibling;
    if (btn) { btn.textContent = 'Guardando...'; btn.disabled = true; }

    try {
        await fetch(`/api/tasks/${taskId}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notesContent })
        });
        if (btn) {
            btn.textContent = '¡Guardado!';
            btn.classList.add('text-emerald-600');
            setTimeout(() => {
                btn.textContent = 'Guardar notas';
                btn.disabled = false;
                btn.classList.remove('text-emerald-600');
            }, 1500);
        }
    } catch (error) {
        if (btn) { btn.textContent = 'Error'; btn.disabled = false; }
    }
}

// -------------------------------------------------------------
// VISOR DE IGNIS Y DOCUMENTOS
// -------------------------------------------------------------
function openIgnisWorkspace(taskId) {
    const task = typeof taskId === 'object' ? taskId : tasksMap.get(String(taskId));
    if (!task) return;

    currentTaskContext = task;
    const tTitle = document.getElementById('modal-task-title');
    if (tTitle) tTitle.textContent = `${task.course_name}: ${task.title}`;

    autoSelectMentor(task.course_name);
    setupDocumentCarousel(task);

    const chatContainer = document.getElementById('chat-messages');

    if (sessionTaskHistories[task.id]) {
        chatHistory = sessionTaskHistories[task.id].history;
        chatContainer.innerHTML = sessionTaskHistories[task.id].html;
    } else {
        chatHistory = [];
        
        let welcomeMsg = `¡Hola! Soy <strong>Ignis</strong>. Estoy analizando las consignas de <strong>${task.title}</strong> con el visor oficial de la izquierda para guiarte sin regalarte la respuesta. ¿Por dónde empezamos?`;
        if (task.classroom_status === 'DEVUELTA') {
            welcomeMsg = `¡Hola! Tu profesor devolvió <strong>${task.title}</strong> para ajustes. Vamos a revisar los puntos clave para que la vuelvas a entregar impecable.`;
        }

        chatContainer.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-200 dark:border-indigo-500/30">
                    <i class="fa-solid fa-fire text-amber-500 text-xs"></i>
                </div>
                <div class="bg-cantera-50 dark:bg-slate-900 p-3 rounded-2xl rounded-tl-none border border-cantera-300 dark:border-slate-700 text-xs text-cantera-900 dark:text-slate-200 leading-relaxed shadow-sm">
                    ${welcomeMsg}
                </div>
            </div>
        `;
        sessionTaskHistories[task.id] = {
            history: chatHistory,
            html: chatContainer.innerHTML
        };
    }

    const modal = document.getElementById('ignis-workspace-modal');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.remove('hidden');
    }
    setTimeout(() => {
        const inp = document.getElementById('chat-input');
        if (inp) inp.focus();
    }, 80);
}

function closeIgnisWorkspace() {
    const modal = document.getElementById('ignis-workspace-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.add('hidden');
    }
    currentTaskContext = null;
}

document.addEventListener('mousedown', (e) => {
    const modal = document.getElementById('ignis-workspace-modal');
    if (!modal || modal.style.display === 'none') return;
    if (!modal.contains(e.target) && !e.target.closest('button[onclick*="openIgnisWorkspace"]')) {
        closeIgnisWorkspace();
    }
});

function autoSelectMentor(courseName) {
    const name = (courseName || '').toLowerCase();
    const select = document.getElementById('mentor-select');
    if (!select) return;

    if (name.includes('sistema') || name.includes('cálculo') || name.includes('física') || name.includes('circuito') || name.includes('control')) {
        select.value = 'newton';
    } else if (name.includes('program') || name.includes('datos') || name.includes('algoritmo') || name.includes('compilador')) {
        select.value = 'lovelace';
    } else if (name.includes('redes') || name.includes('arquitectura') || name.includes('lógica')) {
        select.value = 'turing';
    } else if (name.includes('taller') || name.includes('lectura') || name.includes('redacción') || name.includes('metodología')) {
        select.value = 'sorjuana';
    } else if (name.includes('salud') || name.includes('médic') || name.includes('anatomía')) {
        select.value = 'osler';
    } else if (name.includes('derecho') || name.includes('legal')) {
        select.value = 'ciceron';
    }
}

function setupDocumentCarousel(task) {
    currentTaskDocs = [];
    currentDocIndex = 0;
    const desc = task.description || '';
    
    try {
        const driveLinks = [...desc.matchAll(/https:\/\/drive\.google\.com\/file\/d\/[^\s\)]+/g)].map(m => m[0]);
        const docMatches = [...desc.matchAll(/--- Documento adjunto: (.*?) ---\n([\s\S]*?)(?=(--- Documento adjunto:|$))/g)];
        
        if (docMatches.length > 0) {
            docMatches.forEach((m, idx) => {
                const docTitle = m.at(1) || 'Documento adjunto';
                const docContent = m.at(2) || '';
                const docLink = driveLinks.at(idx) || task.link;
                currentTaskDocs.push({
                    title: docTitle.trim(),
                    content: docContent.trim(),
                    link: docLink
                });
            });
        } else {
            currentTaskDocs.push({
                title: "Instrucciones de la tarea",
                content: desc || "No hay documento adjunto para esta tarea.",
                link: driveLinks.at(0) || task.link
            });
        }
    } catch (err) {
        currentTaskDocs.push({
            title: "Instrucciones de la tarea",
            content: desc || "No hay documento adjunto.",
            link: task.link
        });
    }

    renderCurrentDoc();
}

function renderCurrentDoc() {
    if (currentTaskDocs.length === 0) return;
    const doc = currentTaskDocs[currentDocIndex];
    document.getElementById('doc-carousel-title').textContent = doc.title;
    document.getElementById('doc-carousel-counter').textContent = `${currentDocIndex + 1}/${currentTaskDocs.length}`;
    document.getElementById('doc-external-link').href = doc.link || currentTaskContext.link;

    const container = document.getElementById('doc-viewer-container');

    if (docViewMode === 'pdf' && doc.link && doc.link.includes('drive.google.com/file/d/')) {
        const fileId = doc.link.split('/d/').at(1).split('/')[0];
        const previewUrl = `https://drive.google.com/file/d/${fileId}/preview`;
        container.innerHTML = `
            <iframe src="${previewUrl}" class="w-full h-full min-h-[500px] border-0 rounded-xl bg-white" allow="autoplay"></iframe>
        `;
    } else {
        container.innerHTML = `<div class="whitespace-pre-wrap p-3 text-xs leading-relaxed text-cantera-900 dark:text-slate-300">${doc.content}</div>`;
    }

    document.getElementById('doc-prev-btn').disabled = currentDocIndex === 0;
    document.getElementById('doc-next-btn').disabled = currentDocIndex >= currentTaskDocs.length - 1;
}

function prevDoc() {
    if (currentDocIndex > 0) {
        currentDocIndex--;
        renderCurrentDoc();
    }
}

function nextDoc() {
    if (currentDocIndex < currentTaskDocs.length - 1) {
        currentDocIndex++;
        renderCurrentDoc();
    }
}

// -------------------------------------------------------------
// CHAT CON IGNIS
// -------------------------------------------------------------
function appendMessage(role, content) {
    const chatContainer = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = "flex items-start gap-3 " + (role === 'user' ? "flex-row-reverse" : "");

    const icon = role === 'user' ?
        `<div class="w-8 h-8 rounded-full bg-cantera-200 dark:bg-slate-700 flex items-center justify-center shrink-0 border border-cantera-300 dark:border-slate-600 text-cantera-800 dark:text-slate-300"><i class="fa-solid fa-user text-xs"></i></div>` :
        `<div class="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-200 dark:border-indigo-500/30"><i class="fa-solid fa-fire text-amber-500 text-xs"></i></div>`;

    const bubbleClass = role === 'user' ?
        "bg-indigo-100 dark:bg-indigo-900/40 p-3 rounded-2xl rounded-tr-none border border-indigo-300 dark:border-indigo-700/50 text-xs text-indigo-950 dark:text-indigo-100 whitespace-pre-wrap max-w-[85%]" :
        "bg-cantera-50 dark:bg-slate-900 p-3.5 rounded-2xl rounded-tl-none border border-cantera-300 dark:border-slate-700 text-xs whitespace-pre-wrap text-cantera-900 dark:text-slate-200 max-w-[85%] leading-relaxed shadow-sm";

    let formattedContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code class="bg-cantera-200 dark:bg-slate-800 text-indigo-600 dark:text-indigo-300 px-1 py-0.5 rounded text-[11px]">$1</code>');

    msgDiv.innerHTML = `${icon}<div class="${bubbleClass}">${formattedContent}</div>`;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    if (currentTaskContext) {
        sessionTaskHistories[currentTaskContext.id] = {
            history: chatHistory,
            html: chatContainer.innerHTML
        };
    }
}

function showTypingIndicator() {
    const chatContainer = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.id = "typing-indicator";
    msgDiv.className = "flex items-start gap-3";
    msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-200 dark:border-indigo-500/30">
            <i class="fa-solid fa-fire text-amber-500 text-xs"></i>
        </div>
        <div class="bg-cantera-50 dark:bg-slate-900 p-3 rounded-2xl rounded-tl-none border border-cantera-300 dark:border-slate-700 text-xs flex gap-1 items-center shadow-sm">
            <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
            <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
            <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
        </div>
    `;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

async function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const btn = document.getElementById('chat-submit-btn');
    const text = input.value.trim();

    if (!text || !currentTaskContext) return;

    input.value = '';
    input.disabled = true;
    btn.disabled = true;

    appendMessage('user', text);
    chatHistory.push({ role: 'user', content: text });

    const provider = document.querySelector('input[name="ai_provider"]:checked').value;
    const mentor = document.getElementById('mentor-select').value;

    showTypingIndicator();

    try {
        const response = await fetch('/api/copilot/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                provider: provider,
                mentor: mentor,
                task_context: {
                    course_name: currentTaskContext.course_name,
                    title: currentTaskContext.title,
                    description: currentTaskContext.description,
                    due_date: currentTaskContext.due_date
                },
                messages: chatHistory
            })
        });

        removeTypingIndicator();
        if (!response.ok) throw new Error('Error from AI service');

        const data = await response.json();
        appendMessage('assistant', data.response);
        chatHistory.push({ role: 'assistant', content: data.response });

    } catch (error) {
        removeTypingIndicator();
        appendMessage('assistant', 'Hubo un error al consultar a Ignis. Por favor intenta de nuevo.');
    } finally {
        input.disabled = false;
        btn.disabled = false;
        input.focus();
    }
}

// -------------------------------------------------------------
// MENÚ DE 3 LÍNEAS Y CALIFICACIONES
// -------------------------------------------------------------
function toggleMainMenu() {
    const drawerEl = document.getElementById('main-menu-drawer');
    if (!drawerEl) return;
    drawerEl.style.display = drawerEl.style.display === 'none' ? 'block' : 'none';
}

function openMentorsModal() {
    toggleMainMenu();
    const el = document.getElementById('modal-mentors');
    if (el) el.style.display = 'flex';
}

function closeMentorsModal() {
    const el = document.getElementById('modal-mentors');
    if (el) el.style.display = 'none';
}

function openTechniquesModal() {
    toggleMainMenu();
    const el = document.getElementById('modal-techniques');
    if (el) el.style.display = 'flex';
}

function closeTechniquesModal() {
    const el = document.getElementById('modal-techniques');
    if (el) el.style.display = 'none';
}

function openGradesModal() {
    toggleMainMenu();
    renderGradesSummary();
    const el = document.getElementById('modal-grades');
    if (el) el.style.display = 'flex';
}

function closeGradesModal() {
    const el = document.getElementById('modal-grades');
    if (el) el.style.display = 'none';
}

function openSettingsModal() {
    toggleMainMenu();
    const el = document.getElementById('modal-settings');
    if (el) el.style.display = 'flex';
}

function closeSettingsModal() {
    const el = document.getElementById('modal-settings');
    if (el) el.style.display = 'none';
}

function renderGradesSummary() {
    const container = document.getElementById('grades-summary-content');
    if (!container) return;
    container.innerHTML = '';

    const all = [...allUpcomingTasks, ...allCompletedTasks, ...allOverdueTasks, ...allNoDateTasks];
    const courses = [...new Set(all.map(t => t.course_name).filter(Boolean))];

    if (courses.length === 0) {
        container.innerHTML = `<p class="text-slate-500 italic text-center py-3">No hay materias registradas.</p>`;
        return;
    }

    courses.forEach(c => {
        const courseTasks = all.filter(t => t.course_name === c);
        const gradedTasks = courseTasks.filter(t => t.classroom_status === 'CALIFICADA' && t.assigned_grade !== null);
        const submittedTasks = courseTasks.filter(t => t.classroom_status === 'ENTREGADA' || t.status === 'done');
        const total = courseTasks.length;

        let avgStr = 'Sin nota aún';
        if (gradedTasks.length > 0) {
            const sumGrades = gradedTasks.reduce((acc, t) => acc + (t.assigned_grade || 0), 0);
            const sumMax = gradedTasks.reduce((acc, t) => acc + (t.max_points || 100), 0);
            const avgPct = Math.round((sumGrades / sumMax) * 100);
            avgStr = `Promedio: ${avgPct}/100`;
        }

        const pctGraded = Math.round((gradedTasks.length / (total || 1)) * 100);
        const pctSub = Math.round((submittedTasks.length / (total || 1)) * 100);

        container.innerHTML += `
            <details class="group p-3 rounded-xl bg-cantera-100 dark:bg-slate-800/80 border border-cantera-200 dark:border-slate-700">
                <summary class="cursor-pointer list-none flex justify-between items-center font-bold">
                    <span class="text-cantera-900 dark:text-slate-200 truncate pr-2">${c}</span>
                    <span class="text-indigo-600 dark:text-indigo-400 shrink-0 text-xs font-extrabold">${avgStr}</span>
                </summary>
                
                <div class="mt-2.5 pt-2 border-t border-cantera-200 dark:border-slate-700/60 space-y-2 text-[11px]">
                    <div class="w-full bg-cantera-200 dark:bg-slate-900 rounded-full h-1.5 overflow-hidden flex">
                        <div class="bg-emerald-500 h-full" style="width: ${pctGraded}%"></div>
                        <div class="bg-indigo-500 h-full" style="width: ${pctSub}%"></div>
                    </div>
                    <div class="flex justify-between text-slate-400">
                        <span>${gradedTasks.length} calificadas</span>
                        <span>${submittedTasks.length} en revisión</span>
                        <span>${total - gradedTasks.length - submittedTasks.length} pendientes</span>
                    </div>

                    <div class="space-y-1 pt-1.5">
                        ${courseTasks.map(t => {
                            let badge = '<span class="text-slate-500">Pendiente</span>';
                            if (t.classroom_status === 'CALIFICADA') {
                                badge = `<span class="text-emerald-500 font-bold">${t.assigned_grade}/${t.max_points || 100}</span>`;
                            } else if (t.classroom_status === 'ENTREGADA' || t.status === 'done') {
                                badge = '<span class="text-indigo-400 font-medium">Entregada</span>';
                            }
                            return `<div class="flex justify-between py-0.5 border-b border-cantera-200/40 dark:border-slate-700/30 truncate"><span class="truncate pr-2">${t.title}</span><span class="shrink-0">${badge}</span></div>`;
                        }).join('')}
                    </div>
                </div>
            </details>
        `;
    });
}let currentTaskContext = null;
let chatHistory = [];
const sessionTaskHistories = {};

const tasksMap = new Map();

let allUpcomingTasks = [];
let allOverdueTasks = [];
let allNoDateTasks = [];
let allCompletedTasks = [];

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

// -------------------------------------------------------------
// TEMPORIZADOR A PRUEBA DE FALLOS
// -------------------------------------------------------------
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

// Atajo de teclado: Barra Espaciadora
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
// CARGA Y SEPARACIÓN DE TAREAS (Activas vs Entregadas)
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
        const now = new Date();
        allUpcomingTasks = [];
        allOverdueTasks = [];
        allNoDateTasks = [];
        allCompletedTasks = [];
        tasksMap.clear();

        // Procesar tareas con fecha
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

        // Procesar tareas sin fecha
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
// CAMPANA DE NOTIFICACIONES (Tablón y Correos)
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
                        <p class="text-cantera-800 dark:text-slate-200 text-xs leading-relaxed">${a.content}</p>
                        ${a.link ? `<a href="${a.link}" target="_blank" class="self-end text-indigo-600 dark:text-indigo-400 hover:underline text-[10px] font-semibold mt-0.5 flex items-center gap-1">Ver aviso <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i></a>` : ''}
                    </div>
                `;
            });
        } else {
            badge.style.display = 'none';
            container.innerHTML = `<p class="text-slate-500 italic text-center py-3">No hay avisos recientes</p>`;
        }
    } catch(e) {}
}

// -------------------------------------------------------------
// FILTROS Y ORDENAMIENTO (Incluye Filtro por Día del Calendario)
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

    // Filtro por Día del Calendario
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
            else titleEl.textContent = "Próximas entregas";
        }
    }

    // Filtro por Materia
    if (selectedCourses.size > 0) {
        filtered = filtered.filter(t => selectedCourses.has(t.course_name));
    }

    // Filtro por Misión
    if (currentMissionFilter !== 'all') {
        filtered = filtered.filter(t => t.mission_type === currentMissionFilter);
    }

    // Criterio de Ordenamiento
    if (currentSortMode === 'urgency') {
        filtered.sort((a, b) => {
            if (!a.due_date) return 1;
            if (!b.due_date) return -1;
            return new Date(a.due_date) - new Date(b.due_date);
        });
    } else if (currentSortMode === 'importance') {
        const priority = { 'main': 1, 'daily': 2, 'secondary': 3, 'special': 4, 'rescue': 5 };
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

    const all = [...allUpcomingTasks, ...allCompletedTasks, ...allOverdueTasks, ...allNoDateTasks];
    const courses = [...new Set(all.map(t => t.course_name).filter(Boolean))];

    if (courses.length === 0) {
        listEl.innerHTML = `<p class="text-cantera-600 dark:text-slate-500 italic text-[11px] py-1">Sin materias activas</p>`;
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
            <span class="truncate pr-2">${course}</span>
            ${isSelected ? '<i class="fa-solid fa-check text-indigo-600 dark:text-indigo-400 text-[10px]"></i>' : ''}
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
    ['all', 'main', 'secondary', 'daily', 'special', 'rescue'].forEach(f => {
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

    if (cAll) cAll.textContent = base.length;
    if (cMain) cMain.textContent = base.filter(t => t.mission_type === 'main').length;
    if (cSec) cSec.textContent = base.filter(t => t.mission_type === 'secondary').length;
    if (cDaily) cDaily.textContent = base.filter(t => t.mission_type === 'daily').length;
    if (cSpecial) cSpecial.textContent = base.filter(t => t.mission_type === 'special').length;
    if (cRescue) cRescue.textContent = allOverdueTasks.length;
}

function toggleProgressMetric() {
    metricMode = metricMode === 'tasks' ? 'hours' : 'tasks';
    const label = document.getElementById('metric-btn-label');
    if (label) label.textContent = metricMode === 'tasks' ? 'Por Tareas' : 'Por Horas';
    updateProgressBars();
}

// -------------------------------------------------------------
// REGLA ESTRICTA DE RACHA (Solo al 100% de los pendientes de hoy)
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

    // Barra Tripartita Global del Semestre
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

    // Antorcha de Prometeo: Solo se enciende si había tareas hoy y se cumplieron todas al 100%
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
// CALENDARIO INTERACTIVO CON PUNTOS SEMÁNTICOS
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
            const dayNum = new Date(t.due_date).getDate();
            if (!dayStatus[dayNum]) dayStatus[dayNum] = { pending: false, done: false };
            const isDone = t.status === 'done' || t.classroom_status === 'ENTREGADA' || t.classroom_status === 'CALIFICADA';
            if (isDone) dayStatus[dayNum].done = true;
            else dayStatus[dayNum].pending = true;
        }
    });

    for (let day = 1; day <= totalDays; day++) {
        const info = dayStatus[day];
        const isToday = day === now.getDate();
        const isSelected = selectedCalendarDay === day;

        let dotsHtml = '';
        if (info) {
            dotsHtml = `<div class="flex items-center justify-center gap-0.5 mt-0.5">`;
            if (info.pending) dotsHtml += `<span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>`;
            if (info.done) dotsHtml += `<span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>`;
            dotsHtml += `</div>`;
        }

        let selectRing = isSelected ? 'ring-2 ring-indigo-500 font-extrabold bg-indigo-50 dark:bg-indigo-950/60' : '';
        let todayClass = isToday ? 'bg-indigo-600 text-white font-bold' : 'text-cantera-800 dark:text-slate-400 hover:bg-cantera-200 dark:hover:bg-slate-800/60';

        calEl.innerHTML += `
            <button onclick="filterByCalendarDay(${day})" class="h-8 flex flex-col items-center justify-center rounded-lg ${todayClass} ${selectRing} transition-all cursor-pointer">
                <span class="leading-none">${day}</span>
                ${dotsHtml}
            </button>
        `;
    }
}

// -------------------------------------------------------------
// RENDER DE TARJETAS (Borde de 5px Inquebrantable)
// -------------------------------------------------------------
function renderTasks(tasks, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    if (!tasks || tasks.length === 0) {
        container.innerHTML = `<p class="text-cantera-600 dark:text-slate-500 italic text-sm py-4 text-center">No hay misiones activas en esta vista</p>`;
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
        }

        const dateStr = formatRelativeDate(task.due_date);

        // Fila compacta de tarea entregada
        if (isDone) {
            card.className = "bg-cantera-50/80 dark:bg-night-950/60 border border-cantera-300 dark:border-slate-800 rounded-lg px-4 py-3 flex items-center justify-between text-cantera-600 dark:text-slate-400 shadow-sm opacity-85 hover:opacity-100 transition-opacity";
            card.style.borderLeft = `5px solid #10B981`;
            card.innerHTML = `
                <div class="flex items-center gap-3 min-w-0 pr-4">
                    <input type="checkbox" checked onchange="toggleStatus('${taskId}', false)" class="w-4 h-4 accent-emerald-500 rounded cursor-pointer" title="Marcar como pendiente">
                    <span class="text-xs px-2 py-0.5 rounded bg-cantera-200 dark:bg-slate-800 text-cantera-700 dark:text-slate-400 truncate">${task.course_name}</span>
                    <span class="text-sm line-through text-cantera-500 dark:text-slate-500 truncate">${task.title}</span>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                    ${classroomBadge}
                    <button onclick="openIgnisWorkspace('${taskId}')" class="text-xs text-cantera-700 dark:text-slate-400 hover:text-indigo-600 px-2.5 py-1 rounded bg-cantera-100 dark:bg-slate-800 border border-cantera-300 dark:border-slate-700 flex items-center gap-1.5">
                        <i class="fa-solid fa-fire text-amber-500"></i> Ignis
                    </button>
                </div>
            `;
            container.appendChild(card);
            return;
        }

        // Tarea activa amplia
        card.className = "bg-white dark:bg-night-800/90 border border-cantera-300 dark:border-slate-700/80 rounded-xl p-5 flex flex-col gap-4 shadow-sm hover:shadow-md transition-all";
        card.style.borderLeft = `5px solid ${borderHex}`;

        card.innerHTML = `
            <div class="flex-1 w-full flex flex-col">
                <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-semibold px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">${task.course_name}</span>
                        ${missionBadge}
                        ${classroomBadge}
                    </div>
                    <span class="text-xs font-semibold text-cantera-700 dark:text-slate-300"><i class="fa-regular fa-clock mr-1 text-slate-400"></i>${dateStr}</span>
                </div>

                <h3 class="text-xl font-bold text-cantera-900 dark:text-slate-100 mb-2">
                    <a href="${task.link}" target="_blank" class="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors flex items-center gap-1.5">
                        ${task.title}
                        <i class="fa-solid fa-arrow-up-right-from-square text-xs opacity-50"></i>
                    </a>
                </h3>

                <p class="text-sm text-cantera-700 dark:text-slate-300 whitespace-pre-line line-clamp-3 mb-4 leading-relaxed">${task.description || 'Sin descripción.'}</p>

                <details class="mb-4 group">
                    <summary class="cursor-pointer text-xs font-medium text-cantera-600 dark:text-slate-400 hover:text-cantera-900 dark:hover:text-slate-200 list-none flex items-center gap-1">
                        <i class="fa-solid fa-pen-to-square"></i>
                        <span>Notas personales</span>
                    </summary>
                    <div class="mt-2 flex flex-col gap-2">
                        <textarea id="notes-${taskId}" rows="2" class="w-full bg-cantera-50 dark:bg-slate-900 border border-cantera-300 dark:border-slate-700 rounded-lg p-2 text-sm text-cantera-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500 resize-none">${task.notes || ''}</textarea>
                        <button onclick="saveNotes('${taskId}')" class="self-end text-xs bg-cantera-100 dark:bg-slate-700 hover:bg-cantera-200 text-cantera-800 dark:text-slate-200 px-3 py-1.5 rounded border border-cantera-300 dark:border-slate-600 font-medium">
                            Guardar notas
                        </button>
                    </div>
                </details>

                <div class="flex items-center justify-between gap-3 pt-3 border-t border-cantera-200 dark:border-slate-700/60 mt-auto">
                    <button onclick="openIgnisWorkspace('${taskId}')" class="text-sm font-semibold bg-indigo-50 dark:bg-indigo-600/20 hover:bg-indigo-100 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30 px-4 py-2 rounded-lg flex items-center gap-2 transition-all">
                        <i class="fa-solid fa-fire text-amber-500"></i> Abrir en Ignis
                    </button>

                    <label class="flex items-center gap-2 cursor-pointer text-sm text-cantera-800 dark:text-slate-300 select-none font-medium">
                        <span>Pendiente</span>
                        <input type="checkbox" onchange="toggleStatus('${taskId}', true)" class="w-5 h-5 accent-emerald-500 rounded cursor-pointer">
                    </label>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function formatRelativeDate(dueStr) {
    if (!dueStr) return 'Sin fecha';
    const due = new Date(dueStr);
    const now = new Date();
    const diffMs = due - now;
    const diffHours = Math.round(diffMs / (1000 * 60 * 60));

    if (diffHours > 0 && diffHours <= 12) {
        return `Vence en ${diffHours}h`;
    }
    if (diffHours > 12 && diffHours <= 24) {
        return `Vence hoy a las ${due.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`;
    }
    return due.toLocaleString('es-ES', { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

async function toggleStatus(taskId, isChecked) {
    const newStatus = isChecked ? 'done' : 'pending';
    try {
        await fetch(`/api/tasks/${taskId}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        setTimeout(loadTasks, 200);
    } catch (error) {
        console.error("Error toggling status:", error);
    }
}

async function saveNotes(taskId) {
    const textarea = document.getElementById(`notes-${taskId}`);
    if (!textarea) return;
    const notesContent = textarea.value;
    const btn = textarea.nextElementSibling;
    if (btn) { btn.textContent = 'Guardando...'; btn.disabled = true; }

    try {
        await fetch(`/api/tasks/${taskId}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notesContent })
        });
        if (btn) {
            btn.textContent = '¡Guardado!';
            btn.classList.add('text-emerald-600');
            setTimeout(() => {
                btn.textContent = 'Guardar notas';
                btn.disabled = false;
                btn.classList.remove('text-emerald-600');
            }, 1500);
        }
    } catch (error) {
        if (btn) { btn.textContent = 'Error'; btn.disabled = false; }
    }
}

// -------------------------------------------------------------
// VISOR DE IGNIS Y DOCUMENTOS
// -------------------------------------------------------------
function openIgnisWorkspace(taskId) {
    const task = typeof taskId === 'object' ? taskId : tasksMap.get(String(taskId));
    if (!task) return;

    currentTaskContext = task;
    const tTitle = document.getElementById('modal-task-title');
    if (tTitle) tTitle.textContent = `${task.course_name}: ${task.title}`;

    autoSelectMentor(task.course_name);
    setupDocumentCarousel(task);

    const chatContainer = document.getElementById('chat-messages');

    if (sessionTaskHistories[task.id]) {
        chatHistory = sessionTaskHistories[task.id].history;
        chatContainer.innerHTML = sessionTaskHistories[task.id].html;
    } else {
        chatHistory = [];
        
        let welcomeMsg = `¡Hola! Soy <strong>Ignis</strong>. Estoy analizando las consignas de <strong>${task.title}</strong> con el visor oficial de la izquierda para guiarte sin regalarte la respuesta. ¿Por dónde empezamos?`;
        if (task.classroom_status === 'DEVUELTA') {
            welcomeMsg = `¡Hola! Tu profesor devolvió <strong>${task.title}</strong> para ajustes. Vamos a revisar los puntos clave para que la vuelvas a entregar impecable.`;
        }

        chatContainer.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-200 dark:border-indigo-500/30">
                    <i class="fa-solid fa-fire text-amber-500 text-xs"></i>
                </div>
                <div class="bg-cantera-50 dark:bg-slate-900 p-3 rounded-2xl rounded-tl-none border border-cantera-300 dark:border-slate-700 text-xs text-cantera-900 dark:text-slate-200 leading-relaxed shadow-sm">
                    ${welcomeMsg}
                </div>
            </div>
        `;
        sessionTaskHistories[task.id] = {
            history: chatHistory,
            html: chatContainer.innerHTML
        };
    }

    const modal = document.getElementById('ignis-workspace-modal');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.remove('hidden');
    }
    setTimeout(() => {
        const inp = document.getElementById('chat-input');
        if (inp) inp.focus();
    }, 80);
