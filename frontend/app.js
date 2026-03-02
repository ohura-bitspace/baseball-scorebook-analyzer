// ── Config ───────────────────────────────────────────────────────────────────
const API_BASE = "http://localhost:8000";

// ── DOM refs ─────────────────────────────────────────────────────────────────
const dropZone      = document.getElementById("drop-zone");
const fileInput     = document.getElementById("file-input");
const previewWrapper = document.getElementById("preview-wrapper");
const imagePreview  = document.getElementById("image-preview");
const clearBtn      = document.getElementById("clear-btn");
const analyzeBtn    = document.getElementById("analyze-btn");
const loading       = document.getElementById("loading");
const errorBox      = document.getElementById("error-box");
const errorMsg      = document.getElementById("error-msg");
const results       = document.getElementById("results");

let selectedFile = null;

// ── Drag and drop ─────────────────────────────────────────────────────────────
["dragenter", "dragover"].forEach(evt =>
  dropZone.addEventListener(evt, e => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  })
);
["dragleave", "drop"].forEach(evt =>
  dropZone.addEventListener(evt, e => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
  })
);
dropZone.addEventListener("drop", e => {
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});
dropZone.addEventListener("keydown", e => {
  if (e.key === "Enter" || e.key === " ") fileInput.click();
});
dropZone.addEventListener("click", () => fileInput.click());

// ── File picker ───────────────────────────────────────────────────────────────
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(file) {
  if (!file.type.startsWith("image/")) {
    showError("画像ファイル（JPEG, PNG, WEBP）を選択してください。");
    return;
  }
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = e => {
    imagePreview.src = e.target.result;
    previewWrapper.hidden = false;
    dropZone.hidden = true;
  };
  reader.readAsDataURL(file);
  analyzeBtn.disabled = false;
  hideError();
  results.hidden = true;
}

clearBtn.addEventListener("click", () => {
  selectedFile = null;
  fileInput.value = "";
  previewWrapper.hidden = true;
  dropZone.hidden = false;
  analyzeBtn.disabled = true;
  results.hidden = true;
  hideError();
});

