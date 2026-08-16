# Karel IV. — Universal Translation Layer

## Category: Education & Human Potential

## What it does

Karel IV. is an AI-native translation and dubbing platform that takes any YouTube video
and autonomously translates, dubs, and generates sign language — making education
accessible to everyone, in every language, in your own voice.

**Free sign language for the deaf community. Always.**

## How it works

1. User pastes a YouTube URL
2. AI pipeline autonomously:
   - Downloads subtitles (yt-dlp)
   - Translates via Gemini API (22+ languages)
   - Generates voice dubbing (Edge-TTS / Spark-TTS)
   - Produces sign language glosses (FREE)
3. User receives translated + dubbed video

## Tech Stack

- **Ada/SPARK** — formally verified core (286+ proved checks, 0 errors)
- **Gemini API** — translation engine (Google Cloud requirement met)
- **Python/FastAPI** — web API layer
- **Prometheus** — monitoring (Ada HTTP server on port 9307)
- **Solar powered** — zero operating cost

## AI-Native Operations

The entire business runs through AI:
- Translation pipeline is autonomous (no human in the loop)
- Revenue engine manages pricing and reinvestment (SPARK proved)
- Marketing funnel tracks visitors → trials → subscribers autonomously
- Sign language generation runs 24/7 without human intervention

## Revenue Model

| Tier | Price | Features |
|------|-------|----------|
| Free | 0 | Sign language (always free for deaf) |
| Geall 111 | 111 CZK/mo | AI assistant |
| Karel 222 | 222 CZK/mo | Translation + voice |
| Dubbing 333 | 333 CZK/mo | Stream dubbing |
| Family 423 | 423 CZK/mo | Everything, whole family |

## Evidence

- GitHub: private repo shared with testing@devpost.com and judging@hacker.fund
- Live API: running on Ubuntu server (Asgard Lab)
- SPARK proofs: 286+ formal verification checks, 0 unproved
- Prometheus metrics: real-time monitoring dashboard

## Links

- Website: https://web4light.online
- DevPost: https://devpost.com/software/karel-iv-universal-translation-layer
- Repo: https://github.com/Rebirth-Phoenix-Foundation-Charter/Universal-Translation-Layer

## Video Script (< 3 min)

[Avatar speaks — Werich/Rudolf II. style]

"Hey. I'm your buddy — Karel IV.
Give me any YouTube video. I'll translate it for you.
Into anything. In your own voice.

Can't hear? I'll show you with my hands. For free. Always.

This is how it works:
[demo: paste URL → pipeline runs → output]

Under the hood: Ada/SPARK formal verification.
286 mathematical proofs. Zero runtime errors.
Running on solar power. Zero operating cost.

Education should be accessible to everyone.
In every language. In every modality.

Hoc est via.
web4light.online"
