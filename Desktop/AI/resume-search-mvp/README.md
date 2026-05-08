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

Upload a TXT resume:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/resumes/upload" -F "file=@C:\path\to\resume.txt;type=text/plain"
```

## Local Drive Simulator

For now, resumes should be placed in:

```text
data/drive_resumes/
```

Supported files are PDF, DOCX, and TXT. TXT extraction is implemented; PDF and DOCX are placeholders for now.

Trigger local Drive ingestion:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/resumes/ingest-local-drive"
```

This endpoint uses the same batch-processing flow intended for a future nightly job. It scans the folder, skips unchanged files by file hash, reprocesses changed files, extracts text, parses candidate profiles, and stores results in SQLite.

You can also trigger the same batch process through the batch endpoint:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/batch/run-local-drive"
```

View recent batch runs:

```powershell
curl.exe "http://127.0.0.1:8000/batch/runs"
```

List ingested resumes:

```powershell
curl.exe "http://127.0.0.1:8000/resumes"
```

Search ingested resumes with a job description:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/jobs/search" -H "Content-Type: application/json" -d "{\"job_title\":\"AI Engineer\",\"job_description\":\"Build AI systems\",\"required_skills\":[\"Python\"],\"nice_to_have_skills\":[\"FastAPI\"]}"
```

## Candidate Profile Parsing

Resume ingestion parses extracted text into a structured candidate profile. The default parser uses local Ollama and falls back to rule-based parsing if Ollama fails, times out, returns invalid JSON, or returns invalid profile data.

Default configuration:

```text
RESUME_PARSER_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT_SECONDS=60
OLLAMA_MAX_RESUME_CHARS=12000
DATABASE_URL=sqlite:///./data/resume_search.db
ENABLE_NIGHTLY_BATCH=false
NIGHTLY_BATCH_HOUR=2
NIGHTLY_BATCH_MINUTE=0
LOCAL_DRIVE_RESUME_DIR=data/drive_resumes
```

The SQLite database tables are created automatically when the API starts. The database file lives under `data/` and is ignored by git.

Nightly batch scheduling is currently a foundation hook only. `ENABLE_NIGHTLY_BATCH` is disabled by default, and Google Drive integration is not implemented yet. `data/drive_resumes/` remains the local Drive simulator for this MVP step.

To use the fallback parser as the primary parser during development:

```powershell
$env:RESUME_PARSER_PROVIDER="rule_based"
```

## Tests

Run the test suite:

```powershell
pytest
```
