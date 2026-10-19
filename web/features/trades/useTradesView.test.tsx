import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const nav = vi.hoisted(() => ({ replace: vi.fn(), params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => nav.params,
  usePathname: () => "/trades",
}));

import { useTradesDay, useTradesView } from "./useTradesView";

beforeEach(() => {
  nav.replace.mockReset();
  nav.params = new URLSearchParams();
});

describe("useTradesView", () => {
  it("reads ?view=", () => {
    nav.params = new URLSearchParams("view=assessed");
    const { result } = renderHook(() => useTradesView("all", 3));
    expect(result.current[0]).toBe("assessed");
  });
  it("opens History for a retired view name", () => {
    nav.params = new URLSearchParams("view=decided");
    const { result } = renderHook(() => useTradesView("all", 3));
    expect(result.current[0]).toBe("history");
  });
  it("opens Proposals when something waits on you, History when nothing does, nothing while unknown", () => {
    expect(renderHook(() => useTradesView("all", 2)).result.current[0]).toBe("proposals");
    expect(renderHook(() => useTradesView("all", 0)).result.current[0]).toBe("history");
    expect(renderHook(() => useTradesView("all", null)).result.current[0]).toBeNull();
  });
  it("keeps the default it chose when the last proposal is approved", () => {
    const { result, rerender } = renderHook(({ n }: { n: number | null }) => useTradesView("all", n), {
      initialProps: { n: 1 },
    });
    expect(result.current[0]).toBe("proposals");
    rerender({ n: 0 });
    expect(result.current[0]).toBe("proposals");
  });
  it("writes a view into the URL and keeps the strategy", () => {
    nav.params = new URLSearchParams("strategy=csp");
    const { result } = renderHook(() => useTradesView("csp", 0));
    act(() => result.current[1]("history"));
    expect(nav.replace).toHaveBeenCalledWith("/trades?strategy=csp&view=history", { scroll: false });
  });
  it("shows Spreads for credit spreads whatever the URL says", () => {
    nav.params = new URLSearchParams("strategy=spread&view=history");
    const { result } = renderHook(() => useTradesView("spread", null));
    expect(result.current[0]).toBe("spreads");
  });
});

describe("useTradesDay", () => {
  it("reads a well-formed ?day= and ignores anything else", () => {
    nav.params = new URLSearchParams("day=2026-10-09");
    expect(renderHook(() => useTradesDay()).result.current[0]).toBe("2026-10-09");
    nav.params = new URLSearchParams("day=yesterday");
    expect(renderHook(() => useTradesDay()).result.current[0]).toBeNull();
  });
  it("writes and clears the day, keeping the rest of the URL", () => {
    nav.params = new URLSearchParams("view=history");
    const { result } = renderHook(() => useTradesDay());
    act(() => result.current[1]("2026-10-09"));
    expect(nav.replace).toHaveBeenLastCalledWith("/trades?view=history&day=2026-10-09", { scroll: false });
    nav.params = new URLSearchParams("view=history&day=2026-10-09");
    const again = renderHook(() => useTradesDay());
    act(() => again.result.current[1](null));
    expect(nav.replace).toHaveBeenLastCalledWith("/trades?view=history", { scroll: false });
  });
});
