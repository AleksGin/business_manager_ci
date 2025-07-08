class BusinessManagerApp {
    constructor() {
        this.API_BASE = window.location.origin;
        this.currentUser = null;
        this.accessToken = localStorage.getItem('access_token');
        this.initializeApp();
    }

    // API Methods
    async apiCall(endpoint, options = {}) {
        const url = `${this.API_BASE}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...(this.accessToken && { 'Authorization': `Bearer ${this.accessToken}` })
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                this.logout();
                throw new Error('Не авторизован');
            }

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка запроса');
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    async login(email, password) {
        const data = await this.apiCall('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        this.accessToken = data.access_token;
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        this.currentUser = data.user;
        
        return data;
    }

    async register(userData) {
        const data = await this.apiCall('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
        
        this.accessToken = data.access_token;
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        this.currentUser = data.user;
        
        return data;
    }

    logout() {
        this.accessToken = null;
        this.currentUser = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        this.showAuthSection();
    }

    async makeFirstAdmin() {
        return this.apiCall('/api/users/make-first-admin', {
            method: 'POST'
        });
    }

    // Data fetching methods
    async getUsers() {
        return this.apiCall('/api/users/');
    }

    async getTeams() {
        return this.apiCall('/api/teams/');
    }

    async getTasks() {
        return this.apiCall('/api/tasks/');
    }

    async getMeetings() {
        return this.apiCall('/api/meetings/');
    }

    // UI Methods
    initializeApp() {
        this.bindEvents();
        
        // Check if already logged in
        if (this.accessToken) {
            this.showDashboard();
            this.loadDashboardData();
        } else {
            this.showAuthSection();
        }
    }

    bindEvents() {
        // Auth events
        document.getElementById('toggle-auth').addEventListener('click', this.toggleAuthMode.bind(this));
        document.getElementById('login-btn').addEventListener('click', this.handleLogin.bind(this));
        document.getElementById('register-btn').addEventListener('click', this.handleRegister.bind(this));
        document.getElementById('logout-btn').addEventListener('click', this.logout.bind(this));
        document.getElementById('make-admin-btn').addEventListener('click', this.handleMakeAdmin.bind(this));

        // Tab events
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.target.dataset.tab;
                this.switchTab(tab);
            });
        });

        // Enter key handling for forms
        document.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const activeForm = document.querySelector('#login-form:not(.hidden), #register-form:not(.hidden)');
                if (activeForm) {
                    if (activeForm.id === 'login-form') {
                        this.handleLogin();
                    } else {
                        this.handleRegister();
                    }
                }
            }
        });
    }

    showAuthSection() {
        document.getElementById('auth-section').classList.remove('hidden');
        document.getElementById('dashboard-section').classList.add('hidden');
    }

    showDashboard() {
        document.getElementById('auth-section').classList.add('hidden');
        document.getElementById('dashboard-section').classList.remove('hidden');
        
        if (this.currentUser) {
            this.updateUserInfo();
        }
    }

    updateUserInfo() {
        const userInfo = document.getElementById('user-info');
        const makeAdminBtn = document.getElementById('make-admin-btn');
        
        userInfo.innerHTML = `
            ${this.currentUser.name} ${this.currentUser.surname}
            ${this.currentUser.role ? `<span class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">${this.currentUser.role}</span>` : ''}
        `;

        // Show "Make Admin" button if not admin
        if (this.currentUser.role !== 'Administrator') {
            makeAdminBtn.classList.remove('hidden');
        } else {
            makeAdminBtn.classList.add('hidden');
        }
    }

    toggleAuthMode() {
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');
        const toggleBtn = document.getElementById('toggle-auth');

        if (loginForm.classList.contains('hidden')) {
            // Show login
            loginForm.classList.remove('hidden');
            registerForm.classList.add('hidden');
            toggleBtn.textContent = 'Нет аккаунта? Регистрация';
        } else {
            // Show register
            loginForm.classList.add('hidden');
            registerForm.classList.remove('hidden');
            toggleBtn.textContent = 'Есть аккаунт? Войти';
        }
        
        this.hideError();
    }

    async handleLogin() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        if (!email || !password) {
            this.showError('Email и пароль обязательны');
            return;
        }

        try {
            this.showLoading(true);
            await this.login(email, password);
            this.showDashboard();
            this.loadDashboardData();
            this.hideError();
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async handleRegister() {
        const email = document.getElementById('reg-email').value;
        const name = document.getElementById('reg-name').value;
        const surname = document.getElementById('reg-surname').value;
        const gender = document.getElementById('reg-gender').value;
        const birthDate = document.getElementById('reg-birth-date').value;
        const password = document.getElementById('reg-password').value;

        if (!email || !name || !surname || !gender || !birthDate || !password) {
            this.showError('Все поля обязательны');
            return;
        }

        if (password.length < 10) {
            this.showError('Пароль должен содержать минимум 10 символов');
            return;
        }

        try {
            this.showLoading(true);
            await this.register({
                email,
                name,
                surname,
                gender,
                birth_date: birthDate,
                password
            });
            this.showDashboard();
            this.loadDashboardData();
            this.hideError();
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async handleMakeAdmin() {
        try {
            this.showLoading(true);
            const result = await this.makeFirstAdmin();
            this.currentUser.role = 'Administrator';
            this.updateUserInfo();
            this.showSuccess('Вы стали администратором!');
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    }

    showLoading(show) {
        const loading = document.getElementById('loading');
        if (show) {
            loading.classList.remove('hidden');
        } else {
            loading.classList.add('hidden');
        }
    }

    showError(message) {
        const errorDiv = document.getElementById('error-message');
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
        errorDiv.classList.add('error-message');
    }

    hideError() {
        const errorDiv = document.getElementById('error-message');
        errorDiv.classList.add('hidden');
    }

    showSuccess(message) {
        const errorDiv = document.getElementById('error-message');
        errorDiv.textContent = message;
        errorDiv.className = 'mt-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded success-message';
        errorDiv.classList.remove('hidden');
        
        // Hide after 3 seconds
        setTimeout(() => {
            this.hideError();
        }, 3000);
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.add('hidden');
        });

        // Show selected tab
        document.getElementById(`tab-${tabName}`).classList.remove('hidden');

        // Load data for the tab
        this.loadTabData(tabName);
    }

    async loadTabData(tabName) {
        try {
            this.showLoading(true);
            
            switch (tabName) {
                case 'users':
                    await this.loadUsers();
                    break;
                case 'teams':
                    await this.loadTeams();
                    break;
                case 'tasks':
                    await this.loadTasks();
                    break;
                case 'meetings':
                    await this.loadMeetings();
                    break;
                case 'dashboard':
                    await this.loadDashboardData();
                    break;
            }
        } catch (error) {
            this.showError(`Ошибка загрузки данных: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    async loadDashboardData() {
        try {
            const [users, teams, tasks] = await Promise.all([
                this.getUsers(),
                this.getTeams(),
                this.getTasks()
            ]);

            const completedTasks = tasks.filter(task => task.status === 'Done').length;

            document.getElementById('stats-users').textContent = users.length;
            document.getElementById('stats-teams').textContent = teams.length;
            document.getElementById('stats-tasks').textContent = tasks.length;
            document.getElementById('stats-completed').textContent = completedTasks;

        } catch (error) {
            console.error('Error loading dashboard:', error);
        }
    }

    async loadUsers() {
        try {
            const users = await this.getUsers();
            const tbody = document.getElementById('users-table');
            
            tbody.innerHTML = users.map(user => `
                <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">${user.name} ${user.surname}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-900">${user.email}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="status-badge role-${user.role ? user.role.toLowerCase() : 'employee'}">
                            ${user.role || 'Employee'}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="status-badge ${user.is_active ? 'status-active' : 'status-inactive'}">
                            ${user.is_active ? 'Активен' : 'Неактивен'}
                        </span>
                    </td>
                </tr>
            `).join('');

        } catch (error) {
            console.error('Error loading users:', error);
        }
    }

    async loadTeams() {
        try {
            const teams = await this.getTeams();
            const container = document.getElementById('teams-content');
            
            if (teams.length === 0) {
                container.innerHTML = '<p class="text-gray-500">Команды не найдены</p>';
                return;
            }

            container.innerHTML = teams.map(team => `
                <div class="border rounded-lg p-4 mb-4 hover-card">
                    <h4 class="text-lg font-medium text-gray-900 mb-2">${team.name}</h4>
                    <p class="text-gray-600 mb-2">${team.description}</p>
                    <div class="text-sm text-gray-500">
                        Владелец: ${team.owner_uuid}
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Error loading teams:', error);
        }
    }

    async loadTasks() {
        try {
            const tasks = await this.getTasks();
            const tbody = document.getElementById('tasks-table');
            
            tbody.innerHTML = tasks.map(task => `
                <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">${task.title}</div>
                        ${task.description ? `<div class="text-sm text-gray-500">${task.description}</div>` : ''}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="status-badge status-${task.status.toLowerCase().replace(' ', '-')}">
                            ${task.status}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${new Date(task.deadline).toLocaleDateString('ru-RU')}
                    </td>
                </tr>
            `).join('');

        } catch (error) {
            console.error('Error loading tasks:', error);
        }
    }

    async loadMeetings() {
        try {
            const meetings = await this.getMeetings();
            const tbody = document.getElementById('meetings-table');
            
            tbody.innerHTML = meetings.map(meeting => `
                <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">${meeting.title}</div>
                        ${meeting.description ? `<div class="text-sm text-gray-500">${meeting.description}</div>` : ''}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${new Date(meeting.date_time).toLocaleDateString('ru-RU')} 
                        ${new Date(meeting.date_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${meeting.team_uuid}
                    </td>
                </tr>
            `).join('');

        } catch (error) {
            console.error('Error loading meetings:', error);
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new BusinessManagerApp();
});