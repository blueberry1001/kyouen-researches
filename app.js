/* Research dashboard for 7x7 cocircular-free (safe) configurations. */
const CORNER = 48; // (6,6)

const DEMOS = [
  {
    id: "trap",
    label: "最近接トラップ 4469…",
    mask: 4469862961153,
    meta: "追加飽和 · 最近接へは3石減 · 遠い先なら1石減",
  },
  {
    id: "maxA",
    label: "最大配置 A",
    mask: 7422057382691,
    meta: "14石 · 16個の最大配置のひとつ",
  },
  {
    id: "maxB",
    label: "最大配置 B",
    mask: 306772355099666,
    meta: "14石 · A とは対称差20 · 最短移動に5石減",
  },
  {
    id: "hard13",
    label: "13石の硬例",
    mask: 1204403437784,
    meta: "単調経路だと全指定先で3石減が必要",
  },
];

const HIERARCHY = [
  { floor: "13石以上", text: "各最大配置が <em>孤立</em>。12石以上では移動不可。" },
  { floor: "12石以上", text: "16個が <em>2個ずつ8群</em>。第四の角ゲートが必須。" },
  { floor: "11石以上", text: "最大配置16個が <em>すべて連結</em>。成分は903局面＋大成分。" },
  { floor: "10石以上", text: "12石の例外5,816個も含め <em>一つの巨大成分</em>。" },
];

const LOSS_ROWS = [
  ["0–5", "1.9e6", 100, 0, 0, 0],
  ["6", "8,796,600", 99.9, 0.1, 0, 0],
  ["7", "29,688,640", 99.9, 0.1, 0, 0],
  ["8", "56,927,728", 97.8, 2.2, 0, 0],
  ["9", "55,173,324", 85.3, 14.7, 0.001, 0],
  ["10", "23,478,868", 52.8, 47.0, 0.2, 0],
  ["11", "3,707,028", 14.1, 80.3, 5.6, 0.001],
  ["12", "177,760", 2.7, 51.7, 45.5, 0.2],
  ["13", "2,176", 10.3, 15.8, 59.2, 14.7],
  ["14", "16", 100, 0, 0, 0],
];

const DISTANCE_ROWS = [
  ["4–5", "下限9〜10", "最大配置と遠いが、石数を守りやすい例がある"],
  ["6", "下限10〜11", "最遠軌道の代表。37手の経路を検証済み"],
  ["7", "下限9も存在", "共通が多くても深い障壁。順序が逆転する"],
  ["8–10", "下限9〜10", "近くても単調経路では余計に減ることがある"],
];

const TRAPS = [
  {
    mask: 4469862961153,
    title: "代表 4469862961153",
    nearest: "対称差 11 → 減石 3",
    alt: "対称差 17 → 減石 1",
    barrier: "閉集合 11局面",
  },
  {
    mask: 39857431521553,
    title: "代表 39857431521553",
    nearest: "対称差 13 → 減石 3",
    alt: "対称差 15 → 減石 1",
    barrier: "閉集合 23局面",
  },
  {
    mask: 377961410760,
    title: "代表 377961410760",
    nearest: "対称差 13 → 減石 3",
    alt: "減石 1 の到着先あり",
    barrier: "閉集合 11–23局面",
  },
];

const PRESCRIBED = [
  { k: "10石", max: 2, n: "3.76億組" },
  { k: "11石", max: 3, n: "5,931万組" },
  { k: "12石", max: 3, n: "284万組" },
  { k: "13石", max: 4, n: "3.5万組" },
  { k: "14石", max: 5, n: "120組" },
];

function cellsFromMask(mask) {
  const cells = [];
  for (let p = 0; p < 49; p++) {
    cells.push({
      p,
      x: p % 7,
      y: Math.floor(p / 7),
      on: (mask >> BigInt(p)) & 1n,
    });
  }
  return cells;
}

function renderBoard(el, mask, { markCorner = true, blocked = null } = {}) {
  el.innerHTML = "";
  const cells = cellsFromMask(BigInt(mask));
  for (const c of cells) {
    const div = document.createElement("div");
    div.className = "cell";
    div.title = `(${c.x},${c.y})`;
    if (c.on) {
      div.classList.add("stone");
      div.textContent = "●";
      if (markCorner && c.p === CORNER) div.classList.add("corner");
    } else if (blocked && blocked.has(c.p)) {
      div.classList.add("blocked");
      div.textContent = "×";
    }
    el.appendChild(div);
  }
}

function initDemo() {
  const board = document.getElementById("board-demo");
  const meta = document.getElementById("board-demo-meta");
  const chips = document.getElementById("demo-chips");
  DEMOS.forEach((d, i) => {
    const b = document.createElement("button");
    b.className = "chip" + (i === 0 ? " active" : "");
    b.textContent = d.label;
    b.onclick = () => {
      chips.querySelectorAll(".chip").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      renderBoard(board, d.mask);
      meta.textContent = d.meta;
    };
    chips.appendChild(b);
  });
  renderBoard(board, DEMOS[0].mask);
  meta.textContent = DEMOS[0].meta;
}

function initHierarchy() {
  const root = document.getElementById("hierarchy");
  for (const row of HIERARCHY) {
    const div = document.createElement("div");
    div.className = "hier-row";
    div.innerHTML = `<strong>${row.floor}</strong><span>${row.text}</span>`;
    root.appendChild(div);
  }
}

function initLossTable() {
  const tbody = document.querySelector("#loss-table tbody");
  for (const row of LOSS_ROWS) {
    const tr = document.createElement("tr");
    tr.innerHTML = row.map((v) => `<td>${v}</td>`).join("");
    tbody.appendChild(tr);
  }
}

function initDistanceTable() {
  const tbody = document.querySelector("#distance-table tbody");
  for (const row of DISTANCE_ROWS) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row[0]}</td><td style="text-align:left">${row[1]}</td><td style="text-align:left">${row[2]}</td>`;
    tbody.appendChild(tr);
  }
}

function initTraps() {
  const root = document.getElementById("trap-grid");
  for (const t of TRAPS) {
    const card = document.createElement("div");
    card.className = "trap-card";
    const board = document.createElement("div");
    board.className = "board";
    renderBoard(board, t.mask);
    const stats = document.createElement("div");
    stats.className = "trap-stats";
    stats.innerHTML = `
      <div><b>${t.title}</b></div>
      <div class="hi">${t.nearest}</div>
      <div>${t.alt}</div>
      <div>${t.barrier}</div>
      <div>空点はすべて追加不能（飽和）</div>
    `;
    card.appendChild(board);
    card.appendChild(stats);
    root.appendChild(card);
  }
}

function initPrescribed() {
  const root = document.getElementById("prescribed-bars");
  for (const row of PRESCRIBED) {
    const div = document.createElement("div");
    div.className = "bar-row";
    const width = (row.max / 5) * 100;
    div.innerHTML = `
      <div class="label">${row.k}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
      <div class="val">−${row.max} · ${row.n}</div>
    `;
    root.appendChild(div);
  }
}

initDemo();
initHierarchy();
initLossTable();
initDistanceTable();
initTraps();
initPrescribed();
