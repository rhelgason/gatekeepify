import { describe, expect, it } from "vitest";

import { ApiError, invalidateCache } from "./api";

describe("ApiError", () => {
  it("carries a message and status code", () => {
    const err = new ApiError("nope", 404);
    expect(err).toBeInstanceOf(Error);
    expect(err.message).toBe("nope");
    expect(err.status).toBe(404);
  });
});

describe("invalidateCache", () => {
  it("does not throw with or without a pattern", () => {
    expect(() => invalidateCache()).not.toThrow();
    expect(() => invalidateCache("/friends")).not.toThrow();
  });
});
