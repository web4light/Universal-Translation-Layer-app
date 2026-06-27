# 👑 Karel IV. — Real-time Voice Translator

**AsgardLab** | [web4light.online](https://web4light.online) | phoenix@web4light.online

> *Named after Charles IV (Karel IV.) — King of Bohemia, fluent in 7 languages. 1316–1378.*

Speak in Czech. Be heard in Japanese. **In your own voice.**

---

## What is Karel IV.?

Karel IV. is a real-time AI voice translator that:

- Listens to your microphone
- Transcribes speech using **Whisper** (MIT, runs locally)
- Translates using **Gemini AI** (Apache 2.0)
- Synthesizes output in **your own voice** using Coqui TTS (MIT)
- Delivers translated audio to your headphones in real-time

Built for **VR environments** — walk into a virtual meeting speaking Czech,
be heard in any language.

Powered by a **mesh network** of user hardware + **Sepolia ETH** payments.

---

## Quick Start

### Option 1: Docker (recommended)

```bash
# Clone repo
git clone https://github.com/Rebirth-Phoenix-Foundation-Charter/karel-iv.git
cd karel-iv

# Configure
cp docker/.env.example docker/.env
# Edit docker/.env — add your GEMINI_API_KEY

# Run everything
docker compose -f docker/docker-compose.yml up

# Karel IV. starts translating cs→en
# Metrics: http://localhost:9306/metrics
# Grafana: http://localhost:3000 (admin/asgardlab)
```

### Option 2: Python directly

```bash
# Install dependencies
pip install -r docker/requirements.txt

# Run Karel IV.
python src/karel_iv.py --source cs --target en

# With voice cloning (30s WAV sample)
python src/karel_iv.py --source cs --target en --voice my_voice.wav

# List supported languages
python src/karel_iv.py --list-languages
```

---

## Supported Languages

| Code | Language |
|------|----------|
| `cs` | Czech |
| `en` | English |
| `de` | German |
| `fr` | French |
| `ja` | Japanese |
| `es` | Spanish |
| `it` | Italian |
| `pl` | Polish |
| `sk` | Slovak |

---

## Architecture

```
Microphone
    ↓
Virtual Audio Card
    ↓
Whisper STT (local, MIT)
    ↓
Ada/SPARK Validation (formally verified)
    ↓
Gemini AI Translation (Apache 2.0)
    ↓
Coqui TTS — Your Voice Clone (MIT)
    ↓
Headphones
```

**Infrastructure:** Vakuová Mincovna (Primary + Shadow Node, Prometheus)
**Payments:** Sepolia ETH testnet → mainnet
**Mesh:** User hardware contributes idle CPU/GPU → earns ETH credits

---

## Pricing

| Plan | Price | Includes |
|------|-------|---------|
| Personal Assistant | 111 Kč/month | AI assistant, 1 device |
| Karel IV. | 222 Kč/month | Real-time translation, voice clone |
| Stream Dubbing | 333 Kč/month | Netflix/YouTube dubbing |
| **Family Plan** | **423 Kč/month** | **Everything, whole household** |

*Paid via Ethereum. Cancel anytime.*

---

## Tech Stack

| Component | Technology | License |
|-----------|-----------|---------|
| Speech-to-text | OpenAI Whisper | MIT |
| Translation | Google Gemini | Apache 2.0 |
| Voice synthesis | Coqui TTS | MIT |
| Orchestration | n8n | Sustainable Use |
| Core validation | Ada/SPARK | GPL-2.0 + exception |
| Network | Faucet SDN | Apache 2.0 |
| Monitoring | Prometheus + Grafana | Apache 2.0 |
| Payments | Ethereum (Sepolia) | Open |

---

## License

**Dual License:**

- **GPL 3.0** — for open-source and non-commercial use
- **Commercial** — for proprietary use, contact phoenix@web4light.online

See [LICENSE](LICENSE) for details.

---

## AsgardLab

Building the Web4 ecosystem.

- 🌐 [web4light.online](https://web4light.online)
- 📧 phoenix@web4light.online
- 📧 arch@web4light.online
- 🐙 [github.com/Rebirth-Phoenix-Foundation-Charter](https://github.com/Rebirth-Phoenix-Foundation-Charter)

---

*Karel IV. — First article must be bulletproof. Then the rest builds autonomously.*
