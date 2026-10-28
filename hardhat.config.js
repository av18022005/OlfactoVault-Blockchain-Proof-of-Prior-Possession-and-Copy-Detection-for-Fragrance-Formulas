require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const key = process.env.PRIVATE_KEY
  ? ["0x" + process.env.PRIVATE_KEY.replace(/^0x/, "")]
  : [];

module.exports = {
  solidity: "0.8.28",
  networks: {
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      accounts: key,
    },
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY,
  },
};