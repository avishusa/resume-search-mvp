import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";

import { listResumes, searchJobs } from "./api";
import "./styles.css";
import { parseCommaSeparatedSkills } from "./utils/skills";

const initialForm = {
  jobTitle: "AI Engineer",
  jobDescription:
    "Looking for an AI Engineer with Python, LLM, LangChain and FastAPI experience.",
  requiredSkills: "Python, LLM, LangChain",
  niceToHaveSkills: "FastAPI, Docker",
  minYearsExperience: "0",
};

function App() {
  const [activeView, setActiveView] = useState("search");

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Recruiter Workspace</p>
          <h1>Resume Search</h1>
        </div>
        <div className="view-switch" aria-label="View">
          <button
            className={activeView === "search" ? "active" : ""}
            type="button"
            onClick={() => setActiveView("search")}
          >
            JD Search
          </button>
          <button
            className={activeView === "resumes" ? "active" : ""}
            type="button"
            onClick={() => setActiveView("resumes")}
          >
            Resume Status
          </button>
        </div>
      </header>

      {activeView === "search" ? <JobSearchPage /> : <ResumeStatusPage />}
    </main>
  );
}

function JobSearchPage() {
  const [form, setForm] = useState(initialForm);
  const [searchState, setSearchState] = useState({
    loading: false,
    error: "",
    response: null,
    hasSearched: false,
  });

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
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function submitSearch(event) {
    event.preventDefault();
    setSearchState({
      loading: true,
      error: "",
      response: null,
      hasSearched: true,
    });

    try {
      const response = await searchJobs(payload);
      setSearchState({
        loading: false,
        error: "",
        response,
        hasSearched: true,
      });
    } catch (error) {
      setSearchState({
        loading: false,
        error: error.message || "Search failed.",
        response: null,
        hasSearched: true,
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

        <button className="primary-button" disabled={searchState.loading} type="submit">
          {searchState.loading ? "Searching..." : "Search"}
        </button>
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

function ResumeStatusPage() {
  const [state, setState] = useState({ loading: true, error: "", resumes: [] });

  useEffect(() => {
    let isMounted = true;
    listResumes()
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
  }, []);

  if (state.loading) {
    return <StatusPanel title="Loading" message="Loading resume status." />;
  }

  if (state.error) {
    return <StatusPanel title="Backend unavailable" message={state.error} />;
  }

  if (state.resumes.length === 0) {
    return <StatusPanel title="No resumes found" message="Run batch ingestion before searching." />;
  }

  return (
    <section className="resume-table-wrap">
      <table className="resume-table">
        <thead>
          <tr>
            <th>Candidate</th>
            <th>Title</th>
            <th>Parsing</th>
            <th>Parser</th>
            <th>Experience</th>
            <th>Skills</th>
            <th>File</th>
          </tr>
        </thead>
        <tbody>
          {state.resumes.map((resume) => (
            <tr key={resume.resume_id}>
              <td>{resume.candidate_name || "Unnamed"}</td>
              <td>{resume.current_title || "Unknown"}</td>
              <td>{resume.parsing_status || "Unknown"}</td>
              <td>{resume.parser_used || "Unknown"}</td>
              <td>
                {resume.total_experience_years === null
                  ? "Unknown"
                  : `${resume.total_experience_years} years`}
              </td>
              <td>{resume.skills.join(", ") || "None"}</td>
              <td>{resume.file_name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
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

createRoot(document.getElementById("root")).render(<App />);
