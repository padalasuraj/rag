"""Seed a demo knowledge base so the UI has something to explore immediately.

Run from the backend directory. It generates real local embeddings, so install
the embedding dependencies first:

    python -m scripts.seed_demo

It creates a KB called "Introduction to Machine Learning" with two text sources
and processes them synchronously through the real ingestion pipeline.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.models import KnowledgeBase, Source
from app.services import ingestion_service

DEMO_NAME = "Introduction to Machine Learning"

SOURCES: list[tuple[str, str]] = [
    (
        "Regression Basics",
        """Linear regression models the relationship between input features and a
continuous target by fitting a straight line that minimizes the mean squared
error between predictions and actual values. It assumes a roughly linear
relationship and is easy to interpret because each coefficient represents the
effect of one feature.

Logistic regression, despite its name, is a classification algorithm. It passes
a linear combination of the features through the sigmoid function to produce a
probability between 0 and 1, and then applies a threshold to decide the class.
The main advantages of logistic regression are that it is simple, fast to train,
highly interpretable, and outputs calibrated probabilities rather than just a
label. It works best when classes are roughly linearly separable.

The key difference between the two is the target: linear regression predicts a
continuous number, while logistic regression predicts the probability of a
category.""",
    ),
    (
        "Overfitting and Regularization",
        """Overfitting occurs when a model learns the noise and idiosyncrasies of the
training data instead of the underlying pattern. An overfit model performs very
well on training data but poorly on unseen data because it fails to generalize.
Signs include a large gap between training accuracy and validation accuracy.

Regularization combats overfitting by penalizing model complexity. L2
regularization (ridge) adds the squared magnitude of the weights to the loss,
shrinking them toward zero. L1 regularization (lasso) adds the absolute
magnitude, which can drive some weights exactly to zero and thus perform feature
selection.

Other practical defenses against overfitting include gathering more training
data, using cross-validation to tune hyperparameters, applying dropout in neural
networks, and stopping training early when validation performance stops
improving.""",
    ),
]


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        existing = db.execute(
            select(KnowledgeBase).where(KnowledgeBase.name == DEMO_NAME)
        ).scalar_one_or_none()
        if existing:
            print(f"Demo knowledge base already exists (id={existing.id}). Skipping.")
            return

        kb = KnowledgeBase(name=DEMO_NAME, description="Sample data — safe to delete.", is_demo=True)
        db.add(kb)
        db.commit()
        db.refresh(kb)
        print(f"Created knowledge base: {kb.name} (id={kb.id})")

        for title, content in SOURCES:
            source = Source(
                knowledge_base_id=kb.id,
                source_type="text",
                title=title,
                status="pending",
                meta={"char_count": len(content)},
            )
            db.add(source)
            db.commit()
            db.refresh(source)
            print(f"  Ingesting '{title}' ...", end=" ", flush=True)
            ingestion_service.ingest_text(source.id, content)
            db.refresh(source)
            print(f"{source.status} ({source.num_chunks} chunks)")

        print("\nDemo seed complete. Open the app and select the demo knowledge base.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
