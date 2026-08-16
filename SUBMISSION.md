# Asgard Lab — XPRIZE Build with Gemini Submission

## Narrative (Submission)

### What We Built

Asgard Lab is an autonomous AI-powered translation and accessibility platform. Feed it any video — a YouTube link, a film, a news broadcast — and it delivers three outputs from one input:

1. **Translated subtitles** in 22+ languages (Gemini AI)
2. **AI dubbing** — spoken audio in the target language (TTS)
3. **Sign language** — animation instructions for a signing avatar (FREE for deaf users)

We call this principle **1+1=3**: translation plus dubbing creates accessibility as a third, emergent value.

### How AI Operates the Business

Our system runs **24/7 without human intervention**. The core is built in Ada/SPARK — a formally verified language that mathematically proves the pipeline cannot crash, leak memory, or skip segments. SPARK's ranged types and bounded loops guarantee constant memory usage indefinitely.

The AI pipeline:
- **Gemini API** translates subtitles (Google Cloud requirement ✓)
- **Geall** (our Ada AI agent) orchestrates the pipeline autonomously
- **gTTS/Coqui** synthesizes spoken audio from translated text
- **Sign Language Renderer** generates signing instructions from glosses

A user submits a video URL. The system autonomously downloads subtitles, translates them, generates dubbing audio, and produces sign language output. No human touches the pipeline. SPARK guarantees it runs forever without degradation.

### What Humans Do vs. What AI Does

| Human | AI |
|-------|-----|
| Submit video URL | Download subtitles from source |
| Choose target language | Translate via Gemini |
| — | Synthesize audio (TTS) |
| — | Generate sign language glosses |
| — | Deliver all three outputs |
| Review quality (optional) | Self-monitor via Prometheus metrics |

The ratio is approximately **5% human, 95% AI**. The human's only job is to choose what to translate. Everything else is autonomous.

### Jobs and Economic Opportunities Created

1. **Deaf community access** — We work directly with Tichý svět (Silent World), a Czech organization for deaf people. They receive our sign language output FREE. Their members pick up materials from our print shop on Tuesday. These are real users, not hypothetical.

2. **Content creators** — Any YouTuber or filmmaker can reach global audiences without paying for professional dubbing studios.

3. **Small translation businesses** — Our API enables small agencies to offer dubbing services without hiring voice actors.

4. **Language learners** — The continuous dubbing pipeline (SPARK running 24/7 translating series) serves as a language learning tool. You learn by consuming content in your target language.

### The Story of Building This Way

We started with a question: Why can't a deaf person in Prague watch Japanese anime with Czech sign language? Why does dubbing cost thousands when subtitles already exist as free text?

The answer was obvious — **subtitles are the input**. Every film, every stream, every YouTube video already has text. We just needed Gemini to translate it and a pipeline to convert it into speech and signs.

We built the prototype in 9 days. Ada/SPARK gives us the confidence to run it unsupervised. Gemini gives us the intelligence to translate naturally. The combination — mathematical certainty plus AI creativity — is something no other team offers.

Our web presence (web4light.online) states our mission in Latin — a language older than English, describing technology newer than anything else:

> *Loquere lingua tua. Omnes te audient sua lingua. Tua voce.*
> Speak your language. Everyone hears you in theirs. In your voice.

### Technical Stack

- **Formal verification**: Ada/SPARK (GNAT 14, gnatprove)
- **AI translation**: Gemini API (Google Cloud)
- **TTS synthesis**: gTTS, Coqui XTTS v2
- **Sign language**: Rule-based + Gemini glossing (ČZJ, ASL, BSL, DGS)
- **Orchestration**: Geall (Ada AI agent), systemd services
- **Monitoring**: Prometheus + Grafana (ports 9302-9305)
- **Infrastructure**: 3-node system (Ubuntu + Windows + NAS), mesh network

### Revenue Model

- **Paid**: Dubbing services for content creators and businesses
- **Free**: Sign language for deaf community (social mission)
- **B2B**: API for streaming platforms and translation agencies

### Category

**Education & Human Potential** — Transforming how deaf people access content and how everyone learns languages through AI-translated media.

---

*Built by Pan Jeskyně / Rebirth Phoenix Foundation Charter*
*web4light.online*
