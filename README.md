# CLEP US History I — Study Guide

A single self-contained HTML study guide for the CLEP *History of the United States I: Early Colonization to 1877* exam.

**To study:** download [`clep-us-history-1-study-guide.html`](clep-us-history-1-study-guide.html) and open it in any browser. It works offline; progress saves in your browser (export/import JSON from the About panel).

## What's inside
- 12 units weighted by the official outline (1500–1789 = 30%, 1790–1877 = 70%), each with a lesson, a must-know box, a timeline, a quiz, and flashcards
- 30-question diagnostic with skim / study / must-study labels per unit
- Two timed 120-question, 90-minute practice exams (no pausing; results by unit and official topic)
- Leitner spaced-repetition flashcards (237), mistake log, readiness meter, study-plan generator
- One-page printable cheat sheet with a recall mode
- 416 original questions; the quiz, diagnostic, Exam A and Exam B pools do not overlap

## Repository layout
| Path | Purpose |
|---|---|
| `outline.json` | Official format, topic and chronological weights, unit plan, sources |
| `src/units/uNN.txt` | Lesson, must-know, timeline, flashcards, and quiz questions per unit |
| `src/bank/uNN.txt` | Diagnostic and practice-exam questions per unit |
| `src/cheat.html` | Cheat sheet content |
| `src/template.html` | App shell (CSS + JS) |
| `build.py` | Assembles everything into the single HTML file |
| `audit_data.py` | Static checks: one correct answer, explanations, tags, pool overlap, balance |
| `audit_ui.js` | Browser end-to-end run of the diagnostic, an exam, and other features (Playwright) |
| `factcheck.py` | Flags answers whose key terms don't appear in the lesson material |

## Rebuild and audit
```sh
python3 build.py
python3 audit_data.py
NODE_PATH=/path/to/node_modules node audit_ui.js   # needs playwright + Chromium
```

Exam figures come from the College Board's exam page (https://clep.collegeboard.org/exam/history-us-i); items the guide could not verify are marked "unverified" in the app.
