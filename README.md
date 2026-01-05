# Kerjasama Agent

WhatsApp AI agent that responds to availability and pricing inquiries.

## Tech Stack

- **FastAPI** - Web framework for building APIs
- **SetFit** - Few-shot text classification
- **Google ADK** - AI Development Kit for agent capabilities
- **PostgreSQL** - Database for persistent storage

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL database

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd kerjasama-agent
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Train the classifier (required before first run):
   ```bash
   python train_classifier.py
   ```

6. Run the application:
   ```bash
   uvicorn main:app --reload --log-level debug
   ```

   ```bash
   ngrok http 8000
   ```

## API Endpoints

- `GET /` - Health check endpoint

## Classifier Training

The message classifier uses a pre-trained SetFit model. The model must be trained before running the service.

### Train the model (required before first run):
```bash
python train_classifier.py
```
This saves the trained model to `whatsapp_intent_model/`.

### Commit the model for deployment:
```bash
git add whatsapp_intent_model/
git commit -m "Add trained classifier model"
```

### When to re-train:
- After updating TRAINING_EXAMPLES in classifier.py
- After changing the model backbone

Note: Training takes ~4 minutes. The model is committed to the repo so deployment is fast.

## Running Tests

### Install Test Dependencies

Test dependencies are included in the main requirements.txt. For additional development tools:

```bash
pip3 install -r requirements-dev.txt
```

### Run Tests

```bash
  pip install -r requirements-dev.txt
```

Run all tests:
```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_classifier.py
```

Run specific test:
```bash
pytest tests/test_classifier.py::test_classifier_initialization
```

Run with verbose output:
```bash
pytest -v
```

Run with coverage report:
```bash
pytest --cov=. --cov-report=html
```

This generates an HTML report in `htmlcov/` directory. Open `htmlcov/index.html` in a browser to view.

### Watch Mode (Optional)

For continuous testing during development:

```bash
pip install pytest-watch
ptw
```

This automatically re-runs tests when files change.

### Interpreting Results

```
========================= test session starts ==========================
collected 9 items

tests/test_classifier.py ........                                 [100%]
tests/test_main.py ..                                             [100%]

========================== 9 passed in 2.34s ===========================
```

- `.` = passed test
- `F` = failed test
- `E` = error during test
- `s` = skipped test

For failed tests, pytest shows the assertion that failed and a traceback.

## Deployment

### Prerequisites
- gcloud CLI installed and authenticated
- Secrets configured in GCP Secret Manager
- Classifier model trained: `python train_classifier.py`
- All tests passing: `pytest tests/ -v`

### Deploy to Cloud Run
```bash
./deploy.sh
```

The script will:
1. Run all tests locally (aborts if any fail)
2. Deploy to Cloud Run with the pre-trained model

### Required Secrets (already configured):
- whatsapp-verify-token
- whatsapp-app-secret
- database-url
- google-adk-api-key
- encryption-key

## License

MIT