"""
Subtitle Translator — Asgard Lab / UTL
========================================

Pipeline: SRT/VTT vstup → Gemini překlad → SRT/VTT výstup

Přeloží titulky z jakéhokoliv jazyka do cílového jazyka pomocí Gemini API.
Zachovává timing, formátování a strukturu titulků.

Použití:
    python subtitle_translator.py input.srt --target cs --output output.srt
    python subtitle_translator.py input.vtt --target ja --output output.vtt

Autor: Pan Jeskyně
Asistent: Kiro
Organizace: Rebirth Phoenix Foundation Charter
Projekt: XPRIZE Build with Gemini — Asgard Lab
"""

import os
import re
import sys
import time
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import srt

# === AI ENGINES (Gemini nebo Groq) ===

try:
    from google import genai
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False

try:
    from groq import Groq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False

# === LOGGING ===

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TRANSLATOR] %(message)s"
)
logger = logging.getLogger(__name__)

# === CONSTANTS ===

# Gemini model — aktuální, rychlý, 1M tokenů
GEMINI_MODEL = "gemini-2.5-flash"

# Maximální počet titulků v jednom batchi pro překlad
BATCH_SIZE = 50

# Podporované formáty
SUPPORTED_FORMATS = {".srt", ".vtt"}

# Jazyky — zobrazované názvy
LANGUAGE_NAMES = {
    "cs": "čeština",
    "sk": "slovenština",
    "en": "angličtina",
    "de": "němčina",
    "fr": "francouzština",
    "es": "španělština",
    "it": "italština",
    "ja": "japonština",
    "ko": "korejština",
    "zh": "čínština",
    "pl": "polština",
    "ru": "ruština",
    "uk": "ukrajinština",
    "pt": "portugalština",
    "nl": "holandština",
    "ar": "arabština",
    "hi": "hindština",
    "tr": "turečtina",
    "sv": "švédština",
    "da": "dánština",
    "no": "norština",
    "fi": "finština",
}


# === DATA MODELS ===

@dataclass
class TranslationStats:
    """Statistiky překladu."""
    total_subtitles: int = 0
    translated_subtitles: int = 0
    failed_subtitles: int = 0
    total_characters: int = 0
    elapsed_seconds: float = 0.0
    source_lang: str = "auto"
    target_lang: str = "cs"

    @property
    def success_rate(self) -> float:
        if self.total_subtitles == 0:
            return 0.0
        return self.translated_subtitles / self.total_subtitles * 100

    def summary(self) -> str:
        return (
            f"Přeloženo: {self.translated_subtitles}/{self.total_subtitles} "
            f"({self.success_rate:.1f}%) | "
            f"Znaků: {self.total_characters} | "
            f"Čas: {self.elapsed_seconds:.1f}s | "
            f"Jazyk: {self.source_lang} → {self.target_lang}"
        )


# === VTT PARSER ===

def parse_vtt(content: str) -> list[srt.Subtitle]:
    """Parse WebVTT soubor do seznamu Subtitle objektů.

    WebVTT je podobný SRT ale má header 'WEBVTT' a používá
    tečku místo čárky v časech.
    """
    # Odstranit WEBVTT header a metadata
    lines = content.strip().split("\n")
    srt_lines = []
    header_done = False
    index = 1

    for line in lines:
        # Přeskočit WEBVTT header
        if not header_done:
            if line.strip() == "" and srt_lines == []:
                continue
            if line.startswith("WEBVTT"):
                continue
            if line.startswith("Kind:") or line.startswith("Language:"):
                continue
            if line.strip() == "":
                header_done = True
                continue
            header_done = True

        # Konvertovat VTT timestamps na SRT formát (tečka → čárka)
        if "-->" in line:
            # Přidat index před timestamp
            srt_lines.append(str(index))
            index += 1
            # Nahradit tečku čárkou v timestamps
            line = line.replace(".", ",", 2)
            # Odstranit position/alignment metadata za timestamps
            parts = line.split("-->")
            if len(parts) == 2:
                start = parts[0].strip()
                end_and_meta = parts[1].strip().split(" ")
                end = end_and_meta[0].strip()
                # Doplnit hodiny pokud chybí (VTT může mít MM:SS.mmm)
                if start.count(":") == 1:
                    start = "00:" + start
                if end.count(":") == 1:
                    end = "00:" + end
                line = f"{start} --> {end}"

        srt_lines.append(line)

    srt_content = "\n".join(srt_lines)
    return list(srt.parse(srt_content))


