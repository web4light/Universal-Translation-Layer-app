"""
Asgard Lab — Web API Server
==============================
Nasazená appka: vloží YouTube URL → vrátí překlad + dabing + znaky.

Spuštění:
    python src/asgard_server.py

Endpoint:
    POST /translate  {"url": "https://youtube.com/...", "target": "cs"}
    GET  /status     {"status": "running", "pipeline": "ready"}
    GET  /           Web UI

Port: 8000
"""

import os
import sys
import time
import json
import tempfile
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Pipeline imports
sys.path.insert(0, str(Path(__file__).parent))
from subtitle_translator import GeminiSubtitleTranslator, load_subtitles, save_subtitles, LANGUAGE_NAMES
from tts_dubber import dub_file
from sign_language_renderer import SignLanguageRenderer, SignLanguage

# === CONFIG ===
PORT = int(os.environ.get("PORT", 8000))
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or open(
    Path.home() / ".gemini_api_key"
).read().strip().split("=")[-1]
GROQ_KEY = os.environ.get("GROQ_API_KEY") or open(
    Path.home() / ".groq_api_key"
).read().strip().split("=")[-1]

os.environ["GEMINI_API_KEY"] = GEMINI_KEY
os.environ["GROQ_API_KEY"] = GROQ_KEY

# === APP ===
app = FastAPI(
    title="Asgard Lab API",
    description="1+1=3: Translation + Dubbing + Sign Language",
    version="1.0.0",
)

# === STATIC FILES (SCADA, DLP3D, assets) ===
_static_dir = Path(__file__).parent.parent / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# === DLP3D Avatar (MIT) ===
_dlp3d_dir = Path(__file__).parent.parent / "dlp3d" / "public"
if _dlp3d_dir.exists():
    app.mount("/avatar", StaticFiles(directory=str(_dlp3d_dir)), name="avatar")

# === STRIPE INTEGRATION ===
from stripe_integration import router as stripe_router
app.include_router(stripe_router, tags=["payments"])

# === MODELS ===
class TranslateRequest(BaseModel):
    url: str
    target: str = "cs"
    source: str = "auto"

class TranslateResponse(BaseModel):
    status: str
    subtitles_translated: int
    subtitles_total: int
    translation_time_s: float
    dubbing_time_s: float
    sign_language_glosses: int
    total_time_s: float
    files: dict

# === YOUTUBE DOWNLOAD ===
def download_youtube_subs(url: str, lang: str = "en") -> str:
    output_dir = tempfile.mkdtemp(prefix="asgard_")
    output_template = str(Path(output_dir) / "%(title).50s.%(ext)s")
    
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--skip-download",
        "--write-subs", "--write-auto-subs",
        "--sub-lang", lang,
        "--sub-format", "srt",
        "--convert-subs", "srt",
        "-o", output_template,
        url,
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    srt_files = list(Path(output_dir).glob("*.srt"))
    if not srt_files:
        raise HTTPException(status_code=400, detail=f"No subtitles found for {url}")
    
    return str(srt_files[0])

# === ENDPOINTS ===

