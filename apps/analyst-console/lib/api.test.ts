import { fetchJson, postJson } from "@/lib/api";


describe("api helpers", () => {
  it("returns parsed JSON payloads on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ status: "ok" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchJson<{ status: string }>("/health/live");

    expect(result).toEqual({
      data: { status: "ok" },
      error: null,
    });
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/health/live", {
      cache: "no-store",
      headers: { "content-type": "application/json" },
    });
  });

  it("surfaces backend error detail on POST failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: vi.fn().mockResolvedValue({ detail: "invalid payload" }),
      }),
    );

    const result = await postJson("/cases/case-123/feedback", {
      analyst_id: "analyst_demo",
    });

    expect(result).toEqual({
      data: null,
      error: "invalid payload",
    });
  });
});
