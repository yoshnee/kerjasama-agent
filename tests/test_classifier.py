"""Tests for message classifier module."""

import pytest

from classifier import MessageClassifier
from constants import (
    CATEGORY_GREETING,
    CATEGORY_AVAILABILITY,
    CATEGORY_PRICING,
    CATEGORY_OTHER,
    CONFIDENCE_THRESHOLD,
)


@pytest.fixture(scope="module")
def trained_classifier() -> MessageClassifier:
    """
    Initialize and train classifier once for all tests.

    This fixture uses module scope to avoid expensive retraining
    for each test function.
    """
    classifier = MessageClassifier()
    classifier.train()
    return classifier


@pytest.fixture
def fresh_classifier() -> MessageClassifier:
    """Create a fresh untrained classifier instance for each test."""
    return MessageClassifier()


@pytest.fixture
def sample_messages() -> dict:
    """
    Return dictionary of sample messages for each category.

    These are test messages distinct from training data.
    """
    return {
        "greeting_messages": [
            "Hi there. My name is John and I am interested in hiring you for my wedding.",
            "Hello JS Photography, I got your contact from a friend and I was wondering if you could bake cookies for my event.",
        ],
        "availability_messages": [
            "My wedding is on Jan 23rd 2026, are you available?",
            "Do you work in July",
            "Are you available in two weeks?",
        ],
        "pricing_messages": [
            "Can you share your pricing packages with me?",
            "Can send me your costs? My budget is a little low",
            "How much you charge?",
        ],
        "other_messages": [
            "I just adopted a cat",
            "I'm thinking blue color will be better",
            "Thanks so much!",
            "Can you send me the contract?",
        ],
    }


def test_classifier_initialization(fresh_classifier, trained_classifier):
    assert not fresh_classifier._is_trained
    assert trained_classifier._is_trained


def test_classify_greeting(trained_classifier, sample_messages):
    for message in sample_messages["greeting_messages"]:
         assert trained_classifier.classify(message) == CATEGORY_GREETING

def test_classify_greeting_with_confidence_score(trained_classifier, sample_messages):
    for message in sample_messages["greeting_messages"]:
        (classification, score) = trained_classifier.classify(message, True)
        assert classification == CATEGORY_GREETING
        assert score >= CONFIDENCE_THRESHOLD


def test_classify_availability(trained_classifier, sample_messages):
    for message in sample_messages["availability_messages"]:
        assert trained_classifier.classify(message) == CATEGORY_AVAILABILITY

def test_classify_availability_with_confidence_score(trained_classifier, sample_messages):
    for message in sample_messages["availability_messages"]:
        (classification, score) = trained_classifier.classify(message, True)
        assert classification == CATEGORY_AVAILABILITY
        assert score >= CONFIDENCE_THRESHOLD

def test_classify_pricing(trained_classifier, sample_messages):
    for message in sample_messages["pricing_messages"]:
        assert trained_classifier.classify(message) == CATEGORY_PRICING

def test_classify_pricing_with_confidence_score(trained_classifier, sample_messages):
    for message in sample_messages["pricing_messages"]:
        (classification, score) = trained_classifier.classify(message, True)
        assert classification == CATEGORY_PRICING
        assert score >= CONFIDENCE_THRESHOLD

def test_classify_other(trained_classifier, sample_messages):
    for message in sample_messages["other_messages"]:
        assert trained_classifier.classify(message) == CATEGORY_OTHER

def test_classify_other_with_confidence_score(trained_classifier, sample_messages):
    for message in sample_messages["other_messages"]:
        (classification, score) = trained_classifier.classify(message, True)
        #print(f"{message[:30]:30} → {classification:15} (confidence: {score:.3f})")
        assert classification == CATEGORY_OTHER
        assert score < CONFIDENCE_THRESHOLD


def test_classifier_edge_cases(trained_classifier):
    trained_classifier.classify("") == CATEGORY_OTHER

    trained_classifier.classify("I just wanted to say that I went to this restaurant last night and the service was absolutely terrible, like I've been going there for years and they used to be so good but now it's like they don't even care anymore, the waiter took forever to come to our table and when he finally did he was super rude and didn't even apologize for the wait, then the food came out cold and we had to send it back twice, TWICE!, and by the time we got it back everyone else at the table was already done eating so I just sat there awkwardly while they watched me eat my reheated pasta that was still somehow undercooked, and to top it all off they had the nerve to add an automatic gratuity to the bill even though the service was awful, I mean I get it if you have a large party but there were only four of us, anyway I'm never going back there again and I left them a terrible review on Yelp, I just can't believe how much that place has gone downhill, it's such a shame because it used to be my favorite spot in the neighborhood") == CATEGORY_OTHER

    trained_classifier.classify("Wah seriously lah, today I went to the bank and waited for like one hour just to update my address, the system pulak down so they asked me to come back tomorrow, memang waste my time only, I took leave from work for this also!") == CATEGORY_OTHER
