import React, { useEffect, useMemo, useRef, useState } from "react";

import {
  getActiveBatchRun,
  getBatchRuns,
  getResumes,
  runLocalBatch,
  searchJobs,
} from "./api";
import {
  clearPersistedSearchState,
  createEmptyJobSearchForm,
  createEmptySearchState,
  loadPersistedSearchState,
  savePersistedSearchState,
} from "./searchState";
import { parseCommaSeparatedSkills } from "./utils/skills";

const views = [
  ["search", "JD Search"],
  ["resumes", "Resume Status"],
  ["batch", "Batch Runs"],
];

export const ACTIVE_BATCH_POLL_MS = 4000;

export function App() {
  const [activeView, setActiveView] = useState("search");
  const [jobSearch, setJobSearch] = useState(() => loadPersistedSearchState());
  const [resumeRefreshKey, setResumeRefreshKey] = useState(0);

  useEffect(() => {
    savePersistedSearchState(jobSearch.form, jobSearch.searchState);
  }, [jobSearch]);

  function updateJobSearch(nextState) {
    setJobSearch((current) => ({
      ...current,
      ...nextState,
    }));
  }

  function clearJobSearch() {
    const nextState = {
      form: createEmptyJobSearchForm(),
      searchState: createEmptySearchState(),
    };
    clearPersistedSearchState();
    setJobSearch(nextState);
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Recruiter Workspace</p>
          <h1>Resume Search</h1>
        </div>
        <nav className="view-switch" aria-label="View">
          {views.map(([viewId, label]) => (
            <button
              className={activeView === viewId ? "active" : ""}
              key={viewId}
              type="button"
              onClick={() => setActiveView(viewId)}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      {activeView === "search" && (
        <JobSearchPage
          form={jobSearch.form}
          searchState={jobSearch.searchState}
          onClear={clearJobSearch}
          onChange={updateJobSearch}
        />
      )}
      {activeView === "resumes" && <ResumeStatusPage refreshKey={resumeRefreshKey} />}
      {activeView === "batch" && (
        <BatchRunsPage
          onBatchCompleted={() => setResumeRefreshKey((current) => current + 1)}
        />
      )}
    </main>
  );
}

export function JobSearchPage({ form, searchState, onChange, onClear }) {
  const payload = useMemo(
    () => ({
      job_title: form.jobTitle.trim(),
      job_description: form.jobDescription.trim(),
      required_skills: parseCommaSeparatedSkills(form.requiredSkills),
      nice_to_have_skills: parseCommaSeparatedSkills(form.niceToHaveSkills),
      min_years_experience: Number(form.minYearsExperience) || 0,
    }),
    [form],
  );

  function updateField(event) {
    const { name, value } = event.target;
    onChange({
      form: {
        ...form,
        [name]: value,
      },
    });
  }

  async function submitSearch(event) {
    event.preventDefault();
    onChange({
      searchState: {
        loading: true,
        error: "",
        response: null,
        hasSearched: true,
      },
    });

    try {
      const response = await searchJobs(payload);
      onChange({
        searchState: {
          loading: false,
          error: "",
          response,
          hasSearched: true,
        },
      });
    } catch (error) {
      onChange({
        searchState: {
          loading: false,
          error: error.message || "Search failed.",
          response: null,
          hasSearched: true,
        },
      });
    }
  }

  return (
    <section className="workspace-grid">
      <form className="search-panel" onSubmit={submitSearch}>
        <label>
          <span>Job Title</span>
          <input
            name="jobTitle"
            required
            value={form.jobTitle}
            onChange={updateField}
          />
        </label>

        <label>
          <span>Job Description</span>
          <textarea
            name="jobDescription"
            required
            rows="8"
            value={form.jobDescription}
            onChange={updateField}
          />
        </label>

        <label>
          <span>Required Skills</span>
          <input
            name="requiredSkills"
            value={form.requiredSkills}
            onChange={updateField}
          />
        </label>

        <label>
          <span>Nice-to-Have Skills</span>
          <input
            name="niceToHaveSkills"
            value={form.niceToHaveSkills}
            onChange={updateField}
          />
        </label>

        <label>
          <span>Minimum Years of Experience</span>
          <input
            min="0"
            name="minYearsExperience"
            step="0.5"
            type="number"
            value={form.minYearsExperience}
            onChange={updateField}
          />
        </label>

        <div className="form-actions">
          <button className="primary-button" disabled={searchState.loading} type="submit">
            {searchState.loading ? "Searching..." : "Search"}
          </button>
          <button className="secondary-button" type="button" onClick={onClear}>
            Clear
          </button>
        </div>
      </form>

      <SearchResults state={searchState} />
    </section>
  );
}

function SearchResults({ state }) {
  if (state.loading) {
    return <StatusPanel title="Loading" message="Search is running." />;
  }

  if (state.error) {
    return <StatusPanel title="Search failed" message={state.error} />;
  }

  if (!state.hasSearched) {
    return <StatusPanel title="Ready" message="Submit a job description to search parsed resumes." />;
  }

  if (!state.response || state.response.results.length === 0) {
    return <StatusPanel title="No results found" message="No parsed resumes matched this job search." />;
  }

  return (
    <section className="results-panel">
      <div className="summary-strip">
        <Metric label="Considered" value={state.response.total_candidates_considered} />
        <Metric label="Matched" value={state.response.matched_count} />
        <Metric label="Title Excluded" value={state.response.excluded_by_title_count} />
        <Metric
          label="Experience Excluded"
          value={state.response.excluded_by_experience_count}
        />
      </div>

      <div className="result-list">
        {state.response.results.map((result) => (
          <CandidateResult key={result.resume_id} result={result} />
        ))}
      </div>
    </section>
  );
}

function CandidateResult({ result }) {
  return (
    <article className="candidate-card">
      <div className="candidate-header">
        <div>
          <h2>{result.candidate_name || "Unnamed Candidate"}</h2>
          <p>{result.current_title || "Title unavailable"}</p>
        </div>
        <div className="score-pill">{formatScore(result.overall_score)}</div>
      </div>

      <dl className="details-grid">
        <Detail label="Email" value={result.email || "Not available"} />
        <Detail label="Phone" value={result.phone || "Not available"} />
        <Detail
          label="Experience"
          value={
            result.total_experience_years === null
              ? "Unknown"
              : `${result.total_experience_years} years`
          }
        />
        <Detail label="Resume" value={result.file_name} />
      </dl>

      <div className="score-grid">
        <Metric label="Title" value={formatScore(result.title_score)} />
        <Metric label="Required Skills" value={formatScore(result.required_skill_score)} />
        <Metric label="Nice-to-Have" value={formatScore(result.nice_to_have_skill_score)} />
      </div>

      <SkillGroup label="Matched Required" skills={result.matched_required_skills} />
      <SkillGroup label="Missing Required" skills={result.missing_required_skills} muted />
      <SkillGroup label="Matched Nice-to-Have" skills={result.matched_nice_to_have_skills} />

      <p className="match-reason">{result.match_reason}</p>
      <p className="source-path">{result.source_path || "No source path"}</p>
    </article>
  );
}

function ResumeStatusPage({ refreshKey }) {
  const [state, setState] = useState({ loading: true, error: "", resumes: [] });

  useEffect(() => {
    let isMounted = true;
    getResumes()
      .then((resumes) => {
        if (isMounted) {
          setState({ loading: false, error: "", resumes });
        }
      })
      .catch((error) => {
        if (isMounted) {
          setState({
            loading: false,
            error: error.message || "Backend unavailable.",
            resumes: [],
          });
        }
      });

    return () => {
      isMounted = false;
    };
  }, [refreshKey]);

  if (state.loading) {
    return <StatusPanel title="Loading" message="Loading resume status." />;
  }

  if (state.error) {
    return <StatusPanel title="Backend unavailable" message={state.error} />;
  }

  if (state.resumes.length === 0) {
    return <StatusPanel title="No resumes found" message="Run batch ingestion before searching." />;
  }

  return <ResumeStatusTable resumes={state.resumes} />;
}

function BatchRunsPage({ onBatchCompleted }) {
  const [force, setForce] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [latestBatchRun, setLatestBatchRun] = useState(null);
  const isRunningBatchRef = useRef(false);
  const [state, setState] = useState({
    loading: true,
    running: false,
    activeBatch: { is_running: false },
    error: "",
    runs: [],
  });

  async function loadActiveStatus() {
    const activeBatch = await getActiveBatchRun();
    setState((current) => ({ ...current, activeBatch }));
    return activeBatch;
  }

  async function loadRuns() {
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await getBatchRuns();
      setState((current) => ({
        ...current,
        loading: false,
        error: "",
        runs: response.runs || [],
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error.message || "Unable to load batch runs.",
      }));
    }
  }

  async function refreshBatchPage() {
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const [activeBatch, batchRuns] = await Promise.all([
        getActiveBatchRun(),
        getBatchRuns(),
      ]);
      setState((current) => ({
        ...current,
        loading: false,
        error: "",
        activeBatch,
        runs: batchRuns.runs || [],
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error.message || "Unable to load batch status.",
      }));
    }
  }

  useEffect(() => {
    refreshBatchPage();
  }, []);

  useEffect(() => {
    if (!shouldPollActiveBatch(state.activeBatch, state.running)) {
      return undefined;
    }

    const intervalId = window.setInterval(async () => {
      try {
        const activeBatch = await getActiveBatchRun();
        setState((current) => ({ ...current, activeBatch }));
        if (!activeBatch.is_running) {
          const response = await getBatchRuns();
          setState((current) => ({
            ...current,
            activeBatch,
            runs: response.runs || [],
          }));
          setLatestBatchRun(response.runs?.[0] || null);
          setStatusMessage({
            tone: "success",
            text: "Batch completed successfully.",
          });
          onBatchCompleted?.();
        }
      } catch (error) {
        setState((current) => ({
          ...current,
          error: error.message || "Unable to refresh active batch status.",
        }));
      }
    }, ACTIVE_BATCH_POLL_MS);

    return () => window.clearInterval(intervalId);
  }, [state.activeBatch.is_running, state.running, onBatchCompleted]);

  async function triggerBatch() {
    if (!canStartBatch(isRunningBatchRef.current, state.activeBatch)) {
      setStatusMessage({
        tone: "warning",
        text: "A batch is already running. Please wait for it to finish.",
      });
      return;
    }

    isRunningBatchRef.current = true;
    setStatusMessage(null);
    setLatestBatchRun(null);
    setState((current) => ({ ...current, running: true, error: "" }));
    try {
      const batchRun = await runLocalBatch({ force });
      setLatestBatchRun(batchRun);
      setStatusMessage({
        tone: "success",
        text: "Batch completed successfully.",
      });
      await loadRuns();
      onBatchCompleted?.();
    } catch (error) {
      setStatusMessage({
        tone: "error",
        text: "Batch failed. Please check backend logs or try again.",
      });
      setState((current) => ({
        ...current,
        error: error.message || "Batch run failed.",
      }));
    } finally {
      isRunningBatchRef.current = false;
      setState((current) => ({
        ...current,
        running: false,
        activeBatch: { is_running: false },
      }));
      loadActiveStatus().catch(() => undefined);
    }
  }

  const activeBatchIsRunning = state.running || state.activeBatch?.is_running;

  return (
    <section className="batch-page">
      <BatchRunControls
        force={force}
        activeBatch={state.activeBatch}
        isRunning={activeBatchIsRunning}
        onForceChange={setForce}
        onRun={triggerBatch}
      />

      {statusMessage && (
        <p className={`${statusMessage.tone}-message`}>{statusMessage.text}</p>
      )}
      {latestBatchRun && <BatchSummaryPanel batchRun={latestBatchRun} />}
      {state.error && <StatusPanel title="Batch error" message={state.error} />}
      {state.loading && <StatusPanel title="Loading" message="Loading batch runs." />}
      {!state.loading && !state.error && state.runs.length === 0 && (
        <StatusPanel title="No batch runs" message="Run local batch to process resumes." />
      )}
      {!state.loading && !state.error && state.runs.length > 0 && (
        <BatchRunsTable runs={state.runs} />
      )}
    </section>
  );
}

export function canStartBatch(isRunningBatch, activeBatch = { is_running: false }) {
  return !isRunningBatch && !activeBatch?.is_running;
}

export function shouldPollActiveBatch(activeBatch, isRunningBatch = false) {
  return Boolean(activeBatch?.is_running || isRunningBatch);
}

export function BatchRunControls({
  force,
  isRunning,
  activeBatch = { is_running: false },
  onForceChange,
  onRun,
}) {
  return (
    <div className="batch-toolbar">
      <button
        className="primary-button batch-run-button"
        disabled={isRunning}
        type="button"
        onClick={onRun}
      >
        {isRunning && <span className="spinner" aria-hidden="true" />}
        {isRunning ? "Processing..." : "Run Local Batch"}
      </button>
      <label className="checkbox-label">
        <input
          checked={force}
          disabled={isRunning}
          type="checkbox"
          onChange={(event) => onForceChange(event.target.checked)}
        />
        <span>Force reprocess unchanged files</span>
      </label>
      <p className="batch-note">
        Manual batch processing may take longer when many resumes need Ollama parsing.
      </p>
      {isRunning && (
        <div className="batch-processing-message" role="status">
          <strong>Processing resumes. This may take a while because resumes are being extracted and parsed.</strong>
          <span>Batch processing is running. Please do not refresh or click again.</span>
          {activeBatch?.batch_id && (
            <span>Active batch: {activeBatch.batch_id}</span>
          )}
          {activeBatch?.started_at && (
            <span>Started: {formatDateTime(activeBatch.started_at)}</span>
          )}
        </div>
      )}
    </div>
  );
}

export function BatchSummaryPanel({ batchRun }) {
  return (
    <section className="batch-summary-panel">
      <h2>Latest Batch Summary</h2>
      <div className="summary-strip">
        <Metric label="Total Files" value={batchRun.total_files_seen} />
        <Metric label="Ingested" value={batchRun.ingested_count} />
        <Metric label="Updated" value={batchRun.updated_count} />
        <Metric label="Skipped" value={batchRun.skipped_count} />
        <Metric label="Failed" value={batchRun.failed_count} />
        <Metric label="Parsed" value={batchRun.parsed_count} />
        <Metric label="Fallback" value={batchRun.fallback_count} />
      </div>
    </section>
  );
}

export function ResumeStatusTable({ resumes }) {
  return (
    <section className="resume-table-wrap">
      <table className="resume-table">
        <thead>
          <tr>
            <th>Candidate</th>
            <th>File</th>
            <th>Title</th>
            <th>Contact</th>
            <th>Experience</th>
            <th>Skills</th>
            <th>Extraction</th>
            <th>Parsing</th>
            <th>Parser</th>
            <th>Parsed At</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {resumes.map((resume) => (
            <tr key={resume.resume_id}>
              <td>{resume.candidate_name || "Unnamed"}</td>
              <td>{resume.file_name}</td>
              <td>{resume.current_title || "Unknown"}</td>
              <td>
                <div>{resume.email || "No email"}</div>
                <div>{resume.phone || "No phone"}</div>
              </td>
              <td>{formatYears(resume.total_experience_years)}</td>
              <td>{resume.skills?.join(", ") || "None"}</td>
              <td>
                <StatusBadge status={resume.extraction_status} />
              </td>
              <td>
                <StatusBadge status={resume.parsing_status} />
                {resume.parsing_error && (
                  <p className="table-error">{resume.parsing_error}</p>
                )}
              </td>
              <td>
                <span className="parser-pill">{resume.parser_used || "Unknown"}</span>
              </td>
              <td>{formatDateTime(resume.parsed_at)}</td>
              <td className="source-cell">{resume.source_path || "No source path"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function BatchRunsTable({ runs }) {
  return (
    <section className="resume-table-wrap">
      <table className="resume-table batch-table">
        <thead>
          <tr>
            <th>Batch ID</th>
            <th>Status</th>
            <th>Started</th>
            <th>Finished</th>
            <th>Total</th>
            <th>Ingested</th>
            <th>Updated</th>
            <th>Skipped</th>
            <th>Failed</th>
            <th>Parsed</th>
            <th>Fallback</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.batch_id}>
              <td className="source-cell">{run.batch_id}</td>
              <td>
                <StatusBadge status={run.status} />
              </td>
              <td>{formatDateTime(run.started_at)}</td>
              <td>{formatDateTime(run.finished_at)}</td>
              <td>{run.total_files_seen}</td>
              <td>{run.ingested_count}</td>
              <td>{run.updated_count}</td>
              <td>{run.skipped_count}</td>
              <td>{run.failed_count}</td>
              <td>{run.parsed_count}</td>
              <td>{run.fallback_count}</td>
              <td>{run.error_message || "None"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function StatusBadge({ status }) {
  const safeStatus = status || "unknown";
  return <span className={`status-badge ${statusTone(safeStatus)}`}>{safeStatus}</span>;
}

function StatusPanel({ title, message }) {
  return (
    <section className="status-panel">
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function SkillGroup({ label, skills, muted = false }) {
  return (
    <div className="skill-row">
      <span>{label}</span>
      <div>
        {skills.length === 0 ? (
          <em>None</em>
        ) : (
          skills.map((skill) => (
            <span className={muted ? "skill muted" : "skill"} key={skill}>
              {skill}
            </span>
          ))
        )}
      </div>
    </div>
  );
}

function formatScore(score) {
  return `${Math.round(Number(score || 0) * 100)}%`;
}

function formatYears(years) {
  return years === null || years === undefined ? "Unknown" : `${years} years`;
}

function formatDateTime(value) {
  if (!value) {
    return "Not available";
  }
  return new Date(value).toLocaleString();
}

function statusTone(status) {
  if (["parsed", "completed", "extracted", "ollama"].includes(status)) {
    return "good";
  }
  if (["review_required", "running", "rule_based"].includes(status)) {
    return "warning";
  }
  if (["failed"].includes(status)) {
    return "error";
  }
  return "neutral";
}
