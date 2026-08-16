#!/usr/bin/env python3
"""
Asgard Vision MCP Server — grafický modul pro Kiro CLI.

Poskytuje:
1. generate_svg — SCADA/ConWin diagram z popisu
2. analyze_image — Gemini multimodal popis obrázku
3. generate_scada — interaktivní HTML dashboard

Kiro CLI konfigurace (~/.kiro/settings/mcp.json):
{
  "mcpServers": {
    "asgard-vision": {
      "command": "python3",
      "args": ["/home/pj/Universal-Translation-Layer/src/vision_mcp.py"],
      "env": {"GEMINI_API_KEY": "${GEMINI_API_KEY}"}
    }
  }
}

Autor: Pan Jeskyně
"""

import os
import sys
import json
import base64
from pathlib import Path

# MCP stdio protocol
def read_request():
    """Přečti JSON-RPC request ze stdin."""
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line)

def write_response(result):
    """Zapiš JSON-RPC response na stdout."""
    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()


# === TOOLS ===

OUTPUT_DIR = Path("/tmp/asgard_vision")
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_svg(components: list, connections: list, title: str = "Asgard Lab") -> str:
    """Vygeneruj SVG SCADA diagram."""
    
    width = 1200
    height = 800
    
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="2" dy="2" stdDeviation="2" flood-opacity="0.3"/>
    </filter>
    <marker id="arrow" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#2196F3"/>
    </marker>
    <marker id="arrow-red" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#F44336"/>
    </marker>
  </defs>
  
  <!-- Pozadí -->
  <rect width="{width}" height="{height}" fill="#E8F5E9" rx="8"/>
  
  <!-- Titulek -->
  <text x="{width//2}" y="35" text-anchor="middle" font-family="Arial" font-size="24" font-weight="bold" fill="#1B5E20">{title}</text>
  <text x="{width//2}" y="55" text-anchor="middle" font-family="Arial" font-size="12" fill="#4CAF50">SCADA — Live Monitoring Panel</text>
  
  <!-- Mřížka -->
  <g opacity="0.1">
'''
    for x in range(0, width, 50):
        svg += f'    <line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="#000" stroke-width="0.5"/>\n'
    for y in range(0, height, 50):
        svg += f'    <line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="#000" stroke-width="0.5"/>\n'
    svg += '  </g>\n\n'
    
    # Rozložení komponent v mřížce
    cols = 4
    box_w = 220
    box_h = 100
    margin_x = 50
    margin_y = 80
    start_y = 80
    
    positions = {}
    
    for i, comp in enumerate(components):
        col = i % cols
        row = i // cols
        x = margin_x + col * (box_w + 40)
        y = start_y + row * (box_h + margin_y)
        positions[comp.get("id", f"c{i}")] = (x + box_w // 2, y + box_h // 2)
        
        # Barva podle stavu
        state = comp.get("state", "on")
        fill = "#C8E6C9" if state == "on" else "#FFCDD2"
        border = "#2E7D32" if state == "on" else "#C62828"
        dot = "#4CAF50" if state == "on" else "#F44336"
        
        # Box
        svg += f'''  <!-- {comp.get("name", "")} -->
  <g filter="url(#shadow)">
    <rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" fill="{fill}" stroke="{border}" stroke-width="2" rx="6"/>
    <circle cx="{x + 15}" cy="{y + 15}" r="6" fill="{dot}"/>
    <text x="{x + 30}" y="{y + 18}" font-family="Arial" font-size="11" font-weight="bold" fill="{border}">{comp.get("name", "")}</text>
    <text x="{x + 10}" y="{y + 40}" font-family="monospace" font-size="10" fill="#333">{comp.get("port", "")}</text>
    <text x="{x + 10}" y="{y + 58}" font-family="monospace" font-size="11" fill="#1565C0">{comp.get("value", "")}</text>
    <text x="{x + 10}" y="{y + 76}" font-family="Arial" font-size="9" fill="#666">{comp.get("desc", "")}</text>
  </g>
  
  <!-- Ventil (jistič) -->
  <polygon points="{x - 15},{y + 40} {x - 5},{y + 30} {x - 5},{y + 50}" fill="{dot}" stroke="{border}" stroke-width="1"/>

