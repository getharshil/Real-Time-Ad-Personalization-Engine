/**
 * Content detail page with like/dislike interactions
 * and event tracking for every meaningful action.
 */

async function renderContentPage(contentId) {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading"><span class="spinner"></span> Loading...</div>';

    try {
        const item = await apiGetContentById(contentId);

        // Track content view event
        if (isLoggedIn()) {
            apiTrackEvent('CONTENT_VIEW', 'content', item.id).catch(() => {});
        }

        main.innerHTML = `
            <div class="content-detail">
                <button onclick="navigate('home')" class="btn-ghost" style="margin-bottom:1rem;">← Back to feed</button>

                <div class="card-meta" style="margin-bottom:0.75rem;">
                    ${item.category_name ? `<span class="badge badge-category">${item.category_name}</span>` : ''}
                    <span>Popularity: ${(item.popularity_score * 100).toFixed(0)}%</span>
                </div>

                <h1>${escapeHtml(item.title)}</h1>

                <div class="meta">
                    <span>Published: ${new Date(item.created_at).toLocaleDateString()}</span>
                </div>

                <div class="body">
                    <p>${escapeHtml(item.description)}</p>
                    <br>
                    <p>This is a content article in the ${item.category_name || 'General'} category.
                       In a production system, this would contain the full article text, images, and
                       multimedia content. The key point is that your interaction with this page
                       (viewing, liking, or disliking) is being tracked as a real event that updates
                       your user profile and influences future recommendations.</p>
                </div>

                ${isLoggedIn() ? `
                <div class="interaction-bar">
                    <button onclick="handleContentLike(${item.id})" class="btn btn-outline btn-sm" id="like-btn-${item.id}">
                         Like
                    </button>
                    <button onclick="handleContentDislike(${item.id})" class="btn btn-outline btn-sm" id="dislike-btn-${item.id}">
                         Not for me
                    </button>
                </div>
                ` : '<p style="color:var(--text-dim);font-size:0.85rem;margin-top:1rem;">Sign in to interact with content</p>'}

                <!-- Related Ad -->
                <div id="content-ad" style="margin-top:2rem;"></div>

                <!-- Related Content -->
                <div id="related-content" style="margin-top:2rem;"></div>
            </div>
        `;

        // Load related ad
        if (isLoggedIn()) {
            loadInlineAd();
        }
    } catch (err) {
        main.innerHTML = `<div class="empty-state">Content not found: ${err.message}</div>`;
    }
}


async function handleContentLike(contentId) {
    try {
        await apiTrackEvent('CONTENT_LIKE', 'content', contentId);
        const btn = document.getElementById(`like-btn-${contentId}`);
        if (btn) {
            btn.innerHTML = ' Liked!';
            btn.style.borderColor = 'var(--accent)';
            btn.style.color = 'var(--accent)';
        }
        showToast('Your interests have been updated!');
    } catch (err) {
        console.warn('Like event failed:', err);
    }
}


async function handleContentDislike(contentId) {
    try {
        await apiTrackEvent('CONTENT_DISLIKE', 'content', contentId);
        const btn = document.getElementById(`dislike-btn-${contentId}`);
        if (btn) {
            btn.innerHTML = ' Noted';
            btn.style.borderColor = 'var(--error)';
            btn.style.color = 'var(--error)';
        }
        showToast('We\'ll show less of this type');
    } catch (err) {
        console.warn('Dislike event failed:', err);
    }
}


async function loadInlineAd() {
    const container = document.getElementById('content-ad');
    if (!container) return;

    try {
        const data = await apiGetAdRecommendations(1);
        if (data.recommendations && data.recommendations.length > 0) {
            const ad = data.recommendations[0];
            container.innerHTML = `
                <div class="ad-card">
                    <div class="ad-label">
                        <span class="badge badge-sponsored">Sponsored</span>
                        ${ad.category_name ? `<span class="badge badge-category">${ad.category_name}</span>` : ''}
                    </div>
                    <h3 class="card-title">${escapeHtml(ad.title)}</h3>
                    <p class="card-desc">${escapeHtml(ad.description)}</p>
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

            // Record impression
            apiRecordImpression(ad.id, ad.score).catch(() => {});
        }
    } catch (err) {
        console.warn('Inline ad failed:', err);
    }
}
