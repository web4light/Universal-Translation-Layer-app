# ✦ Strands Good Neighbor Sovereign Agent (Asterisk Mesh)
### *Accessible 3D Sign Language, Spark-TTS & Formally Verified Ethics for 500M Deaf & Blind Humans*

**Devpost Hackathon Submission:** [Agents for Humans](https://agentsforhumans.devpost.com/)  
**Track:** **Good Neighbor Agents** (Accessibility, Non-profit & Community Impact)  
**SDK Used:** **AWS Strands Agents SDK** (`strands-agents` & `strands-agents-tools`)  
**License:** GNU General Public License v3.0 (Open Source)  
**Author / Architect:** Pan Jeskyně & AsgardLab Sovereign Mesh  

---

## 🌟 Inspiration & "Good Neighbor" Vision

Over 500 million deaf and visually impaired people worldwide face severe digital isolation during live streams, educational content, and public announcements. Commercial speech and translation services are behind steep paywalls with predatory per-token pricing and invasive tracking.

Our mission as a **Good Neighbor Agent** is simple and uncompromising:
1. **100% Free Forever for Vulnerable Humans:** No subscription fees, no token meters, zero cost ($0.00).
2. **Real-time Multimodal Accessibility:** 3D Sign Language Avatar (`dlp3d` Three.js/WebGL) + tactile Spark-TTS audio scene descriptions.
3. **Formally Verified Ethics & Privacy:** Powered by Ada/SPARK 2026 mathematical contracts (SPARK Mode On, 0 heap, 0 exceptions) and the **HusGraal Judge Lab** enforcing GDPR and the EU AI Act before any data is processed.
4. **Zero-Trace In-Memory RAM Architecture:** The Ash Sweeper protocol incinerates all transient audio buffers and pose vectors directly in RAM — with proof of 0 bytes written to disk.

---

## 🛠️ Unified Tri-Repo Architecture

We brought together three sovereign platforms into one seamless agentic experience orchestrated by the **AWS Strands Agents SDK**:

```
 ┌────────────────────────────────────────────────────────┐
 │       AWS Strands Agents SDK Orchestration Core        │
 │              (strands_good_neighbor_agent.py)          │
 └─────────────────────────┬──────────────────────────────┘
                           │
 ┌─────────────────────────┼──────────────────────────────┐
 │                         │                              │
 ▼                         ▼                              ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  HusGraal Court  │  │ Universal Layer  │  │   WebMCP Mesh    │
│  (Ada/SPARK 2026)│  │ (3D Avatar + ETH)│  │   (Zero-Trace)   │
│                  │  │                  │  │                  │
│ • EU AI Act Art50│  │ • 3D Sign Avatar │  │ • WebMCP Toolset │
│ • GDPR Art 9 & 25│  │ • Soulbound NFT  │  │ • Ash Sweeper    │
│ • SIC/NON Verdict│  │ • SPARKdog Guard │  │ • In-Memory Ring │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

1. **`Universal-Translation-Layer`**:
   - High-fidelity 3D Sign Language Avatar rendering skeleton keyframes in real-time.
   - Ada/SPARK 2026 Soulbound Ethereum Wallet (`eth_wallet.ads/adb`) with 2FA double voiceprint authentication and EIP-155 replay protection.
   - SPARKdog Mesh Watchdog (`sparkdog_guardian.ads/adb`) ensuring sub-millisecond mesh fuel replenishment so services never go down.
2. **`husgraal`**:
   - Ada/SPARK Judge Lab (`judge_lab.ads/adb`) operating as an automated legal judge ("Žižka - blind and just").
   - Delivers formal binary verdicts (**SIC** / **NON**) on whether an agentic interaction adheres to human rights, GDPR consent, and EU AI Act transparency rules.
3. **`webmcp-mesh-sovereign`**:
   - WebMCP tool specifications (`document.modelContext`) for browser-native agent interaction.
   - In-memory audio loopback and RAM Ash Sweeper for instant data destruction.

---

## 🤖 Strands Agents SDK Integration

The core orchestrator is implemented in `src/strands_good_neighbor_agent.py` using `from strands import Agent, tool` and `BedrockModel`:

* **`husgraal_legal_ethics_guard`**: Pre-flight verification checking EU AI Act Art. 50 (transparency) and GDPR Art. 25 (privacy by design).
* **`sparkdog_sovereign_mesh_fuel`**: Validates beneficiary zero-cost guarantee and triggers the compiled Ada/SPARK verification binary (`eth_wallet_main`).
* **`accessibility_sign_avatar`**: Generates real-time 3D spatial hand/face keyframes for the WebGL avatar.
* **`accessibility_spark_tts`**: Streams high-fidelity audio scene descriptions for blind users.
* **`zero_trace_ram_purger`**: Runs the Ash Sweeper protocol, wiping all transient vectors from RAM.

Both **AWS Bedrock** (live cloud execution) and **Sovereign Offline Verified** mode are supported out-of-the-box, allowing evaluation with or without AWS keys.

---

## 🚀 Quick Start & Reproduction

```bash
# 1. Clone repository & install dependencies
git clone https://github.com/Rebirth-Phoenix-Foundation-Charter/Universal-Translation-Layer.git
cd Universal-Translation-Layer

# 2. Run the Strands Good Neighbor Agent
npm run strands:run

# 3. Launch the Strands FastAPI + WebMCP Server (Port 8089)
npm run strands:serve

# 4. Verify the formal Ada/SPARK mathematical proof
npm run wallet:run
npm run ada:run
```

---

## 🏆 Hackathon Alignment: Good Neighbor Track

- **Who does it help?** 500,000,000+ deaf and blind individuals globally who are cut off from streaming content and emergency broadcasts.
- **Why is it a Good Neighbor?** It charges $0.00, runs decentralized volunteer compute, respects personal privacy to the mathematical extreme (formal SPARK verification), and upholds international human rights laws.
