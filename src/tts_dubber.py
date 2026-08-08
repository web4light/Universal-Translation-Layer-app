"""
TTS Dubber — Asgard Lab / UTL
================================

Pipeline: Přeložené titulky (SRT/VTT) → TTS syntéza → Audio dabing

Přečte přeložené titulky pomocí TTS enginu a vytvoří audio soubor
synchronizovaný s původním videem.

Podporované TTS enginy:
- gTTS (Google Text-to-Speech) — zdarma, online
- Coqui TTS (XTTS v2) — lokální, kvalitní hlasy
- Gemini TTS (plánováno) — přes Google Cloud

Použití:
    python tts_dubber.py translated.srt --output dubbing.mp3
    python tts_dubber.py translated.srt --engine gtts --lang cs
    python tts_dubber.py translated.srt --engine coqui --voice male

Autor: Pan Jeskyně
Asistent: Kiro
Organizace: Rebirth Phoenix Foundation Charter
Projekt: XPRIZE Build with Gemini — Asgard Lab
"""

import io
import os
import sys
import time
import wave
import logging
import argparse
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum

import srt

# === LOGGING ===

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TTS-DUBBER] %(message)s"
)
logger = logging.getLogger(__name__)

# === OPTIONAL DEPENDENCIES ===

try:
    from gtts import gTTS
    _GTTS_AVAILABLE = True
except ImportError:
    _GTTS_AVAILABLE = False

try:
    from pydub import AudioSegment
    _PYDUB_AVAILABLE = True
except ImportError:
    _PYDUB_AVAILABLE = False

try:
    from TTS.api import TTS as CoquiTTS
    _COQUI_AVAILABLE = True
except ImportError:
    _COQUI_AVAILABLE = False


# === CONSTANTS ===

DEFAULT_SAMPLE_RATE = 24000
DEFAULT_SILENCE_PADDING_MS = 100  # Pauza mezi segmenty


# === ENUMS ===

class TTSEngine(Enum):
    """Dostupné TTS enginy."""
    GTTS = "gtts"       # Google TTS (online, zdarma)
    COQUI = "coqui"     # Coqui XTTS (lokální, kvalitní)
    GEMINI = "gemini"   # Gemini API TTS (plánováno)


# === DATA MODELS ===

@dataclass
class DubbingStats:
    """Statistiky dabingu."""
    total_segments: int = 0
    synthesized_segments: int = 0
    failed_segments: int = 0
    total_duration_s: float = 0.0
    audio_duration_s: float = 0.0
    elapsed_seconds: float = 0.0
    engine: str = "gtts"

    def summary(self) -> str:
        return (
            f"Segmentů: {self.synthesized_segments}/{self.total_segments} | "
            f"Audio: {self.audio_duration_s:.1f}s | "
            f"Engine: {self.engine} | "
            f"Čas: {self.elapsed_seconds:.1f}s"
        )


@dataclass
class AudioSegmentData:
    """Jeden audio segment dabingu."""
    index: int
    start_ms: int          # Začátek v milisekundách
    end_ms: int            # Konec v milisekundách
    text: str              # Text k syntéze
    audio_data: bytes      # Raw audio data (MP3 nebo WAV)
    format: str = "mp3"    # Formát audio dat


# === TTS ENGINES ===

class GTTSEngine:
    """Google Text-to-Speech engine (online, zdarma).

    Výhody: Zdarma, podporuje mnoho jazyků, jednoduchý.
    Nevýhody: Potřebuje internet, robotický hlas, rate limiting.
    """

    def __init__(self, lang: str = "cs"):
        self._lang = lang

    def synthesize(self, text: str) -> bytes:
        """Syntetizuj text do MP3 audio.

        Args:
            text: Text k syntéze.

        Returns:
            MP3 audio data jako bytes.
        """
        if not _GTTS_AVAILABLE:
            raise RuntimeError(
                "gTTS není nainstalován. Instaluj: pip install gtts"
            )

        tts = gTTS(text=text, lang=self._lang, slow=False)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        return buffer.read()

    @property
    def format(self) -> str:
        return "mp3"


