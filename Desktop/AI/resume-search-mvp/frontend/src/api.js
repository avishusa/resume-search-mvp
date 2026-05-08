const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export function buildApiUrl(path, baseUrl = API_BASE_URL) {
  return `${baseUrl}${path}`;
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(buildApiUrl(path), options);
  } catch (error) {
    throw new Error("Backend unavailable. Check that the FastAPI server is running.");
  }

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Request failed.");
  }

  return response.json();
}

export function searchJobs(payload) {
  return request("/jobs/search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function getResumes() {
  return request("/resumes");
}

export const listResumes = getResumes;

export function getBatchRuns() {
  return request("/batch/runs");
}

export function getActiveBatchRun() {
  return request("/batch/runs/active");
}

export function runLocalBatch({ force = false } = {}) {
  return request(`/batch/run-local-drive?force=${force ? "true" : "false"}`, {
    method: "POST",
  });
}
