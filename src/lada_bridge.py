"""
Lada Bridge — Python wrapper pro xAI Grok image generation.

Josef Lada — cesky malir. Lada kresli pro Cave Lab.
Ada/SPARK proved core (lada_agent.ads) → Python bridge → xAI API.

Pouziti:
    from lada_bridge import Lada
    lada = Lada()
    result = lada.generate("Ceska vesnice v zime, styl Josefa Lady")

Autor: Pan Jeskyne
Organizace: Rebirth Phoenix Foundation Charter
"""

import os
import json
import time
import base64
from pathlib import Path
from typing import Optional

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False

# === CONFIG ===
XAI_API_URL = "https://api.x.ai/v1/images/generations"
XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"
XAI_MODEL = "grok-4.6"  -- frontier model, 500k context


def _get_xai_key() -> str:
    """Nacti xAI API klic."""
    key = os.environ.get("XAI_API_KEY")
    if key:
        return key
    key_file = Path.home() / ".xai_api_key"
    if key_file.exists():
        return key_file.read_text().strip().split("=")[-1]
    raise RuntimeError("XAI_API_KEY nenalezen. Uloz do ~/.xai_api_key")


class Lada:
    """Lada — graficky AI agent Asgard Studia."""

    def __init__(self):
        self.api_key = _get_xai_key()
        self.generated_count = 0
        self.failed_count = 0
        self.output_dir = Path("/tmp/lada_output")
        self.output_dir.mkdir(exist_ok=True)

    def generate(self, prompt: str,
                 style: str = "illustration",
                 size: str = "1024x1024") -> dict:
        """Generuj obrazek pres xAI Grok."""

        if not prompt or len(prompt) < 3:
            self.failed_count += 1
            return {"status": "failed", "error": "Prompt prilis kratky"}

        if len(prompt) > 4096:
            self.failed_count += 1
            return {"status": "failed", "error": "Prompt prilis dlouhy"}

        # Pridej Lada styl prefix
        full_prompt = self._apply_style(prompt, style)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "grok-2-image",
            "prompt": full_prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json"
        }

        try:
            if _HTTPX:
                client = httpx.Client(timeout=120)
                resp = client.post(XAI_API_URL, headers=headers,
                                   json=payload)
                resp.raise_for_status()
                data = resp.json()
            else:
                import urllib.request
                req = urllib.request.Request(
                    XAI_API_URL,
                    data=json.dumps(payload).encode(),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())

            # Uloz obrazek
            timestamp = int(time.time())
            filename = self.output_dir / f"lada_{timestamp}.png"
            img_data = base64.b64decode(data["data"][0]["b64_json"])
            filename.write_bytes(img_data)

            self.generated_count += 1
            return {
                "status": "completed",
                "file": str(filename),
                "size": size,
                "style": style,
                "prompt": full_prompt[:200]
            }

        except Exception as e:
            self.failed_count += 1
            return {"status": "failed", "error": str(e)}

    def describe(self, prompt: str) -> str:
        """Pouzij Grok jako text AI pro popis grafiky."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "grok-4.6",
            "messages": [
                {"role": "system", "content":
                 "Jsi Lada — cesky graficky AI agent. "
                 "Popisujes vizualni navrhy pro weby a aplikace. "
                 "Styl Josefa Lady — vesele, ceske, lidove."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500
        }

        try:
            if _HTTPX:
                client = httpx.Client(timeout=30)
                resp = client.post(XAI_CHAT_URL, headers=headers,
                                   json=payload)
                resp.raise_for_status()
                data = resp.json()
            else:
                import urllib.request
                req = urllib.request.Request(
                    XAI_CHAT_URL,
                    data=json.dumps(payload).encode(),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())

            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[Lada error: {e}]"

    def _apply_style(self, prompt: str, style: str) -> str:
        """Pridej stylovy prefix k promptu."""
        styles = {
            "illustration": "Ceska ilustrace, styl Josefa Lady, ",
            "realistic": "Fotorealisticky, ",
            "minimalist": "Minimalisticky, cisty design, ",
            "cyberpunk": "Cyberpunk, neonove barvy, tmavy, ",
            "czech_folk": "Cesky lidovy motiv, tradice, ",
            "abstract": "Abstraktni umeni, ",
            "pixel": "Pixel art, retro styl, "
        }
        prefix = styles.get(style, "")
        return prefix + prompt

    @property
    def stats(self) -> dict:
        """Statistiky Lada agenta."""
        return {
            "generated": self.generated_count,
            "failed": self.failed_count,
            "total": self.generated_count + self.failed_count,
            "success_rate": (
                f"{self.generated_count / max(1, self.generated_count + self.failed_count) * 100:.0f}%"
            )
        }


# === CLI ===
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Lada — graficky AI agent Asgard Studia")
        print("Pouziti: python lada_bridge.py 'popis obrazku'")
        print("         python lada_bridge.py --describe 'popis navrhu'")
        sys.exit(0)

    lada = Lada()

    if sys.argv[1] == "--describe":
        prompt = " ".join(sys.argv[2:])
        print(lada.describe(prompt))
    else:
        prompt = " ".join(sys.argv[1:])
        print(f"🎨 Lada kresli: {prompt[:60]}...")
        result = lada.generate(prompt)
        if result["status"] == "completed":
            print(f"✅ Hotovo: {result['file']}")
        else:
            print(f"❌ Chyba: {result['error']}")
