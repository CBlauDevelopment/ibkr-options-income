import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { IdealZoneBar, creditWords, zoneWords } from "./IdealZoneBar";

describe("zoneWords and creditWords", () => {
  it("places the strike against the zone in words", () => {
    expect(zoneWords(190, 185, 192)).toBe("inside the zone");
    expect(zoneWords(180, 185, 192)).toBe("below the zone");
    expect(zoneWords(195, 185, 192)).toBe("above the zone");
    expect(zoneWords(190, null, 192)).toBeNull();
  });
  it("places the premium against the least credit worth taking", () => {
    expect(creditWords(3.25, 3.1)).toBe("above it");
    expect(creditWords(3.0, 3.1)).toBe("below it");
    expect(creditWords(3.1, 3.1)).toBe("exactly at it");
    expect(creditWords(null, 3.1)).toBeNull();
  });
});

describe("IdealZoneBar", () => {
  it("shows the strike zone and the credit floor as separate lines, never on one axis", () => {
    render(<IdealZoneBar ideal={{ lo: 185, hi: 192, min_credit: 3.1 }} premium={3.25} strike={190} />);
    expect(screen.getByText("$185.00")).toBeDefined();
    expect(screen.getByText("$192.00")).toBeDefined();
    expect(screen.getByText(/inside the zone/)).toBeDefined();
    expect(screen.getByText("$3.10")).toBeDefined();
    expect(screen.getByText(/above it/)).toBeDefined();
  });
  it("writes a debit roll's negative net with the minus sign first, never $-0.30", () => {
    render(<IdealZoneBar ideal={{ lo: 185, hi: 192, min_credit: 3.1 }} premium={-0.3} strike={190} />);
    expect(screen.getByText("−$0.30")).toBeDefined();
    expect(document.body.textContent).not.toMatch(/\$-/);
  });
  it("renders an unknown floor as n/a with the hatch", () => {
    render(<IdealZoneBar ideal={{ lo: 185, hi: 192, min_credit: null }} premium={3.25} strike={190} />);
    const na = screen.getByText("n/a");
    expect(na.className).toContain("hatch");
  });
  it("says when no zone was derived", () => {
    render(<IdealZoneBar ideal={{ lo: null, hi: null, min_credit: null }} premium={3.25} strike={190} />);
    expect(screen.getByText("No ideal zone derived.")).toBeDefined();
  });
});
