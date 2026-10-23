/**
 * TaskFlow Frontend Application
 */

class TaskFlowApp {
  constructor() {
    this.user = null;
    this.workspaces = [];
    this.activeWorkspace = null;
    this.projects = [];
    this.tasks = [];
    this.habits = [];
    this.notes = [];
    this.activeTimer = null;
    this.timerInterval = null;
    this.timerSeconds = 0;
    this.currentView = 'tasks';
    this.viewMode = 'kanban'; // 'kanban' or 'list'
    this.activeTaskModal = null;
    this.filters = {
      project_id: '',
      priority: '',
      search: '',
    };
  }

  async init() {
    this.initEventListeners();

    if (api.isAuthenticated()) {
      try {
        this.user = await api.getMe();
        this.onAuthenticated();
      } catch (err) {
        console.warn('Session expired or invalid token', err);
        api.clearAuth();
        this.showAuthModal();
      }
    } else {
      this.showAuthModal();
    }
  }

  // ── Auth Handling ──────────────────────────────────────────────────────────
  showAuthModal() {
    document.getElementById('modal-auth').classList.remove('hidden');
    this.renderIcons();
  }

  hideAuthModal() {
    document.getElementById('modal-auth').classList.add('hidden');
  }

  async quickLogin(email, password) {
    try {
      this.showToast('Вход в аккаунт...', 'info');
      const res = await api.login(email, password);
      this.user = res.user;
      this.hideAuthModal();
      this.onAuthenticated();
      this.showToast(`Добро пожаловать, ${this.user.display_name || this.user.username}!`, 'success');
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  }

  async onAuthenticated() {
    this.updateUserUI();
    this.initWebSocket();
    await this.loadWorkspaces();
    this.startActiveTimerWatcher();
  }

  updateUserUI() {
    if (!this.user) return;
    const name = this.user.display_name || this.user.username;
    const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'U';

    const avatar = document.getElementById('user-avatar');
    if (avatar) avatar.textContent = initials;

    const userName = document.getElementById('user-name');
    if (userName) userName.textContent = name;

    const menuName = document.getElementById('user-menu-name');
    if (menuName) menuName.textContent = name;

    const menuEmail = document.getElementById('user-menu-email');
    if (menuEmail) menuEmail.textContent = this.user.email;
  }

  initWebSocket() {
    api.connectWebSocket((message) => {
      if (message.event === 'notification.new') {
        const notif = message.payload;
        this.showToast(notif.message || 'Новое уведомление', 'info');
        this.loadNotifications();
      }
    });
  }

  // ── Workspaces ─────────────────────────────────────────────────────────────
  async loadWorkspaces() {
    try {
      this.workspaces = await api.getWorkspaces();
      if (!this.workspaces || this.workspaces.length === 0) {
        // Auto-create default workspace if none
        const ws = await api.createWorkspace('Мой Воркспейс', 'my-workspace', 'Персональное рабочее пространство');
        this.workspaces = [ws];
      }

      // Pick previously selected or first
      const savedWsId = localStorage.getItem('taskflow_active_ws');
      this.activeWorkspace = this.workspaces.find(w => w.id === savedWsId) || this.workspaces[0];
      localStorage.setItem('taskflow_active_ws', this.activeWorkspace.id);

      this.renderWorkspacesDropdown();
      await this.loadActiveWorkspaceData();
    } catch (err) {
      this.showToast(`Ошибка загрузки воркспейсов: ${err.message}`, 'error');
    }
  }

  renderWorkspacesDropdown() {
    if (!this.activeWorkspace) return;
    const wsName = document.getElementById('current-ws-name');
    if (wsName) wsName.textContent = this.activeWorkspace.name;

    const list = document.getElementById('ws-list');
    if (!list) return;

    list.innerHTML = this.workspaces.map(w => `
      <button onclick="app.switchWorkspace('${w.id}')" class="w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between ${w.id === this.activeWorkspace.id ? 'bg-brand-600/20 text-brand-300 font-semibold' : 'text-slate-300 hover:bg-surface-800'}">
        <span class="truncate">${this.escapeHtml(w.name)}</span>
        ${w.id === this.activeWorkspace.id ? '<span class="w-1.5 h-1.5 rounded-full bg-brand-400"></span>' : ''}
      </button>
    `).join('');
  }

  async switchWorkspace(wsId) {
    const ws = this.workspaces.find(w => w.id === wsId);
    if (!ws) return;
    this.activeWorkspace = ws;
    localStorage.setItem('taskflow_active_ws', ws.id);
    document.getElementById('ws-menu').classList.add('hidden');
    this.renderWorkspacesDropdown();
    await this.loadActiveWorkspaceData();
    this.showToast(`Воркспейс переключен на: ${ws.name}`, 'info');
  }

  async loadActiveWorkspaceData() {
    if (!this.activeWorkspace) return;
    await Promise.all([
      this.loadProjects(),
      this.loadTasks(),
      this.loadNotifications(),
    ]);

    if (this.currentView === 'habits') await this.loadHabits();
    if (this.currentView === 'notes') await this.loadNotes();
    if (this.currentView === 'activity') await this.loadActivity();
    if (this.currentView === 'members') await this.loadMembers();
    if (this.currentView === 'timer') await this.loadTimerView();
  }

  // ── Projects ───────────────────────────────────────────────────────────────
  async loadProjects() {
    try {
      this.projects = await api.getProjects(this.activeWorkspace.id);
      this.renderProjectFilters();
      if (this.currentView === 'projects') {
        this.renderProjectsGrid();
      }
    } catch (err) {
      console.error('Error loading projects', err);
    }
  }

  renderProjectFilters() {
    const filterSelect = document.getElementById('filter-project');
    const taskProjectSelect = document.getElementById('task-project');
    const timerTaskSelect = document.getElementById('timer-select-task');

    const options = [
      '<option value="">Все проекты</option>',
      ...this.projects.map(p => `<option value="${p.id}">${this.escapeHtml(p.name)}</option>`)
    ].join('');

    if (filterSelect) filterSelect.innerHTML = options;

    if (taskProjectSelect) {
      taskProjectSelect.innerHTML = this.projects.map(p =>
        `<option value="${p.id}">${this.escapeHtml(p.name)}</option>`
      ).join('');
    }
  }

  renderProjectsGrid() {
    const grid = document.getElementById('projects-grid');
    if (!grid) return;

    if (this.projects.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-500 text-xs">
          В этом воркспейсе еще нет проектов. Нажмите «Новый проект», чтобы создать первый.
        </div>
      `;
      return;
    }

    grid.innerHTML = this.projects.map(p => {
      const projTasks = this.tasks.filter(t => t.project_id === p.id);
      const doneCount = projTasks.filter(t => t.status === 'done').length;
      const progress = projTasks.length > 0 ? Math.round((doneCount / projTasks.length) * 100) : 0;

      return `
        <div class="rounded-2xl bg-surface-900 border border-slate-800 p-5 space-y-4 card-hover">
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-3">
              <span class="w-3.5 h-3.5 rounded-md" style="background-color: ${p.color || '#6366f1'}"></span>
              <h3 class="font-bold text-sm text-white">${this.escapeHtml(p.name)}</h3>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${p.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-700 text-slate-400'}">${p.status}</span>
          </div>

          <p class="text-xs text-slate-400 line-clamp-2">${this.escapeHtml(p.description || 'Без описания')}</p>

          <div class="space-y-1.5">
            <div class="flex justify-between text-[11px] text-slate-400 font-medium">
              <span>Прогресс задач</span>
              <span>${doneCount}/${projTasks.length} (${progress}%)</span>
            </div>
            <div class="w-full bg-surface-800 rounded-full h-1.5 overflow-hidden">
              <div class="bg-brand-500 h-1.5 rounded-full transition-all duration-500" style="width: ${progress}%"></div>
            </div>
          </div>

          <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
            <button onclick="app.filterByProject('${p.id}')" class="text-brand-400 hover:underline flex items-center gap-1">
              <span>Открыть задачи</span>
              <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
            </button>
            <span class="text-[11px] text-slate-500">${new Date(p.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      `;
    }).join('');

    this.renderIcons();
  }

  filterByProject(projectId) {
    this.filters.project_id = projectId;
    const select = document.getElementById('filter-project');
    if (select) select.value = projectId;
    this.switchView('tasks');
  }

  // ── Tasks & Kanban ─────────────────────────────────────────────────────────
  async loadTasks() {
    try {
      const res = await api.getTasks(this.activeWorkspace.id, this.filters);
      this.tasks = res.items || [];
      this.renderTasks();
      this.updateTimerTaskDropdown();
    } catch (err) {
      console.error('Error loading tasks', err);
    }
  }

  renderTasks() {
    if (this.viewMode === 'kanban') {
      this.renderKanban();
    } else {
      this.renderTaskList();
    }
  }

  renderKanban() {
    const statuses = ['todo', 'in_progress', 'in_review', 'done'];
    const filteredTasks = this.getFilteredTasks();

    statuses.forEach(status => {
      const col = document.getElementById(`col-${status}`);
      const count = document.getElementById(`col-count-${status}`);
      if (!col) return;

      const items = filteredTasks.filter(t => t.status === status);
      if (count) count.textContent = items.length;

      if (items.length === 0) {
        col.innerHTML = `
          <div class="h-28 border border-dashed border-slate-800/80 rounded-xl flex items-center justify-center text-slate-600 text-xs">
            Нет задач
          </div>
        `;
        return;
      }

      col.innerHTML = items.map(task => this.renderTaskCard(task)).join('');
    });

    this.initDragAndDrop();
    this.renderIcons();
  }

  renderTaskCard(task) {
    const priorityStyles = {
      low: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      medium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      high: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
      critical: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    };

    const project = this.projects.find(p => p.id === task.project_id);
    const assigneeName = task.assignee ? (task.assignee.display_name || task.assignee.username) : null;
    const assigneeInitials = assigneeName ? assigneeName.substring(0, 2).toUpperCase() : '?';

    return `
      <div 
        id="task-${task.id}" 
        draggable="true" 
        data-id="${task.id}" 
        data-version="${task.version}" 
        onclick="app.openTaskDetails('${task.id}')"
        class="task-card p-3.5 rounded-xl bg-surface-850 hover:bg-surface-800 border border-slate-700/60 shadow-lg space-y-2.5 transition"
      >
        <div class="flex items-center justify-between gap-2">
          <span class="text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${priorityStyles[task.priority] || priorityStyles.medium}">
            ${task.priority}
          </span>
          ${project ? `
            <span class="text-[10px] font-medium text-slate-400 truncate max-w-[110px]" title="${this.escapeHtml(project.name)}">
              <span class="inline-block w-1.5 h-1.5 rounded-full mr-1" style="background-color: ${project.color || '#6366f1'}"></span>
              ${this.escapeHtml(project.name)}
            </span>
          ` : ''}
        </div>

        <h4 class="text-xs font-semibold text-white leading-snug line-clamp-2">${this.escapeHtml(task.title)}</h4>

        ${task.description ? `<p class="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">${this.escapeHtml(task.description)}</p>` : ''}

        ${task.labels && task.labels.length > 0 ? `
          <div class="flex flex-wrap gap-1">
            ${task.labels.map(l => `
              <span class="text-[9px] px-1.5 py-0.5 rounded text-white font-medium" style="background-color: ${l.color || '#3b82f6'}88">
                ${this.escapeHtml(l.name)}
              </span>
            `).join('')}
          </div>
        ` : ''}

        <div class="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
          <div class="flex items-center gap-1.5">
            ${task.due_date ? `
              <i data-lucide="calendar" class="w-3 h-3 text-slate-500"></i>
              <span class="${new Date(task.due_date) < new Date() && task.status !== 'done' ? 'text-rose-400 font-semibold' : ''}">${task.due_date}</span>
            ` : '<span class="text-slate-600">Бессрочно</span>'}
          </div>

          <div class="flex items-center gap-2">
            <button onclick="event.stopPropagation(); app.startTimerForTask('${task.id}')" title="Запустить таймер" class="p-1 rounded hover:bg-brand-500/20 text-brand-400 transition">
              <i data-lucide="play" class="w-3 h-3 fill-current"></i>
            </button>
            <div title="${assigneeName || 'Не назначен'}" class="w-5 h-5 rounded-full bg-slate-700 text-slate-200 flex items-center justify-center font-bold text-[9px]">
              ${assigneeInitials}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderTaskList() {
    const tbody = document.getElementById('task-list-tbody');
    if (!tbody) return;

    const filtered = this.getFilteredTasks();
    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-slate-500">Нет подходящих задач</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(t => {
      const project = this.projects.find(p => p.id === t.project_id);
      const assigneeName = t.assignee ? (t.assignee.display_name || t.assignee.username) : '—';
      return `
        <tr class="hover:bg-surface-800/40 transition cursor-pointer" onclick="app.openTaskDetails('${t.id}')">
          <td class="py-3 px-4 font-semibold text-white">${this.escapeHtml(t.title)}</td>
          <td class="py-3 px-4 text-slate-400">${project ? this.escapeHtml(project.name) : '—'}</td>
          <td class="py-3 px-4 uppercase text-[10px] font-bold">${t.priority}</td>
          <td class="py-3 px-4 text-slate-300">${t.status}</td>
          <td class="py-3 px-4 text-slate-400">${t.due_date || '—'}</td>
          <td class="py-3 px-4 text-slate-300">${this.escapeHtml(assigneeName)}</td>
          <td class="py-3 px-4 text-right">
            <button onclick="event.stopPropagation(); app.startTimerForTask('${t.id}')" class="p-1.5 rounded hover:bg-brand-600/20 text-brand-400 transition">
              <i data-lucide="play" class="w-3.5 h-3.5 fill-current"></i>
            </button>
          </td>
        </tr>
      `;
    }).join('');

    this.renderIcons();
  }

  getFilteredTasks() {
    return this.tasks.filter(t => {
      if (this.filters.project_id && t.project_id !== this.filters.project_id) return false;
      if (this.filters.priority && t.priority !== this.filters.priority) return false;
      if (this.filters.search) {
        const query = this.filters.search.toLowerCase();
        const inTitle = t.title.toLowerCase().includes(query);
        const inDesc = t.description ? t.description.toLowerCase().includes(query) : false;
        if (!inTitle && !inDesc) return false;
      }
      return true;
    });
  }

  // ── Drag & Drop Kanban ─────────────────────────────────────────────────────
  initDragAndDrop() {
    const cards = document.querySelectorAll('.task-card');
    const cols = document.querySelectorAll('.kanban-col');

    cards.forEach(card => {
      card.addEventListener('dragstart', (e) => {
        card.classList.add('dragging');
        e.dataTransfer.setData('text/plain', JSON.stringify({
          taskId: card.dataset.id,
          version: parseInt(card.dataset.version, 10),
        }));
      });

      card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
      });
    });

    cols.forEach(col => {
      col.addEventListener('dragover', (e) => {
        e.preventDefault();
        col.classList.add('drag-over');
      });

      col.addEventListener('dragleave', () => {
        col.classList.remove('drag-over');
      });

      col.addEventListener('drop', async (e) => {
        e.preventDefault();
        col.classList.remove('drag-over');

        const raw = e.dataTransfer.getData('text/plain');
        if (!raw) return;

        try {
          const { taskId, version } = JSON.parse(raw);
          const newStatus = col.dataset.status;

          const task = this.tasks.find(t => t.id === taskId);
          if (!task || task.status === newStatus) return;

          // Optimistic update
          const oldStatus = task.status;
          task.status = newStatus;
          this.renderKanban();

          // Call API with optimistic locking version
          try {
            const updated = await api.updateTask(this.activeWorkspace.id, taskId, {
              status: newStatus,
              version: version,
            });
            task.version = updated.version;
            this.showToast(`Статус обновлен на: ${newStatus}`, 'success');
          } catch (err) {
            // Rollback on conflict or failure
            task.status = oldStatus;
            this.renderKanban();
            this.showToast(`Не удалось обновить задачу: ${err.message}`, 'error');
            await this.loadTasks();
          }
        } catch (err) {
          console.error('Drop error', err);
        }
      });
    });
  }

  // ── Task Details Modal ─────────────────────────────────────────────────────
  async openTaskDetails(taskId) {
    const task = this.tasks.find(t => t.id === taskId);
    if (!task) return;

    this.activeTaskModal = task;
    const modal = document.getElementById('modal-task-details');
    modal.classList.remove('hidden');

    document.getElementById('detail-task-title').textContent = task.title;
    document.getElementById('detail-task-desc').textContent = task.description || 'Описание отсутствует';
    document.getElementById('detail-task-due').textContent = task.due_date || 'Не указан';
    document.getElementById('detail-task-priority').textContent = task.priority.toUpperCase();
    document.getElementById('detail-task-status-select').value = task.status;

    const project = this.projects.find(p => p.id === task.project_id);
    document.getElementById('detail-task-project').textContent = project ? project.name : 'Без проекта';

    const assignee = task.assignee ? (task.assignee.display_name || task.assignee.username) : 'Не назначен';
    document.getElementById('detail-task-assignee').textContent = assignee;

    // Load comments and task activity
    await Promise.all([
      this.loadTaskComments(task.id),
      this.loadTaskActivity(task.id),
    ]);

    this.renderIcons();
  }

  async loadTaskComments(taskId) {
    try {
      const comments = await api.getComments(this.activeWorkspace.id, taskId);
      const countEl = document.getElementById('detail-comments-count');
      if (countEl) countEl.textContent = comments.length;

      const listEl = document.getElementById('detail-comments-list');
      if (!listEl) return;

      if (comments.length === 0) {
        listEl.innerHTML = `<div class="text-slate-500 text-xs py-2">Комментариев пока нет. Будьте первым!</div>`;
        return;
      }

      listEl.innerHTML = comments.map(c => {
        const author = c.author ? (c.author.display_name || c.author.username) : 'Пользователь';
        return `
          <div class="p-3 rounded-xl bg-surface-800/60 border border-slate-700/50 space-y-1">
            <div class="flex items-center justify-between text-[11px]">
              <span class="font-bold text-slate-200">${this.escapeHtml(author)}</span>
              <span class="text-slate-500">${new Date(c.created_at).toLocaleString()}</span>
            </div>
            <p class="text-slate-300 leading-relaxed text-xs">${this.escapeHtml(c.content)}</p>
          </div>
        `;
      }).join('');
    } catch (err) {
      console.error('Error loading comments', err);
    }
  }

  async loadTaskActivity(taskId) {
    try {
      const logs = await api.getTaskActivity(this.activeWorkspace.id, taskId);
      const listEl = document.getElementById('detail-activity-list');
      if (!listEl) return;

      if (logs.length === 0) {
        listEl.innerHTML = `<div class="text-slate-500 text-[11px]">История пуста</div>`;
        return;
      }

      listEl.innerHTML = logs.map(l => `
        <div class="flex items-center justify-between py-1 border-b border-slate-800/40">
          <span>Действие: <strong class="text-slate-300">${l.action}</strong></span>
          <span class="text-slate-500">${new Date(l.created_at).toLocaleTimeString()}</span>
        </div>
      `).join('');
    } catch (err) {
      console.error('Error loading task activity', err);
    }
  }

  // ── Time Tracking ──────────────────────────────────────────────────────────
  async startActiveTimerWatcher() {
    try {
      this.activeTimer = await api.getActiveTimer();
      this.updateTimerUI();
    } catch (err) {
      console.warn('Could not fetch active timer', err);
    }
  }

  updateTimerUI() {
    const widget = document.getElementById('active-timer-widget');
    const pageTask = document.getElementById('timer-page-task-name');
    const pageStopBtn = document.getElementById('timer-page-stop-btn');

    if (!this.activeTimer) {
      if (widget) widget.classList.add('hidden');
      if (pageTask) pageTask.textContent = 'Таймер не запущен';
      if (pageStopBtn) pageStopBtn.classList.add('hidden');
      if (this.timerInterval) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
      }
      return;
    }

    if (widget) widget.classList.remove('hidden');
    if (pageStopBtn) pageStopBtn.classList.remove('hidden');

    const task = this.tasks.find(t => t.id === this.activeTimer.task_id);
    const taskTitle = task ? task.title : 'Задача';

    const titleEl = document.getElementById('timer-task-title');
    if (titleEl) titleEl.textContent = taskTitle;
    if (pageTask) pageTask.textContent = taskTitle;

    const startTime = new Date(this.activeTimer.started_at).getTime();

    if (this.timerInterval) clearInterval(this.timerInterval);
    this.timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const formatted = this.formatSeconds(elapsed);

      const counter = document.getElementById('timer-counter');
      const pageClock = document.getElementById('timer-page-clock');
      if (counter) counter.textContent = formatted;
      if (pageClock) pageClock.textContent = formatted;
    }, 1000);
  }

  async startTimerForTask(taskId, description = '') {
    try {
      this.activeTimer = await api.startTimer(this.activeWorkspace.id, taskId, description);
      this.updateTimerUI();
      this.showToast('Таймер запущен!', 'success');
      if (this.currentView === 'timer') await this.loadTimerView();
    } catch (err) {
      this.showToast(`Ошибка запуска таймера: ${err.message}`, 'error');
    }
  }

  async stopCurrentTimer() {
    try {
      await api.stopTimer();
      this.activeTimer = null;
      this.updateTimerUI();
      this.showToast('Таймер остановлен. Запись сохранена.', 'success');
      if (this.currentView === 'timer') await this.loadTimerView();
    } catch (err) {
      this.showToast(`Ошибка остановки таймера: ${err.message}`, 'error');
    }
  }

  async loadTimerView() {
    this.updateTimerTaskDropdown();
    try {
      const entries = await api.getTimeEntries(50);
      const tbody = document.getElementById('time-entries-tbody');
      if (!tbody) return;

      if (entries.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="py-8 text-center text-slate-500">Записей времени пока нет</td></tr>`;
        return;
      }

      tbody.innerHTML = entries.map(e => {
        const task = this.tasks.find(t => t.id === e.task_id);
        const taskTitle = task ? task.title : 'Задача';
        const user = e.user ? (e.user.display_name || e.user.username) : 'Пользователь';
        const dur = e.duration_seconds ? this.formatSecondsShort(e.duration_seconds) : 'В процессе...';

        return `
          <tr class="hover:bg-surface-800/40 transition">
            <td class="py-3 px-4 font-medium text-slate-300">${this.escapeHtml(user)}</td>
            <td class="py-3 px-4 text-white font-semibold">${this.escapeHtml(taskTitle)}</td>
            <td class="py-3 px-4 text-slate-400">${new Date(e.started_at).toLocaleString()}</td>
            <td class="py-3 px-4 text-slate-400">${e.ended_at ? new Date(e.ended_at).toLocaleString() : '—'}</td>
            <td class="py-3 px-4 font-mono font-bold text-brand-400">${dur}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error('Error loading time entries', err);
    }
  }

  updateTimerTaskDropdown() {
    const select = document.getElementById('timer-select-task');
    if (!select) return;
    select.innerHTML = [
      '<option value="">Выберите задачу для запуска таймера...</option>',
      ...this.tasks.map(t => `<option value="${t.id}">${this.escapeHtml(t.title)}</option>`)
    ].join('');
  }

  // ── Habits ─────────────────────────────────────────────────────────────────
  async loadHabits() {
    try {
      this.habits = await api.getHabits();
      this.renderHabits();
    } catch (err) {
      console.error('Error loading habits', err);
    }
  }

  renderHabits() {
    const grid = document.getElementById('habits-grid');
    if (!grid) return;

    if (this.habits.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-500 text-xs">
          Привычки пока не созданы. Нажмите «Новая привычка», чтобы начать формировать рутину!
        </div>
      `;
      return;
    }

    grid.innerHTML = this.habits.map(h => `
      <div class="rounded-2xl bg-surface-900 border border-slate-800 p-5 space-y-4 card-hover">
        <div class="flex items-start justify-between">
          <div class="space-y-1">
            <h3 class="font-bold text-sm text-white">${this.escapeHtml(h.title)}</h3>
            <span class="text-[10px] uppercase font-semibold text-brand-400">${h.frequency === 'daily' ? 'Ежедневно' : 'Еженедельно'}</span>
          </div>
          <button onclick="app.deleteHabit('${h.id}')" class="p-1 rounded text-slate-500 hover:text-rose-400 transition" title="Удалить">
            <i data-lucide="trash" class="w-3.5 h-3.5"></i>
          </button>
        </div>

        ${h.description ? `<p class="text-xs text-slate-400 line-clamp-2">${this.escapeHtml(h.description)}</p>` : ''}

        <div class="flex items-center justify-between p-3 rounded-xl bg-surface-800/60 border border-slate-800">
          <div class="flex items-center gap-2">
            <span class="text-xl">🔥</span>
            <div>
              <div class="text-xs font-bold text-white">${h.current_streak} дней</div>
              <div class="text-[10px] text-slate-500">Текущая серия</div>
            </div>
          </div>
          <div class="text-right">
            <div class="text-xs font-bold text-slate-300">Рекорд: ${h.longest_streak}</div>
            <div class="text-[10px] text-slate-500">Цель: ${h.target_count}/день</div>
          </div>
        </div>

        <button onclick="app.checkinHabit('${h.id}')" class="w-full py-2.5 rounded-xl bg-brand-600/20 hover:bg-brand-600/30 text-brand-300 border border-brand-500/30 font-semibold text-xs flex items-center justify-center gap-2 transition">
          <i data-lucide="check" class="w-4 h-4"></i>
          <span>Отметить сегодня (+1)</span>
        </button>
      </div>
    `).join('');

    this.renderIcons();
  }

  async checkinHabit(habitId) {
    try {
      await api.checkinHabit(habitId, 1);
      this.showToast('Отлично! Чек-ин записан, серия продолжена! 🔥', 'success');
      await this.loadHabits();
    } catch (err) {
      this.showToast(`Ошибка чек-ина: ${err.message}`, 'error');
    }
  }

  async deleteHabit(habitId) {
    if (!confirm('Удалить эту привычку?')) return;
    try {
      await api.deleteHabit(habitId);
      this.showToast('Привычка удалена', 'info');
      await this.loadHabits();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  }

  // ── Notes ──────────────────────────────────────────────────────────────────
  async loadNotes() {
    try {
      const filterType = document.getElementById('notes-filter-type')?.value || 'all';
      let isPersonal = null;
      if (filterType === 'personal') isPersonal = true;
      if (filterType === 'workspace') isPersonal = false;

      this.notes = await api.getNotes(this.activeWorkspace.id, isPersonal);
      this.renderNotes();
    } catch (err) {
      console.error('Error loading notes', err);
    }
  }

  renderNotes() {
    const grid = document.getElementById('notes-grid');
    if (!grid) return;

    if (this.notes.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-500 text-xs">
          Заметок пока нет. Создайте первую заметку для фиксации идей!
        </div>
      `;
      return;
    }

    grid.innerHTML = this.notes.map(n => `
      <div class="rounded-2xl bg-surface-900 border border-slate-800 p-5 space-y-3 card-hover flex flex-col justify-between">
        <div class="space-y-2">
          <div class="flex items-start justify-between gap-2">
            <h3 class="font-bold text-sm text-white line-clamp-1">${this.escapeHtml(n.title)}</h3>
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${n.is_personal ? 'bg-amber-500/10 text-amber-400' : 'bg-brand-500/10 text-brand-400'}">
              ${n.is_personal ? 'Личная' : 'Командная'}
            </span>
          </div>
          <p class="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap line-clamp-4 font-mono bg-surface-850 p-2.5 rounded-lg border border-slate-800/80">${this.escapeHtml(n.content || '')}</p>
        </div>

        <div class="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
          <span>${new Date(n.created_at).toLocaleDateString()}</span>
          <button onclick="app.deleteNote('${n.id}')" class="text-slate-500 hover:text-rose-400 p-1">
            <i data-lucide="trash" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      </div>
    `).join('');

    this.renderIcons();
  }

  async deleteNote(noteId) {
    if (!confirm('Удалить эту заметку?')) return;
    try {
      await api.deleteNote(noteId);
      this.showToast('Заметка удалена', 'info');
      await this.loadNotes();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  }

  // ── Activity Log ───────────────────────────────────────────────────────────
  async loadActivity() {
    try {
      const logs = await api.getWorkspaceActivity(this.activeWorkspace.id);
      const list = document.getElementById('activity-list');
      if (!list) return;

      if (logs.length === 0) {
        list.innerHTML = `<div class="py-12 text-center text-slate-500 text-xs">Журнал активности пуст</div>`;
        return;
      }

      list.innerHTML = logs.map(l => `
        <div class="p-3.5 rounded-xl bg-surface-900 border border-slate-800 flex items-center justify-between text-xs">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-surface-800 flex items-center justify-center text-brand-400">
              <i data-lucide="activity" class="w-4 h-4"></i>
            </div>
            <div>
              <div class="font-semibold text-slate-200">
                Действие <span class="text-brand-400 font-mono">${l.action}</span> над сущностью <span class="text-white">${l.entity_type}</span>
              </div>
              <div class="text-[11px] text-slate-500">ID: ${l.entity_id}</div>
            </div>
          </div>
          <span class="text-slate-500 text-[11px] font-mono">${new Date(l.created_at).toLocaleString()}</span>
        </div>
      `).join('');

      this.renderIcons();
    } catch (err) {
      console.error('Error loading activity', err);
    }
  }

  // ── Members ────────────────────────────────────────────────────────────────
  async loadMembers() {
    try {
      const members = await api.getWorkspaceMembers(this.activeWorkspace.id);
      const tbody = document.getElementById('members-tbody');
      if (!tbody) return;

      tbody.innerHTML = members.map(m => {
        const user = m.user || {};
        const name = user.display_name || user.username || 'Пользователь';
        return `
          <tr class="hover:bg-surface-800/40 transition">
            <td class="py-3 px-4 font-semibold text-white flex items-center gap-2">
              <div class="w-6 h-6 rounded-full bg-brand-600 text-[10px] text-white flex items-center justify-center font-bold">
                ${name.substring(0, 1).toUpperCase()}
              </div>
              <span>${this.escapeHtml(name)}</span>
            </td>
            <td class="py-3 px-4 text-slate-400">${this.escapeHtml(user.email || '—')}</td>
            <td class="py-3 px-4">
              <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold ${m.role === 'owner' ? 'bg-amber-500/10 text-amber-400' : 'bg-brand-500/10 text-brand-400'}">
                ${m.role}
              </span>
            </td>
            <td class="py-3 px-4 text-emerald-400">${m.status}</td>
            <td class="py-3 px-4 text-slate-500">${new Date(m.joined_at || m.created_at).toLocaleDateString()}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error('Error loading members', err);
    }
  }

  // ── Notifications ──────────────────────────────────────────────────────────
  async loadNotifications() {
    try {
      const notifs = await api.getNotifications();
      const unread = notifs.filter(n => !n.is_read);

      const badge = document.getElementById('notif-badge');
      if (badge) {
        if (unread.length > 0) badge.classList.remove('hidden');
        else badge.classList.add('hidden');
      }

      const list = document.getElementById('notif-list');
      if (!list) return;

      if (notifs.length === 0) {
        list.innerHTML = `<div class="text-center py-6 text-slate-500 text-xs">Нет уведомлений</div>`;
        return;
      }

      list.innerHTML = notifs.map(n => `
        <div class="p-2.5 rounded-lg ${n.is_read ? 'bg-surface-800/30 text-slate-400' : 'bg-surface-800 text-slate-200 border-l-2 border-brand-500'} flex items-start justify-between gap-2">
          <div>
            <div class="font-medium text-xs leading-snug">${this.escapeHtml(n.payload?.message || n.type)}</div>
            <div class="text-[10px] text-slate-500 mt-1">${new Date(n.created_at).toLocaleString()}</div>
          </div>
          ${!n.is_read ? `
            <button onclick="app.markNotificationRead('${n.id}')" class="text-brand-400 hover:text-white text-[10px] shrink-0">
              OK
            </button>
          ` : ''}
        </div>
      `).join('');
    } catch (err) {
      console.error('Error loading notifications', err);
    }
  }

  async markNotificationRead(id) {
    try {
      await api.markNotificationRead(id);
      await this.loadNotifications();
    } catch (err) {
      console.error(err);
    }
  }

  // ── Global Search ──────────────────────────────────────────────────────────
  async handleGlobalSearch(query) {
    const container = document.getElementById('search-results-container');
    if (!container) return;

    if (!query || query.trim().length === 0) {
      container.innerHTML = `<div class="text-center py-8 text-slate-500">Введите ключевое слово для поиска</div>`;
      return;
    }

    try {
      const res = await api.search(query, 'all', this.activeWorkspace.id);
      const tasks = res.tasks || [];
      const notes = res.notes || [];

      if (tasks.length === 0 && notes.length === 0) {
        container.innerHTML = `<div class="text-center py-8 text-slate-500">Ничего не найдено по запросу «${this.escapeHtml(query)}»</div>`;
        return;
      }

      let html = '';
      if (tasks.length > 0) {
        html += `<div class="px-2 py-1 text-[11px] font-bold text-slate-400 uppercase">Задачи (${tasks.length})</div>`;
        html += tasks.map(t => `
          <div onclick="app.closeSearchAndOpenTask('${t.id}')" class="p-2.5 rounded-lg hover:bg-surface-800 cursor-pointer flex items-center justify-between text-xs">
            <span class="font-medium text-white">${this.escapeHtml(t.title)}</span>
            <span class="text-[10px] text-slate-500 uppercase">${t.status}</span>
          </div>
        `).join('');
      }

      if (notes.length > 0) {
        html += `<div class="px-2 py-1 text-[11px] font-bold text-slate-400 uppercase mt-2">Заметки (${notes.length})</div>`;
        html += notes.map(n => `
          <div onclick="app.closeSearchAndOpenNotes()" class="p-2.5 rounded-lg hover:bg-surface-800 cursor-pointer flex items-center justify-between text-xs">
            <span class="font-medium text-white">${this.escapeHtml(n.title)}</span>
            <span class="text-[10px] text-slate-500">${n.is_personal ? 'Личная' : 'Командная'}</span>
          </div>
        `).join('');
      }

      container.innerHTML = html;
    } catch (err) {
      container.innerHTML = `<div class="text-rose-400 text-xs py-4">Ошибка поиска: ${err.message}</div>`;
    }
  }

  closeSearchAndOpenTask(taskId) {
    document.getElementById('modal-search').classList.add('hidden');
    this.openTaskDetails(taskId);
  }

  closeSearchAndOpenNotes() {
    document.getElementById('modal-search').classList.add('hidden');
    this.switchView('notes');
  }

  // ── View Switching & Nav ───────────────────────────────────────────────────
  switchView(viewName) {
    this.currentView = viewName;

    // Toggle panels
    document.querySelectorAll('.view-panel').forEach(p => p.classList.add('hidden'));
    const active = document.getElementById(`view-${viewName}`);
    if (active) active.classList.remove('hidden');

    // Update nav buttons
    document.querySelectorAll('.nav-item').forEach(btn => {
      if (btn.dataset.view === viewName) {
        btn.classList.add('bg-brand-600/20', 'text-brand-400', 'border', 'border-brand-500/30', 'text-white');
        btn.classList.remove('text-slate-400');
      } else {
        btn.classList.remove('bg-brand-600/20', 'text-brand-400', 'border', 'border-brand-500/30', 'text-white');
        btn.classList.add('text-slate-400');
      }
    });

    // Refresh view specific data
    if (viewName === 'tasks') this.renderTasks();
    if (viewName === 'projects') this.renderProjectsGrid();
    if (viewName === 'timer') this.loadTimerView();
    if (viewName === 'habits') this.loadHabits();
    if (viewName === 'notes') this.loadNotes();
    if (viewName === 'activity') this.loadActivity();
    if (viewName === 'members') this.loadMembers();
  }

  // ── Event Listeners ────────────────────────────────────────────────────────
  initEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.addEventListener('click', () => this.switchView(btn.dataset.view));
    });

    // Kanban / List toggle
    document.getElementById('view-kanban-btn')?.addEventListener('click', () => {
      this.viewMode = 'kanban';
      document.getElementById('kanban-container')?.classList.remove('hidden');
      document.getElementById('task-list-container')?.classList.add('hidden');
      document.getElementById('view-kanban-btn')?.classList.add('bg-brand-600', 'text-white');
      document.getElementById('view-list-btn')?.classList.remove('bg-brand-600', 'text-white');
      this.renderTasks();
    });

    document.getElementById('view-list-btn')?.addEventListener('click', () => {
      this.viewMode = 'list';
      document.getElementById('kanban-container')?.classList.add('hidden');
      document.getElementById('task-list-container')?.classList.remove('hidden');
      document.getElementById('view-list-btn')?.classList.add('bg-brand-600', 'text-white');
      document.getElementById('view-kanban-btn')?.classList.remove('bg-brand-600', 'text-white');
      this.renderTasks();
    });

    // Dropdowns toggle
    this.setupDropdown('ws-selector-btn', 'ws-menu');
    this.setupDropdown('notif-btn', 'notif-menu');
    this.setupDropdown('user-menu-btn', 'user-menu');

    // Close modals on cancel or backdrop click
    document.querySelectorAll('.close-modal-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        btn.closest('.modal-backdrop')?.classList.add('hidden');
      });
    });

    document.querySelectorAll('.modal-backdrop').forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal && modal.id !== 'modal-auth') {
          modal.classList.add('hidden');
        }
      });
    });

    // Filters
    document.getElementById('filter-project')?.addEventListener('change', (e) => {
      this.filters.project_id = e.target.value;
      this.renderTasks();
    });

    document.getElementById('filter-priority')?.addEventListener('change', (e) => {
      this.filters.priority = e.target.value;
      this.renderTasks();
    });

    document.getElementById('filter-search')?.addEventListener('input', (e) => {
      this.filters.search = e.target.value;
      this.renderTasks();
    });

    document.getElementById('reset-filters-btn')?.addEventListener('click', () => {
      this.filters = { project_id: '', priority: '', search: '' };
      document.getElementById('filter-project').value = '';
      document.getElementById('filter-priority').value = '';
      document.getElementById('filter-search').value = '';
      this.renderTasks();
    });

    // Global Search Modal Trigger & Ctrl+K
    const openSearch = () => {
      const modal = document.getElementById('modal-search');
      modal?.classList.remove('hidden');
      document.getElementById('global-search-input')?.focus();
    };

    document.getElementById('search-trigger-btn')?.addEventListener('click', openSearch);
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openSearch();
      }
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-backdrop').forEach(m => {
          if (m.id !== 'modal-auth') m.classList.add('hidden');
        });
      }
    });

    let searchTimeout = null;
    document.getElementById('global-search-input')?.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => this.handleGlobalSearch(e.target.value), 250);
    });

    // Stop timer buttons
    document.getElementById('stop-timer-btn')?.addEventListener('click', () => this.stopCurrentTimer());
    document.getElementById('timer-page-stop-btn')?.addEventListener('click', () => this.stopCurrentTimer());

    // Timer start button on timer page
    document.getElementById('timer-start-btn')?.addEventListener('click', () => {
      const taskId = document.getElementById('timer-select-task')?.value;
      const desc = document.getElementById('timer-desc-input')?.value || '';
      if (!taskId) {
        this.showToast('Выберите задачу для отсчета времени', 'error');
        return;
      }
      this.startTimerForTask(taskId, desc);
    });

    // Detail modal start timer
    document.getElementById('detail-start-timer-btn')?.addEventListener('click', () => {
      if (this.activeTaskModal) {
        this.startTimerForTask(this.activeTaskModal.id);
      }
    });

    // Detail modal status change
    document.getElementById('detail-task-status-select')?.addEventListener('change', async (e) => {
      if (!this.activeTaskModal) return;
      const newStatus = e.target.value;
      try {
        const updated = await api.updateTask(this.activeWorkspace.id, this.activeTaskModal.id, {
          status: newStatus,
          version: this.activeTaskModal.version,
        });
        this.activeTaskModal.status = updated.status;
        this.activeTaskModal.version = updated.version;
        await this.loadTasks();
        this.showToast('Статус обновлен', 'success');
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    });

    // Detail modal delete task
    document.getElementById('detail-delete-task-btn')?.addEventListener('click', async () => {
      if (!this.activeTaskModal || !confirm('Удалить эту задачу?')) return;
      try {
        await api.deleteTask(this.activeWorkspace.id, this.activeTaskModal.id);
        document.getElementById('modal-task-details').classList.add('hidden');
        this.showToast('Задача удалена', 'info');
        await this.loadTasks();
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    });

    // Detail modal add comment
    document.getElementById('form-add-comment')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!this.activeTaskModal) return;
      const input = document.getElementById('comment-input');
      const content = input.value.trim();
      if (!content) return;

      try {
        await api.createComment(this.activeWorkspace.id, this.activeTaskModal.id, content);
        input.value = '';
        await this.loadTaskComments(this.activeTaskModal.id);
        this.showToast('Комментарий добавлен', 'success');
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    });

    // Modals Open Triggers
    document.getElementById('open-create-task-btn')?.addEventListener('click', () => {
      document.getElementById('modal-create-task')?.classList.remove('hidden');
    });

    document.getElementById('open-create-project-btn')?.addEventListener('click', () => {
      document.getElementById('modal-create-project')?.classList.remove('hidden');
    });

    document.getElementById('open-create-ws-btn')?.addEventListener('click', () => {
      document.getElementById('ws-menu')?.classList.add('hidden');
      document.getElementById('modal-create-ws')?.classList.remove('hidden');
    });

    document.getElementById('open-create-habit-btn')?.addEventListener('click', () => {
      document.getElementById('modal-create-habit')?.classList.remove('hidden');
    });

    document.getElementById('open-create-note-btn')?.addEventListener('click', () => {
      document.getElementById('modal-create-note')?.classList.remove('hidden');
    });

    // Notes filter
    document.getElementById('notes-filter-type')?.addEventListener('change', () => {
      this.loadNotes();
    });

    // Notifications mark all read
    document.getElementById('mark-all-read-btn')?.addEventListener('click', async () => {
      try {
        await api.markAllNotificationsRead();
        await this.loadNotifications();
        this.showToast('Все уведомления прочитаны', 'info');
      } catch (err) {
        console.error(err);
      }
    });

    // Logout
    document.getElementById('logout-btn')?.addEventListener('click', async () => {
      await api.logout();
      window.location.reload();
    });

    // Form Submissions
    this.setupFormSubmissions();
  }

  setupDropdown(buttonId, menuId) {
    const btn = document.getElementById(buttonId);
    const menu = document.getElementById(menuId);
    if (!btn || !menu) return;

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      menu.classList.toggle('hidden');
    });

    document.addEventListener('click', (e) => {
      if (!btn.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add('hidden');
      }
    });
  }

  setupFormSubmissions() {
    // Form: Create Task
    document.getElementById('form-create-task')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('task-title').value.trim();
      const projectId = document.getElementById('task-project').value;
      const status = document.getElementById('task-status').value;
      const priority = document.getElementById('task-priority').value;
      const dueDate = document.getElementById('task-due-date').value || null;
      const description = document.getElementById('task-description').value.trim() || null;

      try {
        await api.createTask(this.activeWorkspace.id, {
          title,
          project_id: projectId,
          status,
          priority,
          due_date: dueDate,
          description,
        });

        document.getElementById('modal-create-task').classList.add('hidden');
        document.getElementById('form-create-task').reset();
        this.showToast('Задача успешно создана!', 'success');
        await this.loadTasks();
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    });

    // Form: Create Project
    document.getElementById('form-create-project')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('project-name').value.trim();
      const description = document.getElementById('project-desc').value.trim() || null;
      const color = document.getElementById('project-color').value;

      try {
        await api.createProject(this.activeWorkspace.id, { name, description, color });
        document.getElementById('modal-create-project').classList.add('hidden');
        document.getElementById('form-create-project').reset();
        this.showToast('Проект создан!', 'success');
        await this.loadProjects();
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    });

    // Form: Create Workspace
    document.getElementById('form-create-ws')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('ws-input-name').value.trim();
      const slug = document.getElementById('ws-input-slug').value.trim();
      const description = document.getElementById('ws-input-desc').value.trim();

      try {
        const ws = await api.createWorkspace(name, slug, description);
        document.getElementById('modal-create-ws').classList.add('hidden');
        document.getElementById('form-create-ws').reset();
        this.showToast('Воркспейс успешно создан!', 'success');
        await this.loadWorkspaces();
        await this.switchWorkspace(ws.id);
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    });

    // Form: Create Habit
    document.getElementById('form-create-habit')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('habit-title').value.trim();
      const frequency = document.getElementById('habit-frequency').value;
      const targetCount = parseInt(document.getElementById('habit-target').value, 10) || 1;
      const description = document.getElementById('habit-desc').value.trim() || null;

      try {
        await api.createHabit({ title, frequency, target_count: targetCount, description });
        document.getElementById('modal-create-habit').classList.add('hidden');
        document.getElementById('form-create-habit').reset();
        this.showToast('Привычка добавлена!', 'success');
        await this.loadHabits();
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    });

    // Form: Create Note
    document.getElementById('form-create-note')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('note-title').value.trim();
      const content = document.getElementById('note-content').value.trim();
      const isPersonal = document.getElementById('note-is-personal').checked;

      try {
        await api.createNote({
          title,
          content,
          is_personal: isPersonal,
          workspace_id: isPersonal ? null : this.activeWorkspace.id,
        });
        document.getElementById('modal-create-note').classList.add('hidden');
        document.getElementById('form-create-note').reset();
        this.showToast('Заметка сохранена!', 'success');
        await this.loadNotes();
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    });

    // Form: Auth Login
    document.getElementById('form-login')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('login-email').value.trim();
      const password = document.getElementById('login-password').value;
      await this.quickLogin(email, password);
    });

    // Form: Auth Register
    document.getElementById('form-register')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('reg-email').value.trim();
      const username = document.getElementById('reg-username').value.trim();
      const displayName = document.getElementById('reg-display-name').value.trim();
      const password = document.getElementById('reg-password').value;

      try {
        const res = await api.register(email, username, password, displayName);
        this.user = res.user;
        this.hideAuthModal();
        this.onAuthenticated();
        this.showToast('Регистрация прошла успешно!', 'success');
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    });

    // Auth tab toggles
    document.getElementById('auth-tab-login')?.addEventListener('click', () => {
      document.getElementById('auth-tab-login').className = 'flex-1 pb-2 font-semibold text-xs border-b-2 border-brand-500 text-brand-400';
      document.getElementById('auth-tab-register').className = 'flex-1 pb-2 font-semibold text-xs border-b-2 border-transparent text-slate-400 hover:text-slate-200';
      document.getElementById('form-login').classList.remove('hidden');
      document.getElementById('form-register').classList.add('hidden');
    });

    document.getElementById('auth-tab-register')?.addEventListener('click', () => {
      document.getElementById('auth-tab-register').className = 'flex-1 pb-2 font-semibold text-xs border-b-2 border-brand-500 text-brand-400';
      document.getElementById('auth-tab-login').className = 'flex-1 pb-2 font-semibold text-xs border-b-2 border-transparent text-slate-400 hover:text-slate-200';
      document.getElementById('form-register').classList.remove('hidden');
      document.getElementById('form-login').classList.add('hidden');
    });
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  formatSeconds(sec) {
    const h = String(Math.floor(sec / 3600)).padStart(2, '0');
    const m = String(Math.floor((sec % 3600) / 60)).padStart(2, '0');
    const s = String(sec % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
  }

  formatSecondsShort(sec) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    if (h > 0) return `${h}ч ${m}м`;
    if (m > 0) return `${m}м ${s}с`;
    return `${s}с`;
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const colors = {
      success: 'bg-emerald-950/90 text-emerald-200 border border-emerald-500/40',
      error: 'bg-rose-950/90 text-rose-200 border border-rose-500/40',
      info: 'bg-surface-850/90 text-slate-200 border border-slate-700/60',
    };

    const icons = {
      success: '<i data-lucide="check-circle" class="w-4 h-4 text-emerald-400 shrink-0"></i>',
      error: '<i data-lucide="alert-circle" class="w-4 h-4 text-rose-400 shrink-0"></i>',
      info: '<i data-lucide="info" class="w-4 h-4 text-brand-400 shrink-0"></i>',
    };

    toast.className = `toast ${colors[type] || colors.info}`;
    toast.innerHTML = `
      ${icons[type] || icons.info}
      <span class="flex-1">${this.escapeHtml(message)}</span>
    `;

    container.appendChild(toast);
    this.renderIcons();

    setTimeout(() => {
      toast.classList.add('toast-out');
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  renderIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }
}

// Global initialization
window.app = new TaskFlowApp();
document.addEventListener('DOMContentLoaded', () => {
  window.app.init();
});
