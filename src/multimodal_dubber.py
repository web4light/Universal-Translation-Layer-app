#!/usr/bin/env python3
"""
Multimodal Dubbing Agent — Vidí a slyší, pak dabuje.
=======================================================

Agent co VIDÍ video a SLYŠÍ audio → rozhodne jak dabovat.
Ne jazykový model co překládá text. Multimodální AI.

Pipeline:
  1. Agent VIDÍ video (scéna, kdo mluví, emoce, gesta)
  2. Agent SLYŠÍ audio (hlasy, tón, tempo, pauzy, hudba)
  3. Agent ROZHODNE (kdo říká co, jak to zní, jaká emoce)
  4. Agent SESTAVÍ dabing (správný hlas, správná emoce, správný timing)

Enginy:
  - Gemini 2.5 Flash (multimodální — vidí + slyší video)
  - Speaker Mapper (rozliší mluvčí)
  - Edge-TTS / Spark-TTS (syntéza hlasu)

Spuštění:
    python src/multimodal_dubber.py video.mp4 --target cs
    python src/multimodal_dubber.py video.mp4 --target ja --voices 5

Autor: Pan Jeskyně
Organizace: Rebirth Phoenix Foundation Charter
"""

import os
import sys
import json
import time
import logging
import tempfile
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DUBBING-AGENT] %(message)s")
logger = logging.getLogger(__name__)

# === CONFIG ===

GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or Path(
    Path.home() / ".gemini_api_key"
).read_text().strip().split("=")[-1]

os.environ["GEMINI_API_KEY"] = GEMINI_KEY

# Edge-TTS hlasy (5 různých pro multi-voice)
VOICES = {
    "male_1": "cs-CZ-AntoninNeural",
    "male_2": "cs-CZ-AntoninNeural",  # jiný pitch
    "female_1": "cs-CZ-VlastaNeural",
    "female_2": "cs-CZ-VlastaNeural",  # jiný pitch
    "narrator": "en-US-AndrewMultilingualNeural",
}

# Mapování jazyků na hlasy
LANG_VOICES = {
    "cs": {"male": "cs-CZ-AntoninNeural", "female": "cs-CZ-VlastaNeural"},
    "en": {"male": "en-US-AndrewMultilingualNeural", "female": "en-US-AvaMultilingualNeural"},
    "de": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural"},
    "ja": {"male": "ja-JP-KeitaNeural", "female": "ja-JP-NanamiNeural"},
    "fr": {"male": "fr-FR-HenriNeural", "female": "fr-FR-DeniseNeural"},
    "es": {"male": "es-ES-AlvaroNeural", "female": "es-ES-ElviraNeural"},
    "uk": {"male": "uk-UA-OstapNeural", "female": "uk-UA-PolinaNeural"},
    "pl": {"male": "pl-PL-MarekNeural", "female": "pl-PL-ZofiaNeural"},
    "it": {"male": "it-IT-DiegoNeural", "female": "it-IT-ElsaNeural"},
    "pt": {"male": "pt-BR-AntonioNeural", "female": "pt-BR-FranciscaNeural"},
    "zh": {"male": "zh-CN-YunxiNeural", "female": "zh-CN-XiaoxiaoNeural"},
    "ko": {"male": "ko-KR-InJoonNeural", "female": "ko-KR-SunHiNeural"},
}


# === DATA MODELS ===

@dataclass
class Speaker:
    """Jeden detekovaný mluvčí ve videu."""
    id: str
    gender: str  # "male" / "female"
    emotion: str  # "neutral" / "happy" / "angry" / "sad"
    voice_assigned: str = ""  # Edge-TTS voice name


@dataclass
class DubbingSegment:
    """Jeden segment k dabování."""
    start_ms: int
    end_ms: int
    speaker: Speaker
    original_text: str
    translated_text: str
    emotion: str = "neutral"
    speed: float = 1.0


@dataclass
class DubbingResult:
    """Výsledek celého dabingu."""
    output_path: str
    segments_total: int = 0
    segments_dubbed: int = 0
    speakers_detected: int = 0
    duration_seconds: float = 0.0
    elapsed_seconds: float = 0.0


# === MULTIMODAL AGENT ===

