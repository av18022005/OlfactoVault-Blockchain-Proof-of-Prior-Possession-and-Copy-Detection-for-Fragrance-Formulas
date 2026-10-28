import json
import secrets
import numpy as np
from web3 import Web3
from vectors import make_formula, make_clone, formula_to_vector

# Hardhat's well-known test account #0 (public, holds no real value).
# Used only so the Hardhat test can reproduce Python's hash.
HARDHAT_ACCOUNT_0 = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


def quantize(vec):
    """Floats -> whole numbers (0..10000), so the hash is stable."""
    return [int(x) for x in np.round(vec * 10000)]


def make_commitment(owner, vec_int, salt):
    """keccak256(owner, vector, salt): matches Solidity
    abi.encodePacked(address, uint256[], bytes32)."""
    h = Web3.solidity_keccak(["address", "uint256[]", "bytes32"],
                             [Web3.to_checksum_address(owner), vec_int, salt])
    return Web3.to_hex(h)


if __name__ == "__main__":
    owner = HARDHAT_ACCOUNT_0
    formula = make_formula()
    vec = formula_to_vector(formula)
    vec_int = quantize(vec)

    salt = secrets.token_bytes(32)
    commitment = make_commitment(owner, vec_int, salt)
    print("Commitment:", commitment)

    print("Same input gives same hash:",
          make_commitment(owner, quantize(vec), salt) == commitment)
    print("Tiny noise gives same hash:",
          make_commitment(owner, quantize(vec + 1e-9), salt) == commitment)
    clone_int = quantize(formula_to_vector(make_clone(formula)))
    print("Clone gives different hash:",
          make_commitment(owner, clone_int, salt) != commitment)
    print("Different owner gives different hash:",
          make_commitment("0x45f2257eDf7B4006978B98f4d5B6870dDfE4AC35", vec_int, salt) != commitment)

    with open("my_secret.json", "w") as f:
        json.dump({"owner": owner, "vector": vec_int, "salt": Web3.to_hex(salt),
                   "commitment": commitment}, f)
    print("Saved my_secret.json")