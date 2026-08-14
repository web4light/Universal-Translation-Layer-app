#!/usr/bin/env python3
"""
Asgard CLI — Jeden terminál, celý Web4Light.

Příkazy:
    asgard translate <url> --to <lang>     Přelož YouTube video
    asgard voice <text> --ref <wav>        Voice cloning (Spark-TTS)
    asgard sign <text>                     Znaková řeč (glosses)
    asgard vision <image>                  Popis obrázku (Gemini)
    asgard scada                           Vygeneruj SCADA SVG
    asgard status                          Stav všech služeb
    asgard prove                           Spusť gnatprove na všem
    asgard cave <prompt>                   Cave Lab — vygeneruj web
    asgard dirigent --status               Dirigent stav
    asgard pipeline <url> --to <lang>      Celý pipeline (translate+dub+sign)

Autor: Pan Jeskyně
Licence: Apache 2.0
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
BIN = ROOT / "bin"
SRC = ROOT / "src"


def cmd_status():
    """Stav všech služeb — jističe."""
    import urllib.request
    services = [
        ("Asgard API", "http://localhost:8000/status"),
        ("Cave Lab", "http://localhost:8001/"),
        ("Shadow Node", "http://localhost:9303/"),
        ("Watchdog", "http://localhost:9304/"),
        ("Privacy 4:23", "http://localhost:9305/"),
        ("SDN Bridge", "http://localhost:9306/metrics"),
        ("Prometheus Ada", "http://localhost:9307/metrics"),
        ("Prometheus", "http://localhost:9090/api/v1/targets"),
        ("Grafana", "http://localhost:3000/"),
    ]
    print("ASGARD LAB — STAV JISTIČŮ")
    print("=" * 40)
    for name, url in services:
        try:
            urllib.request.urlopen(url, timeout=2)
            print(f"  ON   {name}")
        except Exception:
            print(f"  OFF  {name}")
    print("=" * 40)


def cmd_prove():
    """Spusť gnatprove na všech modulech."""
    gpr_files = list(ROOT.glob("*.gpr"))
    prover = "/mnt/web4light/tools/gnatprove/13.2.1/bin/gnatprove"
    if not Path(prover).exists():
        prover = "gnatprove"

    total_checks = 0
    total_unproved = 0

    for gpr in sorted(gpr_files):
        name = gpr.stem
        result = subprocess.run(
            [prover, "-P", str(gpr), "--mode=prove", "--level=0", "--timeout=10"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        # Parse output
        for line in result.stdout.split("\n"):
            if "Total" in line and "Flow" in line:
                continue
            if "Total" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p.isdigit() and i == 1:
                        total_checks += int(p)
        print(f"  {name}")

    print(f"\nCELKEM: {total_checks} checks")


def cmd_translate(args):
    """Přelož YouTube video."""
    import urllib.request
    url = args.url
    target = args.to or "cs"

    payload = json.dumps({"url": url, "target": target}).encode()
    req = urllib.request.Request(
        "http://localhost:8000/translate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        if data.get("status") == "success":
            print(f"PŘELOŽENO: {data['subtitles_translated']}/{data['subtitles_total']}")
            print(f"Čas: {data['total_time_s']}s")
            print(f"Znaky: {data['sign_language_glosses']} glosses")
            print(f"Soubory: {json.dumps(data['files'], indent=2)}")
        else:
            print(f"CHYBA: {data}")
    except Exception as e:
        print(f"CHYBA: {e}")


def cmd_dirigent(args):
    """Dirigent — Ada orchestrátor."""
    dirigent = BIN / "dirigent_main"
    if not dirigent.exists():
        print("Dirigent binárka neexistuje. Spusť: gprbuild -P dirigent_main.gpr")
        return
    flag = "--status" if args.status else ""
    result = subprocess.run([str(dirigent), flag] if flag else [str(dirigent)],
                           capture_output=True, text=True)
    print(result.stdout)


def cmd_vision(args):
    """Popis obrázku přes Gemini."""
    vision = SRC / "vision_mcp.py"
    result = subprocess.run(
        [sys.executable, str(vision), "--analyze", args.image],
        capture_output=True, text=True
    )
    print(result.stdout)


def cmd_scada():
    """Vygeneruj SCADA SVG."""
    vision = SRC / "vision_mcp.py"
    result = subprocess.run(
        [sys.executable, str(vision), "--generate"],
        capture_output=True, text=True
    )
    print(result.stdout)


def cmd_sign(args):
    """Znaková řeč — glosses."""
    text = " ".join(args.text)
    # Jednoduchý glosser
    words = text.upper().split()
    glosses = " ".join(words)
    print(f"GLOSSES ({len(words)}): {glosses}")


def cmd_cave(args):
    """Cave Lab — vygeneruj web."""
    prompt = " ".join(args.prompt)
    import urllib.request
    payload = json.dumps({"prompt": prompt}).encode()
    req = urllib.request.Request(
        "http://localhost:8001/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        print(f"Web vygenerován: {data.get('web', {}).get('file', '?')}")
    except Exception as e:
        print(f"CHYBA: {e}")


def cmd_voice(args):
    """Voice cloning přes Spark-TTS (Windows GPU)."""
    text = " ".join(args.text)
    ref = args.ref or ""
    print(f"Text: {text}")
    print(f"Ref: {ref}")
    print("Spark-TTS běží na Windows RTX 3070...")
    # SSH na Windows
    script = f"import sys; sys.path.insert(0,'D:/python_libs'); sys.path.insert(0,'C:/Users/pan_jeskyne/spark-tts'); import soundfile as sf; from cli.SparkTTS import SparkTTS; tts = SparkTTS(model_dir='C:/Users/pan_jeskyne/spark-tts/models/models--SparkAudio--Spark-TTS-0.5B/snapshots/642071559bfc6346c2359d19dcb6be3f9dd8a05d', device='cuda'); wav = tts.inference(text='{text}', prompt_speech_path='{ref}', gender='male', pitch='moderate', speed='moderate'); sf.write('D:/asgard_voice_out.wav', wav, 16000); print('DONE!')"
    result = subprocess.run(
        ["ssh", "pan_jeskyne@192.168.123.191", f"python -c \"{script}\""],
        capture_output=True, text=True, timeout=120
    )
    print(result.stdout or result.stderr)


def main():
    parser = argparse.ArgumentParser(
        prog="asgard",
        description="Asgard CLI — Jeden terminál, celý Web4Light."
    )
    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="Stav služeb")

    # prove
    sub.add_parser("prove", help="SPARK prove všech modulů")

    # translate
    p = sub.add_parser("translate", help="Přelož YouTube video")
    p.add_argument("url")
    p.add_argument("--to", default="cs")

    # dirigent
    p = sub.add_parser("dirigent", help="Dirigent orchestrátor")
    p.add_argument("--status", action="store_true")

    # vision
    p = sub.add_parser("vision", help="Popis obrázku")
    p.add_argument("image")

    # scada
    sub.add_parser("scada", help="Vygeneruj SCADA SVG")

    # sign
    p = sub.add_parser("sign", help="Znaková řeč")
    p.add_argument("text", nargs="+")

    # cave
    p = sub.add_parser("cave", help="Cave Lab — web generátor")
    p.add_argument("prompt", nargs="+")

    # voice
    p = sub.add_parser("voice", help="Voice cloning (Spark-TTS)")
    p.add_argument("text", nargs="+")
    p.add_argument("--ref", default="")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "prove":
        cmd_prove()
    elif args.command == "translate":
        cmd_translate(args)
    elif args.command == "dirigent":
        cmd_dirigent(args)
    elif args.command == "vision":
        cmd_vision(args)
    elif args.command == "scada":
        cmd_scada()
    elif args.command == "sign":
        cmd_sign(args)
    elif args.command == "cave":
        cmd_cave(args)
    elif args.command == "voice":
        cmd_voice(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