def compose_vtt(subtitles: list[srt.Subtitle]) -> str:
    """Compose WebVTT output z seznamu Subtitle objektů."""
    lines = ["WEBVTT", ""]

    for sub in subtitles:
        # Formát timestamps VTT (čárka → tečka)
        start = srt.timedelta_to_srt_timestamp(sub.start).replace(",", ".")
        end = srt.timedelta_to_srt_timestamp(sub.end).replace(",", ".")
        lines.append(f"{start} --> {end}")
        lines.append(sub.content)
        lines.append("")

    return "\n".join(lines)


# === GEMINI TRANSLATION ===

class GeminiSubtitleTranslator:
    """Překladač titulků pomocí Gemini API nebo Groq (fallback).

    Přeloží titulky po batchích, zachovává timing a strukturu.
    Pokud Gemini není dostupný, použije Groq (llama-3.3-70b).
    """

    def __init__(self, api_key: Optional[str] = None,
                 model: str = GEMINI_MODEL,
                 engine: str = "auto"):
        """Inicializace překladače.

        Args:
            api_key: Gemini API klíč. Pokud None, použije env GEMINI_API_KEY.
            model: Gemini model pro překlad.
            engine: 'gemini', 'groq', nebo 'auto' (zkusí gemini, pak groq).
        """
        self._engine = engine
        self._gemini_client = None
        self._groq_client = None
        self._model = model
        self._groq_model = "llama-3.3-70b-versatile"

        if engine in ("gemini", "auto") and _GEMINI_AVAILABLE:
            try:
                if api_key is None:
                    api_key = self._load_api_key("gemini")
                self._gemini_client = genai.Client(api_key=api_key)
                logger.info(f"Gemini překladač inicializován (model={model})")
            except Exception as e:
                logger.warning(f"Gemini nedostupný: {e}")

        if engine in ("groq", "auto") and _GROQ_AVAILABLE:
            try:
                groq_key = self._load_api_key("groq")
                os.environ["GROQ_API_KEY"] = groq_key
                self._groq_client = Groq()
                logger.info(f"Groq překladač inicializován (model={self._groq_model})")
            except Exception as e:
                logger.warning(f"Groq nedostupný: {e}")

        if not self._gemini_client and not self._groq_client:
            raise ValueError(
                "Žádný AI engine nedostupný. Nastav GEMINI_API_KEY nebo GROQ_API_KEY."
            )

    def _load_api_key(self, engine: str = "gemini") -> str:
        """Načte API klíč z env nebo souboru."""
        if engine == "groq":
            # 1. Env
            key = os.environ.get("GROQ_API_KEY")
            if key:
                return key
            # 2. Soubor
            key_file = Path.home() / ".groq_api_key"
            if key_file.exists():
                content = key_file.read_text().strip()
                if "=" in content:
                    return content.split("=", 1)[1].strip()
                return content
            raise ValueError("Groq API klíč nenalezen")

        # Gemini
        # 1. Environment variable
        key = os.environ.get("GEMINI_API_KEY")
        if key:
            return key

        # 2. Soubor ~/.gemini_api_key
        key_file = Path.home() / ".gemini_api_key"
        if key_file.exists():
            content = key_file.read_text().strip()
            # Formát: GEMINI_API_KEY=xxx nebo jen xxx
            if "=" in content:
                key = content.split("=", 1)[1].strip()
            else:
                key = content
            if key:
                return key

        # 3. gala_key.conf
        gala_conf = Path.home() / "Universal-Translation-Layer" / "gala_key.conf"
        if gala_conf.exists():
            content = gala_conf.read_text().strip()
            if "=" in content:
                key = content.split("=", 1)[1].strip()
            else:
                key = content
            if key:
                return key

        raise ValueError(
            "Gemini API klíč nenalezen. Nastav GEMINI_API_KEY env "
            "nebo ulož do ~/.gemini_api_key"
        )

    def translate_subtitles(
        self,
        subtitles: list[srt.Subtitle],
        target_lang: str = "cs",
        source_lang: str = "auto",
        batch_size: int = BATCH_SIZE,
    ) -> tuple[list[srt.Subtitle], TranslationStats]:
        """Přelož seznam titulků do cílového jazyka.

        Args:
            subtitles: Seznam titulků k překladu.
            target_lang: Cílový jazyk (ISO 639-1 kód).
            source_lang: Zdrojový jazyk ('auto' pro autodetekci).
            batch_size: Počet titulků v jednom API volání.

        Returns:
            Tuple (přeložené titulky, statistiky).
        """
        stats = TranslationStats(
            total_subtitles=len(subtitles),
            source_lang=source_lang,
            target_lang=target_lang,
        )

        start_time = time.time()
        translated = []

        # Zpracuj po batchích
        for i in range(0, len(subtitles), batch_size):
            batch = subtitles[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(subtitles) + batch_size - 1) // batch_size

            logger.info(
                f"Překládám batch {batch_num}/{total_batches} "
                f"({len(batch)} titulků)..."
            )

            translated_batch = self._translate_batch(
                batch, target_lang, source_lang
            )

            for orig, trans_text in zip(batch, translated_batch):
                if trans_text is not None:
                    new_sub = srt.Subtitle(
                        index=orig.index,
                        start=orig.start,
                        end=orig.end,
                        content=trans_text,
                    )
                    translated.append(new_sub)
                    stats.translated_subtitles += 1
                    stats.total_characters += len(trans_text)
                else:
                    # Fallback: ponechat originál
                    translated.append(orig)
                    stats.failed_subtitles += 1

        stats.elapsed_seconds = time.time() - start_time
        return translated, stats

    def _translate_batch(
        self,
        batch: list[srt.Subtitle],
        target_lang: str,
        source_lang: str,
    ) -> list[Optional[str]]:
        """Přelož batch titulků jedním API voláním.

        Posílá všechny texty jako číslovaný seznam, Gemini přeloží
        a vrátí stejně číslovaný seznam.
        """
        # Sestavit prompt
        lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)
        source_info = ""
        if source_lang != "auto":
            source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
            source_info = f" ze zdrojového jazyka ({source_name})"

        # Číslovaný seznam textů
        numbered_texts = []
        for i, sub in enumerate(batch, 1):
            # Odstranit HTML tagy z titulků (bold, italic)
            clean_text = re.sub(r'<[^>]+>', '', sub.content)
            numbered_texts.append(f"{i}. {clean_text}")

        texts_block = "\n".join(numbered_texts)

        prompt = f"""Přelož následující titulky{source_info} do jazyka: {lang_name}.

Pravidla:
- Zachovej číslování (1., 2., 3., ...)
- Překládej přirozeně, ne doslovně
- Zachovej styl a tón originálu
- Pokud je text krátký (citoslovce, jména), ponech jak je nebo přelož smysluplně
- Nekomentuj, nevysvětluj — jen přeložené texty
- Každý překlad na novém řádku ve formátu: ČÍSLO. PŘEKLAD

Titulky k překladu:
{texts_block}"""

        try:
            # Zkusit Gemini, pak Groq
            if self._gemini_client:
                try:
                    response = self._gemini_client.models.generate_content(
                        model=self._model,
                        contents=prompt,
                    )
                    return self._parse_batch_response(response.text, len(batch))
                except Exception as e:
                    logger.warning(f"Gemini selhalo: {e}, zkouším Groq...")

            if self._groq_client:
                response = self._groq_client.chat.completions.create(
                    model=self._groq_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000,
                )
                return self._parse_batch_response(
                    response.choices[0].message.content, len(batch)
                )

            return [None] * len(batch)

        except Exception as e:
            logger.error(f"AI překlad chyba: {e}")
            # Vrátit None pro všechny v batchi
            return [None] * len(batch)

    def _parse_batch_response(
        self, response_text: str, expected_count: int
    ) -> list[Optional[str]]:
        """Parse odpověď Gemini — číslovaný seznam překladů.

        Args:
            response_text: Raw text odpovědi z Gemini.
            expected_count: Očekávaný počet překladů.

        Returns:
            Seznam přeložených textů (nebo None pro chybějící).
        """
        results: list[Optional[str]] = [None] * expected_count

        if not response_text:
            return results

        # Parse číslovaný seznam
        lines = response_text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match formát: "1. překlad" nebo "1) překlad"
            match = re.match(r'^(\d+)[.)]\s*(.+)$', line)
            if match:
                idx = int(match.group(1)) - 1  # 0-based
                text = match.group(2).strip()
                if 0 <= idx < expected_count:
                    results[idx] = text

        # Pokud se nepodařilo parsovat čísla, zkusit řádek po řádku
        if all(r is None for r in results) and len(lines) >= expected_count:
            for i, line in enumerate(lines[:expected_count]):
                line = line.strip()
                if line:
                    # Odstranit případné číslo na začátku
                    cleaned = re.sub(r'^\d+[.)]\s*', '', line)
                    results[i] = cleaned if cleaned else line

        return results


