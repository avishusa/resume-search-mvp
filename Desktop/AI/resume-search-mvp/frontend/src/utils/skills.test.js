import { describe, expect, it } from "vitest";

import { parseCommaSeparatedSkills } from "./skills";

describe("parseCommaSeparatedSkills", () => {
  it("trims comma-separated skills and removes blank values", () => {
    expect(parseCommaSeparatedSkills(" Python, LLM, , LangChain ")).toEqual([
      "Python",
      "LLM",
      "LangChain",
    ]);
  });

  it("returns an empty list for blank input", () => {
    expect(parseCommaSeparatedSkills("   ")).toEqual([]);
  });
});
