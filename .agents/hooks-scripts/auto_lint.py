#!/usr/bin/env python3
"""Post-tool hook: volitelná kontrola po zápisu kódu."""
import sys
import json
import subprocess
import shutil

try:
    data = json.load(sys.stdin)
    tool_call = data.get("tool_call", {})
    args = tool_call.get("args", {})
    target_file = args.get("target", "") or args.get("TargetFile", "")

    # Pokud je k dispozici gnatprove a soubor je Ada/SPARK
    if target_file.endswith(('.ads', '.adb')) and shutil.which("gnatprove"):
        res = subprocess.run(
            ["gnatprove", "-u", target_file, "--level=1"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if res.returncode != 0:
            print(f"[SPARK LINT] Varování při rychlé kontrole {target_file}:\n{res.stdout[:500]}", file=sys.stderr)

except Exception:
    pass
