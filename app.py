import json
import os
import secrets
from datetime import datetime, timezone

import numpy as np
import streamlit as st
from dotenv import load_dotenv
from web3 import Web3

from vectors import make_formula, make_clone, formula_to_vector, cosine
from commit import quantize, make_commitment

load_dotenv()
MEAN_VEC = np.load("mean_vec.npy")
CONTRACT_ADDRESS = "0x37967107f022a75a25250f846dabB203C01a6Dd3"
STATE_FILE = "demo_state.json"
ABI = [
    {"name": "register", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "commitment", "type": "bytes32"}], "outputs": []},
    {"name": "getRecord", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "creator", "type": "address"}, {"name": "commitment", "type": "bytes32"}],
     "outputs": [{"name": "currentOwner", "type": "address"}, {"name": "timestamp", "type": "uint256"}]},
    {"name": "verifyReveal", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "creator", "type": "address"}, {"name": "vector", "type": "uint256[]"},
                {"name": "salt", "type": "bytes32"}],
     "outputs": [{"type": "bool"}, {"type": "address"}, {"type": "uint256"}]},
]

w3 = Web3(Web3.HTTPProvider(os.getenv("SEPOLIA_RPC_URL")))
account = w3.eth.account.from_key(os.getenv("PRIVATE_KEY"))
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return []


def save_state(records):
    with open(STATE_FILE, "w") as f:
        json.dump(records, f)


def send_register(commitment):
    tx = contract.functions.register(commitment).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "chainId": 11155111,
    })
    signed = account.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw)
    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    return Web3.to_hex(tx_hash)


def etherscan_tx(h):
    return f"https://sepolia.etherscan.io/tx/{h}"


st.set_page_config(page_title="OlfactoVault", page_icon="🧪")
st.title("🧪 OlfactoVault")
st.caption("Prove you owned a perfume formula first, without revealing it. (Sepolia test network)")

with st.sidebar:
    st.subheader("Connection")
    st.write("Connected:", w3.is_connected())
    st.write("Wallet:", account.address)
    st.write("Test ETH:", round(w3.from_wei(w3.eth.get_balance(account.address), "ether"), 4))
    st.markdown(f"[Contract on Etherscan](https://sepolia.etherscan.io/address/{CONTRACT_ADDRESS})")

records = load_state()
tab1, tab2, tab3 = st.tabs(["1. Register", "2. Investigate", "3. Duplicate test"])

# ---------------- TAB 1: REGISTER ----------------
with tab1:
    st.write("A sample formula is created and converted to an odor vector **on this laptop**. "
             "Only its salted hash (which includes the owner's address) goes to the blockchain.")
    if st.button("Create formula and register on-chain"):
        formula = make_formula()
        vec_int = quantize(formula_to_vector(formula))
        salt = secrets.token_bytes(32)
        commitment = make_commitment(account.address, vec_int, salt)
        with st.spinner("Sending transaction to Sepolia (15-30 seconds)..."):
            try:
                tx_hash = send_register(commitment)
            except Exception as e:
                st.error(f"Registration failed: {e}")
                st.stop()
        records.append({
            "formula": {str(k): v for k, v in formula.items()},
            "vector": vec_int,
            "salt": Web3.to_hex(salt),
            "commitment": commitment,
            "tx": tx_hash,
        })
        save_state(records)
        st.success("Registered!")
        st.write("**What goes on-chain (only this):**")
        st.code(commitment)
        st.markdown(f"[View transaction on Etherscan]({etherscan_tx(tx_hash)})")
        with st.expander("What stays private on my laptop"):
            st.write("Formula:", formula)
            st.write("Vector (first 10 numbers):", vec_int[:10])
    st.write(f"Registered formulas so far: **{len(records)}**")

# ---------------- TAB 2: INVESTIGATE ----------------
with tab2:
    if not records:
        st.info("Register a formula in tab 1 first.")
    else:
        idx = st.selectbox("My registered formula", range(len(records)),
                           format_func=lambda i: f"#{i + 1}  {records[i]['commitment'][:18]}...")
        rec = records[idx]
        kind = st.radio("Suspect perfume", ["Clone (a few molecules swapped)", "Unrelated perfume"])
        swaps = st.slider("Molecules swapped in the clone", 1, 6, 3) if kind.startswith("Clone") else 0
        threshold = st.slider("Copy threshold", 0.0, 0.9, 0.30, 0.01)

        if st.button("Reveal and compare"):
            # 1. Reveal to the contract: it recomputes keccak(owner, vector, salt) and checks it
            ok, owner, ts = contract.functions.verifyReveal(
                account.address, rec["vector"], rec["salt"]).call()
            if not ok:
                st.error("Reveal does NOT match any on-chain record.")
                st.stop()
            when = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            st.success("On-chain check passed: this vector was committed earlier.")
            st.write("Owner:", owner)
            st.write("Registered at:", when)

            # 2. Build the suspect and compare off-chain
            if kind.startswith("Clone"):
                original = {int(k): v for k, v in rec["formula"].items()}
                suspect = make_clone(original, swaps=swaps)
            else:
                suspect = make_formula()
            sus_vec = np.array(quantize(formula_to_vector(suspect)), dtype=float)
            score = cosine(np.array(rec["vector"], dtype=float) - MEAN_VEC, sus_vec - MEAN_VEC)

            st.metric("Similarity score", round(score, 3))
            if score >= threshold:
                st.error(f"FLAGGED: likely copy (score is at least {threshold}).")
            else:
                st.success(f"Not flagged (score is below {threshold}).")

# ---------------- TAB 3: DUPLICATE TEST ----------------
with tab3:
    st.write("Try to register an already-registered commitment. The contract should refuse.")
    if not records:
        st.info("Register a formula in tab 1 first.")
    elif st.button("Try to register the latest commitment again"):
        try:
            contract.functions.register(records[-1]["commitment"]).estimate_gas({"from": account.address})
            st.warning("Unexpected: it was accepted.")
        except Exception as e:
            st.success("Rejected by the smart contract, as expected.")
            st.code(str(e)[:300])