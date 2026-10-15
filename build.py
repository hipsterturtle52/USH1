#!/usr/bin/env python3
"""Assemble the single-file study guide.

Sources:
  outline.json        official format/weights + unit plan
  src/units/uNN.txt   lesson, must-know, timeline, flashcards, unit quiz questions
  src/bank/uNN.txt    extra questions for the diagnostic and the two practice exams
  src/cheat.html      hand-written cheat sheet sections (master timeline is generated)
  src/template.html   app shell

Output: clep-us-history-1-study-guide.html
"""
import html, json, random, re, sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "clep-us-history-1-study-guide.html"
EXAM_Q = 120
# per-unit quotas: (diagnostic, per-exam). Quiz size = however many questions the unit file has.
QUOTA = {1: (2, 6), 2: (2, 7), 3: (2, 8), 4: (2, 9), 5: (1, 6), 6: (3, 13), 7: (2, 10),
         8: (3, 10), 9: (3, 12), 10: (4, 14), 11: (3, 13), 12: (3, 12)}
HOURS = {"diag": 0.6, "unitsTotal": 17, "exam": 2.75, "final": 2}
THEMES = {
    "P": ("Political institutions, political developments & public policy", "Political"),
    "S": ("Social developments", "Social"),
    "E": ("Economic developments", "Economic"),
    "C": ("Cultural & intellectual developments", "Cultural"),
    "D": ("Diplomacy & transnational interactions", "Diplomacy"),
}

errors = []


def err(msg):
    errors.append(msg)


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = s.replace("--", "—")
    return s


def lesson_html(lines):
    out, para, lst = [], [], []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()
        if lst:
            out.append("<ul>" + "".join("<li>" + inline(x) + "</li>" for x in lst) + "</ul>")
            lst.clear()

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush()
        elif line.startswith("## "):
            flush(); out.append("<h2>" + inline(line[3:]) + "</h2>")
        elif line.startswith("=> "):
            flush()
            parts = [p.strip() for p in line[3:].split("|")]
            if len(parts) != 3:
                err(f"chain needs 3 parts: {line}")
                continue
            c, e, r = (inline(p) for p in parts)
            out.append(f'<div class="chain"><div><b>Cause</b>{c}</div><span>→</span><div class="ev"><b>Event</b>{e}</div><span>→</span><div><b>Consequence</b>{r}</div></div>')
        elif line.startswith("!! "):
            flush(); out.append('<div class="tip"><b>Exam tip:</b> ' + inline(line[3:]) + "</div>")
        elif line.startswith("- "):
            if para:
                out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
            lst.append(line[2:])
        else:
            if lst:
                flush()
            para.append(line.strip())
    flush()
    return "\n".join(out)


def parse_questions(lines, unit, prefix, src):
    qs, cur = [], None
    for raw in lines + [""]:
        line = raw.rstrip()
        if not line.strip():
            if cur:
                qs.append(cur); cur = None
            continue
        if line.startswith("Q "):
            if cur:
                qs.append(cur)
            m = re.match(r"Q ([PSECD])([123]) (.*)", line)
            if not m:
                err(f"{src}: bad Q line: {line}")
                cur = None
                continue
            cur = {"u": unit, "t": m.group(1), "d": int(m.group(2)), "q": [m.group(3)], "pas": [], "tab": [], "right": None, "wrong": [], "src": src}
        elif cur is None:
            err(f"{src}: stray line: {line}")
        elif line.startswith("+ ") or line.startswith("- "):
            if "||" not in line:
                err(f"{src}: option without note: {line}")
                continue
            o, n = (x.strip() for x in line[2:].split("||", 1))
            if line[0] == "+":
                if cur["right"]:
                    err(f"{src}: two correct options in: {cur['q'][0][:60]}")
                cur["right"] = (o, n)
            else:
                cur["wrong"].append((o, n))
        elif line.startswith("> "):
            cur["pas"].append(line[2:])
        elif line.startswith("T "):
            cur["tab"].append([c.strip() for c in line[2:].split("|")])
        else:
            cur["q"].append(line.strip())
    out = []
    for i, c in enumerate(qs, 1):
        qid = f"{prefix}{unit}-{i}"
        head = c["q"][0][:70]
        if not c["right"]:
            err(f"{src}: no correct option: {head}")
            continue
        if len(c["wrong"]) != 4:
            err(f"{src}: needs 4 wrong options (has {len(c['wrong'])}): {head}")
            continue
        texts = [c["right"][0]] + [w[0] for w in c["wrong"]]
        if len(set(t.lower() for t in texts)) != 5:
            err(f"{src}: duplicate options: {head}")
        if any(re.search(r"\ball of the above\b|\bnone of the above\b", t, re.I) for t in texts):
            err(f"{src}: 'all/none of the above' not allowed: {head}")
        if any(not n for n in [c["right"][1]] + [w[1] for w in c["wrong"]]):
            err(f"{src}: empty explanation: {head}")
        qh = inline(" ".join(c["q"]))
        if c["pas"]:
            qh += "<blockquote>" + "<br>".join(inline(p) for p in c["pas"]) + "</blockquote>"
        if c["tab"]:
            rows = c["tab"]
            t = "<table><tr>" + "".join(f"<th>{inline(x)}</th>" for x in rows[0]) + "</tr>"
            t += "".join("<tr>" + "".join(f"<td>{inline(x)}</td>" for x in r) + "</tr>" for r in rows[1:]) + "</table>"
            qh += t
        out.append({"id": qid, "u": unit, "t": c["t"], "d": c["d"], "q": qh,
                    "right": (inline(c["right"][0]), inline(c["right"][1])),
                    "wrong": [(inline(o), inline(n)) for o, n in c["wrong"]]})
    return out


