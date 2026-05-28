// index.ts — Hono router do Worker LP Builder
import { Hono } from "hono";
import type { Env } from "./types";
import {
  authenticatePublic,
  authenticateAdmin,
  corsHeaders,
} from "./auth";
import { checkAndIncrement, getUsage } from "./rate-limit";
import { streamChat, sanitizeMessages } from "./chat-adapter";

const app = new Hono<{ Bindings: Env }>();

const VALID_LEAD_STATUS = new Set([
  "novo",
  "em_conversa",
  "qualificado",
  "encaminhado_humano",
  "converteu",
  "abandonou",
]);

const MAX_CHAT_CONTENT = 4096;
const MAX_CHAT_HISTORY = 20;
const MAX_NAME_LEN = 120;
const MAX_TEXT_LEN = 500;
const MAX_URL_LEN = 2048;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_DIGIT_RE = /^\d{10,13}$/;
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function randomId(): string {
  return crypto.randomUUID();
}

function clamp(value: unknown, max: number): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  return trimmed.slice(0, max);
}

async function safeJson<T>(req: Request): Promise<T | null> {
  try { return await req.json<T>(); } catch { return null; }
}

// CORS preflight + escolha de headers dinâmico
app.options("*", async (c) => {
  const origin = c.req.header("origin") ?? null;
  const lpId = c.req.query("lp_id") ?? c.req.header("X-LP-Id");
  if (lpId) {
    const row = await c.env.DB.prepare("SELECT allowed_origins FROM lp_configs WHERE id = ?")
      .bind(lpId)
      .first<{ allowed_origins: string }>();
    let allowed: string[] = [];
    try { allowed = JSON.parse(row?.allowed_origins ?? "[]"); } catch { /* */ }
    return new Response(null, { status: 204, headers: corsHeaders(origin, allowed) });
  }
  return new Response(null, { status: 204 });
});

// GET /health — público, sem dados sensíveis
app.get("/health", (c) => {
  return c.json({ ok: true, ts: new Date().toISOString() });
});

