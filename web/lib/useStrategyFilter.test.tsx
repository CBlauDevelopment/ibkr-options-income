import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const nav = vi.hoisted(() => ({
  replace: vi.fn(),
  params: new URLSearchParams(),
  pathname: "/",
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => nav.params,
  usePathname: () => nav.pathname,
}));

import { useStrategyFilter } from "./useStrategyFilter";

beforeEach(() => {
  nav.replace.mockReset();
  nav.params = new URLSearchParams();
  nav.pathname = "/";
});

describe("useStrategyFilter", () => {
  it("reads the filter from ?strategy=", () => {
    nav.params = new URLSearchParams("strategy=cc");
    const { result } = renderHook(() => useStrategyFilter());
    expect(result.current[0]).toBe("cc");
  });
  it("shows All for a junk value", () => {
    nav.params = new URLSearchParams("strategy=foo");
    const { result } = renderHook(() => useStrategyFilter());
    expect(result.current[0]).toBe("all");
  });
  it("writes the choice into the URL and drops it for All, keeping other params", () => {
    nav.params = new URLSearchParams("x=1");
    const { result } = renderHook(() => useStrategyFilter());
    act(() => result.current[1]("csp"));
    expect(nav.replace).toHaveBeenLastCalledWith("/?x=1&strategy=csp", { scroll: false });
    act(() => result.current[1]("all"));
    expect(nav.replace).toHaveBeenLastCalledWith("/?x=1", { scroll: false });
  });
});
