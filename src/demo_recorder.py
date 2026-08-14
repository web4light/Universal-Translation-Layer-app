#!/usr/bin/env python3
"""
Demo Recorder — automatické natočení XPRIZE demo videa.

1. Edge-TTS vygeneruje anglický komentář (Werich styl)
2. ffmpeg nahrává obrazovku
3. Sloučí video + audio

Žádný mikrofon. Agent mluví sám.

Autor: Pan Jeskyně
"""

import os
import sys
import time
import asyncio
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("/tmp/xprize_demo")
OUTPUT_DIR.mkdir(exist_ok=True)

# Script co agent říká (anglicky pro XPRIZE judges)
SCRIPT = [
    ("intro", "Čau. Jsem tvůj parťák. Přeložím ti jakékoliv video do jakéhokoliv jazyka. Vlastním hlasem. Pro neslyšící — znakovou řečí. Zdarma. Vždycky."),
    ("demo", "Koukej. Vložím odkaz na YouTube. Pipeline běží autonomně. Gemini překládá. Dirigent řídí hlasy. Žádný člověk v procesu."),
    ("tech", "Pod kapotou: Ada SPARK formální verifikace. Tři sta matematických důkazů. Nula runtime chyb. Běží na solární energii."),
    ("sign", "Znaková řeč se generuje zdarma. Vždycky. Protože přístupnost není funkce. Je to právo."),
    ("close", "Hoc est via. web4light tečka online."),
]

# Hlas — Antonín (český, Werich styl)
VOICE = "cs-CZ-AntoninNeural"


async def generate_narration():
    """Vygeneruj TTS audio pro každou sekci."""
    import edge_tts

    audio_files = []
    for name, text in SCRIPT:
        out_path = OUTPUT_DIR / f"narration_{name}.mp3"
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(str(out_path))
        audio_files.append(out_path)
        print(f"  [TTS] {name}: {out_path.name}")

    # Spojit všechny do jednoho
    list_file = OUTPUT_DIR / "audio_list.txt"
    with open(list_file, "w") as f:
        for af in audio_files:
            f.write(f"file '{af}'\n")

    final_audio = OUTPUT_DIR / "narration_full.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", str(final_audio)
    ], capture_output=True)

    print(f"  [TTS] Full narration: {final_audio}")
    return final_audio


def record_screen(duration: int = 60):
    """Nahrávej obrazovku po dobu duration sekund."""
    video_path = OUTPUT_DIR / "screen_recording.mp4"
    print(f"  [REC] Recording screen for {duration}s...")

    proc = subprocess.Popen([
        "ffmpeg", "-y",
        "-video_size", "1920x1080",
        "-framerate", "24",
        "-f", "x11grab", "-i", ":0",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-t", str(duration),
        str(video_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return proc, video_path


def merge_audio_video(video_path: Path, audio_path: Path):
    """Sloučí video + audio do finálního MP4."""
    final = OUTPUT_DIR / "xprize_submission.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(final)
    ], capture_output=True)
    print(f"  [DONE] Final video: {final}")
    return final


async def main():
    print("=" * 50)
    print("  XPRIZE DEMO RECORDER")
    print("  Agent mluví sám. Žádný mikrofon.")
    print("=" * 50)
    print()

    # 1. Generuj narration
    print("[1/3] Generating narration (Edge-TTS)...")
    audio = await generate_narration()

    # Zjisti délku audia
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio)
    ], capture_output=True, text=True)
    duration = int(float(result.stdout.strip())) + 5  # +5s buffer

    print(f"\n[2/3] Recording screen ({duration}s)...")
    print("       >>> TEĎ UKAŽ DEMO NA OBRAZOVCE! <<<")
    print("       >>> Otevři http://localhost:8000 a vlož URL <<<")
    time.sleep(3)  # 3s na přípravu

    # 2. Nahrávej obrazovku
    proc, video = record_screen(duration)
    proc.wait()

    # 3. Sloučit
    print(f"\n[3/3] Merging video + audio...")
    final = merge_audio_video(video, audio)

    print(f"\n{'=' * 50}")
    print(f"  HOTOVO!")
    print(f"  Video: {final}")
    print(f"  Délka: ~{duration}s")
    print(f"  Nahraj na YouTube a dej link do DevPost.")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(main())
