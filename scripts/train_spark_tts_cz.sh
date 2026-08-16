#!/bin/bash
# ============================================================
# Spark-TTS Czech Fine-tune — Brev GPU (L40S / A100)
# Spustit na Brev instanci: bash train_spark_tts_cz.sh
# ============================================================

set -e

echo "=== SPARK-TTS ČESKÝ TRÉNINK ==="
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'checking...')"
echo ""

# 1. Clone Spark-TTS
if [ ! -d "spark-tts" ]; then
    echo "[1/5] Klonuji Spark-TTS..."
    git clone https://github.com/SparkAudio/Spark-TTS.git spark-tts
fi
cd spark-tts

# 2. Install dependencies
echo "[2/5] Instaluji závislosti..."
pip install -q torch torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -q -r requirements.txt
pip install -q soundfile datasets yt-dlp

# 3. Download Czech dubbing audio (training data)
echo "[3/5] Stahuji české dabingové audio..."
mkdir -p data/czech_dubbing

# České filmy/seriály s dobrým dabingem (Mensík, Labus styl)
# Stáhneme audio z YouTube — české pohádky, dokumenty, dabing
URLS=(
    "ytsearch5:český dabing film ukázka"
    "ytsearch5:české pohádky vypravěč"
    "ytsearch3:jan werich vypráví"
    "ytsearch3:miroslav horníček vypráví"
    "ytsearch3:český dokument vypravěč"
)

for url in "${URLS[@]}"; do
    echo "  Stahuji: $url"
    yt-dlp -x --audio-format wav --audio-quality 0 \
        --max-downloads 5 \
        -o "data/czech_dubbing/%(title)s.%(ext)s" \
        "$url" 2>/dev/null || true
done

# Ořízni na 10-30s segmenty
echo "  Segmentace audia..."
mkdir -p data/czech_segments
for f in data/czech_dubbing/*.wav; do
    if [ -f "$f" ]; then
        base=$(basename "$f" .wav)
        # Rozřež na 15s segmenty
        ffmpeg -y -i "$f" -f segment -segment_time 15 -ar 16000 -ac 1 \
            "data/czech_segments/${base}_%03d.wav" 2>/dev/null || true
    fi
done

SEGMENT_COUNT=$(ls data/czech_segments/*.wav 2>/dev/null | wc -l)
echo "  Připraveno $SEGMENT_COUNT segmentů"

# 4. Fine-tune
echo "[4/5] Spouštím fine-tune..."
python -c "
import sys
sys.path.insert(0, '.')
import torch
import torchaudio
from pathlib import Path

print(f'PyTorch: {torch.__version__}')
print(f'CUDA: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB')

# Počet trénovacích segmentů
segments = list(Path('data/czech_segments').glob('*.wav'))
print(f'Trénovací segmenty: {len(segments)}')

if len(segments) < 10:
    print('VAROVÁNÍ: Málo segmentů. Potřeba min 50+ pro kvalitní fine-tune.')
    print('Zvyš počet URL nebo stáhni víc materiálu.')
else:
    print(f'OK — {len(segments)} segmentů, spouštím trénink...')
"

# Spark-TTS fine-tune (pokud existuje train script)
if [ -f "train.py" ]; then
    python train.py \
        --data_dir data/czech_segments \
        --model_dir models/models--SparkAudio--Spark-TTS-0.5B \
        --output_dir models/spark-tts-czech \
        --epochs 50 \
        --batch_size 8 \
        --learning_rate 1e-4 \
        --language cs
elif [ -f "finetune.py" ]; then
    python finetune.py \
        --data_dir data/czech_segments \
        --model_dir models/models--SparkAudio--Spark-TTS-0.5B \
        --output_dir models/spark-tts-czech \
        --epochs 50
else
    echo "POZNÁMKA: Spark-TTS nemá oficiální fine-tune script."
    echo "Použijeme voice cloning s velkým referenčním audiem."
    echo ""
    echo "Alternativa: spojíme všechny segmenty do jednoho reference audio"
    
    # Spojit segmenty do jednoho velkého reference
    ls data/czech_segments/*.wav | head -100 | sed 's/^/file /' > data/concat_list.txt
    ffmpeg -y -f concat -safe 0 -i data/concat_list.txt \
        -ar 16000 -ac 1 data/czech_reference_full.wav 2>/dev/null
    
    echo "Vytvořeno: data/czech_reference_full.wav"
    echo "Toto použij jako prompt_speech_path při inference."
fi

# 5. Test
echo "[5/5] Test inference..."
python -c "
import sys
sys.path.insert(0, '.')
from cli.SparkTTS import SparkTTS
import soundfile as sf
from pathlib import Path

# Použij fine-tuned model nebo originál s českým reference
model_dir = 'models/spark-tts-czech' if Path('models/spark-tts-czech').exists() else 'models/models--SparkAudio--Spark-TTS-0.5B'

# Najdi snapshot
snapshots = list(Path(model_dir).rglob('config.json'))
if snapshots:
    model_path = str(snapshots[0].parent)
else:
    model_path = model_dir

print(f'Model: {model_path}')
tts = SparkTTS(model_dir=model_path, device='cuda')

# Reference audio (pokud existuje)
ref_path = 'data/czech_reference_full.wav' if Path('data/czech_reference_full.wav').exists() else None

text = 'Dobrý den, jsem Karel, váš osobní překladatel z Asgard Lab.'
kwargs = {'text': text, 'gender': 'male', 'pitch': 'moderate', 'speed': 'moderate'}
if ref_path:
    kwargs['prompt_speech_path'] = ref_path

wav = tts.inference(**kwargs)
sf.write('output_czech_test.wav', wav, 16000)
print(f'HOTOVO: output_czech_test.wav')
print(f'Velikost: {Path(\"output_czech_test.wav\").stat().st_size / 1024:.1f} KB')
"

echo ""
echo "=== TRÉNINK DOKONČEN ==="
echo "Výstup: output_czech_test.wav"
echo "Zkopíruj na NAS: scp output_czech_test.wav pj@192.168.123.169:/mnt/web4light/media/"
echo ""
