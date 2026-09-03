let currentTaskContext = null;
let chatHistory = [];

document.addEventListener('DOMContentLoaded', () => {
    loadTasks();
});

async function loadTasks() {
    const loading = document.getElementById('loading');
    const container = document.getElementById('tasks-container');
    const authWarning = document.getElementById('auth-warning');

    loading.classList.remove('hidden');
    container.classList.add('hidden');
    authWarning.classList.add('hidden');

    try {
        const response = await fetch('/api/tasks');

        if (response.status === 401) {
            authWarning.classList.remove('hidden');
            loading.classList.add('hidden');
            return;
        }

        if (!response.ok) throw new Error('Error fetching tasks');

        const data = await response.json();
        renderTasks(data.tasks_with_dates, 'timeline');
        renderTasks(data.tasks_without_dates, 'no-date-tasks');

        document.getElementById('no-date-count').textContent = data.tasks_without_dates.length;

        container.classList.remove('hidden');
    } catch (error) {
        console.error("Error loading tasks:", error);
        alert("Hubo un error cargando las tareas.");
    } finally {
        loading.classList.add('hidden');
    }
}

function renderTasks(tasks, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (tasks.length === 0) {
        container.innerHTML = `<p class="text-slate-500 italic text-sm py-2">No hay tareas aquí.</p>`;
        return;
    }

    tasks.forEach(task => {
        const isDone = task.status === 'done';
        const card = document.createElement('div');
        card.className = `bg-slate-800 border ${isDone ? 'border-green-900/50 opacity-70' : 'border-slate-700'} rounded-lg p-4 md:p-5 flex flex-col md:flex-row gap-4 transition-all duration-300 relative overflow-hidden group`;

        if(isDone) {
            card.innerHTML += `<div class="absolute inset-0 bg-green-900/10 pointer-events-none"></div>`;
        }

        const dateStr = task.due_date ? new Date(task.due_date).toLocaleString('es-ES', {
            weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute:'2-digit'
        }) : 'Sin fecha';

        let materialsHtml = '';
        if (task.materials && task.materials.length > 0) {
            materialsHtml = `<div class="flex flex-wrap gap-2 mb-4">`;
            task.materials.forEach(mat => {
                const icon = mat.type === 'driveFile' ? 'fa-file-pdf' : 'fa-link';
                materialsHtml += `
                    <a href="${mat.url}" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-700/50 hover:bg-slate-700 border border-slate-600 text-xs text-slate-300 hover:text-indigo-300 transition-colors max-w-full">
                        <i class="fa-solid ${icon}"></i>
                        <span class="truncate">${mat.title}</span>
                    </a>
                `;
            });
            materialsHtml += `</div>`;
        }

        card.innerHTML += `
            <div class="flex-1 z-10 w-full flex flex-col">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-900/50 text-indigo-300 border border-indigo-800">${task.course_name}</span>
                    <span class="text-xs text-slate-400"><i class="fa-regular fa-clock mr-1"></i>${dateStr}</span>
                </div>
                <h3 class="text-lg font-bold ${isDone ? 'text-slate-400 line-through' : 'text-slate-100'} mb-2">
                    <a href="${task.link}" target="_blank" class="hover:text-indigo-400 transition-colors">${task.title} <i class="fa-solid fa-arrow-up-right-from-square text-xs ml-1 opacity-50"></i></a>
                </h3>
                <p class="text-sm text-slate-400 line-clamp-2 mb-3">${task.description || 'Sin descripción.'}</p>
                ${materialsHtml}

                <details class="mb-4">
                    <summary class="cursor-pointer text-sm text-slate-400 hover:text-slate-200 transition-colors">
                        <i class="fa-solid fa-pen-to-square mr-1"></i> Notas personales
                    </summary>
                    <div class="mt-2 flex flex-col gap-2">
                        <textarea id="notes-${task.id}" rows="2" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors resize-none">${task.notes || ''}</textarea>
                        <button onclick="saveNotes('${task.id}')" class="self-end text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-1.5 rounded transition-colors border border-slate-600">
                            Guardar notas
                        </button>
                    </div>
                </details>

                <div class="flex items-center gap-3 mt-auto">
                    <button onclick='openCopilot(${JSON.stringify(task).replace(/'/g, "&#39;")})' class="text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-1.5 rounded flex items-center gap-2 transition-colors border border-slate-600">
                        <i class="fa-solid fa-robot text-indigo-400"></i> Copilot
                    </button>

                    <label class="flex items-center gap-2 cursor-pointer ml-auto text-sm text-slate-300">
                        <span class="${isDone ? 'text-green-400 font-semibold' : ''}">${isDone ? 'Completada' : 'Pendiente'}</span>
                        <input type="checkbox" ${isDone ? 'checked' : ''} onchange="toggleStatus('${task.id}', this.checked)" class="w-5 h-5 accent-green-500 bg-slate-700 border-slate-600 rounded focus:ring-green-500 focus:ring-offset-slate-800">
                    </label>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

async function toggleStatus(taskId, isChecked) {
    const newStatus = isChecked ? 'done' : 'pending';
    try {
        await fetch(`/api/tasks/${taskId}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        // Optimistic UI update - just reload tasks to sync UI
        setTimeout(loadTasks, 300);
    } catch (error) {
        console.error("Error toggling status:", error);
    }
}

async function saveNotes(taskId) {
    const textarea = document.getElementById(`notes-${taskId}`);
    const notesContent = textarea.value;
    const btn = textarea.nextElementSibling;

    const originalText = btn.textContent;
    btn.textContent = 'Guardando...';
    btn.disabled = true;

    try {
        await fetch(`/api/tasks/${taskId}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notesContent })
        });
        btn.textContent = '¡Guardado!';
        btn.classList.add('text-green-400');
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
            btn.classList.remove('text-green-400');
        }, 2000);
    } catch (error) {
        console.error("Error saving notes:", error);
        btn.textContent = 'Error';
        btn.disabled = false;
    }
}

// Copilot logic
function openCopilot(task) {
    currentTaskContext = task;
    chatHistory = [];

    document.getElementById('modal-task-title').textContent = `${task.course_name}: ${task.title}`;

    // Reset chat
    const chatContainer = document.getElementById('chat-messages');
    chatContainer.innerHTML = `
        <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0">
                <i class="fa-solid fa-robot text-xs"></i>
            </div>
            <div class="bg-slate-800 p-3 rounded-2xl rounded-tl-none border border-slate-700 text-sm">
                ¡Hola! Estoy listo para ayudarte con la tarea <strong>${task.title}</strong>. ¿Qué necesitas saber?
            </div>
        </div>
    `;

    document.getElementById('copilot-modal').classList.remove('hidden');
    setTimeout(() => document.getElementById('chat-input').focus(), 100);
}

function closeCopilot() {
    document.getElementById('copilot-modal').classList.add('hidden');
    currentTaskContext = null;
}

function appendMessage(role, content) {
    const chatContainer = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = "flex items-start gap-3 " + (role === 'user' ? "flex-row-reverse" : "");

    const icon = role === 'user' ?
        `<div class="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center shrink-0 border border-slate-600"><i class="fa-solid fa-user text-xs"></i></div>` :
        `<div class="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0"><i class="fa-solid fa-robot text-xs"></i></div>`;

    const bubbleClass = role === 'user' ?
        "bg-indigo-900/50 p-3 rounded-2xl rounded-tr-none border border-indigo-800 text-sm text-indigo-100 whitespace-pre-wrap" :
        "bg-slate-800 p-3 rounded-2xl rounded-tl-none border border-slate-700 text-sm whitespace-pre-wrap text-slate-300";

    // Format basic markdown if present
    let formattedContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code class="bg-slate-900 text-indigo-300 px-1 py-0.5 rounded text-xs">$1</code>');

    msgDiv.innerHTML = `
        ${icon}
        <div class="${bubbleClass}">
            ${formattedContent}
        </div>
    `;

    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showTypingIndicator() {
    const chatContainer = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.id = "typing-indicator";
    msgDiv.className = "flex items-start gap-3";
    msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0">
            <i class="fa-solid fa-robot text-xs"></i>
        </div>
        <div class="bg-slate-800 p-3 rounded-2xl rounded-tl-none border border-slate-700 text-sm flex gap-1 items-center">
            <div class="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
            <div class="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
            <div class="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
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

    // Add user message to UI and history
    appendMessage('user', text);
    chatHistory.push({ role: 'user', content: text });

    const provider = document.querySelector('input[name="ai_provider"]:checked').value;

    showTypingIndicator();

    try {
        const response = await fetch('/api/copilot/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                provider: provider,
                task_context: {
                    course_name: currentTaskContext.course_name,
                    title: currentTaskContext.title,
                    description: currentTaskContext.description,
                        due_date: currentTaskContext.due_date,
                        materials_text: currentTaskContext.materials_text
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
        console.error("Chat error:", error);
        appendMessage('assistant', 'Hubo un error de conexión con el proveedor seleccionado. Revisa tu clave API o intenta con otro.');
    } finally {
        input.disabled = false;
        btn.disabled = false;
        input.focus();
    }
}
