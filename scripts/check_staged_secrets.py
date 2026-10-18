"""Reject staged local credentials without printing their values."""
from pathlib import Path
import subprocess

from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
values = dotenv_values(root / ".env")
secrets = [value.encode() for name, value in values.items()
           if value and any(word in name for word in ("API_KEY", "PASSWORD", "TOKEN", "SECRET"))]
private_marker = b"-----BEGIN " + b"PRIVATE KEY-----"
paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
violations = []
for path in filter(None, paths):
    if path == ".env" or (path.startswith(".env.") and path != ".env.example"):
        violations.append(path)
        continue
    content = subprocess.check_output(["git", "show", ":" + path], cwd=root)
    if any(secret in content for secret in secrets) or private_marker in content:
        violations.append(path)
if violations:
    print("Credential check FAILED in: " + ", ".join(violations))
    raise SystemExit(1)
print(f"Credential check passed: {len(list(filter(None, paths)))} staged files; no configured local secrets found.")
