# Real-Time AI Personalization & Ad Recommendation Platform

A genuinely functioning, end-to-end platform that collects real-time user interaction events, stores them in a normalized PostgreSQL database, derives behavioral features and user interests, feeds those features into a personalization and ad-ranking pipeline, predicts the likelihood of user interaction with candidate advertisements, ranks the candidates, serves the highest-ranked recommendations through a FastAPI backend, and records subsequent impressions/clicks back into the event pipeline to continuously update the user's profile.

**Every result is generated from actual data, actual database records, actual user interactions, and actual model logic. Nothing is hardcoded.**

## Architecture

```text
                    FRONTEND (Vanilla JS)
                         │
                         ▼
                   FASTAPI BACKEND
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
     Auth Service   Event Service   Recommendation
                                       Engine
          │              │              │
          └──────────────┼──────────────┘
                         │
                    PostgreSQL
                    ┌────┴────┐
                    ▼         ▼
              Analytics   ML Pipeline
              Service     (CTR Prediction)
                    │         │
                    └────┬────┘
                         ▼
                   User Profile
                   (Dynamic)
                         │
                    Redis Cache ──→ Frontend
```

### Feedback Loop

```text
User sees ad → AD_IMPRESSION event → Stored in DB
User clicks → AD_CLICK event → User interest updated
                              → CTR recalculated
                              → Next recommendations change
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend | FastAPI (Python) | Async REST API with auto-generated Swagger docs |
| Database | PostgreSQL 16 | Normalized relational schema, DBMS concepts |
| ORM | SQLAlchemy 2.0 (async) | Type-safe queries, parameterized (SQL injection safe) |
| Auth | JWT + bcrypt | Secure token-based authentication |
| ML | scikit-learn, XGBoost | CTR prediction model |
| Cache | Redis | Recommendation & profile caching |
| Frontend | Vanilla HTML/CSS/JS | Lightweight, fast-loading, no framework bloat |
| Containers | Docker Compose | Single-command dev environment |
| Testing | pytest + httpx | Unit and integration tests |

## Database Schema

14 tables with proper normalization, foreign keys, constraints, and indexes:

```text
users ──────┬── user_sessions ── events
            ├── user_interests
            ├── recommendations
            └── ab_test_assignments

advertisers ── campaigns ── advertisements ──┬── ad_impressions
                                             └── ad_clicks

content_categories ── content
ab_experiments ── ab_test_assignments
```

### DBMS Concepts Demonstrated

| Concept | Where |
|---------|-------|
| **Normalization (3NF)** | Categories in separate table, no redundant data |
| **Primary/Foreign Keys** | Every table has PK; FKs with ON DELETE CASCADE/SET NULL |
| **Indexes** | 25+ indexes on user_id, event_type, ad_id, timestamps |
| **CHECK Constraints** | affinity_score [0,1], budget > 0, valid event types |
| **UNIQUE Constraints** | username, email, user+category interest pairs |
| **JOINs** | Multi-table queries in analytics (campaigns→ads→impressions→clicks) |
| **Aggregations** | COUNT, AVG, GROUP BY for CTR, engagement, category metrics |
| **Transactions** | Batch event insertion, session lifecycle |
| **Query Optimization** | Composite indexes on (user_id, event_type), partial indexes |

### Example SQL (Analytics Query)

```sql
-- Campaign performance with multi-table JOIN
SELECT
    c.name AS campaign,
    a.name AS advertiser,
    COUNT(DISTINCT ai.id) AS impressions,
    COUNT(DISTINCT ac.id) AS clicks,
    ROUND(COUNT(DISTINCT ac.id)::numeric / NULLIF(COUNT(DISTINCT ai.id), 0), 4) AS ctr
FROM campaigns c
JOIN advertisers a ON c.advertiser_id = a.id
JOIN advertisements ad ON ad.campaign_id = c.id
LEFT JOIN ad_impressions ai ON ai.ad_id = ad.id
LEFT JOIN ad_clicks ac ON ac.ad_id = ad.id
GROUP BY c.id, c.name, a.name
ORDER BY impressions DESC;
```

## ML Pipeline

### CTR Prediction Model

```text
Training Data (PostgreSQL)
        ↓
Feature Engineering (10 features):
  - user_category_affinity
  - user_historical_ctr
  - ad_historical_ctr
  - num_previous_impressions/clicks
  - hour_of_day, day_of_week
  - user_engagement_score
  - ad_recency
  - bid_amount
        ↓
Train/Test Split (80/20, stratified)
        ↓
Models:
  1. Logistic Regression (baseline)
  2. Random Forest
  3. Gradient Boosting
        ↓
Evaluation:
  - ROC-AUC (primary, imbalance-friendly)
  - Precision, Recall, F1
  - Log Loss
        ↓
Best model saved → loaded at startup → inference
```

### Cold Start Strategy

| User Stage | Events | Strategy |
|-----------|--------|----------|
| New | < 10 | Popularity-based (global CTR + bid) |
| Transitioning | 10-50 | Blended (personalized + popular) |
| Established | > 50 | Full ML personalization |

## Recommendation Algorithm

```text
1. CANDIDATE GENERATION
   Filter: active campaigns, valid dates, budget remaining, frequency caps

