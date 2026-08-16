"""
Sign Language Renderer — Asgard Lab / UTL
============================================

Pipeline: Text → Gemini (glosování) → Sekvence znaků → Avatar animace

Generuje znakovou řeč z přeloženého textu pro neslyšící.
Podobně jako tlumočník v rohu obrazovky na ČT1.

Přístup:
1. Text → Gemini rozloží na glosy (základní znaky)
2. Glosy → mapování na animační sekvence
3. Sekvence → SVG/video avatar (nebo instrukce pro 3D renderer)

ZDARMA pro lidi s hendikepem — sociální mise Asgard Lab.

Podporované znakové jazyky:
- ČZJ (Český znakový jazyk)
- ASL (American Sign Language)
- BSL (British Sign Language)
- DGS (Deutsche Gebärdensprache)

Použití:
    python sign_language_renderer.py "Dobrý den, jak se máte?" --lang czj
    python sign_language_renderer.py --input subtitles.srt --output signs.json

Autor: Pan Jeskyně
Asistent: Kiro
Organizace: Rebirth Phoenix Foundation Charter
Projekt: XPRIZE Build with Gemini — Asgard Lab
Licence: ZDARMA pro osoby se sluchovým hendikepem
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

# === LOGGING ===

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SIGN-LANG] %(message)s"
)
logger = logging.getLogger(__name__)

# === OPTIONAL: Gemini pro glosování ===

try:
    from google import genai
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False


# === CONSTANTS ===

GEMINI_MODEL = "gemini-2.5-flash"


# === ENUMS ===

class SignLanguage(Enum):
    """Podporované znakové jazyky."""
    CZJ = "czj"    # Český znakový jazyk
    ASL = "asl"    # American Sign Language
    BSL = "bsl"    # British Sign Language
    DGS = "dgs"    # Deutsche Gebärdensprache
    ISL = "isl"    # International Sign Language


class HandShape(Enum):
    """Základní tvary rukou pro znakový jazyk."""
    FLAT = "flat"           # Plochá dlaň
    FIST = "fist"           # Pěst
    POINT = "point"         # Ukazováček
    SPREAD = "spread"       # Roztažené prsty
    PINCH = "pinch"         # Špetka
    HOOK = "hook"           # Hák
    C_SHAPE = "c_shape"     # Tvar C
    O_SHAPE = "o_shape"     # Tvar O
    V_SHAPE = "v_shape"     # Tvar V (dva prsty)
    THUMB_UP = "thumb_up"   # Palec nahoru


class SignLocation(Enum):
    """Pozice znaku vůči tělu."""
    HEAD = "head"
    FOREHEAD = "forehead"
    CHIN = "chin"
    CHEST = "chest"
    SHOULDER = "shoulder"
    NEUTRAL = "neutral"     # Neutrální prostor před tělem
    SIDE = "side"


class SignMovement(Enum):
    """Typ pohybu."""
    NONE = "none"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    CIRCULAR = "circular"
    WAVE = "wave"
    FORWARD = "forward"
    BACKWARD = "backward"


# === DATA MODELS ===

@dataclass
class SignGloss:
    """Jedna glosa (základní jednotka znakového jazyka).

    Glosa = slovní reprezentace jednoho znaku.
    Např: "DOBRÝ-DEN" = jeden znak v ČZJ.
    """
    gloss: str                          # Textová glosa (velkými písmeny)
    dominant_hand: HandShape = HandShape.FLAT
    non_dominant_hand: Optional[HandShape] = None
    location: SignLocation = SignLocation.NEUTRAL
    movement: SignMovement = SignMovement.NONE
    duration_ms: int = 500              # Délka znaku v ms
    facial_expression: str = "neutral"  # Mimika (důležitá v ZJ!)
    repetitions: int = 1                # Počet opakování pohybu


@dataclass
class SignSequence:
    """Sekvence znaků pro jednu větu/frázi."""
    text: str                           # Původní text
    language: SignLanguage = SignLanguage.CZJ
    glosses: list[SignGloss] = field(default_factory=list)
    total_duration_ms: int = 0
    timestamp_start_ms: int = 0         # Pro synchronizaci s videem
    timestamp_end_ms: int = 0

    @property
    def gloss_string(self) -> str:
        """Textová reprezentace glos."""
        return " ".join(g.gloss for g in self.glosses)

    def to_dict(self) -> dict:
        """Serializace pro JSON export."""
        return {
            "text": self.text,
            "language": self.language.value,
            "gloss_string": self.gloss_string,
            "timestamp_start_ms": self.timestamp_start_ms,
            "timestamp_end_ms": self.timestamp_end_ms,
            "total_duration_ms": self.total_duration_ms,
            "glosses": [
                {
                    "gloss": g.gloss,
                    "dominant_hand": g.dominant_hand.value,
                    "non_dominant_hand": g.non_dominant_hand.value if g.non_dominant_hand else None,
                    "location": g.location.value,
                    "movement": g.movement.value,
                    "duration_ms": g.duration_ms,
                    "facial_expression": g.facial_expression,
                    "repetitions": g.repetitions,
                }
                for g in self.glosses
            ],
        }


@dataclass
class RenderStats:
    """Statistiky renderování."""
    total_phrases: int = 0
    total_glosses: int = 0
    total_duration_ms: int = 0
    elapsed_seconds: float = 0.0
    language: str = "czj"

    def summary(self) -> str:
        return (
            f"Fráze: {self.total_phrases} | "
            f"Znaků: {self.total_glosses} | "
            f"Délka: {self.total_duration_ms/1000:.1f}s | "
            f"Jazyk: {self.language} | "
            f"Čas: {self.elapsed_seconds:.1f}s"
        )


# === GLOSS DATABASE ===
# Základní slovník ČZJ glos s parametry animace
# V produkci by toto byl velký dataset, zde prototyp

CZJ_GLOSS_DB: dict[str, SignGloss] = {
    "DOBRÝ-DEN": SignGloss(
        gloss="DOBRÝ-DEN",
        dominant_hand=HandShape.FLAT,
        location=SignLocation.FOREHEAD,
        movement=SignMovement.FORWARD,
        duration_ms=600,
        facial_expression="smile",
    ),
    "JÁ": SignGloss(
        gloss="JÁ",
        dominant_hand=HandShape.POINT,
        location=SignLocation.CHEST,
        movement=SignMovement.NONE,
        duration_ms=300,
    ),
    "TY": SignGloss(
        gloss="TY",
        dominant_hand=HandShape.POINT,
        location=SignLocation.NEUTRAL,
        movement=SignMovement.FORWARD,
        duration_ms=300,
    ),
    "DĚKUJI": SignGloss(
        gloss="DĚKUJI",
        dominant_hand=HandShape.FLAT,
        location=SignLocation.CHIN,
        movement=SignMovement.FORWARD,
        duration_ms=500,
        facial_expression="smile",
    ),
    "ANO": SignGloss(
        gloss="ANO",
        dominant_hand=HandShape.FIST,
        location=SignLocation.NEUTRAL,
        movement=SignMovement.DOWN,
        duration_ms=400,
        facial_expression="nod",
    ),
    "NE": SignGloss(
        gloss="NE",
        dominant_hand=HandShape.POINT,
        location=SignLocation.NEUTRAL,
        movement=SignMovement.LEFT,
        duration_ms=400,
        facial_expression="shake",
        repetitions=2,
    ),
    "PROSÍM": SignGloss(
        gloss="PROSÍM",
        dominant_hand=HandShape.FLAT,
        location=SignLocation.CHEST,
        movement=SignMovement.CIRCULAR,
        duration_ms=500,
    ),
    "ROZUMĚT": SignGloss(
        gloss="ROZUMĚT",
        dominant_hand=HandShape.POINT,
        location=SignLocation.FOREHEAD,
        movement=SignMovement.FORWARD,
        duration_ms=400,
    ),
    "NEVĚDĚT": SignGloss(
        gloss="NEVĚDĚT",
        dominant_hand=HandShape.SPREAD,
        location=SignLocation.SHOULDER,
        movement=SignMovement.UP,
        duration_ms=500,
        facial_expression="shrug",
    ),
    "FILM": SignGloss(
        gloss="FILM",
        dominant_hand=HandShape.SPREAD,
        non_dominant_hand=HandShape.FLAT,
        location=SignLocation.NEUTRAL,
        movement=SignMovement.CIRCULAR,
        duration_ms=600,
    ),
    "JAZYK": SignGloss(
        gloss="JAZYK",
        dominant_hand=HandShape.POINT,
        location=SignLocation.CHIN,
        movement=SignMovement.FORWARD,
        duration_ms=400,
    ),
    "PŘEKLAD": SignGloss(
        gloss="PŘEKLAD",
        dominant_hand=HandShape.FLAT,
        non_dominant_hand=HandShape.FLAT,
        location=SignLocation.NEUTRAL,
        movement=SignMovement.CIRCULAR,
        duration_ms=600,
    ),
    "SVĚT": SignGloss(
        gloss="SVĚT",
        dominant_hand=HandShape.C_SHAPE,
        location=SignLocation.NEUTRAL,
        movement=SignMovement.CIRCULAR,
        duration_ms=700,
    ),
    "POMOC": SignGloss(
        gloss="POMOC",
        dominant_hand=HandShape.FIST,
        non_dominant_hand=HandShape.FLAT,
        location=SignLocation.NEUTRAL,
        movement=SignMovement.UP,
        duration_ms=500,
    ),
    "ZDARMA": SignGloss(
        gloss="ZDARMA",
        dominant_hand=HandShape.FLAT,
        location=SignLocation.NEUTRAL,
        movement=SignMovement.FORWARD,
        duration_ms=500,
        facial_expression="emphasis",
    ),
}

# Výchozí glosa pro neznámá slova
DEFAULT_GLOSS = SignGloss(
    gloss="?",
    dominant_hand=HandShape.SPREAD,
    location=SignLocation.NEUTRAL,
    movement=SignMovement.NONE,
    duration_ms=400,
)


# === GLOSSER (TEXT → GLOSY) ===

class SignLanguageGlosser:
    """Převede text na sekvenci glos znakového jazyka.

    Dva režimy:
    1. Gemini AI glosování — přesnější, kontextové
    2. Pravidlový fallback — slovníkový lookup
    """

    def __init__(self, language: SignLanguage = SignLanguage.CZJ,
                 use_gemini: bool = True):
        self._language = language
        self._use_gemini = use_gemini and _GEMINI_AVAILABLE
        self._client = None

        if self._use_gemini:
            try:
                api_key = self._load_api_key()
                self._client = genai.Client(api_key=api_key)
                logger.info("Gemini glosér inicializován")
            except Exception as e:
                logger.warning(f"Gemini nedostupný ({e}), používám fallback")
                self._use_gemini = False

    def _load_api_key(self) -> str:
        """Načte Gemini API klíč."""
        key = os.environ.get("GEMINI_API_KEY")
        if key:
            return key

        key_file = Path.home() / ".gemini_api_key"
        if key_file.exists():
            content = key_file.read_text().strip()
            if "=" in content:
                return content.split("=", 1)[1].strip()
            return content

        gala_conf = Path.home() / "gala_key.conf"
        if gala_conf.exists():
            content = gala_conf.read_text().strip()
            if "=" in content:
                return content.split("=", 1)[1].strip()
            return content

        raise ValueError("Gemini API klíč nenalezen")

    def gloss_text(self, text: str) -> list[SignGloss]:
        """Převeď text na seznam glos.

        Args:
            text: Vstupní text k převodu na znakový jazyk.

        Returns:
            Seznam SignGloss objektů.
        """
        if self._use_gemini and self._client:
            return self._gloss_with_gemini(text)
        return self._gloss_with_rules(text)

    def _gloss_with_gemini(self, text: str) -> list[SignGloss]:
        """Použij Gemini pro rozklad textu na glosy ČZJ."""
        lang_name = {
            SignLanguage.CZJ: "Český znakový jazyk (ČZJ)",
            SignLanguage.ASL: "American Sign Language (ASL)",
            SignLanguage.BSL: "British Sign Language (BSL)",
            SignLanguage.DGS: "Deutsche Gebärdensprache (DGS)",
        }.get(self._language, "znakový jazyk")

        prompt = f"""Převeď následující text do glos pro {lang_name}.

