/**
 * User profile page: shows dynamic interests, engagement metrics,
 * and analytics — all fetched from real API endpoints.
 */

async function renderProfilePage() {
    const main = document.getElementById('main-content');

    if (!isLoggedIn()) {
        navigate('login');
        return;
    }

    main.innerHTML = '<div class="loading"><span class="spinner"></span> Loading profile...</div>';

    try {
        const [profile, analytics] = await Promise.all([
            apiGetProfile(),
            apiGetUserAnalytics(),
        ]);

        const user = getCurrentUser();
        const initials = user ? user.username.substring(0, 2).toUpperCase() : '??';

        main.innerHTML = `
            <div style="max-width:800px;">
                <!-- Profile Header -->
                <div class="profile-header">
                    <div class="profile-avatar">${initials}</div>
                    <div class="profile-info">
                        <h2>${escapeHtml(profile.username)}</h2>
                        <p>${profile.is_cold_start ? 'New user — keep exploring to personalize your feed' : 'Personalized experience active'}</p>
                    </div>
                </div>

                <!-- Stats -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">${analytics.total_sessions}</div>
                        <div class="stat-label">Sessions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${analytics.total_events}</div>
                        <div class="stat-label">Events</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${analytics.content_views}</div>
                        <div class="stat-label">Content Views</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${analytics.ad_impressions}</div>
                        <div class="stat-label">Ad Impressions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${analytics.ad_clicks}</div>
                        <div class="stat-label">Ad Clicks</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${(analytics.ctr * 100).toFixed(1)}%</div>
                        <div class="stat-label">CTR</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${(profile.engagement_score * 100).toFixed(0)}%</div>
                        <div class="stat-label">Engagement</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${analytics.avg_session_duration_seconds ? formatDuration(analytics.avg_session_duration_seconds) : 'N/A'}</div>
                        <div class="stat-label">Avg Session</div>
                    </div>
                </div>

                <!-- Interests -->
                <div class="card" style="margin-bottom:1.5rem;">
                    <div class="section-header" style="margin-bottom:0.75rem;">
                        <h3 class="section-title">Your Interests</h3>
                        <span class="section-subtitle">Derived from your interactions</span>
                    </div>
                    ${profile.interests.length > 0 ? `
                    <div class="interest-list">
                        ${profile.interests.map(i => `
                            <div class="interest-item">
                                <span class="interest-name">${escapeHtml(i.category)}</span>
                                <div class="interest-bar-bg">
                                    <div class="interest-bar" style="width:${(i.affinity_score * 100).toFixed(0)}%"></div>
                                </div>
                                <span class="interest-score">${(i.affinity_score * 100).toFixed(0)}%</span>
                            </div>
                        `).join('')}
                    </div>
                    ` : '<p style="color:var(--text-dim);font-size:0.85rem;">Browse and interact with content to build your interest profile</p>'}
                </div>

                <!-- Most Viewed Categories -->
                ${analytics.most_viewed_categories.length > 0 ? `
                <div class="card" style="margin-bottom:1.5rem;">
                    <div class="section-header" style="margin-bottom:0.75rem;">
                        <h3 class="section-title">Most Viewed Categories</h3>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Category</th>
                                <th>Views</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${analytics.most_viewed_categories.map(c => `
                                <tr>
                                    <td>${escapeHtml(c.category)}</td>
                                    <td>${c.views}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                ` : ''}

                <!-- Recent Interests -->
                ${analytics.recent_interests.length > 0 ? `
                <div class="card">
                    <div class="section-header" style="margin-bottom:0.5rem;">
                        <h3 class="section-title">Recent Interests</h3>
                    </div>
                    <div class="chips">
                        ${analytics.recent_interests.map(c => `<span class="chip active">${escapeHtml(c)}</span>`).join('')}
                    </div>
                </div>
                ` : ''}
            </div>
        `;
    } catch (err) {
        main.innerHTML = `<div class="empty-state">Failed to load profile: ${err.message}</div>`;
    }
}

function formatDuration(seconds) {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.round(seconds / 60);
    return `${mins}m`;
}
