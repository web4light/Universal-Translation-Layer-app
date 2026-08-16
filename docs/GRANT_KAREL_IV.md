# Grant Application — Karel IV. Real-time Voice Translator

**Žadatel:** AsgardLab  
**Autor / Architekt:** Jakub Panocha (Pan Jeskyně)  
**Kontakt:** phoenix@web4light.online | arch@web4light.online  
**Web:** https://web4light.online  
**GitHub:** https://github.com/Rebirth-Phoenix-Foundation-Charter/Karel_IV  
**Datum:** 2026-07-11  

---

## 1. Shrnutí projektu (Executive Summary)

Karel IV. je real-time AI hlasový překladač, který uživateli umožní mluvit v češtině a být slyšen ve vlastním hlase v japonštině — bez latence, bez cloudové závislosti, bez tokenizace přístupu.

Projekt je pojmenován po Karlu IV., králi Čech, který plynně hovořil 7 jazyky. Cíl je stejný: **mluvit všemi jazyky. Najednou.**

Pipeline: `Mikrofon → Whisper STT → Ada/SPARK validace → Gemini překlad → Coqui TTS → Sluchátka`

---

## 2. Problém, který řešíme

### 2.1 Jazyková bariéra ve VR / metaverse

VR prostředí a globální online spolupráce narážejí na fundamentální problém: lidé mluví různými jazyky a dostupné překladače mají nevyhovující latenci (2–8 sekund), ztrácejí přirozený hlas mluvčího a jsou závislé na centrálním cloudu.

### 2.2 Tokenizace přístupu

Současné AI překladové služby fungují na modelu "pay per token" nebo "pay per minute" — uživatel nikdy přesně neví, kolik zaplatí, a nemá motivaci používat službu naplno. Každá minuta překladu stojí extra.

### 2.3 Centralizace a single point of failure

Všechny hlavní překladové služby (DeepL, Google Translate API, Azure Translator) jsou centralizované cloudy. Výpadek = žádný překlad. Cena = libovolná a měnitelná.

---

## 3. Řešení — Karel IV.

### 3.1 Technická architektura

```
Mikrofon
    ↓
Virtuální zvukovka (cross-platform)
    ↓
Whisper STT — lokální inference, MIT licence, nulové API náklady
    ↓
Ada/SPARK validace — formálně ověřená vstupní vrstva (žádné runtime chyby)
    ↓
Gemini AI překlad — Apache 2.0, free tier 1500 req/den
    ↓
Coqui TTS — klon hlasu uživatele, MIT licence, lokální běh
    ↓
Sluchátka
```

**Klíčové vlastnosti:**
- **Latence < 2s** end-to-end (Whisper base model na CPU)
- **Klon hlasu** — výstup zní jako samotný uživatel, ne syntetický robot
- **Lokální inference** — Whisper a Coqui TTS běží na hardware uživatele
- **9 jazyků** v první verzi: CS, EN, DE, FR, JA, ES, IT, PL, SK
- **Prometheus metriky** — každý překlad sledován, latence histogramem

### 3.2 Formální verifikace (Ada/SPARK)

Vstupní validační vrstva je napsána v jazyce Ada/SPARK 2022 s formální verifikací pomocí gnatprove. To garantuje:
- Žádné runtime chyby (overflow, null pointer, out of bounds)
- Matematicky ověřené Pre/Post podmínky
- SPARK Mode On na všech bezpečnostně relevantních procedurách

### 3.3 Infrastruktura — Vakuová Mincovna

Karel IV. běží na decentralizované infrastruktuře Vakuová Mincovna:
- **Primary Node** — hlavní uzel (Faucet Bridge, Prometheus port 9302)
- **Shadow Node** — záložní uzel s automatickým failoverem (< 25s)
- **Watchdog** — 5-úrovňový bezpečnostní scanner
- **Privacy Purge** — denní mazání metadat (GDPR)
- **Faucet SDN** — síťová vrstva, Erlang/OTP gen_server

