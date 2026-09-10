// ============================================================
//  Asterisk (*) — Sovereign AI Studio & In-Memory Asistent
//  Běží v RAM (Zero-Trace, 0 bajtů zápis na disk)
// ============================================================

document.addEventListener('DOMContentLoaded', () => {

  // ------------------------------------------------------------
  // 1. SPRÁVA ZÁLOŽEK
  // ------------------------------------------------------------
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.dataset.tab;
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add('active');
      }
    });
  });

  // ------------------------------------------------------------
  // 2. SOVEREIGN KNOWLEDGE BASE (KOMPLETNÍ KONTEXT V RAM)
  // ------------------------------------------------------------
  const SOVEREIGN_CONTEXT = {
    creator: "Pan Jeskyně / Asgard (web4light)",
    system: "Asterisk (*) — Suverénní WebMCP Mesh Platforma",
    companion: "Obelix — Heavyweight Compute Node v Dockeru (port 8423, SPARK vault)",
    frontend: "Asterisk Chrome Extension (Manifest V3, 3D znakový avatar, Spark TTS)",
    rules: "Ada/SPARK 2022 level 4 proof, žádný heap (new/Free), žádné výjimky (raise), pouze ranged types, Pre/Post kontrakty",
    privacy: "SPARKdog Guardian s GNATem — likvidace cizích šmíráků, telemetrie a Velkého Bratra. Hermetický štít.",
    self_healing: "Samo-oprava za chodu (In-Vivo Hot-Patching) — okamžité zacelení paměťových stavů za 0.1 ms bez nutnosti restartu a bez pádů.",
    pjay: "Protokol PJAY 4.23 / Standard 700 (Hoc est via, Locutus sum, Ego sum Groot).",
    energy: "Solární Genesis — 100% napájení ze slunce a bateriového úložiště, nulové idle náklady ($0 idle cost).",
    impact: "100% Free pro 500 milionů neslyšících a nevidomých lidí. Komerční flat-rate $111/měsíc.",
    memory: "100% In-Memory RAM Only, Zero-Trace. Ash Sweeper provádí skartaci v 04:23 UTC.",
    devpost: "5 Devpost výzev 2026: WebMCP Sovereign Mesh, A11y 500M Voices, Agentic Komenský, Solar AI, Multimodal 3D Avatar.",
    network_switch: "Propojení přes switch: LAN IP 191.168.123.192 (Obelix uzel na Ubuntu) <-> Windows PC. Porty: 3000 (Avatar), 8088/8085 (Studio), 8423 (Obelix SPARK)."
  };

  // ------------------------------------------------------------
  // 3. IN-MEMORY CHAT ASISTENT
  // ------------------------------------------------------------
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chips = document.querySelectorAll('.chip');

  // Paměť konverzace výhradně v RAM (žádný disk)
  const memoryChatLog = [];

  function appendMessage(text, isUser = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `msg ${isUser ? 'msg-user' : 'msg-bot'}`;
    
    if (isUser) {
      msgDiv.textContent = text;
    } else {
      msgDiv.innerHTML = text;
    }

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    memoryChatLog.push({ role: isUser ? 'user' : 'assistant', text, time: Date.now() });
  }

  function generateSovereignResponse(query) {
    const q = query.toLowerCase();

    // 1. Samo-oprava za chodu
    if (q.includes('samo-oprav') || q.includes('opravovat za chodu') || q.includes('self-heal') || q.includes('hot-patch') || q.includes('regenerace')) {
      return `🩹 <strong>Samo-oprava za chodu (In-Vivo Hot-Patching):</strong><br>
Náš systém se nikdy nezhroutí! Když útočník pošle poškozená data nebo dojde k anomálii, <code>SPARKdog_Guardian</code> zavolá proceduru:
<pre>procedure Self_Heal_Runtime_State
  (State          : in out SPARKdog_State;
   Repair_Success :    out Boolean)
with
   Pre  => State.Self_Heals_Count < Max_Self_Heals,
   Post => (if Repair_Success then
               State.Memory_Safe and State.Hermetic_Shield and
               State.Alert_Level = Bark_Self_Healing_Applied);</pre>
Poškozený stav se zacelí za <strong>0.1 ms v RAM</strong>, bez pádů, bez výjimek a bez nutnosti restartu celé aplikace!`;
    }

    // 2. Asterisk vs Obelix
    if (q.includes('obelix') || q.includes('asterisk') || q.includes('architektur') || q.includes('mesh')) {
      return `🏛️ <strong>Architektura Asterisk (*) & Obelix:</strong><br>
• <strong>Asterisk (*) [Chrome Extension]</strong>: Lehký klientský WebMCP uzel přímo v prohlížeči. Stará se o 3D avatara pro 500M neslyšících, Spark TTS pro nevidomé a WebMCP komunikační rozhraní.<br>
• <strong>Obelix [Docker Heavy Node]</strong>: Těžký výpočetní uzel a SPARK vault na portu <strong>8423</strong>. Zpracovává těžké LLM operace, formální důkazy a běží s plnou suverenitou pod ochranou SPARKdoga.<br>
• <strong>Společně</strong> tvoří nezávislý decentralizovaný mesh bez závislosti na cloudu!`;
    }

    // 3. Velký Bratr a šmíráci
    if (q.includes('smirak') || q.includes('šmírák') || q.includes('velk') || q.includes('bratr') || q.includes('sledov') || q.includes('telemetr')) {
      return `🛡️ <strong>Aktivní likvidace Velkého Bratra:</strong><br>
SPARKdog Guardian aktivně hlídá každé odchozí spojení:
<br>• Každý tracker, nepovolená telemetrie nebo pokus o fingerprinting je okamžitě zachycen (<code>Intercept_Big_Brother_Threat</code>).
<br>• <strong>Hermetic Shield</strong> uzavře odchozí brány a izoluje proces v RAM.
<br>• Žádná data neodchází cizím korporátům ani reklamním systémům.`;
    }

    // 4. Devpost Hackathony
    if (q.includes('devpost') || q.includes('hackathon') || q.includes('vyzv') || q.includes('submission')) {
      return `🏆 <strong>Strategie pro Devpost Hackathony 2026:</strong><br>
Máme připravenou matici 5 velkých kategorií:<br>
1. <strong>WebMCP Challenge</strong>: Decentralizovaný mesh streamovaný v RAM.<br>
2. <strong>A11y 500M Voices</strong>: 3D avatar znakového jazyka 100% zdarma.<br>
3. <strong>All Things Agentic</strong>: Didaktický 5-fázový agent s 15s failoverem.<br>
4. <strong>Solar Sovereign AI</strong>: 100% solární napájení s $0 idle náklady.<br>
V záložce <strong>⚡ Studio</strong> si můžeš jedním kliknutím vygenerovat kompletní podklady pro odevzdání!`;
    }

    // 5. PJAY skript a standard 700
    if (q.includes('pjay') || q.includes('hoc est via') || q.includes('standard 700') || q.includes('groot')) {
      return `📜 <strong>Jazyk PJAY (Protocol 4.23 / Standard 700):</strong><br>
Náš nativní řídicí jazyk s posvátnými direktivami:
<br>• <code>Hoc_est_via:</code> (This is the way) – Nastavení invariantů.
<br>• <code>Locutus_sum:</code> (I have spoken) – Spuštění WebMCP a Spark TTS.
<br>• <code>Ego_sum_Groot:</code> – Dohledová smyčka SPARKdoga s GNATem a časový spouštěč <strong>Ash Sweeper (04:23 UTC)</strong>, který skartuje všechna dočasná data v paměti.`;
    }

    // 6. Solární napájení a energetika
    if (q.includes('solar') || q.includes('slunc') || q.includes('bater') || q.includes('energie') || q.includes('genesis')) {
      return `☀️ <strong>Solární Genesis (100% Solar-Powered):</strong><br>
Celý systém běží na solární energii s bateriovým úložištěm.
<br>• Nulové idle náklady ($0/měsíc při nečinnosti).
<br>• Ekologicky čistý výpočetní výkon bez uhlíkové stopy.
<br>• Ideální pro udržitelnou infrastrukturu a suverénní lokální uzly.`;
    }

    // 7. Znakový jazyk / 500M
    if (q.includes('znakov') || q.includes('neslys') || q.includes('nevidom') || q.includes('avatar') || q.includes('500')) {
      return `🤟 <strong>3D Znakový Avatar & Přístupnost:</strong><br>
Naše mise je pomoci 500 milionům neslyšících a nevidomých lidí na celém světě:
<br>• <strong>100% Free</strong> přístup bez bariér.
<br>• 3D avatar vykreslovaný v reálném čase s plynulým přechodem gest.
<br>• Integrovaný <strong>Spark TTS</strong> most pro okamžitý hlasový popis.`;
    }

    // 8. Síťové propojení přes switch (LAN IP 191.168.123.192)
    if (q.includes('switch') || q.includes('191.168') || q.includes('192.168') || q.includes('propojen') || q.includes('komp') || q.includes('lan') || q.includes('ip')) {
      return `🔌 <strong>Síťové propojení přes Switch (LAN IP 191.168.123.192):</strong><br>
Perfektní! Počítače máš propojené napřímo přes switch. To znamená, že <strong>na Windows nemusíš instalovat těžký backend ani Docker</strong>:<br>
• <strong>Ubuntu ESPRIMO (191.168.123.192)</strong> běží jako těžký výpočetní uzel <strong>OBELIX</strong>.<br>
• <strong>Z Windows PC</strong> stačí v prohlížeči otevřít:<br>
  - <strong>3D Znakový Avatar:</strong> <code>http://191.168.123.192:3000</code><br>
  - <strong>Hackathon AI Studio:</strong> <code>http://191.168.123.192:8088</code> (nebo <code>:8085</code>)<br>
  - <strong>Obelix SPARK Node:</strong> <code>http://191.168.123.192:8423</code><br>
  - <strong>Grafana Metriky:</strong> <code>http://191.168.123.192:3001</code><br>
Všechny služby naslouchají na <code>0.0.0.0</code>, takže komunikace mezi kompy běží s nulovou latencí (&lt; 1 ms) bez zátěže Windows PC!`;
    }

    // Obecná odpověď s kontextem
    return `🤖 <strong>Sovereign Asistent (v RAM):</strong><br>
Rozumím tvému dotazu: <em>"${query}"</em>.<br>
V mém kontextu mám načtenou kompletní architekturu <strong>Asterisk (*)</strong>, uzel <strong>Obelix</strong>, dohled <strong>SPARKdog s GNATem</strong> i samo-opravu za chodu.<br><br>
Můžeš se mě zeptat na cokoliv ohledně kódu v Adě/SPARK, PJAY skriptu, generování Devpost přihlášek nebo ochrany paměti!`;
  }

  // Odeslání formuláře
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    appendMessage(text, true);
    chatInput.value = '';

    // Simulace bleskového zpracování v RAM
    setTimeout(() => {
      const response = generateSovereignResponse(text);
      appendMessage(response, false);
    }, 150);
  });

  // Kliknutí na chip otázky
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const q = chip.dataset.q;
      appendMessage(q, true);
      setTimeout(() => {
        const response = generateSovereignResponse(q);
        appendMessage(response, false);
      }, 150);
    });
  });

  // ------------------------------------------------------------
  // 4. HACKATHON GENERATOR STUDIO
  // ------------------------------------------------------------
  const pTitle = document.getElementById('pTitle');
  const pPrompt = document.getElementById('pPrompt');
  const pOutput = document.getElementById('pOutput');
  const btnBuild = document.getElementById('btnBuild');

  document.querySelectorAll('.btn-preset').forEach(btn => {
    btn.addEventListener('click', () => {
      pTitle.value = btn.dataset.title || '';
      pPrompt.value = btn.dataset.prompt || '';
    });
  });

  btnBuild.addEventListener('click', () => {
    const t = pTitle.value;
    const p = pPrompt.value;

    pOutput.innerText = 
`# ✦ ${t}
### *Sovereign Solution for Devpost 2026*

## ☀️ The Solar Genesis
Powered 100% by solar energy from the very first line of code.

## 🌟 Mission & Social Impact
${p}
- 100% Free for 500 Million Deaf & Blind Users
- Commercial flat-rate: $111/month

## 🛡️ Formally Verified SPARK Core & Self-Healing
- Zero runtime crashes (Ada/SPARK 2022 level 4 formal proof)
- In-Vivo Self-Healing: hot-repair in 0.1 ms upon memory perturbation
- Zero-Trace RAM protocol (Ash Sweeper incinerates data at 04:23 UTC)
- SPARKdog Guardian actively intercepts Big Brother & third-party trackers
- WebMCP native integration via document.modelContext`;

    console.log('[SidePanel Studio] Project generated for:', t);
  });

  // ------------------------------------------------------------
  // 5. SPARKDOG MONITOR & SAMO-OPRAVA TEST
  // ------------------------------------------------------------
  const btnSimulateHeal = document.getElementById('btnSimulateHeal');
  const guardLog = document.getElementById('guardLog');
  const selfHealStatus = document.getElementById('selfHealStatus');

  btnSimulateHeal.addEventListener('click', () => {
    guardLog.innerHTML = `[0.00ms] ⚠️ Simulace anomálie: Detekován pokus o narušení bufferu útočníkem...<br>`;
    
    setTimeout(() => {
      guardLog.innerHTML += `[0.05ms] 🚨 SPARKdog zachytil nesoulad s kontraktem! Zastavena propagace.<br>`;
      guardLog.innerHTML += `[0.10ms] 🩹 Spuštěna procedura Self_Heal_Runtime_State...<br>`;
      
      setTimeout(() => {
        guardLog.innerHTML += `<span style="color:#4ade80;">[0.12ms] ✅ SAMO-OPRAVA ÚSPĚŠNÁ! Stav v RAM obnoven, Hermetic Shield 100% aktivní, 0 výpadek.</span>`;
        selfHealStatus.textContent = "AKTIVNÍ (Zaceleno za 0.12 ms)";
      }, 200);
    }, 150);
  });

});
