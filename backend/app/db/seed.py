"""
Seed data generator for the AI Personalization Platform.

Generates realistic synthetic data:
- 100 users with varied activity levels
- 10 content categories
- 200 content items across categories
- 10 advertisers with 30 campaigns and 100 ads
- ~50,000 historical events with realistic distributions
- Ad impressions and clicks with realistic CTR patterns
- User interests derived from event patterns

IMPORTANT: This is clearly synthetic seed data. Not real-world user data.
Users have designed interest patterns so the recommendation model can learn.
"""

import asyncio
import hashlib
import random
from datetime import datetime, timedelta, timezone, date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory, init_db
from app.db.models import (
    User, UserSession, ContentCategory, Content, Event,
    UserInterest, Advertiser, Campaign, Advertisement,
    AdImpression, AdClick, ABExperiment, ABTestAssignment,
)
from app.services.auth_service import hash_password


# ---- Configuration ----
NUM_USERS = 100
NUM_CONTENT_PER_CATEGORY = 20
NUM_ADVERTISERS = 10
NUM_CAMPAIGNS = 30
NUM_ADS = 100
EVENTS_PER_USER_RANGE = (50, 800)  # Varied activity levels
CLICK_PROBABILITY = 0.08  # 8% baseline CTR

CATEGORIES = [
    ("Gaming", "gaming", "Video games, esports, and gaming hardware"),
    ("Electronics", "electronics", "Gadgets, devices, and consumer electronics"),
    ("Technology", "technology", "Software, AI, cloud computing, and tech news"),
    ("Sports", "sports", "Sports news, fitness, and athletic gear"),
    ("Fashion", "fashion", "Clothing, accessories, and style trends"),
    ("Travel", "travel", "Destinations, hotels, flights, and travel tips"),
    ("Food", "food", "Recipes, restaurants, and food delivery"),
    ("Fitness", "fitness", "Workouts, health supplements, and wellness"),
    ("Entertainment", "entertainment", "Movies, music, streaming, and pop culture"),
    ("Business", "business", "Finance, startups, investing, and entrepreneurship"),
]

# Each user gets 2-3 "strong" categories (high interaction)
# and 1-2 "weak" categories (occasional interaction)
USER_INTEREST_PATTERNS = [
    (["gaming", "technology", "electronics"], ["entertainment"]),
    (["sports", "fitness"], ["food", "fashion"]),
    (["fashion", "entertainment"], ["travel"]),
    (["technology", "business"], ["electronics"]),
    (["food", "travel"], ["entertainment", "fashion"]),
    (["electronics", "gaming"], ["technology"]),
    (["business", "technology"], ["finance"]),
    (["entertainment", "gaming"], ["sports"]),
    (["fitness", "food"], ["sports", "travel"]),
    (["travel", "fashion"], ["food"]),
]

