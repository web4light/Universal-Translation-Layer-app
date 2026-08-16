#!/usr/bin/env python3
"""Pre-tool hook pro SPARK Code Agenta: blokuje zakázané konstrukce."""
import sys
import json

try:
    data = json.load(sys.stdin)
    tool_call = data.get("tool_call", {})
    args = tool_call.get("args", {})
    content = args.get("content", "") + args.get("CodeContent", "")

    # Zakázaná klíčová slova a konstrukce
    forbidden = [
        "access ",
        "raise ",
        "new ",
        "Unchecked_Conversion",
        "Unchecked_Deallocation",
        "goto ",
        "abort;",
        "pragma Assume",
    ]

    violations = [w for w in forbidden if w in content]

    if violations:
        response = {
            "decision": "deny",
            "reason": (
                f"Kód porušuje pravidla SPARK! Nalezeny zakázané konstrukce: {', '.join(violations)}. "
                "Pravidla: Žádné pointery (access), alokace (new), výjimky (raise), unchecked konverze, goto ani pragma Assume."
            ),
        }
    else:
        response = {"decision": "allow"}

    print(json.dumps(response))

except Exception as e:
    # Při chybě skriptu nezablokovat běh (standardní fallback dle dokumentace)
    print(json.dumps({"decision": "allow"}))
