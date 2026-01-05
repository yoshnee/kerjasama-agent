"""Message classification module using SetFit and ModernBERT."""

import logging
import os
from typing import Union

from setfit import SetFitModel

from utils.constants import (
    CATEGORY_GREETING,
    CATEGORY_AVAILABILITY,
    CATEGORY_PRICING,
    CATEGORY_OTHER,
    CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "answerdotai/ModernBERT-base"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_PATH = os.path.join(BASE_DIR, "whatsapp_intent_model")


# Training examples for each category
TRAINING_EXAMPLES = {
    CATEGORY_GREETING: [
        "I'm interested in booking your services for an event",
        "Hi, I saw your work and want to inquire about a session",
        "Hello, I'm looking for a professional for my wedding",
        "Hi there, do you offer your services for large groups?",
        "Good evening, I'd like to inquire about your services",
        "Hey, I saw your profile and I'm interested",
        "Hey! I need a makeup artist for a photoshoot next month",
        "Hi, my name is Sarah and I'm interested in hiring you",
        "Hello, I found your profile and love your style, are you taking new clients?",
        "I'm reaching out to get some info on your business services",
        "Hi, I'm Mira and I would like for you to be my wedding photographer",
        "Hi! I'm looking for someone to handle my event's videography",
        "Hello, I'm getting married soon and need a stylist",
        "Good afternoon, I'm interested in hiring you",
        "Hi there, I got your number from a friend and I want to book you",
        "Hello, I'm getting married and need a photographer",
        "Hey, I would like to know more about your services",
        "Hi! my wedding is soon and I am interested in your wedding planning services",
        "Hello, can you help me with my upcoming event?",
        "Hi, I'm interested in booking you for a party",
        "Hey there, I need a makeup artist for an event",
        "Hi, I came across your page and I'm interested in hiring you",
    ],
    CATEGORY_AVAILABILITY: [
        "Are you free on date?",
        "Do you have availability on Monday?",
        "Do you have any openings this coming Saturday?"
        "When are you available?",
        "Are you available March 15th?",
        "Do you have any openings this weekend?",
        "Can you do Saturday the 20th?",
        "Are you free in the evening on Friday?",
        "Is June 15th still open on your calendar?"
        "What days are you available next month?",
        "Do you have time on the 3rd?",
        "Can you fit me in next Tuesday?",
        "Checking if you are available for a corporate event next Thursday?"
        "Are you booked for December 10th?",
        "Do you have any slots open in January of 2026?",
        "I need someone for next Saturday, are you free?",
        "What's your availability like for April 2026?",
        "My event is on 25th of January 2027, are you available?",
        "Do you work on Sundays?",
        "Are you available to work my wedding on June 5th, 2027?"
        "What dates do you have available in July of next year?",
    ],
    CATEGORY_PRICING: [
        "What are your prices?",
        "How much do you charge?",
        "What are your rates?"
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
        "I'm looking for a quote for your services",
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
        "How much do you charge for?",
        "Do you have different pricing tiers?",
    ],
    CATEGORY_OTHER: [
        # General Info (Not a booking request)
        "What are your business hours?",
        "Are you open on Sundays?",
        "Where is your studio located?",
        "What's your address?",
        "Do you have a website?",

        # Post-Service/Existing Client
        "Thanks for the photos, I love them!",
        "I just sent the deposit via bank transfer",
        "Can you send me the tracking number?",
        "I'm running 5 minutes late!",
        "Is my order ready for pickup?",

        # Pure Social/Noise
        "Hi", "Hello", "Hey there",
        "How are you today?",
        "Cool, thanks!",
        "Talk to you later",
        "Wrong number, sorry",
        "Ok", "Perfect",

        # Long sentences
        "I went to this place last night and the service was terrible, the food was cold and the waiter was rude, I'm never going back there again and I'm leaving a bad review.",
        "I was just telling my mom about how much I've been working lately and how I really need a vacation but I can't find the time because the kids have soccer and my car is in the shop again.",
        "Hey sorry I think I have the wrong number but while I have you do you know if the old bakery on 5th street is still open because I drove by and it looked closed.",
    ]
}


class MessageClassifier:
    """Classifier for WhatsApp messages using SetFit and ModernBERT."""

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        """
        Load pre-trained SetFit model.

        Args:
            model_path: Path to the trained model folder (default: 'whatsapp_intent_model')

        Raises:
            FileNotFoundError: If the model folder doesn't exist
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"No trained model found at '{model_path}'. "
                f"Run: python train_classifier.py"
            )

        logger.info("Loading pre-trained model from %s", model_path)
        self.model = SetFitModel.from_pretrained(model_path)
        logger.info("Loaded pre-trained model")

        # Dynamically generate label mappings from TRAINING_EXAMPLES keys
        self._categories = list(TRAINING_EXAMPLES.keys())
        self.label_to_category = {i: cat for i, cat in enumerate(self._categories)}
        self.category_to_label = {cat: i for i, cat in enumerate(self._categories)}

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
        clean_message = message.strip()

        # Too short - likely noise
        if len(clean_message) < 2:
            return (CATEGORY_OTHER, 0.0) if return_confidence else CATEGORY_OTHER

        # Too long (400+ chars) - likely off-topic rant or spam
        if len(clean_message) >= 400:
            return (CATEGORY_OTHER, 0.0) if return_confidence else CATEGORY_OTHER

        # Get probability scores for each category
        probabilities = self.model.predict_proba([message])[0]

        # Find the category with highest confidence
        max_confidence = float(max(probabilities))
        predicted_label = int(probabilities.argmax())
        predicted_category = self.label_to_category[predicted_label]

        # Return OTHER if: model predicts OTHER, OR confidence is below threshold
        if predicted_category == CATEGORY_OTHER or max_confidence < CONFIDENCE_THRESHOLD:
            category = CATEGORY_OTHER
        else:
            category = predicted_category

        if return_confidence:
            return (category, max_confidence)
        return category
