/**
 * Home / Discovery page.
 * Shows personalized content, recommended ads, trending content.
 * All data fetched from real API endpoints.
 */

let homeCategories = [];
let homeSelectedCategory = null;
let homePage = 1;

async function renderHomePage() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading"><span class="spinner"></span> Loading your feed...</div>';

    try {
        // Fetch categories
        homeCategories = await apiGetCategories();

        // Build page
        main.innerHTML = `
            <div id="home-page">
                <!-- Category Filters -->
                <div class="chips" id="category-chips"></div>

                <!-- Recommended Ads Section -->
                <div id="ads-section" style="margin-bottom:1.5rem;"></div>

                <!-- Personalized Content -->
                <div id="personalized-section" style="margin-bottom:2rem;"></div>

                <!-- All Content / Trending -->
                <div>
                    <div class="section-header">
                        <div>
                            <h2 class="section-title" id="content-section-title">Latest Content</h2>
                            <p class="section-subtitle">Browse all content</p>
                        </div>
                        <div style="display:flex;gap:0.4rem;">
                            <button onclick="loadContent('created_at')" class="chip active" id="sort-latest">Latest</button>
                            <button onclick="loadContent('popularity')" class="chip" id="sort-popular">Popular</button>
                        </div>
                    </div>
                    <div class="content-grid" id="content-grid"></div>
                    <div id="content-pagination"></div>
                </div>
            </div>
        `;

        renderCategoryChips();
        await Promise.all([
            loadAds(),
            loadPersonalizedContent(),
            loadContent('created_at'),
        ]);
    } catch (err) {
        main.innerHTML = `<div class="empty-state">Failed to load: ${err.message}</div>`;
    }
}


function renderCategoryChips() {
    const container = document.getElementById('category-chips');
    if (!container) return;

    let html = `<button class="chip ${!homeSelectedCategory ? 'active' : ''}" onclick="filterCategory(null)">All</button>`;
    for (const cat of homeCategories) {
        const active = homeSelectedCategory === cat.id ? 'active' : '';
        html += `<button class="chip ${active}" onclick="filterCategory(${cat.id})">${cat.name}</button>`;
    }
    container.innerHTML = html;
}


function filterCategory(catId) {
    homeSelectedCategory = catId;
    homePage = 1;
    renderCategoryChips();
    loadContent();

    // Track search/filter event
    if (isLoggedIn() && catId) {
        apiTrackEvent('SEARCH', null, null, { category_id: catId }).catch(() => {});
    }
}


async function loadContent(sortBy = 'created_at') {
    const grid = document.getElementById('content-grid');
    if (!grid) return;

    // Update sort button states
    const latestBtn = document.getElementById('sort-latest');
    const popularBtn = document.getElementById('sort-popular');
    if (latestBtn && popularBtn) {
        latestBtn.classList.toggle('active', sortBy === 'created_at');
        popularBtn.classList.toggle('active', sortBy === 'popularity');
    }

    grid.innerHTML = '<div class="loading"><span class="spinner"></span></div>';

    try {
        const data = await apiGetContent(homePage, homeSelectedCategory, sortBy);
        if (!data.items || data.items.length === 0) {
            grid.innerHTML = '<div class="empty-state">No content found</div>';
            return;
        }

        grid.innerHTML = data.items.map(item => renderContentCard(item)).join('');
        renderPagination(data.total, data.page, data.page_size);
    } catch (err) {
        grid.innerHTML = `<div class="empty-state">${err.message}</div>`;
    }
}


function renderContentCard(item) {
    return `
        <div class="card" onclick="viewContent(${item.id})" style="cursor:pointer;">
            <div class="card-meta">
                ${item.category_name ? `<span class="badge badge-category">${item.category_name}</span>` : ''}
            </div>
            <h3 class="card-title" style="margin-top:0.5rem;">${escapeHtml(item.title)}</h3>
            <p class="card-desc">${escapeHtml(truncate(item.description, 120))}</p>
            <div class="card-meta">
                <span>Popularity: ${(item.popularity_score * 100).toFixed(0)}%</span>
            </div>
        </div>
    `;
}


