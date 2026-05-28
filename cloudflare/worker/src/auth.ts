// auth.ts — autenticação dividida em dois níveis:
//   - authenticatePublic: rotas que o browser do visitante chama
//       (capture-lead, chat-ia). Valida Origin allowlist + lp_id existente.
//       Requer Origin presente (block server-to-server bypass).
//   - authenticateAdmin: rotas administrativas (leads, usage). Exige X-LP-Token
//       comparado contra lp_configs.token_hash (sha-256, constant-time).
import type { Env } from "./types";

export interface AuthContext {
  lpConfigId: string;
  ownerId: string;
  allowedOrigins: string[];
  dailyLimit: number;
  briefing: string;
  name: string;
  fallbackContactUrl: string | null;
  tokenHash: string | null;
}

// Hints traduzidos por error code — ajudam aluno/visitante a entender o erro
// sem precisar abrir docs/troubleshooting.md. Adicione novos códigos aqui
// pra manter mensagens consistentes.
const ERROR_HINTS: Record<string, string> = {
  missing_lp_id: "Inclua ?lp_id=<UUID> na URL ou header X-LP-Id.",
  lp_not_found: "lp_id não existe no D1. Rode `setup_cloudflare.py` pra inserir/atualizar.",
  origin_required: "Origin ausente. Browser sempre envia; curl precisa de -H 'Origin: https://...'.",
  origin_not_allowed: "Esse domínio não está em allowed_origins do D1. Edite via setup_deploy.py (auto) ou wrangler d1 execute.",
  missing_auth: "Endpoint admin exige X-LP-Token + X-LP-Id (ou ?lp_id=).",
  invalid_token: "Token errado. Confira ~/.operacao-ia/config/setup9.env (LP_TOKEN).",
  daily_limit_exceeded: "Limite diário (800) atingido. Reseta em 00:00 UTC.",
};

function jsonError(status: number, error: string, detail?: string): Response {
  const body: Record<string, string> = { error };
  if (detail) body.detail = detail;
  const hint = ERROR_HINTS[error];
  if (hint) body.hint = hint;
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
    "SELECT id, owner_id, allowed_origins, daily_limit, briefing, fallback_contact_url, token_hash, name FROM lp_configs WHERE id = ?",
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
    name: String(row.name ?? ""),
    allowedOrigins,
    dailyLimit: Number(row.daily_limit ?? Number(env.DEFAULT_DAILY_LIMIT ?? 800)),
    briefing: String(row.briefing ?? ""),
    fallbackContactUrl: row.fallback_contact_url ? String(row.fallback_contact_url) : null,
    tokenHash: row.token_hash ? String(row.token_hash) : null,
  };
}

/**
 * Autenticação pra endpoints públicos (chamados pelo browser do visitante).
 * NÃO exige X-LP-Token — segurança vem de Origin allowlist + rate limit.
 * Origin é OBRIGATÓRIO (rejeita curl/server-to-server pra evitar abuso).
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
  if (!origin) {
    return jsonError(403, "origin_required");
  }
  if (originDenied(origin, ctx.allowedOrigins)) {
    return jsonError(403, "origin_not_allowed");
  }

  return ctx;
}

// Constant-time string compare (ambos hex de mesmo length).
function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

async function sha256Hex(input: string): Promise<string> {
  const bytes = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const arr = Array.from(new Uint8Array(digest));
  return arr.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Autenticação pra endpoints admin (CRM, usage).
 * Exige X-LP-Token cujo sha-256 bate com lp_configs.token_hash (per-LP).
 * Fallback: se a row não tem token_hash setado, aceita env.LP_TOKEN
 * (compat com setups antigos antes da migration 002).
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

  const ctx = await loadLpConfig(env, lpConfigId);
  if (ctx instanceof Response) return ctx;

  if (ctx.tokenHash) {
    const inputHash = await sha256Hex(token);
    if (!timingSafeEqual(inputHash, ctx.tokenHash)) {
      return jsonError(403, "invalid_token");
    }
  } else {
    // Fallback pra setups antes da migration 002.
    if (!timingSafeEqual(token, env.LP_TOKEN ?? "")) {
      return jsonError(403, "invalid_token");
    }
  }

  return ctx;
}

export function corsHeaders(origin: string | null, allowed: string[]): HeadersInit {
  const isAllowed = origin && (allowed.includes("*") || allowed.includes(origin));
  return {
    "access-control-allow-origin": isAllowed ? (origin as string) : "null",
    "access-control-allow-headers": "content-type, x-lp-token, x-lp-id",
    "access-control-allow-methods": "GET, POST, PATCH, OPTIONS",
    "access-control-max-age": "86400",
    "vary": "Origin",
  };
}

export function originDenied(origin: string | null, allowed: string[]): boolean {
  if (!origin) return true;  // Origin é obrigatório agora — bloqueia bypass server-to-server.
  return !(allowed.includes("*") || allowed.includes(origin));
}
