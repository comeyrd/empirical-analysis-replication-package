"""Statistical tools shared by both experiments.

- Paired comparison: two-sided Wilcoxon signed-rank test with the Hodges-Lehmann (HL) estimate of the
  paired difference and its distribution-free 95 % CI (Hollander & Wolfe), Holm correction.
- Guarantee: failure shares resampled by a workload bootstrap (multinomial weights per workload).
- Association: Spearman correlation with a workload-bootstrap CI.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

ALPHA = 0.05            # HL interval at 1 - ALPHA
EXACT_MAX_N = 50        # exact null distribution up to this n, normal approximation above
ROUND_DECIMALS = 10     # differences are rounded before ranking, so that exact ties stay ties


def holm(pvalues) -> np.ndarray:
    """Holm-adjusted p-values. NaN entries stay NaN and are left out of the family."""
    p = np.asarray(pvalues, dtype=float)
    out = np.full(p.shape, np.nan)
    ok = np.isfinite(p)
    m = int(ok.sum())
    if m == 0:
        return out
    q = p[ok]
    order = np.argsort(q)
    adjusted = np.minimum(1.0, np.maximum.accumulate((m - np.arange(m)) * q[order]))
    ranked = np.empty(m)
    ranked[order] = adjusted
    out[ok] = ranked
    return out


def _ci_rank(n: int, alpha: float = ALPHA) -> int:
    """1-based rank k of the lower HL bound among the n(n+1)/2 sorted Walsh averages (0: no interval)."""
    m = n * (n + 1) // 2
    if n <= EXACT_MAX_N:
        counts = np.zeros(m + 1)        # counts[s]: subsets of the ranks {1..n} summing to s
        counts[0] = 1.0
        for r in range(1, n + 1):
            counts[r:] = counts[r:] + counts[:-r]
        below = np.flatnonzero(np.cumsum(counts) / 2.0**n <= alpha / 2)
        return int(below[-1]) + 1 if below.size else 0
    z = stats.norm.ppf(1 - alpha / 2)
    return max(int(np.floor(m / 2 - z * np.sqrt(n * (n + 1) * (2 * n + 1) / 24))), 0)


def hodges_lehmann(d: np.ndarray, alpha: float = ALPHA) -> tuple[float, float, float]:
    """HL estimate (median of the Walsh averages) and its confidence interval."""
    n = d.size
    m = n * (n + 1) // 2
    walsh = np.empty(m)
    pos = 0
    for i in range(n):
        walsh[pos:pos + n - i] = (d[i] + d[i:]) / 2.0
        pos += n - i
    k = _ci_rank(n, alpha)
    mid = [(m - 1) // 2, m // 2]
    bounds = [k - 1, m - k] if k >= 1 else []
    walsh.partition(sorted(set(mid + bounds)))
    hl = float(0.5 * (walsh[mid[0]] + walsh[mid[1]]))
    if not bounds:
        return hl, np.nan, np.nan
    return hl, float(walsh[k - 1]), float(walsh[m - k])


def wilcoxon_hl(d) -> dict:
    """Two-sided Wilcoxon signed-rank test of median(d) = 0 (Pratt zeros), with HL [95 % CI] of d."""
    d = np.asarray(d, dtype=float)
    d = np.round(d[np.isfinite(d)], ROUND_DECIMALS)
    n = d.size
    nonzero = d[d != 0]
    out = {"n": n, "n_zero": n - nonzero.size,
           "share_pos": float(np.mean(d > 0) * 100.0) if n else np.nan,
           "share_neg": float(np.mean(d < 0) * 100.0) if n else np.nan,
           "statistic": np.nan, "p": np.nan, "hl": np.nan, "ci_low": np.nan, "ci_high": np.nan, "method": ""}
    if n == 0:
        return out
    out["hl"], out["ci_low"], out["ci_high"] = hodges_lehmann(d)
    if nonzero.size == 0:
        out.update(p=1.0, method="all zero")
        return out
    # The exact null distribution only holds without zeros or ties
    exact = nonzero.size == n and n <= EXACT_MAX_N and np.unique(np.abs(d)).size == n
    res = stats.wilcoxon(d, zero_method="pratt", method="exact" if exact else "approx")
    out.update(statistic=float(res.statistic), p=float(res.pvalue), method="exact" if exact else "normal")
    return out


def loo_drift(x) -> float:
    """Inter-campaign drift (thesis notation): mean over k of |x_k - mean of the others| / mean(x) x 100."""
    v = np.asarray(x, dtype=float)
    k = v.size
    if k < 2:
        return np.nan
    loo = (v.sum() - v) / (k - 1)
    mean = v.mean()
    return float(np.mean(np.abs(v - loo)) / mean * 100.0) if mean != 0 else np.nan


# --------------------------------------------------------------------------- #
# Workload bootstrap
# --------------------------------------------------------------------------- #
def bootstrap_weights(n_groups: int, n_replicates: int, rng: np.random.Generator) -> np.ndarray:
    """Multinomial weights (n_replicates, n_groups): how many times each group is drawn."""
    return rng.multinomial(n_groups, np.full(n_groups, 1.0 / n_groups), size=n_replicates).astype(float)


def weighted_share(weights: np.ndarray, hits: np.ndarray, counts: np.ndarray) -> np.ndarray:
    """Share (%) of hits on each replicate: hits (n_configs, n_groups) and counts (n_groups) per group."""
    return (weights @ hits.T) / (weights @ counts)[:, None] * 100.0


def resamples(groups: np.ndarray, weights: np.ndarray) -> list[np.ndarray]:
    """Row indices of each replicate: every group brings all its rows, as many times as it is drawn."""
    members = [np.flatnonzero(groups == i) for i in range(weights.shape[1])]
    return [np.concatenate([np.tile(members[i], int(c)) for i, c in enumerate(row) if c > 0]) for row in weights]


def spearman_boot(x, y, replicates: list[np.ndarray]) -> dict:
    """Spearman rho on the finite pairs, its p-value, and rho on each bootstrap replicate."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)

    def rho_of(ids: np.ndarray) -> float:
        keep = ids[ok[ids]]
        return float(stats.spearmanr(x[keep], y[keep])[0])

    rho, p = stats.spearmanr(x[ok], y[ok])
    reps = np.array([rho_of(ids) for ids in replicates])
    lo, hi = np.nanpercentile(reps, [2.5, 97.5])
    return {"n": int(ok.sum()), "rho": float(rho), "p": float(p), "ci_low": float(lo), "ci_high": float(hi), "reps": reps}


# --------------------------------------------------------------------------- #
# Summaries of curves over traces
# --------------------------------------------------------------------------- #
def tukey_summary(e: np.ndarray, low_floor: float | None = None) -> dict:
    """Per column of e (traces x points): median, Q25, Q75 and Tukey whiskers, the most extreme values
    within 1.5 IQR of the quartiles (the lower fence is raised to low_floor when given)."""
    q25, q75 = np.nanpercentile(e, 25, axis=0), np.nanpercentile(e, 75, axis=0)
    iqr = q75 - q25
    fence_low = q25 - 1.5 * iqr if low_floor is None else np.maximum(low_floor, q25 - 1.5 * iqr)
    w_high = np.max(np.where(~np.isnan(e) & (e <= (q75 + 1.5 * iqr)[None, :]), e, -np.inf), axis=0)
    w_low = np.min(np.where(~np.isnan(e) & (e >= fence_low[None, :]), e, np.inf), axis=0)
    return {"median": np.nanmedian(e, axis=0), "q25": q25, "q75": q75,
            "w_low": np.where(np.isposinf(w_low), q25, w_low), "w_high": np.where(np.isneginf(w_high), q75, w_high)}
