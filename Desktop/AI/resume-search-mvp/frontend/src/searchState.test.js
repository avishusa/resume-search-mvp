import { describe, expect, it } from "vitest";

import {
  SEARCH_STORAGE_KEY,
  clearPersistedSearchState,
  createEmptyJobSearchForm,
  loadPersistedSearchState,
  savePersistedSearchState,
} from "./searchState";

function createMemoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

describe("job search state", () => {
  it("does not initialize with hardcoded AI Engineer defaults", () => {
    expect(createEmptyJobSearchForm()).toEqual({
      jobTitle: "",
      jobDescription: "",
      requiredSkills: "",
      niceToHaveSkills: "",
      minYearsExperience: "0",
    });
  });

  it("persists the last search form and results", () => {
    const storage = createMemoryStorage();
    const form = {
      jobTitle: "Data Science",
      jobDescription: "Find data science candidates",
      requiredSkills: "Python, SQL",
      niceToHaveSkills: "GCP",
      minYearsExperience: "4",
    };
    const searchState = {
      loading: false,
      error: "",
      hasSearched: true,
      response: { matched_count: 1, results: [{ resume_id: "1" }] },
    };

    savePersistedSearchState(form, searchState, storage);

    expect(loadPersistedSearchState(storage)).toEqual({
      form,
      searchState,
    });
  });

  it("clears persisted search state", () => {
    const storage = createMemoryStorage();
    storage.setItem(SEARCH_STORAGE_KEY, "{}");

    clearPersistedSearchState(storage);

    expect(storage.getItem(SEARCH_STORAGE_KEY)).toBeNull();
  });
});
