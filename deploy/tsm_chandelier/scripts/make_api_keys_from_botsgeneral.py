#!/usr/bin/env python3
"""Build config/api_keys.json from /etc/botsgeneral/bybit_keys.txt (account names only logged)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_botsgeneral_keys(path: Path) -> dict[str, dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    accounts: dict[str, dict] = {}
    cur: str | None = None
    api_key = ""
    api_secret = ""

    def flush() -> None:
        nonlocal cur, api_key, api_secret
        if cur and api_key and api_secret:
            accounts[cur] = {"api_key": api_key, "api_secret": api_secret, "testnet": False}
        cur, api_key, api_secret = None, "", ""

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(?i)^ACCOUNT:\s*(.+)$", line)
        if m:
            flush()
            cur = m.group(1).strip()
            continue
        m = re.match(r"(?i)^API\s*KEY:\s*(.+)$", line)
        if m and cur:
            api_key = m.group(1).strip()
            continue
        m = re.match(r"(?i)^API\s*SECRET:\s*(.+)$", line)
        if m and cur:
            api_secret = m.group(1).strip()
            continue
        # [XxobsterN] ini style
        m = re.match(r"^\[(.+)\]$", line)
        if m:
            flush()
            cur = m.group(1).strip()
            continue
        if "=" in line and cur:
            k, v = line.split("=", 1)
            k = k.strip().lower()
            v = v.strip().strip('"').strip("'")
            if k in ("api_key", "key"):
                api_key = v
            elif k in ("api_secret", "secret"):
                api_secret = v
    flush()
    return accounts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/etc/botsgeneral/bybit_keys.txt")
    ap.add_argument("--dst", default="/config/api_keys.json")
    ap.add_argument("--only", nargs="*", default=["Xxobster6"], help="Account names to keep")
    args = ap.parse_args()
    all_accts = parse_botsgeneral_keys(Path(args.src))
    keep = args.only or list(all_accts)
    out = {}
    for name in keep:
        if name not in all_accts:
            # case-insensitive
            lower = {k.lower(): k for k in all_accts}
            if name.lower() not in lower:
                raise SystemExit(f"account {name!r} not found in {args.src}; have={sorted(all_accts)}")
            name = lower[name.lower()]
        out[name] = all_accts[name]
    dst = Path(args.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    dst.chmod(0o600)
    print("wrote", dst, "accounts=", sorted(out))


if __name__ == "__main__":
    main()
