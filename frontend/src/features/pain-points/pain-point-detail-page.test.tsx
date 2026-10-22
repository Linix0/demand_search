import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { PainPointDetailPage } from "./pain-point-detail-page";

function renderDetail() {
  return renderWithProviders(
    <Routes>
      <Route path="/pain-points/:painPointId" element={<PainPointDetailPage />} />
    </Routes>,
    { route: "/pain-points/00000000-0000-0000-0000-000000000001" },
  );
}

describe("PainPointDetailPage", () => {
  it("shows evidence quotes, timestamps, and independent score explanations", async () => {
    renderDetail();

    expect(
      await screen.findByText(/We spend two days every month reconciling exports by hand/),
    ).toBeInTheDocument();
    expect(screen.getByText("来源可追溯")).toBeInTheDocument();
    expect(screen.getAllByText("证据置信度").length).toBeGreaterThan(0);
    expect(screen.getAllByText("商业机会分").length).toBeGreaterThan(0);
    expect(screen.getAllByText("覆盖度").length).toBeGreaterThan(0);
  });

  it("never renders an unsafe evidence URL as a link", async () => {
    renderDetail();

    await screen.findByText(/We spend two days every month/);
    expect(screen.getAllByText("来源地址缺失或不是有效的 HTTP(S) 链接").length).toBeGreaterThan(0);
    const links = screen.getAllByRole("link");
    expect(links.every((link) => link.getAttribute("href")?.startsWith("https://") || link.getAttribute("href")?.startsWith("/"))).toBe(true);
  });
});
