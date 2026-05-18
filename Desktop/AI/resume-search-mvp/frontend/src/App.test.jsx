import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  BatchRunControls,
  BatchRunsTable,
  BatchSummaryPanel,
  CandidateResult,
  JobSearchPage,
  ResumeStatusTable,
  SearchResults,
  canStartBatch,
  filterSearchResults,
  getResultFilterCounts,
  shouldPollActiveBatch,
} from "./App";

const searchResult = {
  resume_id: "resume-1",
  file_name: "Bhavesh_Wadhwani_Resume.pdf",
  source_path: "data/drive_resumes/Bhavesh_Wadhwani_Resume.pdf",
  candidate_name: "Bhavesh Wadhwani",
  email: "bhavesh@example.com",
  phone: "+1 312-555-1212",
  current_title: "Data Scientist",
  skills: ["Python", "SQL"],
  total_experience_years: 4.5,
  title_score: 0.9,
  required_skill_score: 0.67,
  nice_to_have_skill_score: 0.5,
  experience_score: 1,
  overall_score: 0.78,
  shortlist_decision: "shortlist",
  recommendation_level: "strong_match",
  match_summary: "Strong match: title, experience, and skills align.",
  matched_required_skills: ["Python", "SQL"],
  missing_required_skills: ["Machine Learning"],
  matched_nice_to_have_skills: ["Docker"],
  missing_nice_to_have_skills: ["GCP"],
  required_skill_match_percentage: 66.7,
  nice_to_have_skill_match_percentage: 50,
  title_match_type: "alias",
  title_match_reason: "Titles are in the same controlled alias group.",
  experience_match_reason: "Experience requirement met: 4.5 years >= 3 years.",
  required_skill_match_reason:
    "Matched 2/3 required skills: Python, SQL. Missing required skills: Machine Learning.",
  nice_to_have_skill_match_reason:
    "Matched 1/2 optional nice-to-have skills: Docker. Missing optional nice-to-have skills: GCP.",
  match_reason: "Strong match: title, experience, and skills align.",
};

describe("ResumeStatusTable", () => {
  it("renders parsed resume data", () => {
    const html = renderToStaticMarkup(
      <ResumeStatusTable
        resumes={[
          {
            resume_id: "resume-1",
            candidate_name: "Bhavesh Wadhwani",
            file_name: "Bhavesh_Wadhwani_Resume.pdf",
            current_title: "Data Scientist",
            email: "bhavesh@example.com",
            phone: "+1 312-555-1212",
            total_experience_years: 4.5,
            skills: ["Python", "GCP"],
            extraction_status: "extracted",
            parsing_status: "parsed",
            parser_used: "ollama",
            parsing_error: null,
            parsed_at: "2026-05-08T20:00:00Z",
            source_path: "data/drive_resumes/Bhavesh_Wadhwani_Resume.pdf",
          },
        ]}
      />,
    );

    expect(html).toContain("Bhavesh Wadhwani");
    expect(html).toContain("Data Scientist");
    expect(html).toContain("ollama");
    expect(html).toContain("parsed");
    expect(html).toContain("Python, GCP");
  });
});

describe("BatchRunsTable", () => {
  it("renders batch summary counts", () => {
    const html = renderToStaticMarkup(
      <BatchRunsTable
        runs={[
          {
            batch_id: "batch-1",
            started_at: "2026-05-08T20:00:00Z",
            finished_at: "2026-05-08T20:01:00Z",
            status: "completed",
            total_files_seen: 2,
            ingested_count: 1,
            updated_count: 1,
            skipped_count: 0,
            failed_count: 0,
            parsed_count: 2,
            fallback_count: 0,
            error_message: null,
          },
        ]}
      />,
    );

    expect(html).toContain("batch-1");
    expect(html).toContain("completed");
    expect(html).toContain("<td>2</td>");
    expect(html).toContain("<td>1</td>");
    expect(html).toContain("None");
  });
});

