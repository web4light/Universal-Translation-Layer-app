---
name: spark-verifier
description: Ověří a dokáže Ada/SPARK kód pomocí nástroje gnatprove bez chyb
---
# SPARK Verifier Skill

Tento skill slouží k automatické formální verifikaci veškerého Ada/SPARK kódu v sandboxu.

## Postup při verifikaci:
1. Ujisti se, že soubory `.ads` a `.adb` jsou správně uloženy.
2. Spusť formální verifikaci:
   ```bash
   gnatprove -P default.gpr --level=2 --report=all
   ```
   nebo přímo na soubory:
   ```bash
   gnatprove -u <soubor>.adb --level=2 --report=all
   ```
3. Pokud `gnatprove` zahlásí chybu, nesplněný kontrakt (`VC`) nebo varování:
   - Identifikuj řádek a důvod selhání důkazu.
   - Doplň explicitní `Pre` a `Post` podmínky.
   - V případě potřeby uprav rozsah typů (`subtype`).
   - Opakuj běh, dokud `gnatprove` neprojde 100% čistě.
