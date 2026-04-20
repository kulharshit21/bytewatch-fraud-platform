const API_BASE =
  process.env.API_INTERNAL_BASE_URL ??
  process.env.API_PUBLIC_BASE_URL ??
  "http://localhost:8000";

export type ApiResult<T> = {
  data: T | null;
  error: string | null;
};

export async function fetchJson<T>(path: string): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      headers: { "content-type": "application/json" },
    });
    if (!response.ok) {
      const detail = await safeDetail(response);
      return { data: null, error: detail };
    }
    return { data: (await response.json()) as T, error: null };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : "Unknown API error",
    };
  }
}

export async function postJson<T>(
  path: string,
  body: unknown,
): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      cache: "no-store",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const detail = await safeDetail(response);
      return { data: null, error: detail };
    }
    return { data: (await response.json()) as T, error: null };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : "Unknown API error",
    };
  }
}

async function safeDetail(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request failed with ${response.status}`;
  } catch {
    return `Request failed with ${response.status}`;
  }
}
