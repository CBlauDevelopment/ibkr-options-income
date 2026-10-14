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

function declared(src: string, name: string): string {
  const m = src.match(new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})\\b`));
  expect(m, `missing ${name}`).not.toBeNull();
  return (m as RegExpMatchArray)[1];
}

// WCAG 2.x relative luminance and contrast ratio.
function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(fg: string, bg: string): number {
  const [hi, lo] = [luminance(fg), luminance(bg)].sort((a, b) => b - a);
  return (hi + 0.05) / (lo + 0.05);
}

describe("globals.css unknown grey", () => {
  // DESIGN.md: small "n/a" text may sit on the page, a card or a pressed fill, so the grey has to
  // pass AA (4.5:1) on all three in both themes. (Sunk-deep is only a hover fill: AA-large.)
  for (const [theme, selector] of [
    ["light", ":root"],
    ["dark", ':root[data-theme="dark"]'],
  ] as const) {
    it(`passes AA on the page, card and pressed fill in the ${theme} theme`, () => {
      const src = block(selector);
      const unknown = declared(src, "--color-unknown");
      for (const surface of ["--bg-background", "--bg-surface", "--bg-elevated"]) {
        const ratio = contrast(unknown, declared(src, surface));
        expect(ratio, `${unknown} on ${surface}`).toBeGreaterThanOrEqual(4.5);
      }
    });
  }
});

describe("globals.css browser chrome", () => {
  it("never paints text selection lime: lime means act (DESIGN.md)", () => {
    expect(block("::selection")).not.toContain("--color-primary");
  });
});
