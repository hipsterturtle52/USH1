#!/usr/bin/env python3
"""Static audit of the built study guide: extracts DATA from the HTML and checks every question."""
import json, re, sys, collections
from pathlib import Path
html = Path(__file__).with_name("clep-us-history-1-study-guide.html").read_text(encoding="utf-8")
m = re.search(r"const DATA=(\{.*?\});\n", html, re.S)
D = json.loads(m.group(1).replace("<\\/", "</"))
Q, U = D["Q"], D["units"]
problems = []
for qid, q in Q.items():
    if len(q["o"]) != 5: problems.append(f"{qid}: {len(q['o'])} options")
    if not (0 <= q["a"] < 5): problems.append(f"{qid}: bad answer index")
    if len(set(o.lower() for o in q["o"])) != 5: problems.append(f"{qid}: duplicate options")
    if len(q["e"]) != 5 or any(not e.strip() for e in q["e"]): problems.append(f"{qid}: missing explanation")
    if q["u"] not in range(1, 13): problems.append(f"{qid}: bad unit tag")
    if q["t"] not in "PSECD": problems.append(f"{qid}: bad topic tag")
    if q["d"] not in (1, 2, 3): problems.append(f"{qid}: bad difficulty")
pools = {"quiz": [i for u in U for i in u["quiz"]], "diag": D["diag"], "examA": D["exams"][0], "examB": D["exams"][1]}
allp = sum(pools.values(), [])
if len(allp) != len(set(allp)): problems.append("pools overlap")
if set(allp) != set(Q): problems.append("some questions are in no pool")
def pct(c, n): return f"{100*c/n:.0f}%"
print(f"questions {len(Q)}; problems: {len(problems)}"); [print("  ", p) for p in problems]
for name, ids in pools.items():
    n = len(ids); pos = collections.Counter(Q[i]["a"] for i in ids); th = collections.Counter(Q[i]["t"] for i in ids); df = collections.Counter(Q[i]["d"] for i in ids)
    print(f"{name:6} n={n:3}  answer A-E {[pos[k] for k in range(5)]}  topics " + " ".join(f"{k}:{pct(th[k],n)}" for k in "PSECD") + "  diff " + "/".join(pct(df[k], n) for k in (1, 2, 3)))
print("\nunit  weight  lesson-min  quizQ  allQ  Q-share  cards  card-share  diag  examA  examB")
nc = sum(len(u["cards"]) for u in U)
for u in U:
    a = sum(1 for q in Q.values() if q["u"] == u["n"])
    cnt = lambda ids: sum(1 for i in ids if Q[i]["u"] == u["n"])
    print(f"{u['n']:>4}  {u['weight']:>5}%  {u['minutes']:>10}  {len(u['quiz']):>5}  {a:>4}  {pct(a,len(Q)):>7}  {len(u['cards']):>5}  {pct(len(u['cards']),nc):>10}  {cnt(pools['diag']):>4}  {cnt(pools['examA']):>5}  {cnt(pools['examB']):>5}")
th = collections.Counter(q["t"] for q in Q.values()); df = collections.Counter(q["d"] for q in Q.values())
print("\nwhole bank topics: " + "  ".join(f"{D['themes'][k]['short']} {pct(th[k],len(Q))} (official {D['themes'][k]['weight']}%)" for k in "PSECD"))
print("whole bank difficulty easy/med/hard: " + "/".join(pct(df[k], len(Q)) for k in (1, 2, 3)) + "  (target 30/50/20)")
pre = sum(1 for q in Q.values() if q["u"] <= 5)
print(f"chronology 1500-1789: {pct(pre,len(Q))} (official 30%)")
sys.exit(1 if problems else 0)