2. FEATURE GENERATION (per user-ad pair)
   User affinity × ad category, historical CTR, engagement, recency, bid

3. SCORING
   ML model: predict_proba → P(click)
   Fallback: weighted formula (0.35×affinity + 0.25×engagement + 0.20×CTR + ...)

4. RANKING
   Sort by score, apply diversity constraints

5. SERVE top-N with scores and algorithm label
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register user |
| POST | /api/auth/login | Login, returns JWT |
| GET | /api/auth/me | Current user info |
| GET | /api/content | List content (paginated) |
| GET | /api/content/{id} | Content detail |
| GET | /api/content/categories | All categories |
| GET | /api/search?q=... | Search content |
| POST | /api/events | Record event |
| POST | /api/events/batch | Batch events |
| GET | /api/recommendations/ads | Personalized ads |
| GET | /api/recommendations/content | Personalized content |
| POST | /api/ads/{id}/impression | Record impression |
| POST | /api/ads/{id}/click | Record click (triggers feedback loop) |
| GET | /api/users/me/profile | Dynamic user profile |
| GET | /api/users/me/analytics | User analytics |
| POST | /api/sessions/start | Start session |
| POST | /api/sessions/{id}/end | End session |
| GET | /api/admin/analytics/overview | Platform metrics |
| GET | /api/admin/analytics/campaigns | Campaign performance |
| GET | /api/admin/analytics/categories | Category engagement |

Full interactive docs at: `http://localhost:8000/docs` (Swagger UI)

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and start
docker compose up --build

# Seed the database
docker compose exec backend python -m app.db.seed

# Train ML model
docker compose exec backend python scripts/train_model.py

# Open the app
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# 1. Start PostgreSQL and Redis (via Docker or locally)
docker run -d --name pg -p 5432:5432 -e POSTGRES_DB=adplatform -e POSTGRES_PASSWORD=postgres postgres:16-alpine
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env

# 4. Start the backend
uvicorn app.main:app --reload --port 8000

# 5. Seed the database
python -m app.db.seed

# 6. Train the ML model
python scripts/train_model.py

# 7. Serve the frontend
cd ../frontend
python -m http.server 5500
# Open http://localhost:5500
```

### Demo Login

After seeding, you can log in as any seed user:
- Username: `user_001` through `user_100`
- Password: `password123`

Or register a new account to experience the cold-start → personalization journey.

## Testing

```bash
cd backend

# Install test dependencies
pip install pytest pytest-asyncio httpx aiosqlite

# Run tests
pytest tests/ -v
```

## Event Flow

Every user action generates a real event:

```text
APP_OPEN → SEARCH → CONTENT_VIEW → CONTENT_LIKE
AD_IMPRESSION → AD_CLICK → AD_SKIP
SESSION_START → SESSION_END
```

Events are stored in PostgreSQL, used to:
1. Update user interest scores (feedback loop)
2. Compute engagement metrics
3. Generate ML training features
4. Calculate CTR and analytics

## Project Structure

```text
├── backend/
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── db/           # SQLAlchemy models, database, seed
│   │   ├── ml/           # Feature engineering, predictor
│   │   ├── schemas/      # Pydantic validation
│   │   ├── services/     # Business logic
│   │   ├── config.py     # Environment settings
│   │   └── main.py       # FastAPI app
│   ├── scripts/          # ML training pipeline
│   ├── tests/            # pytest tests
│   ├── ml_models/        # Trained model files
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   ├── js/               # API client, pages, routing
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

## Key Engineering Decisions

1. **No Kafka**: Event volume doesn't justify the operational complexity. FastAPI async + PostgreSQL handles ingestion efficiently. Can be added when genuine streaming needs arise.

2. **Vanilla frontend**: React/Vue would add build complexity without proportional value for this use case. Vanilla JS keeps the frontend under 30KB total.

3. **Two-tier recommendation**: Rule-based fallback ensures the system works without an ML model. ML enhances it when sufficient data exists.

4. **Affinity saturation formula**: `count / (count + decay_factor)` bounds scores to [0,1] and provides diminishing returns — a user who views 100 gaming articles isn't "infinitely" more interested than one who views 50.

5. **SQLite for tests, PostgreSQL for production**: Tests run fast without external dependencies while production uses full PostgreSQL features.

## Limitations & Future Improvements

### Current Limitations
- Single-instance deployment (no horizontal scaling)
- No real-time WebSocket updates (polling-based)
- ML model retrained offline (no online learning)
- Simple A/B testing (no multi-armed bandits)

### Future Improvements
- Kafka for high-volume event streaming
- Collaborative filtering (user-to-user similarity)
- Deep learning CTR models (DeepFM, Wide & Deep)
- Real-time model updates with online learning
- Geographic and demographic targeting
- Multi-armed bandit for exploration/exploitation
- Prometheus + Grafana monitoring
- Kubernetes deployment

## License

This is a portfolio/demonstration project.