Uživatelský hardware přispívá idle CPU/GPU do meshe → snižuje provozní náklady → snižuje cenu předplatného.

---

## 4. Obchodní model

### 4.1 Filosofie: Konec tokenizace

> "Zaplať měsíc, používej neomezeně. Žádné zkušební období — buď máš nebo nemáš."

### 4.2 Cenový model

| Plán | Cena | Obsah |
|------|------|-------|
| Osobní asistent | 111 Kč/měs | AI asistent, 1 zařízení |
| Karel IV. | 222 Kč/měs | Real-time překlad, klon hlasu |
| Stream Dabing | 333 Kč/měs | Netflix/YouTube dabing v reálném čase |
| **Rodinný plán** | **423 Kč/měs** | **Vše, celá domácnost** |

### 4.3 Cílové trhy

**Primární:**
- VR / metaverse uživatelé (gaming, business meetings, vzdělávání)
- Čeští expati a diaspory (komunikace s rodinou v zahraničí)
- Cestovní ruch a hospitality sektor

**Sekundární:**
- Streamers a content creators (real-time dabing)
- Korporátní zákazníci (mezinárodní porady)
- Zdravotnictví (komunikace s cizinci)

### 4.4 Projekce příjmů (rok 1)

| Segment | Uživatelé | Průměrný plán | Měsíční příjem |
|---------|-----------|---------------|----------------|
| Early adopters (Q3 2026) | 50 | 222 Kč | 11 100 Kč |
| Organický růst (Q4 2026) | 200 | 222 Kč | 44 400 Kč |
| Rok 1 (celkem) | 500 | 250 Kč | 125 000 Kč/měs |

Break-even: ~300 platících uživatelů při rodinném plánu.

---

## 5. Technologický stack a open-source základ

| Komponenta | Technologie | Licence | Náklady |
|-----------|-------------|---------|---------|
| STT | OpenAI Whisper | MIT | Zdarma |
| Překlad | Google Gemini 1.5 Flash | Apache 2.0 | Free tier / minimální |
| TTS + Voice clone | Coqui XTTS v2 | MIT | Zdarma |
| Validace | Ada/SPARK + GNAT | GPL-2.0 | Zdarma (GNAT Community) |
| Monitoring | Prometheus + Grafana | Apache 2.0 | Zdarma |
| Orchestrace | n8n | Sustainable Use | Self-hosted zdarma |
| Síť | Faucet SDN (Erlang) | Apache 2.0 | Zdarma |

**Celkové náklady na infrastrukturu při < 500 uživatelích: < 500 Kč/měs** (elektřina + doména).

---

## 6. Tým

### Jakub Panocha — Architekt / Zakladatel

- Celý systém navržen a implementován jako sole developer
- Ada/SPARK formální verifikace, Python pipeline, Erlang SDN, DevOps
- Filosofie: "Faucet nic" — nulová spotřeba externích zdrojů kde to jde

### Plánované rozšíření týmu (při grant funding)

| Role | Čas | Zaměření |
|------|-----|---------|
| ML Engineer | 0.5 FTE | Optimalizace Whisper latence, fine-tuning |
| Frontend Dev | 0.5 FTE | Electron/Web appka pro end-uživatele |
| DevOps | 0.25 FTE | Ubuntu produkční deployment, CI/CD |

---

## 7. Současný stav (Milestones)

### ✅ Milestone 1 — Hotovo

- Ada/SPARK Core (mincovna.adb) — formálně ověřen, Standard 700
- Karel IV. pipeline (karel_iv.py) — kompletní implementace
- Shadow Node + automatický failover (< 25s)
- Prometheus monitoring (porty 9302–9306)
- Faucet DNS (Erlang gen_server)
- Docker deployment (docker-compose.yml)
- Kompletní dokumentace (13 dokumentů)

### ✅ Milestone 1b — Proof of Concept (ověřeno)

