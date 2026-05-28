// index.ts — Hono router do Worker LP Builder
import { Hono } from "hono";
import type { Env } from "./types";
import { authenticateRequest, corsHeaders, originDenied } from "./auth";
import { checkAndIncrement, getUsage } from "./rate-limit";
import { streamChat, type ChatRequest } from "./chat-adapter";

const app = new Hono<{ Bindings: Env }>();

function randomId(): string {
  return crypto.randomUUID();
}

// CORS preflight + escolha de headers dinâmico
app.options("*", async (c) => {
  const origin = c.req.header("origin") ?? null;
  // Sem autenticar — preflight não precisa, mas usamos lp_id se vier
  const lpId = c.req.query("lp_id");
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

// GET /health — público (gate da skill T4)
app.get("/health", async (c) => {
  const lpCount = await c.env.DB.prepare("SELECT COUNT(*) as n FROM lp_configs").first<{ n: number }>();
  return c.json({ ok: true, lp_count: lpCount?.n ?? 0, ts: new Date().toISOString() });
});

// POST /capture-lead — autenticado + CORS validado + rate limit
app.post("/capture-lead", async (c) => {
  const auth = await authenticateRequest(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const origin = c.req.header("origin") ?? null;
  if (originDenied(origin, auth.allowedOrigins)) {
    return c.json({ error: "origin_not_allowed" }, 403);
  }

  const usage = await checkAndIncrement(c.env, auth.lpConfigId, "capture-lead", auth.dailyLimit);
  if (usage.exceeded) {
    return c.json({ error: "daily_limit_exceeded" }, 429, corsHeaders(origin, auth.allowedOrigins));
  }

  const body = await c.req.json<{
    name: string;
    email?: string;
    whatsapp?: string;
    utm_source?: string;
    utm_medium?: string;
    utm_campaign?: string;
    utm_content?: string;
    utm_term?: string;
  }>();

  if (!body.name || body.name.trim().length < 2) {
    return c.json({ error: "invalid_name" }, 400);
  }

  const id = randomId();
  await c.env.DB.prepare(
    `INSERT INTO leads
     (id, lp_config_id, name, email, whatsapp, utm_source, utm_medium, utm_campaign, utm_content, utm_term)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(
      id,
      auth.lpConfigId,
      body.name.trim(),
      body.email ?? null,
      body.whatsapp ?? null,
      body.utm_source ?? null,
      body.utm_medium ?? null,
      body.utm_campaign ?? null,
      body.utm_content ?? null,
      body.utm_term ?? null,
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

// GET /leads — listar leads do lp_config_id (paginado)
app.get("/leads", async (c) => {
  const auth = await authenticateRequest(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const limit = Math.min(Number(c.req.query("limit") ?? 50), 200);
  const offset = Math.max(Number(c.req.query("offset") ?? 0), 0);
  const status = c.req.query("status");

  const params: unknown[] = [auth.lpConfigId];
  let where = "lp_config_id = ?";
  if (status) {
    where += " AND status = ?";
    params.push(status);
  }

  const rows = await c.env.DB.prepare(
    `SELECT id, name, email, whatsapp, status, utm_source, utm_medium, utm_campaign, created_at
     FROM leads WHERE ${where} ORDER BY created_at DESC LIMIT ? OFFSET ?`,
  )
    .bind(...params, limit, offset)
    .all();

  return c.json({ leads: rows.results ?? [], limit, offset });
});

// POST /chat-ia — streaming SSE
app.post("/chat-ia", async (c) => {
  const auth = await authenticateRequest(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const origin = c.req.header("origin") ?? null;
  if (originDenied(origin, auth.allowedOrigins)) {
    return c.json({ error: "origin_not_allowed" }, 403);
  }

  const usage = await checkAndIncrement(c.env, auth.lpConfigId, "chat-ia", auth.dailyLimit);
  if (usage.exceeded) {
    return c.json({ error: "daily_limit_exceeded" }, 429);
  }

  const body = await c.req.json<ChatRequest & { session_id?: string }>();
  if (!body.messages || body.messages.length === 0) {
    return c.json({ error: "missing_messages" }, 400);
  }

  const { stream, provider } = await streamChat(c.env, body);

  // Async: grava último user msg (não-bloqueante)
  const lastUser = [...body.messages].reverse().find((m) => m.role === "user");
  if (lastUser && body.session_id) {
    c.executionCtx.waitUntil(
      c.env.DB.prepare(
        "INSERT INTO chat_messages (id, lp_config_id, session_id, role, content, provider) VALUES (?, ?, ?, 'user', ?, ?)",
      )
        .bind(randomId(), auth.lpConfigId, body.session_id, lastUser.content, provider)
        .run(),
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

// GET /usage — counts diários
app.get("/usage", async (c) => {
  const auth = await authenticateRequest(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const usage = await getUsage(c.env, auth.lpConfigId, auth.dailyLimit);
  return c.json(usage);
});

// 404 handler
app.notFound((c) => c.json({ error: "not_found" }, 404));

export default app;
