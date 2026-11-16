const STEPS = [
  {
    title: "What is rated",
    body: `<p>The source files are not edited. Cleaning writes a silver copy. Ratings read that copy and score legal balls only. A legal ball is not a wide, a no-ball, or an other-type extra. An other-type extra is re-bowled like a no-ball; counting it as legal would push 150 innings past 120 legal balls. Innings 3 and 4 are super overs and are kept: every super-over ball is a death ball, and the second super over chases the first one's total plus one. About 192,445 legal balls remain from 200,999 deliveries, 33 of them in super overs.</p>
    <p>A bowler wicket is caught, bowled, LBW, stumped, or hit wicket. A run-out dismisses the batter and does not credit the bowler. Every extra now carries its run amount, so team totals include wides, no-balls, byes, and leg-byes. A bowler is charged the bat runs, every run off a wide, and the one run of a no-ball. <span class="formula">charged runs = 0</span> on a bye, leg-bye, or penalty, and byes run off a no-ball are not charged either.</p>`,
  },
  {
    title: "Phase, chase, and ladders",
    body: `<p>Balls are ordered inside the innings. The phase cut uses the legal-ball number and the innings allowance, 120 unless the match was shortened.</p>
    <p class="formula">powerplay ends at round(0.30 × allowance) &nbsp; death starts after round(0.80 × allowance)</p>
    <p>An ordinary chase target is the first-innings total plus 1. A revised target is used as supplied. If the match was shortened and no revised target is present, no required rate is invented. The required rate is runs still needed divided by overs still left.</p>
    <p>Three ladders, each starting at 1500. IPL is one. T20I is the second. Emerging Teams and Rising Stars are the third, a lower level than T20I. A rating learned on the lower ladder does not carry into a T20I. Expected runs are fit inside the ladder, so a lower-T20 score is judged against other lower-T20 bowling. A lower-T20 ball counts as half a ball in the career rates and in the ranking floor.</p>`,
  },
  {
    title: "Pressure, which only chooses the band",
    body: `<p>Pressure is not an eighth weight in the ranking. It decides whether a ball is zero, medium, or high.</p>
    <p class="formula">pressure = occasion × competition × ball difficulty + shock + run of play</p>
    <p>Occasion is 3 for a final, 2 for a semi-final, 1.5 for a qualifier or eliminator, 1.3 for Super 4, 1 for a league match, 0.8 for other bilateral matches, and 0.4 once a bilateral series is already won. A super over counts as a knockout: it is never below 1.5, and a semi-final or final super over keeps 2 or 3. Competition is 0.7 for Other T20 and for events whose name contains Emerging or Rising, otherwise 1.</p>
    <p>Ball difficulty is capped from 0 to 1. For a batter the phase term is 0.25, 0.10, and 0.40 for powerplay, middle, and death. Wickets already down add 0, 0.15, or 0.30. A required rate of at least 8 adds 0.15, and at least 12 adds 0.30. For a bowler the phase term is 0.32, 0.24, and 0.32 at the death against a batter listed 1 to 7, otherwise 0.14 at the death. Wickets down subtract 0, 0.10, or 0.25. The current ball is never included in the shock or the run of play.</p>`,
  },
  {
    title: "Shock and the run of play",
    body: `<p>The count uses the previous six legal balls. A batter dot is 0.05 and a wicket is 0.33, capped at 1. A wicket is not also a dot. A bowler four is 0.12 and a six is 0.33, capped at 1. Three wickets or three sixes reach 1.</p>
    <p>After the Elo walk, the same six balls add wickets minus the expected wicket chance for the batter, and charged runs minus the expected charged runs for the bowler. Each excess is divided by its usual size and capped from −0.5 to 1. The count and the excess are added and capped again.</p>
    <p>Once 18 legal balls exist, the run of play is the rate in the last 6 minus the rate in the last 18. Wickets per ball for a batter, runs per ball for a bowler. That gap is divided by its usual size and capped from −0.5 to 1.</p>`,
  },
  {
    title: "Who is in the high band",
    body: `<p>For batters, high is the top fifth of batter pressure, at or above the 80th percentile. Medium is from the 50th percentile up to that cut. The rest is zero. This cut is not split by batting role.</p>
    <p>For bowlers the same two percentiles are taken inside pace and again inside spin, so each arm has its own top fifth. That stops the powerplay, which pace bowls, from filling the high band with pace.</p>`,
  },
  {
    title: "What a ball was worth",
    body: `<p>Expected runs and the expected wicket chance use only balls already bowled. The cell is phase, pace or spin, and ladder, shrunk toward the coarser cell with 30 balls. Before any ball, the starting assumption is 1.0 run and a 0.05 wicket chance. Batters are priced on bat runs. Bowlers are priced on charged runs.</p>
    <p class="formula">gap = 0.15(batter − bowler)/400 + 0.05(batting side − bowling side)/400 + 0.10(ground − 1500)/400</p>
    <p class="formula">x runs = cell mean × exp(gap), capped from 0 to 6</p>
    <p>The ratings used in the gap are pulled toward 1500 until the player has 30 legal balls on that ladder. The ground rating uses only balls already bowled there, shrunk with 2,400 balls. A new player and a new ground start at 1500.</p>
    <p class="formula">batter ball value = (bat runs − x runs) − 4(striker out − x wicket)</p>
    <p class="formula">bowler ball value = (x charged runs − charged runs) + 4(bowler wicket − x wicket)</p>
    <p>The bowler’s rating moves with charged runs, the same quantity as the bowler ball value. The step sizes are 4 for a run, 16 for a wicket, and 20 for a team result. If the ratings spread past the allowed edges, those steps are halved once and the walk is repeated.</p>`,
  },
  {
    title: "The seven scores",
    body: `<p>A season weight is 0.9 to the power of how many years it sits before 2026. A career rate is the decay-weighted mean of the rows the player actually has. A season with no rows is left out. It is not written as zero, and it is not divided by 4.0951.</p>
    <p>Every published component is then a z-score: value minus the reference mean, divided by the reference population spread, capped at −3 and 3. For batters that reference is other players in the same role with at least 30 decay-weighted legal balls. Top order is batting positions 1 to 3, middle is 4 to 6, and lower is 7 and below. For bowlers the reference is all bowlers with at least 30 decay-weighted legal balls.</p>
    <p>Baseline is half the z-score of the phase-adjusted strike rate and half the phase-adjusted average for a batter. For a bowler it is half the economy gap and half the balls-per-wicket gap, with the sign flipped so lower is better. Strike rate and economy shrink toward the phase expectation with 120 balls. Average and balls per wicket shrink with 4 dismissals or wickets.</p>
    <p>Each band score is the ball value inside that band, as a decay-weighted mean, shrunk toward 0 with 30 balls. Peers compare an innings of at least 6 balls with teammates and with the other side. Both z-scores are capped at 3. Clutch does that only in the high band, and a spell below the player’s own rate stays negative. Consistency prefers a narrower spread of match values, shrunk toward the typical spread with 8 matches.</p>`,
  },
  {
    title: "The rank",
    body: `<p class="formula">composite = 0.20 baseline + 0.10 zero + 0.15 medium + 0.20 high + 0.15 clutch + 0.10 peers + 0.10 consistency</p>
    <p>The seven weights sum to 1. A player is ranked with at least 120 decay-weighted legal balls and at least 30 of those in the high band. Rank 1 is the highest composite. A tie goes to the smaller player id.</p>
    <p>Open a player from the rankings to see each weight times each z-score, the rank of that component, and the innings and balls underneath it.</p>`,
  },
];