describe("BatchRunControls", () => {
  it("disables controls and shows loading message while batch is running", () => {
    const html = renderToStaticMarkup(
      <BatchRunControls
        force
        isRunning
        onForceChange={() => {}}
        onRun={() => {}}
      />,
    );

    expect(html).toContain("Processing...");
    expect(html).toContain("disabled");
    expect(html).toContain(
      "Processing resumes. This may take a while because resumes are being extracted and parsed.",
    );
    expect(html).toContain(
      "Batch processing is running. Please do not refresh or click again.",
    );
  });

  it("shows active backend batch details while running", () => {
    const html = renderToStaticMarkup(
      <BatchRunControls
        activeBatch={{
          is_running: true,
          batch_id: "batch-active",
          started_at: "2026-05-08T20:00:00Z",
        }}
        force={false}
        isRunning
        onForceChange={() => {}}
        onRun={() => {}}
      />,
    );

    expect(html).toContain("Active batch: batch-active");
    expect(html).toContain("Started:");
  });

  it("guards against duplicate batch starts", () => {
    expect(canStartBatch(false, { is_running: false })).toBe(true);
    expect(canStartBatch(true, { is_running: false })).toBe(false);
    expect(canStartBatch(false, { is_running: true })).toBe(false);
  });

  it("polls while a batch is active or a request is running", () => {
    expect(shouldPollActiveBatch({ is_running: true }, false)).toBe(true);
    expect(shouldPollActiveBatch({ is_running: false }, true)).toBe(true);
    expect(shouldPollActiveBatch({ is_running: false }, false)).toBe(false);
  });
});

describe("BatchSummaryPanel", () => {
  it("renders latest batch summary after completion", () => {
    const html = renderToStaticMarkup(
      <BatchSummaryPanel
        batchRun={{
          total_files_seen: 7,
          ingested_count: 2,
          updated_count: 1,
          skipped_count: 3,
          failed_count: 0,
          parsed_count: 3,
          fallback_count: 1,
          providers: [
            {
              provider_name: "local",
              total_files_seen: 4,
              ingested_count: 1,
              updated_count: 0,
              skipped_count: 3,
              failed_count: 0,
            },
            {
              provider_name: "google_drive",
              total_files_seen: 3,
              ingested_count: 1,
              updated_count: 1,
              skipped_count: 1,
              failed_count: 0,
            },
          ],
        }}
      />,
    );

    expect(html).toContain("Latest Batch Summary");
    expect(html).toContain("Total Files");
    expect(html).toContain("<strong>7</strong>");
    expect(html).toContain("Fallback");
    expect(html).toContain("<strong>1</strong>");
    expect(html).toContain("local");
    expect(html).toContain("google_drive");
    expect(html).toContain("4 files");
  });
});

describe("JobSearchPage", () => {
  it("renders an empty search form without hardcoded AI Engineer defaults", () => {
    const html = renderToStaticMarkup(
      <JobSearchPage
        form={{
          jobTitle: "",
          jobDescription: "",
          requiredSkills: "",
          niceToHaveSkills: "",
          minYearsExperience: "0",
        }}
        searchState={{
          loading: false,
          error: "",
          response: null,
          hasSearched: false,
        }}
        onChange={() => {}}
        onClear={() => {}}
      />,
    );

    expect(html).not.toContain("AI Engineer");
    expect(html).toContain("Clear");
  });
});