class MultimodalDubbingAgent:
    """Agent co vidí a slyší video, pak sestaví dabing.
    
    Používá Gemini 2.5 jako multimodální mozek:
    - Pošle mu video → Gemini vidí + slyší
    - Gemini vrátí strukturovanou analýzu (kdo, co, jak)
    - Agent na základě toho sestaví dabing s Edge-TTS
    """

    def __init__(self, target_lang: str = "cs", max_speakers: int = 5):
        self._target_lang = target_lang
        self._max_speakers = max_speakers
        self._speakers: dict[str, Speaker] = {}
        
        from google import genai
        self._client = genai.Client(api_key=GEMINI_KEY)
        logger.info(f"Multimodal Dubbing Agent ready (target={target_lang}, max_speakers={max_speakers})")

    def analyze_video(self, video_path: str) -> list[DubbingSegment]:
        """Pošli video Gemini — agent vidí + slyší, vrátí analýzu.
        
        Gemini dostane celé video a vrátí:
        - Kdo mluví (speaker ID, pohlaví)
        - Co říká (originální text)
        - Jak to říká (emoce, tempo)
        - Kdy to říká (timestamp)
        """
        logger.info(f"Analyzuji video: {video_path}")
        
        video_file = Path(video_path)
        if not video_file.exists():
            raise FileNotFoundError(f"Video nenalezeno: {video_path}")
        
        # Upload video do Gemini
        logger.info("Nahrávám video do Gemini (multimodální analýza)...")
        
        uploaded = self._client.files.upload(file=video_path)
        
        # Počkat na zpracování
        import time as t
        while uploaded.state.name == "PROCESSING":
            t.sleep(2)
            uploaded = self._client.files.get(name=uploaded.name)
        
        logger.info(f"Video zpracováno: {uploaded.state.name}")

        # Multimodální prompt — agent VIDÍ a SLYŠÍ
        prompt = f"""Analyzuj toto video. Vidíš obraz i slyšíš zvuk.

Vrať JSON pole segmentů. Pro každý segment kde někdo mluví:

[{{
  "start_ms": 0,
  "end_ms": 3500,
  "speaker_id": "speaker_1",
  "gender": "male",
  "emotion": "neutral",
  "original_text": "co přesně říká (originální jazyk)",
  "translated_text": "překlad do {self._target_lang}",
  "speed": 1.0
}}]

PRAVIDLA:
- Rozliš jednotlivé mluvčí (speaker_1, speaker_2...)
- Urči pohlaví z hlasu (male/female)
- Urči emoci (neutral/happy/angry/sad/excited/whisper)
- Přepiš PŘESNĚ co říkají (ne přibližně)
- Přelož do: {self._target_lang}
- Timing v milisekundách (přesně podle videa)
- Speed: 1.0 = normální, 1.2 = rychlejší (když je málo času)
- Ignoruj hudbu a zvukové efekty (jen řeč)
- Max {self._max_speakers} mluvčích

Vrať POUZE JSON, nic jiného."""

        response = self._client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded, prompt],
        )

        # Parse odpovědi
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        segments_raw = json.loads(text.strip())
        logger.info(f"Detekováno {len(segments_raw)} segmentů")

        # Vytvořit Speaker objekty a DubbingSegmenty
        segments = []
        for seg in segments_raw:
            speaker_id = seg.get("speaker_id", "speaker_1")
            gender = seg.get("gender", "male")
            
            if speaker_id not in self._speakers:
                self._speakers[speaker_id] = Speaker(
                    id=speaker_id,
                    gender=gender,
                    emotion=seg.get("emotion", "neutral"),
                    voice_assigned=self._assign_voice(gender),
                )
            
            speaker = self._speakers[speaker_id]
            
            segments.append(DubbingSegment(
                start_ms=seg.get("start_ms", 0),
                end_ms=seg.get("end_ms", 0),
                speaker=speaker,
                original_text=seg.get("original_text", ""),
                translated_text=seg.get("translated_text", ""),
                emotion=seg.get("emotion", "neutral"),
                speed=seg.get("speed", 1.0),
            ))

        # Cleanup uploaded file
        try:
            self._client.files.delete(name=uploaded.name)
        except Exception:
            pass

        return segments

    def _assign_voice(self, gender: str) -> str:
        """Přiřaď Edge-TTS hlas podle pohlaví a jazyka."""
        voices = LANG_VOICES.get(self._target_lang, LANG_VOICES["en"])
        return voices.get(gender, voices["male"])

    def synthesize_dubbing(self, segments: list[DubbingSegment], output_dir: Path) -> list[Path]:
        """Syntetizuj audio pro každý segment přes Edge-TTS."""
        
        audio_files = []
        
        for i, seg in enumerate(segments):
            if not seg.translated_text.strip():
                continue
            
            output_file = output_dir / f"seg_{i:04d}.mp3"
            
            # Edge-TTS s emocí (style)
            voice = seg.speaker.voice_assigned
            rate = f"+{int((seg.speed - 1) * 100)}%" if seg.speed > 1 else f"{int((seg.speed - 1) * 100)}%"
            
            cmd = [
                sys.executable, "-m", "edge_tts",
                "--voice", voice,
                "--text", seg.translated_text,
                "--rate", rate,
                "--write-media", str(output_file),
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if output_file.exists():
                audio_files.append(output_file)
                logger.info(f"  [{i+1}/{len(segments)}] {seg.speaker.id} ({seg.emotion}): {seg.translated_text[:40]}...")
            else:
                logger.warning(f"  [{i+1}] FAIL: {result.stderr[:100]}")
        
        return audio_files

    def assemble_dubbed_audio(
        self,
        segments: list[DubbingSegment],
        audio_files: list[Path],
        original_video: str,
        output_path: str,
    ) -> DubbingResult:
        """Sestav finální dabované audio — správný timing, mix s originálem."""
        
        start_time = time.time()
        
        # Získat délku originálu
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", original_video],
            capture_output=True, text=True
        )
        total_duration_ms = int(float(probe.stdout.strip()) * 1000) if probe.stdout.strip() else 0
        
        # Vytvořit ffmpeg filter complex pro přesný timing
        tmp_dir = Path(tempfile.mkdtemp())
        
        # 1. Extrahovat originální audio (pro mix hudby/SFX)
        original_audio = tmp_dir / "original.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", original_video,
            "-vn", "-acodec", "pcm_s16le", "-ar", "24000",
            str(original_audio)
        ], capture_output=True)
        
        # 2. Vytvořit tiché audio o celkové délce
        silent = tmp_dir / "silent.wav"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anullsrc=r=24000:cl=mono:d={total_duration_ms/1000:.3f}",
            "-acodec", "pcm_s16le",
            str(silent)
        ], capture_output=True)
        
        # 3. Overlay segmenty na správné pozice
        # Sestavit ffmpeg příkaz s adelay filtery
        if not audio_files:
            logger.warning("Žádné audio segmenty!")
            return DubbingResult(output_path=output_path)
        
        inputs = ["-i", str(silent)]
        filter_parts = []
        
        dubbed_segments = []
        for i, (seg, audio_file) in enumerate(zip(segments, audio_files)):
            if not audio_file.exists():
                continue
            inputs.extend(["-i", str(audio_file)])
            idx = len(dubbed_segments) + 1
            delay = seg.start_ms
            filter_parts.append(f"[{idx}]adelay={delay}|{delay}[d{i}]")
            dubbed_segments.append(i)
        
        if not dubbed_segments:
            logger.warning("Žádné platné segmenty!")
            return DubbingResult(output_path=output_path)
        
        # Mix všech delayed segmentů
        mix_inputs = "".join(f"[d{i}]" for i in dubbed_segments)
        filter_parts.append(f"[0]{mix_inputs}amix=inputs={len(dubbed_segments)+1}:duration=first[out]")
        
        filter_complex = ";".join(filter_parts)
        
        # Finální mix
        dubbed_audio = tmp_dir / "dubbed.wav"
        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-acodec", "pcm_s16le",
            str(dubbed_audio)
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        # 4. Spojit dabované audio s videem
        if dubbed_audio.exists():
            subprocess.run([
                "ffmpeg", "-y",
                "-i", original_video,
                "-i", str(dubbed_audio),
                "-c:v", "copy",
                "-map", "0:v", "-map", "1:a",
                "-shortest",
                output_path
            ], capture_output=True)
        
        elapsed = time.time() - start_time
        
        result = DubbingResult(
            output_path=output_path,
            segments_total=len(segments),
            segments_dubbed=len(dubbed_segments),
            speakers_detected=len(self._speakers),
            duration_seconds=total_duration_ms / 1000,
            elapsed_seconds=elapsed,
        )
        
        logger.info(f"✅ Dabing hotov: {result.segments_dubbed}/{result.segments_total} segmentů, "
                    f"{result.speakers_detected} mluvčích, {result.elapsed_seconds:.1f}s")
        
        return result