CONTENT_TEMPLATES = {
    "gaming": [
        ("Top 10 Battle Royale Games of 2026", "Discover the best battle royale games dominating the gaming scene this year."),
        ("RTX 5090 Review: Next-Gen Graphics", "A deep dive into NVIDIA's latest GPU and what it means for gamers."),
        ("Esports Tournament Guide", "Everything you need to know about upcoming competitive gaming events."),
        ("Best Gaming Keyboards 2026", "Mechanical keyboards that give you the competitive edge."),
        ("Cloud Gaming: Is It Ready?", "We test the latest cloud gaming platforms to see if they can replace consoles."),
    ],
    "electronics": [
        ("Smartphone Showdown: Pixel 12 vs iPhone 18", "Comparing the two flagship phones head-to-head."),
        ("Best Wireless Earbuds Under $100", "Great sound doesn't have to break the bank."),
        ("Smart Home Setup Guide", "Transform your home with these essential smart devices."),
        ("Foldable Laptops: The Future?", "Are foldable screens the next big thing in computing?"),
        ("Best Portable Chargers 2026", "Never run out of battery with these power banks."),
    ],
    "technology": [
        ("AI in Everyday Life", "How artificial intelligence is changing the way we work and live."),
        ("Cybersecurity Basics Everyone Should Know", "Protect yourself online with these essential tips."),
        ("The Rise of Edge Computing", "Why processing data closer to the source matters."),
        ("Open Source vs Proprietary Software", "Understanding the trade-offs in software licensing."),
        ("Quantum Computing Explained Simply", "Breaking down quantum computing for non-physicists."),
    ],
    "sports": [
        ("Premier League Season Preview", "Key transfers and predictions for the upcoming season."),
        ("Marathon Training for Beginners", "A 16-week plan to get you race-ready."),
        ("Best Running Shoes 2026", "Our picks for the best running shoes across all budgets."),
        ("Home Gym Essentials", "Build an effective home gym without spending a fortune."),
        ("The Science of Athletic Recovery", "Evidence-based recovery methods for athletes."),
    ],
    "fashion": [
        ("Sustainable Fashion Brands to Watch", "Eco-friendly fashion that doesn't compromise on style."),
        ("Minimalist Wardrobe Guide", "Build a versatile wardrobe with fewer pieces."),
        ("Sneaker Culture in 2026", "The trends shaping sneaker design and collecting."),
        ("Work From Home Style Guide", "Look professional on camera without sacrificing comfort."),
        ("Accessories That Elevate Any Outfit", "Small additions that make a big impact."),
    ],
    "travel": [
        ("Hidden Gems in Southeast Asia", "Off-the-beaten-path destinations worth exploring."),
        ("Budget Travel Tips for Europe", "See Europe without emptying your wallet."),
        ("Best Travel Apps 2026", "Apps that make travel planning and navigation effortless."),
        ("Solo Travel Safety Guide", "Stay safe while exploring the world on your own."),
        ("Digital Nomad Destinations", "The best cities for remote workers."),
    ],
    "food": [
        ("15-Minute Healthy Meal Prep", "Quick and nutritious meals for busy weekdays."),
        ("Best Coffee Makers for Home", "Barista-quality coffee without leaving your kitchen."),
        ("Plant-Based Protein Guide", "Complete protein sources for vegetarians and vegans."),
        ("Food Delivery App Comparison", "Which delivery service offers the best value?"),
        ("Kitchen Gadgets That Actually Work", "Useful tools that earn their counter space."),
    ],
    "fitness": [
        ("Bodyweight Workout Routine", "Build strength anywhere with no equipment needed."),
        ("Best Fitness Trackers 2026", "Wearables that help you reach your goals."),
        ("Nutrition for Muscle Growth", "What to eat to maximize your training results."),
        ("Yoga for Desk Workers", "Stretches and poses to combat sitting all day."),
        ("Sleep and Performance", "How quality sleep impacts your fitness gains."),
    ],
    "entertainment": [
        ("Best Streaming Shows This Month", "What to watch across Netflix, Disney+, and more."),
        ("Indie Music Discoveries", "Emerging artists you should be listening to."),
        ("Podcast Recommendations 2026", "Engaging podcasts across various genres."),
        ("Board Games for Adults", "Strategic and social games beyond the classics."),
        ("Virtual Reality Experiences", "The most immersive VR content available now."),
    ],
    "business": [
        ("Startup Funding Guide", "Understanding seed rounds, Series A, and beyond."),
        ("Remote Team Management", "Best practices for leading distributed teams."),
        ("Personal Finance Basics", "Essential money management skills for professionals."),
        ("Side Hustle Ideas for 2026", "Realistic ways to earn extra income."),
        ("AI in Business Strategy", "How companies are leveraging AI for competitive advantage."),
    ],
}