const COLUMNS = {
  batters: [
    ["rank", "Rank"],
    ["player_name", "Player"],
    ["role", "Role"],
    ["composite", "Composite"],
    ["baseline", "Baseline"],
    ["band_high", "High"],
    ["clutch", "Clutch"],
    ["peers", "Peers"],
    ["consistency", "Consistency"],
    ["runs", "Runs"],
    ["strike_rate", "Strike rate"],
    ["n_eff", "Weighted balls"],
    ["high_n_eff", "High balls"],
  ],
  bowlers: [
    ["rank", "Rank"],
    ["player_name", "Player"],
    ["role", "Role"],
    ["composite", "Composite"],
    ["baseline", "Baseline"],
    ["band_high", "High"],
    ["clutch", "Clutch"],
    ["peers", "Peers"],
    ["consistency", "Consistency"],
    ["wickets", "Wickets"],
    ["economy", "Economy"],
    ["n_eff", "Weighted balls"],
    ["high_n_eff", "High balls"],
  ],
};

const PIECES = [
  ["baseline", "Baseline", 0.20],
  ["band_zero", "Quiet balls", 0.10],
  ["band_medium", "The squeeze", 0.15],
  ["band_high", "High pressure", 0.20],
  ["clutch", "Clutch", 0.15],
  ["peers", "Same innings", 0.10],
  ["consistency", "Consistency", 0.10],
];

const state = {
  view: "board",
  skill: "batters",
  q: "",
  role: "",
  ranked: "1",
  sort: "rank",
  dir: "asc",
  playerId: null,
  ballOffset: 0,
  ballPhase: "",
  ballBand: "",
  weights: Object.fromEntries(PIECES.map(([key, , weight]) => [key, weight])),
  used: Object.fromEntries(PIECES.map(([key]) => [key, true])),
  pool: null,
  portraits: null,
  pageSkill: null,
  pageId: null,
  pageMatch: null,
  pageInnings: null,
};

const app = document.querySelector("#app");

