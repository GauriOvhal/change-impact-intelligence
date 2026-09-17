/* =========================================================
   Change Impact Intelligence — frontend logic
   ========================================================= */

const API_BASE = ""; // same origin - backend serves this file too

let state = {
  projectId: null,
  userId: null,
};

// ---------------- navigation ----------------
const navItems = document.querySelectorAll(".nav-item");
const views = document.querySelectorAll(".view");

navItems.forEach((btn) => {
  btn.addEventListener("click", () => {
    navItems.forEach((b) => b.classList.remove("active"));
    views.forEach((v) => v.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`view-${btn.dataset.view}`).classList.add("active");

    if (btn.dataset.view === "dashboard") loadDashboard();
    if (btn.dataset.view === "impact") loadRevisionOptions("impact-select");
    if (btn.dataset.view === "ripple") loadRevisionOptions("ripple-select");
  });
});

// ---------------- helpers ----------------
const rupees = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;

function riskPill(level) {
  const cls = level === "High" ? "risk-high" : level === "Medium" ? "risk-medium" : "risk-low";
  return `<span class="risk-pill ${cls}">${level}</span>`;
}

function statusPill(status) {
  const cls =
    status === "Approved" ? "status-approved" : status === "Rejected" ? "status-rejected" : "status-pending";
  return `<span class="status-pill ${cls}">${status}</span>`;
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status} on ${path}`);
  return res.json();
}

// ---------------- projects & users ----------------
async function loadProjects() {
  const projects = await api("/api/projects");
  const select = document.getElementById("project-select");
  select.innerHTML = projects
    .map((p) => `<option value="${p.id}">${p.name}</option>`)
    .join("");
  state.projectId = Number(select.value) || (projects[0] && projects[0].id) || null;
}

document.getElementById("project-select").addEventListener("change", (e) => {
  state.projectId = Number(e.target.value);
  loadDashboard();
});

document.getElementById("new-project-btn").addEventListener("click", () => {
  document.getElementById("new-project-overlay").classList.remove("hidden");
  document.getElementById("np-name").focus();
});

function closeProjectModal() {
  document.getElementById("new-project-overlay").classList.add("hidden");
  document.getElementById("new-project-form").reset();
  document.getElementById("np-budget-preview").innerHTML = "&nbsp;";
}

document.getElementById("np-cancel").addEventListener("click", closeProjectModal);
document.getElementById("np-cancel-2").addEventListener("click", closeProjectModal);
document.getElementById("new-project-overlay").addEventListener("click", (e) => {
  if (e.target.id === "new-project-overlay") closeProjectModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !document.getElementById("new-project-overlay").classList.contains("hidden")) {
    closeProjectModal();
  }
});

document.getElementById("np-budget").addEventListener("input", (e) => {
  const preview = document.getElementById("np-budget-preview");
  const val = Number(e.target.value);
  preview.textContent = val ? rupees(val) : "";
});

document.getElementById("new-project-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById("np-name").value,
    client: document.getElementById("np-client").value,
    budget: Number(document.getElementById("np-budget").value) || 0,
    deadline: document.getElementById("np-deadline").value,
  };
  const project = await api("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await loadProjects();
  document.getElementById("project-select").value = project.id;
  state.projectId = project.id;
  closeProjectModal();
  loadDashboard();
});

function formatDeadline(iso) {
  if (!iso) return null;
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

function renderProjectStrip(project) {
  const strip = document.getElementById("project-strip");
  if (!project) {
    strip.classList.remove("visible");
    strip.innerHTML = "";
    return;
  }

  const pct = project.budget_used_pct;
  const pctClamped = pct === null || pct === undefined ? 0 : Math.min(pct, 100);
  const barClass = pct >= 100 ? "over" : pct >= 80 ? "warn" : "";

  let deadlineTag = "";
  if (project.deadline) {
    const days = project.days_left;
    const cls = days < 0 ? "overdue" : days <= 14 ? "soon" : "";
    const label =
      days < 0 ? `${Math.abs(days)} days overdue` : days === 0 ? "Due today" : `${days} days left`;
    deadlineTag = `<span class="ps-deadline-tag ${cls}">${formatDeadline(project.deadline)} · ${label}</span>`;
  }

  strip.innerHTML = `
    <span class="ps-name">${project.name}</span>
    ${project.client ? `<div class="ps-item"><span>CLIENT</span><strong>${project.client}</strong></div>` : ""}
    ${deadlineTag ? `<div class="ps-item"><span>DEADLINE</span><strong>${deadlineTag}</strong></div>` : ""}
    ${
      project.budget
        ? `<div class="ps-item ps-budget">
             <span>BUDGET UTILISATION — ${rupees(project.budget)}</span>
             <div class="ps-budget-bar"><div class="ps-budget-bar-fill ${barClass}" style="width:${pctClamped}%"></div></div>
           </div>`
        : ""
    }
  `;
  strip.classList.add("visible");
}

async function loadUsers() {
  const users = await api("/api/users");
  const select = document.getElementById("user-select");
  select.innerHTML = users
    .map((u) => `<option value="${u.id}">${u.name} — ${u.role}</option>`)
    .join("");
  state.userId = Number(select.value) || (users[0] && users[0].id) || null;
}

document.getElementById("user-select").addEventListener("change", (e) => {
  state.userId = Number(e.target.value);
});

// ---------------- dashboard ----------------
let categoryChart, riskChart, trendChart, costChart;

async function loadDashboard() {
  const qs = state.projectId ? `?project_id=${state.projectId}` : "";
  const d = await api(`/api/dashboard${qs}`);

  renderProjectStrip(d.active_project);

  document.getElementById("kpi-projects").textContent = d.total_projects;
  document.getElementById("kpi-revisions").textContent = d.total_revisions;
  document.getElementById("kpi-cost").textContent = rupees(d.total_cost);
  document.getElementById("kpi-delay").textContent = `${d.total_delay} days`;
  document.getElementById("kpi-risk").textContent = d.high_risk_changes;
  document.getElementById("kpi-pending").textContent = d.pending_approvals;
  document.getElementById("kpi-requester").textContent = d.top_requester
    ? `${d.top_requester.name} (${d.top_requester.c})`
    : "—";

  const box = document.getElementById("highest-risk-box");
  box.textContent = d.highest_risk_revision
    ? `${d.highest_risk_revision.title} — risk score ${d.highest_risk_revision.risk_score}/100`
    : "No revisions yet.";

  renderTrendChart(d.revision_trend);
  renderCostChart(d.recent_revisions);
  renderCategoryChart(d.revisions_by_category);
  renderRiskChart(d.revisions_by_risk);
  renderRecentTable(d.recent_revisions);
}

function renderTrendChart(rows) {
  const ctx = document.getElementById("chart-trend");
  const labels = rows.map((r) => r.day);
  const values = rows.map((r) => r.count);
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Revisions logged",
          data: values,
          borderColor: "#1F8A7A",
          backgroundColor: "rgba(31,138,122,0.12)",
          fill: true,
          tension: 0.25,
        },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#64708A" }, grid: { color: "#DCE3EE" } },
        y: { ticks: { color: "#64708A" }, grid: { color: "#DCE3EE" }, beginAtZero: true, precision: 0 },
      },
    },
  });
}

function renderCostChart(rows) {
  const ctx = document.getElementById("chart-cost");
  const ordered = [...rows].reverse(); // oldest -> newest, matches trend chart direction
  const labels = ordered.map((r) => r.title);
  const values = ordered.map((r) => r.total_cost);
  if (costChart) costChart.destroy();
  costChart = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets: [{ data: values, backgroundColor: "#1F8A7A" }] },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#64708A", maxRotation: 30, minRotation: 0 }, grid: { color: "#DCE3EE" } },
        y: { ticks: { color: "#64708A" }, grid: { color: "#DCE3EE" }, beginAtZero: true },
      },
    },
  });
}

function renderCategoryChart(rows) {
  const ctx = document.getElementById("chart-category");
  const labels = rows.map((r) => r.category || "Uncategorised");
  const values = rows.map((r) => r.c);
  if (categoryChart) categoryChart.destroy();
  categoryChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: "#B5750E" }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#64708A" }, grid: { color: "#DCE3EE" } },
        y: { ticks: { color: "#64708A" }, grid: { color: "#DCE3EE" }, beginAtZero: true },
      },
    },
  });
}

function renderRiskChart(rows) {
  const ctx = document.getElementById("chart-risk");
  const order = ["Low", "Medium", "High"];
  const colors = { Low: "#1F8A7A", Medium: "#B5750E", High: "#C9402B" };
  const map = Object.fromEntries(rows.map((r) => [r.risk_level, r.c]));
  const labels = order.filter((o) => map[o] !== undefined);
  const values = labels.map((l) => map[l]);
  if (riskChart) riskChart.destroy();
  riskChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: labels.map((l) => colors[l]) }],
    },
    options: { plugins: { legend: { labels: { color: "#1B2434" } } } },
  });
}

function renderRecentTable(rows) {
  const tbody = document.querySelector("#recent-table tbody");
  tbody.innerHTML = rows
    .map(
      (r) => `<tr>
        <td>${r.title}</td>
        <td>${rupees(r.total_cost)}</td>
        <td>${r.total_delay} days</td>
        <td>${riskPill(r.risk_level)}</td>
        <td>${statusPill(r.status)}</td>
        <td>${r.created_at}</td>
      </tr>`
    )
    .join("") || `<tr><td colspan="6">No revisions logged yet.</td></tr>`;
}

// ---------------- new revision ----------------
document.getElementById("revision-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    project_id: state.projectId,
    created_by: state.userId,
    title: document.getElementById("rev-title").value,
    description: document.getElementById("rev-desc").value,
    category: document.getElementById("rev-category").value || null,
    priority: document.getElementById("rev-priority").value,
  };

  const result = await api("/api/revisions", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  const grid = document.getElementById("analysis-grid");
  grid.innerHTML = `
    <div class="analysis-item"><span>Category</span><strong>${result.category}</strong></div>
    <div class="analysis-item"><span>Risk</span><strong>${result.risk_score}/100 — ${result.risk_level}</strong></div>
    <div class="analysis-item"><span>Affected Departments</span><strong>${result.affected_departments.join(", ")}</strong></div>
    <div class="analysis-item"><span>Affected Stakeholders</span><strong>${result.affected_stakeholders.join(", ")}</strong></div>
    <div class="analysis-item" style="grid-column: 1 / -1;"><span>Impact Summary</span><strong>${result.impact_summary}</strong></div>
    <div class="analysis-item"><span>Cost Impact</span><strong>${rupees(result.total_cost)}</strong></div>
    <div class="analysis-item"><span>Timeline Impact</span><strong>${result.total_delay} days</strong></div>
  `;
  document.getElementById("analysis-result").classList.remove("hidden");
  e.target.reset();
  document.getElementById("rev-priority").value = "Medium";
});

// ---------------- shared: load revision dropdowns (scoped to active project) ----------------
async function loadRevisionOptions(selectId) {
  const qs = state.projectId ? `?project_id=${state.projectId}` : "";
  const revisions = await api(`/api/revisions${qs}`);
  const select = document.getElementById(selectId);
  select.innerHTML = revisions
    .map((r) => `<option value="${r.id}">${r.title}</option>`)
    .join("") || `<option value="">No revisions yet — add one first</option>`;

  if (selectId === "impact-select") renderImpact();
  if (selectId === "ripple-select") renderRipple();
}

// ---------------- impact analysis ----------------
document.getElementById("impact-select").addEventListener("change", renderImpact);

async function renderImpact() {
  const id = document.getElementById("impact-select").value;
  const cards = document.getElementById("impact-cards");
  const approvalPanel = document.getElementById("approval-panel");
  if (!id) {
    cards.innerHTML = "";
    approvalPanel.classList.add("hidden");
    return;
  }

  const r = await api(`/api/revisions/${id}`);
  cards.innerHTML = `
    <div class="impact-card">
      <h4>Cost Impact</h4>
      <div class="big">${rupees(r.total_cost)}</div>
      <ul>
        <li>Material: ${rupees(r.material_cost)}</li>
        <li>Labor: ${rupees(r.labor_cost)}</li>
      </ul>
    </div>
    <div class="impact-card">
      <h4>Timeline Impact</h4>
      <div class="big">${r.total_delay} days</div>
      <ul>
        <li>Procurement delay: ${r.procurement_delay} days</li>
        <li>Installation delay: ${r.installation_delay} days</li>
      </ul>
    </div>
    <div class="impact-card">
      <h4>Risk Score</h4>
      <div class="big">${r.risk_score}/100 ${riskPill(r.risk_level)}</div>
    </div>
    <div class="impact-card">
      <h4>Affected Stakeholders</h4>
      <ul>${r.affected_stakeholders.split(",").map((s) => `<li>${s}</li>`).join("")}</ul>
    </div>
  `;

  document.getElementById("current-status").innerHTML = statusPill(r.status);
  approvalPanel.classList.remove("hidden");
  approvalPanel.dataset.revisionId = id;
}

document.querySelectorAll("#approval-panel [data-status]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const id = document.getElementById("approval-panel").dataset.revisionId;
    if (!id) return;
    await api(`/api/revisions/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: btn.dataset.status }),
    });
    renderImpact();
  });
});

