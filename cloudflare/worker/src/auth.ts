// auth.ts — autenticação dividida em dois níveis:
//   - authenticatePublic: rotas que o browser do visitante chama
//       (capture-lead, chat-ia). Valida APENAS Origin allowlist + lp_id existente.
//       NÃO exige X-LP-Token — o token nunca é exposto no front-end público.
//   - authenticateAdmin: rotas administrativas (leads, usage). Exige X-LP-Token.
import type { Env } from "./types";

export interface AuthContext {
  lpConfigId: string;
  ownerId: string;
  allowedOrigins: string[];
  dailyLimit: number;
}

function jsonError(status: number, error: string, detail?: string): Response {
  const body: Record<string, string> = { error };
  if (detail) body.detail = detail;
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

async function loadLpConfig(
  env: Env,
  lpConfigId: string,
): Promise<AuthContext | Response> {
  const row = await env.DB.prepare(
    "SELECT id, owner_id, allowed_origins, daily_limit FROM lp_configs WHERE id = ?",
  )
    .bind(lpConfigId)
    .first();

  if (!row) return jsonError(404, "lp_not_found");

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

/**
 * Autenticação pra endpoints públicos (chamados pelo browser do visitante).
 * NÃO exige X-LP-Token — segurança vem de Origin allowlist + rate limit.
 */
export async function authenticatePublic(
  request: Request,
  env: Env,
): Promise<AuthContext | Response> {
  const lpConfigId = new URL(request.url).searchParams.get("lp_id")
    || request.headers.get("X-LP-Id");

  if (!lpConfigId) {
    return jsonError(400, "missing_lp_id", "X-LP-Id header or ?lp_id= required");
  }

  const ctx = await loadLpConfig(env, lpConfigId);
  if (ctx instanceof Response) return ctx;

  const origin = request.headers.get("origin");
  if (origin && originDenied(origin, ctx.allowedOrigins)) {
    return jsonError(403, "origin_not_allowed");
  }

  return ctx;
}

/**
 * Autenticação pra endpoints admin (CRM, usage).
 * Exige X-LP-Token igual ao secret LP_TOKEN do Worker.
 */
export async function authenticateAdmin(
  request: Request,
  env: Env,
): Promise<AuthContext | Response> {
  const token = request.headers.get("X-LP-Token");
  const lpConfigId = new URL(request.url).searchParams.get("lp_id")
    || request.headers.get("X-LP-Id");

  if (!token || !lpConfigId) {
    return jsonError(401, "missing_auth", "X-LP-Token + lp_id required");
  }
  if (token !== env.LP_TOKEN) {
    return jsonError(403, "invalid_token");
  }
  return loadLpConfig(env, lpConfigId);
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
