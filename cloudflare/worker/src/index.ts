// index.ts — Hono router do Worker LP Builder
import { Hono } from "hono";
import type { Env } from "./types";
import {
  authenticatePublic,
  authenticateAdmin,
  corsHeaders,
} from "./auth";
import { checkAndIncrement, getUsage } from "./rate-limit";
import { streamChat, type ChatRequest } from "./chat-adapter";

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

function randomId(): string {
  return crypto.randomUUID();
}

// CORS preflight + escolha de headers dinâmico
app.options("*", async (c) => {
  const origin = c.req.header("origin") ?? null;
  // Sem autenticar — preflight não precisa, mas usamos lp_id se vier
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

// POST /capture-lead — público (browser do visitante): só Origin allowlist + rate limit
app.post("/capture-lead", async (c) => {
  const auth = await authenticatePublic(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const origin = c.req.header("origin") ?? null;

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

// GET /leads — admin (exige X-LP-Token)
app.get("/leads", async (c) => {
  const auth = await authenticateAdmin(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const limit = Math.min(Number(c.req.query("limit") ?? 50), 200);
  const offset = Math.max(Number(c.req.query("offset") ?? 0), 0);
  const status = c.req.query("status");

  const params: unknown[] = [auth.lpConfigId];
  let where = "lp_config_id = ?";
  if (status) {
    if (!VALID_LEAD_STATUS.has(status)) {
      return c.json({ error: "invalid_status" }, 400);
    }
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

// POST /chat-ia — público (browser do visitante): só Origin allowlist + rate limit
app.post("/chat-ia", async (c) => {
  const auth = await authenticatePublic(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const origin = c.req.header("origin") ?? null;

  const usage = await checkAndIncrement(c.env, auth.lpConfigId, "chat-ia", auth.dailyLimit);
  if (usage.exceeded) {
    return c.json({ error: "daily_limit_exceeded" }, 429, corsHeaders(origin, auth.allowedOrigins));
  }

  const body = await c.req.json<ChatRequest & { session_id?: string }>();
  if (!body.messages || body.messages.length === 0) {
    return c.json({ error: "missing_messages" }, 400);
  }

  // Cap defensivo em content (SQLite não enforce length)
  for (const m of body.messages) {
    if (typeof m.content === "string" && m.content.length > MAX_CHAT_CONTENT) {
      m.content = m.content.slice(0, MAX_CHAT_CONTENT);
    }
  }

  // Captura o último user msg pra log (antes de stream consumir)
  const lastUser = [...body.messages].reverse().find((m) => m.role === "user");
  const sessionId = body.session_id;
  const assistantBuffer: string[] = [];

  // Stream com callback de chunk pra acumular assistant response
  const { stream, provider } = await streamChat(c.env, body, (chunk) => {
    if (assistantBuffer.length < 32) assistantBuffer.push(chunk);  // cap memory
    else assistantBuffer.push(chunk);  // continua, sem cap pra texto final
  });

  // Async: grava user msg + assistant msg quando stream terminar
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
    // Grava assistant após stream consumido. waitUntil sustenta após Response.
    c.executionCtx.waitUntil(
      (async () => {
        // Espera 30s no máx; assistantBuffer é mutado pelo callback do stream
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

// GET /usage — admin (counts diários)
app.get("/usage", async (c) => {
  const auth = await authenticateAdmin(c.req.raw, c.env);
  if (auth instanceof Response) return auth;

  const usage = await getUsage(c.env, auth.lpConfigId, auth.dailyLimit);
  return c.json(usage);
});

// 404 handler
app.notFound((c) => c.json({ error: "not_found" }, 404));

export default app;