AD_TEMPLATES = {
    "gaming": [
        ("Gaming Laptop Pro X1", "Ultra-high performance laptop with RTX 5080. Built for serious gamers.", "Shop Now", 5.0),
        ("CloudPlay Premium", "Stream AAA games anywhere. First month free.", "Start Free Trial", 3.5),
        ("ProGamer Headset 7.1", "Immersive surround sound for competitive gaming.", "Buy Now", 2.5),
    ],
    "electronics": [
        ("SmartWatch Ultra", "Advanced health tracking, GPS, and 7-day battery life.", "Learn More", 4.0),
        ("NoiseFree ANC Earbuds", "Active noise cancellation with crystal-clear audio.", "Order Now", 3.0),
        ("HomeHub Smart Speaker", "Control your entire smart home with voice commands.", "Get Yours", 3.5),
    ],
    "technology": [
        ("CodeCloud IDE", "AI-powered cloud development environment. Code faster.", "Try Free", 4.5),
        ("CyberShield VPN", "Military-grade encryption. Protect your privacy online.", "Get Protected", 3.0),
        ("DataVault Backup", "Automatic cloud backup for all your devices.", "Start Backup", 2.0),
    ],
    "sports": [
        ("RunFast Pro Shoes", "Carbon-plated running shoes for your next PR.", "Shop Running", 3.5),
        ("FitTrack Band", "Advanced fitness tracking with real-time coaching.", "Get Fit", 2.5),
        ("SportFuel Protein", "Clean protein powder for peak performance.", "Order Now", 2.0),
    ],
    "fashion": [
        ("StyleBox Subscription", "Curated fashion delivered monthly. Personalized to your taste.", "Subscribe", 4.0),
        ("EcoWear Collection", "Sustainable fashion made from recycled materials.", "Shop Eco", 3.0),
        ("LuxWatch Classic", "Timeless design meets modern craftsmanship.", "Explore", 5.0),
    ],
    "travel": [
        ("WanderFlights Deal Finder", "AI-powered flight deals. Save up to 60%.", "Find Deals", 4.5),
        ("StayEasy Hotels", "Book unique accommodations worldwide.", "Book Now", 3.5),
        ("TravelGuard Insurance", "Comprehensive travel insurance from $4.99/day.", "Get Covered", 2.0),
    ],
    "food": [
        ("FreshBox Meal Kit", "Chef-designed meals delivered to your door.", "Start Cooking", 3.5),
        ("BrewMaster Coffee", "Premium single-origin coffee beans.", "Order Beans", 2.5),
        ("NutriPlan App", "Personalized meal planning and calorie tracking.", "Download Free", 2.0),
    ],
    "fitness": [
        ("HomeFit Equipment Bundle", "Complete home gym setup. Free shipping.", "Shop Now", 4.0),
        ("ZenYoga Online", "Unlimited yoga classes from world-class instructors.", "Join Free", 3.0),
        ("VitaBoost Supplements", "Science-backed supplements for active lifestyles.", "Shop Vitamins", 2.5),
    ],
    "entertainment": [
        ("StreamAll Premium", "One subscription for all your entertainment.", "Subscribe Now", 5.0),
        ("BookNest Unlimited", "Access thousands of ebooks and audiobooks.", "Read Free", 3.0),
        ("ConcertPass VIP", "Exclusive access to live events and concerts.", "Get VIP", 4.0),
    ],
    "business": [
        ("BizSuite CRM", "All-in-one business management platform.", "Start Free Trial", 5.0),
        ("InvestSmart App", "AI-powered investment recommendations.", "Start Investing", 4.0),
        ("SkillUp Pro", "Professional courses from industry experts.", "Learn More", 3.0),
    ],
}


