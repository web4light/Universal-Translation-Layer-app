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
    ("intro", "Dobrý den. Jsem Karel, váš osobní překladatel z Asgard Lab."),
    ("product", "Náš produkt překládá jakékoliv video do jakéhokoliv jazyka. Vlastním hlasem mluvčího. V reálném čase. Bez lidského zásahu."),
    ("sign", "Pro neslyšící komunitu generujeme znakovou řeč. Zdarma. Navždy. Protože přístupnost není prémiová funkce. Je to základní lidské právo."),
    ("impact", "Dva a půl miliardy lidí na světě nemá přístup ke vzdělávání ve svém jazyce. Čtyři sta šedesát šest milionů lidí je neslyšících. Náš produkt tuto bariéru odstraňuje."),
    ("tech", "Pod kapotou běží Ada SPARK formální verifikace. Tři sta matematických důkazů. Nula chyb za běhu. Systém běží autonomně na solární energii."),
    ("try_it", "Vyzkoušejte si to sami. Otevřete web4light tečka online. Vložte odkaz na jakékoliv YouTube video. Vyberte jazyk. Klikněte. Hotovo."),
    ("close", "Hoc est via. Děkuji za pozornost."),
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
    print("  XPRIZE VIDEO — Agent se představuje")
    print("  Antonín (Werich styl) + bg video")
    print("=" * 50)
    print()

    # 1. Generuj narration
    print("[1/2] Generating narration (Edge-TTS, Antonín)...")
    audio = await generate_narration()

    # 2. Spoj s pozadím (bg.mp4 z webu nebo černý frame)
    print("\n[2/2] Composing final video...")
    
    bg_video = Path(__file__).parent.parent / "static" / "bg.mp4"
    if not bg_video.exists():
        # Stáhni z webu
        print("  Stahuji bg.mp4 z web4light.online...")
        subprocess.run([
            "curl", "-sL", "-o", str(bg_video),
            "https://web4light.github.io/bg.mp4"
        ])
    
    final = OUTPUT_DIR / "xprize_submission.mp4"
    
    # Zjisti délku audia
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio)
    ], capture_output=True, text=True)
    audio_duration = float(result.stdout.strip())
    
    # Loop bg video na délku audia + overlay text
    subprocess.run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(bg_video),
        "-i", str(audio),
        "-t", str(audio_duration + 3),
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-vf", "scale=1920:1080,drawtext=text='web4light.online':fontsize=36:fontcolor=gold:x=(w-text_w)/2:y=h-60:font=Arial",
        "-shortest",
        str(final)
    ], capture_output=True)

    size_mb = final.stat().st_size / 1024 / 1024
    print(f"\n{'=' * 50}")
    print(f"  HOTOVO!")
    print(f"  Video: {final}")
    print(f"  Délka: {audio_duration + 3:.0f}s")
    print(f"  Velikost: {size_mb:.1f} MB")
    print(f"  Nahraj na YouTube → link do DevPost.")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(main())
