import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer


# Resolve paths relative to this file, regardless of where Python starts.
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


@lru_cache(maxsize=1)
def load_classifier():
    """Load once per Python process."""
    config = json.loads(
        (ARTIFACT_DIR / "config.json").read_text(encoding="utf-8")
    )

    model = SentenceTransformer(
        str(ARTIFACT_DIR / "embedding_model"),
        device="cpu",
    )

    knn = joblib.load(ARTIFACT_DIR / "knn.joblib")

    categories = np.load(
        ARTIFACT_DIR / "train_categories.npy",
        allow_pickle=False,
    )

    if len(categories) != knn.n_samples_fit_:
        raise ValueError("Training labels and classifier size do not match.")

    return model, knn, categories, config


def triage_ticket(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Please enter a non-empty ticket description.")

    text = text.strip()
    model, knn, categories, config = load_classifier()

    embedding = model.encode(
        [text],
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    prediction = str(knn.predict(embedding)[0])
    distances, indices = knn.kneighbors(embedding)

    top_similarity = float(1 - distances[0, 0])
    vote_agreement = float(
        (categories[indices[0]] == prediction).mean()
    )

    reasons = []

    if top_similarity < config["min_similarity"]:
        reasons.append("Low similarity to training examples")

    if vote_agreement < config["min_agreement"]:
        reasons.append("Split neighbor votes")

    return {
        "ticket": text,
        "predicted_category": prediction,
        "suggested_team": config["team_by_category"][prediction],
        "status": (
            "Needs human review" if reasons
            else "Automatically accepted"
        ),
        "top_similarity": top_similarity,
        "vote_agreement": vote_agreement,
        "review_reason": "; ".join(reasons) if reasons else None,
    }


if __name__ == "__main__":
    result = triage_ticket("I was charged twice for my order.")
    print(json.dumps(result, indent=2))