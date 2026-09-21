/**
 * Admin dashboard: platform-wide analytics from real database aggregations.
 * Uses Chart.js for simple charts.
 */

async function renderAdminPage() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading"><span class="spinner"></span> Loading dashboard...</div>';

    try {
        const [overview, campaigns, categories] = await Promise.all([
            apiGetPlatformOverview(),
            apiGetCampaignAnalytics(),
            apiGetCategoryAnalytics(),
        ]);

        main.innerHTML = `
            <div>
                <div class="section-header">
                    <div>
                        <h2 class="section-title">Platform Dashboard</h2>
                        <p class="section-subtitle">Real-time metrics from PostgreSQL</p>
                    </div>
                </div>

                <!-- Overview Metrics -->
                <div class="dashboard-grid">
                    <div class="metric-card">
                        <div class="metric-value">${overview.total_users.toLocaleString()}</div>
                        <div class="metric-label">Total Users</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${overview.active_users.toLocaleString()}</div>
                        <div class="metric-label">Active (7d)</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${overview.total_sessions.toLocaleString()}</div>
                        <div class="metric-label">Sessions</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${overview.total_events.toLocaleString()}</div>
                        <div class="metric-label">Events</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${overview.total_impressions.toLocaleString()}</div>
                        <div class="metric-label">Impressions</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${overview.total_clicks.toLocaleString()}</div>
                        <div class="metric-label">Clicks</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${(overview.overall_ctr * 100).toFixed(2)}%</div>
                        <div class="metric-label">Overall CTR</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${overview.total_content.toLocaleString()}</div>
                        <div class="metric-label">Content Items</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${overview.total_ads.toLocaleString()}</div>
                        <div class="metric-label">Active Ads</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${overview.total_campaigns.toLocaleString()}</div>
                        <div class="metric-label">Campaigns</div>
                    </div>
                </div>

                <!-- Category Analytics -->
                <div class="card" style="margin-bottom:1.5rem;">
                    <div class="section-header" style="margin-bottom:0.5rem;">
                        <h3 class="section-title">Category Engagement</h3>
                    </div>
                    <div id="category-chart" style="margin-bottom:1rem;">
                        ${renderCategoryBars(categories)}
                    </div>
                </div>

                <!-- Campaign Performance -->
                <div class="card" style="margin-bottom:1.5rem;">
                    <div class="section-header" style="margin-bottom:0.5rem;">
                        <h3 class="section-title">Campaign Performance</h3>
                    </div>
                    <div style="overflow-x:auto;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Campaign</th>
                                    <th>Advertiser</th>
                                    <th>Impressions</th>
                                    <th>Clicks</th>
                                    <th>CTR</th>
                                    <th>Budget</th>
                                    <th>Spent</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${campaigns.map(c => `
                                    <tr>
                                        <td>${escapeHtml(c.campaign_name)}</td>
                                        <td>${escapeHtml(c.advertiser_name)}</td>
                                        <td>${c.impressions.toLocaleString()}</td>
                                        <td>${c.clicks.toLocaleString()}</td>
                                        <td>${(c.ctr * 100).toFixed(2)}%</td>
                                        <td>$${c.budget.toLocaleString()}</td>
                                        <td>$${c.spent.toLocaleString()}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    } catch (err) {
        main.innerHTML = `<div class="empty-state">Dashboard error: ${err.message}</div>`;
    }
}


function renderCategoryBars(categories) {
    if (!categories || categories.length === 0) return '<p style="color:var(--text-dim);">No data yet</p>';

    const maxViews = Math.max(...categories.map(c => c.content_views), 1);

    return `
        <div class="interest-list">
            ${categories.map(c => `
                <div class="interest-item">
                    <span class="interest-name" style="width:120px;">${escapeHtml(c.category_name)}</span>
                    <div class="interest-bar-bg">
                        <div class="interest-bar" style="width:${(c.content_views / maxViews * 100).toFixed(0)}%"></div>
                    </div>
                    <span class="interest-score" style="width:60px;">${c.content_views}</span>
                </div>
            `).join('')}
        </div>
    `;
}
