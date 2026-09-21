/**
 * Main application: routing, navigation, and utility functions.
 */

// ---- Router ----
function navigate(page, param = null) {
    switch (page) {
        case 'home':
            renderHomePage();
            break;
        case 'login':
            renderAuthPage('login');
            break;
        case 'register':
            renderAuthPage('register');
            break;
        case 'profile':
            renderProfilePage();
            break;
        case 'admin':
            renderAdminPage();
            break;
        case 'content':
            renderContentPage(param);
            break;
        case 'search':
            renderSearchResults(param);
            break;
        default:
            renderHomePage();
    }
    window.scrollTo({ top: 0 });
}

function viewContent(id) {
    navigate('content', id);
}


// ---- Search ----
function handleSearch() {
    const input = document.getElementById('search-input');
    const query = input ? input.value.trim() : '';
    if (query) {
        // Track search event
        if (isLoggedIn()) {
            apiTrackEvent('SEARCH', null, null, { query }).catch(() => {});
        }
        navigate('search', query);
    }
}

async function renderSearchResults(query) {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading"><span class="spinner"></span> Searching...</div>';

    try {
        const data = await apiSearch(query);
        main.innerHTML = `
            <div>
                <button onclick="navigate('home')" class="btn-ghost" style="margin-bottom:1rem;">← Back to feed</button>
                <div class="section-header">
                    <div>
                        <h2 class="section-title">Search results for "${escapeHtml(query)}"</h2>
                        <p class="section-subtitle">${data.total} results found</p>
                    </div>
                </div>
                <div class="content-grid">
                    ${data.items.length > 0
                        ? data.items.map(item => renderContentCard(item)).join('')
                        : '<div class="empty-state">No results found. Try a different search term.</div>'
                    }
                </div>
            </div>
        `;
    } catch (err) {
        main.innerHTML = `<div class="empty-state">Search failed: ${err.message}</div>`;
    }
}


// ---- Navbar Updates ----
function updateNavbar() {
    const navUser = document.getElementById('nav-user');
    const navAuth = document.getElementById('nav-auth');
    const navUsername = document.getElementById('nav-username');

    if (isLoggedIn()) {
        const user = getCurrentUser();
        navUser.style.display = 'flex';
        navAuth.style.display = 'none';
        navUsername.textContent = user ? user.username : 'Profile';
    } else {
        navUser.style.display = 'none';
        navAuth.style.display = 'flex';
    }
}


// ---- Toast Notifications ----
function showToast(message, duration = 3000) {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}


// ---- Utility Functions ----
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function truncate(str, len = 150) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len) + '...' : str;
}


// ---- Keyboard shortcuts ----
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.id === 'search-input') {
        handleSearch();
    }
});


// ---- Initialize ----
document.addEventListener('DOMContentLoaded', () => {
    updateNavbar();

    if (isLoggedIn()) {
        navigate('home');
    } else {
        navigate('home'); // Show home page even for non-logged-in users
    }
});
