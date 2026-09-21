/**
 * API client — all communication with the FastAPI backend.
 * No hardcoded data. Every response comes from real API calls.
 */

const API_BASE = 'http://localhost:8000/api';

function getAuthHeaders() {
    const token = localStorage.getItem('token');
    if (!token) return {};
    return { 'Authorization': `Bearer ${token}` };
}

async function apiRequest(method, path, body = null) {
    const headers = {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
    };

    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${API_BASE}${path}`, opts);

    if (res.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        navigate('login');
        throw new Error('Authentication required');
    }

    const data = await res.json();

    if (!res.ok) {
        throw new Error(data.detail || 'API error');
    }

    return data;
}

// ---- Auth ----
async function apiRegister(username, email, password) {
    return apiRequest('POST', '/auth/register', { username, email, password });
}

async function apiLogin(username, password) {
    return apiRequest('POST', '/auth/login', { username, password });
}

async function apiGetMe() {
    return apiRequest('GET', '/auth/me');
}

// ---- Content ----
async function apiGetContent(page = 1, categoryId = null, sortBy = 'created_at') {
    let url = `/content?page=${page}&page_size=12&sort_by=${sortBy}`;
    if (categoryId) url += `&category_id=${categoryId}`;
    return apiRequest('GET', url);
}

async function apiGetContentById(id) {
    return apiRequest('GET', `/content/${id}`);
}

async function apiGetCategories() {
    return apiRequest('GET', '/content/categories');
}

async function apiSearch(query, page = 1) {
    return apiRequest('GET', `/search?q=${encodeURIComponent(query)}&page=${page}`);
}

// ---- Events ----
async function apiTrackEvent(eventType, entityType = null, entityId = null, metadata = {}) {
    const sessionId = parseInt(localStorage.getItem('session_id')) || null;
    return apiRequest('POST', '/events', {
        session_id: sessionId,
        event_type: eventType,
        entity_type: entityType,
        entity_id: entityId,
        metadata: { ...metadata, source: 'web', device: detectDevice() },
    });
}

// ---- Sessions ----
async function apiStartSession() {
    return apiRequest('POST', '/sessions/start');
}

async function apiEndSession(sessionId) {
    return apiRequest('POST', `/sessions/${sessionId}/end`);
}

// ---- Recommendations ----
async function apiGetAdRecommendations(topN = 3) {
    return apiRequest('GET', `/recommendations/ads?top_n=${topN}`);
}

async function apiGetContentRecommendations(topN = 10) {
    return apiRequest('GET', `/recommendations/content?top_n=${topN}`);
}

// ---- Ad Interactions ----
async function apiRecordImpression(adId, score = null) {
    const sessionId = parseInt(localStorage.getItem('session_id')) || null;
    return apiRequest('POST', `/ads/${adId}/impression`, {
        session_id: sessionId,
        recommendation_score: score,
        source: 'recommendation',
    });
}

async function apiRecordClick(adId, impressionId = null) {
    return apiRequest('POST', `/ads/${adId}/click`, {
        impression_id: impressionId,
    });
}

// ---- User Profile & Analytics ----
async function apiGetProfile() {
    return apiRequest('GET', '/users/me/profile');
}

async function apiGetUserAnalytics() {
    return apiRequest('GET', '/users/me/analytics');
}

// ---- Admin ----
async function apiGetPlatformOverview() {
    return apiRequest('GET', '/admin/analytics/overview');
}

async function apiGetCampaignAnalytics() {
    return apiRequest('GET', '/admin/analytics/campaigns');
}

async function apiGetCategoryAnalytics() {
    return apiRequest('GET', '/admin/analytics/categories');
}

// ---- Helpers ----
function detectDevice() {
    const w = window.innerWidth;
    if (w < 768) return 'mobile';
    if (w < 1024) return 'tablet';
    return 'desktop';
}
