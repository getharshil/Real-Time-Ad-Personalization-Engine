"""
ML Training Pipeline for CTR Prediction.

This script:
1. Connects to PostgreSQL and extracts training data from actual records
2. Engineers features from ad_impressions, ad_clicks, user_interests, and events
3. Trains multiple models (Logistic Regression, Random Forest, XGBoost)
4. Evaluates using ROC-AUC, Precision, Recall, F1, Log Loss
5. Saves the best model as a .pkl file for inference

Run: python scripts/train_model.py
"""

import os
import sys
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

warnings.filterwarnings("ignore")

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def get_db_url():
    """Get sync database URL from environment or default."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    return os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://postgres:postgres@localhost:5432/adplatform"
    )


def extract_training_data(engine) -> pd.DataFrame:
    """
    Extract training data from PostgreSQL using real JOINs and aggregations.

    Each row represents one ad impression with a binary label (clicked/not clicked).

    Features are derived from:
    - user_interests (category affinity)
    - ad_impressions + ad_clicks (historical CTR)
    - events (engagement metrics)
    - advertisements (bid, recency)
    """
    print("\n[1/5] Extracting training data from PostgreSQL...")

    query = text("""
        WITH user_stats AS (
            SELECT
                user_id,
                COUNT(*) AS total_events,
                COUNT(*) FILTER (WHERE event_type IN ('CONTENT_VIEW', 'CONTENT_LIKE', 'AD_CLICK', 'SEARCH'))
                    AS interactive_events
            FROM events
            GROUP BY user_id
        ),
        user_ad_stats AS (
            SELECT
                ai.user_id,
                ai.ad_id,
                COUNT(DISTINCT ai.id) AS user_ad_impressions,
                COUNT(DISTINCT ac.id) AS user_ad_clicks
            FROM ad_impressions ai
            LEFT JOIN ad_clicks ac ON ac.ad_id = ai.ad_id AND ac.user_id = ai.user_id
            GROUP BY ai.user_id, ai.ad_id
        ),
        ad_stats AS (
            SELECT
                ai.ad_id,
                COUNT(DISTINCT ai.id) AS total_ad_impressions,
                COUNT(DISTINCT ac.id) AS total_ad_clicks
            FROM ad_impressions ai
            LEFT JOIN ad_clicks ac ON ac.ad_id = ai.ad_id
            GROUP BY ai.ad_id
        ),
        user_ctr AS (
            SELECT
                ai.user_id,
                COUNT(DISTINCT ai.id) AS total_user_impressions,
                COUNT(DISTINCT ac.id) AS total_user_clicks
            FROM ad_impressions ai
            LEFT JOIN ad_clicks ac ON ac.user_id = ai.user_id AND ac.impression_id = ai.id
            GROUP BY ai.user_id
        )
        SELECT
            ai.id AS impression_id,
            ai.user_id,
            ai.ad_id,
            a.target_category_id,
            COALESCE(ui.affinity_score, 0.0) AS user_category_affinity,
            COALESCE(
                uc.total_user_clicks::float / NULLIF(uc.total_user_impressions, 0),
                0.0
            ) AS user_historical_ctr,
            COALESCE(
                ads.total_ad_clicks::float / NULLIF(ads.total_ad_impressions, 0),
                0.0
            ) AS ad_historical_ctr,
            COALESCE(uas.user_ad_impressions, 0) AS num_previous_impressions,
            COALESCE(uas.user_ad_clicks, 0) AS num_previous_clicks,
            EXTRACT(HOUR FROM ai.created_at) AS hour_of_day,
            EXTRACT(DOW FROM ai.created_at) AS day_of_week,
            COALESCE(
                us.interactive_events::float / NULLIF(us.total_events, 0),
                0.0
            ) AS user_engagement_score,
            EXTRACT(EPOCH FROM (NOW() - a.created_at)) / 86400.0 AS ad_age_days,
            a.bid_amount,
            CASE WHEN ac.id IS NOT NULL THEN 1 ELSE 0 END AS clicked
        FROM ad_impressions ai
        JOIN advertisements a ON a.id = ai.ad_id
        LEFT JOIN user_interests ui ON ui.user_id = ai.user_id AND ui.category_id = a.target_category_id
        LEFT JOIN user_stats us ON us.user_id = ai.user_id
        LEFT JOIN user_ad_stats uas ON uas.user_id = ai.user_id AND uas.ad_id = ai.ad_id
        LEFT JOIN ad_stats ads ON ads.ad_id = ai.ad_id
        LEFT JOIN user_ctr uc ON uc.user_id = ai.user_id
        LEFT JOIN ad_clicks ac ON ac.impression_id = ai.id
        ORDER BY ai.id
    """)

    df = pd.read_sql(query, engine)
    print(f"  ✓ Extracted {len(df)} impression records")
    print(f"  ✓ Positive class (clicked): {df['clicked'].sum()} ({df['clicked'].mean():.2%})")
    print(f"  ✓ Negative class (not clicked): {(1 - df['clicked']).sum()}")

    return df


def engineer_features(df: pd.DataFrame) -> tuple:
    """
    Prepare feature matrix and labels.
    Normalize features to [0, 1] range for model consumption.
    """
    print("\n[2/5] Engineering features...")

    feature_cols = [
        "user_category_affinity",
        "user_historical_ctr",
        "ad_historical_ctr",
        "num_previous_impressions",
        "num_previous_clicks",
        "hour_of_day",
        "day_of_week",
        "user_engagement_score",
        "ad_age_days",
        "bid_amount",
    ]

    X = df[feature_cols].copy()

    # Normalize features
    X["num_previous_impressions"] = X["num_previous_impressions"].clip(0, 50) / 50.0
    X["num_previous_clicks"] = X["num_previous_clicks"].clip(0, 10) / 10.0
    X["hour_of_day"] = X["hour_of_day"] / 23.0
    X["day_of_week"] = X["day_of_week"] / 6.0
    X["ad_age_days"] = 1.0 - (X["ad_age_days"].clip(0, 90) / 90.0)  # Newer = higher
    X["bid_amount"] = X["bid_amount"].clip(0, 10) / 10.0

    # Fill NaN with 0
    X = X.fillna(0.0)

    y = df["clicked"].values

    print(f"  ✓ Feature matrix shape: {X.shape}")
    print(f"  ✓ Feature names: {list(X.columns)}")
    print(f"  ✓ Label distribution: {np.bincount(y)}")

    return X, y, feature_cols


def train_and_evaluate(X, y, feature_cols):
    """
    Train multiple models, evaluate, and select the best one.

    Models:
    1. Logistic Regression (baseline — interpretable)
    2. Random Forest (ensemble — captures non-linear patterns)
    3. Gradient Boosting (strongest for tabular data)

    Evaluation metrics (important for imbalanced CTR data):
    - ROC-AUC (primary — class-imbalance friendly)
    - Precision, Recall, F1
    - Log Loss
    """
    print("\n[3/5] Training models...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  Train: {len(X_train)}, Test: {len(X_test)}")
    print(f"  Train positive rate: {y_train.mean():.2%}")
    print(f"  Test positive rate:  {y_test.mean():.2%}")

    models = {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=42
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100, max_depth=10, class_weight="balanced",
            random_state=42, n_jobs=-1
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.1,
            random_state=42
        ),
    }

    results = {}
    best_model = None
    best_auc = 0.0
    best_name = ""

    for name, model in models.items():
        print(f"\n  Training {name}...")
        start = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - start

        # Predictions
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        # Metrics
        auc = roc_auc_score(y_test, y_proba)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        logloss = log_loss(y_test, y_proba)

        results[name] = {
            "model": model,
            "auc": auc,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "log_loss": logloss,
            "train_time": train_time,
        }

        print(f"    ROC-AUC:   {auc:.4f}")
        print(f"    Precision: {precision:.4f}")
        print(f"    Recall:    {recall:.4f}")
        print(f"    F1:        {f1:.4f}")
        print(f"    Log Loss:  {logloss:.4f}")
        print(f"    Time:      {train_time:.2f}s")

        if auc > best_auc:
            best_auc = auc
            best_model = model
            best_name = name

    # Feature importance for the best model
    print(f"\n  Best model: {best_name} (AUC: {best_auc:.4f})")

    if hasattr(best_model, "feature_importances_"):
        importances = best_model.feature_importances_
        print("\n  Feature Importances:")
        for fname, imp in sorted(zip(feature_cols, importances), key=lambda x: -x[1]):
            bar = "█" * int(imp * 50)
            print(f"    {fname:30s} {imp:.4f} {bar}")
    elif hasattr(best_model, "coef_"):
        coefs = best_model.coef_[0]
        print("\n  Feature Coefficients:")
        for fname, coef in sorted(zip(feature_cols, coefs), key=lambda x: -abs(x[1])):
            print(f"    {fname:30s} {coef:+.4f}")

    return best_model, best_name, results


def save_model(model, model_path: str):
    """Save the trained model to disk."""
    print(f"\n[4/5] Saving model to {model_path}...")
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    size_kb = os.path.getsize(model_path) / 1024
    print(f"  ✓ Model saved ({size_kb:.1f} KB)")


def print_summary(results: dict):
    """Print a comparison table of all models."""
    print("\n[5/5] Model Comparison Summary")
    print("=" * 80)
    print(f"{'Model':<25s} {'AUC':>8s} {'Prec':>8s} {'Recall':>8s} {'F1':>8s} {'LogLoss':>8s} {'Time':>8s}")
    print("-" * 80)
    for name, r in results.items():
        print(
            f"{name:<25s} {r['auc']:>8.4f} {r['precision']:>8.4f} "
            f"{r['recall']:>8.4f} {r['f1']:>8.4f} {r['log_loss']:>8.4f} {r['train_time']:>7.2f}s"
        )
    print("=" * 80)


def main():
    print("=" * 60)
    print("CTR PREDICTION MODEL TRAINING PIPELINE")
    print("=" * 60)

    # Connect to database
    db_url = get_db_url()
    print(f"\nConnecting to: {db_url.split('@')[1] if '@' in db_url else db_url}")
    engine = create_engine(db_url)

    # Extract data
    df = extract_training_data(engine)

    if len(df) < 100:
        print("\n  Not enough data for training. Run seed data first:")
        print("   python -m app.db.seed")
        return

    # Engineer features
    X, y, feature_cols = engineer_features(df)

    # Train and evaluate
    best_model, best_name, results = train_and_evaluate(X, y, feature_cols)

    # Save best model
    model_path = os.path.join(os.path.dirname(__file__), "..", "ml_models", "ctr_model.pkl")
    save_model(best_model, model_path)

    # Summary
    print_summary(results)

    print(f"\n✓ Training complete. Best model: {best_name}")
    print(f"  Restart the backend to load the new model for inference.")

    engine.dispose()


if __name__ == "__main__":
    main()
