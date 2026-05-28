// rate-limit.ts — cap diário por (lp_config_id, endpoint) usando D1 usage_counters
import type { Env } from "./types";

function todayUTC(): string {
  return new Date().toISOString().slice(0, 10);  // YYYY-MM-DD
}

export interface UsageState {
  count: number;
  limit: number;
  remaining: number;
  exceeded: boolean;
}

export async function checkAndIncrement(
  env: Env,
  lpConfigId: string,
  endpoint: string,
  limit: number,
): Promise<UsageState> {
  const day = todayUTC();
  const row = await env.DB.prepare(
    "SELECT count FROM usage_counters WHERE lp_config_id = ? AND day = ? AND endpoint = ?",
  )
    .bind(lpConfigId, day, endpoint)
    .first<{ count: number }>();

  const current = row?.count ?? 0;
  if (current >= limit) {
    return { count: current, limit, remaining: 0, exceeded: true };
  }

  await env.DB.prepare(
    `INSERT INTO usage_counters (lp_config_id, day, endpoint, count)
     VALUES (?, ?, ?, 1)
     ON CONFLICT(lp_config_id, day, endpoint)
     DO UPDATE SET count = count + 1`,
  )
    .bind(lpConfigId, day, endpoint)
    .run();

  return {
    count: current + 1,
    limit,
    remaining: limit - current - 1,
    exceeded: false,
  };
}

export async function getUsage(
  env: Env,
  lpConfigId: string,
  limit: number,
): Promise<{ day: string; byEndpoint: Record<string, number>; limit: number }> {
  const day = todayUTC();
  const rows = await env.DB.prepare(
    "SELECT endpoint, count FROM usage_counters WHERE lp_config_id = ? AND day = ?",
  )
    .bind(lpConfigId, day)
    .all<{ endpoint: string; count: number }>();

  const byEndpoint: Record<string, number> = {};
  for (const r of rows.results ?? []) {
    byEndpoint[r.endpoint] = r.count;
  }
  return { day, byEndpoint, limit };
}
