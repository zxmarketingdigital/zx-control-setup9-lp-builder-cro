// chat-adapter.ts — streaming SSE com auto-fallback Gemini → Claude → canned
// Adaptado de ~/zx-flow-white-label/supabase/functions/agent-chat/index.ts
import type { Env } from "./types";

export interface ChatTurn {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatRequest {
  messages: ChatTurn[];
  briefing: string;  // conteúdo do briefing.md vira system prompt
  lpName: string;
  fallbackContactUrl?: string;  // wa.me/... pra canned response
}

const CANNED_FALLBACK = (waUrl?: string) =>
  waUrl
    ? `Estou temporariamente com alta demanda. Pode falar direto com a equipe humana aqui: ${waUrl}`
    : "Estou temporariamente com alta demanda. Tente novamente em alguns minutos ou fale com a equipe humana.";

function buildSystemPrompt(briefing: string, lpName: string): string {
  return `Você é o assistente da landing page "${lpName}". Responda dúvidas dos visitantes baseado APENAS no contexto abaixo. Se a pergunta não tiver resposta no contexto, peça pra falar com humano.

# Contexto da LP
${briefing}

# Regras
- Português brasileiro natural, tom profissional mas acessível
- NUNCA invente preço, prazo ou benefício não declarado
- Se perguntado sobre disponibilidade/orçamento real, peça pra falar com humano
- Respostas curtas (3-5 frases máx)
- NÃO fale "como assistente IA" — fale como representante da marca`;
}

async function* streamGemini(
  env: Env,
  systemPrompt: string,
  messages: ChatTurn[],
): AsyncGenerator<string, void, unknown> {
  const apiKey = env.GEMINI_API_KEY;
  if (!apiKey) throw new Error("GEMINI_API_KEY missing");

  // Gemini API: contents = histórico user/model, systemInstruction separado
  const contents = messages.map((m) => ({
    role: m.role === "assistant" ? "model" : "user",
    parts: [{ text: m.content }],
  }));

  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?alt=sse&key=${apiKey}`;

  const resp = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: systemPrompt }] },
      contents,
      generationConfig: { maxOutputTokens: 500, temperature: 0.7 },
    }),
  });

  if (!resp.ok) {
    if (resp.status === 429 || resp.status === 403) {
      throw new Error(`GEMINI_RATE_LIMIT:${resp.status}`);
    }
    throw new Error(`GEMINI_ERROR:${resp.status}`);
  }

  const reader = resp.body?.getReader();
  if (!reader) throw new Error("GEMINI_NO_BODY");
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (!payload) continue;
      try {
        const data = JSON.parse(payload);
        const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
        if (text) yield text;
      } catch {
        // ignora linha mal-formada
      }
    }
  }
}

async function* streamClaude(
  env: Env,
  systemPrompt: string,
  messages: ChatTurn[],
): AsyncGenerator<string, void, unknown> {
  const apiKey = env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error("ANTHROPIC_API_KEY missing");

  const claudeMessages = messages
    .filter((m) => m.role !== "system")
    .map((m) => ({ role: m.role, content: m.content }));

  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 500,
      system: systemPrompt,
      stream: true,
      messages: claudeMessages,
    }),
  });

  if (!resp.ok) throw new Error(`CLAUDE_ERROR:${resp.status}`);

  const reader = resp.body?.getReader();
  if (!reader) throw new Error("CLAUDE_NO_BODY");
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (!payload || payload === "[DONE]") continue;
      try {
        const data = JSON.parse(payload);
        if (data.type === "content_block_delta" && data.delta?.text) {
          yield data.delta.text;
        }
      } catch {
        // ignora
      }
    }
  }
}

export async function streamChat(
  env: Env,
  req: ChatRequest,
): Promise<{ stream: ReadableStream<Uint8Array>; provider: string }> {
  const systemPrompt = buildSystemPrompt(req.briefing, req.lpName);
  const encoder = new TextEncoder();
  let provider = "gemini";

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const tryProvider = async (
        gen: AsyncGenerator<string, void, unknown>,
        name: string,
      ): Promise<boolean> => {
        try {
          provider = name;
          for await (const chunk of gen) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text: chunk })}\n\n`));
          }
          return true;
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          console.error(`provider ${name} failed: ${msg}`);
          return false;
        }
      };

      // 1. tenta Gemini
      if (env.GEMINI_API_KEY) {
        const ok = await tryProvider(streamGemini(env, systemPrompt, req.messages), "gemini");
        if (ok) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ done: true, provider })}\n\n`));
          controller.close();
          return;
        }
      }

      // 2. fallback Claude
      if (env.ANTHROPIC_API_KEY) {
        const ok = await tryProvider(streamClaude(env, systemPrompt, req.messages), "claude");
        if (ok) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ done: true, provider })}\n\n`));
          controller.close();
          return;
        }
      }

      // 3. canned
      provider = "canned";
      const canned = CANNED_FALLBACK(req.fallbackContactUrl);
      controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text: canned })}\n\n`));
      controller.enqueue(encoder.encode(`data: ${JSON.stringify({ done: true, provider })}\n\n`));
      controller.close();
    },
  });

  return { stream, provider };
}
