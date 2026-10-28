# OlfactoVault-Blockchain-Proof-of-Prior-Possession-and-Copy-Detection-for-Fragrance-Formulas
Blockchain system that proves who held a perfume formula first, without publishing it. Salted, owner-bound hash of an odor vector is timestamped on Ethereum (Sepolia). Near-copies are flagged by odor-vector similarity. Solidity, Hardhat, Python, Streamlit.

## How it works

1. **Convert.** A formula (molecules and percentages) becomes a 113-number odor vector, using labels from the public Leffingwell dataset (via Pyrfume).
2. **Lock.** The vector is quantized to integers and hashed with a random salt and the owner's address: `keccak256(owner, vector, salt)`.
3. **Timestamp.** Only that hash goes on the Sepolia test blockchain. The formula never leaves the owner's computer.
4. **Compare.** In a dispute, the owner reveals the vector and salt. The contract recomputes the hash and confirms the record. Similarity to the suspect perfume is then computed off-chain (centered cosine similarity).

Front-running defence: the owner's address is inside the hash and records are stored per creator, so a copied hash cannot block the creator or verify as the attacker's.

## Project structure

| File | Purpose |
|---|---|
| `contracts/OlfactoVault.sol` | Smart contract (register, getRecord, verifyReveal, transferOwnership) |
| `test/` | Hardhat tests (11), including the front-running test and a Python/Solidity hash match |
| `vectors.py` | Formula to odor vector, clone and unrelated formula generators |
| `commit.py` | Quantization and commitment hash (generates `my_secret.json`) |
| `evaluate.py` | Evaluation: score distributions, threshold, exact-hash baseline |
| `app.py` | Streamlit demo (Register, Investigate, Duplicate test) |
| `scripts/deploy.js` | Deployment script |

## Setup

Requirements: Python 3.10+, Node.js (LTS), a Sepolia RPC URL, a test-only wallet funded from a Sepolia faucet.

```
python -m venv venv
venv\Scripts\activate
pip install pyrfume numpy pandas web3 streamlit matplotlib python-dotenv
npm install
```

1. Copy `.env.example` to `.env` and fill in your values.
2. Download the dataset once (needs internet):
   ```
   python -c "import pyrfume; df = pyrfume.load_data('leffingwell/behavior.csv'); df.to_csv('behavior_local.csv'); print(df.shape)"
   ```
   This should print `(3522, 113)`.
3. Generate the secret used by the cross-language test: `python commit.py`
4. If you deploy your own contract, run `npx hardhat run scripts/deploy.js --network sepolia` and put the printed address in `CONTRACT_ADDRESS` in `app.py`.

## Run

```
npx hardhat test          # 11 tests
python evaluate.py        # evaluation, saves results.csv, PNG plots, mean_vec.npy
streamlit run app.py      # demo at http://localhost:8501
```

## Results (synthetic formulas, 300 originals)

| | Centered cosine |
|---|---|
| AUC | 0.975 |
| Threshold (chosen from data) | 0.288 |
| Clones detected | about 90% |
| False positive rate | 4% |
| Exact-hash matching | 0 of 1800 clones caught |

Detection falls as more molecules are swapped: about 99% at 1 swap, about 76% at 6.

Deployed on Sepolia: `0x37967107f022a75a25250f846dabB203C01a6Dd3`

## Limitations

- Formulas are synthetic. Real commercial perfumes are trade secrets and were not available, and real competitors in the same category share notes, so false positives may be higher.
- The blockchain proves when a hash was registered, not who invented the formula.
- A similarity score is evidence, not legal proof.
- Revealing the vector to an arbiter exposes the odor profile. A zero-knowledge similarity proof is the planned extension.
- Sepolia is a test network, and the demo signs with a test key instead of a MetaMask confirmation.

## Related work

Blockchain registration of obfuscated trade secrets with similarity matching appears in existing patents (for example US 12148058 B2), and zero-knowledge similarity proofs exist in biometrics. This project applies the approach to molecular fragrance formulas, with an owner-bound commitment and a measured evaluation. It makes no patentability claim.

## Security

Never commit `.env`. Use a throwaway test wallet with no real funds.
