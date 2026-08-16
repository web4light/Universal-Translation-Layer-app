"""
Cave Lab — AI Web & Graphics Studio
======================================
Zadej prompt → dostaneš hotový web + grafiku.

"První umělecké malby jsou z jeskyní. Cave Lab je návrat ke kořenům tvorby."

Použití:
    python cave_lab.py "Vytvoř web pro restauraci U Zlatého hroznu"
    python cave_lab.py "Landing page pro fitness trenéra"
    python cave_lab.py --server  (spustí web studio na :8001)

Autor: Pan Jeskyně
Organizace: Rebirth Phoenix Foundation Charter
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

from groq import Groq

# Gemini
try:
    from google import genai
    _GEMINI = True
except ImportError:
    _GEMINI = False

# === CONFIG ===
GROQ_KEY = os.environ.get("GROQ_API_KEY") or Path(Path.home() / ".groq_api_key").read_text().strip().split("=")[-1]
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or Path(Path.home() / ".gemini_api_key").read_text().strip().split("=")[-1]

os.environ["GROQ_API_KEY"] = GROQ_KEY
os.environ["GEMINI_API_KEY"] = GEMINI_KEY

OUTPUT_DIR = Path("/tmp/cave_lab_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# === WEB GENERATOR ===

def generate_website(prompt: str) -> dict:
    """Generuj kompletní web z promptu."""
    
    client = Groq()
    
    system_prompt = """Jsi Cave Lab — AI web designer. Generuješ kompletní HTML webové stránky.

PRAVIDLA:
- Vrať POUZE HTML kód (žádný markdown, žádné vysvětlování)
- Vše v jednom souboru (inline CSS + JS)
- Moderní design (tmavý/světlý podle kontextu)
- Responsive (mobile-first)
- Čeština jako výchozí jazyk
- Přidej favicon emoji v <title>
- Použij Google Fonts
- Přidej interaktivní prvky kde to dává smysl
- ŽÁDNÉ placeholder texty — vymysli reálný obsah"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Vytvoř kompletní webovou stránku: {prompt}"}
        ],
        max_tokens=8000,
    )
    
    html = response.choices[0].message.content
    
    # Vyčistit (odstranit případné markdown backticks)
    if html.startswith("```"):
        html = html.split("\n", 1)[1]
    if html.endswith("```"):
        html = html.rsplit("```", 1)[0]
    html = html.strip()
    
    # Uložit
    filename = prompt[:40].replace(" ", "_").replace("/", "_") + ".html"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(html, encoding="utf-8")
    
    return {
        "status": "success",
        "file": str(filepath),
        "size": len(html),
        "prompt": prompt,
    }


# === GRAPHICS GENERATOR (text description) ===

def generate_graphics_prompt(prompt: str) -> dict:
    """Generuj popis grafiky pro AI image generator."""
    
    client = Groq()
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Jsi grafický designer. Na základě zadání vytvoř detailní prompt pro AI image generátor (Midjourney/DALL-E styl). Vrať POUZE prompt v angličtině, nic jiného."},
            {"role": "user", "content": f"Vytvoř grafický prompt pro: {prompt}"}
        ],
        max_tokens=500,
    )
    
    return {
        "status": "success",
        "image_prompt": response.choices[0].message.content.strip(),
        "original_prompt": prompt,
    }


# === FULL STUDIO (web + grafika) ===

def create_project(prompt: str) -> dict:
    """Kompletní projekt — web + grafika."""
    
    print(f"🎨 Cave Lab — Tvořím projekt: {prompt}")
    print()
    
    # 1. Web
    print("  [1/2] Generuji webovou stránku...")
    start = time.time()
    web = generate_website(prompt)
    web_time = time.time() - start
    print(f"  ✓ Web: {web['file']} ({web['size']} bytes, {web_time:.1f}s)")
    
    # 2. Grafika
    print("  [2/2] Generuji grafický návrh...")
    start = time.time()
    gfx = generate_graphics_prompt(prompt)
    gfx_time = time.time() - start
    print(f"  ✓ Grafika prompt: {gfx['image_prompt'][:80]}...")
    print(f"    ({gfx_time:.1f}s)")
    
    print()
    print("═══════════════════════════════════════")
    print(f"  🎨 Cave Lab — Projekt hotov!")
    print(f"  📄 Web: {web['file']}")
    print(f"  🖼️  Grafika: použij prompt v Gemini/DALL-E")
    print("═══════════════════════════════════════")
    
    return {"web": web, "graphics": gfx}


