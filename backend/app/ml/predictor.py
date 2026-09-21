"""
ML model predictor: loads trained model and performs CTR prediction inference.

The model is trained offline (see scripts/train_model.py) and loaded at startup.
If no model file exists, the system gracefully falls back to rule-based scoring.
"""

import logging
import os
from typing import List, Optional

import joblib
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Global model instance
_model = None
_model_loaded = False


class CTRPredictor:
    """Wraps a scikit-learn compatible model for CTR prediction."""

    def __init__(self, model):
        self.model = model

    def predict_ctr(self, features: List[float]) -> float:
        """Predict click-through probability for a single feature vector."""
        X = np.array(features).reshape(1, -1)
        proba = self.model.predict_proba(X)
        # Return probability of class 1 (clicked)
        return float(proba[0][1])

    def predict_batch(self, feature_matrix: List[List[float]]) -> List[float]:
        """Predict CTR for a batch of feature vectors."""
        X = np.array(feature_matrix)
        proba = self.model.predict_proba(X)
        return [float(p[1]) for p in proba]


def load_model() -> Optional[CTRPredictor]:
    """Load the trained model from disk."""
    global _model, _model_loaded

    model_path = settings.model_path
    if not os.path.exists(model_path):
        logger.warning(f"Model file not found at {model_path}. Using rule-based scoring.")
        _model_loaded = False
        return None

    try:
        raw_model = joblib.load(model_path)
        _model = CTRPredictor(raw_model)
        _model_loaded = True
        logger.info(f"CTR prediction model loaded from {model_path}")
        return _model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        _model_loaded = False
        return None


def get_predictor() -> Optional[CTRPredictor]:
    """Get the current model predictor, or None if no model is loaded."""
    global _model, _model_loaded
    if not _model_loaded:
        return None
    return _model
