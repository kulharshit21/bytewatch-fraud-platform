import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import OverviewPage from "@/app/overview/page";
import { fetchJson } from "@/lib/api";

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api", () => ({
  fetchJson: vi.fn(),
}));

describe("OverviewPage", () => {
  it("renders live dashboard data from the API", async () => {
    vi.mocked(fetchJson).mockResolvedValue({
      data: {
        summary: {
          total_transactions: 42,
          blocked_transactions: 5,
          review_transactions: 3,
          approved_transactions: 34,
          average_score: 0.73,
          last_updated_at: "2026-04-21T00:00:00Z",
        },
        trends: [{ bucket: "2026-04-21T00:00:00Z", decision: "BLOCK", count: 5 }],
        model: {
          model_name: "fraud_xgboost",
          model_version: "7",
          model_alias: "champion",
          review_threshold: 0.55,
          block_threshold: 0.82,
        },
        grafana_url: "http://localhost:3000",
      },
      error: null,
    });

    const html = renderToStaticMarkup(await OverviewPage());

    expect(html).toContain("Streaming fraud operations at a glance");
    expect(html).toContain(">42<");
    expect(html).toContain("fraud_xgboost@champion");
    expect(html).toContain("Open analyst queue");
  });

  it("shows an honest empty state when the backend payload is unavailable", async () => {
    vi.mocked(fetchJson).mockResolvedValue({
      data: null,
      error: "API offline",
    });

    const html = renderToStaticMarkup(await OverviewPage());

    expect(html).toContain("Overview is waiting on the backend");
    expect(html).toContain("API offline");
  });
});