class CoquiEngine:
    """Coqui XTTS v2 engine (lokální, kvalitní).

    Výhody: Lokální, kvalitní hlasy, voice cloning.
    Nevýhody: Vyžaduje GPU pro rychlou syntézu, velký model.
    """

    def __init__(self, lang: str = "cs", model_name: str = None):
        if not _COQUI_AVAILABLE:
            raise RuntimeError(
                "Coqui TTS není nainstalován. Instaluj: pip install TTS"
            )

        self._lang = lang
        model = model_name or "tts_models/multilingual/multi-dataset/xtts_v2"

        logger.info(f"Načítám Coqui TTS model: {model}")
        self._tts = CoquiTTS(model_name=model, progress_bar=False)

    def synthesize(self, text: str) -> bytes:
        """Syntetizuj text do WAV audio.

        Args:
            text: Text k syntéze.

        Returns:
            WAV audio data jako bytes.
        """
        # Coqui vrací seznam floatů
        wav_data = self._tts.tts(text=text, language=self._lang)

        # Konvertovat na WAV bytes
        buffer = io.BytesIO()
        import numpy as np
        audio_np = np.array(wav_data, dtype=np.float32)

        # Normalizace
        if np.max(np.abs(audio_np)) > 0:
            audio_np = audio_np / np.max(np.abs(audio_np))

        # Float32 → Int16
        audio_int16 = (audio_np * 32767).astype(np.int16)

        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(DEFAULT_SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        buffer.seek(0)
        return buffer.read()

    @property
    def format(self) -> str:
        return "wav"


# === MAIN DUBBER ===

class TTSDubber:
    """Hlavní dabovací engine.

    Načte přeložené titulky, syntetizuje audio pro každý segment
    a poskládá do jednoho výstupního souboru se správným timingem.
    """

    def __init__(self, engine: TTSEngine = TTSEngine.GTTS, lang: str = "cs"):
        """Inicializace dubberu.

        Args:
            engine: Který TTS engine použít.
            lang: Cílový jazyk pro syntézu.
        """
        self._engine_type = engine
        self._lang = lang
        self._engine = self._create_engine(engine, lang)
        logger.info(f"TTS Dubber inicializován (engine={engine.value}, lang={lang})")

    def _create_engine(self, engine: TTSEngine, lang: str):
        """Vytvoř TTS engine instanci."""
        if engine == TTSEngine.GTTS:
            return GTTSEngine(lang=lang)
        elif engine == TTSEngine.COQUI:
            return CoquiEngine(lang=lang)
        elif engine == TTSEngine.GEMINI:
            # TODO: Implementovat Gemini TTS až bude API dostupné
            logger.warning("Gemini TTS zatím nedostupný, fallback na gTTS")
            return GTTSEngine(lang=lang)
        else:
            raise ValueError(f"Neznámý engine: {engine}")

    def dub_subtitles(
        self,
        subtitles: list[srt.Subtitle],
        output_path: str,
    ) -> DubbingStats:
        """Nadabuj titulky — syntetizuj audio a sestav výstup.

        Args:
            subtitles: Seznam titulků k dabingu.
            output_path: Cesta výstupního audio souboru.

        Returns:
            DubbingStats se statistikami.
        """
        if not _PYDUB_AVAILABLE:
            raise RuntimeError(
                "pydub není nainstalován. Instaluj: pip install pydub\n"
                "Také potřebuješ ffmpeg: sudo apt install ffmpeg"
            )

        stats = DubbingStats(
            total_segments=len(subtitles),
            engine=self._engine_type.value,
        )

        start_time = time.time()

        # Zjistit celkovou délku (poslední titulek end time)
        if subtitles:
            last_end = subtitles[-1].end
            total_duration_ms = int(last_end.total_seconds() * 1000)
            # Přidat 2s buffer na konec
            total_duration_ms += 2000
        else:
            total_duration_ms = 0

        stats.total_duration_s = total_duration_ms / 1000.0

        # Vytvořit "tiché" audio o celkové délce
        silence = AudioSegment.silent(duration=total_duration_ms)

        # Syntetizovat a vložit každý segment
        for i, sub in enumerate(subtitles):
            text = sub.content.strip()
            if not text:
                continue

            start_ms = int(sub.start.total_seconds() * 1000)
            end_ms = int(sub.end.total_seconds() * 1000)
            available_ms = end_ms - start_ms

            logger.info(
                f"  [{i+1}/{len(subtitles)}] "
                f"{self._format_time(start_ms)} → {self._format_time(end_ms)} "
                f"| {text[:50]}..."
            )

            try:
                # Syntetizuj segment
                audio_bytes = self._engine.synthesize(text)

                # Konvertovat na AudioSegment
                fmt = self._engine.format
                segment_audio = AudioSegment.from_file(
                    io.BytesIO(audio_bytes), format=fmt
                )

                # Upravit rychlost aby se vešel do dostupného času
                segment_audio = self._fit_to_duration(
                    segment_audio, available_ms
                )

                # Overlay na správné místo
                silence = silence.overlay(segment_audio, position=start_ms)

                stats.synthesized_segments += 1

            except Exception as e:
                logger.warning(f"  ⚠ Segment {i+1} selhal: {e}")
                stats.failed_segments += 1

        # Export výstupního souboru
        out_path = Path(output_path)
        out_format = out_path.suffix.lstrip(".") or "mp3"

        logger.info(f"Exportuji do {out_path} ({out_format})...")
        silence.export(str(out_path), format=out_format)

        stats.audio_duration_s = len(silence) / 1000.0
        stats.elapsed_seconds = time.time() - start_time

        return stats

    def _fit_to_duration(
        self, audio: 'AudioSegment', target_ms: int
    ) -> 'AudioSegment':
        """Upraví délku audio aby se vešlo do cílového časového okna.

        Pokud je audio delší než okno, zrychlí se (max 1.5x).
        Pokud je kratší, nechá se jak je (ticho na konci).

        Args:
            audio: Vstupní audio segment.
            target_ms: Cílová délka v milisekundách.

        Returns:
            Upravený audio segment.
        """
        current_ms = len(audio)

        if current_ms <= target_ms:
            # Audio se vejde, ok
            return audio

        # Audio je moc dlouhé — zrychlit (max 1.5x)
        speedup = min(current_ms / target_ms, 1.5)

        if speedup > 1.0:
            # Speedup pomocí frame_rate change
            new_frame_rate = int(audio.frame_rate * speedup)
            audio = audio._spawn(
                audio.raw_data,
                overrides={"frame_rate": new_frame_rate}
            )
            # Reset na standardní frame_rate pro export
            audio = audio.set_frame_rate(44100)

        # Oříznout na max délku
        if len(audio) > target_ms:
            audio = audio[:target_ms]

        return audio

    def _format_time(self, ms: int) -> str:
        """Formátuj milisekundy na MM:SS."""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


# === FILE I/O ===

def load_srt_file(filepath: str) -> list[srt.Subtitle]:
    """Načti SRT/VTT soubor."""
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".vtt" or content.strip().startswith("WEBVTT"):
        # Import VTT parser z subtitle_translator
        sys.path.insert(0, str(path.parent))
        from subtitle_translator import parse_vtt
        return parse_vtt(content)
    else:
        return list(srt.parse(content))


# === MAIN PIPELINE ===

def dub_file(
    input_path: str,
    output_path: Optional[str] = None,
    engine: str = "gtts",
    lang: str = "cs",
) -> DubbingStats:
    """Hlavní pipeline: načti titulky → syntetizuj → ulož audio.

    Args:
        input_path: Cesta k přeloženým titulkům (SRT/VTT).
        output_path: Výstupní audio soubor. Pokud None, generuje se.
        engine: TTS engine ('gtts', 'coqui', 'gemini').
        lang: Jazyk pro TTS syntézu.

    Returns:
        DubbingStats se statistikami.
    """
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Soubor nenalezen: {input_path}")

    # 1. Načti titulky
    subtitles = load_srt_file(input_path)
    logger.info(f"Načteno {len(subtitles)} titulků z {input_path}")

    if not subtitles:
        logger.warning("Žádné titulky k dabingu!")
        return DubbingStats()

    # 2. Výstupní cesta
    if output_path is None:
        output_path = str(input_file.parent / f"{input_file.stem}_dubbed.mp3")

    # 3. Dabuj
    tts_engine = TTSEngine(engine)
    dubber = TTSDubber(engine=tts_engine, lang=lang)
    stats = dubber.dub_subtitles(subtitles, output_path)

    logger.info(f"✓ {stats.summary()}")
    logger.info(f"✓ Výstup: {output_path}")

    return stats


# === CLI ===

def main():
    """CLI entry point pro TTS dabing."""
    parser = argparse.ArgumentParser(
        description="Asgard Lab — TTS Dubber: Přeloží titulky na mluvené slovo",
        epilog="Příklad: python tts_dubber.py film_cs.srt --engine gtts --lang cs"
    )
    parser.add_argument(
        "input",
        help="Vstupní soubor s přeloženými titulky (SRT nebo VTT)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Výstupní audio soubor (výchozí: input_dubbed.mp3)"
    )
    parser.add_argument(
        "--engine", "-e",
        choices=["gtts", "coqui", "gemini"],
        default="gtts",
        help="TTS engine (výchozí: gtts)"
    )
    parser.add_argument(
        "--lang", "-l",
        default="cs",
        help="Jazyk pro TTS syntézu (výchozí: cs)"
    )

    args = parser.parse_args()

    print("═══════════════════════════════════════════════")
    print("  🎙️  Asgard Lab — TTS Dubber")
    print("  Subtitle-to-Speech Pipeline")
    print("═══════════════════════════════════════════════")
    print()

    # Kontrola závislostí
    if not _GTTS_AVAILABLE and args.engine == "gtts":
        print("  ⚠ gTTS není nainstalován: pip install gtts")
        sys.exit(1)
    if not _PYDUB_AVAILABLE:
        print("  ⚠ pydub není nainstalován: pip install pydub")
        print("  ⚠ Také potřebuješ: sudo apt install ffmpeg")
        sys.exit(1)

    try:
        stats = dub_file(
            input_path=args.input,
            output_path=args.output,
            engine=args.engine,
            lang=args.lang,
        )
        print()
        print(f"  ✓ Hotovo! {stats.summary()}")
        print()
    except Exception as e:
        logger.error(f"Chyba: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
