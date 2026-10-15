// End-to-end audit: drives the built HTML in headless Chromium.
// Run: NODE_PATH=<dir with playwright> node audit_ui.js [screenshotDir]
const { chromium } = require('playwright');
const path = require('path');
const FILE = 'file://' + path.resolve(__dirname, 'clep-us-history-1-study-guide.html');
const SHOTS = process.argv[2] || null;
const exe = process.env.CHROME || '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
let fails = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fails++; };
(async () => {
  const b = await chromium.launch({ executablePath: exe });
  const ctx = await b.newContext({ viewport: { width: 1200, height: 900 } });
  const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  p.on('dialog', d => d.accept());
  await p.goto(FILE + '#diag');

  // ---- Diagnostic: answer every question via keyboard, deliberately missing the first 5
  await p.click('#go');
  const diagIds = await p.evaluate(() => RUN.ids);
  for (let i = 0; i < diagIds.length; i++) {
    const shown = await p.evaluate(() => RUN.ids[RUN.i]);
    const q = await p.evaluate(id => ({ a: Q[id].a, n: Q[id].o.length, u: Q[id].u, t: Q[id].t, e: Q[id].e.filter(Boolean).length }), shown);
    if (q.n !== 5 || q.e !== 5 || !q.u || !q.t) ok(false, 'diag question malformed ' + shown);
    const key = i < 5 ? ((q.a + 1) % 5) + 1 : q.a + 1;   // wrong for first five
    await p.keyboard.press(String(key));
    await p.keyboard.press('Enter');
  }
  // Enter on last question triggers submit confirm (auto-accepted)
  const diag = await p.evaluate(() => S.diag);
  ok(diag && diag.t === 30, 'diagnostic recorded 30 questions');
  ok(diag && diag.c === 25 && diag.score === 83, `diagnostic score 25/30 = 83% (got ${diag && diag.c}/${diag && diag.t})`);
  ok(Object.keys(diag.byUnit).length === 12, 'diagnostic has results for all 12 units');
  ok(await p.locator('text=What to skim vs. study').count() === 1, 'skim/study table shown');
  ok(await p.evaluate(() => Object.keys(S.mis).length) === 5, 'five misses entered the mistake log');
  if (SHOTS) await p.screenshot({ path: SHOTS + '/diag-results.png', fullPage: false });

  // ---- Practice exam A: format, timer, no pause (resume after reload keeps clock), results by topic
  await p.goto(FILE + '#exam/1'); await p.reload();
  await p.click('#go');
  const ex = await p.evaluate(() => ({ n: RUN.ids.length, mins: (RUN.end - RUN.start) / 6e4, uniq: new Set(RUN.ids).size }));
  ok(ex.n === 120 && ex.uniq === 120, 'exam A has 120 unique questions');
  ok(ex.mins === 90, 'exam timer is 90 minutes');
  const overlap = await p.evaluate(() => { const quiz = new Set(U.flatMap(u => u.quiz)); const d = new Set(DATA.diag); const B = new Set(DATA.exams[1]);
    return DATA.exams[0].filter(id => quiz.has(id) || d.has(id) || B.has(id)).length + DATA.exams[1].filter(id => quiz.has(id) || d.has(id)).length; });
  ok(overlap === 0, 'exams share no questions with quizzes, diagnostic, or each other');
  // answer 60 correctly, then reload mid-exam
  for (let i = 0; i < 60; i++) { const a = await p.evaluate(() => Q[RUN.ids[RUN.i]].a); await p.keyboard.press(String(a + 1)); await p.keyboard.press('Enter'); }
  if (SHOTS) await p.screenshot({ path: SHOTS + '/exam.png' });
  const endBefore = await p.evaluate(() => S.run.end);
  await p.reload();
  const resumed = await p.evaluate(() => ({ i: RUN && RUN.i, answered: RUN && Object.keys(RUN.ans).length, end: RUN && RUN.end }));
  ok(resumed.answered === 60 && resumed.i === 60, 'exam resumes at question 61 with 60 answers after reload');
  ok(resumed.end === endBefore, 'timer end time unchanged by reload (no pausing)');
  ok(await p.locator('#timer').count() === 1, 'timer visible');
  // simulate the clock running out
  await p.evaluate(() => { S.run.end = Date.now() - 1000; save(); });
  await p.reload();
  const exA = await p.evaluate(() => S.exams[1]);
  ok(exA && exA.timeUp === true, 'exam auto-submitted when time expired');
  ok(exA && exA.c === 60 && exA.t === 120 && exA.score === 50, `exam A scored 60/120 = 50% (got ${exA && exA.c}/${exA && exA.t})`);
  ok(exA && Object.keys(exA.byTheme).length === 5, 'exam results broken down by all 5 official topics');
  ok(exA && Object.keys(exA.byUnit).length === 12, 'exam results broken down by all 12 units');
  ok(await p.evaluate(() => S.run) === null, 'no exam left in progress');
  ok(await p.locator('text=By topic (official categories)').count() === 1, 'topic breakdown rendered');
  if (SHOTS) await p.screenshot({ path: SHOTS + '/exam-results.png' });

  // ---- Readiness: not ready until both exams >= 75
  await p.goto(FILE + '#home');
  ok(await p.locator('text=Not ready yet').count() === 1, 'readiness meter says not ready after 50% exam');
  await p.evaluate(() => { S.exams[1] = Object.assign({}, S.exams[1], { score: 80 }); S.exams[2] = Object.assign({}, S.exams[1], { score: 76 }); save(); route(); });
  ok(await p.locator('text=✓ Ready to book').count() === 1, 'readiness says ready when both exams >= 75');
  await p.evaluate(() => { S.exams[2].score = 74; save(); route(); });
  ok(await p.locator('text=Not ready yet').count() === 1, 'one exam at 74% keeps it not ready');

  // ---- Mistake drill clears items answered correctly
  await p.goto(FILE + '#mistakes'); await p.reload();
  const before = await p.evaluate(() => Object.keys(S.mis).length);
  await p.click('#drill');
  const n = await p.evaluate(() => RUN.ids.length);
  for (let i = 0; i < n; i++) { const a = await p.evaluate(() => Q[RUN.ids[RUN.i]].a); await p.keyboard.press(String(a + 1)); await p.keyboard.press('Enter'); }
  const after = await p.evaluate(() => Object.keys(S.mis).length);
  ok(after === before - n, `mistake drill cleared ${n} items (${before} → ${after})`);

  // ---- Flashcards: Leitner boxes, missed-only mode
  await p.goto(FILE + '#unit/3/cards');
  await p.click('[data-m=due]');
  for (let i = 0; i < 4; i++) { await p.keyboard.press(' '); await p.keyboard.press(i % 2 ? '2' : '1'); }
  const cs = await p.evaluate(() => Object.values(S.cards).map(c => c.b));
  ok(cs.includes(1) && cs.includes(2), 'missed cards go to box 1, known cards to box 2');
  await p.goto(FILE + '#unit/3/cards'); await p.reload();
  ok(await p.locator('[data-m=miss]').isEnabled(), '"Review missed only" enabled after a miss');

  // ---- Study plan generator
  await p.goto(FILE + '#plan');
  await p.fill('#hpd', '2');
  const d = new Date(Date.now() + 14 * 864e5); const ds = d.toISOString().slice(0, 10);
  await p.fill('#edate', ds); await p.click('#mk');
  const plan = await p.evaluate(() => [...document.querySelectorAll('.plan-day')].map(x => x.innerText));
  ok(plan.length >= 3, `plan has ${plan.length} days`);
  ok(/EXAM DAY/.test(plan[plan.length - 1]), 'plan ends on exam day');
  ok(/Practice exam B/.test(plan[plan.length - 2]) && /Practice exam A/.test(plan[plan.length - 3]), 'practice exams scheduled 2 days and 1 day before');
  if (SHOTS) await p.screenshot({ path: SHOTS + '/plan.png' });

  // ---- Export / import round trip
  await p.goto(FILE + '#about');
  const [dl] = await Promise.all([p.waitForEvent('download'), p.click('#exp')]);
  const fp = await dl.path(); const exported = JSON.parse(require('fs').readFileSync(fp, 'utf8'));
  ok(exported.state && exported.state.diag && exported.state.exams[1], 'export contains progress');
  await p.evaluate(() => { localStorage.clear(); S = defState(); save(); });
  await p.setInputFiles('#imp', fp);
  await p.waitForTimeout(300);
  ok(await p.evaluate(() => !!(S.diag && S.exams[1])), 'import restores progress');

  // ---- Storage blocked: app still works
  const p2 = await ctx.newPage(); const errs2 = []; p2.on('pageerror', e => errs2.push(e.message));
  await p2.addInitScript(() => { Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } }); });
  await p2.goto(FILE + '#unit/1/quiz'); await p2.click('#go'); await p2.keyboard.press('1');
  ok(errs2.length === 0 && await p2.locator('.banner').count() === 1, 'works with storage blocked and shows a warning banner');

  // ---- Every unit lesson renders; dark mode; cheat sheet
  for (let u = 1; u <= 12; u++) { await p.goto(FILE + '#unit/' + u); if (!(await p.locator('.must li').count() >= 5 && await p.locator('.tl li').count() >= 10)) ok(false, 'unit ' + u + ' lesson incomplete'); }
  ok(true, 'all 12 lessons render must-know boxes and timelines');
  await p.goto(FILE + '#cheat');
  ok(await p.locator('.cheat .mt div').count() > 50, 'cheat sheet master timeline rendered');
  await p.evaluate(() => toggleTheme());
  if (SHOTS) { await p.goto(FILE + '#unit/10'); await p.screenshot({ path: SHOTS + '/dark-unit.png' }); }
  const p3 = await ctx.newPage(); await p3.setViewportSize({ width: 390, height: 844 });
  await p3.goto(FILE + '#home');
  ok(await p3.evaluate(() => document.documentElement.scrollWidth <= 390), 'no horizontal scroll at phone width');
  if (SHOTS) await p3.screenshot({ path: SHOTS + '/phone-home.png' });
  ok(errs.length === 0, 'no page errors' + (errs.length ? ': ' + errs.join(' | ') : ''));
  await b.close();
  console.log(fails ? `\n${fails} FAILED` : '\nALL UI CHECKS PASSED');
  process.exit(fails ? 1 : 0);
})();
