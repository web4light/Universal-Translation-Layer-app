"""
Asgard Lab — Demo CLI Interface
==================================

Jednoduchý interface pro celý pipeline:
  Titulky → Překlad → Dabing → Znaková řeč

Režimy:
  1. translate  — přeloží titulky
  2. dub        — přeloží + nadabuje
  3. sign       — přeloží + znaková řeč
  4. full       — všechno (1+1=3: překlad + dabing + znaková řeč)

Použití:
    python asgard_demo.py full input.srt --target cs
    python asgard_demo.py translate input.vtt --target ja
    python asgard_demo.py dub input.srt --target de
    python asgard_demo.py sign input.srt --target czj

Autor: Pan Jeskyně
Asistent: Kiro
Organizace: Rebirth Phoenix Foundation Charter
Projekt: XPRIZE Build with Gemini — Asgard Lab
"""

import sys
import time
import argparse
import logging
import tempfile
import subprocess
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ASGARD] %(message)s"
)
logger = logging.getLogger(__name__)

# Přidej src do path
sys.path.insert(0, str(Path(__file__).parent))

from subtitle_translator import translate_file, load_subtitles, LANGUAGE_NAMES
from tts_dubber import dub_file
from sign_language_renderer import SignLanguageRenderer, SignLanguage


# === BANNER ===

BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ⚡ ASGARD LAB — Universal Translation Layer                ║
║                                                               ║
║   🌍 Překlad titulků (22 jazyků)                             ║
║   🎙️  AI Dabing (text-to-speech)                              ║
║   🤟 Znaková řeč (ZDARMA pro neslyšící)                      ║
║                                                               ║
║   Powered by: Gemini AI + Ada/SPARK                           ║
║   Princip: 1+1=3 — tři výstupy z jednoho vstupu              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""


# === YOUTUBE SUBTITLE DOWNLOADER ===

