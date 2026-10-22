/* JAYHIND TalentHub - small UI helpers (vanilla JS + Fetch API) */
(function () {
  "use strict";
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;

  // Mobile sidebar
  document.getElementById("sidebarToggle")?.addEventListener("click", () => document.getElementById("sidebar").classList.toggle("open"));
  document.addEventListener("click", (e) => {
    const sb = document.getElementById("sidebar");
    if (sb?.classList.contains("open") && !sb.contains(e.target) && !e.target.closest("#sidebarToggle")) sb.classList.remove("open");
  });

  // Auto-dismiss flash messages
  document.querySelectorAll(".toast-zone .alert").forEach((el) => setTimeout(() => bootstrap.Alert.getOrCreateInstance(el).close(), 6500));

  // Confirm dialogs + loading state on submit
  document.addEventListener("submit", (e) => {
    const form = e.target;
    const msg = form.dataset.confirm;
    if (msg && !window.confirm(msg)) { e.preventDefault(); return; }
    const btn = e.submitter || form.querySelector("[data-loading]");
    if (btn && btn.dataset.loading !== undefined && form.checkValidity()) {
      setTimeout(() => { btn.classList.add("btn-loading"); if (btn.dataset.loading) btn.dataset.original = btn.textContent, btn.textContent = btn.dataset.loading; }, 0);
    }
  });

  // Select-all for bulk tables
  document.querySelectorAll("[data-select-all]").forEach((master) => {
    master.addEventListener("change", () => document.querySelectorAll(master.dataset.selectAll).forEach((c) => (c.checked = master.checked)));
  });

  // Prefill modal fields from the clicked button (data-fill-*)
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-fill-target]");
    if (!btn) return;
    const modal = document.querySelector(btn.dataset.fillTarget);
    Object.entries(btn.dataset).forEach(([k, v]) => {
      if (!k.startsWith("fill") || k === "fillTarget") return;
      const el = modal.querySelector(`[data-slot="${k.slice(4).toLowerCase()}"]`);
      if (!el) return;
      if (el.tagName === "FORM") el.action = v; else if (el.tagName === "INPUT") el.value = v; else el.textContent = v;
    });
  });

  // Notifications: mark as read with fetch, refresh badge periodically
  function setBadge(n) {
    const dot = document.getElementById("notifDot");
    if (!dot) return;
    dot.textContent = n; dot.classList.toggle("d-none", !n);
  }
  document.querySelectorAll("[data-read-url]").forEach((el) => el.addEventListener("click", () => {
    fetch(el.dataset.readUrl, { method: "POST", headers: { "X-CSRFToken": csrf } }).then((r) => r.json()).then((d) => {
      setBadge(d.unread); el.closest(".note")?.classList.remove("unread");
    });
  }));
  if (document.getElementById("notifDot")) {
    setInterval(() => fetch("/notifications/count").then((r) => r.json()).then((d) => setBadge(d.unread)).catch(() => {}), 60000);
  }

  // "Why this match?" dialog
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-match-url]");
    if (!btn) return;
    const body = document.getElementById("matchBody");
    body.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-secondary"></div></div>';
    bootstrap.Modal.getOrCreateInstance(document.getElementById("matchModal")).show();
    fetch(btn.dataset.matchUrl).then((r) => r.json()).then((d) => {
      const names = { skill: "Skill match", education: "Education match", preference: "Career preference", location: "Location preference", experience: "Experience match" };
      const rows = Object.entries(d.components).map(([k, c]) => `
        <div class="mb-3"><div class="d-flex justify-content-between small fw-semibold"><span>${names[k]} <span class="text-muted">(weight ${c.weight}%)</span></span><span>${c.score}% &rarr; ${c.points} pts</span></div>
        <div class="progress mt-1"><div class="progress-bar ${c.score >= 70 ? "bg-green" : c.score >= 40 ? "bg-accent" : "bg-danger"}" style="width:${c.score}%"></div></div></div>`).join("");
      const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
      body.innerHTML = `<div class="d-flex align-items-center gap-3 mb-3"><div class="ring" style="--p:${d.score}; --size:70px"><span>${d.score}%</span></div>
        <div><div class="fw-bold">${esc(d.label)}</div><div class="small text-muted">${esc(d.explanation)}</div></div></div>${rows}
        <div class="small text-muted mt-2">Matched skills: ${d.skills.matched.map(esc).join(", ") || "none"}<br>Missing: ${d.skills.missing.map(esc).join(", ") || "none"}<br>TF-IDF cosine similarity: ${d.skills.cosine}</div>`;
    }).catch(() => (body.innerHTML = '<div class="text-danger">Could not load the match details.</div>'));
  });

  // Chart.js helper
  const PALETTE = ["#16a34a", "#f28a17", "#0f766e", "#84cc16", "#fb923c", "#22c55e", "#ca8a04", "#64748b"];
  window.TH = {
    chart(id, type, labels, data, opts = {}) {
      const el = document.getElementById(id);
      if (!el || !window.Chart) return;
      if (!data.length || data.every((v) => !v)) {
        el.parentElement.innerHTML = '<div class="empty py-4"><i class="bi bi-bar-chart"></i>No data yet</div>'; return;
      }
      const round = type === "doughnut" || type === "pie";
      new Chart(el, {
        type, data: { labels, datasets: [{ label: opts.label || "", data, backgroundColor: round || opts.multi ? PALETTE : (opts.color || PALETTE[0]),
          borderColor: type === "line" ? (opts.color || PALETTE[1]) : "#fff", borderWidth: type === "line" ? 3 : round ? 2 : 0,
          borderRadius: type === "bar" ? 6 : 0, fill: type === "line", tension: .35, pointRadius: type === "line" ? 4 : 0,
          backgroundColor: type === "line" ? "rgba(242,138,23,.12)" : (round || opts.multi ? PALETTE : (opts.color || PALETTE[0])) }] },
        options: { responsive: true, maintainAspectRatio: false, indexAxis: opts.horizontal ? "y" : "x",
          plugins: { legend: { display: round, position: "bottom", labels: { boxWidth: 10, usePointStyle: true } } },
          scales: round ? {} : { y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#eef0f8" } }, x: { grid: { display: false } } } },
      });
    },
  };
})();
