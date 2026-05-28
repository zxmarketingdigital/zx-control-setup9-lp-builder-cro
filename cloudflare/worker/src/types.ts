// types.ts — env bindings do Worker
export interface Env {
  // D1 binding (definido em wrangler.toml)
  DB: D1Database;

  // Secrets
  LP_TOKEN: string;
  GEMINI_API_KEY?: string;
  ANTHROPIC_API_KEY?: string;

  // Vars
  ENVIRONMENT?: string;
  DEFAULT_DAILY_LIMIT?: string;
}
