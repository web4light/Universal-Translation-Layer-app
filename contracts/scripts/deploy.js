// Deploy Pražský Groš na Sepolia
// Standard 700: 1 GROŠ = 12g stříbra v ETH ekvivalentu
//
// Aktuální poměr (srpen 2026, přibližně):
// 1g stříbra ~ $1 → 12g = $12
// 1 ETH ~ $3000 → 1 Groš = 12/3000 = 0.004 ETH = 4000000000000000 wei
//
// Spuštění: npx hardhat run scripts/deploy.js --network sepolia

const hre = require("hardhat");

async function main() {
  // Poměr: kolik wei = 1 Groš (12g stříbra v ETH)
  // 12g stříbra ~ $12 ~ 0.004 ETH ~ 4e15 wei
  const weiPerGros = ethers.parseEther("0.004");
  
  console.log("=== RAŽBA PRAŽSKÉHO GROŠE ===");
  console.log("Standard 700: 1 GROŠ = 12g stříbra");
  console.log(`Wei per Groš: ${weiPerGros}`);
  console.log("");
  
  // Deploy contract
  const PrazskyGros = await hre.ethers.getContractFactory("PrazskyGros");
  const gros = await PrazskyGros.deploy(weiPerGros);
  await gros.waitForDeployment();
  
  const address = await gros.getAddress();
  console.log(`Pražský Groš deployed: ${address}`);
  console.log("");
  
  // Vyrazit prvních 1000 Grošů
  const mintAmount = ethers.parseEther("1000"); // 1000 GROŠ
  const requiredETH = ethers.parseEther("4"); // 1000 * 0.004 = 4 ETH
  
  console.log("Razím 1000 Grošů...");
  console.log(`Potřeba: ${ethers.formatEther(requiredETH)} ETH jako krytí`);
  
  const tx = await gros.mint(
    await (await hre.ethers.getSigners())[0].getAddress(),
    mintAmount,
    { value: requiredETH }
  );
  await tx.wait();
  
  console.log("✓ 1000 Grošů vyraženo!");
  console.log(`  Backing ratio: ${await gros.backingRatio()}%`);
  console.log(`  isFull: ${await gros.isFull()}`);
  console.log("");
  console.log("=== STARSCHAIN ŽIJE ===");
  console.log(`Contract: ${address}`);
  console.log("Hoc est via.");
}

main().catch(console.error);
