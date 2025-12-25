"""Reusable constants for the kerjasama-agent application."""

# Message categories
CATEGORY_GREETING = "GREETING"
CATEGORY_AVAILABILITY = "AVAILABILITY"
CATEGORY_PRICING = "PRICING"
CATEGORY_OTHER = "OTHER"

# List of trained categories (OTHER is inferred from low confidence)
TRAINED_CATEGORIES = [CATEGORY_GREETING, CATEGORY_AVAILABILITY, CATEGORY_PRICING]

# All possible categories
ALL_CATEGORIES = [CATEGORY_GREETING, CATEGORY_AVAILABILITY, CATEGORY_PRICING, CATEGORY_OTHER]

# Classification confidence threshold
# If highest confidence is below this, return CATEGORY_OTHER
CONFIDENCE_THRESHOLD = 0.955
