import { NextRequest, NextResponse } from "next/server";

const API_BASE =
  process.env.API_INTERNAL_BASE_URL ??
  process.env.API_PUBLIC_BASE_URL ??
  "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ slug: string[] }> },
) {
  return forwardRequest(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ slug: string[] }> },
) {
  return forwardRequest(request, context);
}

async function forwardRequest(
  request: NextRequest,
  context: { params: Promise<{ slug: string[] }> },
) {
  const { slug } = await context.params;
  const target = new URL(slug.join("/"), `${API_BASE}/`);
  target.search = request.nextUrl.search;

  const response = await fetch(target, {
    method: request.method,
    cache: "no-store",
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
    },
    body:
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.text(),
  });

  return new NextResponse(response.body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