function num(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function cls(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "";
  return Number(value) >= 0 ? "positive" : "negative";
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function setView(view) {
  state.view = view;
  document.querySelectorAll(".nav button").forEach((button) => button.classList.remove("active"));
  const tab = view === "player" ? (state.skill === "bowlers" ? "bowlers" : "batters") : view === "rankings" ? (state.skill === "bowlers" ? "bowlers" : "batters") : "board";
  const node = document.querySelector(`#tab-${tab}`);
  if (node) node.classList.add("active");
  render();
}

function round1(value) {
  return Math.round(value);
}

function story(player, skill, phases) {
  const highBalls = round1(player.high_n_eff);
  const lines = [];
  if (skill === "batters") {
    lines.push(`${player.role[0].toUpperCase()}${player.role.slice(1)}. ${round1(player.runs)} runs at a strike rate of ${round1(player.strike_rate)}, average ${num(player.average, 1)}, from ${round1(player.legal_balls)} balls. About ${highBalls} of those balls were the tight ones: the death, a steep required rate, or a final.`);
  } else {
    lines.push(`${player.role}. ${round1(player.wickets)} wickets at ${num(player.economy, 2)} an over, a wicket every ${num(player.balls_per_wicket, 1)} balls, from ${round1(player.legal_balls)} legal balls. About ${highBalls} of those were bowled when the batter was trying to break the game.`);
  }
  const ranked = PIECES
    .map(([key, label, weight]) => ({ key, label, score: weight * Number(player[key] || 0) }))
    .sort((a, b) => b.score - a.score);
  const lead = ranked[0];
  const share = player.stood_out_share;
  const stood = share == null || Number.isNaN(Number(share)) ? "" : ` About ${round1(Number(share) * 100)} in 100 of his longer spells stood clear of the others in the innings and ahead of his own usual rate.`;
  const leadLine = {
    baseline: skill === "batters"
      ? "The rank starts from the everyday innings. Once the mix of powerplay, middle and death is allowed for, that strike rate and average sit with the best of his batting group."
      : "The rank starts from the ordinary spell. For his pace or spin, he goes for fewer than the over usually costs and breaks the stand sooner.",
    band_high: skill === "batters"
      ? "What lifts him is the tight ball. When the death arrives or the chase steepens, he takes more off the delivery than that situation usually gives up."
      : "What lifts him is the tight over. When the batter is looking to finish it, he still keeps the runs down or takes the wicket.",
    band_medium: skill === "batters"
      ? "He does his work as the squeeze starts, in the overs where the rate is climbing but the game is not yet gone."
      : "He does his work as the squeeze starts, before the last two overs, when the batter is just beginning to look for the boundary.",
    band_zero: skill === "batters"
      ? "Even in the quiet passages, with wickets in hand and no steep ask, he scores more than the field is offering."
      : "Even in the quiet passages he keeps the over tidy and does not wait for the death to take a wicket.",
    clutch: skill === "batters"
      ? "In those high-pressure spells he also beats the rate he scores at in ordinary cricket, and he outscores the partner at the other end."
      : "In those finishing spells he is harder to get after than his own usual economy, and harder than the other bowlers in the same attack.",
    peers: skill === "batters"
      ? `In the same innings he pulls away from his own side and stands up to the other batting side.${stood}`
      : `In the same innings his spell is the one that stands out in the attack.${stood}`,
    consistency: "From match to match the return does not swing from a blitz to a trudge.",
  };
  lines.push(leadLine[lead.key]);
  const drag = [...ranked].reverse().find((part) => part.score < -0.02);
  if (drag && drag.key !== lead.key) lines.push(leadLine[drag.key]);
  const death = (phases || []).find((phase) => phase.phase === "death");
  if (death && death.balls >= 12) {
    if (skill === "batters") {
      lines.push(`In the death itself he has ${round1(death.runs)} runs from ${round1(death.balls)} balls, a strike rate of ${round1(100 * death.runs / death.balls)}.`);
    } else {
      lines.push(`In the death he goes at ${num(6 * death.runs / death.balls, 1)} an over across ${round1(death.balls)} balls.`);
    }
  }
  return lines.filter(Boolean);
}

function experimentScore(player) {
  return PIECES.reduce((total, [key]) => total + (state.used[key] ? state.weights[key] * Number(player[key] || 0) : 0), 0);
}

function experimentOrder(rows) {
  return rows
    .map((row) => ({ ...row, trial: experimentScore(row) }))
    .sort((a, b) => b.trial - a.trial || a.player_id - b.player_id);
}

function formulaText() {
  const terms = PIECES.filter(([key]) => state.used[key]).map(([key, label]) => `${state.weights[key].toFixed(2)} ${label}`);
  if (!terms.length) return "No piece is selected.";
  return terms.join(" + ");
}

async function loadPool() {
  if (state.pool) return state.pool;
  const [batters, bowlers] = await Promise.all([
    getJson("/api/batters?ranked=1&sort=rank&dir=asc"),
    getJson("/api/bowlers?ranked=1&sort=rank&dir=asc"),
  ]);
  state.pool = { batters: batters.rows, bowlers: bowlers.rows };
  return state.pool;
}

function miniList(title, rows) {
  const top = experimentOrder(rows).slice(0, 10);
  return `<div class="mini-rank"><h3>${title}</h3><ol>${top.map((row, index) => `<li><span>${String(index + 1).padStart(2, "0")}</span><span>${row.player_name}</span><b>${num(row.trial, 3)}</b><span>was ${row.rank}</span></li>`).join("")}</ol></div>`;
}

function officialList(title, rows, skill) {
  const top = rows.slice(0, 10);
  return `<section class="rank-card"><h3>${title}</h3><ol>${top.map((row) => `<li class="pick" tabindex="0" data-skill="${skill}" data-id="${row.player_id}"><div class="pick-line"><span>${String(row.rank).padStart(2, "0")}</span><span>${row.player_name}</span><b>${num(row.composite, 3)}</b></div></li>`).join("")}</ol><button class="ghost more" type="button" data-open="${skill}">Full ${skill === "batters" ? "batter" : "bowler"} list</button></section>`;
}

function portrait(row, skill, phases) {
  const lines = story(row, skill, phases);
  const chips = skill === "batters"
    ? [`${round1(row.strike_rate)} strike rate`, `average ${num(row.average, 1)}`, `${round1(row.high_n_eff)} tight balls`, row.role]
    : [`${num(row.economy, 2)} economy`, `wicket every ${num(row.balls_per_wicket, 1)}`, `${round1(row.wickets)} wickets`, row.role];
  return `<article class="portrait"><div class="num">${String(row.rank).padStart(2, "0")}</div><div><h3>${row.player_name}</h3><p class="meta">${skill === "batters" ? "Batter" : "Bowler"} · published score ${num(row.composite, 3)}</p>${lines.map((line) => `<p>${line}</p>`).join("")}<div class="chips">${chips.map((chip) => `<span>${chip}</span>`).join("")}</div></div></article>`;
}

const METRICS = {
  baseline: {
    short: "Plain skill, before pressure is considered.",
    batter: "Strike rate and average, each set against what his mix of powerplay, middle, and death overs usually yields. Half of each.",
    bowler: "Economy and balls per wicket, each set against what that phase and pace or spin usually concede. Half of each, lower is better.",
    detail: "Rates are pulled toward the expectation until there are 120 balls, or 4 dismissals for the average.",
  },
  band_zero: {
    short: "Value added on the quiet half of balls.",
    batter: "Runs above expectation, less the cost of getting out, when nothing much is riding on the ball.",
    bowler: "Runs saved and wickets above expectation in the same easy situations.",
    detail: "Bottom 50 percent of pressure. Pulled toward 0 until 30 balls.",
  },
  band_medium: {
    short: "Value added when the game starts to tighten.",
    batter: "The same ball value, on balls where the asking rate or the wickets begin to bite.",
    bowler: "The same ball value, when the batting side has started to chase the game.",
    detail: "The 50th to 80th percentile of pressure. Pulled toward 0 until 30 balls.",
  },
  band_high: {
    short: "Value added in the tightest fifth of balls.",
    batter: "Death overs, a steep chase, wickets down, a knockout: does he still beat what the ball usually gives?",
    bowler: "The same squeeze from the other end. The cut is made inside pace and inside spin separately.",
    detail: "Top 20 percent of pressure. Pulled toward 0 until 30 balls.",
  },
  clutch: {
    short: "Stood up when teammates did not.",
    batter: "In a high-pressure spell of 6 balls or more, did he beat his own usual rate while the rest of the order fell short?",
    bowler: "In a high-pressure spell, did he hold up while the other bowlers went for runs?",
    detail: "A spell worse than his own rate counts against him. Beating it counts more when teammates struggled more.",
  },
  peers: {
    short: "Better than everyone else in the same match.",
    batter: "Each innings of 6 balls or more set against teammates and the opposition batters on the same pitch, same day.",
    bowler: "Each spell set against teammates and the opposition bowlers in the same game.",
    detail: "Both comparisons capped at 3 z. Pulled toward 0 until 5 innings.",
  },
  consistency: {
    short: "Reliable rather than all-or-nothing.",
    batter: "A narrower spread of match-by-match value scores higher than big swings between huge and nothing.",
    bowler: "The same spread, for match-by-match bowling value.",
    detail: "Spread is pulled toward the usual spread until 8 matches.",
  },
};

function metricsGuide() {
  const terms = PIECES.map(([, label, weight]) => `${weight.toFixed(2)} × ${label}`).join(" + ");
  const cards = PIECES.map(([key, label, weight]) => {
    const item = METRICS[key];
    return `<article class="metric-card">
      <header><h3>${label}</h3><span class="metric-weight">${weight.toFixed(2)}</span></header>
      <p class="metric-short">${item.short}</p>
      <p><b>Batter</b> ${item.batter}</p>
      <p><b>Bowler</b> ${item.bowler}</p>
      <p class="metric-detail">${item.detail}</p>
    </article>`;
  }).join("");
  return `<section class="metrics">
    <div class="metrics-head">
      <div>
        <h2>What the score measures</h2>
        <p>Every legal ball gets a value: what the batter or bowler did against what that ball usually yields. Each ball also gets a pressure score, which decides whether it is a quiet ball, a squeeze, or high pressure. Seven measures are built from those values. Each is turned into a z-score against comparable players, capped at 3 either way, and the published score is their weighted sum.</p>
      </div>
      <div class="formula-block metrics-formula"><p>The published score</p><code>score = ${terms}</code><small>Weights sum to 1.00. Each measure is a z-score: 0 is an ordinary player, +1 is one spread above.</small></div>
    </div>
    <div class="metric-grid">${cards}<article class="metric-card metric-read">
      <header><h3>Reading a score</h3></header>
      <p class="metric-short">0 is an ordinary player in the comparison group.</p>
      <p>Each measure sits between −3 and +3. A +1 means one spread better than the group, roughly the top sixth.</p>
      <p>Because the weights sum to 1, the published score reads on the same scale. A score near +1 across the board is a very good T20 cricketer.</p>
      <p class="metric-detail">Hover a name in the top 10 to see his seven bars.</p>
    </article></div>
    <div class="metric-basis">
      <div><h4>Ball value</h4><code>batter = (bat runs − expected runs) − 4 × (out − expected wicket chance)</code><code>bowler = (expected runs − runs charged) + 4 × (wicket − expected wicket chance)</code><p>Expected runs and wicket chance come only from balls already bowled in that phase, pace or spin, and level, adjusted for the batter, bowler, teams, and ground.</p></div>
      <div><h4>Pressure</h4><code>pressure = occasion × competition × ball difficulty + shock + run of play</code><p>Occasion runs from a dead rubber up to a final. Ball difficulty adds the phase, wickets down, and the asking rate. Shock and run of play read the last six and eighteen balls, never the current one.</p></div>
      <div><h4>Who is compared and who is ranked</h4><p>Batters are compared within top, middle, or lower order. Bowlers are compared with all bowlers. Seasons fade by 0.9 a year back from 2026, and Emerging and Rising Stars balls count half. To be ranked a player needs 120 weighted legal balls, 30 of them high pressure.</p></div>
    </div>
  </section>`;
}

async function board() {
  const pool = await loadPool();
  const why = {};
  const whyNote = (row, skill) => {
    const bars = PIECES.map(([key, label]) => {
      const z = Number(row[key] || 0);
      const width = Math.min(Math.abs(z), 3) / 3 * 50;
      return `<li><span>${label}</span><i><em class="${z < 0 ? "neg" : "pos"}" style="width:${width}%;${z < 0 ? `right:50%` : `left:50%`}"></em></i><b>${z >= 0 ? "+" : ""}${num(z, 2)}</b></li>`;
    }).join("");
    return `<p class="why-name">${row.player_name}</p><p class="why-meta">${skill === "batters" ? "Batter" : "Bowler"} · rank ${row.rank} · score ${num(row.composite, 3)}</p>${story(row, skill).map((line) => `<p>${line}</p>`).join("")}<p class="why-sub">The seven pieces, against peers</p><ul class="why-bars">${bars}</ul>`;
  };
  pool.batters.slice(0, 10).forEach((row) => { why[`batters-${row.player_id}`] = whyNote(row, "batters"); });
  pool.bowlers.slice(0, 10).forEach((row) => { why[`bowlers-${row.player_id}`] = whyNote(row, "bowlers"); });
  app.innerHTML = `
    <section class="board-ten">
      <div class="board-copy">
        <h2>Top 10</h2>
        <p>These are the batters and bowlers who have held up best when the game tightens: the death, a steep chase, or a knockout. The number beside each name is the published score. Higher is better. A player needs 120 weighted legal balls, and 30 of them in those tight overs, before he can appear here.</p>
        <p>Rest on a name. The pink note beside the lists says, in ordinary cricket, why that person is this high.</p>
        <p>All batters and All bowlers, in the banner, open the full ranked lists. Data deep dive opens one of these ten and walks through a whole innings, ball by ball, with the match result. The block below lets you change the weights. Those short lists move. This top 10 does not.</p>
      </div>
      <div class="official">${officialList("Batters", pool.batters, "batters")}${officialList("Bowlers", pool.bowlers, "bowlers")}</div>
      <div id="why-panel" class="why-panel"></div>
    </section>
    <nav class="link-row">
      <a class="link-box" href="#report"><strong>Report</strong><em>Yet to be attached</em></a>
      <a class="link-box" href="#notebooks"><strong>Notebooks</strong><em>Yet to be attached</em></a>
      <a class="link-box" href="#slides"><strong>Slides</strong><em>Yet to be attached</em></a>
      <a class="link-box" href="#code"><strong>Code</strong><em>Yet to be attached</em></a>
    </nav>
    <section class="sandbox">
      <div class="play-explain">
        <h2>A score you can retune</h2>
        <p>The published score adds seven pieces of a player’s cricket. Switch a piece off or move its weight. The short lists change in the browser. The top 10 above stays the published order, and nothing you move is saved.</p>
      </div>
      <div class="play-box">
        <div class="formula-block"><p>Play with the formula</p><code id="formula-line">${formulaText()}</code></div>
        <div class="play-main">
          <div>
            <div class="weights">${PIECES.map(([key, label]) => `<label class="weight"><input type="checkbox" data-use="${key}" ${state.used[key] ? "checked" : ""}><span>${label}</span><input type="range" min="0" max="40" step="1" data-weight="${key}" value="${Math.round(state.weights[key] * 100)}" ${state.used[key] ? "" : "disabled"}><b>${state.weights[key].toFixed(2)}</b></label>`).join("")}</div>
            <button class="ghost" id="reset-weights" type="button">Reset weights</button>
          </div>
          <div class="live-lists">${miniList("Batters", pool.batters)}${miniList("Bowlers", pool.bowlers)}</div>
        </div>
      </div>
    </section>
    ${metricsGuide()}`;
  const paintLive = () => {
    const line = document.querySelector("#formula-line");
    if (line) line.textContent = formulaText();
    document.querySelectorAll("[data-weight]").forEach((slider) => {
      const readout = slider.parentElement.querySelector("b");
      if (readout) readout.textContent = state.weights[slider.dataset.weight].toFixed(2);
    });
    const lists = document.querySelector(".live-lists");
    if (lists) lists.innerHTML = `${miniList("Batters", pool.batters)}${miniList("Bowlers", pool.bowlers)}`;
  };
  document.querySelectorAll("[data-use]").forEach((box) => box.onchange = () => {
    state.used[box.dataset.use] = box.checked;
    box.parentElement.querySelector("[data-weight]").disabled = !box.checked;
    paintLive();
  });
  document.querySelectorAll("[data-weight]").forEach((slider) => slider.oninput = () => {
    state.weights[slider.dataset.weight] = Number(slider.value) / 100;
    paintLive();
  });
  document.querySelector("#reset-weights").onclick = () => {
    state.weights = Object.fromEntries(PIECES.map(([key, , weight]) => [key, weight]));
    state.used = Object.fromEntries(PIECES.map(([key]) => [key, true]));
    board();
  };
  document.querySelectorAll("[data-open]").forEach((button) => button.onclick = () => {
    state.skill = button.dataset.open;
    state.q = "";
    state.role = "";
    state.ranked = "1";
    state.sort = "rank";
    state.dir = "asc";
    setView("rankings");
  });
  const panel = document.querySelector("#why-panel");
  const picks = [...document.querySelectorAll(".pick")];
  const paintWhy = (pick) => {
    picks.forEach((item) => item.classList.toggle("active", item === pick));
    panel.innerHTML = `${why[`${pick.dataset.skill}-${pick.dataset.id}`] || ""}<p class="why-hint">Rest on another name to swap this note.</p>`;
  };
  if (picks.length) paintWhy(picks[0]);
  let hoverTimer = 0;
  picks.forEach((pick) => {
    const show = () => {
      window.clearTimeout(hoverTimer);
      hoverTimer = window.setTimeout(() => paintWhy(pick), 220);
    };
    pick.addEventListener("mouseenter", show);
    pick.addEventListener("focus", show);
  });
}

function method() {
  app.innerHTML = `<section class="step-list">${STEPS.map((step, index) => `
    <details class="step" ${index === 0 ? "open" : ""}>
      <summary><span>${index + 1}</span>${step.title}</summary>
      <div class="body">${step.body}</div>
    </details>`).join("")}</section>`;
}

async function rankings() {
  const params = new URLSearchParams({
    q: state.q, role: state.role, ranked: state.ranked, sort: state.sort, dir: state.dir,
  });
  const data = await getJson(`/api/${state.skill}?${params}`);
  const columns = COLUMNS[state.skill];
  app.innerHTML = `
    <div class="toolbar">
      <div class="skill">
        <button type="button" data-skill="batters" class="${state.skill === "batters" ? "active" : ""}">Batters</button>
        <button type="button" data-skill="bowlers" class="${state.skill === "bowlers" ? "active" : ""}">Bowlers</button>
      </div>
      <input id="search" type="search" placeholder="Search a player" value="${state.q}">
      <select id="role">
        <option value="">All roles</option>
        ${data.roles.map((role) => `<option value="${role}" ${role === state.role ? "selected" : ""}>${role}</option>`).join("")}
      </select>
      <select id="ranked">
        <option value="1" ${state.ranked === "1" ? "selected" : ""}>Ranked only</option>
        <option value="0" ${state.ranked === "0" ? "selected" : ""}>Everyone</option>
      </select>
    </div>
    <div class="table-wrap"><table>
      <thead><tr>${columns.map(([key, label]) => `<th class="${key === "player_name" ? "name" : ""}" data-sort="${key}">${label}${state.sort === key ? (state.dir === "asc" ? " ↑" : " ↓") : ""}</th>`).join("")}</tr></thead>
      <tbody>${data.rows.map((row) => `<tr class="clickable" data-id="${row.player_id}">
        ${columns.map(([key]) => `<td class="${key === "player_name" ? "name" : ""} ${["composite", "baseline", "band_high", "clutch", "peers", "consistency"].includes(key) ? cls(row[key]) : ""}">${key === "player_name" || key === "role" ? row[key] : key === "rank" ? (row.rank ?? "—") : num(row[key], key === "runs" || key === "wickets" ? 0 : 3)}</td>`).join("")}
      </tr>`).join("")}</tbody>
    </table></div>
    <p class="note">${data.count} players. Click a row to see how that composite was built. Click a column heading to sort.</p>`;
  document.querySelectorAll("[data-skill]").forEach((button) => button.onclick = () => {
    state.skill = button.dataset.skill;
    state.role = "";
    state.sort = "rank";
    state.dir = "asc";
    rankings();
  });
  document.querySelector("#search").onchange = (event) => { state.q = event.target.value; rankings(); };
  document.querySelector("#role").onchange = (event) => { state.role = event.target.value; rankings(); };
  document.querySelector("#ranked").onchange = (event) => { state.ranked = event.target.value; rankings(); };
  document.querySelectorAll("th[data-sort]").forEach((header) => header.onclick = () => {
    const key = header.dataset.sort;
    state.dir = state.sort === key && state.dir === "asc" ? "desc" : "asc";
    state.sort = key;
    rankings();
  });
  document.querySelectorAll("tr.clickable").forEach((row) => row.onclick = () => {
    state.playerId = Number(row.dataset.id);
    state.ballOffset = 0;
    state.ballPhase = "";
    state.ballBand = "";
    setView("player");
  });
}

function spellTable(skill, spells) {
  if (!spells.length) return "<p>No innings of at least 6 legal balls.</p>";
  const metric = skill === "batters" ? "Strike rate" : "Economy";
  return `<div class="table-wrap"><table>
    <thead><tr><th class="name">Date</th><th>Innings</th><th>Balls</th><th>${metric}</th><th>Teammate z</th><th>Opposition z</th><th>Passage</th><th class="name">Label</th></tr></thead>
    <tbody>${spells.map((spell) => `<tr>
      <td class="name">${spell.match_date}</td><td>${spell.innings}</td><td>${num(spell.balls, 0)}</td>
      <td>${num(spell.metric, 2)}</td><td class="${cls(spell.z_team)}">${num(spell.z_team)}</td>
      <td class="${cls(spell.z_opp)}">${num(spell.z_opp)}</td><td class="${cls(spell.z_passage)}">${num(spell.z_passage)}</td>
      <td class="name">${spell.label}</td></tr>`).join("")}
    </tbody></table></div>`;
}

function clutchTable(rows) {
  if (!rows.length) return "<p>No high-band spell of at least 6 balls with a teammate comparison.</p>";
  return `<div class="table-wrap"><table>
    <thead><tr><th class="name">Date</th><th>Innings</th><th>Balls</th><th>Spell rate</th><th>Own gap</th><th>Teammate z</th><th>Spell score</th></tr></thead>
    <tbody>${rows.map((spell) => `<tr>
      <td class="name">${spell.match_date}</td><td>${spell.innings}</td><td>${num(spell.balls, 0)}</td>
      <td>${num(spell.metric, 2)}</td><td class="${cls(spell.own_gap)}">${num(spell.own_gap)}</td>
      <td class="${cls(spell.z_team)}">${num(spell.z_team)}</td><td class="${cls(spell.clutch)}">${num(spell.clutch)}</td>
    </tr>`).join("")}</tbody></table></div>`;
}

function ballTable(skill, payload) {
  const rows = payload.rows;
  if (!rows.length) return "<p>No legal balls for this filter.</p>";
  const bandKey = skill === "batters" ? "band" : "band_bowl";
  const valueKey = skill === "batters" ? "e_bat" : "e_bowl";
  const xKey = skill === "batters" ? "x_runs" : "x_runs_bowl";
  const other = skill === "batters" ? "bowler_name" : "striker_name";
  return `<div class="table-wrap"><table>
    <thead><tr>
      <th class="name">Date</th><th class="name">Competition</th><th>Inn</th><th>Ball</th><th>Phase</th><th>Band</th>
      <th class="name">${skill === "batters" ? "Bowler" : "Batter"}</th><th>Bat runs</th><th>Charged</th>
      <th>x runs</th><th>x wicket</th><th>Ball value</th><th>Pressure</th>
    </tr></thead>
    <tbody>${rows.map((ball) => `<tr>
      <td class="name">${ball.match_date}</td><td class="name">${ball.comp_name}</td><td>${ball.innings}</td><td>${ball.n}</td>
      <td>${ball.phase}</td><td>${ball[bandKey]}</td><td class="name">${ball[other]}</td>
      <td>${num(ball.bat_runs, 0)}</td><td>${num(ball.charged_runs, 0)}</td><td>${num(ball[xKey])}</td>
      <td>${num(ball.x_wicket, 3)}</td><td class="${cls(ball[valueKey])}">${num(ball[valueKey])}</td>
      <td>${num(skill === "batters" ? ball.pressure_bat : ball.pressure_bowl)}</td>
    </tr>`).join("")}</tbody></table></div>
    <div class="pager" style="margin-top:10px">
      <button type="button" id="prev" ${payload.offset === 0 ? "disabled" : ""}>Previous</button>
      <span class="note">${payload.offset + 1}–${Math.min(payload.offset + payload.limit, payload.total)} of ${payload.total}</span>
      <button type="button" id="next" ${payload.offset + payload.limit >= payload.total ? "disabled" : ""}>Next</button>
    </div>`;
}

async function player() {
  const data = await getJson(`/api/player/${state.skill}/${state.playerId}`);
  const balls = await getJson(`/api/player/${state.skill}/${state.playerId}/balls?offset=${state.ballOffset}&phase=${encodeURIComponent(state.ballPhase)}&band=${encodeURIComponent(state.ballBand)}`);
  const person = data.player;
  const equation = data.parts.map((part) => `${num(part.weight, 2)}×${num(part.z, 3)}`).join(" + ");
  app.innerHTML = `
    <button class="back" id="back" type="button">Back to rankings</button>
    <div class="player-head">
      <div>
        <h2>${person.player_name}</h2>
        <p class="note">${person.role} · ${state.skill === "batters" ? "batter" : "bowler"} · ${person.ranked ? `ranked ${person.rank}` : "below the ranking floor"}</p>
      </div>
      <div class="rank-mark">${person.ranked ? `#${person.rank}` : "—"}</div>
    </div>
    <div class="cards">
      <div class="card"><div class="k">Composite</div><div class="v">${num(person.composite)}</div></div>
      <div class="card"><div class="k">Sum of weight × z</div><div class="v">${num(data.contribution_sum)}</div></div>
      <div class="card"><div class="k">Weighted balls</div><div class="v">${num(person.n_eff, 1)}</div></div>
      <div class="card"><div class="k">High-band balls</div><div class="v">${num(person.high_n_eff, 1)}</div></div>
    </div>
    <div class="equation">Composite = ${equation} = ${num(data.contribution_sum)}. The published composite is ${num(person.composite)}. Component ranks below are among ranked players. ${state.skill === "batters" ? "The role rank is among ranked players in the same batting role, because the z-score itself was taken inside that role." : "Bowling z-scores are taken across all bowlers."}</div>
    ${data.parts.map((part) => `<details class="component">
      <summary><strong>${part.label}</strong> · z ${num(part.z)} · weight ${num(part.weight, 2)} · contribution <span class="${cls(part.contribution)}">${num(part.contribution)}</span> · rank ${part.rank ?? "—"} of ranked${part.role_rank ? ` · ${part.role_rank} in role` : ""}</summary>
      <div class="body">${part.detail.map((line) => `<p>${line}</p>`).join("")}
        ${part.key === "peers" ? spellTable(state.skill, data.spells) : ""}
        ${part.key === "clutch" ? clutchTable(data.clutch) : ""}      </div>
    </details>`).join("")}
    <h3>Phases</h3>
    <div class="table-wrap"><table>
      <thead><tr><th class="name">Phase</th><th>Balls</th><th>${state.skill === "batters" ? "Runs" : "Charged runs"}</th></tr></thead>
      <tbody>${data.phases.map((phase) => `<tr><td class="name">${phase.phase}</td><td>${num(phase.balls, 0)}</td><td>${num(phase.runs, 0)}</td></tr>`).join("")}</tbody>
    </table></div>
    <h3>Legal balls</h3>
    <div class="filters">
      <select id="phase"><option value="">All phases</option>${["powerplay", "middle", "death"].map((phase) => `<option ${state.ballPhase === phase ? "selected" : ""}>${phase}</option>`).join("")}</select>
      <select id="band"><option value="">All bands</option>${["zero", "medium", "high"].map((band) => `<option ${state.ballBand === band ? "selected" : ""}>${band}</option>`).join("")}</select>
    </div>
    <div id="balls">${ballTable(state.skill, balls)}</div>`;
  document.querySelector("#back").onclick = () => setView("rankings");
  document.querySelector("#phase").onchange = (event) => { state.ballPhase = event.target.value; state.ballOffset = 0; player(); };
  document.querySelector("#band").onchange = (event) => { state.ballBand = event.target.value; state.ballOffset = 0; player(); };
  const prev = document.querySelector("#prev");
  const next = document.querySelector("#next");
  if (prev) prev.onclick = () => { state.ballOffset = Math.max(0, state.ballOffset - balls.limit); player(); };
  if (next) next.onclick = () => { state.ballOffset += balls.limit; player(); };
}

async function render() {
  if (state.view === "board") await board();
  else if (state.view === "rankings") await rankings();
  else await player();
}

function divergingBars(items) {
  const max = Math.max(...items.map((item) => Math.abs(item.value)), 0.05);
  return `<div class="dbars">${items.map((item) => {
    const pct = Math.abs(item.value) / max * 48;
    const left = item.value >= 0 ? 50 : 50 - pct;
    return `<div class="dbar"><span>${item.label}</span><div class="dtrack"><i class="${item.value < 0 ? "down" : "up"}" style="left:${left}%;width:${pct}%"></i></div><b>${item.value.toFixed(2)}</b></div>`;
  }).join("")}</div>`;
}

function componentChart(parts) {
  const rows = parts.map((part) => ({ label: part.label, value: part.contribution || 0 }));
  return divergingBars(rows);
}

async function playersPage() {
  const pool = await loadPool();
  const skill = state.pageSkill;
  const list = skill ? pool[skill].slice(0, 10) : [];
  const selected = list.find((row) => row.player_id === state.pageId) || null;
  let detail = null;
  let options = [];
  let innings = null;
  if (selected) {
    detail = await getJson(`/api/player/${skill}/${selected.player_id}`);
    const listed = await getJson(`/api/player/${skill}/${selected.player_id}/innings`);
    options = listed.innings || [];
    const chosen = options.find((item) => item.match_id === state.pageMatch && item.innings === state.pageInnings) || options[0];
    if (chosen) {
      state.pageMatch = chosen.match_id;
      state.pageInnings = chosen.innings;
      innings = await getJson(`/api/player/${skill}/${selected.player_id}/innings/${chosen.match_id}/${chosen.innings}`);
    }
  }
  app.innerHTML = `
    <section class="chooser">
      <h2>Look at one of the ten</h2>
      <p class="lede">Pick batters or bowlers, then one name. The drawing uses his saved score. It does not use the weight experiment on the board.</p>
      <div class="nav">
        <button type="button" id="pick-batters" class="${skill === "batters" ? "active" : ""}">Top 10 batters</button>
        <button type="button" id="pick-bowlers" class="${skill === "bowlers" ? "active" : ""}">Top 10 bowlers</button>
      </div>
      ${skill ? `<ol class="chooser-list">${list.map((row) => `<li><button type="button" class="${row.player_id === state.pageId ? "active" : ""}" data-id="${row.player_id}"><span>${String(row.rank).padStart(2, "0")}</span><span>${row.player_name}</span><b>${num(row.composite, 3)}</b></button></li>`).join("")}</ol>` : ""}
    </section>
    ${selected && detail ? drawnPlayer(selected, skill, detail, options, innings) : ""}`;
  document.querySelector("#pick-batters").onclick = () => {
    state.pageSkill = "batters";
    state.pageId = null;
    state.pageMatch = null;
    state.pageInnings = null;
    playersPage();
  };
  document.querySelector("#pick-bowlers").onclick = () => {
    state.pageSkill = "bowlers";
    state.pageId = null;
    state.pageMatch = null;
    state.pageInnings = null;
    playersPage();
  };
  document.querySelectorAll("[data-id]").forEach((button) => button.onclick = () => {
    state.pageId = Number(button.dataset.id);
    state.pageMatch = null;
    state.pageInnings = null;
    playersPage();
  });
  document.querySelectorAll("[data-innings]").forEach((button) => button.onclick = () => {
    state.pageMatch = Number(button.dataset.match);
    state.pageInnings = Number(button.dataset.innings);
    playersPage();
  });
}

function drawnPlayer(row, skill, detail, options, innings) {
  const lines = story(row, skill, detail.phases);
  const parts = detail.parts;
  const ownLine = !innings ? "" : skill === "batters"
    ? `He made ${round1(innings.player_runs)} from ${innings.player_balls} balls in this innings.`
    : `He bowled ${innings.player_balls} balls, took ${round1(innings.player_wickets)} wickets, and conceded ${round1(innings.player_charged)}.`;
  const ballRows = (innings && innings.rows) || [];
  return `<section class="drawn">
    <div class="player-head">
      <div>
        <p class="eyebrow">${skill === "batters" ? "Batter" : "Bowler"} · ${row.role}</p>
        <h2>${row.player_name}</h2>
      </div>
      <div class="rank-mark">#${row.rank}</div>
    </div>
    <div class="cards">
      <div class="card"><div class="k">Score</div><div class="v">${num(row.composite, 3)}</div></div>
      <div class="card"><div class="k">Rank</div><div class="v">${row.rank}</div></div>
      <div class="card"><div class="k">Tight balls</div><div class="v">${round1(row.high_n_eff)}</div></div>
      <div class="card"><div class="k">Compared with</div><div class="v">${skill === "batters" ? row.role : "All bowlers"}</div></div>
    </div>
    ${lines.map((line) => `<p class="lede">${line}</p>`).join("")}
    <h3>Each piece of the ${num(row.composite, 2)}</h3>
    <p class="note">Bar length is the weight times the player’s score on that piece. The seven bars sum to the published score. Rank is among ranked ${skill === "batters" ? "batters" : "bowlers"}.</p>
    ${componentChart(parts)}
    <div class="table-wrap"><table>
      <thead><tr><th class="name">Piece</th><th>Weight</th><th>Score</th><th>Share of the total</th><th>Rank</th></tr></thead>
      <tbody>${parts.map((part) => `<tr><td class="name">${part.label}</td><td>${num(part.weight, 2)}</td><td class="${cls(part.z)}">${num(part.z, 2)}</td><td class="${cls(part.contribution)}">${num(part.contribution, 3)}</td><td>${part.rank ?? "—"}</td></tr>`).join("")}</tbody>
    </table></div>
    <h3>One innings</h3>
    <p class="note">Pick a match he played. The table is every ball of that innings. His own balls are marked.</p>
    <div class="ball-strip">${(options || []).map((item) => `<button type="button" data-match="${item.match_id}" data-innings="${item.innings}" class="${item.match_id === state.pageMatch && item.innings === state.pageInnings ? "active" : ""}">${item.match_date}${item.innings > 2 ? " · super over" : ""}<br>${item.comp_name}<br>${skill === "batters" ? `${round1(item.runs)} runs` : `${round1(item.wickets)} wickets`}</button>`).join("")}</div>
    ${innings ? `<div class="innings-head"><p><strong>${innings.home} vs ${innings.away}</strong></p><p>${innings.competition}. ${innings.date}. ${innings.stage}.</p><p>${innings.result}</p><p>${innings.innings > 2 ? `Super over (innings ${innings.innings})` : `Innings ${innings.innings}`}: ${round1(innings.runs)} for ${innings.wickets} from ${innings.balls} balls. ${ownLine}</p></div>
    <div class="table-wrap innings-table"><table>
      <thead><tr><th>Ball</th><th class="name">Phase</th><th class="name">Batter</th><th class="name">Bowler</th><th>Runs</th><th class="name">Wicket</th></tr></thead>
      <tbody>${ballRows.map((item) => {
        const mine = skill === "batters" ? item.striker_id === row.player_id : item.bowler_id === row.player_id;
        const wicket = item.striker_out ? "out" : "";
        return `<tr class="${mine ? "mine" : ""}"><td>${item.n}</td><td class="name">${item.phase}</td><td class="name">${item.striker_name}</td><td class="name">${item.bowler_name}</td><td>${round1(item.bat_runs)}</td><td class="name">${wicket}</td></tr>`;
      }).join("")}</tbody>
    </table></div>` : ""}
  </section>`;
}

if (document.body.dataset.page === "players") {
  playersPage();
} else {
  document.querySelector("#tab-board").onclick = () => setView("board");
  document.querySelector("#tab-batters").onclick = () => {
    state.skill = "batters";
    state.q = "";
    state.role = "";
    state.ranked = "1";
    state.sort = "rank";
    state.dir = "asc";
    setView("rankings");
  };
  document.querySelector("#tab-bowlers").onclick = () => {
    state.skill = "bowlers";
    state.q = "";
    state.role = "";
    state.ranked = "1";
    state.sort = "rank";
    state.dir = "asc";
    setView("rankings");
  };
  render();
}
