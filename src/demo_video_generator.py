#!/usr/bin/env python3
"""
Cave Lab — Autonomous Demo Video Generator
=============================================
Vytvoří XPRIZE demo video autonomně:
  1. Gemini napíše scénář (EN, < 3 min)
  2. Edge-TTS nasyntetizuje hlas
  3. Systém nahraje demo (screenshots/screencast)
  4. ffmpeg složí finální video

Spuštění:
    python src/demo_video_generator.py

Výstup: /tmp/cave_lab_output/xprize_demo.mp4

Autor: Pan Jeskyně
Oddělení: Cave Lab (autonomní)
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# === CONFIG ===
OUTPUT_DIR = Path("/tmp/cave_lab_output")
OUTPUT_DIR.mkdir(exist_ok=True)

GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or Path(
    Path.home() / ".gemini_api_key"
).read_text().strip().split("=")[-1]

os.environ["GEMINI_API_KEY"] = GEMINI_KEY

# === 1. SCÉNÁŘ ===

SCENARIO_PROMPT = """
Write a 3-minute video script for the All Things Agentic Hackathon ($180,000) submission.

Product: Universal Translation Layer (UTL) — Protocol 4.23
Key Personas:
- Agent Jan Amos Komenský (Supreme Taskmaster: 5-step didactic pipeline with Gemini 3.5 Flash)
- Kněžna Libuše & Přemysl Oráč (Prometheus telemetry, Ethereum Geth mirror, and PJAY mesh engine)
- 100% On-device Interaction Memory Bank (1 GB = 8 years of life)
- Ada/SPARK 2022 formal mathematical verification (gnatprove Level 4)
- Google Cloud Run deployment with Scale-to-Zero ($0 idle cost)
- GNU General Public License v3.0 (GNU GPLv3)

Key points to cover (in this order):
1. INTRO (20s): "Universal Translation Layer breaks all linguistic barriers. Governed by Agent Jan Amos Komenský & Kněžna Libuše."
2. PROBLEM (25s): Language barriers isolate billions. Conventional tools are fragile chat wrappers that crash on edge cases and leak data.
3. AGENT TASKMASTER (45s): Agent Komenský's 5 didactic phases: Labyrinth Analysis -> Janua Linguarum Translation (Gemini) -> Orbis Pictus Timing Sync -> SPARK Verification -> Mastered Delivery.
4. SOVEREIGN ARCHITECTURE (40s): Ada/SPARK 2022 mathematically proven core + Agent Přemysl mesh routing in PJAY language with 15s automated failover.
5. ON-DEVICE MEMORY & PRIVACY (25s): On-device memory bank (1GB = 8 years) complying with the Digital Hippocratic Oath.
6. GOOGLE CLOUD RUN DEPLOYMENT (20s): Stateless container deployment on Google Cloud Run with scale-to-zero ($0 idle cost).
7. CLOSE (15s): "Omnibus, non cum aliquo. Speak your language, everyone hears you in theirs."

Format: Return JSON with array of segments:
[{"time": "0:00-0:20", "title": "...", "narration": "...", "visual": "description of what to show"}]

IMPORTANT: English narration only. Keep total under 3:00.
"""


def generate_scenario() -> list:
    """Gemini generuje scénář."""
    from google import genai

    client = genai.Client(api_key=GEMINI_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=SCENARIO_PROMPT,
    )

    # Parse JSON z odpovědi
    text = response.text
    # Vyčistit markdown
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    segments = json.loads(text.strip())
    print(f"✅ Scénář: {len(segments)} segmentů")
    return segments


# === 2. SYNTÉZA HLASU ===

def synthesize_narration(segments: list) -> Path:
    """Edge-TTS nasyntetizuje celou naraci."""
    full_text = " ".join(seg["narration"] for seg in segments)
    
    output_file = OUTPUT_DIR / "narration.mp3"
    
    # Edge-TTS (Microsoft, zdarma, kvalitní)
    cmd = [
        sys.executable, "-m", "edge_tts",
        "--voice", "en-US-AndrewMultilingualNeural",
        "--text", full_text,
        "--write-media", str(output_file),
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️  Edge-TTS error: {result.stderr}")
        # Fallback: espeak
        subprocess.run(["espeak", "-w", str(output_file), full_text], capture_output=True)
    
    print(f"✅ Narace: {output_file} ({output_file.stat().st_size // 1024}KB)")
    return output_file


# === 3. VIZUÁLNÍ PODKLADY ===

def generate_visuals(segments: list) -> list:
    """Vytvoří vizuální podklady — HTML slides + screenshots."""
    slides = []
    
    for i, seg in enumerate(segments):
        # Vytvořit HTML slide
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{
    background: linear-gradient(135deg, #0a0a2e 0%, #1a1040 100%);
    color: white;
    font-family: 'Segoe UI', Arial, sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    margin: 0;
    padding: 2rem;
}}
.slide {{
    text-align: center;
    max-width: 80%;
}}
h1 {{ font-size: 3rem; margin-bottom: 1rem; }}
p {{ font-size: 1.5rem; color: #a0b8d0; line-height: 1.6; }}
.badge {{ 
    display: inline-block;
    background: #6a3fd8;
    padding: 0.5rem 1.5rem;
    border-radius: 20px;
    font-size: 1.2rem;
    margin-top: 1rem;
}}
</style></head><body>
<div class="slide">
<h1>{seg.get('visual', '').split('.')[0] if seg.get('visual') else f'Segment {i+1}'}</h1>
<p>{seg['narration'][:200]}</p>
<div class="badge">Asgard Lab • web4light.online</div>
</div>
</body></html>"""
        
        slide_path = OUTPUT_DIR / f"slide_{i:02d}.html"
        slide_path.write_text(html, encoding="utf-8")
        slides.append(slide_path)
    
    print(f"✅ Vizuály: {len(slides)} slides vygenerováno")
    return slides


