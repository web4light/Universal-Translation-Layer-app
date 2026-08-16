---
trigger: always_on
---

# Pravidla pro Agenta (Čeština & Ada/SPARK)

1. Komunikuj vždy kompletně v **češtině**.
2. Pro veškerý Ada/SPARK kód dodržuj zásady formální verifikace pro `gnatprove`.
3. Používej `pragma SPARK_Mode (On);`, ranged typy, inicializované záznamy a Pre/Post kontrakty.
4. Zákaz: `access`, `raise`, `new`, `Unchecked_*`, `goto`, `abort`.
