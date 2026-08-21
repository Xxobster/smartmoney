from pathlib import Path

text = Path(r"C:\projects\videoanalysis\reports\secret_mindset\transcript_7J2djQ9C-dE.txt").read_text(encoding="utf-8")
# print numbered aspects
for i in range(1, 11):
    key = f"Number {i}"
    idx = text.find(key)
    if idx < 0:
        key = f"number {i}"
        idx = text.lower().find(key)
    print("====", key, idx)
    if idx >= 0:
        print(text[idx : idx + 420])
        print()
# full strategy sentence
for phrase in [
    "full strategy",
    "rising wedge",
    "falling wedge",
    "target",
    "breakout",
    "50 EMA",
    "100 EMA",
]:
    i = text.lower().find(phrase.lower())
    print("##", phrase, i)
    if i >= 0:
        print(text[i : i + 350])
        print()
