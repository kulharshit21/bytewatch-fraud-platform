import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import CasesPage from "@/app/cases/page";
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

describe("CasesPage", () => {
  it("defaults to the open REVIEW analyst backlog and renders live counts", async () => {
    vi.mocked(fetchJson).mockResolvedValue({
      data: {
        items: [
          {
            case_id: "case-1",
            transaction_id: "txn_00000042",
            decision: "REVIEW",
            status: "open",
            decision_time: "2026-04-21T00:00:00Z",
            score: 0.62,
            scenario: "new_device_high_amount",
            amount: 1200,
            country: "IN",
            channel: "ecommerce",
            account_id: "acct_001",
          },
        ],
        pagination: {
          page: 1,
          page_size: 20,
          total: 1,
          total_pages: 1,
        },
        live_window: {
          window_seconds: 30,
          matching_cases: 1,
          blocked_cases: 0,
          review_cases: 1,
          last_updated_at: "2026-04-21T00:00:00Z",
        },
        activities: [
          {
            id: "decision:case-1",
            type: "decision",
            timestamp: "2026-04-21T00:00:00Z",
            transaction_id: "txn_00000042",
            decision: "REVIEW",
            score: 0.62,
            message: "REVIEW • txn_00000042 • score 0.62",
          },
        ],
      },
      error: null,
    });

    const html = renderToStaticMarkup(await CasesPage({ searchParams: Promise.resolve({}) }));

    expect(html).toContain("Analyst backlog");
    expect(html).toContain("Defaults to open REVIEW cases");
    expect(html).toContain("Open analyst backlog");
    expect(html).toContain("New in last 30s");
    expect(html).toContain("Live activity strip");
  });
});
