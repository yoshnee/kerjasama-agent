"""Message classification module using SetFit."""

from typing import Union

from setfit import SetFitModel, Trainer, TrainingArguments
from datasets import Dataset

from constants import (
    CATEGORY_GREETING,
    CATEGORY_AVAILABILITY,
    CATEGORY_PRICING,
    CATEGORY_OTHER,
    TRAINED_CATEGORIES,
    CONFIDENCE_THRESHOLD,
)


# Training examples for each category (OTHER is not trained, it's inferred)
TRAINING_EXAMPLES = {
    CATEGORY_GREETING: [
    "Hello, I need help",
    "Hi, I'm interested in your services",
    "Hello, my name is Sarah and I would like to book an appointment",
    "Hi! I need a makeup artist for my wedding",
    "Good evening, I'd like to inquire about your services",
    "Hey, I saw your profile and I'm interested",
    "Hi there, can you help me?",
    "Hello, I'm planning an event",
    "Hi, I'm looking for someone to help with my birthday party",
    "Good morning! I need your services",
    "Hi, I'm Mira and I would like for you to be my wedding photographer",
    "Hello, I'm reaching out about booking your services",
    "Hi, I found you online and need a photographer",
    "Good afternoon, I'm interested in hiring you",
    "Hey! I'm looking for a makeup artist",
    "Hi there, I need help with my event",
    "Hello, I'm getting married and need a photographer",
    "Hi, my name is John and I'm looking to book",
    "Good morning, I'd like to inquire about availability",
    "Hey, I need someone for a photoshoot",
    "Hi! I'm planning a wedding and need your help",
    "Hello, can you help me with my upcoming event?",
    "Hi, I'm interested in booking you for a party",
    "Good evening, I'm looking for a professional photographer",
    "Hey there, I need a makeup artist for an event",
    "Hi, I came across your page and I'm interested",
    ],
    CATEGORY_AVAILABILITY: [
        "Are you free on this date?",
        "Do you have availability on Monday?",
        "When are you available?",
        "Are you available March 15th?",
        "Do you have any openings this weekend?",
        "Can you do Saturday the 20th?",
        "Are you free in the evening on Friday?",
        "What days are you available next month?",
        "Do you have time on the 3rd?",
        "Can you fit me in next Tuesday?",
        "Are you booked for December 10th?",
        "Do you have any slots open in January of 2026?",
        "I need someone for next Saturday, are you free?",
        "What's your availability like for April 2026?",
        "My event is on 25th of January 2027, are you available?",
        "Do you work on Sundays?",
        "What dates do you have available in July of next year?"
    ],
    CATEGORY_PRICING: [
        "What are your prices?",
        "How much do you charge?",
        "What's your rate?",
        "How much for wedding makeup?",
        "What do you charge per hour?",
        "Can you send me your pricing packages?",
        "What are your rates for events?",
        "How much would it cost for 3 hours?",
        "What's your pricing structure?",
        "Do you have a price list?",
        "How much for a full day?",
        "What are your packages?",
        "How much do you charge for videography?",
        "What's the cost for your services?",
        "What's your budget range?",
        "How much should I expect to pay?",
        "What are your fees?",
        "Is there a minimum charge?",
        "How much?",
        "Price?",
        "Cost?",
        "What do u charge",
        "Can u send pricing",
        "how much would it be",
        "what r ur prices",
        "price list?",
        "What's your pricing for a 2 hour session?",
        "How much do you charge for engagement photos?",
        "Do you have different pricing tiers?",
    ],
}


class MessageClassifier:
    """Classifier for WhatsApp messages using SetFit."""

    def __init__(self):
        """Load pre-trained SetFit model."""
        self.model = SetFitModel.from_pretrained(
            "sentence-transformers/paraphrase-MiniLM-L3-v2"
        )
        self.label_to_category = {i: cat for i, cat in enumerate(TRAINED_CATEGORIES)}
        self.category_to_label = {cat: i for i, cat in enumerate(TRAINED_CATEGORIES)}
        self._is_trained = False

    def train(self) -> None:
        """Fine-tune the model with example messages."""
        texts = []
        labels = []

        for category, examples in TRAINING_EXAMPLES.items():
            for text in examples:
                texts.append(text)
                labels.append(self.category_to_label[category])

        dataset = Dataset.from_dict({"text": texts, "label": labels})

        args = TrainingArguments(
            batch_size=4,
            num_epochs=11,
            num_iterations=5,
        )

        trainer = Trainer(
            model=self.model,
            args=args,
            train_dataset=dataset,
        )

        trainer.train()
        self._is_trained = True

    def classify(
        self, message: str, return_confidence: bool = False
    ) -> Union[str, tuple[str, float]]:
        """
        Classify a message into a category.

        Args:
            message: The message text to classify.
            return_confidence: If True, return tuple of (category, confidence).

        Returns:
            If return_confidence is False:
                One of: CATEGORY_GREETING, CATEGORY_AVAILABILITY, CATEGORY_PRICING, CATEGORY_OTHER
            If return_confidence is True:
                Tuple of (category, confidence_score)
        """
        # Get probability scores for each category
        probabilities = self.model.predict_proba([message])[0]

        # Find the category with highest confidence
        max_confidence = float(max(probabilities))
        predicted_label = int(probabilities.argmax())
        predicted_category = self.label_to_category[predicted_label]

        # If confidence is below threshold, classify as OTHER
        if max_confidence < CONFIDENCE_THRESHOLD:
            category = CATEGORY_OTHER
            confidence = max_confidence
        else:
            category = predicted_category
            confidence = max_confidence

        if return_confidence:
            return (category, confidence)
        return category
