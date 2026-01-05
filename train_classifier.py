#!/usr/bin/env python3
"""
Training script for the WhatsApp message classifier.

Usage:
    python train_classifier.py

This script fine-tunes the SetFit model on the training examples
and saves the trained model to 'whatsapp_intent_model/' folder.
"""

import logging
import sys

from setfit import SetFitModel, Trainer, TrainingArguments
from datasets import Dataset

from src.classifier import MODEL_NAME, TRAINING_EXAMPLES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

OUTPUT_PATH = "whatsapp_intent_model"


def main():
    """Train and save the classifier model."""
    logger.info("Loading base model: %s", MODEL_NAME)
    model = SetFitModel.from_pretrained(MODEL_NAME)

    # Build training dataset
    categories = list(TRAINING_EXAMPLES.keys())
    category_to_label = {cat: i for i, cat in enumerate(categories)}

    texts = []
    labels = []

    for category, examples in TRAINING_EXAMPLES.items():
        if not examples:
            logger.warning("No training examples for category: %s", category)
            continue
        for text in examples:
            texts.append(text)
            labels.append(category_to_label[category])

    logger.info("Training with %d examples across %d categories", len(texts), len(categories))

    dataset = Dataset.from_dict({"text": texts, "label": labels})

    args = TrainingArguments(
        batch_size=16,
        num_epochs=3,
        num_iterations=20,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
    )

    logger.info("Starting training...")
    trainer.train()

    # Save the trained model
    logger.info("Saving model to %s/", OUTPUT_PATH)
    model.save_pretrained(OUTPUT_PATH)

    logger.info("Model trained and saved to %s/", OUTPUT_PATH)
    logger.info("You can now start the service with: uvicorn main:app --reload")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Training interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error("Training failed: %s", e)
        sys.exit(1)
