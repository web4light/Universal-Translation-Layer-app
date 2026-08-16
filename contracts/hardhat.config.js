require("@nomicfoundation/hardhat-toolbox");

const SEPOLIA_RPC = "https://rpc.sepolia.org";
// Private key — NIKDY NECOMMITOVAT! Použij env var.
const PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY || "0x0000000000000000000000000000000000000000000000000000000000000001";

module.exports = {
  solidity: "0.8.20",
  networks: {
    sepolia: {
      url: SEPOLIA_RPC,
      accounts: [PRIVATE_KEY],
    },
    hardhat: {
      chainId: 31337,
    },
  },
};
