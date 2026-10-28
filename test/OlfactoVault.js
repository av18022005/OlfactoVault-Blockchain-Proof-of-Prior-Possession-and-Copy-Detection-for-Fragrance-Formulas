const { expect } = require("chai");
const { ethers } = require("hardhat");
const fs = require("fs");

describe("OlfactoVault", function () {
  let vault, owner, other, attacker;

  const vector = [1200, 0, 530, 8700, 45];
  const salt = "0x" + "11".repeat(32);

  function commitmentOf(addr, vec, s) {
    return ethers.solidityPackedKeccak256(
      ["address", "uint256[]", "bytes32"], [addr, vec, s]);
  }

  beforeEach(async function () {
    [owner, other, attacker] = await ethers.getSigners();
    const Vault = await ethers.getContractFactory("OlfactoVault");
    vault = await Vault.deploy();
    await vault.waitForDeployment();
  });

  it("registers a commitment and stores owner and timestamp", async function () {
    const c = commitmentOf(owner.address, vector, salt);
    await vault.register(c);
    const [recOwner, ts] = await vault.getRecord(owner.address, c);
    expect(recOwner).to.equal(owner.address);
    expect(ts).to.be.gt(0);
  });

  it("rejects the same account registering a commitment twice", async function () {
    const c = commitmentOf(owner.address, vector, salt);
    await vault.register(c);
    await expect(vault.register(c)).to.be.revertedWith("Already registered");
  });

  it("rejects an empty commitment", async function () {
    await expect(vault.register(ethers.ZeroHash)).to.be.revertedWith("Empty commitment");
  });

  it("getRecord reverts for an unregistered commitment", async function () {
    await expect(vault.getRecord(owner.address, commitmentOf(owner.address, vector, salt)))
      .to.be.revertedWith("Not found");
  });

  it("accepts a correct reveal", async function () {
    await vault.register(commitmentOf(owner.address, vector, salt));
    const [ok, recOwner] = await vault.verifyReveal(owner.address, vector, salt);
    expect(ok).to.equal(true);
    expect(recOwner).to.equal(owner.address);
  });

  it("rejects a wrong vector", async function () {
    await vault.register(commitmentOf(owner.address, vector, salt));
    const [ok] = await vault.verifyReveal(owner.address, [1200, 0, 530, 8700, 46], salt);
    expect(ok).to.equal(false);
  });

  it("rejects a wrong salt", async function () {
    await vault.register(commitmentOf(owner.address, vector, salt));
    const [ok] = await vault.verifyReveal(owner.address, vector, "0x" + "22".repeat(32));
    expect(ok).to.equal(false);
  });

  it("verifyReveal is false when nothing is registered", async function () {
    const [ok] = await vault.verifyReveal(owner.address, vector, salt);
    expect(ok).to.equal(false);
  });

  it("FRONT-RUNNING: copying someone's commitment does not steal ownership", async function () {
    const victimCommit = commitmentOf(owner.address, vector, salt);

    // Attacker sees the hash in the mempool and registers it first
    await vault.connect(attacker).register(victimCommit);

    // The real owner can still register the same hash (no collision)
    await vault.register(victimCommit);

    // The real owner's reveal verifies, and shows the real owner
    const [ok, recOwner] = await vault.verifyReveal(owner.address, vector, salt);
    expect(ok).to.equal(true);
    expect(recOwner).to.equal(owner.address);

    // The attacker cannot reveal it as theirs: their address is not in the hash
    const [atkOk] = await vault.verifyReveal(attacker.address, vector, salt);
    expect(atkOk).to.equal(false);
  });

  it("only the owner can transfer ownership", async function () {
    const c = commitmentOf(owner.address, vector, salt);
    await vault.register(c);
    await expect(vault.connect(other).transferOwnership(c, other.address))
      .to.be.revertedWith("Not the owner");
    await vault.transferOwnership(c, other.address);
    const [newOwner] = await vault.getRecord(owner.address, c);
    expect(newOwner).to.equal(other.address);
  });

  it("Python hash matches Solidity hash (uses my_secret.json)", async function () {
    const secret = JSON.parse(fs.readFileSync("my_secret.json", "utf8"));
    // my_secret.json was made for Hardhat account #0, which is `owner` here
    expect(owner.address).to.equal(secret.owner);
    const jsHash = commitmentOf(secret.owner, secret.vector, secret.salt);
    expect(jsHash).to.equal(secret.commitment);
    await vault.register(secret.commitment);
    const [ok, recOwner] = await vault.verifyReveal(secret.owner, secret.vector, secret.salt);
    expect(ok).to.equal(true);
    expect(recOwner).to.equal(owner.address);
  });
});