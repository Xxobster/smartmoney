"""Parse HA video VTT into plain text and print rule snippets."""
from __future__ import annotations

import re
from pathlib import Path

vtt = Path(r"C:\projects\videoanalysis\data\secret_mindset\ha_subs\7J2djQ9C-dE.en.vtt").read_text(encoding="utf-8")
lines = []
for line in vtt.splitlines():
    line = line.strip()
    if not line or line.startswith("WEBVTT") or "-->" in line or line.isdigit():
        continue
    line = re.sub(r"<[^>]+>", "", line)
    if line:
        lines.append(line)
# de-dupe consecutive
out = []
for x in lines:
    if not out or out[-1] != x:
        out.append(x)
text = " ".join(out)
Path(r"C:\projects\videoanalysis\reports\secret_mindset\transcript_7J2djQ9C-dE.txt").write_text(text, encoding="utf-8")
print("chars", len(text))
for kw in [
    "50",
    "EMA",
    "enter",
    "entry",
    "buy",
    "sell",
    "stop",
    "take profit",
    "heikin",
    "heiken",
    "green",
    "red",
    "color",
    "above",
    "below",
    "timeframe",
    "minute",
    "hour",
]:
    i = text.lower().find(kw.lower())
    print("====", kw, i)
    if i >= 0:
        print(text[max(0, i - 80) : i + 280])
        print()