def parse_unit(path):
    sec, d = None, {"lesson": [], "must": [], "timeline": [], "cards": [], "quiz": []}
    meta = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"@(\w+)\s*(.*)$", line)
        if m and m.group(1) in ("unit", "title", "short", "years", "weight"):
            meta[m.group(1)] = m.group(2).strip()
            continue
        if m and m.group(1) == "end":
            sec = None
            continue
        if m and m.group(1) in d and not m.group(2):
            sec = m.group(1)
            continue
        if sec:
            d[sec].append(line)
    n = int(meta["unit"])
    words = len(re.findall(r"\w+", " ".join(d["lesson"] + d["must"] + d["timeline"])))
    must = [inline(l[2:]) for l in d["must"] if l.startswith("- ")]
    tl = []
    for l in d["timeline"]:
        if not l.strip():
            continue
        key = l.startswith("*")
        parts = [p.strip() for p in l.lstrip("*").split("|")]
        if len(parts) != 3 or parts[2] not in THEMES:
            err(f"{path.name}: bad timeline line: {l}")
            continue
        tl.append({"y": parts[0], "e": inline(parts[1]), "th": parts[2], "key": key})
    cards = []
    for i, l in enumerate([l for l in d["cards"] if "::" in l], 1):
        f, b = (x.strip() for x in l.split("::", 1))
        cards.append({"id": f"c{n}-{i}", "u": n, "f": inline(f), "b": inline(b)})
    quiz = parse_questions(d["quiz"], n, "q", path.name)
    return {"n": n, "title": meta["title"], "short": meta.get("short", meta["title"]), "years": meta["years"],
            "weight": int(meta["weight"]), "lesson": lesson_html(d["lesson"]), "words": words,
            "minutes": max(1, round(words / 150)), "must": must, "timeline": tl, "cards": cards}, quiz


def balanced_positions(n, rng):
    pos = [i % 5 for i in range(n)]
    rng.shuffle(pos)
    return pos


def place(q, p, rng):
    wrong = q["wrong"][:]
    rng.shuffle(wrong)
    opts = wrong[:p] + [q["right"]] + wrong[p:]
    return {"id": q["id"], "u": q["u"], "t": q["t"], "d": q["d"], "q": q["q"],
            "o": [o for o, _ in opts], "e": [n for _, n in opts], "a": p}


def assign_bank(qs, nd, ne, rng):
    """Split a unit's bank into diag / examA / examB, stratified by difficulty."""
    need = nd + 2 * ne
    if len(qs) != need:
        err(f"bank unit {qs[0]['u'] if qs else '?'}: has {len(qs)} questions, needs {need}")
    qs = sorted(qs, key=lambda q: (q["d"], rng.random()))
    pools = {"diag": [], "A": [], "B": []}
    cap = {"diag": nd, "A": ne, "B": ne}
    # deal round-robin within difficulty-sorted order so each pool gets a similar mix
    order = []
    while len(order) < len(qs):
        for k in ("A", "B", "diag"):
            order.append(k)
    i = 0
    for q in qs:
        for _ in range(3):
            k = order[i % len(order)]; i += 1
            if len(pools[k]) < cap[k]:
                pools[k].append(q); break
        else:
            for k in pools:
                if len(pools[k]) < cap[k]:
                    pools[k].append(q); break
    return pools


DIFF_TARGET = {1: 0.30, 2: 0.50, 3: 0.20}


def optimize_pools(banks, outline, rng):
    """Swap same-unit questions between diag/A/B so each pool's topic and difficulty mix
    approaches the official topic weights and the 30/50/20 difficulty target."""
    tw = {t["id"]: t["weight"] / 100 for t in outline["topical"]}
    pools = {k: [q for u in sorted(banks) for q in banks[u][k]] for k in ("diag", "A", "B")}

    def cost(pool):
        n = len(pool)
        if not n:
            return 0
        c = 0.0
        for t, w in tw.items():
            c += (sum(q["t"] == t for q in pool) / n - w) ** 2
        for d, w in DIFF_TARGET.items():
            c += (sum(q["d"] == d for q in pool) / n - w) ** 2
        return c * n

    names = list(pools)
    total = sum(cost(pools[k]) for k in names)
    for _ in range(40000):
        a, b = rng.sample(names, 2)
        i = rng.randrange(len(pools[a]))
        u = pools[a][i]["u"]
        cand = [j for j, q in enumerate(pools[b]) if q["u"] == u]
        if not cand:
            continue
        j = rng.choice(cand)
        before = cost(pools[a]) + cost(pools[b])
        pools[a][i], pools[b][j] = pools[b][j], pools[a][i]
        after = cost(pools[a]) + cost(pools[b])
        if after <= before:
            total += after - before
        else:
            pools[a][i], pools[b][j] = pools[b][j], pools[a][i]
    return pools