'''
    
    # Spojení
    for conn in connections:
        src = positions.get(conn.get("from", ""))
        dst = positions.get(conn.get("to", ""))
        if src and dst:
            color = conn.get("color", "#2196F3")
            marker = "arrow-red" if color == "#F44336" else "arrow"
            svg += f'  <line x1="{src[0]}" y1="{src[1]}" x2="{dst[0]}" y2="{dst[1]}" stroke="{color}" stroke-width="2" marker-end="url(#{marker})" opacity="0.7"/>\n'
    
    # Patička
    svg += f'''
  <!-- Patička -->
  <rect x="0" y="{height - 40}" width="{width}" height="40" fill="#1B5E20" opacity="0.9"/>
  <text x="20" y="{height - 15}" font-family="monospace" font-size="12" fill="#A5D6A7">SPARK PROVED: 286+ checks | 0 errors | Hoc est via</text>
  <text x="{width - 200}" y="{height - 15}" font-family="monospace" font-size="12" fill="#A5D6A7">web4light.online</text>
</svg>'''
    
    # Ulož
    out_path = OUTPUT_DIR / "asgard_scada.svg"
    out_path.write_text(svg, encoding="utf-8")
    return str(out_path)


def analyze_image(image_path: str) -> str:
    """Analyzuj obrázek přes Gemini multimodal."""
    try:
        import google.genai as genai
        
        key = os.environ.get("GEMINI_API_KEY") or \
              Path.home().joinpath(".gemini_api_key").read_text().strip().split("=")[-1]
        
        client = genai.Client(api_key=key)
        
        img_data = Path(image_path).read_bytes()
        img_b64 = base64.b64encode(img_data).decode()
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {"parts": [
                    {"text": "Popiš detailně co je na tomto obrázku. Zaměř se na: rozložení prvků, barvy, text, typ diagramu/UI. Odpověz česky."},
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}}
                ]}
            ]
        )
        
        return response.text
    except Exception as e:
        return f"Chyba analýzy: {e}"


def generate_scada_default() -> str:
    """Vygeneruj výchozí SCADA pro Asgard Lab."""
    
    components = [
        {"id": "asgard", "name": "ASGARD SERVER", "port": ":8000", "value": "T: 61 subtitles", "desc": "Translation pipeline", "state": "on"},
        {"id": "cave", "name": "CAVE LAB", "port": ":8001", "value": "Web generator", "desc": "AI Web Studio", "state": "on"},
        {"id": "gemini", "name": "GEMINI API", "port": "cloud", "value": "22+ langs", "desc": "Translation engine", "state": "on"},
        {"id": "dirigent", "name": "DIRIGENT", "port": "bin/", "value": "0 overlaps", "desc": "Ada orchestrator (PROVED)", "state": "on"},
        {"id": "shadow", "name": "SHADOW NODE", "port": ":9303", "value": "failover 20s", "desc": "Hot standby", "state": "on"},
        {"id": "watchdog", "name": "WATCHDOG", "port": ":9304", "value": "Heimdall", "desc": "Mesh guardian", "state": "on"},
        {"id": "privacy", "name": "PRIVACY 4:23", "port": ":9305", "value": "daily purge", "desc": "Metadata cleanup", "state": "on"},
        {"id": "prometheus", "name": "PROMETHEUS", "port": ":9307", "value": "286 checks", "desc": "Ada metrics server", "state": "on"},
        {"id": "tts", "name": "TTS DUBBER", "port": "gTTS", "value": "Edge/Spark", "desc": "Voice synthesis", "state": "on"},
        {"id": "sign", "name": "SIGN LANGUAGE", "port": "CZJ", "value": "142 glosses", "desc": "FREE forever", "state": "on"},
        {"id": "dlp3d", "name": "DLP3D AVATAR", "port": "MIT", "value": "Babylon.js", "desc": "3D sign avatar", "state": "on"},
        {"id": "wallet", "name": "ETH WALLET", "port": "Sepolia", "value": "Soulbound NFT", "desc": "KYC/Identity", "state": "off"},
    ]
    
    connections = [
        {"from": "asgard", "to": "gemini", "color": "#2196F3"},
        {"from": "gemini", "to": "dirigent", "color": "#F44336"},
        {"from": "dirigent", "to": "tts", "color": "#F44336"},
        {"from": "dirigent", "to": "sign", "color": "#2196F3"},
        {"from": "sign", "to": "dlp3d", "color": "#2196F3"},
        {"from": "asgard", "to": "prometheus", "color": "#4CAF50"},
        {"from": "shadow", "to": "asgard", "color": "#FF9800"},
        {"from": "watchdog", "to": "shadow", "color": "#FF9800"},
        {"from": "wallet", "to": "asgard", "color": "#9C27B0"},
    ]
    
    return generate_svg(components, connections, "ASGARD LAB — SCADA Panel")


# === MCP PROTOCOL (stdio) ===

TOOLS = {
    "generate_scada": {
        "description": "Vygeneruje SCADA/ConWin SVG diagram systému Asgard Lab",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulek diagramu"}
            }
        }
    },
    "analyze_image": {
        "description": "Analyzuje obrázek přes Gemini multimodal a vrátí textový popis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Cesta k PNG/JPG souboru"}
            },
            "required": ["image_path"]
        }
    },
    "generate_svg": {
        "description": "Vygeneruje SVG z popisu komponent a spojení (SCADA styl)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "components": {"type": "array", "description": "Seznam komponent"},
                "connections": {"type": "array", "description": "Seznam spojení"},
                "title": {"type": "string", "description": "Titulek"}
            },
            "required": ["components", "connections"]
        }
    }
}


def handle_request(req):
    """Zpracuj MCP request."""
    method = req.get("method", "")
    params = req.get("params", {})
    req_id = req.get("id")
    
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "asgard-vision", "version": "1.0"}
        }}
    
    elif method == "tools/list":
        tools = [{"name": k, **v} for k, v in TOOLS.items()]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        
        if tool_name == "generate_scada":
            path = generate_scada_default()
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "content": [{"type": "text", "text": f"SCADA SVG vygenerován: {path}"}]
            }}
        
        elif tool_name == "analyze_image":
            desc = analyze_image(args.get("image_path", ""))
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "content": [{"type": "text", "text": desc}]
            }}
        
        elif tool_name == "generate_svg":
            path = generate_svg(
                args.get("components", []),
                args.get("connections", []),
                args.get("title", "Asgard Lab")
            )
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "content": [{"type": "text", "text": f"SVG vygenerován: {path}"}]
            }}
        
        return {"jsonrpc": "2.0", "id": req_id, "error": {
            "code": -32601, "message": f"Unknown tool: {tool_name}"
        }}
    
    elif method == "notifications/initialized":
        return None  # no response needed
    
    return {"jsonrpc": "2.0", "id": req_id, "error": {
        "code": -32601, "message": f"Unknown method: {method}"
    }}


def main():
    """Hlavní MCP stdio loop."""
    # Pokud spuštěn bez argumentů — vygeneruj default SCADA
    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        path = generate_scada_default()
        print(f"SCADA SVG: {path}")
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == "--analyze":
        desc = analyze_image(sys.argv[2])
        print(desc)
        return
    
    # MCP stdio mode
    while True:
        req = read_request()
        if req is None:
            break
        resp = handle_request(req)
        if resp:
            write_response(resp)


if __name__ == "__main__":
    main()
