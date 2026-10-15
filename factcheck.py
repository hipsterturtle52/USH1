#!/usr/bin/env python3
"""Flag questions whose correct answer mentions names/numbers absent from all lesson material."""
import json, re, html as H
from pathlib import Path
src = Path(__file__).with_name("clep-us-history-1-study-guide.html").read_text(encoding="utf-8")
D = json.loads(re.search(r"const DATA=(\{.*?\});\n", src, re.S).group(1).replace("<\\/", "</"))
strip = lambda s: H.unescape(re.sub(r"<[^>]+>", " ", s))
corpus = " ".join(strip(u["lesson"]) + " " + " ".join(map(strip, u["must"])) + " " + " ".join(strip(t["e"]) + " " + t["y"] for t in u["timeline"]) + " " + " ".join(strip(c["f"] + " " + c["b"]) for c in u["cards"]) for u in D["units"]).lower()
STOP = {"The","A","An","In","Which","Of","And","Both","It","He","She","They","His","Her","Only","Most","All","No","Not","US","Congress","Union","South","North","West","American","Americans","States","United","State","Native","European","British","French","Spanish","Constitution","Court","Supreme","Party","President","After","During","Before","Many","Several","Some","Each","Their","This","That","From","For","With","By","As","On","At"}
flags = 0
for qid, q in D["Q"].items():
    right = strip(q["o"][q["a"]])
    terms = [t for t in re.findall(r"\b(?:[A-Z][a-zA-Z'’\-]+(?:\s+[A-Z][a-zA-Z'’\-]+)*|\d{4})\b", right)]
    missing = []
    for t in terms:
        words = [w for w in t.split() if w not in STOP]
        if words and not all(w.lower() in corpus for w in words):
            missing.append(t)
    if missing:
        flags += 1
        print(f"{qid:7} u{q['u']}: {right[:90]}  -> missing {missing}")
print(f"\n{flags} questions flagged for manual review out of {len(D['Q'])}")