- **Real-time překlad funguje** na standardním gaming PC (i7 12th gen, RTX 3070, 16GB RAM)
- Latence pod 2s end-to-end na hardware dostupném běžnému uživateli
- Potvrzuje mesh model — každý gaming PC v síti přispívá reálným výkonem
- GPU není podmínkou — CPU mode funkční, GPU pouze urychluje

### ⏳ Milestone 2 — Testování (aktuálně)

- Lokální Windows testing (Primary + Shadow)
- Failover testy (cíl: < 25s)
- End-to-end překladový test (CS → EN → JA)

### 📋 Milestone 3 — Produkce (s grant podporou)

- Ubuntu deployment (Primary na i5 Fujitsu, Shadow na i7)
- Voice cloning fine-tuning (30s sample → přirozený hlas)
- Web appka (Electron) pro end-uživatele
- Blockchain integrace (Sepolia testnet → mainnet)
- Beta program (50 uživatelů)

---

## 8. Infrastrukturní strategie — EW=M3

### Rovnice růstu

**EW = M3** — Earnings from Web4 = Google Cloud M3 instance

Cíl: příjmy z Karel IV. pokryjí provoz produkčního serveru. Do té doby platí grant.

### Fáze 1 (rok 1) — Grant platí cloud

Grant pokryje provoz **Google Cloud M3 megamem** instance po dobu 1 roku:
- M3 = paměťově optimalizovaná instance, stovky GB RAM, bez GPU
- Whisper STT, Coqui TTS i orchestrace běží čistě na CPU — GPU není potřeba
- M3 slouží jako **showcase** — dokonalé prostředí pro první uživatelskou zkušenost
- Nulová latence při prvním použití → uživatel platí → mesh roste

### Fáze 2 (rok 2) — Mesh přebírá zátěž

Každý platící uživatel přispívá svým idle CPU/RAM do peer-to-peer meshe:

```
Klasický SaaS:  uživatelé ↑ → náklady ↑ → cena ↑
Web4 mesh:      uživatelé ↑ → náklady ↓ → cena stejná nebo klesá
```

- Whisper inference → distribuovaná na zařízeních uživatelů (lokální běh)
- Coqui TTS → běží lokálně na hardware uživatele
- M3 řeší jen orchestraci a koordinaci meshe — ne samotnou inferenci
- Provozní náklady klesají s každým novým uživatelem

### Fáze 3 (rok 2–3) — Vlastní rack přebírá

Vlastní fyzická infrastruktura **již existuje a běží**:

**Hardware:**
- Fujitsu Primergy TX300 S4 — enterprise server (Primary Node)
- Fujitsu Primergy RX série — Server01 + Server02 (Shadow + compute)
- Síťový rack s patch panelem, firewall, switch
- UPS záložní napájení

**Energetická nezávislost:**
- **Doma:** 24 × 550W solárních panelů = 13,2 kWp + LEDVANCE bateriové úložiště
- **V práci:** 24 × 550W solárních panelů = 13,2 kWp
- **Celkem: 26,4 kWp** vlastní solární energie
- Průměrná produkce: 100+ kWh/den (léto)
- Provozní náklady na elektřinu: **0 Kč**

**Srovnání s cloudem:**
```
Google Cloud M3:   ~240 000 Kč/rok + závislost na Googlu
Vlastní rack:      0 Kč/rok provoz + enterprise Fujitsu hardware
```

GCP M3 slouží pouze jako **dočasný showcase** v roce 1 — pro dokonalý první dojem nových uživatelů. Od roku 2 vlastní rack přebírá orchestraci, GCP zůstane jako záloha při špičkách.

### Financování — žádní investoři

Projekt je záměrně budován bez externího investičního kapitálu:
- Grant = startovní palivo pro GCP showcase rok 1
- Příjmy z předplatného = vývoj + tým
- Vlastní solární hardware = provozní náklady nula navždy

> "Faucet nic" není jen filosofie — je to fyzicky postavená realita.

---

## 9. Využití grantu

### Celková žádost: 500 000 Kč