@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html lang="la"><head><meta charset="utf-8"><title>Asgard Lab</title>
<style>
body{background:#0a0a0f;color:#e0e8f0;font-family:Georgia,serif;max-width:900px;margin:0 auto;padding:2rem}
h1{color:#ffd700;text-align:center;font-size:2.2rem;letter-spacing:2px}
.tagline{text-align:center;color:#8ba4c8;font-style:italic;margin-bottom:1rem}
.principle{text-align:center;font-size:2.5rem;color:#ffd700;font-weight:bold;margin:1rem}
input,select,button{padding:.8rem;border-radius:8px;border:1px solid #3a4560;background:#1a1e28;color:#fff;font-size:1rem;margin:.3rem}
input[type=url]{width:100%}
button{background:#2a6fd8;border:none;cursor:pointer;font-weight:bold;font-size:1.1rem}
button:hover{background:#3a8ff8}
#output{background:#12141a;border:1px solid #2a3040;border-radius:8px;padding:1.5rem;margin-top:1rem;display:none;white-space:pre-wrap;font-family:monospace;font-size:.85rem}
.free{color:#6ad86a;text-align:center;margin:.5rem}
.speech{background:#1a2a3a;border:1px solid #3a5a7a;border-radius:12px;padding:1rem;margin:1rem auto;max-width:500px;text-align:center;font-style:italic;color:#c0d8f0}
</style></head><body>
<h1>ASGARD LAB</h1>
<div class="tagline">Loquere lingua tua. Omnes te audient sua lingua. Tua voce.</div>

<div class="speech" id="speech">
  Vlož YouTube URL. Přeložím, nadabuju, ukážu znakově. Autonomně. Bez lidského zásahu.
</div>

<div class="principle">1 + 1 = 3</div>

<input type="url" id="url" placeholder="Paste YouTube URL...">
<div style="display:flex;gap:.5rem;margin-top:.5rem;justify-content:center">
<select id="lang">
<option value="cs">Čeština</option><option value="en">English</option>
<option value="de">Deutsch</option><option value="fr">Français</option>
<option value="es">Español</option><option value="ja">日本語</option>
<option value="ko">한국어</option><option value="zh">中文</option>
<option value="pl">Polski</option><option value="sk">Slovenčina</option>
<option value="mn">Монгол</option><option value="la">Latina</option>
</select>
<button onclick="runTranslation()">Translate + Dub + Sign</button>
</div>
<div class="free">Sign language: FREE for deaf community. Always.</div>

<div id="output"></div>

<script>
async function runTranslation(){
  const url=document.getElementById('url').value;
  const lang=document.getElementById('lang').value;
  const out=document.getElementById('output');
  const speech=document.getElementById('speech');
  if(!url){alert('Paste YouTube URL');return}
  out.style.display='block';
  speech.textContent='Pracuju na tom... moment.';
  out.textContent='Pipeline running autonomously...\\n';
  try{
    const r=await fetch('/translate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url,target:lang})});
    const d=await r.json();
    if(d.status==='success'){
      speech.textContent='Hotovo! Prelozeno, nadabovano, znakova rec pripravena.';
      out.textContent='PIPELINE COMPLETE (1+1=3)\\n\\n'+
        'Translation: '+d.subtitles_translated+'/'+d.subtitles_total+' ('+d.translation_time_s.toFixed(1)+'s)\\n'+
        'Dubbing: generated ('+d.dubbing_time_s.toFixed(1)+'s)\\n'+
        'Sign Language: '+d.sign_language_glosses+' glosses (FREE)\\n'+
        'Total: '+d.total_time_s.toFixed(1)+'s\\n\\n'+
        'Files:\\n'+JSON.stringify(d.files,null,2);
      // Zobrazit glosses
      if(d.sign_language_glosses>0){
        const signDiv=document.createElement('div');
        signDiv.style='margin-top:1rem;padding:1rem;background:#0a2a0a;border:2px solid #22c55e;border-radius:8px;color:#22c55e;font-size:1.2rem;text-align:center';
        signDiv.innerHTML='<b>SIGN LANGUAGE (FREE)</b><br>'+d.sign_language_glosses+' glosses generated<br><small style=\"color:#6ad86a\">Czech Sign Language (CZJ) + ASL + BSL + DGS</small>';
        out.parentNode.insertBefore(signDiv,out.nextSibling);
      }
    }else{
      speech.textContent='Hmm, neco se nepovedlo. Zkus to znova.';
      out.textContent='Error: '+JSON.stringify(d);
    }
  }catch(e){
    speech.textContent='Chyba spojeni. Jsem tu, zkus to znova.';
    out.textContent=e.message;
  }
}
</script>
<p style="text-align:center;color:#4a5a6a;margin-top:2rem">
Ada/SPARK verified | Gemini + Groq | Solar powered<br>
Hoc est via. | <a href="https://web4light.online" style="color:#5a8fd8">web4light.online</a> | XPRIZE 2026
</p></body></html>"""


@app.get("/pricing")
async def pricing():
    return {
        "standard_700": "1 GROS = 12g silver",
        "tiers": {
            "free": {"price": "0", "features": ["Sign language (CZJ, ASL, BSL, DGS)", "Audio navigation for blind"]},
            "gros_1": {"price": "111 CZK / 1 GROS", "features": ["AI assistant", "5 videos/day"]},
            "gros_2": {"price": "222 CZK / 2 GROS", "features": ["Translation + voice dubbing", "Unlimited"]},
            "gros_3": {"price": "333 CZK / 3 GROS", "features": ["Stream dubbing", "Real-time"]},
            "gros_4": {"price": "423 CZK / 4 GROS", "features": ["Everything", "Whole family", "Charter member"]}
        },
        "payment": {
            "network": "Sepolia ETH (testnet)",
            "contract": "PrazskyGros.sol (ERC-20)",
            "wallet": "Connect MetaMask to pay with GROS"
        },
        "free_forever": ["Sign language for deaf", "Audio navigation for blind"],
        "principle": "1+1=3"
    }


@app.get("/status")
async def status():
    return {
        "status": "running",
        "pipeline": "ready",
        "engines": {
            "gemini": "active" if GEMINI_KEY else "unavailable",
            "groq": "active" if GROQ_KEY else "unavailable",
            "tts": "gtts",
            "sign_language": "czj",
        },
        "principle": "1+1=3",
    }


@app.post("/translate")
async def translate(req: TranslateRequest):
    start_time = time.time()
    
    try:
        # 1. Download subtitles
        source_lang = req.source if req.source != "auto" else "en"
        srt_path = download_youtube_subs(req.url, lang=source_lang)
        
        # 2. Translate
        subtitles, fmt = load_subtitles(Path(srt_path))
        translator = GeminiSubtitleTranslator(engine="auto")
        translated, stats = translator.translate_subtitles(
            subtitles, target_lang=req.target, source_lang=req.source
        )
        
        # Save translated
        translated_path = srt_path.replace(".srt", f"_{req.target}.srt")
        save_subtitles(translated, Path(translated_path), fmt="srt")
        
        translation_time = time.time() - start_time
        
        # 3. Dirigent (Ada orchestrace hlasů)
        dirigent_bin = Path(__file__).parent.parent / "bin" / "dirigent_main"
        dirigent_result = None
        if dirigent_bin.exists():
            import subprocess as sp
            dr = sp.run([str(dirigent_bin), "--status"],
                       capture_output=True, text=True, timeout=5)
            if dr.returncode == 0:
                dirigent_result = json.loads(dr.stdout)

        # 4. Dub
        dub_start = time.time()
        dubbed_path = srt_path.replace(".srt", f"_{req.target}_dubbed.mp3")
        dub_file(
            input_path=translated_path,
            output_path=dubbed_path,
            engine="gtts",
            lang=req.target,
        )
        dubbing_time = time.time() - dub_start
        
        # 5. Sign language
        sign_start = time.time()
        renderer = SignLanguageRenderer(language=SignLanguage.CZJ, use_gemini=True)
        sign_path = srt_path.replace(".srt", "_signs.json")
        sign_stats = renderer.render_subtitles(translated_path, sign_path)
        
        total_time = time.time() - start_time
        
        return TranslateResponse(
            status="success",
            subtitles_translated=stats.translated_subtitles,
            subtitles_total=stats.total_subtitles,
            translation_time_s=round(translation_time, 1),
            dubbing_time_s=round(dubbing_time, 1),
            sign_language_glosses=sign_stats.total_glosses,
            total_time_s=round(total_time, 1),
            files={
                "subtitles": translated_path,
                "dubbing": dubbed_path,
                "sign_language": sign_path,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === MAIN ===
if __name__ == "__main__":
    print("═══════════════════════════════════════════════")
    print("  ⚡ ASGARD LAB — Web API Server")
    print(f"  http://localhost:{PORT}")
    print("  1+1=3: Translation + Dubbing + Sign Language")
    print("═══════════════════════════════════════════════")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