async def seed_database():
    """Main seed function. Run with: python -m app.db.seed"""
    print("=" * 60)
    print("SEED DATA GENERATOR")
    print("Generating realistic synthetic data for the platform")
    print("=" * 60)

    await init_db()

    async with async_session_factory() as db:
        # Check if data already exists
        existing = await db.execute(select(User).limit(1))
        if existing.scalar_one_or_none():
            print("\n  Database already contains data. Skipping seed.")
            print("   Drop tables first if you want to re-seed.")
            return

        # ---- 1. Categories ----
        print("\n[1/8] Creating content categories...")
        cat_map = {}
        for name, slug, desc in CATEGORIES:
            cat = ContentCategory(name=name, slug=slug, description=desc)
            db.add(cat)
            await db.flush()
            cat_map[slug] = cat.id
        print(f"  ✓ Created {len(CATEGORIES)} categories")

        # ---- 2. Content ----
        print("[2/8] Creating content items...")
        content_count = 0
        content_ids_by_category = {}
        for slug, cat_id in cat_map.items():
            content_ids_by_category[slug] = []
            templates = CONTENT_TEMPLATES.get(slug, [])
            # Create from templates + generated variations
            for i in range(NUM_CONTENT_PER_CATEGORY):
                if i < len(templates):
                    title, desc = templates[i]
                else:
                    title = f"{slug.title()} Article #{i+1}"
                    desc = f"Interesting content about {slug} topics. Explore the latest trends and insights."
                content = Content(
                    title=title,
                    description=desc,
                    category_id=cat_id,
                    popularity_score=round(random.uniform(0.1, 0.95), 3),
                )
                db.add(content)
                await db.flush()
                content_ids_by_category[slug].append(content.id)
                content_count += 1
        print(f"  ✓ Created {content_count} content items")

        # ---- 3. Users ----
        print("[3/8] Creating users...")
        user_ids = []
        for i in range(NUM_USERS):
            user = User(
                username=f"user_{i+1:03d}",
                email=f"user{i+1}@example.com",
                password_hash=hash_password("password123"),
                device_type=random.choice(["desktop", "mobile", "tablet"]),
            )
            db.add(user)
            await db.flush()
            user_ids.append(user.id)
        print(f"  ✓ Created {NUM_USERS} users")

        # ---- 4. Advertisers & Campaigns & Ads ----
        print("[4/8] Creating advertisers, campaigns, and ads...")
        advertiser_names = [
            "TechGiant Inc", "FashionForward", "SportZone", "GameVerse",
            "TravelWise", "FoodieHub", "FitLife Co", "BizTools",
            "StreamMedia", "ElectroPro",
        ]
        ad_ids_by_category = {}
        all_ad_ids = []

        for i, name in enumerate(advertiser_names):
            adv = Advertiser(name=name, contact_email=f"ads@{name.lower().replace(' ', '')}.com")
            db.add(adv)
            await db.flush()

            # 2-4 campaigns per advertiser
            num_campaigns = random.randint(2, 4)
            for j in range(num_campaigns):
                start = date.today() - timedelta(days=random.randint(10, 60))
                campaign = Campaign(
                    advertiser_id=adv.id,
                    name=f"{name} Campaign {j+1}",
                    budget=round(random.uniform(1000, 10000), 2),
                    spent=0.0,
                    start_date=start,
                    end_date=start + timedelta(days=random.randint(60, 180)),
                )
                db.add(campaign)
                await db.flush()

                # 2-4 ads per campaign, targeting specific categories
                cat_slugs = list(cat_map.keys())
                target_slugs = random.sample(cat_slugs, min(3, len(cat_slugs)))

                for slug in target_slugs:
                    templates = AD_TEMPLATES.get(slug, [])
                    if templates:
                        tmpl = random.choice(templates)
                        title, desc, cta, bid = tmpl
                    else:
                        title = f"Ad for {slug.title()}"
                        desc = f"Great deals on {slug} products and services."
                        cta = "Learn More"
                        bid = round(random.uniform(1.0, 5.0), 2)

                    ad = Advertisement(
                        campaign_id=campaign.id,
                        target_category_id=cat_map[slug],
                        title=title,
                        description=desc,
                        cta_text=cta,
                        landing_url=f"https://example.com/{slug}/{random.randint(1000,9999)}",
                        bid_amount=bid,
                        frequency_cap=random.choice([5, 10, 15, 20]),
                    )
                    db.add(ad)
                    await db.flush()
                    all_ad_ids.append(ad.id)
                    if slug not in ad_ids_by_category:
                        ad_ids_by_category[slug] = []
                    ad_ids_by_category[slug].append(ad.id)

        print(f"  ✓ Created {len(advertiser_names)} advertisers, {len(all_ad_ids)} ads")

        # ---- 5. Sessions, Events, Impressions, Clicks ----
        print("[5/8] Generating user sessions and events...")
        total_events = 0
        total_impressions = 0
        total_clicks = 0

        for idx, user_id in enumerate(user_ids):
            # Assign interest pattern
            pattern = USER_INTEREST_PATTERNS[idx % len(USER_INTEREST_PATTERNS)]
            strong_cats, weak_cats = pattern

            # Number of events for this user (varied activity)
            num_events = random.randint(*EVENTS_PER_USER_RANGE)

            # Create 3-10 sessions
            num_sessions = random.randint(3, 10)
            session_ids = []
            base_time = datetime.now(None) - timedelta(days=random.randint(7, 30))

            for s in range(num_sessions):
                session_start = base_time + timedelta(
                    hours=random.randint(0, 720),
                    minutes=random.randint(0, 59),
                )
                duration = random.randint(120, 2400)  # 2-40 minutes
                session = UserSession(
                    user_id=user_id,
                    started_at=session_start,
                    ended_at=session_start + timedelta(seconds=duration),
                    duration_seconds=duration,
                    device_type=random.choice(["desktop", "mobile", "tablet"]),
                )
                db.add(session)
                await db.flush()
                session_ids.append((session.id, session_start, duration))

            # Generate events distributed across sessions
            events_per_session = num_events // num_sessions

            for session_id, session_start, duration in session_ids:
                for e in range(events_per_session):
                    event_time = session_start + timedelta(
                        seconds=random.randint(0, duration)
                    )

                    # Choose category based on interest pattern
                    if random.random() < 0.7:
                        cat_slug = random.choice(strong_cats)
                    elif weak_cats:
                        cat_slug = random.choice(weak_cats)
                    else:
                        cat_slug = random.choice(list(cat_map.keys()))

                    # Decide event type with realistic distribution
                    roll = random.random()
                    if roll < 0.35:
                        event_type = "CONTENT_VIEW"
                        entity_type = "content"
                        entity_id = random.choice(content_ids_by_category.get(cat_slug, [1]))
                    elif roll < 0.45:
                        event_type = "CONTENT_LIKE"
                        entity_type = "content"
                        entity_id = random.choice(content_ids_by_category.get(cat_slug, [1]))
                    elif roll < 0.50:
                        event_type = "CONTENT_DISLIKE"
                        entity_type = "content"
                        entity_id = random.choice(content_ids_by_category.get(cat_slug, [1]))
                    elif roll < 0.55:
                        event_type = "SEARCH"
                        entity_type = None
                        entity_id = None
                    elif roll < 0.60:
                        event_type = "APP_OPEN"
                        entity_type = None
                        entity_id = None
                    else:
                        # Ad events
                        ad_cat_ads = ad_ids_by_category.get(cat_slug, all_ad_ids[:5])
                        ad_id = random.choice(ad_cat_ads) if ad_cat_ads else random.choice(all_ad_ids)
                        entity_type = "advertisement"
                        entity_id = ad_id

                        # Create impression
                        impression = AdImpression(
                            ad_id=ad_id,
                            user_id=user_id,
                            session_id=session_id,
                            recommendation_score=round(random.uniform(0.3, 0.95), 4),
                            source="recommendation",
                            created_at=event_time,
                        )
                        db.add(impression)
                        await db.flush()
                        total_impressions += 1

                        event_type = "AD_IMPRESSION"

                        # Determine if click happens
                        # Higher CTR for strong-interest categories
                        click_prob = CLICK_PROBABILITY
                        if cat_slug in strong_cats:
                            click_prob *= 2.0  # 16% for strong interests
                        if random.random() < click_prob:
                            click = AdClick(
                                impression_id=impression.id,
                                ad_id=ad_id,
                                user_id=user_id,
                                created_at=event_time + timedelta(seconds=random.randint(1, 10)),
                            )
                            db.add(click)
                            total_clicks += 1

                            # Also add click event
                            click_event = Event(
                                user_id=user_id,
                                session_id=session_id,
                                event_type="AD_CLICK",
                                entity_type="advertisement",
                                entity_id=ad_id,
                                created_at=event_time + timedelta(seconds=random.randint(1, 10)),
                            )
                            db.add(click_event)
                            total_events += 1

                    event = Event(
                        user_id=user_id,
                        session_id=session_id,
                        event_type=event_type,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        created_at=event_time,
                        metadata_={"source": "seed", "device": random.choice(["desktop", "mobile"])},
                    )
                    db.add(event)
                    total_events += 1

            if (idx + 1) % 20 == 0:
                await db.flush()
                print(f"  ... processed {idx + 1}/{NUM_USERS} users")

        print(f"  ✓ Generated {total_events} events, {total_impressions} impressions, {total_clicks} clicks")
        print(f"  ✓ Seed CTR: {total_clicks / max(total_impressions, 1):.2%}")

        # ---- 6. User Interests (derived from events) ----
        print("[6/8] Computing user interests from events...")
        decay_factor = 10
        for user_id in user_ids:
            # Count interactions per category for this user
            from sqlalchemy import text as sql_text
            result = await db.execute(
                select(
                    Content.category_id,
                    func.count().label("cnt"),
                )
                .select_from(Event)
                .join(Content, (Event.entity_id == Content.id) & (Event.entity_type == "content"))
                .where(
                    Event.user_id == user_id,
                    Event.event_type.in_(("CONTENT_VIEW", "CONTENT_LIKE")),
                )
                .group_by(Content.category_id)
            )
            for cat_id, cnt in result.all():
                if cat_id:
                    affinity = cnt / (cnt + decay_factor)
                    interest = UserInterest(
                        user_id=user_id,
                        category_id=cat_id,
                        affinity_score=round(min(affinity, 1.0), 4),
                        interaction_count=cnt,
                        last_interaction_at=datetime.now(None),
                    )
                    db.add(interest)

            # Also add interests from ad clicks
            ad_result = await db.execute(
                select(
                    Advertisement.target_category_id,
                    func.count().label("cnt"),
                )
                .select_from(Event)
                .join(Advertisement, (Event.entity_id == Advertisement.id) & (Event.entity_type == "advertisement"))
                .where(
                    Event.user_id == user_id,
                    Event.event_type == "AD_CLICK",
                )
                .group_by(Advertisement.target_category_id)
            )
            for cat_id, cnt in ad_result.all():
                if cat_id:
                    # Check if interest already exists, update if so
                    existing = await db.execute(
                        select(UserInterest).where(
                            UserInterest.user_id == user_id,
                            UserInterest.category_id == cat_id,
                        )
                    )
                    ex = existing.scalar_one_or_none()
                    if ex:
                        ex.interaction_count += cnt
                        ex.affinity_score = round(
                            min(ex.interaction_count / (ex.interaction_count + decay_factor), 1.0), 4
                        )
                    else:
                        interest = UserInterest(
                            user_id=user_id,
                            category_id=cat_id,
                            affinity_score=round(min(cnt / (cnt + decay_factor), 1.0), 4),
                            interaction_count=cnt,
                            last_interaction_at=datetime.now(None),
                        )
                        db.add(interest)

        print("  ✓ User interests computed")

        # ---- 7. A/B Experiment ----
        print("[7/8] Creating A/B experiment...")
        experiment = ABExperiment(
            name="personalized_vs_popular",
            description="Compare personalized ML recommendations against popularity-based baseline",
            variant_a_name="popularity",
            variant_b_name="personalized",
        )
        db.add(experiment)
        await db.flush()

        # Assign users deterministically
        for user_id in user_ids:
            variant = "A" if (hash(f"{user_id}_{experiment.id}") % 2 == 0) else "B"
            assignment = ABTestAssignment(
                experiment_id=experiment.id,
                user_id=user_id,
                variant=variant,
            )
            db.add(assignment)
        print("  ✓ A/B experiment created with user assignments")

        # ---- 8. Commit ----
        print("[8/8] Committing to database...")
        await db.commit()

        print("\n" + "=" * 60)
        print("SEED DATA GENERATION COMPLETE")
        print("=" * 60)
        print(f"  Users:       {NUM_USERS}")
        print(f"  Categories:  {len(CATEGORIES)}")
        print(f"  Content:     {content_count}")
        print(f"  Advertisers: {len(advertiser_names)}")
        print(f"  Ads:         {len(all_ad_ids)}")
        print(f"  Events:      {total_events}")
        print(f"  Impressions: {total_impressions}")
        print(f"  Clicks:      {total_clicks}")
        print(f"  Seed CTR:    {total_clicks / max(total_impressions, 1):.2%}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_database())
