import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EvidenceLink } from "./evidence-link";

describe("EvidenceLink", () => {
  it("opens a valid HTTP(S) source safely in a new tab", () => {
    render(<EvidenceLink url="https://example.com/issue/1" />);

    const link = screen.getByRole("link", { name: /打开原始来源/ });
    expect(link).toHaveAttribute("href", "https://example.com/issue/1");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders an explicit error state instead of a synthesized or unsafe link", () => {
    render(<EvidenceLink url="javascript:alert(1)" />);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("来源地址缺失或不是有效的 HTTP(S) 链接");
  });
});
