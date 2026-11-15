/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
// Client copy of backend/app/engine/scoring.py combine_score(). Parity is tested in tests/test_parity.py.
export const CLIMATE_WEIGHT = 0.35;
export const PRIORITY_KEYS = ["resilience", "profit", "soil", "water"];
export const roundHalfUp = (x) => Math.floor(x + 0.5);

export function normalizePriorities(p) {
  const a = {};
  for (const k of PRIORITY_KEYS) a[k] = Math.max(0, Number(p?.[k] ?? 0) || 0);
  const total = PRIORITY_KEYS.reduce((s, k) => s + a[k], 0) || 1;
  for (const k of PRIORITY_KEYS) a[k] /= total;
  return a;
}

// A priority whose component is null (e.g. profit before any costed crop exists) is excluded and the rest renormalised.
export function combineScore(c, pr) {
  const map = [["resilience", "resilience"], ["water", "water_fit"], ["soil", "soil_and_rotation"], ["profit", "profit"]];
  let num = 0, den = 0;
  for (const [pk, ck] of map) {
    const v = c[ck], w = pr[pk] ?? 0;
    if (v === null || v === undefined || w <= 0) continue;
    num += w * v; den += w;
  }
  if (den <= 0) return Math.max(1, Math.min(99, roundHalfUp(c.climate)));
  return Math.max(1, Math.min(99, roundHalfUp(CLIMATE_WEIGHT * c.climate + (1 - CLIMATE_WEIGHT) * (num / den))));
}
