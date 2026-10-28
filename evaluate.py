import secrets
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from commit import HARDHAT_ACCOUNT_0

from vectors import make_formula, make_clone, formula_to_vector, cosine
from commit import quantize, make_commitment

N = 300
SWAPS = [1, 2, 3, 4, 5, 6]


def qvec(f):
    return np.array(quantize(formula_to_vector(f)), dtype=float)


print("Generating formulas...")
originals = [make_formula() for _ in range(N)]
orig_vecs = [qvec(f) for f in originals]
unrel_vecs = [qvec(make_formula()) for _ in range(N)]

# Mean vector used for centering (computed from the pool, off-chain only)
mean_vec = np.mean(orig_vecs + unrel_vecs, axis=0)


def centered(a, b):
    return cosine(a - mean_vec, b - mean_vec)


rows = []
exact_hash_hits = 0
exact_hash_total = 0

for i, f in enumerate(originals):
    v = orig_vecs[i]
    salt = secrets.token_bytes(32)
    orig_commit = make_commitment(HARDHAT_ACCOUNT_0, quantize(formula_to_vector(f)), salt)

    # Unrelated pair
    u = unrel_vecs[i]
    rows.append(dict(kind="unrelated", swaps=0,
                     raw=cosine(v, u), centered=centered(v, u)))

    # Clones with 1..6 swaps
    for s in SWAPS:
        clone = make_clone(f, swaps=s)
        c_int = quantize(formula_to_vector(clone))
        c = np.array(c_int, dtype=float)
        rows.append(dict(kind="clone", swaps=s,
                         raw=cosine(v, c), centered=centered(v, c)))
        # Exact-hash baseline: would the clone's commitment equal the original's?
        exact_hash_total += 1
        if make_commitment(HARDHAT_ACCOUNT_0, c_int, salt) == orig_commit:
            exact_hash_hits += 1

df = pd.DataFrame(rows)
df.to_csv("results.csv", index=False)


def auc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    return float(((pos[:, None] > neg[None, :]).mean()
                  + 0.5 * (pos[:, None] == neg[None, :]).mean()))


def best_threshold(pos, neg):
    best = (None, -1, 0, 0)
    for t in np.linspace(0, 1, 1001):
        tpr = (pos >= t).mean()
        fpr = (neg >= t).mean()
        j = tpr - fpr
        if j > best[1]:
            best = (t, j, tpr, fpr)
    return best


clones = df[df.kind == "clone"]
unrel = df[df.kind == "unrelated"]

print("\n================ RESULTS ================")
for col in ["raw", "centered"]:
    pos, neg = clones[col].values, unrel[col].values
    t, j, tpr, fpr = best_threshold(pos, neg)
    print(f"\n--- {col.upper()} cosine ---")
    print(f"Unrelated: mean {neg.mean():.3f}, std {neg.std():.3f}, max {neg.max():.3f}")
    print(f"Clones (all swaps): mean {pos.mean():.3f}, min {pos.min():.3f}")
    print(f"AUC: {auc(pos, neg):.4f}")
    print(f"Best threshold: {t:.3f}")
    print(f"  Detection rate (clones flagged): {tpr*100:.1f}%  -> false negatives {(1-tpr)*100:.1f}%")
    print(f"  False positive rate (unrelated flagged): {fpr*100:.1f}%")
    print("  Per swap count (mean score | detection rate at threshold):")
    for s in SWAPS:
        x = clones[clones.swaps == s][col].values
        print(f"    {s} swaps: {x.mean():.3f} | {(x >= t).mean()*100:.1f}%")

print("\n--- EXACT-HASH BASELINE ---")
print(f"Clones caught by exact hash match: {exact_hash_hits} of {exact_hash_total}")

# Plots
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, col in zip(axes, ["raw", "centered"]):
    ax.hist(unrel[col], bins=40, alpha=0.6, label="Unrelated")
    ax.hist(clones[col], bins=40, alpha=0.6, label="Clones")
    ax.set_title(f"Score distribution ({col} cosine)")
    ax.set_xlabel("Similarity score")
    ax.set_ylabel("Count")
    ax.legend()
plt.tight_layout()
plt.savefig("score_distribution.png", dpi=150)

plt.figure(figsize=(7, 4))
data = [unrel["centered"]] + [clones[clones.swaps == s]["centered"] for s in SWAPS]
plt.boxplot(data, tick_labels=["Unrel"] + [str(s) for s in SWAPS])
plt.xlabel("Molecules swapped in clone")
plt.ylabel("Similarity (centered)")
plt.title("Similarity vs number of swaps")
plt.tight_layout()
plt.savefig("scores_by_swaps.png", dpi=150)

print("\nSaved: results.csv, score_distribution.png, scores_by_swaps.png")

np.save("mean_vec.npy", mean_vec)
print("Saved mean_vec.npy")