import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RationaleTags, rationaleTagLabel } from "./RationaleTags";

afterEach(cleanup);

describe("RationaleTags", () => {
  it("renders nothing without tags", () => {
    const { container } = render(<RationaleTags tags={[]} />);
    expect(container.firstChild).toBeNull();
    const { container: c2 } = render(<RationaleTags tags={undefined} />);
    expect(c2.firstChild).toBeNull();
  });

  it("marks a missing IV rank as an unknown state with texture, not colour alone", () => {
    render(<RationaleTags tags={["iv_rank_unavailable"]} />);
    // The texture is a small mark beside the words, never over them: hatching the whole
    // sentence drew same-coloured lines through every letter (da-vinci finish, 2026-10-19).
    const item = screen.getByText(/IV rank unavailable/);
    expect(item.className).not.toContain("hatch");
    expect(item.className).toContain("text-unknown");
    expect(item.querySelector(".hatch")).not.toBeNull();
  });

  it("de-snake-cases tags it has no label for", () => {
    expect(rationaleTagLabel("some_new_tag")).toBe("some new tag");
  });
});