// POST /capture-lead — público (browser): Origin allowlist + rate limit + validation
app.post("/capture-lead", async (c) => {
  const auth = await authenticatePublic(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const origin = c.req.header("origin") ?? null;

  const usage = await checkAndIncrement(c.env, auth.lpConfigId, "capture-lead", auth.dailyLimit);
  if (usage.exceeded) {
    return new Response(JSON.stringify({ error: "daily_limit_exceeded" }), {
      status: 429,
      headers: { "content-type": "application/json", ...corsHeaders(origin, auth.allowedOrigins) },
    });
  }

  const body = await safeJson<{
    name?: string;
    email?: string;
    whatsapp?: string;
    utm_source?: string;
    utm_medium?: string;
    utm_campaign?: string;
    utm_content?: string;
    utm_term?: string;
    page_url?: string;
    referrer?: string;
  }>(c.req.raw);
  if (!body) {
    return new Response(JSON.stringify({ error: "invalid_json" }), {
      status: 400,
      headers: { "content-type": "application/json", ...corsHeaders(origin, auth.allowedOrigins) },
    });
  }

  // Validation
  const name = clamp(body.name, MAX_NAME_LEN);
  if (!name || name.length < 2) {
    return new Response(JSON.stringify({ error: "invalid_name" }), {
      status: 400,
      headers: { "content-type": "application/json", ...corsHeaders(origin, auth.allowedOrigins) },
    });
  }
  const email = clamp(body.email, MAX_TEXT_LEN);
  if (email && !EMAIL_RE.test(email)) {
    return new Response(JSON.stringify({ error: "invalid_email" }), {
      status: 400,
      headers: { "content-type": "application/json", ...corsHeaders(origin, auth.allowedOrigins) },
    });
  }
  let whatsapp: string | null = null;
  if (body.whatsapp) {
    const digits = String(body.whatsapp).replace(/\D/g, "");
    if (!PHONE_DIGIT_RE.test(digits)) {
      return new Response(JSON.stringify({ error: "invalid_whatsapp" }), {
        status: 400,
        headers: { "content-type": "application/json", ...corsHeaders(origin, auth.allowedOrigins) },
      });
    }
    whatsapp = digits;
  }

  const id = randomId();
  await c.env.DB.prepare(
    `INSERT INTO leads
     (id, lp_config_id, name, email, whatsapp,
      utm_source, utm_medium, utm_campaign, utm_content, utm_term,
      page_url, referrer)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(
      id,
      auth.lpConfigId,
      name,
      email,
      whatsapp,
      clamp(body.utm_source, MAX_TEXT_LEN),
      clamp(body.utm_medium, MAX_TEXT_LEN),
      clamp(body.utm_campaign, MAX_TEXT_LEN),
      clamp(body.utm_content, MAX_TEXT_LEN),
      clamp(body.utm_term, MAX_TEXT_LEN),
      clamp(body.page_url, MAX_URL_LEN),
      clamp(body.referrer, MAX_URL_LEN),
    )
    .run();

  return new Response(JSON.stringify({ ok: true, id }), {
    status: 200,
    headers: {
      "content-type": "application/json",
      ...corsHeaders(origin, auth.allowedOrigins),
    },
  });
});

// Helper pra response JSON com CORS headers (admin endpoints precisam ou browser bloqueia).
function jsonWithCors(
  origin: string | null,
  allowedOrigins: string[],
  body: unknown,
  status = 200,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
      ...corsHeaders(origin, allowedOrigins),
    },
  });
}

// GET /leads — admin
app.get("/leads", async (c) => {
  const origin = c.req.header("origin") ?? null;
  const auth = await authenticateAdmin(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const rawLimit = Number(c.req.query("limit") ?? 50);
  const rawOffset = Number(c.req.query("offset") ?? 0);
  if (!Number.isFinite(rawLimit) || rawLimit < 0) {
    return jsonWithCors(origin, auth.allowedOrigins, { error: "invalid_limit" }, 400);
  }
  if (!Number.isFinite(rawOffset) || rawOffset < 0) {
    return jsonWithCors(origin, auth.allowedOrigins, { error: "invalid_offset" }, 400);
  }
  const limit = Math.min(Math.floor(rawLimit), 200);
  const offset = Math.floor(rawOffset);
  const status = c.req.query("status");

  let sql: string;
  let params: unknown[];
  if (status) {
    if (!VALID_LEAD_STATUS.has(status)) {
      return jsonWithCors(origin, auth.allowedOrigins, { error: "invalid_status" }, 400);
    }
    sql = `SELECT id, name, email, whatsapp, status,
                  utm_source, utm_medium, utm_campaign, utm_content, utm_term,
                  page_url, referrer, created_at
           FROM leads WHERE lp_config_id = ? AND status = ?
           ORDER BY created_at DESC LIMIT ? OFFSET ?`;
    params = [auth.lpConfigId, status, limit, offset];
  } else {
    sql = `SELECT id, name, email, whatsapp, status,
                  utm_source, utm_medium, utm_campaign, utm_content, utm_term,
                  page_url, referrer, created_at
           FROM leads WHERE lp_config_id = ?
           ORDER BY created_at DESC LIMIT ? OFFSET ?`;
    params = [auth.lpConfigId, limit, offset];
  }

  const rows = await c.env.DB.prepare(sql).bind(...params).all();
  return jsonWithCors(origin, auth.allowedOrigins, { leads: rows.results ?? [], limit, offset });
});

// PATCH /leads/:id — admin: atualizar status com escopo de lp_config_id (anti cross-tenant)
app.patch("/leads/:id", async (c) => {
  const origin = c.req.header("origin") ?? null;
  const auth = await authenticateAdmin(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const id = c.req.param("id");
  if (!id || !UUID_RE.test(id)) {
    return jsonWithCors(origin, auth.allowedOrigins, { error: "invalid_id" }, 400);
  }

  const body = await safeJson<{ status?: string }>(c.req.raw);
  if (!body || !body.status || !VALID_LEAD_STATUS.has(body.status)) {
    return jsonWithCors(origin, auth.allowedOrigins, { error: "invalid_status" }, 400);
  }

  const result = await c.env.DB.prepare(
    "UPDATE leads SET status = ? WHERE id = ? AND lp_config_id = ?",
  )
    .bind(body.status, id, auth.lpConfigId)
    .run();

  if (!result.meta.changes) {
    return jsonWithCors(origin, auth.allowedOrigins, { error: "not_found" }, 404);
  }
  return jsonWithCors(origin, auth.allowedOrigins, { ok: true, id, status: body.status });
});

// POST /chat-ia — público: Origin allowlist + rate limit + briefing server-side
app.post("/chat-ia", async (c) => {
  const auth = await authenticatePublic(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const origin = c.req.header("origin") ?? null;

  const usage = await checkAndIncrement(c.env, auth.lpConfigId, "chat-ia", auth.dailyLimit);
  if (usage.exceeded) {
    return new Response(JSON.stringify({ error: "daily_limit_exceeded" }), {
      status: 429,
      headers: { "content-type": "application/json", ...corsHeaders(origin, auth.allowedOrigins) },
    });
  }

  const body = await safeJson<{ messages?: unknown; session_id?: unknown }>(c.req.raw);
  if (!body) {
    return new Response(JSON.stringify({ error: "invalid_json" }), {
      status: 400,
      headers: { "content-type": "application/json", ...corsHeaders(origin, auth.allowedOrigins) },
    });
  }

  // Sanitiza histórico: aceita só user/assistant, rejeita system, normaliza 'bot' legacy
  const sanitized = sanitizeMessages(body.messages)
    .slice(-MAX_CHAT_HISTORY)
    .map((m) => ({
      role: m.role,
      content: m.content.length > MAX_CHAT_CONTENT ? m.content.slice(0, MAX_CHAT_CONTENT) : m.content,
    }));

  if (sanitized.length === 0) {
    return new Response(JSON.stringify({ error: "missing_messages" }), {
      status: 400,
      headers: { "content-type": "application/json", ...corsHeaders(origin, auth.allowedOrigins) },
    });
  }

  // session_id: opcional. Se vier, deve ser UUID (defesa contra injection).
  let sessionId: string | undefined;
  if (typeof body.session_id === "string" && UUID_RE.test(body.session_id)) {
    sessionId = body.session_id;
  }

  // Captura o último user msg pra log
  const lastUser = [...sanitized].reverse().find((m) => m.role === "user");
  const assistantBuffer: string[] = [];

  // Briefing/lpName/fallbackUrl agora vêm SEMPRE do D1 (auth.* carrega de lp_configs).
  const { stream, provider } = await streamChat(
    c.env,
    { messages: sanitized },
    {
      briefing: auth.briefing,
      lpName: auth.name,
      fallbackContactUrl: auth.fallbackContactUrl,
    },
    (chunk) => assistantBuffer.push(chunk),
  );

  if (sessionId) {
    if (lastUser) {
      const userContent = lastUser.content.slice(0, MAX_CHAT_CONTENT);
      c.executionCtx.waitUntil(
        c.env.DB.prepare(
          "INSERT INTO chat_messages (id, lp_config_id, session_id, role, content, provider) VALUES (?, ?, ?, 'user', ?, ?)",
        )
          .bind(randomId(), auth.lpConfigId, sessionId, userContent, provider)
          .run(),
      );
    }
    c.executionCtx.waitUntil(
      (async () => {
        const start = Date.now();
        while (Date.now() - start < 30_000) {
          if (assistantBuffer.length > 0 && stream.locked === false) break;
          await new Promise((r) => setTimeout(r, 200));
        }
        const content = assistantBuffer.join("").slice(0, MAX_CHAT_CONTENT);
        if (content) {
          await c.env.DB.prepare(
            "INSERT INTO chat_messages (id, lp_config_id, session_id, role, content, provider) VALUES (?, ?, ?, 'assistant', ?, ?)",
          )
            .bind(randomId(), auth.lpConfigId, sessionId, content, provider)
            .run();
        }
      })(),
    );
  }

  return new Response(stream, {
    status: 200,
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache",
      "x-provider": provider,
      ...corsHeaders(origin, auth.allowedOrigins),
    },
  });
});

// GET /usage — admin
app.get("/usage", async (c) => {
  const origin = c.req.header("origin") ?? null;
  const auth = await authenticateAdmin(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const usage = await getUsage(c.env, auth.lpConfigId, auth.dailyLimit);
  return jsonWithCors(origin, auth.allowedOrigins, usage);
});

// 404 handler
app.notFound((c) => c.json({ error: "not_found" }, 404));

export default app;