// ---------------- ripple effect (interactive SVG graph) ----------------
document.getElementById("ripple-select").addEventListener("change", renderRipple);

async function renderRipple() {
  const id = document.getElementById("ripple-select").value;
  const container = document.getElementById("ripple-graph");
  if (!id) { container.innerHTML = ""; return; }

  const r = await api(`/api/revisions/${id}/ripple`);
  drawRippleGraph(container, r.graph);
}

function drawRippleGraph(container, graph) {
  const { nodes, edges } = graph;

  // Layout: group nodes by column, space them evenly down each column.
  const columns = {};
  nodes.forEach((n) => {
    columns[n.column] = columns[n.column] || [];
    columns[n.column].push(n);
  });
  const columnKeys = Object.keys(columns).map(Number).sort((a, b) => a - b);

  const colWidth = 230;
  const nodeHeight = 56;
  const nodeWidth = 190;
  const rowGap = 26;
  const maxRows = Math.max(...columnKeys.map((c) => columns[c].length));
  const svgHeight = Math.max(220, maxRows * (nodeHeight + rowGap) + rowGap);
  const svgWidth = columnKeys.length * colWidth + 40;

  const pos = {};
  columnKeys.forEach((col) => {
    const list = columns[col];
    const totalHeight = list.length * nodeHeight + (list.length - 1) * rowGap;
    const startY = (svgHeight - totalHeight) / 2;
    list.forEach((n, i) => {
      pos[n.id] = {
        x: 20 + col * colWidth,
        y: startY + i * (nodeHeight + rowGap),
      };
    });
  });

  const edgePath = (from, to) => {
    const x1 = pos[from].x + nodeWidth;
    const y1 = pos[from].y + nodeHeight / 2;
    const x2 = pos[to].x;
    const y2 = pos[to].y + nodeHeight / 2;
    const midX = (x1 + x2) / 2;
    return `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`;
  };

  const edgesSvg = edges
    .map(
      (e, i) =>
        `<path class="rg-edge" id="edge-${i}" data-from="${e.from}" data-to="${e.to}" d="${edgePath(e.from, e.to)}" />`
    )
    .join("");

  const nodesSvg = nodes
    .map((n) => {
      const p = pos[n.id];
      const label = n.label.length > 26 ? n.label.slice(0, 24) + "…" : n.label;
      return `
        <g class="rg-node" id="node-${n.id}" data-id="${n.id}" transform="translate(${p.x},${p.y})">
          <rect class="rg-node-box ${n.type}" width="${nodeWidth}" height="${nodeHeight}" rx="2"></rect>
          <text class="rg-node-label" x="14" y="${nodeHeight / 2 + 5}">
            <title>${n.label}</title>${label}
          </text>
        </g>`;
    })
    .join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${svgWidth} ${svgHeight}" width="${svgWidth}" height="${svgHeight}" xmlns="http://www.w3.org/2000/svg">
      ${edgesSvg}
      ${nodesSvg}
    </svg>`;

  // Interactivity: hovering/tapping a node highlights every edge and node
  // reachable downstream from it, so you can trace one branch of the ripple.
  const svg = container.querySelector("svg");
  const downstream = (startId) => {
    const visitedNodes = new Set([startId]);
    const visitedEdges = new Set();
    let changed = true;
    while (changed) {
      changed = false;
      edges.forEach((e, i) => {
        if (visitedNodes.has(e.from) && !visitedEdges.has(i)) {
          visitedEdges.add(i);
          if (!visitedNodes.has(e.to)) {
            visitedNodes.add(e.to);
            changed = true;
          }
        }
      });
    }
    return { visitedNodes, visitedEdges };
  };

  svg.querySelectorAll(".rg-node").forEach((el) => {
    const id = el.dataset.id;
    const highlight = () => {
      const { visitedNodes, visitedEdges } = downstream(id);
      svg.querySelectorAll(".rg-node").forEach((n) =>
        n.classList.toggle("lit", visitedNodes.has(n.dataset.id))
      );
      svg.querySelectorAll(".rg-edge").forEach((edgeEl, i) =>
        edgeEl.classList.toggle("lit", visitedEdges.has(i))
      );
    };
    const clear = () => {
      svg.querySelectorAll(".rg-node").forEach((n) => n.classList.remove("lit"));
      svg.querySelectorAll(".rg-edge").forEach((e) => e.classList.remove("lit"));
    };
    el.addEventListener("mouseenter", highlight);
    el.addEventListener("mouseleave", clear);
    el.addEventListener("click", highlight);
  });
}

// ---------------- what-if simulator ----------------
document.getElementById("sim-run").addEventListener("click", async () => {
  const readForm = (formId) => {
    const form = document.getElementById(formId);
    return {
      title: form.querySelector(".sim-title").value,
      description: form.querySelector(".sim-desc").value,
      priority: form.querySelector(".sim-priority").value,
    };
  };

  const optionA = readForm("sim-form-a");
  const optionB = readForm("sim-form-b");

  if (!optionA.title || !optionA.description || !optionB.title || !optionB.description) {
    alert("Fill in both options before comparing.");
    return;
  }

  const result = await api("/api/simulate", {
    method: "POST",
    body: JSON.stringify({ options: [optionA, optionB] }),
  });

  const [a, b] = result.options;
  document.getElementById("sim-head-a").textContent = a.title;
  document.getElementById("sim-head-b").textContent = b.title;

  const rows = [
    ["Category", a.category, b.category],
    ["Cost", rupees(a.total_cost), rupees(b.total_cost)],
    ["Delay", `${a.total_delay} days`, `${b.total_delay} days`],
    ["Risk", `${a.risk_score}/100 ${riskPill(a.risk_level)}`, `${b.risk_score}/100 ${riskPill(b.risk_level)}`],
    ["Affected Departments", a.affected_departments.join(", "), b.affected_departments.join(", ")],
  ];

  document.querySelector("#sim-table tbody").innerHTML = rows
    .map((row) => `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td></tr>`)
    .join("");

  document.getElementById("sim-result").classList.remove("hidden");
});

// ---------------- boot ----------------
(async function init() {
  await loadProjects();
  await loadUsers();
  await loadDashboard();
})();
