# Resume Search MVP

FastAPI backend skeleton for a resume search MVP. This first step includes only the application structure, configuration, a health check endpoint, and tests.

## Requirements

- Python 3.11+
- pip

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies and the local app package:

```powershell
pip install -r requirements.txt
pip install -e .
```

Run the API locally:

```powershell
uvicorn app.main:app --reload
```

Open the health check:

```text
GET http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "resume-search-api"
}
```

## Tests

Run the test suite:

```powershell
pytest
```