Pravidla:
- Glosy piš VELKÝMI PÍSMENY
- Každá glosa = jeden znak
- Znakový jazyk má jinou gramatiku než mluvený - přizpůsob pořadí
- Odděl glosy mezerami
- Nekomentuj, jen glosy na jednom řádku

Text: {text}

Glosy:"""

        try:
            response = self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            gloss_text = response.text.strip()
            return self._parse_gloss_string(gloss_text)
        except Exception as e:
            logger.warning(f"Gemini glosování selhalo: {e}")
            return self._gloss_with_rules(text)

    def _gloss_with_rules(self, text: str) -> list[SignGloss]:
        """Pravidlový fallback — slovníkový lookup."""
        words = text.upper().replace(",", "").replace(".", "").replace("?", "").split()
        glosses = []

        for word in words:
            # Hledej v databázi
            if word in CZJ_GLOSS_DB:
                glosses.append(CZJ_GLOSS_DB[word])
            else:
                # Zkusit najít podobnou glosu
                found = False
                for key, gloss in CZJ_GLOSS_DB.items():
                    if word in key or key in word:
                        glosses.append(gloss)
                        found = True
                        break

                if not found:
                    # Neznámé slovo — fingerspelling (každé písmeno)
                    # V prototypu: generická glosa
                    new_gloss = SignGloss(
                        gloss=word,
                        dominant_hand=HandShape.POINT,
                        location=SignLocation.NEUTRAL,
                        movement=SignMovement.RIGHT,
                        duration_ms=max(300, len(word) * 150),
                    )
                    glosses.append(new_gloss)

        return glosses

    def _parse_gloss_string(self, gloss_string: str) -> list[SignGloss]:
        """Parse textový výstup Gemini do SignGloss objektů."""
        # Očekávaný formát: "DOBRÝ-DEN JÁ CHTÍT POMOC"
        words = gloss_string.strip().split()
        glosses = []

        for word in words:
            word = word.strip().upper()
            if not word:
                continue

            if word in CZJ_GLOSS_DB:
                glosses.append(CZJ_GLOSS_DB[word])
            else:
                glosses.append(SignGloss(
                    gloss=word,
                    dominant_hand=HandShape.FLAT,
                    location=SignLocation.NEUTRAL,
                    movement=SignMovement.NONE,
                    duration_ms=500,
                ))

        return glosses


# === RENDERER ===

class SignLanguageRenderer:
    """Hlavní renderer znakové řeči.

    Převede text/titulky na animační sekvence pro avatar.
    Výstup: JSON s instrukcemi pro frontend renderer.
    """

    def __init__(self, language: SignLanguage = SignLanguage.CZJ,
                 use_gemini: bool = True):
        self._language = language
        self._glosser = SignLanguageGlosser(
            language=language, use_gemini=use_gemini
        )
        logger.info(f"Sign Language Renderer inicializován (jazyk={language.value})")

    def render_text(self, text: str,
                    start_ms: int = 0, end_ms: int = 0) -> SignSequence:
        """Renderuj text do sekvence znaků.

        Args:
            text: Vstupní text.
            start_ms: Začátek v milisekundách (pro sync s videem).
            end_ms: Konec v milisekundách.

        Returns:
            SignSequence s kompletními instrukcemi pro avatar.
        """
        glosses = self._glosser.gloss_text(text)

        # Vypočítat timing
        total_duration = sum(g.duration_ms for g in glosses)

        # Pokud máme časové okno, přizpůsobit rychlost
        if end_ms > start_ms > 0:
            available_ms = end_ms - start_ms
            if total_duration > available_ms and total_duration > 0:
                # Zrychlit znaky
                ratio = available_ms / total_duration
                for g in glosses:
                    g.duration_ms = max(200, int(g.duration_ms * ratio))
                total_duration = sum(g.duration_ms for g in glosses)

        return SignSequence(
            text=text,
            language=self._language,
            glosses=glosses,
            total_duration_ms=total_duration,
            timestamp_start_ms=start_ms,
            timestamp_end_ms=end_ms or (start_ms + total_duration),
        )

    def render_subtitles(self, subtitles_path: str,
                         output_path: Optional[str] = None) -> RenderStats:
        """Renderuj celý soubor titulků do znakové řeči.

        Args:
            subtitles_path: Cesta k SRT/VTT souboru.
            output_path: Výstupní JSON soubor. Pokud None, generuje se.

        Returns:
            RenderStats se statistikami.
        """
        import srt as srt_module

        path = Path(subtitles_path)
        content = path.read_text(encoding="utf-8")

        # Parse titulky
        if path.suffix.lower() == ".vtt" or content.startswith("WEBVTT"):
            sys.path.insert(0, str(path.parent))
            from subtitle_translator import parse_vtt
            subtitles = parse_vtt(content)
        else:
            subtitles = list(srt_module.parse(content))

        logger.info(f"Načteno {len(subtitles)} titulků z {path}")

        stats = RenderStats(
            total_phrases=len(subtitles),
            language=self._language.value,
        )

        start_time = time.time()
        sequences = []

        for i, sub in enumerate(subtitles):
            text = sub.content.strip()
            if not text:
                continue

            start_ms = int(sub.start.total_seconds() * 1000)
            end_ms = int(sub.end.total_seconds() * 1000)

            seq = self.render_text(text, start_ms=start_ms, end_ms=end_ms)
            sequences.append(seq)

            stats.total_glosses += len(seq.glosses)
            stats.total_duration_ms += seq.total_duration_ms

            logger.info(
                f"  [{i+1}/{len(subtitles)}] "
                f"{text[:40]}... → {seq.gloss_string[:40]}..."
            )

        stats.elapsed_seconds = time.time() - start_time

        # Export JSON
        if output_path is None:
            output_path = str(path.parent / f"{path.stem}_signs.json")

        output_data = {
            "version": "1.0",
            "generator": "Asgard Lab Sign Language Renderer",
            "language": self._language.value,
            "total_sequences": len(sequences),
            "total_glosses": stats.total_glosses,
            "total_duration_ms": stats.total_duration_ms,
            "sequences": [seq.to_dict() for seq in sequences],
        }

        Path(output_path).write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        logger.info(f"✓ Výstup: {output_path}")
        return stats


# === CLI ===

def main():
    """CLI entry point pro generátor znakové řeči."""
    parser = argparse.ArgumentParser(
        description=(
            "Asgard Lab — Generátor znakové řeči\n"
            "ZDARMA pro osoby se sluchovým hendikepem 🤟"
        ),
        epilog='Příklad: python sign_language_renderer.py "Dobrý den" --lang czj'
    )
    parser.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Text k převodu na znakovou řeč"
    )
    parser.add_argument(
        "--input", "-i",
        default=None,
        help="Vstupní soubor s titulky (SRT/VTT)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Výstupní JSON soubor"
    )
    parser.add_argument(
        "--lang", "-l",
        choices=["czj", "asl", "bsl", "dgs"],
        default="czj",
        help="Znakový jazyk (výchozí: czj = Český znakový jazyk)"
    )
    parser.add_argument(
        "--no-gemini",
        action="store_true",
        help="Nepoužívat Gemini (jen pravidlový fallback)"
    )

    args = parser.parse_args()

    print("═══════════════════════════════════════════════")
    print("  🤟 Asgard Lab — Sign Language Renderer")
    print("  ZDARMA pro osoby se sluchovým hendikepem")
    print("═══════════════════════════════════════════════")
    print()

    language = SignLanguage(args.lang)
    renderer = SignLanguageRenderer(
        language=language,
        use_gemini=not args.no_gemini
    )

    if args.input:
        # Režim: celý soubor titulků
        stats = renderer.render_subtitles(
            args.input, output_path=args.output
        )
        print()
        print(f"  ✓ Hotovo! {stats.summary()}")
        print()

    elif args.text:
        # Režim: jeden text
        seq = renderer.render_text(args.text)
        print(f"  Text:  {seq.text}")
        print(f"  Glosy: {seq.gloss_string}")
        print(f"  Znaků: {len(seq.glosses)}")
        print(f"  Délka: {seq.total_duration_ms}ms")
        print()

        # Výpis detailů
        for g in seq.glosses:
            hand = f"ruka={g.dominant_hand.value}"
            loc = f"pozice={g.location.value}"
            mov = f"pohyb={g.movement.value}"
            print(f"    {g.gloss:15s} | {hand:15s} | {loc:18s} | {mov}")

        # Uložit JSON pokud specifikováno
        if args.output:
            output_data = seq.to_dict()
            Path(args.output).write_text(
                json.dumps(output_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"\n  ✓ Uloženo: {args.output}")
        print()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
