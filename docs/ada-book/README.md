# 📚 Vakuová Mincovna - Kompletní Písemná Kniha (Ada/SPARK)

**Standard 700:** 12g stříbra = 1 mince  
**Autor:** Pan Jeskyně  
**Format:** Ada/SPARK (matematicky ověřený kód jako dokumentace)

---

## 🎯 Účel

Tato kniha je **kompletní dokumentace systému Vakuová Mincovna**, napsaná přímo v **Ada/SPARK**.

Každý soubor `.adb` je:
- 📖 **Kapitola knihy** (komentáře = teorie)
- 🔬 **Matematický důkaz** (SPARK anotace)
- ⚙️ **Funkční implementace** (spustitelný kód)
- ✅ **Testovací sada** (unit testy)

---

##human Kapitoly

| # | Soubor | Téma | Status |
|---|--------|------|--------|
| 01 | `01-foundation.adb` | Základy (Standard 700) | ✅ Připraveno |
| 02 | `02-architecture.adb` | Architektura systému | 📝 Čeká na tvůj obsah |
| 03 | `03-faucet.adb` | Faucet SDN | 📝 Čeká na tvůj obsah |
| 04 | `04-gemini-bridge.adb` | Gemini AI integrace | 📝 Čeká na tvůj obsah |
| 05 | `05-security.adb` | Bezpečnost (Mossad ALF++) | 📝 Čeká na tvůj obsah |
| 06 | `06-privacy.adb` | Privacy Protocol 4:23 | 📝 Čeká na tvůj obsah |
| 07 | `07-p2p-network.adb` | P2P síť (423 Kč/měsíc) | 📝 Čeká na tvůj obsah |
| 08 | `08-dubbing.adb` | Tartanskomunikátor | 📝 Čeká na tvůj obsah |
| 09 | `09-blockchain.adb` | Sepolia ETH integrace | 📝 Čeká na tvůj obsah |
| 10 | `10-autonomous.adb` | Autonomní vlastnosti | 📝 Čeká na tvůj obsah |

---

## 📖 Jak číst tuto knihu

### Pro lidi:
```bash
# Přečti kapitolu 1
cat 01-foundation.adb

# Kompiluj a spusť
gprbuild -P ../book.gpr
../bin/01-foundation
```

### Pro AI agenty (Gemini, Claude, atd.):
```python
# Načti všechny kapitoly
import glob
chapters = glob.glob("*.adb")
for chapter in sorted(chapters):
    with open(chapter) as f:
        content = f.read()
        # Parse komentáře (dokumentace)
        # Parse SPARK anotace (důkazy)
        # Parse kód (implementace)
```

---

## 🔨 Build systém

```bash
# Zkompiluj celou knihu
cd docs/ada-book
gprbuild -P book.gpr

# Formální verifikace
gnatprove -P book.gpr --level=4

# Spusť všechny kapitoly
for exe in bin/*; do
    echo "Running $exe..."
    $exe
done
```

---

## ✍️ Jak psát kapitoly

### Struktura kapitoly:

```ada
--  =========================================================================
--  Kapitola X: Název kapitoly
--  
--  Účel:
--    Vysvětlení, co tato kapitola učí.
--  
--  Klíčové koncepty:
--    1. První koncept
--    2. Druhý koncept
--  
--  Matematické záruky:
--    • Co je formálně dokázáno
--    • Jaké invarianty platí
--  =========================================================================

with Ada.Text_IO;

procedure Chapter_X with
   SPARK_Mode => On  -- Vždy zapnutá formální verifikace!
is
   --  Typy a konstanty
   type Moje_Data is ...;
   
   --  Funkce s Pre/Post conditions
   function Moje_Funkce (X : Natural) return Natural
      with
         Pre  => X >= 0,
         Post => Moje_Funkce'Result > X;
   
   --  Implementace
   function Moje_Funkce (X : Natural) return Natural is
   begin
      return X + 1;
   end Moje_Funkce;
   
begin
   Ada.Text_IO.Put_Line ("Kapitola X: Název");
   --  Demo kód
end Chapter_X;
```

---

## 📋 Checklist pro každou kapitolu

- [ ] Komentáře vysvětlují teorii
- [ ] SPARK_Mode => On
- [ ] Pre/Post conditions na funkcích
- [ ] Invarianty jsou dokumentované
- [ ] Kód kompiluje (`gprbuild`)
- [ ] Formální verifikace prochází (`gnatprove`)
- [ ] Demo v `begin .. end` bloku

---

## 🚀 Použití v GEALL

Gemini AI (a jiní agenti) čtou tuto knihu takto:

1. **Načtou všechny kapitoly** → pochopí celou architekturu
2. **Extrahují matematické důkazy** → vědí, co je garantováno
3. **Najdou vzory** → mohou replikovat podobný kód
4. **Vytvoří nový kód** → v souladu s knihou

**Výsledek:** Agent netvoří "něco", ale tvoří **matematicky ověřený kód podle tvé knihy**.

---

## 📂 Struktura složky

```
docs/ada-book/
├── README.md                   ← Tento soubor
├── book.gpr                    ← GNAT project file
├── 01-foundation.adb           ← Kapitola 1
├── 02-architecture.adb         ← Kapitola 2
├── 03-faucet.adb               ← Kapitola 3
├── ...                         ← Další kapitoly
└── bin/                        ← Zkompilované executables
```

---

**Standard 700:** 12g stříbra = 1 mince  
**Formát:** Ada/SPARK - matematicky ověřený  
**Licence:** GEALL (Gemini Enabled Agent License Library)

📚 **Tvoje kniha = Plná dokumentace pro AI agenty k tvorbě kódu!** 📚
