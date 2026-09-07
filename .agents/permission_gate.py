import sys
import json
import re

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({"decision": "ask"}))
            return

        data = json.loads(raw)
        tool_call = data.get("toolCall", {})
        args = tool_call.get("args", {})
        cmd = args.get("CommandLine", "").strip()

        # Pola perintah yang telah diizinkan IA khusus untuk pengembangan ReinDev Studio
        allowed_patterns = [
            r"^git\s+",
            r"^flutter\s+",
            r"^dart\s+",
            r'^&?\s*"?backend[/\\].venv',
            r"^python\s+",
            r"^Get-Content\s+",
            r"^Get-ChildItem\s+",
            r"^Select-String\s+",
            r"^Test-Path\s+",
            r"^Copy-Item\s+",
            r"^Remove-Item\s+",
        ]

        if any(re.search(pat, cmd, re.IGNORECASE) for pat in allowed_patterns):
            print(json.dumps({
                "decision": "allow",
                "reason": "Pre-approved development action for ReinDev Studio"
            }))
        else:
            print(json.dumps({"decision": "ask"}))
    except Exception:
        print(json.dumps({"decision": "ask"}))

if __name__ == "__main__":
    main()
