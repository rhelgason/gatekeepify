import { beforeEach, describe, expect, it } from "vitest";

import { clearToken, getToken, isLoggedIn, setToken } from "./auth";

describe("auth token helpers", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null when no token is stored", () => {
    expect(getToken()).toBeNull();
    expect(isLoggedIn()).toBe(false);
  });

  it("stores and reads back a token", () => {
    setToken("abc123");
    expect(getToken()).toBe("abc123");
    expect(isLoggedIn()).toBe(true);
  });

  it("clears the token", () => {
    setToken("abc123");
    clearToken();
    expect(getToken()).toBeNull();
    expect(isLoggedIn()).toBe(false);
  });
});
