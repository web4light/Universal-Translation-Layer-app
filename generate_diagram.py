#!/usr/bin/env python3
"""
Generate high-resolution architecture diagram for Devpost upload.
"""
from PIL import Image, ImageDraw, ImageFont
import os

WIDTH = 1920
HEIGHT = 1080

img = Image.new("RGB", (WIDTH, HEIGHT), color="#090b14")
draw = ImageDraw.Draw(img)

# Background subtle grid / frame
draw.rectangle([40, 40, WIDTH-40, HEIGHT-40], outline="#d4af37", width=3)
draw.rectangle([50, 50, WIDTH-50, HEIGHT-50], outline="#1e293b", width=1)

# Header
draw.text((80, 70), "UNIVERSAL TRANSLATION LAYER (UTL) — PROTOCOL 4.23", fill="#ffd700")
draw.text((80, 110), "Sovereign 6-Layer Multi-Agent Architecture | All Things Agentic Hackathon", fill="#94a3b8")

# Layers configuration
layers = [
    ("LAYER 1: SOVEREIGN LANGUAGE & SPIRIT", "PJAY Language (.pj) — 'Hoc est via. Locutus sum.' | Agent Přemysl Oráč", "#7e22ce"),
    ("LAYER 2: AUTONOMOUS DIDACTIC TASKMASTER", "Agent Jan Amos Komenský — 5 Didactic Phases (Labyrinth -> Janua -> Orbis -> SPARK -> Ráj) with Gemini 3.5 Flash", "#2563eb"),
    ("LAYER 3: FORMAL MATHEMATICAL VERIFICATION", "Ada/SPARK 2022 Core — GNATprove Level 4 | 0% Crashes, 0 Heap, Bounded Types, Hippocratic Oath Proof", "#059669"),
    ("LAYER 4: NETWORK ORACLE & TELEMETRY", "Kněžna Libuše — Prometheus Telemetry (:9302/:9303) & Ethereum Geth Mirror (Keccak-256 / Standard 700)", "#d97706"),
    ("LAYER 5: ON-DEVICE INTERACTION MEMORY BANK", "Local SQLite Context Vault on User Device | 1 GB = 8 Years of Life | 100% Privacy & Zero Cloud Leakage", "#0891b2"),
    ("LAYER 6: SERVERLESS CLOUD DEPLOYMENT", "Google Cloud Run (Stateless Container via Dockerfile.cloudrun) | Scale-to-Zero ($0.00 Idle Cost)", "#dc2626")
]

start_y = 170
layer_h = 120
spacing = 20

for i, (title, desc, color) in enumerate(layers):
    y = start_y + i * (layer_h + spacing)
    # Box
    draw.rectangle([80, y, WIDTH-80, y + layer_h], fill="#111625", outline=color, width=2)
    # Accent pill
    draw.rectangle([80, y, 95, y + layer_h], fill=color)
    # Text
    draw.text((120, y + 25), title, fill=color)
    draw.text((120, y + 65), desc, fill="#f8fafc")

# Footer
draw.text((80, 1020), "Author: Pan Jeskyně (Solo Architect) | Foundation: Rebirth Phoenix Foundation Charter | License: GNU GPLv3", fill="#64748b")
draw.text((WIDTH - 480, 1020), "Status: 100% Formally Verified & Operational", fill="#4ade80")

out_path = "/home/asgard/Universal-Translation-Layer/architecture_diagram.png"
img.save(out_path, quality=95)
print(f"Generated architecture diagram at {out_path}")
