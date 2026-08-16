# Web4Light — Whitepaper v0.1
## AsgardLab | Rebirth Phoenix Foundation Charter
**Autor:** Pan Jeskyně (Jakub Panocha)
**Datum:** Červen 2026
**GitHub:** https://github.com/Rebirth-Phoenix-Foundation-Charter/Karel_IV

---

## 1. Vize: Konec tokenizace

Stávající internet (Web3) je postavený na tokenizaci přístupu — platíš za každý krok, každý výpočet, každý přístup. Seed fráze, gas fees, trial periody, subscription s háčky.

**Web4 říká: dost.**

> "Zaplať měsíc. Používej neomezeně. Žádné zkušební období — buď máš nebo nemáš."

Web4Light je první implementace tohoto principu. Vakuová Mincovna je Článek #1.

---

## 2. Karel IV. — Real-time Voice Translator

**"Mluví všemi jazyky. Najednou."**

Karel IV. je pojmenován po Karlu IV. — prvním známém polyglotovi Čech, který mluvil 7 jazyky plynně (1316–1378).

### Co dělá
Vstoupíš do virtuální reality mluvíš česky. Ostatní tě slyší ve svém jazyce. Ve tvém vlastním hlase.

### Pipeline
```
Mikrofon
  → Virtuální zvukovka
  → Whisper STT (lokálně, MIT licence)
  → Ada/SPARK validace (formálně ověřeno)
  → Gemini AI překlad (Apache 2.0)
  → Coqui TTS — klon hlasu uživatele (MIT)
  → Sluchátka (real-time)
```

### Cenový model
| Plán | Cena | Obsah |
|------|------|-------|
| Osobní asistent | 111 Kč/měs | AI asistent, 1 zařízení |
| Karel IV. | 222 Kč/měs | Real-time překlad + klon hlasu |
| Stream Dabing | 333 Kč/měs | Netflix/YouTube dabing v reálném čase |
| **Rodinný plán** | **423 Kč/měs** | **Vše, celá domácnost** |

### Voice cloning
- Demo: hlas Jana Wericha (ikonický český herec)
- Produkce: uživatel nahraje 30s vlastního hlasu → překládá se jeho hlasem
- Engine: Coqui TTS (MIT) nebo ElevenLabs API

---

## 3. Ochranná vrstva (co uživatel nevidí)

Navenek vypadá Karel IV. jako jednoduchá appka. Uvnitř je formálně ověřený systém.

```
┌─────────────────────────────────────────────┐
│  UŽIVATEL vidí: Karel IV. aplikace          │
│  "Mluv česky → slyš tě v japonštině"        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  OCHRANNÁ VRSTVA (skrytá)                   │
│                                             │
│  Ada/SPARK + GNAT                           │
│  └─ formálně ověřený core                   │
│  └─ Standard 700 invarianty                 │
│  └─ "faucet nic" — nulová cloud spotřeba    │
│                                             │
│  Faucet SDN                                 │
│  └─ síťový přístup, P2P node registrace     │
│                                             │
│  Prometheus + Grafana                       │
│  └─ mapuje a řídí celý mesh                 │
│  └─ zdraví nodů, failover rozhodování       │
│                                             │
│  n8n                                        │
│  └─ orchestruje workflow na pozadí          │
│                                             │
│  Vakuová Mincovna + Sepolia ETH             │
│  └─ platební a identitní vrstva             │
└─────────────────────────────────────────────┘
```

---

## 4. Standard 700 — Matematická jistota

Základní invariant systému formálně ověřený Ada/SPARK:

```ada
-- 1 coin = 12g stříbra (Standard 700)
Pre  => Silver_Grams >= 0.0
Post => (if Silver_Grams < 12.0 then Result = 0 else Result > 0)
```

Ada/SPARK nezabraňuje chybám pomocí testů — matematicky **dokazuje** jejich nemožnost. Žádné runtime chyby, přetečení zásobníku, dělení nulou.

---

## 5. Digitální Identita — Soulbound NFT

### Princip: 1 člověk = 1 identita

Každý uživatel získá digitální identitu vázanou na biometrii:

```
Biometrie (hlas/tvář)
  → GNAT/Ada validace (lokálně)
  → Odvození klíče z biometrického hashe
  → Wallet adresa (blockchain, veřejná)
  → Soulbound NFT (nepřenosný, 1 na osobu)
```

### Klíčové vlastnosti
- **Bez seed fráze** — klíč odvozený z biometrie, uložen v hardware security chipu
- **Soulbound** = vstupenka do VR (nelze prodat, půjčit, ukrást, duplikovat)
- **KYC uvnitř** — jedině Mincovna (GNAT) zná vazbu biometrie ↔ wallet adresa
- **Display name** — volitelný, uživatel si řídí sám (skutečné jméno nebo přezdívka)
- **Anonymita** — blockchain vidí jen adresu a NFT, ne kdo za tím stojí

### Wallet ekosystém
- MetaMask, Coinbase Wallet — EVM/Ethereum
- 1inch, Uniswap — swap asterisk coinů
- Phantom, Solflare — Solana (levnější gas pro NFT mint)
- MiniMe token — asterisk coiny, subscription platby
- Sepolia testnet → Ethereum mainnet v produkci

---

## 6. Tržiště 1000 světů — Bezcelní zóna

