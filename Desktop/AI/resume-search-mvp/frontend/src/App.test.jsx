import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  BatchRunControls,
  BatchRunsTable,
  BatchSummaryPanel,
  JobSearchPage,
  ResumeStatusTable,
  canStartBatch,
  shouldPollActiveBatch,
} from "./App";

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
        }}
      />,
    );

    expect(html).toContain("Latest Batch Summary");
    expect(html).toContain("Total Files");
    expect(html).toContain("<strong>7</strong>");
    expect(html).toContain("Fallback");
    expect(html).toContain("<strong>1</strong>");
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