def download_youtube_subs(url: str, lang: str = "en",
                          output_dir: str = None) -> str:
    """Stáhne titulky z YouTube videa.

    Používá yt-dlp pro stažení auto-generated nebo manuálních titulků.

    Args:
        url: YouTube URL.
        lang: Preferovaný jazyk titulků (výchozí: en).
        output_dir: Adresář pro výstup. Pokud None, použije tmp.

    Returns:
        Cesta ke staženému SRT souboru.
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="asgard_yt_")

    output_template = str(Path(output_dir) / "%(title).50s.%(ext)s")

    # Zkusit manuální titulky, pak auto-generated
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-lang", lang,
        "--sub-format", "srt",
        "--convert-subs", "srt",
        "-o", output_template,
        url,
    ]

    logger.info(f"Stahuji titulky z YouTube: {url}")
    logger.info(f"Jazyk: {lang}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            # Zkusit bez specifikace jazyka (stáhne co je dostupné)
            cmd_fallback = [
                "yt-dlp",
                "--skip-download",
                "--write-auto-subs",
                "--sub-format", "srt",
                "--convert-subs", "srt",
                "-o", output_template,
                url,
            ]
            result = subprocess.run(
                cmd_fallback, capture_output=True, text=True, timeout=60
            )

    except subprocess.TimeoutExpired:
        raise RuntimeError("YouTube download timeout (60s)")
    except FileNotFoundError:
        raise RuntimeError("yt-dlp není nainstalován: pip install yt-dlp")

    # Najít stažený SRT soubor
    srt_files = list(Path(output_dir).glob("*.srt"))
    if not srt_files:
        raise RuntimeError(
            f"Nepodařilo se stáhnout titulky z {url}. "
            f"Video možná nemá titulky.\n"
            f"yt-dlp output: {result.stderr[:200]}"
        )

    srt_path = str(srt_files[0])
    logger.info(f"✓ Titulky staženy: {srt_path}")
    return srt_path


def is_youtube_url(text: str) -> bool:
    """Zjistí jestli je vstup YouTube URL."""
    return any(x in text for x in [
        "youtube.com/watch",
        "youtu.be/",
        "youtube.com/shorts",
    ])


# === PIPELINE COMMANDS ===

def cmd_translate(args):
    """Přeloží titulky do cílového jazyka."""
    # YouTube auto-detect
    if is_youtube_url(args.input):
        print(f"\n  📺 Detekován YouTube link, stahuji titulky...\n")
        args.input = download_youtube_subs(
            args.input, lang=args.source if args.source != "auto" else "en"
        )

    print(f"\n  🌍 Překládám: {args.input} → {args.target}\n")
    stats = translate_file(
        input_path=args.input,
        target_lang=args.target,
        source_lang=args.source,
        output_path=args.output,
    )
    return stats


def cmd_dub(args):
    """Přeloží titulky + vytvoří audio dabing."""
    # YouTube auto-detect
    if is_youtube_url(args.input):
        print(f"\n  📺 Detekován YouTube link, stahuji titulky...\n")
        args.input = download_youtube_subs(
            args.input, lang=args.source if args.source != "auto" else "en"
        )

    # 1. Přeloží
    print(f"\n  🌍 Krok 1/2: Překládám titulky → {args.target}\n")

    input_path = Path(args.input)
    translated_path = args.output_srt or str(
        input_path.parent / f"{input_path.stem}_{args.target}.srt"
    )

    stats_translate = translate_file(
        input_path=args.input,
        target_lang=args.target,
        source_lang=args.source,
        output_path=translated_path,
    )

    # 2. Dabuj
    print(f"\n  🎙️  Krok 2/2: Generuji dabing\n")

    output_audio = args.output or str(
        input_path.parent / f"{input_path.stem}_{args.target}_dubbed.mp3"
    )

    stats_dub = dub_file(
        input_path=translated_path,
        output_path=output_audio,
        engine=args.engine,
        lang=args.target,
    )

    print(f"\n  ✓ Překlad: {stats_translate.summary()}")
    print(f"  ✓ Dabing:  {stats_dub.summary()}")
    return stats_dub


def cmd_sign(args):
    """Přeloží titulky + vytvoří znakovou řeč."""
    # YouTube auto-detect
    if is_youtube_url(args.input):
        print(f"\n  📺 Detekován YouTube link, stahuji titulky...\n")
        args.input = download_youtube_subs(
            args.input, lang=args.source if args.source != "auto" else "en"
        )

    # 1. Přeloží
    print(f"\n  🌍 Krok 1/2: Překládám titulky → {args.target}\n")

    input_path = Path(args.input)
    translated_path = str(
        input_path.parent / f"{input_path.stem}_{args.target}.srt"
    )

    stats_translate = translate_file(
        input_path=args.input,
        target_lang=args.target,
        source_lang=args.source,
        output_path=translated_path,
    )

    # 2. Znaková řeč
    print(f"\n  🤟 Krok 2/2: Generuji znakovou řeč\n")

    sign_lang = SignLanguage.CZJ  # Výchozí
    if args.sign_lang:
        sign_lang = SignLanguage(args.sign_lang)

    renderer = SignLanguageRenderer(language=sign_lang, use_gemini=True)

    output_json = args.output or str(
        input_path.parent / f"{input_path.stem}_signs.json"
    )

    stats_sign = renderer.render_subtitles(translated_path, output_json)

    print(f"\n  ✓ Překlad:      {stats_translate.summary()}")
    print(f"  ✓ Znaková řeč:  {stats_sign.summary()}")
    return stats_sign


def cmd_full(args):
    """Plný pipeline: překlad + dabing + znaková řeč (1+1=3)."""
    start_time = time.time()
    input_path = Path(args.input)

    # YouTube auto-detect
    if is_youtube_url(args.input):
        print(f"\n  📺 Detekován YouTube link, stahuji titulky...\n")
        srt_path = download_youtube_subs(
            args.input, lang=args.source if args.source != "auto" else "en"
        )
        input_path = Path(srt_path)
        args.input = srt_path

    # 1. Přeloží
    print(f"\n  🌍 Krok 1/3: Překládám titulky → {args.target}\n")

    translated_path = args.output_srt or str(
        input_path.parent / f"{input_path.stem}_{args.target}.srt"
    )

    stats_translate = translate_file(
        input_path=args.input,
        target_lang=args.target,
        source_lang=args.source,
        output_path=translated_path,
    )

    # 2. Dabuj
    print(f"\n  🎙️  Krok 2/3: Generuji dabing\n")

    output_audio = args.output or str(
        input_path.parent / f"{input_path.stem}_{args.target}_dubbed.mp3"
    )

    stats_dub = dub_file(
        input_path=translated_path,
        output_path=output_audio,
        engine=args.engine,
        lang=args.target,
    )

    # 3. Znaková řeč
    print(f"\n  🤟 Krok 3/3: Generuji znakovou řeč\n")

    sign_lang = SignLanguage.CZJ
    if args.sign_lang:
        sign_lang = SignLanguage(args.sign_lang)

    renderer = SignLanguageRenderer(language=sign_lang, use_gemini=True)

    output_json = str(
        input_path.parent / f"{input_path.stem}_signs.json"
    )

    stats_sign = renderer.render_subtitles(translated_path, output_json)

    # Souhrn
    total_time = time.time() - start_time
    print("\n" + "═" * 60)
    print("  📊 SOUHRN (1+1=3)")
    print("═" * 60)
    print(f"  🌍 Překlad:      {stats_translate.summary()}")
    print(f"  🎙️  Dabing:       {stats_dub.summary()}")
    print(f"  🤟 Znaková řeč:  {stats_sign.summary()}")
    print(f"  ⏱️  Celkový čas:  {total_time:.1f}s")
    print("═" * 60)
    print(f"  Výstupy:")
    print(f"    📄 Titulky:      {translated_path}")
    print(f"    🔊 Audio:        {output_audio}")
    print(f"    🤟 Znaky (JSON): {output_json}")
    print("═" * 60)
    print()

    return stats_translate


# === MAIN CLI ===

def main():
    parser = argparse.ArgumentParser(
        description="Asgard Lab — Universal Translation Layer Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Příklady:
  python asgard_demo.py full film.srt --target cs
  python asgard_demo.py translate news.vtt --target ja
  python asgard_demo.py dub film.srt --target de --engine gtts
  python asgard_demo.py sign film.srt --target cs --sign-lang czj
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Příkaz")

    # --- translate ---
    p_trans = subparsers.add_parser("translate", help="Přeloží titulky")
    p_trans.add_argument("input", help="Vstupní SRT/VTT soubor")
    p_trans.add_argument("--target", "-t", default="cs", help="Cílový jazyk")
    p_trans.add_argument("--source", "-s", default="auto", help="Zdrojový jazyk")
    p_trans.add_argument("--output", "-o", default=None, help="Výstupní soubor")

    # --- dub ---
    p_dub = subparsers.add_parser("dub", help="Přeloží + nadabuje")
    p_dub.add_argument("input", help="Vstupní SRT/VTT soubor")
    p_dub.add_argument("--target", "-t", default="cs", help="Cílový jazyk")
    p_dub.add_argument("--source", "-s", default="auto", help="Zdrojový jazyk")
    p_dub.add_argument("--output", "-o", default=None, help="Výstupní audio")
    p_dub.add_argument("--output-srt", default=None, help="Výstupní přeložené titulky")
    p_dub.add_argument("--engine", "-e", default="gtts", choices=["gtts", "coqui", "gemini"])

    # --- sign ---
    p_sign = subparsers.add_parser("sign", help="Přeloží + znaková řeč")
    p_sign.add_argument("input", help="Vstupní SRT/VTT soubor")
    p_sign.add_argument("--target", "-t", default="cs", help="Cílový jazyk")
    p_sign.add_argument("--source", "-s", default="auto", help="Zdrojový jazyk")
    p_sign.add_argument("--output", "-o", default=None, help="Výstupní JSON")
    p_sign.add_argument("--sign-lang", default="czj", choices=["czj", "asl", "bsl", "dgs"])

    # --- full ---
    p_full = subparsers.add_parser("full", help="Plný pipeline (1+1=3)")
    p_full.add_argument("input", help="Vstupní SRT/VTT soubor")
    p_full.add_argument("--target", "-t", default="cs", help="Cílový jazyk")
    p_full.add_argument("--source", "-s", default="auto", help="Zdrojový jazyk")
    p_full.add_argument("--output", "-o", default=None, help="Výstupní audio")
    p_full.add_argument("--output-srt", default=None, help="Výstupní titulky")
    p_full.add_argument("--engine", "-e", default="gtts", choices=["gtts", "coqui", "gemini"])
    p_full.add_argument("--sign-lang", default="czj", choices=["czj", "asl", "bsl", "dgs"])

    args = parser.parse_args()

    print(BANNER)

    if not args.command:
        parser.print_help()
        print("\n  💡 Tip: python asgard_demo.py full film.srt --target cs\n")
        sys.exit(0)

    try:
        if args.command == "translate":
            cmd_translate(args)
        elif args.command == "dub":
            cmd_dub(args)
        elif args.command == "sign":
            cmd_sign(args)
        elif args.command == "full":
            cmd_full(args)
    except KeyboardInterrupt:
        print("\n  ⚠ Přerušeno uživatelem")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Chyba: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
