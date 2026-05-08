export const EMPTY_JOB_SEARCH_FORM = {
  jobTitle: "",
  jobDescription: "",
  requiredSkills: "",
  niceToHaveSkills: "",
  minYearsExperience: "0",
};

export const EMPTY_SEARCH_STATE = {
  loading: false,
  error: "",
  response: null,
  hasSearched: false,
};

export const SEARCH_STORAGE_KEY = "resume-search:last-jd-search";

export function createEmptyJobSearchForm() {
  return { ...EMPTY_JOB_SEARCH_FORM };
}

export function createEmptySearchState() {
  return { ...EMPTY_SEARCH_STATE };
}

export function loadPersistedSearchState(storage = globalThis.localStorage) {
  if (!storage) {
    return {
      form: createEmptyJobSearchForm(),
      searchState: createEmptySearchState(),
    };
  }

  try {
    const rawValue = storage.getItem(SEARCH_STORAGE_KEY);
    if (!rawValue) {
      return {
        form: createEmptyJobSearchForm(),
        searchState: createEmptySearchState(),
      };
    }

    const parsed = JSON.parse(rawValue);
    return {
      form: {
        ...createEmptyJobSearchForm(),
        ...(parsed.form || {}),
      },
      searchState: {
        ...createEmptySearchState(),
        ...(parsed.searchState || {}),
        loading: false,
        error: "",
      },
    };
  } catch (error) {
    return {
      form: createEmptyJobSearchForm(),
      searchState: createEmptySearchState(),
    };
  }
}

export function savePersistedSearchState(
  form,
  searchState,
  storage = globalThis.localStorage,
) {
  if (!storage) {
    return;
  }

  storage.setItem(
    SEARCH_STORAGE_KEY,
    JSON.stringify({
      form,
      searchState: {
        ...searchState,
        loading: false,
        error: "",
      },
    }),
  );
}

export function clearPersistedSearchState(storage = globalThis.localStorage) {
  if (storage) {
    storage.removeItem(SEARCH_STORAGE_KEY);
  }
}