# === 4. SESTAVENÍ VIDEA ===

def assemble_video(narration: Path, slides: list) -> Path:
    """ffmpeg složí narace + vizuály do MP4."""
    
    output_file = OUTPUT_DIR / "xprize_demo.mp4"
    
    # Získat délku narace
    probe_cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(narration)
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    duration = float(result.stdout.strip()) if result.stdout.strip() else 170.0
    
    # Délka jednoho slide
    slide_duration = duration / max(len(slides), 1)
    
    # Vytvořit obrázky ze slides (pomocí wkhtmltoimage nebo chromium screenshot)
    # Fallback: solid color frames s textem
    
    # Sestavit concat file pro ffmpeg
    concat_file = OUTPUT_DIR / "concat.txt"
    with open(concat_file, "w") as f:
        for i, slide in enumerate(slides):
            img_path = OUTPUT_DIR / f"frame_{i:02d}.png"
            # Vytvořit placeholder PNG (solid frame)
            subprocess.run([
                "convert", "-size", "1920x1080",
                f"xc:#0a0a2e",
                "-font", "DejaVu-Sans", "-pointsize", "48",
                "-fill", "white", "-gravity", "center",
                "-annotate", "+0+0", f"Asgard Lab - Segment {i+1}",
                str(img_path)
            ], capture_output=True)
            
            if img_path.exists():
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {slide_duration:.2f}\n")
    
    # ffmpeg: concat images + audio → MP4
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(narration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(output_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"✅ Video: {output_file} ({size_mb:.1f}MB, {duration:.0f}s)")
    else:
        print(f"⚠️  Video assembly failed: {result.stderr[:200]}")
        # Fallback: jen audio jako MP4
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(narration),
            "-vn", "-c:a", "aac",
            str(output_file.with_suffix('.m4a'))
        ], capture_output=True)
        print(f"✅ Fallback: audio only ({output_file.with_suffix('.m4a')})")
    
    return output_file


# === MAIN ===

def main():
    print("═" * 60)
    print("  🎬 CAVE LAB — Autonomous Demo Video Generator")
    print("  XPRIZE Build with Gemini 2026")
    print("═" * 60)
    print()
    
    # 1. Scénář
    print("[1/4] Generuji scénář (Gemini)...")
    try:
        segments = generate_scenario()
    except Exception as e:
        print(f"⚠️  Gemini error: {e}")
        # Fallback scénář
        segments = [
            {"time": "0:00-0:20", "narration": "Asgard Lab breaks every communication barrier. Language. Hearing. Sight. One system, infinite outputs.", "visual": "Logo + tagline"},
            {"time": "0:20-0:50", "narration": "Four hundred million deaf people cannot access video content. Billions face language barriers in education. Current solutions are expensive, slow, and fragmented.", "visual": "Problem statement"},
            {"time": "0:50-1:30", "narration": "Our Universal Translator, Karel the Fourth, converts any input to any output. Voice to voice in twenty-two languages. Voice to sign language for deaf users, always free. Sign language to voice, so deaf people can speak. All in real-time.", "visual": "Pipeline demo"},
            {"time": "1:30-2:00", "narration": "Built on Ada SPARK with formal verification. One hundred eleven mathematical proofs, zero errors. Gemini API powers translation. Five autonomous AI departments run operations twenty-four seven.", "visual": "Tech stack + SPARK proved"},
            {"time": "2:00-2:30", "narration": "Four subscription tiers from one hundred eleven to four hundred twenty-three Czech crowns per month. Sign language is always free. Zero infrastructure cost — solar powered, own hardware.", "visual": "Pricing + dashboard"},
            {"time": "2:30-2:50", "narration": "The first article must be bulletproof. Then the rest builds itself, autonomously. Asgard Lab. web4light.online.", "visual": "Close + URL"},
        ]
        print(f"✅ Fallback scénář: {len(segments)} segmentů")
    
    # Uložit scénář
    scenario_path = OUTPUT_DIR / "scenario.json"
    scenario_path.write_text(json.dumps(segments, indent=2, ensure_ascii=False))
    
    # 2. Narace
    print("\n[2/4] Syntetizuji hlas (Edge-TTS)...")
    narration = synthesize_narration(segments)
    
    # 3. Vizuály
    print("\n[3/4] Generuji vizuály...")
    slides = generate_visuals(segments)
    
    # 4. Video
    print("\n[4/4] Sestavuji video (ffmpeg)...")
    video = assemble_video(narration, slides)
    
    print()
    print("═" * 60)
    print("  🎬 HOTOVO!")
    print(f"  📁 Výstup: {OUTPUT_DIR}")
    print(f"  🎥 Video:  {video}")
    print(f"  📝 Scénář: {scenario_path}")
    print(f"  🔊 Narace: {narration}")
    print()
    print("  Další kroky:")
    print("    1. Nahraj na YouTube")
    print("    2. Přidej link do Devpost submission")
    print("═" * 60)


if __name__ == "__main__":
    main()
