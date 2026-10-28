const { ethers } = require("hardhat");

async function main() {
  const Vault = await ethers.getContractFactory("OlfactoVault");
  const vault = await Vault.deploy();
  await vault.waitForDeployment();
  console.log("OlfactoVault deployed to:", await vault.getAddress());
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});