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

5. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

## API Endpoints

- `GET /` - Health check endpoint

## Running Tests

### Install Test Dependencies

Test dependencies are included in the main requirements.txt. For additional development tools:

```bash
pip3 install -r requirements-dev.txt
```

### Run Tests

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

## License

MIT
