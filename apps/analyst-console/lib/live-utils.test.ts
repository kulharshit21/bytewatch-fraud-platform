import {
  diffNewActivities,
  formatRelativeAge,
  formatScenarioLabel,
  recentDecision,
  toastableActivities,
} from "@/lib/live-utils";

describe("live-utils", () => {
  it("identifies only newly arrived live activities", () => {
    const previous = [{ id: "decision:1", type: "decision", timestamp: "2026-04-21T00:00:00Z", message: "old" }];
    const current = [
      ...previous,
      {
        id: "decision:2",
        type: "decision",
        timestamp: "2026-04-21T00:00:05Z",
        decision: "BLOCK",
        score: 0.99,
        message: "BLOCK • txn_2 • score 0.99",
      },
      {
        id: "feedback:1",
        type: "feedback",
        timestamp: "2026-04-21T00:00:06Z",
        feedback_label: "fraud",
        message: "analyst_demo marked fraud",
      },
    ];

    expect(diffNewActivities(previous, current)).toHaveLength(2);
    expect(toastableActivities(diffNewActivities(previous, current))).toHaveLength(2);
  });

  it("formats live labels honestly", () => {
    expect(formatScenarioLabel("new_device_high_amount")).toBe("new device high amount");
    expect(recentDecision("2026-04-21T00:00:25Z", 30, Date.parse("2026-04-21T00:00:40Z"))).toBe(
      true,
    );
    expect(formatRelativeAge("2026-04-21T00:00:10Z", Date.parse("2026-04-21T00:00:15Z"))).toBe(
      "updated 5s ago",
    );
  });
});