// ── Analyze ───────────────────────────────────────────────────────────────────
analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  setLoading(true);
  hideError();
  results.hidden = true;

  try {
    const form = new FormData();
    form.append("file", selectedFile);

    const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: form });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Server error ${res.status}`);
    }

    const data = await res.json();
    renderResults(data);
  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
});

// ── UI helpers ────────────────────────────────────────────────────────────────
function setLoading(on) {
  loading.hidden = !on;
  analyzeBtn.disabled = on;
}
function showError(msg) {
  errorMsg.textContent = msg;
  errorBox.hidden = false;
}
function hideError() {
  errorBox.hidden = true;
}
function v(x) {
  return x === null || x === undefined ? "—" : x;
}

// ── Result code → CSS class ───────────────────────────────────────────────────
function resultClass(code) {
  if (!code) return "";
  const c = code.toUpperCase();
  if (["1B","2B","3B","SAC","SF","FC","E","HBP"].includes(c)) return "hit";
  if (c === "HR") return "hr";
  if (["BB","IBB"].includes(c)) return "walk";
  return "out";
}

// ── Render functions ──────────────────────────────────────────────────────────
function renderResults(data) {
  renderGameInfo(data);
  renderInningTable(data.innings || []);
  renderBatterTable(data.batters || []);
  renderPitcherTable(data.pitchers || []);
  renderMetadata(data.metadata);

  // Raw JSON — pretty-print but truncate raw_claude_response to keep it readable
  const display = { ...data };
  if (display.raw_claude_response && display.raw_claude_response.length > 500) {
    display.raw_claude_response = display.raw_claude_response.slice(0, 500) + "... [truncated]";
  }
  document.getElementById("raw-json").textContent = JSON.stringify(display, null, 2);

  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth" });
}

function renderGameInfo(data) {
  const rows = [
    ["チーム名",  v(data.team_name)],
    ["対戦相手",  v(data.opponent_name)],
    ["試合日",    v(data.game_date)],
    ["会場",      v(data.venue)],
    ["合計得点",  v(data.total_score)],
  ];
  document.getElementById("game-info-table").innerHTML = rows
    .map(([k, val]) => `<tr><th class="left">${k}</th><td class="left">${val}</td></tr>`)
    .join("");
}

function renderInningTable(innings) {
  const el = document.getElementById("inning-table");
  if (!innings.length) {
    el.innerHTML = "<tr><td>イニングデータなし</td></tr>";
    return;
  }
  const headers = ["イニング", "得点", "安打", "四球", "失策", "投球数"];
  const head = `<thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>`;
  const body = innings.map(inn => `<tr>
    <td>${inn.inning}</td>
    <td>${v(inn.score)}</td>
    <td>${v(inn.hits)}</td>
    <td>${v(inn.walks)}</td>
    <td>${v(inn.errors)}</td>
    <td>${v(inn.pitch_count)}</td>
  </tr>`).join("");
  el.innerHTML = head + `<tbody>${body}</tbody>`;
}

function renderBatterTable(batters) {
  const el = document.getElementById("batter-table");
  if (!batters.length) {
    el.innerHTML = "<tr><td>打者データなし</td></tr>";
    return;
  }

  // Collect all inning numbers that appear in the data
  const inningSet = new Set();
  batters.forEach(b => b.inning_stats.forEach(s => inningSet.add(s.inning)));
  const innings = [...inningSet].sort((a, b) => a - b);

  const headers = [
    "打順", "選手名", "守備",
    ...innings.map(n => `${n}回`),
    "打", "安", "打点", "得", "四", "三振"
  ];
  const head = `<thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>`;

  const body = batters.map(b => {
    const innCells = innings.map(n => {
      const stat = b.inning_stats.find(s => s.inning === n);
      if (!stat || !stat.at_bats.length) return "<td>—</td>";
      const codes = stat.at_bats.map(ab => {
        const cls = resultClass(ab.result_code);
        const tip = ab.notes ? ` title="${ab.notes}"` : "";
        return `<span class="${cls}"${tip}>${ab.result_code}</span>`;
      }).join(" / ");
      return `<td>${codes}</td>`;
    }).join("");

    return `<tr>
      <td>${v(b.batting_order)}</td>
      <td class="left">${v(b.player_name)}</td>
      <td>${v(b.fielding_position)}</td>
      ${innCells}
      <td>${v(b.total_at_bats)}</td>
      <td>${v(b.total_hits)}</td>
      <td>${v(b.total_rbi)}</td>
      <td>${v(b.total_runs)}</td>
      <td>${v(b.total_walks)}</td>
      <td>${v(b.total_strikeouts)}</td>
    </tr>`;
  }).join("");

  el.innerHTML = head + `<tbody>${body}</tbody>`;
}

function renderPitcherTable(pitchers) {
  const el = document.getElementById("pitcher-table");
  if (!pitchers.length) {
    el.innerHTML = "<tr><td>投手データなし</td></tr>";
    return;
  }
  const headers = ["投手名", "回", "投球数", "安打", "四球", "三振", "失点", "自責", "勝敗"];
  const head = `<thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>`;
  const body = pitchers.map(p => `<tr>
    <td class="left">${v(p.pitcher_name)}</td>
    <td>${v(p.innings_pitched)}</td>
    <td>${v(p.total_pitch_count)}</td>
    <td>${v(p.total_hits)}</td>
    <td>${v(p.total_walks)}</td>
    <td>${v(p.total_strikeouts)}</td>
    <td>${v(p.total_earned_runs)}</td>
    <td>${v(p.total_earned_runs)}</td>
    <td>${v(p.win_loss)}</td>
  </tr>`).join("");
  el.innerHTML = head + `<tbody>${body}</tbody>`;
}

function renderMetadata(meta) {
  if (!meta) return;
  const badgeCls = `badge badge-${meta.confidence}`;
  const warnings = meta.warnings.length
    ? `<ul>${meta.warnings.map(w => `<li>${w}</li>`).join("")}</ul>`
    : "なし";

  document.getElementById("metadata-table").innerHTML = `
    <tr><th class="left">信頼度</th><td class="left"><span class="${badgeCls}">${meta.confidence}</span></td></tr>
    <tr><th class="left">画像品質</th><td class="left">${v(meta.image_quality)}</td></tr>
    <tr><th class="left">確認できたイニング数</th><td class="left">${v(meta.total_innings_visible)}</td></tr>
    <tr><th class="left">警告</th><td class="left">${warnings}</td></tr>
  `;
}
