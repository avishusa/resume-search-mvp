import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildApiUrl,
  getActiveBatchRun,
  getBatchRuns,
  getResumes,
  runLocalBatch,
  searchJobs,
} from "./api";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("builds API URLs with the configured base URL", () => {
    expect(buildApiUrl("/jobs/search", "http://api.test")).toBe(
      "http://api.test/jobs/search",
    );
  });

  it("calls the expected backend endpoints", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ runs: [] }),
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await searchJobs({ job_title: "AI Engineer" });
    await getResumes();
    await getBatchRuns();
    await getActiveBatchRun();
    await runLocalBatch({ force: true });

    expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:8000/jobs/search");
    expect(fetchMock.mock.calls[1][0]).toBe("http://127.0.0.1:8000/resumes");
    expect(fetchMock.mock.calls[2][0]).toBe("http://127.0.0.1:8000/batch/runs");
    expect(fetchMock.mock.calls[3][0]).toBe("http://127.0.0.1:8000/batch/runs/active");
    expect(fetchMock.mock.calls[4][0]).toBe(
      "http://127.0.0.1:8000/batch/run-local-drive?force=true",
    );
  });
});
