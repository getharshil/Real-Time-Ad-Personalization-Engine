/**
 * Auth page: login and register forms.
 */

function renderAuthPage(mode = 'login') {
    const isLogin = mode === 'login';
    const main = document.getElementById('main-content');

    main.innerHTML = `
        <div class="auth-container">
            <div class="auth-card">
                <h2 class="auth-title">${isLogin ? 'Welcome back' : 'Create account'}</h2>
                <p class="auth-subtitle">${isLogin ? 'Sign in to your personalized feed' : 'Start discovering personalized content'}</p>

                <form id="auth-form" onsubmit="handleAuthSubmit(event, '${mode}')">
                    ${!isLogin ? `
                    <div class="form-group">
                        <label for="auth-email">Email</label>
                        <input type="email" id="auth-email" required placeholder="you@example.com">
                    </div>
                    ` : ''}
                    <div class="form-group">
                        <label for="auth-username">Username</label>
                        <input type="text" id="auth-username" required placeholder="your username" minlength="3">
                    </div>
                    <div class="form-group">
                        <label for="auth-password">Password</label>
                        <input type="password" id="auth-password" required placeholder="••••••••" minlength="6">
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:100%; margin-top:0.5rem;">
                        ${isLogin ? 'Sign In' : 'Create Account'}
                    </button>
                    <div id="auth-error" class="form-error"></div>
                </form>

                <div class="auth-switch">
                    ${isLogin
                        ? `Don't have an account? <a onclick="navigate('register')">Sign up</a>`
                        : `Already have an account? <a onclick="navigate('login')">Sign in</a>`
                    }
                </div>
            </div>
        </div>
    `;
}


async function handleAuthSubmit(e, mode) {
    e.preventDefault();
    const errorEl = document.getElementById('auth-error');
    errorEl.textContent = '';

    const username = document.getElementById('auth-username').value.trim();
    const password = document.getElementById('auth-password').value;

    try {
        let result;
        if (mode === 'register') {
            const email = document.getElementById('auth-email').value.trim();
            result = await apiRegister(username, email, password);
        } else {
            result = await apiLogin(username, password);
        }

        // Store token
        localStorage.setItem('token', result.access_token);

        // Fetch user info
        const user = await apiGetMe();
        localStorage.setItem('user', JSON.stringify(user));

        // Start session
        try {
            const session = await apiStartSession();
            localStorage.setItem('session_id', session.session_id);
        } catch (e) {
            console.warn('Session start failed:', e);
        }

        // Track app open event
        try {
            await apiTrackEvent('APP_OPEN');
        } catch (e) {}

        updateNavbar();
        navigate('home');
        showToast(`Welcome, ${user.username}!`);

    } catch (err) {
        errorEl.textContent = err.message;
    }
}


function handleLogout() {
    // End session
    const sessionId = localStorage.getItem('session_id');
    if (sessionId) {
        apiEndSession(sessionId).catch(() => {});
        apiTrackEvent('SESSION_END').catch(() => {});
    }

    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('session_id');
    updateNavbar();
    navigate('login');
    showToast('Signed out');
}


function isLoggedIn() {
    return !!localStorage.getItem('token');
}

function getCurrentUser() {
    const u = localStorage.getItem('user');
    return u ? JSON.parse(u) : null;
}
