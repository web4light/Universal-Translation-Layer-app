#!/usr/bin/env python3
"""
Skript pro vytvoření a otestování SPARK Code Agenta v Google AI Studio / Gemini API.
Používá oficiální google-genai SDK s plnou podporou Managed Agents a Antigravity harnessu.
"""

import os
from pathlib import Path
from google import genai

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  Nastavte proměnnou prostředí GEMINI_API_KEY: export GEMINI_API_KEY='váš_klíč'")
        return

    client = genai.Client(api_key=api_key)

    agents_dir = Path(__file__).parent / ".agents"
    agents_md = (agents_dir / "AGENTS.md").read_text(encoding="utf-8")
    skill_md = (agents_dir / "skills/spark-verifier/SKILL.md").read_text(encoding="utf-8")
    hooks_json = (agents_dir / "hooks.json").read_text(encoding="utf-8")
    gate_py = (agents_dir / "hooks-scripts/check_spark_rules.py").read_text(encoding="utf-8")

    print("🚀 Vytvářím SPARK Managed Agenta v Google AI Studio...")

    agent = client.agents.create(
        id="spark-code-agent",
        base_agent="antigravity-preview-05-2026",
        agent_config={
            "type": "antigravity",
            "model": "gemini-3.7-flash",
        },
        system_instruction="Jsi Ada/SPARK Code Agent. Tvůj kód musí projít formální verifikací gnatprove bez chyb.",
        base_environment={
            "type": "remote",
            "sources": [
                {
                    "type": "inline",
                    "target": ".agents/AGENTS.md",
                    "content": agents_md,
                },
                {
                    "type": "inline",
                    "target": ".agents/skills/spark-verifier/SKILL.md",
                    "content": skill_md,
                },
                {
                    "type": "inline",
                    "target": ".agents/hooks.json",
                    "content": hooks_json,
                },
                {
                    "type": "inline",
                    "target": ".agents/hooks-scripts/check_spark_rules.py",
                    "content": gate_py,
                },
            ],
        },
    )

    print(f"✅ Agent úspěšně vytvořen! ID: {agent.id}")
    print("\nOdesílám testovací úlohu agentovi...")

    interaction = client.interactions.create(
        agent=agent.id,
        input="Navrhni balíček Safe_Ring_Buffer pro 32 celočíselných hodnot v Ada/SPARK s Pre/Post kontrakty.",
    )

    print("\n--- Výstup SPARK Agenta ---")
    print(interaction.output_text)

if __name__ == "__main__":
    main()