# === FILE I/O ===

def detect_format(filepath: Path) -> str:
    """Detekuj formát titulků podle přípony a obsahu."""
    suffix = filepath.suffix.lower()
    if suffix == ".vtt":
        return "vtt"
    if suffix == ".srt":
        return "srt"

    # Zkusit detekovat z obsahu
    content = filepath.read_text(encoding="utf-8")
    if content.strip().startswith("WEBVTT"):
        return "vtt"
    return "srt"


def load_subtitles(filepath: Path) -> tuple[list[srt.Subtitle], str]:
    """Načti titulky ze souboru.

    Returns:
        Tuple (seznam titulků, detekovaný formát).
    """
    content = filepath.read_text(encoding="utf-8")
    fmt = detect_format(filepath)

    if fmt == "vtt":
        subtitles = parse_vtt(content)
    else:
        subtitles = list(srt.parse(content))

    logger.info(f"Načteno {len(subtitles)} titulků z {filepath} (formát: {fmt})")
    return subtitles, fmt


def save_subtitles(
    subtitles: list[srt.Subtitle],
    filepath: Path,
    fmt: str = "srt"
) -> None:
    """Ulož titulky do souboru.

    Args:
        subtitles: Seznam přeložených titulků.
        filepath: Cesta výstupního souboru.
        fmt: Formát výstupu ('srt' nebo 'vtt').
    """
    if fmt == "vtt":
        content = compose_vtt(subtitles)
    else:
        content = srt.compose(subtitles)

    filepath.write_text(content, encoding="utf-8")
    logger.info(f"Uloženo {len(subtitles)} titulků do {filepath} (formát: {fmt})")


