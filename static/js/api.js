/**
 * TaskFlow API Client
 */

const API_BASE = '/api/v1';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('taskflow_access_token') || null;
    this.refreshToken = localStorage.getItem('taskflow_refresh_token') || null;
    this.user = JSON.parse(localStorage.getItem('taskflow_user') || 'null');
    this.ws = null;
    this.wsPingInterval = null;
  }

  setAuth(accessToken, refreshToken, user) {
    this.token = accessToken;
    this.refreshToken = refreshToken;
    this.user = user;
    if (accessToken) localStorage.setItem('taskflow_access_token', accessToken);
    else localStorage.removeItem('taskflow_access_token');

    if (refreshToken) localStorage.setItem('taskflow_refresh_token', refreshToken);
    else localStorage.removeItem('taskflow_refresh_token');

    if (user) localStorage.setItem('taskflow_user', JSON.stringify(user));
    else localStorage.removeItem('taskflow_user');
  }

  clearAuth() {
    this.setAuth(null, null, null);
    if (this.ws) {
      try { this.ws.close(); } catch (e) {}
      this.ws = null;
    }
    if (this.wsPingInterval) {
      clearInterval(this.wsPingInterval);
      this.wsPingInterval = null;
    }
  }

  isAuthenticated() {
    return !!this.token;
  }

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const headers = { ...options.headers };

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    let response;
    try {
      response = await fetch(url, { ...options, headers });
    } catch (err) {
      throw new Error(`Сетевая ошибка: ${err.message}`);
    }

    // Auto token refresh on 401 TOKEN_EXPIRED
    if (response.status === 401 && this.refreshToken && !endpoint.includes('/auth/refresh') && !endpoint.includes('/auth/login')) {
      const refreshed = await this.tryRefreshToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${this.token}`;
        response = await fetch(url, { ...options, headers });
      }
    }

    if (response.status === 204) {
      return null;
    }

    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    const data = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const errMsg = (data && data.error && data.error.message) || 
                     (data && data.detail) || 
                     (typeof data === 'string' ? data : 'Произошла ошибка запроса');
      const errCode = (data && data.error && data.error.code) || 'API_ERROR';
      const error = new Error(errMsg);
      error.status = response.status;
      error.code = errCode;
      error.data = data;
      throw error;
    }

    return data;
  }

  async tryRefreshToken() {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      if (res.ok) {
        const data = await res.json();
        this.token = data.access_token;
        this.refreshToken = data.refresh_token;
        localStorage.setItem('taskflow_access_token', this.token);
        localStorage.setItem('taskflow_refresh_token', this.refreshToken);
        return true;
      }
    } catch (e) {
      console.warn('Failed to refresh token', e);
    }
    this.clearAuth();
    return false;
  }

  // ── Auth ───────────────────────────────────────────────────────────────────
  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setAuth(data.access_token, data.refresh_token, data.user);
    return data;
  }

  async register(email, username, password, displayName) {
    const data = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        username,
        password,
        display_name: displayName || username,
      }),
    });
    this.setAuth(data.access_token, data.refresh_token, data.user);
    return data;
  }

  async logout() {
    try {
      if (this.token) {
        await this.request('/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });
      }
    } catch (e) {
      console.warn('Logout error', e);
    } finally {
      this.clearAuth();
    }
  }

  async getMe() {
    return await this.request('/auth/me');
  }

  // ── Workspaces ─────────────────────────────────────────────────────────────
  async getWorkspaces() {
    return await this.request('/workspaces');
  }

  async createWorkspace(name, slug, description) {
    return await this.request('/workspaces', {
      method: 'POST',
      body: JSON.stringify({ name, slug, description }),
    });
  }

  async getWorkspace(id) {
    return await this.request(`/workspaces/${id}`);
  }

  async getWorkspaceMembers(wsId) {
    return await this.request(`/workspaces/${wsId}/members`);
  }

  async getWorkspaceActivity(wsId, limit = 50) {
    return await this.request(`/workspaces/${wsId}/activity?limit=${limit}`);
  }

  // ── Projects ───────────────────────────────────────────────────────────────
  async getProjects(wsId) {
    return await this.request(`/workspaces/${wsId}/projects`);
  }

  async createProject(wsId, data) {
    return await this.request(`/workspaces/${wsId}/projects`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getProjectMilestones(wsId, projectId) {
    return await this.request(`/workspaces/${wsId}/projects/${projectId}/milestones`);
  }

  async createMilestone(wsId, projectId, data) {
    return await this.request(`/workspaces/${wsId}/projects/${projectId}/milestones`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Tasks ──────────────────────────────────────────────────────────────────
  async getTasks(wsId, params = {}) {
    const query = new URLSearchParams();
    if (params.project_id) query.append('project_id', params.project_id);
    if (params.status) query.append('status', params.status);
    if (params.priority) query.append('priority', params.priority);
    if (params.assignee_id) query.append('assignee_id', params.assignee_id);
    query.append('limit', '100');
    return await this.request(`/workspaces/${wsId}/tasks?${query.toString()}`);
  }

  async getTask(wsId, taskId) {
    return await this.request(`/workspaces/${wsId}/tasks/${taskId}`);
  }

  async createTask(wsId, data) {
    return await this.request(`/workspaces/${wsId}/tasks`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTask(wsId, taskId, data) {
    return await this.request(`/workspaces/${wsId}/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteTask(wsId, taskId) {
    return await this.request(`/workspaces/${wsId}/tasks/${taskId}`, {
      method: 'DELETE',
    });
  }

  async getTaskActivity(wsId, taskId) {
    return await this.request(`/workspaces/${wsId}/tasks/${taskId}/activity`);
  }

  // ── Comments ───────────────────────────────────────────────────────────────
  async getComments(wsId, taskId) {
    return await this.request(`/workspaces/${wsId}/tasks/${taskId}/comments`);
  }

  async createComment(wsId, taskId, content) {
    return await this.request(`/workspaces/${wsId}/tasks/${taskId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  }

  async deleteComment(wsId, taskId, commentId) {
    return await this.request(`/workspaces/${wsId}/tasks/${taskId}/comments/${commentId}`, {
      method: 'DELETE',
    });
  }

  // ── Time Tracking ──────────────────────────────────────────────────────────
  async getActiveTimer() {
    try {
      return await this.request('/time-entries/active');
    } catch (e) {
      if (e.status === 404) return null;
      throw e;
    }
  }

  async startTimer(wsId, taskId, description = '') {
    return await this.request(`/workspaces/${wsId}/tasks/${taskId}/time-entries/start`, {
      method: 'POST',
      body: JSON.stringify({ description }),
    });
  }

  async stopTimer() {
    return await this.request('/time-entries/stop', {
      method: 'POST',
    });
  }

  async getTimeEntries(limit = 30) {
    return await this.request(`/time-entries?limit=${limit}`);
  }

  // ── Habits ─────────────────────────────────────────────────────────────────
  async getHabits() {
    return await this.request('/habits');
  }

  async createHabit(data) {
    return await this.request('/habits', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async checkinHabit(habitId, count = 1) {
    return await this.request(`/habits/${habitId}/checkins`, {
      method: 'POST',
      body: JSON.stringify({ count }),
    });
  }

  async deleteHabit(habitId) {
    return await this.request(`/habits/${habitId}`, {
      method: 'DELETE',
    });
  }

  // ── Notes ──────────────────────────────────────────────────────────────────
  async getNotes(workspaceId = null, isPersonal = null) {
    const query = new URLSearchParams();
    if (workspaceId) query.append('workspace_id', workspaceId);
    if (isPersonal !== null) query.append('is_personal', isPersonal);
    return await this.request(`/notes?${query.toString()}`);
  }

  async createNote(data) {
    return await this.request('/notes', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateNote(id, data) {
    return await this.request(`/notes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteNote(id) {
    return await this.request(`/notes/${id}`, {
      method: 'DELETE',
    });
  }

  // ── Search ─────────────────────────────────────────────────────────────────
  async search(queryText, type = 'all', wsId = null) {
    const params = new URLSearchParams({ q: queryText, type });
    if (wsId) params.append('workspace_id', wsId);
    return await this.request(`/search?${params.toString()}`);
  }

  // ── Notifications ──────────────────────────────────────────────────────────
  async getNotifications() {
    return await this.request('/notifications');
  }

  async markNotificationRead(id) {
    return await this.request(`/notifications/${id}/read`, {
      method: 'PATCH',
    });
  }

  async markAllNotificationsRead() {
    return await this.request('/notifications/read-all', {
      method: 'POST',
    });
  }

  // ── WebSocket ──────────────────────────────────────────────────────────────
  connectWebSocket(onMessage) {
    if (!this.token) return;
    if (this.ws) {
      try { this.ws.close(); } catch (e) {}
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}${API_BASE}/ws/notifications?token=${encodeURIComponent(this.token)}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected to notifications stream');
        // Heartbeat every 25 seconds
        if (this.wsPingInterval) clearInterval(this.wsPingInterval);
        this.wsPingInterval = setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ event: 'ping' }));
          }
        }, 25000);
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'pong') return;
          if (onMessage) onMessage(data);
        } catch (e) {
          console.error('[WebSocket] message parse error', e);
        }
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        if (this.wsPingInterval) clearInterval(this.wsPingInterval);
      };

      this.ws.onerror = (err) => {
        console.warn('[WebSocket] Error', err);
      };
    } catch (e) {
      console.warn('[WebSocket] Init error', e);
    }
  }
}

window.api = new ApiClient();
