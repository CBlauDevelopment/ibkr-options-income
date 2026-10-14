import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(resolve(__dirname, "globals.css"), "utf8");

function block(selector: string): string {
  const start = css.indexOf(`${selector} {`);
  expect(start, `missing ${selector} block`).toBeGreaterThanOrEqual(0);
  return css.slice(start, css.indexOf("}", start));
}

function names(src: string): string[] {
  return [...src.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]).sort();
}

describe("globals.css theme tokens", () => {
  it("defines every light token again for dark", () => {
    expect(names(block(':root[data-theme="dark"]'))).toEqual(names(block(":root")));
  });
  it("keeps the semantic names components already use", () => {
    const light = names(block(":root"));
    for (const n of [
      "--bg-background",
      "--bg-surface",
      "--bg-elevated",
      "--text-content",
      "--text-muted",
      "--border-border",
      "--color-gain",
      "--color-loss",
      "--color-unknown",
      "--color-focus",
      "--color-scrim",
      "--shadow-sheet",
    ]) {
      expect(light).toContain(n);
    }
  });
});

describe("globals.css browser chrome", () => {
  it("never paints text selection lime: lime means act (DESIGN.md)", () => {
    expect(block("::selection")).not.toContain("--color-primary");
  });
});