### VR struktura

```
Metaverse světy
├── Lidské světy (vstup jen přes soulbound NFT)
│   └─ boti ZAKÁZÁNI — Mincovna ověří při vstupu
│
└── Tržiště 1000 světů (jediné místo kde smí být boti)
    └─ obchodní boti povoleni
    └─ SparkDog hlídá fair play
    └─ bezcelní zóna — žádné poplatky za transakce
```

### Obchodní boti
Obchodníci nemusí sedět v tržišti 24/7 — nasadí bota který prodává za ně:
- Každý bot vázán na obchodníka přes soulbound NFT
- Obchodník odpovídá za chování svého bota
- Bot překračuje pravidla → Faucet SDN ho vykopne
- Karel IV. překládá zákazníkům v jejich jazyce v reálném čase

### SparkDog protokol
SparkDog (Ada/SPARK watchdog) hlídá tržiště:
- Počet transakcí za sekundu (bot pattern detekce)
- Wash trading s asterisk coiny
- Manipulace cen
- Obtěžování zákazníků
- Rozhodnutí formálně ověřená → nelze najít softwarovou díru

### Bezcelní zóna
- Žádné poplatky za transakce mezi světy
- Obchodník z Japonska prodává do Čech → 0% poplatek
- Platba v asterisk coinech nebo ETH
- První skutečně globální tržiště bez hranic

---

## 7. Infrastruktura: Vakuová Mincovna

### High Availability
- **Primary Node** (port 9302) — hlavní uzel
- **Shadow Node** (port 9303) — záloha, automatický failover < 20s
- **Watchdog** (port 9304) — 5-level security scanner (Mossad ALF++ protokol)
- **Privacy Protocol 4:23** — denní purge metadata

### Prometheus řídí mesh
Prometheus není jen monitoring — aktivně řídí mechaniku:
```
Prometheus scrape → metriky ze všech nodů
  → Alertmanager detekuje problém
  → n8n webhook → akce
  → Faucet SDN přesměruje traffic na Shadow
  → Ada/SPARK validuje nový stav
```

### Deployment fáze
- **Fáze 1 (nyní):** Windows — Primary + Shadow na jednom stroji
- **Fáze 2:** Windows Primary + Ubuntu Shadow (distribuované)
- **Fáze 3:** Oba nody na Ubuntu v produkci

---

## 8. Tech Stack

| Vrstva | Technologie | Role |
|--------|-------------|------|
| Core | Ada/SPARK 2022 + GNAT | Formálně ověřená logika |
| Bridge | Python 3.8+ | HTTP, Prometheus export |
| Network | Erlang/OTP Faucet DNS | SDN access controller |
| Orchestrace | n8n (skrytý) | Workflow automation |
| Monitoring | Prometheus + Grafana | Mesh řízení + vizualizace |
| Překlad | Whisper + Gemini | STT + Translation |
| Hlas | Coqui TTS | Voice synthesis/cloning |
| Blockchain | Ethereum/Sepolia + Solana | Identity + payments |
| Smart contract | MiniMe ERC-20 | Asterisk coiny |

---

## 9. Ekonomický model

### Příjmy
- Subscriptions (111–423 Kč/měsíc)
- Dabing pro streamovací společnosti (Netflix, Disney+, HBO)
- Poplatky z tržiště 1000 světů

### Náklady
- Ada/SPARK: "faucet nic" — nulová cloud spotřeba
- Mesh síť: poháněna uživatelským hardwarem (5% idle CPU)
- Cíl: 100k$ Google startup kredit pokryje první rok

### Startup strategie
- MVP: funkční Karel IV. pipeline + demo hlasem Jana Wericha
- Google for Startups: Apache Spark/Ada architektura = silný argument
- Alternativa: Jensen Huang (Nvidia) — přístup k 150 000 tera výpočetnímu výkonu

---

## 10. Licence

**Duální licence:**
- GPL 3.0 — open-source a nekomerční použití
- Komerční licence — pro proprietární použití (kontakt: phoenix@asgardlab.eu)

---

## Příběhové linie (Stories)

### STORY_001: První článek
"Jakmile stojí první dokonalý článek, zbytek se staví sám." Vakuová Mincovna je Článek #1 Web4 ekosystému. Každý další článek dědí jeho matematickou stabilitu.

### STORY_002: Karel IV. v metaverse
Vstoupíš do VR schůzky. Mluvíš česky. Japonský kolega tě slyší japonsky — ve tvém vlastním hlase. Nikdo nic nenastavoval. Prostě to funguje.

### STORY_003: Obchodník bez hranic
Český řemeslník prodává ručně dělané šperky. Nasadí bota do tržiště 1000 světů. Bot prodává 24/7 zákazníkům z celého světa. Karel IV. překládá. SparkDog hlídá. Obchodník spí.

### STORY_004: Identita bez seed fráze
Uživatel přijde o telefon. Žádná panika. Jde k Mincovně, ověří hlas, dostane přístup zpět. Seed fráze neexistuje — biometrie je klíč.

### STORY_005: Autonomní systém
Prometheus detekuje výpadek Primary nodu. Za 18 sekund Shadow přebírá. Nikdo nic nedělal. Systém se opravil sám.

---

*Web4Light — Building the autonomous infrastructure of the next internet.*
*AsgardLab 2026*
