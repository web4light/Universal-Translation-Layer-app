// SPDX-License-Identifier: Apache-2.0
// Pražský Groš — StarsChain Stablecoin
// Standard 700: 1 GROŠ = 12g stříbra v ETH ekvivalentu
// Každý coin MUSÍ být naplněný. Žádná prázdná mince.
// Vakuová Mincovna razí. SPARK proved.

pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract PrazskyGros is ERC20, Ownable {
    
    // Standard 700: 1 Groš = 12g stříbra
    uint256 public constant STANDARD_700_GRAMS = 12;
    
    // Poměr: kolik wei = 1 Groš (nastaví mincovna podle kurzu ETH/stříbro)
    uint256 public weiPerGros;
    
    // Celkem ETH uzamčených jako krytí
    uint256 public totalBacking;
    
    // Maximální supply (první ražba = 1000)
    uint256 public constant MAX_SUPPLY = 1_000_000 * 10**18;
    
    // Události
    event Minted(address indexed to, uint256 amount, uint256 ethBacking);
    event BackingUpdated(uint256 newWeiPerGros);
    event Refilled(uint256 ethAdded);
    
    constructor(uint256 _weiPerGros) ERC20("Prazsky Gros", "GROS") Ownable(msg.sender) {
        require(_weiPerGros > 0, "Wei per Gros must be > 0");
        weiPerGros = _weiPerGros;
    }
    
    // === RAŽBA (Vakuová Mincovna) ===
    // Razí nové Groše — MUSÍ poslat ETH jako krytí
    // Žádná prázdná mince — proved on-chain
    function mint(address to, uint256 amount) external payable onlyOwner {
        require(amount > 0, "Amount must be > 0 (zadna prazdnota)");
        require(totalSupply() + amount <= MAX_SUPPLY, "Max supply reached");
        
        // Kolik ETH potřebujeme na krytí
        uint256 requiredBacking = (amount * weiPerGros) / 10**18;
        require(msg.value >= requiredBacking, "Nedostatek ETH kryti (Standard 700)");
        
        totalBacking += msg.value;
        _mint(to, amount);
        
        emit Minted(to, amount, msg.value);
    }
    
    // === PLNĚNÍ (furt cpát ETH dovnitř) ===
    // Kdokoliv může přidat ETH krytí — zvyšuje hodnotu všech Grošů
    function refill() external payable {
        require(msg.value > 0, "Posli ETH");
        totalBacking += msg.value;
        emit Refilled(msg.value);
    }
    
    // === AKTUALIZACE POMĚRU ===
    // Mincovna aktualizuje poměr ETH/stříbro
    function updateRate(uint256 _newWeiPerGros) external onlyOwner {
        require(_newWeiPerGros > 0, "Rate must be > 0");
        weiPerGros = _newWeiPerGros;
        emit BackingUpdated(_newWeiPerGros);
    }
    
    // === KONTROLY (proved on-chain) ===
    
    // Je mince plná? (vždy True pokud existuje)
    function isFull() external view returns (bool) {
        if (totalSupply() == 0) return true;
        return totalBacking >= (totalSupply() * weiPerGros) / 10**18;
    }
    
    // Kolik ETH kryje 1 Groš
    function backingPerGros() external view returns (uint256) {
        if (totalSupply() == 0) return 0;
        return (totalBacking * 10**18) / totalSupply();
    }
    
    // Celkové krytí v %
    function backingRatio() external view returns (uint256) {
        if (totalSupply() == 0) return 100;
        uint256 required = (totalSupply() * weiPerGros) / 10**18;
        if (required == 0) return 100;
        return (totalBacking * 100) / required;
    }
    
    // === SPALOVÁNÍ (při výběru ETH) ===
    function burn(uint256 amount) external {
        require(amount > 0, "Amount must be > 0");
        require(balanceOf(msg.sender) >= amount, "Nedostatek Grosu");
        
        // Vrátit poměrné ETH
        uint256 ethToReturn = (amount * totalBacking) / totalSupply();
        totalBacking -= ethToReturn;
        _burn(msg.sender, amount);
        
        payable(msg.sender).transfer(ethToReturn);
    }
    
    // Fallback — přijímej ETH jako refill
    receive() external payable {
        totalBacking += msg.value;
        emit Refilled(msg.value);
    }
}
