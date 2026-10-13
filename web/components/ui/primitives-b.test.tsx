import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Disclosure } from "./Disclosure";
import { Sheet } from "./Sheet";
import { Stub, formatStubValue } from "./Stub";

describe("Disclosure", () => {
  it("starts closed, opens and closes on its button", () => {
    render(<Disclosure summary="Why this trade">IV rank 62</Disclosure>);
    const btn = screen.getByRole("button", { name: /Why this trade/ });
    expect(btn).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("IV rank 62")).not.toBeVisible();
    fireEvent.click(btn);
    expect(btn).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("IV rank 62")).toBeVisible();
  });
  it("can start open", () => {
    render(
      <Disclosure summary="October pay" defaultOpen>
        stub
      </Disclosure>,
    );
    expect(screen.getByRole("button", { name: /October pay/ })).toHaveAttribute("aria-expanded", "true");
  });
});

describe("formatStubValue", () => {
  it("never turns unknown into zero", () => {
    expect(formatStubValue(null, "money")).toBe("n/a");
    expect(formatStubValue(Number.NaN, "percent")).toBe("n/a");
  });
  it("formats signed money with a real minus sign", () => {
    expect(formatStubValue(235, "signed-money")).toBe("+$235.00");
    expect(formatStubValue(-1.3, "signed-money")).toBe("−$1.30");
    expect(formatStubValue(0, "signed-money")).toBe("$0");
  });
  it("formats percent to two places", () => {
    expect(formatStubValue(12.2, "percent")).toBe("12.20%");
  });
});

describe("Stub", () => {
  const lines = [
    { label: "Premium", value: 235, format: "signed-money" as const, explain: "1 contract × $2.35 × 100 shares." },
    { label: "Cash held aside", value: null },
    { label: "A year", value: 12.2, format: "percent" as const, total: true },
  ];
  it("is a labelled group of lines", () => {
    render(<Stub label="AAPL put math" lines={lines} />);
    expect(screen.getByRole("group", { name: "AAPL put math" })).toBeInTheDocument();
    expect(screen.getByText("+$235.00")).toBeInTheDocument();
    expect(screen.getByText("12.20%")).toBeInTheDocument();
  });
  it("hatches an unknown value", () => {
    render(<Stub label="m" lines={lines} />);
    expect(screen.getByText("n/a").className).toContain("hatch");
  });
  it("explains a line in one sentence when tapped", () => {
    render(<Stub label="m" lines={lines} />);
    const line = screen.getByRole("button", { name: /Premium/ });
    expect(line).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(line);
    expect(screen.getByText("1 contract × $2.35 × 100 shares.")).toBeVisible();
  });
});

function SheetHarness({ onClose }: { onClose: () => void }) {
  const [nested, setNested] = useState(false);
  return (
    <Sheet open onClose={onClose} title="Review trade">
      <button type="button">First</button>
      <button type="button" onClick={() => setNested(true)}>
        Approve
      </button>
      {nested && (
        <div role="dialog" aria-modal="true" aria-label="Confirm">
          <button type="button" onClick={() => setNested(false)}>
            Cancel
          </button>
        </div>
      )}
    </Sheet>
  );
}

describe("Sheet", () => {
  it("is a labelled modal dialog that closes on Escape and on the scrim", () => {
    const onClose = vi.fn();
    render(<SheetHarness onClose={onClose} />);
    expect(screen.getByRole("dialog", { name: "Review trade" })).toHaveAttribute("aria-modal", "true");
    fireEvent.keyDown(screen.getByRole("dialog", { name: "Review trade" }), { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId("sheet-scrim"));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
  it("moves focus inside on open", () => {
    render(<SheetHarness onClose={() => {}} />);
    expect(screen.getByRole("dialog", { name: "Review trade" })).toContainElement(
      document.activeElement as HTMLElement,
    );
  });
  it("a nested dialog keeps its own keys", () => {
    const onClose = vi.fn();
    render(<SheetHarness onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    const cancel = screen.getByRole("button", { name: "Cancel" });
    cancel.focus();
    fireEvent.keyDown(cancel, { key: "Escape" });
    fireEvent.keyDown(cancel, { key: "Tab" });
    expect(onClose).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(cancel);
  });
  it("keeps focus where the user put it when the parent re-renders with a fresh onClose", () => {
    // Home polls: the sheet's parent re-renders on every refetch with an inline onClose.
    function Parent() {
      const [ticks, setTicks] = useState(0);
      return (
        <Sheet open onClose={() => setTicks(-1)} title="Review trade">
          <input aria-label="Note" />
          <span data-testid="ticks">{ticks}</span>
          <button type="button" onClick={() => setTicks((t) => t + 1)}>
            Refetch
          </button>
        </Sheet>
      );
    }
    render(<Parent />);
    const note = screen.getByLabelText("Note");
    note.focus();
    fireEvent.click(screen.getByRole("button", { name: "Refetch" }));
    expect(screen.getByTestId("ticks")).toHaveTextContent("1");
    expect(document.activeElement).toBe(note);
  });
  it("keeps Escape and Tab inside the sheet when focus lands on its prose", () => {
    // Clicking non-focusable prose focuses the nearest focusable ancestor: the panel itself.
    // Without a focusable panel focus falls to <body> and the sheet's key handling never sees it.
    const onClose = vi.fn();
    render(
      <Sheet open onClose={onClose} title="Review trade">
        <p>Claude says the put is well covered.</p>
        <button type="button">First</button>
        <button type="button">Last</button>
      </Sheet>,
    );
    const panel = screen.getByRole("dialog", { name: "Review trade" });
    expect(panel).toHaveAttribute("tabindex", "-1");
    panel.focus();
    expect(document.activeElement).toBe(panel);

    fireEvent.keyDown(document.activeElement as Element, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);

    // Shift+Tab from the panel would otherwise leave the sheet for the page behind it.
    const shiftTabNotPrevented = fireEvent.keyDown(panel, { key: "Tab", shiftKey: true });
    expect(shiftTabNotPrevented).toBe(false);
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Last" }));

    panel.focus();
    const tabNotPrevented = fireEvent.keyDown(panel, { key: "Tab" });
    expect(tabNotPrevented).toBe(false);
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Close" }));
  });
  it("renders nothing when closed", () => {
    render(
      <Sheet open={false} onClose={() => {}} title="Review trade">
        x
      </Sheet>,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
