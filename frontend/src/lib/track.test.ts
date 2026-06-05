import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { trackEvent } from "./track";

describe("trackEvent", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("{}"))));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("no-ops when there is no auth token", () => {
    trackEvent("test.action");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("posts to /track-event with the bearer token when logged in", () => {
    localStorage.setItem("token", "tok");
    trackEvent("test.action", { foo: "bar" });
    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toContain("/track-event");
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe("Bearer tok");
    const body = JSON.parse(init.body);
    expect(body.action).toBe("test.action");
    expect(body.details.foo).toBe("bar");
  });
});
