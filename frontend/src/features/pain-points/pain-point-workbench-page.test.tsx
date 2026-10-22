import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { PainPointWorkbenchPage } from "./pain-point-workbench-page";

describe("PainPointWorkbenchPage", () => {
  it("renders server-paginated pain points with three separate scores", async () => {
    renderWithProviders(<PainPointWorkbenchPage />);

    expect(
      await screen.findByText("财务团队每月手工合并多个表格，容易出错且无法及时完成关账。"),
    ).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "证据置信度" })).toHaveAttribute("aria-valuenow", "72.5");
    expect(screen.getByRole("meter", { name: "商业机会" })).toHaveAttribute("aria-valuenow", "64");
    expect(screen.getByRole("meter", { name: "覆盖度" })).toHaveAttribute("aria-valuenow", "38");
    expect(screen.getByRole("status")).toHaveTextContent("Sample coverage is low");
  });
});