describe("CandidateResult", () => {
  it("renders shortlist badge and missing skills", () => {
    const html = renderToStaticMarkup(<CandidateResult result={searchResult} />);

    expect(html).toContain("Shortlist");
    expect(html).toContain("Strong Match");
    expect(html).toContain("Alias title match");
    expect(html).toContain("66.7%");
    expect(html).toContain("Machine Learning");
    expect(html).toContain("GCP");
    expect(html).toContain("Optional Gaps");
    expect(html).toContain("skill optional");
    expect(html).toContain("Strong match: title, experience, and skills align.");
  });

  it("renders title family matches with recruiter-friendly wording", () => {
    const html = renderToStaticMarkup(
      <CandidateResult
        result={{
          ...searchResult,
          title_match_type: "title_family",
          title_match_reason:
            "Title matched by title family: Machine Learning Engineer and Data Scientist are both in ML/Data Science.",
        }}
      />,
    );

    expect(html).toContain("Related title family match");
    expect(html).toContain("ML/Data Science");
  });

  it("keeps shortlisted candidates visible when only nice-to-have skills are missing", () => {
    const html = renderToStaticMarkup(
      <SearchResults
        state={{
          loading: false,
          error: "",
          hasSearched: true,
          response: {
            total_candidates_considered: 1,
            matched_count: 1,
            excluded_by_title_count: 0,
            excluded_by_experience_count: 0,
            results: [
              {
                ...searchResult,
                resume_id: "resume-shortlisted-with-optional-gaps",
                shortlist_decision: "shortlist",
                recommendation_level: "strong_match",
                matched_required_skills: ["Python", "SQL", "Machine Learning"],
                missing_required_skills: [],
                matched_nice_to_have_skills: [],
                missing_nice_to_have_skills: ["GCP", "Docker", "FastAPI"],
              },
            ],
          },
        }}
      />,
    );

    expect(html).toContain("Shortlisted (1)");
    expect(html).toContain("Optional Gaps");
    expect(html).toContain("GCP");
    expect(html).toContain("Docker");
    expect(html).toContain("FastAPI");
  });
});

describe("filterSearchResults", () => {
  it("filters by recommendation decision and sorts by overall score descending", () => {
    const weakResult = {
      ...searchResult,
      resume_id: "resume-2",
      overall_score: 0.95,
      shortlist_decision: "not_recommended",
    };
    const shortlistedResult = {
      ...searchResult,
      resume_id: "resume-3",
      overall_score: 0.75,
      shortlist_decision: "shortlist",
    };

    expect(filterSearchResults([weakResult, shortlistedResult], "shortlist")).toEqual([
      shortlistedResult,
    ]);
    expect(filterSearchResults([shortlistedResult, weakResult], "all")).toEqual([
      weakResult,
      shortlistedResult,
    ]);
    expect(filterSearchResults([shortlistedResult, weakResult], "not_recommended")).toEqual([
      weakResult,
    ]);
  });
});

describe("SearchResults", () => {
  it("shows candidate counts and uses a scrollable result list", () => {
    const reviewResult = {
      ...searchResult,
      resume_id: "resume-review",
      shortlist_decision: "review",
      recommendation_level: "moderate_match",
    };
    const notRecommendedResult = {
      ...searchResult,
      resume_id: "resume-not-recommended",
      shortlist_decision: "not_recommended",
      recommendation_level: "weak_match",
      experience_match_reason: "Experience requirement not met: 4.5 years < 5 years.",
    };

    const html = renderToStaticMarkup(
      <SearchResults
        state={{
          loading: false,
          error: "",
          hasSearched: true,
          response: {
            total_candidates_considered: 3,
            matched_count: 3,
            excluded_by_title_count: 0,
            excluded_by_experience_count: 1,
            results: [searchResult, reviewResult, notRecommendedResult],
          },
        }}
      />,
    );

    expect(html).toContain("All (3)");
    expect(html).toContain("Shortlisted (1)");
    expect(html).toContain("Review (1)");
    expect(html).toContain("Not Recommended (1)");
    expect(html).toContain("scrollable-results");
    expect(html).toContain("Experience Excluded");
    expect(html).toContain("<strong>1</strong>");
  });

  it("counts recommendations for filters", () => {
    expect(
      getResultFilterCounts([
        searchResult,
        { ...searchResult, resume_id: "resume-2", shortlist_decision: "review" },
        {
          ...searchResult,
          resume_id: "resume-3",
          shortlist_decision: "not_recommended",
        },
      ]),
    ).toEqual({
      all: 3,
      shortlist: 1,
      review: 1,
      not_recommended: 1,
    });
  });
});