| Položka | Částka | Popis |
|---------|--------|-------|
| Google Cloud M3 (rok 1) | 240 000 Kč | Produkční showcase instance, ~20 000 Kč/měs |
| Vývoj (ML + Frontend) | 160 000 Kč | 6 měsíců, optimalizace pipeline + appka |
| Marketing a beta program | 60 000 Kč | 50 beta uživatelů, content, PR |
| Právní (IP, licence, GDPR) | 30 000 Kč | Duální licence, ochrana IP, GDPR audit |
| Rezerva | 10 000 Kč | Nepředvídané náklady |

### Alternativní výše grantu

| Výše | Dosažitelný cíl |
|------|----------------|
| 150 000 Kč | GCP rozjezd (6 měsíců) + 50 beta uživatelů |
| 300 000 Kč | GCP rok + appka + 200 uživatelů + voice clone |
| 500 000 Kč | Kompletní Fáze 1 + 2 — mesh ekonomika v provozu |

---

## 9. Rizika a mitigace

| Riziko | Pravděpodobnost | Dopad | Mitigace |
|--------|----------------|-------|---------|
| Gemini API změna cen | Střední | Střední | Modulární architektura — swap na jiný LLM |
| Whisper latence > 2s na slabém HW | Vysoká | Střední | tiny model pro slabý HW, base/small pro střední |
| GDPR compliance | Nízká | Vysoký | Privacy Purge modul již implementován |
| Konkurence (Google, Microsoft) | Vysoká | Nízký | Niche (VR, klon hlasu, flat-rate) + open-source základ |
| Single developer bus factor | Vysoká | Vysoký | Dokumentace kompletní, kód otevřený, grant = tým |

---

## 10. Diferenciace od konkurence

| Funkce | Karel IV. | Google Translate | DeepL | Microsoft Translator |
|--------|-----------|-----------------|-------|---------------------|
| Real-time (< 2s) | ✅ | ❌ (> 3s) | ❌ | ❌ |
| Klon vlastního hlasu | ✅ | ❌ | ❌ | ❌ |
| Flat-rate (bez tokenizace) | ✅ | ❌ | ❌ | ❌ |
| Lokální inference | ✅ | ❌ | ❌ | ❌ |
| Formální verifikace | ✅ | ❌ | ❌ | ❌ |
| Open-source základ | ✅ | ❌ | ❌ | ❌ |
| VR/metaverse ready | ✅ | ❌ | ❌ | ❌ |

---

## 11. Vize — Web4

Karel IV. je první produkt ekosystému Web4:

> Web4 = konec závislosti na centrálních cloudech, konec tokenizace přístupu, autonomní síť poháněná uživatelským hardwarem.

Další produkty v pipelineu:
- **Tržiště 1000 světů** — VR metaverse s bezcelní zónou, soulbound NFT identitou
- **SparkDog** — formálně ověřený fair-play monitor pro VR boty
- **Digitální identita** — biometrie → wallet bez seed fráze → soulbound NFT

Karel IV. je vstupní bod. Každý uživatel Karla IV. je potenciální občan Tržiště 1000 světů.

---

## 12. Kontakt a přílohy

**Jakub Panocha (Pan Jeskyně)**  
Architekt, AsgardLab  
phoenix@web4light.online  
arch@web4light.online  
https://web4light.online  
https://github.com/Rebirth-Phoenix-Foundation-Charter/Karel_IV  

**Přílohy (k dispozici na vyžádání):**
- Zdrojový kód (GitHub)
- SYSTEM_OVERVIEW.md — kompletní technická architektura
- TESTING_GUIDE.md — testovací plán (10 testů)
- docker/docker-compose.yml — deployment konfigurace
- prometheus/prometheus.yml — monitoring konfigurace

---

*Karel IV. — Named after the king who spoke 7 languages. Built for everyone.*

*Standard 700: 12g stříbra = 1 mince. Matematicky ověřeno Ada/SPARK.*