# === CLI ===

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Multimodal Dubbing Agent — vidí + slyší → dabuje")
    parser.add_argument("video", help="Vstupní video soubor")
    parser.add_argument("--target", "-t", default="cs", help="Cílový jazyk (default: cs)")
    parser.add_argument("--voices", "-v", type=int, default=5, help="Max počet hlasů (default: 5)")
    parser.add_argument("--output", "-o", default=None, help="Výstupní soubor")
    
    args = parser.parse_args()
    
    output = args.output or str(Path(args.video).stem + f"_dubbed_{args.target}.mp4")
    
    print("═" * 60)
    print("  🎬 MULTIMODAL DUBBING AGENT")
    print(f"  Vstup:  {args.video}")
    print(f"  Jazyk:  {args.target}")
    print(f"  Hlasů:  {args.voices}")
    print(f"  Výstup: {output}")
    print("═" * 60)
    print()
    
    agent = MultimodalDubbingAgent(target_lang=args.target, max_speakers=args.voices)
    
    # 1. Analýza (Gemini vidí + slyší)
    print("[1/3] Agent analyzuje video (vidí + slyší)...")
    segments = agent.analyze_video(args.video)
    print(f"      → {len(segments)} segmentů, {len(agent._speakers)} mluvčích")
    print()
    
    # 2. Syntéza (Edge-TTS)
    print("[2/3] Syntetizuji hlasy...")
    tmp_dir = Path(tempfile.mkdtemp())
    audio_files = agent.synthesize_dubbing(segments, tmp_dir)
    print(f"      → {len(audio_files)} audio souborů")
    print()
    
    # 3. Sestavení
    print("[3/3] Sestavuji finální dabing...")
    result = agent.assemble_dubbed_audio(segments, audio_files, args.video, output)
    
    print()
    print("═" * 60)
    print(f"  ✅ HOTOVO!")
    print(f"  📁 Výstup: {result.output_path}")
    print(f"  🗣️  Mluvčích: {result.speakers_detected}")
    print(f"  🎬 Segmentů: {result.segments_dubbed}/{result.segments_total}")
    print(f"  ⏱️  Čas: {result.elapsed_seconds:.1f}s")
    print("═" * 60)


if __name__ == "__main__":
    main()
