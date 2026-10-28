import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from vectors import beh, rng, make_formula, make_clone, formula_to_vector, cosine
from commit import quantize

N = 200          # number of original formulas
K = 5            # a substitute is picked among the K most similar-smelling molecules
SWAP_COUNTS = [3, 6, 9, 12]

MEAN_VEC = np.load("mean_vec.npy")

ids = beh.index.to_numpy()
M = beh.to_numpy(dtype=float)
Mn = M / np.linalg.norm(M, axis=1, keepdims=True)
id_to_row = {int(i): r for r, i in enumerate(ids)}


# ---------- clone generators ----------
def similar_swap_clone(formula, swaps):
    """Replace `swaps` molecules with similar-smelling ones (same percentages).
    Substitutes never come from the original formula, so with swaps=12
    the clone shares zero ingredients with the original."""
    clone = dict(formula)
    victims = rng.choice(list(clone.keys()), size=swaps, replace=False)
    for old in victims:
        old = int(old)
        pct = clone.pop(old)
        sims = Mn @ Mn[id_to_row[old]]
        pool = []
        for r in np.argsort(-sims):
            cand = int(ids[r])
            if cand != old and cand not in clone and cand not in formula:
                pool.append(cand)
                if len(pool) == K:
                    break
        clone[int(rng.choice(pool))] = pct
    return clone


def jitter_clone(formula, noise=0.3):
    """Same molecules, percentages changed by up to +/- noise."""
    keys = list(formula)
    pct = np.array([formula[k] for k in keys]) * rng.uniform(1 - noise, 1 + noise, len(keys))
    pct = pct / pct.sum() * 100
    return {k: float(p) for k, p in zip(keys, pct)}


# ---------- similarity methods ----------
def jaccard(f1, f2):
    a, b = set(f1), set(f2)
    return len(a & b) / len(a | b)


def qvec(f):
    return np.array(quantize(formula_to_vector(f)), dtype=float)


def odor_sim(f1, f2):
    return cosine(qvec(f1) - MEAN_VEC, qvec(f2) - MEAN_VEC)


METHODS = {"ingredient overlap": jaccard, "odor vector": odor_sim}


def auc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    return float((pos[:, None] > neg[None, :]).mean()
                 + 0.5 * (pos[:, None] == neg[None, :]).mean())


# ---------- run ----------
print("Generating formulas...")
originals = [make_formula() for _ in range(N)]
unrel = {m: np.array([fn(f, make_formula()) for f in originals]) for m, fn in METHODS.items()}
thresholds = {m: np.quantile(v, 0.95) for m, v in unrel.items()}   # 5% false positive rate

scenarios = [("random swap", make_clone, SWAP_COUNTS),
             ("odor-similar swap", similar_swap_clone, SWAP_COUNTS),
             ("concentration jitter", None, [0])]

rows = []
for name, gen, counts in scenarios:
    for s in counts:
        clones = [jitter_clone(f) if gen is None else gen(f, s) for f in originals]
        for m, fn in METHODS.items():
            scores = np.array([fn(f, c) for f, c in zip(originals, clones)])
            rows.append(dict(scenario=name, swaps=s, method=m,
                             mean_score=round(scores.mean(), 3),
                             AUC=round(auc(scores, unrel[m]), 3),
                             detect_at_5pct_FPR=round((scores > thresholds[m]).mean() * 100, 1)))

df = pd.DataFrame(rows)
df.to_csv("baseline_results.csv", index=False)
print("\n===== RESULTS (detection measured at 5% false positive rate) =====")
print(df.to_string(index=False))

fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for ax, name in zip(axes, ["random swap", "odor-similar swap"]):
    for m in METHODS:
        d = df[(df.scenario == name) & (df.method == m)]
        ax.plot(d.swaps, d.detect_at_5pct_FPR, marker="o", label=m)
    ax.set_title(name)
    ax.set_xlabel("Molecules replaced (of 12)")
    ax.set_ylabel("Clones detected (%) at 5% false positives")
    ax.legend()
plt.tight_layout()
plt.savefig("baseline_comparison.png", dpi=150)
print("\nSaved: baseline_results.csv, baseline_comparison.png") 