// auth.ts — valida X-LP-Token + CORS por allowed_origins do lp_config
import type { Env } from "./types";

export interface AuthContext {
  lpConfigId: string;
  ownerId: string;
  allowedOrigins: string[];
  dailyLimit: number;
}

export async function authenticateRequest(
  request: Request,
  env: Env,
): Promise<AuthContext | Response> {
  const token = request.headers.get("X-LP-Token");
  const lpConfigId = new URL(request.url).searchParams.get("lp_id")
    || request.headers.get("X-LP-Id");

  if (!token || !lpConfigId) {
    return new Response(
      JSON.stringify({ error: "missing_auth", detail: "X-LP-Token + lp_id required" }),
      { status: 401, headers: { "content-type": "application/json" } },
    );
  }

  if (token !== env.LP_TOKEN) {
    return new Response(
      JSON.stringify({ error: "invalid_token" }),
      { status: 403, headers: { "content-type": "application/json" } },
    );
  }

  const row = await env.DB.prepare(
    "SELECT id, owner_id, allowed_origins, daily_limit FROM lp_configs WHERE id = ?",
  )
    .bind(lpConfigId)
    .first();

  if (!row) {
    return new Response(
      JSON.stringify({ error: "lp_not_found" }),
      { status: 404, headers: { "content-type": "application/json" } },
    );
  }

  let allowedOrigins: string[] = [];
  try {
    allowedOrigins = JSON.parse(String(row.allowed_origins ?? "[]"));
  } catch {
    allowedOrigins = [];
  }

  return {
    lpConfigId: String(row.id),
    ownerId: String(row.owner_id),
    allowedOrigins,
    dailyLimit: Number(row.daily_limit ?? Number(env.DEFAULT_DAILY_LIMIT ?? 800)),
  };
}

export function corsHeaders(origin: string | null, allowed: string[]): HeadersInit {
  const isAllowed = origin && (allowed.includes("*") || allowed.includes(origin));
  return {
    "access-control-allow-origin": isAllowed ? (origin as string) : "null",
    "access-control-allow-headers": "content-type, x-lp-token, x-lp-id",
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "access-control-max-age": "86400",
    "vary": "Origin",
  };
}

export function originDenied(origin: string | null, allowed: string[]): boolean {
  if (!origin) return false;  // requests sem origin (curl, server-side) ignoram CORS
  return !(allowed.includes("*") || allowed.includes(origin));
}