def master_timeline(units):
    items = [(t["y"], t["e"], t["th"]) for u in units for t in u["timeline"] if t["key"]]
    def yk(y):
        m = re.search(r"\d{4}", y)
        return int(m.group()) if m else 0
    items.sort(key=lambda x: yk(x[0]))
    return '<div class="mt">' + "".join(f'<div><b class="hidev">{html.escape(y)}</b> {e}</div>' for y, e, _ in items) + "</div>"


def main():
    outline = json.loads((ROOT / "outline.json").read_text())
    rng = random.Random(1877)
    units, Q, diag, exA, exB = [], {}, [], [], []
    unit_files = sorted((ROOT / "src/units").glob("u*.txt"))
    cycle = 0
    banks = {}
    for f in unit_files:
        u, quiz = parse_unit(f)
        pos = [(cycle + i) % 5 for i in range(len(quiz))]
        cycle += len(quiz)
        rng.shuffle(pos)
        u["quiz"] = []
        for q, p in zip(quiz, pos):
            Q[q["id"]] = place(q, p, rng); u["quiz"].append(q["id"])
        units.append(u)
        bf = ROOT / "src/bank" / f.name
        if bf.exists():
            bank = parse_questions([l for l in bf.read_text(encoding="utf-8").splitlines() if not l.startswith("@end")], u["n"], "b", bf.name)
            nd, ne = QUOTA[u["n"]]
            banks[u["n"]] = assign_bank(bank, nd, ne, rng)
    for k, v in optimize_pools(banks, outline, rng).items():
        dest = {"diag": diag, "A": exA, "B": exB}[k]
        for q in v:
            Q[q["id"]] = place(q, 0, rng); dest.append(q["id"])
    # rebalance answer positions within each full exam / diagnostic (they mix units)
    for pool in (diag, exA, exB):
        pp = balanced_positions(len(pool), rng)
        for qid, p in zip(pool, pp):
            q = Q[qid]
            right = (q["o"][q["a"]], q["e"][q["a"]])
            wrong = [(o, e) for k, (o, e) in enumerate(zip(q["o"], q["e"])) if k != q["a"]]
            opts = wrong[:p] + [right] + wrong[p:]
            q["o"], q["e"], q["a"] = [o for o, _ in opts], [e for _, e in opts], p
    tops = {t["id"]: t for t in outline["topical"]}
    themes = {k: {"name": v[0], "short": v[1], "weight": tops[k]["weight"], "status": tops[k]["status"]} for k, v in THEMES.items()}
    cheat_src = ROOT / "src/cheat.html"
    cheat = cheat_src.read_text(encoding="utf-8") if cheat_src.exists() else "<p>Cheat sheet coming soon.</p>"
    cheat = cheat.replace("<!--MASTER_TIMELINE-->", master_timeline(units))
    meta = {
        "exam": outline["exam"],
        "format": {"questions": outline["format"]["questions"]["value"], "minutes": outline["format"]["time_minutes"]["value"],
                   "qStatus": outline["format"]["questions"]["status"], "tStatus": outline["format"]["time_minutes"]["status"],
                   "sStatus": outline["format"]["credit_granting_score"]["status"]},
        "chronological": outline["chronological"], "sources": outline["sources"], "note": outline["verification_note"],
        "hours": dict(HOURS, total=round(HOURS["diag"] + HOURS["unitsTotal"] + 2 * HOURS["exam"] + HOURS["final"])),
    }
    data = {"meta": meta, "themes": themes, "units": units, "Q": Q, "diag": diag, "exams": [exA, exB], "cheat": cheat}
    if len(list((ROOT / "src/bank").glob("u*.txt"))) == 12 and len(exA) != EXAM_Q:
        err(f"exam A has {len(exA)} questions, expected {EXAM_Q}")
    if errors:
        print("\n".join("ERROR: " + e for e in errors)); sys.exit(1)
    js = "const DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"
    tpl = (ROOT / "src/template.html").read_text(encoding="utf-8")
    OUT.write_text(tpl.replace("/*__DATA__*/", js), encoding="utf-8")
    nq = len(Q)
    print(f"built {OUT.name}: {len(units)} units, {nq} questions (diag {len(diag)}, A {len(exA)}, B {len(exB)}), "
          f"{sum(len(u['cards']) for u in units)} cards, {OUT.stat().st_size/1024:.0f} KB")
    for u in units:
        print(f"  U{u['n']:>2} {u['weight']:>2}%  words {u['words']:>5} (~{u['minutes']} min)  must {len(u['must'])}  tl {len(u['timeline'])}  cards {len(u['cards'])}  quiz {len(u['quiz'])}")


if __name__ == "__main__":
    main()
