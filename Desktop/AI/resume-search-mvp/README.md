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

Supported files are PDF, DOCX, and TXT. Text extraction is implemented for all three file types.

Trigger local Drive ingestion:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/resumes/ingest-local-drive"
```

This endpoint uses the same batch-processing flow intended for a future nightly job. It scans the folder, skips unchanged files by file hash, reprocesses changed files, extracts text, parses candidate profiles, and stores results in SQLite.

You can also trigger the same local batch process through the batch endpoint:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/batch/run-local-drive"
```

To run the batch process with whichever storage providers are configured:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/batch/run"
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

For faster local parsing, the Ollama provider sends a compact resume digest by default instead of blindly sending the full extracted text. The digest keeps the top resume area plus detected Skills, Experience, Education, and Certification sections, then caps the input with `OLLAMA_MAX_RESUME_CHARS`. Batch parsing is sequential by default with `RESUME_PARSE_CONCURRENCY=1`; increase it carefully if your local Ollama setup can handle more simultaneous requests.

Default configuration:

```text
RESUME_PARSER_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT_SECONDS=60
OLLAMA_MAX_RESUME_CHARS=6000
OLLAMA_USE_RESUME_DIGEST=true
OLLAMA_TEMPERATURE=0
OLLAMA_NUM_PREDICT=600
OLLAMA_NUM_CTX=
RESUME_PARSE_CONCURRENCY=1
DATABASE_URL=sqlite:///./data/resume_search.db
ENABLE_NIGHTLY_BATCH=false
NIGHTLY_BATCH_HOUR=2
NIGHTLY_BATCH_MINUTE=0
RESUME_STORAGE_PROVIDERS=local
RESUME_STORAGE_PROVIDER=local
LOCAL_DRIVE_RESUME_DIR=data/drive_resumes
LOCAL_DRIVE_RECURSIVE=true
GOOGLE_DRIVE_FOLDER_ID=
GOOGLE_SERVICE_ACCOUNT_FILE=
GOOGLE_DRIVE_ALLOWED_MIME_TYPES=application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain
GOOGLE_DRIVE_RECURSIVE=true
GOOGLE_DRIVE_MAX_DEPTH=10
GOOGLE_DRIVE_MAX_FILES=1000
```

The SQLite database tables are created automatically when the API starts. The database file lives under `data/` and is ignored by git.

Nightly batch scheduling is currently a foundation hook only. `ENABLE_NIGHTLY_BATCH` is disabled by default. `data/drive_resumes/` remains the local Drive simulator for this MVP step.

## Storage Providers

Resume batch processing reads files through storage provider interfaces. The default provider list is `local`, which scans the local simulator folder:

```text
data/drive_resumes/
```

Configure it with:

```text
RESUME_STORAGE_PROVIDERS=local
RESUME_STORAGE_PROVIDER=local
LOCAL_DRIVE_RESUME_DIR=data/drive_resumes
LOCAL_DRIVE_RECURSIVE=true
```

`LOCAL_DRIVE_RECURSIVE=true` means the simulator scans nested folders too, for example `data/drive_resumes/Data Science/2024/resume.pdf`. Set it to `false` to scan only files directly inside `data/drive_resumes/`.

`RESUME_STORAGE_PROVIDER` is still supported for backward compatibility. When `RESUME_STORAGE_PROVIDERS` is set, it takes priority and can include more than one provider:

```text
RESUME_STORAGE_PROVIDERS=local,google_drive
```

`POST /batch/run` scans every configured provider. `POST /batch/run-local-drive` always scans only the local simulator provider, which is useful for local testing. Batch responses include per-provider counts so you can see how many files came from `local` versus `google_drive`.

A `GoogleDriveResumeStorageProvider` authenticates with a service account, lists supported resume files from a configured folder, downloads bytes, and provides metadata through the shared storage interface. Duplicate detection uses `provider_name + source_id`, so Google Drive records are identified by the Drive file ID rather than the file name.

### Google Drive Setup

Google Drive support is available behind the same storage provider interface, but local remains the default for development.

To scan both local and Google Drive during a batch run, set:

```text
RESUME_STORAGE_PROVIDERS=local,google_drive
GOOGLE_DRIVE_FOLDER_ID=your-google-drive-folder-id
GOOGLE_SERVICE_ACCOUNT_FILE=C:\path\to\service-account.json
GOOGLE_DRIVE_RECURSIVE=true
GOOGLE_DRIVE_MAX_DEPTH=10
GOOGLE_DRIVE_MAX_FILES=1000
```

The Google provider uses a service account with read-only Drive access. Share the target Drive folder with the service account email, then run:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/batch/run"
```

To scan only Google Drive, set `RESUME_STORAGE_PROVIDERS=google_drive`. Service account JSON files should never be committed; `.gitignore` excludes common service-account filename patterns.

When `GOOGLE_DRIVE_RECURSIVE=true`, the provider scans nested Google Drive folders under `GOOGLE_DRIVE_FOLDER_ID`, ignores unsupported files, and preserves a readable folder path such as `drive://Recruiting Resumes/Data Science/2024/Jillani Resume.pdf`. `GOOGLE_DRIVE_MAX_DEPTH` and `GOOGLE_DRIVE_MAX_FILES` protect local batch runs from accidentally traversing an unexpectedly large Drive tree. Supported resume MIME types are PDF, DOCX, and TXT by default.

Check provider configuration safely:

```powershell
curl.exe "http://127.0.0.1:8000/debug/storage-provider"
```

To use the fallback parser as the primary parser during development:

```powershell
$env:RESUME_PARSER_PROVIDER="rule_based"
```

## Frontend

The recruiter/admin frontend lives in:

```text
frontend/
```

It provides:

- JD Search for matching already-parsed resumes
- Resume Status for checking parsed candidate profiles
- Batch Runs for manually triggering local batch processing and reviewing recent runs

It does not include resume upload because resumes are processed through the batch/storage provider flow.

Install frontend dependencies:

```powershell
cd frontend
npm install
```

Create local frontend config:

```powershell
Copy-Item .env.example .env
```

Default frontend API config:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Run the backend from the project root:

```powershell
uvicorn app.main:app --reload
```

Run the frontend from `frontend/`:

```powershell
npm run dev
```

Open:

```text
http://localhost:5173
```

From the UI:

- Use `Batch Runs` -> `Run Local Batch` to process files in `data/drive_resumes/`.
- Check `Force reprocess unchanged files` when you want to re-extract and re-parse existing files.
- Use `Resume Status` to confirm `extraction_status`, `parsing_status`, `parser_used`, and parsed candidate fields.
- Use `JD Search` to submit job requirements and view ranked matches.

Run frontend tests:

```powershell
npm test
```

## Tests

Run the test suite:

```powershell
pytest
```