async function loadAds() {
    if (!isLoggedIn()) return;

    const section = document.getElementById('ads-section');
    if (!section) return;

    try {
        const data = await apiGetAdRecommendations(3);
        if (!data.recommendations || data.recommendations.length === 0) {
            section.innerHTML = '';
            return;
        }

        section.innerHTML = `
            <div class="section-header">
                <div>
                    <h2 class="section-title">Recommended for You</h2>
                    <p class="section-subtitle">Personalized ads · ${data.algorithm} algorithm${data.is_cold_start ? ' · Exploring your interests' : ''}</p>
                </div>
            </div>
            <div class="content-grid">
                ${data.recommendations.map(ad => renderAdCard(ad)).join('')}
            </div>
        `;

        // Record impressions for shown ads
        for (const ad of data.recommendations) {
            apiRecordImpression(ad.id, ad.score).catch(() => {});
        }
    } catch (err) {
        console.warn('Failed to load ads:', err);
    }
}


function renderAdCard(ad) {
    return `
        <div class="ad-card">
            <div class="ad-label">
                <span class="badge badge-sponsored">Sponsored</span>
                ${ad.category_name ? `<span class="badge badge-category">${ad.category_name}</span>` : ''}
            </div>
            <h3 class="card-title">${escapeHtml(ad.title)}</h3>
            <p class="card-desc">${escapeHtml(ad.description)}</p>
            <div class="card-meta">
                <span>Relevance: ${(ad.score * 100).toFixed(0)}%</span>
            </div>
            <div class="ad-actions">
                <button class="btn btn-sponsored btn-sm" onclick="handleAdClick(${ad.id}, event)">
                    ${escapeHtml(ad.cta_text || 'View Offer')}
                </button>
                <button class="btn-danger" onclick="handleAdSkip(${ad.id}, event)">
                    Not Interested
                </button>
            </div>
        </div>
    `;
}


async function handleAdClick(adId, e) {
    e.stopPropagation();
    try {
        await apiRecordClick(adId);
        showToast('Thanks for your interest! Your recommendations are updating.');
    } catch (err) {
        console.warn('Click tracking failed:', err);
    }
}


async function handleAdSkip(adId, e) {
    e.stopPropagation();
    try {
        await apiTrackEvent('AD_SKIP', 'advertisement', adId);
        showToast("Got it — we'll adjust your recommendations.");
        // Remove the ad card visually
        e.target.closest('.ad-card').style.opacity = '0.3';
    } catch (err) {
        console.warn('Skip tracking failed:', err);
    }
}


async function loadPersonalizedContent() {
    if (!isLoggedIn()) return;

    const section = document.getElementById('personalized-section');
    if (!section) return;

    try {
        const data = await apiGetContentRecommendations(6);
        if (!data.personalized || data.personalized.length === 0) {
            section.innerHTML = '';
            return;
        }

        section.innerHTML = `
            <div class="section-header">
                <div>
                    <h2 class="section-title">Based on Your Interests</h2>
                    <p class="section-subtitle">Content matched to your browsing patterns</p>
                </div>
            </div>
            <div class="content-grid">
                ${data.personalized.slice(0, 6).map(item => `
                    <div class="card" onclick="viewContent(${item.id})" style="cursor:pointer;">
                        <div class="card-meta">
                            ${item.category_name ? `<span class="badge badge-category">${item.category_name}</span>` : ''}
                        </div>
                        <h3 class="card-title" style="margin-top:0.5rem;">${escapeHtml(item.title)}</h3>
                        <p class="card-desc">${escapeHtml(truncate(item.description, 100))}</p>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        console.warn('Personalized content failed:', err);
    }
}


function renderPagination(total, page, pageSize) {
    const container = document.getElementById('content-pagination');
    if (!container) return;

    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '<div class="pagination">';
    html += `<button ${page <= 1 ? 'disabled' : ''} onclick="changePage(${page - 1})">← Prev</button>`;
    for (let i = 1; i <= Math.min(totalPages, 5); i++) {
        html += `<button class="${page === i ? 'active' : ''}" onclick="changePage(${i})">${i}</button>`;
    }
    html += `<button ${page >= totalPages ? 'disabled' : ''} onclick="changePage(${page + 1})">Next →</button>`;
    html += '</div>';
    container.innerHTML = html;
}

function changePage(page) {
    homePage = page;
    loadContent();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
