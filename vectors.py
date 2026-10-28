from pathlib import Path

import numpy as np
import pandas as pd

# 1. Load the local copy (no internet needed) and keep only molecules
#    with at least one odor label
DATA_FILE = Path(__file__).parent / "behavior_local.csv"
beh = pd.read_csv(DATA_FILE, index_col=0)
beh = beh[beh.sum(axis=1) > 0]
print("Molecules with at least one odor label:", len(beh))

rng = np.random.default_rng(42)  # fixed seed so results repeat


# 2. A formula is a dict: {molecule_id: percentage}
def make_formula(n=12):
    ids = rng.choice(beh.index.to_numpy(), size=n, replace=False)
    pct = rng.dirichlet(np.ones(n)) * 100      # random percentages adding to 100
    return {int(i): float(p) for i, p in zip(ids, pct)}


# 3. Formula -> odor vector (concentration-weighted sum)
def formula_to_vector(formula):
    vec = np.zeros(beh.shape[1])
    for mol_id, pct in formula.items():
        vec += (pct / 100) * beh.loc[mol_id].to_numpy()
    return vec


# 4. Clone: swap a few molecules, keep the same percentages
def make_clone(formula, swaps=3):
    clone = dict(formula)
    to_remove = rng.choice(list(clone.keys()), size=swaps, replace=False)
    for old in to_remove:
        pct = clone.pop(int(old))
        while True:
            new = int(rng.choice(beh.index.to_numpy()))
            if new not in clone and new not in formula:
                break
        clone[new] = pct
    return clone


# 5. Cosine similarity
def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


if __name__ == "__main__":
    original = make_formula()
    clone = make_clone(original, swaps=3)
    other = make_formula()

    v_orig = formula_to_vector(original)
    v_clone = formula_to_vector(clone)
    v_other = formula_to_vector(other)

    print("Original vs clone    :", round(cosine(v_orig, v_clone), 3))
    print("Original vs unrelated:", round(cosine(v_orig, v_other), 3))