# === WEB SERVER MODE ===

def run_server():
    """Spustí Cave Lab jako web studio na :8001."""
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
    
    app = FastAPI(title="Cave Lab", description="AI Web & Graphics Studio")
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>🎨 Cave Lab</title>
<style>
body{background:#0a0a0f;color:#e0e8f0;font-family:Arial;max-width:700px;margin:0 auto;padding:2rem}
h1{text-align:center;font-size:2.5rem}
.sub{text-align:center;color:#8ba4c8;font-style:italic;margin-bottom:2rem}
textarea{width:100%;padding:1rem;border-radius:8px;border:1px solid #3a4560;background:#1a1e28;color:#fff;font-size:1rem;min-height:80px;resize:vertical}
button{width:100%;padding:1rem;border-radius:8px;border:none;background:#6a3fd8;color:#fff;font-size:1.1rem;font-weight:bold;cursor:pointer;margin-top:.5rem}
button:hover{background:#8a5ff8}
#output{background:#12141a;border:1px solid #2a3040;border-radius:8px;padding:1.5rem;margin-top:1rem;display:none;white-space:pre-wrap}
</style></head><body>
<h1>🎨 Cave Lab</h1>
<div class="sub">AI Web & Graphics Studio<br>"První malby jsou z jeskyní"</div>
<textarea id="prompt" placeholder="Popiš co chceš vytvořit...&#10;Např: Web pro kavárnu v centru Prahy"></textarea>
<button onclick="generate()">🚀 Vytvořit web + grafiku</button>
<div id="output"></div>
<script>
async function generate(){
  const p=document.getElementById('prompt').value;
  const o=document.getElementById('output');
  if(!p){alert('Zadej popis');return}
  o.style.display='block';
  o.textContent='🎨 Cave Lab pracuje...';
  const r=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})});
  const d=await r.json();
  if(d.status==='success'){
    o.innerHTML='✅ Web vygenerován!\\n\\n📄 '+d.web.file+'\\n🖼️ Image prompt: '+d.graphics.image_prompt+'\\n\\n<a href="/preview?file='+encodeURIComponent(d.web.file)+'" target="_blank" style="color:#6a3fd8">▶ Náhled webu</a>';
  }else{o.textContent='❌ '+JSON.stringify(d)}
}
</script>
<p style="text-align:center;color:#4a5a6a;margin-top:2rem">Cave Lab • Asgard Studio • web4light.online</p>
</body></html>"""
    
    @app.post("/generate")
    async def generate(data: dict):
        result = create_project(data["prompt"])
        return {"status": "success", "web": result["web"], "graphics": result["graphics"]}
    
    @app.get("/preview")
    async def preview(file: str):
        p = Path(file)
        if p.exists():
            return HTMLResponse(p.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>File not found</h1>")
    
    print("═══════════════════════════════════════")
    print("  🎨 CAVE LAB — AI Web & Graphics Studio")
    print("  http://localhost:8001")
    print("  'První malby jsou z jeskyní'")
    print("═══════════════════════════════════════")
    uvicorn.run(app, host="0.0.0.0", port=8001)


# === CLI ===

def main():
    parser = argparse.ArgumentParser(description="Cave Lab — AI Web & Graphics Studio")
    parser.add_argument("prompt", nargs="?", help="Popis webu/grafiky")
    parser.add_argument("--server", action="store_true", help="Spustit web studio na :8001")
    args = parser.parse_args()
    
    if args.server:
        run_server()
    elif args.prompt:
        create_project(args.prompt)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