# === MAIN PIPELINE ===

def translate_file(
    input_path: str,
    target_lang: str = "cs",
    source_lang: str = "auto",
    output_path: Optional[str] = None,
    output_format: Optional[str] = None,
) -> TranslationStats:
    """Hlavní pipeline: načti → přelož → ulož.

    Args:
        input_path: Cesta k vstupnímu souboru s titulky.
        target_lang: Cílový jazyk (ISO 639-1).
        source_lang: Zdrojový jazyk ('auto' = autodetekce).
        output_path: Cesta výstupu. Pokud None, generuje se automaticky.
        output_format: Formát výstupu ('srt'/'vtt'). Pokud None, stejný jako vstup.

    Returns:
        TranslationStats se statistikami překladu.
    """
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Soubor nenalezen: {input_path}")

    if input_file.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Nepodporovaný formát: {input_file.suffix}. "
            f"Podporované: {SUPPORTED_FORMATS}"
        )

    # 1. Načti titulky
    subtitles, detected_format = load_subtitles(input_file)

    if not subtitles:
        logger.warning("Žádné titulky k překladu!")
        return TranslationStats()

    # 2. Přelož
    translator = GeminiSubtitleTranslator()
    translated, stats = translator.translate_subtitles(
        subtitles,
        target_lang=target_lang,
        source_lang=source_lang,
    )

    # 3. Urči výstupní formát a cestu
    out_fmt = output_format or detected_format

    if output_path is None:
        # Generuj název: input_cs.srt
        stem = input_file.stem
        suffix = f".{out_fmt}"
        output_path = str(input_file.parent / f"{stem}_{target_lang}{suffix}")

    out_file = Path(output_path)

    # 4. Ulož
    save_subtitles(translated, out_file, fmt=out_fmt)

    # 5. Výpis statistik
    logger.info(f"✓ {stats.summary()}")
    logger.info(f"✓ Výstup: {out_file}")

    return stats


# === CLI ===

def main():
    """CLI entry point pro překlad titulků."""
    parser = argparse.ArgumentParser(
        description="Asgard Lab — Překladač titulků pomocí Gemini AI",
        epilog="Příklad: python subtitle_translator.py film.srt --target cs"
    )
    parser.add_argument(
        "input",
        help="Vstupní soubor s titulky (SRT nebo VTT)"
    )
    parser.add_argument(
        "--target", "-t",
        default="cs",
        help="Cílový jazyk (ISO 639-1 kód, výchozí: cs)"
    )
    parser.add_argument(
        "--source", "-s",
        default="auto",
        help="Zdrojový jazyk (výchozí: auto = autodetekce)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Výstupní soubor (výchozí: input_LANG.srt/vtt)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["srt", "vtt"],
        default=None,
        help="Výstupní formát (výchozí: stejný jako vstup)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=BATCH_SIZE,
        help=f"Počet titulků na batch (výchozí: {BATCH_SIZE})"
    )

    args = parser.parse_args()

    print("═══════════════════════════════════════════════")
    print("  🌍 Asgard Lab — Subtitle Translator")
    print("  Powered by Gemini AI")
    print("═══════════════════════════════════════════════")
    print()

    try:
        stats = translate_file(
            input_path=args.input,
            target_lang=args.target,
            source_lang=args.source,
            output_path=args.output,
            output_format=args.format,
        )
        print()
        print(f"  ✓ Hotovo! {stats.summary()}")
        print()
    except Exception as e:
        logger.error(f"Chyba: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
