const PAGE_CONFIG = {
  overview: {
    title: "Overview",
    eyebrow: "Local command center",
    subtitle: "Offline shell for chat, runs, models, memory, logs, context, ops, and health.",
    limits: { runs: 6, memory: 6, snippet: 6, log: 8 },
  },
  chat: {
    title: "Chat",
    eyebrow: "Conversation view",
    subtitle: "Talk to the session, confirm actions, and inspect the last turn.",
    limits: { runs: 4, memory: 6, snippet: 5, log: 6 },
  },
  runs: {
    title: "Runs",
    eyebrow: "Training history",
    subtitle: "Inspect recent checkpoints and compare metrics.",
    limits: { runs: 24, memory: 4, snippet: 4, log: 4 },
  },
  models: {
    title: "Models",
    eyebrow: "Registry and active model",
    subtitle: "See the local model registry and active version.",
    limits: { runs: 6, memory: 4, snippet: 4, log: 4 },
  },
  memory: {
    title: "Memory",
    eyebrow: "Local memory store",
    subtitle: "Search conversation summaries and recent memory entries.",
    limits: { runs: 4, memory: 16, snippet: 6, log: 4 },
  },
  context: {
    title: "Context",
    eyebrow: "Prompt context",
    subtitle: "Review the assembled runtime context and retrieval snippets.",
    limits: { runs: 4, memory: 12, snippet: 10, log: 4 },
  },
  logs: {
    title: "Logs",
    eyebrow: "Audit trail",
    subtitle: "Inspect the action audit JSONL, errors log, and legacy action log.",
    limits: { runs: 4, memory: 4, snippet: 4, log: 24 },
  },
  ops: {
    title: "Ops",
    eyebrow: "Local commands",
    subtitle: "Copy the training, export, and quantization commands.",
    limits: { runs: 4, memory: 4, snippet: 4, log: 4 },
  },
  health: {
    title: "Health",
    eyebrow: "Runtime telemetry",
    subtitle: "CPU pressure proxy, RAM usage, and model confidence summary.",
    limits: { runs: 4, memory: 4, snippet: 4, log: 4 },
  },
  notfound: {
    title: "Page not found",
    eyebrow: "Unknown route",
    subtitle: "That path is not one of the dashboard subpages.",
    limits: { runs: 4, memory: 4, snippet: 4, log: 4 },
  },
};

const ROUTE_ALIASES = {
  "": "overview",
  "/": "overview",
  "/index.html": "overview",
  "/overview.html": "overview",
  "/chat.html": "chat",
  "/runs.html": "runs",
  "/models.html": "models",
  "/memory.html": "memory",
  "/context.html": "context",
  "/logs.html": "logs",
  "/ops.html": "ops",
  "/health.html": "health",
  overview: "overview",
  chat: "chat",
  runs: "runs",
  models: "models",
  memory: "memory",
  context: "context",
  logs: "logs",
  ops: "ops",
  health: "health",
};

const QUICK_LINKS = [
  { route: "chat", label: "Chat", icon: "chat", description: "Conversation history and confirmation flow." },
  { route: "runs", label: "Runs", icon: "runs", description: "Training summaries and checkpoint metrics." },
  { route: "models", label: "Models", icon: "models", description: "Registry entries and the active checkpoint." },
  { route: "memory", label: "Memory", icon: "memory", description: "Recent memories and search results." },
  { route: "context", label: "Context", icon: "context", description: "Assembled prompt context and snippets." },
  { route: "logs", label: "Logs", icon: "logs", description: "Audit trail, error tail, and legacy log." },
  { route: "ops", label: "Ops", icon: "ops", description: "Local commands for training and export." },
  { route: "health", label: "Health", icon: "spark", description: "CPU, RAM, and model confidence telemetry." },
];

const routeMetaEl = document.getElementById("route-meta");
const viewEl = document.getElementById("view");
const globalSearchForm = document.getElementById("global-search");
const globalQueryInput = document.getElementById("global-query");

let currentRoute = normalizeRoute(window.location.pathname);
let currentQuery = new URLSearchParams(window.location.search).get("q")?.trim() || "";
let activeLoadToken = 0;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    switch (char) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      case "'":
        return "&#39;";
      default:
        return char;
    }
  });
}

function icon(name) {
  return `<svg class="icon" aria-hidden="true"><use href="/assets/icons.svg#${escapeHtml(name)}"></use></svg>`;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function formatNumber(value, digits = 0) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "0";
  }
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(number);
}

function formatMetric(value, digits = 4) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "n/a";
  }
  return number.toFixed(digits);
}

function formatTimestamp(raw) {
  const text = String(raw ?? "").trim();
  if (!text) {
    return "Unknown";
  }
  if (/^\d{8}_\d{6}$/.test(text)) {
    return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)} ${text.slice(9, 11)}:${text.slice(11, 13)}:${text.slice(13, 15)}`;
  }
  const parsed = Date.parse(text);
  if (!Number.isNaN(parsed)) {
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(parsed));
  }
  return text;
}

function truncate(text, limit = 80) {
  const value = String(text ?? "").trim();
  if (value.length <= limit) {
    return value;
  }
  return `${value.slice(0, Math.max(limit - 1, 1)).trimEnd()}…`;
}

function preBlock(text) {
  return `<pre class="pre">${escapeHtml(text || "(empty)")}</pre>`;
}

function jsonBlock(value) {
  return `<pre class="pre">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
}

function chip(label, tone = "ghost", iconName = "") {
  return `<span class="chip chip--${escapeHtml(tone)}">${iconName ? icon(iconName) : ""}${escapeHtml(label)}</span>`;
}

function statCard({ label, value, detail = "", tone = "brand" }) {
  return `
    <article class="stat stat--${escapeHtml(tone)}">
      <p class="stat__label">${escapeHtml(label)}</p>
      <p class="stat__value">${escapeHtml(value)}</p>
      ${detail ? `<p class="stat__detail">${escapeHtml(detail)}</p>` : ""}
    </article>
  `;
}

function infoCard(label, value) {
  return `
    <div class="info">
      <p class="info__label">${escapeHtml(label)}</p>
      <p class="info__value">${value}</p>
    </div>
  `;
}

function sectionCard(title, subtitle, body, footer = "", extraClass = "") {
  return `
    <article class="card ${escapeHtml(extraClass)}">
      <div class="card__header">
        <div>
          <h2 class="card__title">${escapeHtml(title)}</h2>
          ${subtitle ? `<p class="card__subtitle">${escapeHtml(subtitle)}</p>` : ""}
        </div>
      </div>
      <div class="card__body">${body}</div>
      ${footer ? `<div class="card__footer">${footer}</div>` : ""}
    </article>
  `;
}

function cardLink({ route, label, icon: iconName, description }) {
  return `
    <a class="command" href="/${escapeHtml(route)}" data-nav="${escapeHtml(route)}">
      <div class="command__head">
        <h3 class="command__title">${icon(iconName)} ${escapeHtml(label)}</h3>
        <span class="badge badge--ghost">Open</span>
      </div>
      <p class="command__body">${escapeHtml(description)}</p>
    </a>
  `;
}

function renderList(items, renderItem, emptyMessage) {
  const list = arrayValue(items);
  if (!list.length) {
    return `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
  }
  return `<div class="list">${list.map(renderItem).join("")}</div>`;
}

function renderBubbles(turns) {
  const list = arrayValue(turns);
  if (!list.length) {
    return `<div class="empty-state">No turns yet. Start a conversation to populate the transcript.</div>`;
  }
  return `
    <div class="bubble-list">
      ${list
        .map((turn) => {
          const role = String(turn?.role || "assistant");
          const message = String(turn?.message || "");
          const roleLabel = role === "user" ? "You" : role.charAt(0).toUpperCase() + role.slice(1);
          return `
            <div class="bubble bubble--${role === "user" ? "user" : "assistant"}">
              <div class="bubble__meta">
                <span>${escapeHtml(roleLabel)}</span>
                <span>${icon(role === "user" ? "chat" : "spark")}</span>
              </div>
              <div class="bubble__body">${escapeHtml(message)}</div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderTable(headers, rows) {
  if (!rows.length) {
    return `<div class="empty-state">No rows available yet.</div>`;
  }
  return `
    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr>
        </thead>
        <tbody>${rows.join("")}</tbody>
      </table>
    </div>
  `;
}

function safeState(state) {
  const data = objectValue(state);
  return {
    service: objectValue(data.service),
    query: String(data.query || ""),
    session: objectValue(data.session),
    context: objectValue(data.context),
    memory: objectValue(data.memory),
    runs: objectValue(data.runs),
    models: objectValue(data.models),
    logs: objectValue(data.logs),
    ops: objectValue(data.ops),
    health: objectValue(data.health),
  };
}

function normalizeRoute(pathname) {
  const raw = String(pathname || "/").replace(/\/+$/, "") || "/";
  const alias = ROUTE_ALIASES[raw] || ROUTE_ALIASES[raw.replace(/^\//, "")];
  if (alias && PAGE_CONFIG[alias]) {
    return alias;
  }
  return PAGE_CONFIG[raw.replace(/^\//, "")] ? raw.replace(/^\//, "") : "notfound";
}

function pageConfig(route) {
  return PAGE_CONFIG[route] || PAGE_CONFIG.notfound;
}

function pageLimits(route) {
  return pageConfig(route).limits;
}

function buildStateUrl(route, query) {
  const limits = pageLimits(route);
  const params = new URLSearchParams();
  if (query) {
    params.set("query", query);
  }
  params.set("runs_limit", String(limits.runs));
  params.set("memory_limit", String(limits.memory));
  params.set("snippet_limit", String(limits.snippet));
  params.set("log_limit", String(limits.log));
  return `/api/state?${params.toString()}`;
}

function setNavActive(route) {
  document.querySelectorAll("[data-nav]").forEach((anchor) => {
    const active = anchor.dataset.nav === route;
    anchor.classList.toggle("is-active", active);
    if (active) {
      anchor.setAttribute("aria-current", "page");
    } else {
      anchor.removeAttribute("aria-current");
    }
  });
}

function setDocumentTitle(route) {
  document.title = `${pageConfig(route).title} | AI Lan`;
}

function setGlobalQueryInput(value) {
  if (globalQueryInput) {
    globalQueryInput.value = value || "";
  }
}

function setStatus(text) {
  const statusChip = document.querySelector('[data-role="status-chip"]');
  if (statusChip) {
    statusChip.textContent = text;
  }
}

function hero(route, state, query) {
  const cfg = pageConfig(route);
  const { session, memory, runs, models, logs, ops, context, health } = safeState(state);
  const queryText = query || state.query || "";
  const chips = [chip("Local only", "good", "check")];

  chips.push(queryText ? chip(`Query: ${truncate(queryText, 40)}`, "brand", "search") : chip("Query: none", "ghost", "search"));

  switch (route) {
    case "overview":
      chips.push(chip(`${formatNumber(session.turn_count || 0)} turns`, "brand", "chat"));
      chips.push(chip(`${formatNumber(runs.visible_run_count || 0)} runs`, "accent", "runs"));
      chips.push(chip(`${formatNumber(models.record_count || 0)} models`, "ghost", "models"));
      chips.push(chip(`${formatNumber(memory.recent_count || 0)} memories`, "ghost", "memory"));
      break;
    case "chat":
      chips.push(chip(session.pending_confirmation ? "Pending confirmation" : "No pending action", session.pending_confirmation ? "danger" : "good", session.pending_confirmation ? "alert" : "check"));
      chips.push(chip(`${formatNumber(session.turn_count || 0)} turns`, "brand", "chat"));
      if (session.last_result && typeof session.last_result === "object") {
        chips.push(chip(`Last: ${truncate(String(session.last_result.status || "unknown"), 24)}`, "ghost", "spark"));
      }
      break;
    case "runs":
      chips.push(chip(`${formatNumber(runs.project_run_count || 0)} project runs`, "good", "runs"));
      chips.push(chip(`${formatNumber(runs.all_run_count || 0)} total runs`, "brand", "runs"));
      if (runs.best_run) {
        chips.push(chip(`Best loss: ${formatMetric(runs.best_run.best_val_loss)}`, "accent", "spark"));
      }
      break;
    case "models":
      chips.push(chip(`${formatNumber(models.record_count || 0)} records`, "brand", "models"));
      chips.push(chip(models.active?.active_version ? `Active: ${models.active.active_version}` : "No active model", models.active?.active_version ? "good" : "ghost", "models"));
      break;
    case "memory":
      chips.push(chip(`${formatNumber(memory.recent_count || 0)} recent`, "brand", "memory"));
      chips.push(chip(`${formatNumber(memory.query_hit_count || 0)} hits`, "accent", "search"));
      break;
    case "context":
      chips.push(chip(`${formatNumber(arrayValue(context.retrieval?.memory_hits).length)} memory hits`, "brand", "memory"));
      chips.push(chip(`${formatNumber(arrayValue(context.retrieval?.corpus_snippets).length)} snippets`, "accent", "context"));
      break;
    case "logs":
      chips.push(chip(`${formatNumber(arrayValue(logs.audit_entries).length)} audit entries`, "brand", "logs"));
      chips.push(chip(`${formatNumber(arrayValue(logs.error_lines).length)} error lines`, "danger", "alert"));
      break;
    case "ops":
      chips.push(chip(`${formatNumber(arrayValue(ops.commands).length)} commands`, "brand", "ops"));
      chips.push(chip(`${formatNumber(Object.keys(objectValue(ops.paths)).length)} paths`, "ghost", "file"));
      break;
    case "health":
      chips.push(chip(`${escapeHtml(String(health.cpu?.thermal_proxy_band || "unknown"))} cpu`, "brand", "spark"));
      chips.push(chip(`${formatNumber(Number(health.memory?.usage_percent || 0), 1)}% ram`, "accent", "memory"));
      chips.push(chip(`${escapeHtml(String(health.model_confidence?.confidence_band || "unknown"))} confidence`, "ghost", "models"));
      break;
    default:
      chips.push(chip("Subpage not found", "danger", "alert"));
      break;
  }

  return `
    <section class="hero">
      <div>
        <p class="hero__eyebrow">${escapeHtml(cfg.eyebrow)}</p>
        <h1 class="hero__title">${escapeHtml(cfg.title)}</h1>
        <p class="hero__subtitle">${escapeHtml(cfg.subtitle)}</p>
      </div>
      <div class="hero__chips">
        ${chips.join("")}
        <span class="chip chip--ghost" data-role="status-chip">Loading...</span>
      </div>
    </section>
  `;
}

function renderOverview(state) {
  const { session, context, memory, runs, models, logs } = safeState(state);
  const turns = arrayValue(session.turns).slice(-8);
  const recentMemories = arrayValue(memory.recent).slice(0, 4);
  const auditEntries = arrayValue(logs.audit_entries).slice(0, 3);
  const bestRun = runs.best_run || runs.visible_runs?.[0] || null;
  const activeModel = models.active?.record || null;
  const latestMemory = recentMemories[0] || null;
  const latestAudit = auditEntries[0] || null;

  return `
    <div class="stack">
      <section class="section">
        <div class="stat-grid">
          ${statCard({ label: "Turns", value: formatNumber(session.turn_count || 0), detail: session.pending_confirmation ? "Waiting on confirmation" : "No confirmation pending", tone: session.pending_confirmation ? "danger" : "good" })}
          ${statCard({ label: "Runs", value: formatNumber(runs.visible_run_count || 0), detail: `${formatNumber(runs.all_run_count || 0)} total on disk`, tone: "brand" })}
          ${statCard({ label: "Models", value: formatNumber(models.record_count || 0), detail: models.active?.active_version ? `Active ${models.active.active_version}` : "No active model", tone: "accent" })}
          ${statCard({ label: "Memory", value: formatNumber(memory.recent_count || 0), detail: memory.db_path || "No memory database", tone: "good" })}
          ${statCard({ label: "Logs", value: formatNumber(auditEntries.length), detail: logs.audit_path || "No audit path", tone: "ghost" })}
          ${statCard({ label: "Context Hits", value: formatNumber(arrayValue(context.retrieval?.memory_hits).length), detail: `${formatNumber(arrayValue(context.retrieval?.corpus_snippets).length)} corpus snippets`, tone: "brand" })}
        </div>
      </section>

      <section class="grid grid--wide">
        ${sectionCard("Recent turns", "Latest conversation turns from the local session.", renderBubbles(turns))}
        ${sectionCard("Subpages", "Jump straight into the section you need.", `<div class="command-grid">${QUICK_LINKS.map(cardLink).join("")}</div>`)}
      </section>

      <section class="grid grid--2">
        ${sectionCard("Context snapshot", "The assembled runtime context used by the session.", preBlock(context.assembled_context || "No context available yet."))}
        ${sectionCard(
          "Artifacts and storage",
          "Saved files, active model, and the latest state snapshots.",
          `
            <div class="info-grid">
              ${infoCard("Run index", escapeHtml(runs.index_path || "Unknown"))}
              ${infoCard("All runs index", escapeHtml(runs.all_index_path || "Unknown"))}
              ${infoCard("Registry", escapeHtml(models.registry_path || "Unknown"))}
              ${infoCard("Memory DB", escapeHtml(memory.db_path || "Unknown"))}
              ${infoCard("Corpus", escapeHtml(session.merged_corpus_path || "Unknown"))}
              ${infoCard("Active model", activeModel ? escapeHtml(activeModel.version || "Unknown") : "No active model")}
            </div>
            <div class="section">
              <div class="grid grid--2">
                ${sectionCard(
                  "Best run",
                  bestRun ? formatTimestamp(bestRun.timestamp) : "No run",
                  bestRun
                    ? `<div class="info-grid">${infoCard("Model", escapeHtml(bestRun.model_type || "Unknown"))}${infoCard("Best loss", escapeHtml(formatMetric(bestRun.best_val_loss)))}${infoCard("Best perplexity", escapeHtml(formatMetric(bestRun.best_val_perplexity)))}${infoCard("Train tokens", escapeHtml(formatNumber(bestRun.train_token_count || 0)))}</div>`
                    : `<div class="empty-state">No runs available yet.</div>`,
                )}
                ${sectionCard(
                  "Latest memory",
                  latestMemory ? `${escapeHtml(latestMemory.kind || "memory")} · ${formatTimestamp(latestMemory.created_at)}` : "No memory entries",
                  latestMemory
                    ? `<p class="timeline-item__body">${escapeHtml(latestMemory.summary || "")}</p>${latestMemory.metadata && Object.keys(latestMemory.metadata).length ? jsonBlock(latestMemory.metadata) : ""}`
                    : `<div class="empty-state">No memory entries have been stored yet.</div>`,
                )}
              </div>
            </div>
            <div class="section">
              <div class="grid grid--2">
                ${sectionCard(
                  "Active model",
                  activeModel ? `${escapeHtml(activeModel.version || "Unknown")} · ${escapeHtml(formatTimestamp(activeModel.created_at))}` : "No active model",
                  activeModel
                    ? `<p class="timeline-item__body">${escapeHtml(activeModel.model_path || "Unknown path")}</p>${activeModel.metrics && Object.keys(activeModel.metrics).length ? jsonBlock(activeModel.metrics) : ""}${activeModel.tags && activeModel.tags.length ? `<div class="hero__chips">${activeModel.tags.map((tag) => chip(tag, "ghost", "spark")).join("")}</div>` : ""}${activeModel.notes ? `<p class="timeline-item__body">${escapeHtml(activeModel.notes)}</p>` : ""}`
                    : `<div class="empty-state">No active model record is available.</div>`,
                )}
                ${sectionCard(
                  "Latest audit",
                  latestAudit ? `${escapeHtml(String(latestAudit?.request?.action || "unknown"))} · ${escapeHtml(String(latestAudit?.result?.status || "unknown"))}` : "No audit entries",
                  latestAudit
                    ? `<div class="info-grid">${infoCard("Timestamp", escapeHtml(formatTimestamp(latestAudit.timestamp)))}${infoCard("Policy", escapeHtml(String(latestAudit?.result?.policy_reason || "unknown")))}${infoCard("Action", escapeHtml(String(latestAudit?.request?.action || "unknown")))}${infoCard("Result", escapeHtml(String(latestAudit?.result?.status || "unknown")))}</div>`
                    : `<div class="empty-state">No audit entries have been recorded yet.</div>`,
                )}
              </div>
            </div>
          `,
        )}
      </section>
    </div>
  `;
}

function renderChat(state) {
  const { session } = safeState(state);
  const turns = arrayValue(session.turns);
  const pendingPayload = String(session.pending_payload_json || "");
  const lastResult = session.last_result_json || "No result yet.";
  const lastContext = session.last_context_json || "No context yet.";
  const shortTerm = session.short_term_context || "No short-term context.";
  const pendingPayloadBody = safeJsonBlock(pendingPayload, "No pending payload.");

  return `
    <section class="grid grid--chat">
      <article class="card card--raised">
        <div class="card__header">
          <div>
            <h2 class="card__title">Conversation</h2>
            <p class="card__subtitle">The live turn transcript, including assistant replies and confirmation prompts.</p>
          </div>
          <div class="toolbar">
            <button type="button" class="btn btn--small btn--ghost" data-action="refresh-chat">
              ${icon("refresh")}
              <span>Refresh</span>
            </button>
          </div>
        </div>
        <div class="card__body">
          <div class="bubble-list" data-role="chat-log">${renderBubbles(turns)}</div>
        </div>
        <div class="card__footer">
          <form class="composer" data-role="chat-form">
            <div class="composer__row">
              <input class="input" data-role="chat-input" placeholder="Type a message, /help, /confirm, or /reject" aria-label="Chat message" />
              <button class="btn btn--green" type="submit">${icon("send")}<span>Send</span></button>
              <button class="btn btn--amber" type="button" data-action="confirm">${icon("check")}<span>Confirm</span></button>
            </div>
            <div class="btn-group">
              <button class="btn btn--red btn--small" type="button" data-action="reject">${icon("close")}<span>Reject</span></button>
              <button class="btn btn--ghost btn--small" type="button" data-action="last">${icon("spark")}<span>Last result</span></button>
              <button class="btn btn--ghost btn--small" type="button" data-action="context">${icon("context")}<span>History</span></button>
            </div>
          </form>
        </div>
      </article>

      <aside class="stack">
        ${sectionCard("Pending confirmation", session.pending_confirmation ? "Action waiting for confirmation" : "No pending action", `<p class="timeline-item__body">${escapeHtml(session.pending_user_text || "No pending user text.")}</p>${pendingPayloadBody}`)}
        ${sectionCard("Last result", "Most recent action response.", preBlock(lastResult))}
        ${sectionCard("Last context", "The context that informed the most recent action.", preBlock(lastContext))}
        ${sectionCard("Short-term buffer", "Current rolling conversation buffer.", preBlock(shortTerm))}
        ${sectionCard(
          "Quick commands",
          "Useful local commands for the chat shell.",
          `<div class="btn-group">${["/help", "/actions", "/history", "/last", "/save", "/load"].map((command) => `<button type="button" class="btn btn--ghost btn--small" data-chat-command="${escapeHtml(command)}">${icon("terminal")}<span>${escapeHtml(command)}</span></button>`).join("")}</div>`,
        )}
      </aside>
    </section>
  `;
}

function renderUnavailable(route) {
  return sectionCard(
    `${pageConfig(route).title} coming soon`,
    "This subpage will be filled in after the next patch.",
    `<div class="empty-state">The shell and chat page are already live. The remaining subpages will be populated with their own local panels in the next update.</div>`,
  );
}

function renderRoute(route, state, query) {
  switch (route) {
    case "overview":
      return renderOverview(state);
    case "chat":
      return renderChat(state);
    case "runs":
      return renderRuns(state);
    case "models":
      return renderModels(state);
    case "memory":
      return renderMemory(state, query);
    case "context":
      return renderContext(state, query);
    case "logs":
      return renderLogs(state);
    case "ops":
      return renderOps(state);
    case "health":
      return renderHealth(state);
    default:
      return renderNotFound(state, window.location.pathname);
  }
}

function renderShell(route, state, query) {
  const cfg = pageConfig(route);
  const { session, memory, runs, models, logs, ops } = safeState(state);
  const queryText = query || state.query || "";

  const summary = [
    infoCard("Page", escapeHtml(cfg.title)),
    infoCard("Query", escapeHtml(queryText || "none")),
    infoCard("Turns", escapeHtml(formatNumber(session.turn_count || 0))),
    infoCard("Runs", escapeHtml(formatNumber(runs.visible_run_count || 0))),
    infoCard("Models", escapeHtml(formatNumber(models.record_count || 0))),
    infoCard("Memories", escapeHtml(formatNumber(memory.recent_count || 0))),
    infoCard("Logs", escapeHtml(formatNumber(arrayValue(logs.audit_entries).length))),
    infoCard("Commands", escapeHtml(formatNumber(arrayValue(ops.commands).length))),
  ];

  routeMetaEl.innerHTML = hero(route, state, query) + `
    <section class="section">
      <div class="info-grid">
        ${summary.join("")}
      </div>
    </section>
  `;

  viewEl.innerHTML = renderRoute(route, state, query);
  setStatus("Ready");
}

function bindGlobalSearch() {
  if (!globalSearchForm || !globalQueryInput) {
    return;
  }
  globalSearchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = globalQueryInput.value.trim();
    const nextUrl = new URL(window.location.href);
    if (query) {
      nextUrl.searchParams.set("q", query);
    } else {
      nextUrl.searchParams.delete("q");
    }
    window.location.href = nextUrl.toString();
  });
}

function safeJsonBlock(value, fallback = "No data.") {
  if (value === null || value === undefined || value === "") {
    return `<div class="empty-state">${escapeHtml(fallback)}</div>`;
  }
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      if (parsed === null || parsed === undefined || parsed === "") {
        return `<div class="empty-state">${escapeHtml(fallback)}</div>`;
      }
      return jsonBlock(parsed);
    } catch {
      return preBlock(value);
    }
  }
  if (value === null || value === undefined || value === "") {
    return `<div class="empty-state">${escapeHtml(fallback)}</div>`;
  }
  return jsonBlock(value);
}

function renderRuns(state) {
  const { runs } = safeState(state);
  const visible = arrayValue(runs.visible_runs);
  const allRuns = arrayValue(runs.all_runs);
  const bestRun = runs.best_run || visible[0] || allRuns[0] || null;

  const buildRow = (run) => {
    const tags = [
      run.is_project_run ? chip("project", "good", "check") : chip("all", "ghost", "runs"),
      run.overfit_warning ? chip("warning", "danger", "alert") : chip("stable", "ghost", "check"),
    ].join(" ");
    return `
      <tr>
        <td>
          <div>${escapeHtml(formatTimestamp(run.timestamp))}</div>
          <div class="muted small">${escapeHtml(run.summary_file || "")}</div>
        </td>
        <td>
          <div>${escapeHtml(run.model_type || "Unknown")}</div>
          <div class="muted small">${tags}</div>
        </td>
        <td>${escapeHtml(formatMetric(run.best_val_loss))}</td>
        <td>${escapeHtml(formatMetric(run.best_val_perplexity))}</td>
        <td>${escapeHtml(formatMetric(run.final_val_loss))}</td>
        <td>
          <div>${escapeHtml(formatNumber(run.train_token_count || 0))} / ${escapeHtml(formatNumber(run.val_token_count || 0))}</div>
          <div class="muted small">${escapeHtml(run.data_path || "")}</div>
        </td>
        <td>
          <div>${escapeHtml(run.samples_file || "")}</div>
          ${run.overfit_warning ? `<div class="muted small">${escapeHtml(run.overfit_warning)}</div>` : ""}
        </td>
      </tr>
    `;
  };

  return `
    <div class="stack">
      <section class="section">
        <div class="stat-grid">
          ${statCard({ label: "Project runs", value: formatNumber(runs.project_run_count || 0), detail: "Runs whose data path points at the project input file.", tone: "good" })}
          ${statCard({ label: "Visible runs", value: formatNumber(runs.visible_run_count || 0), detail: "The runs shown by default in this dashboard.", tone: "brand" })}
          ${statCard({ label: "All runs", value: formatNumber(runs.all_run_count || 0), detail: "Every parsed summary file under the local runs directory.", tone: "accent" })}
          ${statCard({ label: "Best loss", value: bestRun ? formatMetric(bestRun.best_val_loss) : "n/a", detail: bestRun ? `${escapeHtml(formatTimestamp(bestRun.timestamp))} · ${escapeHtml(bestRun.model_type || "Unknown")}` : "No best run yet.", tone: "danger" })}
        </div>
      </section>

      <section class="grid grid--2">
        ${sectionCard(
          "Best run",
          bestRun ? `${escapeHtml(bestRun.summary_file || "")} · ${escapeHtml(formatTimestamp(bestRun.timestamp))}` : "No runs available",
          bestRun
            ? `<div class="info-grid">${infoCard("Model", escapeHtml(bestRun.model_type || "Unknown"))}${infoCard("Best loss", escapeHtml(formatMetric(bestRun.best_val_loss)))}${infoCard("Val perplexity", escapeHtml(formatMetric(bestRun.best_val_perplexity)))}${infoCard("Final train loss", escapeHtml(formatMetric(bestRun.final_train_loss)))}${infoCard("Final val loss", escapeHtml(formatMetric(bestRun.final_val_loss)))}${infoCard("Train tokens", escapeHtml(formatNumber(bestRun.train_token_count || 0)))}</div>${bestRun.overfit_warning ? `<div class="empty-state">${escapeHtml(bestRun.overfit_warning)}</div>` : ""}`
            : `<div class="empty-state">No training summaries were found in the runs directory.</div>`,
        )}
        ${sectionCard(
          "Run indexes",
          "Local JSON index files generated from the run summaries.",
          `<div class="info-grid">${infoCard("Project index", escapeHtml(runs.index_path || "Unknown"))}${infoCard("All index", escapeHtml(runs.all_index_path || "Unknown"))}${infoCard("Best file", escapeHtml(bestRun ? bestRun.summary_file || "" : "None"))}${infoCard("Samples file", escapeHtml(bestRun ? bestRun.samples_file || "" : "None"))}</div>`,
        )}
      </section>

      <section class="grid grid--2">
        ${sectionCard("Visible runs", "The default subset of run summaries surfaced by the dashboard.", renderTable(["Timestamp", "Model", "Best loss", "Best ppl", "Final val", "Tokens", "Files"], visible.map(buildRow)))}
        ${sectionCard("All runs", "Every parsed run summary available in the local workspace.", renderTable(["Timestamp", "Model", "Best loss", "Best ppl", "Final val", "Tokens", "Files"], allRuns.map(buildRow)))}
      </section>
    </div>
  `;
}

function renderModels(state) {
  const { models, ops } = safeState(state);
  const records = arrayValue(models.records);
  const active = models.active?.record || null;

  const recordRows = records.map((record) => {
    const metrics = record.metrics && typeof record.metrics === "object" ? Object.entries(record.metrics).map(([key, value]) => `${key}: ${value}`).join(", ") : "n/a";
    const tags = arrayValue(record.tags).length ? arrayValue(record.tags).join(", ") : "n/a";
    return `
      <tr>
        <td>${escapeHtml(record.version || "Unknown")}</td>
        <td>
          <div>${escapeHtml(record.model_path || "")}</div>
          ${models.active?.active_version === record.version ? `<div class="muted small">${chip("active", "good", "check")}</div>` : ""}
        </td>
        <td>${escapeHtml(formatTimestamp(record.created_at))}</td>
        <td>${escapeHtml(metrics)}</td>
        <td>${escapeHtml(tags)}</td>
        <td>${escapeHtml(record.notes || "")}</td>
      </tr>
    `;
  });

  return `
    <div class="stack">
      <section class="section">
        <div class="stat-grid">
          ${statCard({ label: "Records", value: formatNumber(models.record_count || 0), detail: "All known model registry records on disk.", tone: "brand" })}
          ${statCard({ label: "Active version", value: models.active?.active_version || "none", detail: active ? `Started ${formatTimestamp(active.created_at)}` : "No active model selected.", tone: active ? "good" : "danger" })}
          ${statCard({ label: "Registry path", value: models.registry_path || "Unknown", detail: "Local registry JSON used by the dashboard.", tone: "accent" })}
          ${statCard({ label: "Ops commands", value: formatNumber(arrayValue(ops.commands).length), detail: "Available training, export, and quantization commands.", tone: "ghost" })}
        </div>
      </section>

      <section class="grid grid--2">
        ${sectionCard(
          "Active model",
          active ? `${escapeHtml(active.version || "Unknown")} · ${escapeHtml(formatTimestamp(active.created_at))}` : "No active model",
          active
            ? `<div class="info-grid">${infoCard("Model path", escapeHtml(active.model_path || "Unknown"))}${infoCard("Created", escapeHtml(formatTimestamp(active.created_at)))}${infoCard("Metrics", escapeHtml(active.metrics && Object.keys(active.metrics).length ? Object.entries(active.metrics).map(([key, value]) => `${key}: ${value}`).join(", ") : "n/a"))}${infoCard("Tags", escapeHtml(arrayValue(active.tags).length ? arrayValue(active.tags).join(", ") : "n/a"))}</div>${active.notes ? `<p class="timeline-item__body">${escapeHtml(active.notes)}</p>` : ""}`
            : `<div class="empty-state">No active registry record is set yet.</div>`,
        )}
        ${sectionCard(
          "Registry path",
          "The JSON file used for model records.",
          `<div class="info-grid">${infoCard("Registry", escapeHtml(models.registry_path || "Unknown"))}${infoCard("Active version", escapeHtml(models.active?.active_version || "none"))}${infoCard("Total records", escapeHtml(formatNumber(models.record_count || 0)))}${infoCard("Best model", escapeHtml(ops.paths?.best_model_path || "Unknown"))}</div>`,
        )}
      </section>

      <section class="card">
        <div class="card__header">
          <div>
            <h2 class="card__title">Registry records</h2>
            <p class="card__subtitle">Each row is one local model checkpoint record.</p>
          </div>
        </div>
        <div class="card__body">
          ${renderTable(["Version", "Path", "Created", "Metrics", "Tags", "Notes"], recordRows)}
        </div>
      </section>
    </div>
  `;
}

function renderMemory(state, query) {
  const { memory, session } = safeState(state);
  const recent = arrayValue(memory.recent);
  const hits = arrayValue(memory.query_hits);
  const useHits = query ? hits : recent;

  function memoryItem(entry, isHit = false) {
    const metadata = entry.metadata && typeof entry.metadata === "object" ? entry.metadata : {};
    return `
      <div class="list-item">
        <div class="list-item__meta">
          <span>${chip(isHit ? `score ${formatMetric(entry.score, 3)}` : entry.kind || "memory", isHit ? "accent" : "ghost", isHit ? "spark" : "memory")}</span>
          <span>${escapeHtml(formatTimestamp(entry.created_at))}</span>
          <span>#${escapeHtml(entry.memory_id ?? "")}</span>
        </div>
        <h3 class="list-item__title">${escapeHtml(entry.summary || "")}</h3>
        ${Object.keys(metadata).length ? jsonBlock(metadata) : ""}
      </div>
    `;
  }

  return `
    <div class="stack">
      <section class="card">
        <div class="card__header">
          <div>
            <h2 class="card__title">Search memory</h2>
            <p class="card__subtitle">Search the local memory store and keep the query in the URL.</p>
          </div>
        </div>
        <div class="card__body">
          <form class="composer" data-role="memory-form">
            <div class="composer__row">
              <input class="input" data-role="memory-query" placeholder="Search for docs, safety, memory, or any other local topic" aria-label="Memory query" value="${escapeHtml(query)}" />
              <button class="btn btn--green" type="submit">${icon("search")}<span>Search</span></button>
              <button class="btn btn--ghost" type="button" data-action="memory-recent">${icon("refresh")}<span>Recent</span></button>
            </div>
          </form>
        </div>
      </section>

      <section class="stat-grid">
        ${statCard({ label: "Recent memories", value: formatNumber(memory.recent_count || 0), detail: "Most recent entries stored in the SQLite memory database.", tone: "brand" })}
        ${statCard({ label: "Query hits", value: formatNumber(memory.query_hit_count || 0), detail: query ? `Matches for ${truncate(query, 32)}` : "No query provided yet.", tone: "accent" })}
        ${statCard({ label: "Database", value: memory.db_path || "Unknown", detail: "The local memory store path.", tone: "good" })}
        ${statCard({ label: "Session turns", value: formatNumber(session.turn_count || 0), detail: "Conversation turns are also stored as conversation memories.", tone: "ghost" })}
      </section>

      <section class="grid grid--2">
        ${sectionCard(query ? "Query hits" : "Recent memories", query ? "Entries matching the current search query." : "Latest memory entries from the local store.", renderList(useHits, (entry) => memoryItem(entry, Boolean(query)), query ? `No memory matches were found for ${query}.` : "No memory entries are available yet."))}
        ${sectionCard("Storage paths", "Where the memory data and merged corpus live on disk.", `<div class="info-grid">${infoCard("Memory DB", escapeHtml(memory.db_path || "Unknown"))}${infoCard("Corpus", escapeHtml(session.merged_corpus_path || "Unknown"))}${infoCard("Recent count", escapeHtml(formatNumber(memory.recent_count || 0)))}${infoCard("Hit count", escapeHtml(formatNumber(memory.query_hit_count || 0)))}</div>`)}
      </section>

      <section class="card">
        <div class="card__header">
          <div>
            <h2 class="card__title">Recent memories</h2>
            <p class="card__subtitle">The latest memory entries, regardless of query.</p>
          </div>
        </div>
        <div class="card__body">
          ${renderList(recent, (entry) => memoryItem(entry, false), "No recent memories are available yet.")}
        </div>
      </section>
    </div>
  `;
}

function renderLogs(state) {
  const { logs } = safeState(state);
  const auditEntries = arrayValue(logs.audit_entries);
  const errorLines = arrayValue(logs.error_lines);
  const legacyLines = arrayValue(logs.legacy_action_lines);

  function auditCard(entry) {
    const request = objectValue(entry.request);
    const result = objectValue(entry.result);
    const action = String(request.action || "unknown");
    return `
      <div class="list-item">
        <div class="list-item__meta">
          <span>${chip(String(result.status || "unknown"), result.status === "executed" ? "good" : result.status === "rejected" ? "danger" : "ghost", "logs")}</span>
          <span>${escapeHtml(formatTimestamp(entry.timestamp))}</span>
          <span>${escapeHtml(String(result.policy_reason || "n/a"))}</span>
        </div>
        <h3 class="list-item__title">${escapeHtml(action)}</h3>
        <div class="list-item__body">
          <div class="info-grid">
            ${infoCard("Thought", escapeHtml(String(request.thought || "n/a")))}
            ${infoCard("Action", escapeHtml(action))}
            ${infoCard("Safety", escapeHtml(String(request.safety_level || "n/a")))}
            ${infoCard("Result", escapeHtml(String(result.status || "n/a")))}
          </div>
          ${Object.keys(request).length ? jsonBlock(request) : ""}
          ${Object.keys(result).length ? jsonBlock(result) : ""}
        </div>
      </div>
    `;
  }

  return `
    <div class="stack">
      <section class="stat-grid">
        ${statCard({ label: "Audit entries", value: formatNumber(auditEntries.length), detail: logs.audit_path || "No audit path set.", tone: "brand" })}
        ${statCard({ label: "Error lines", value: formatNumber(errorLines.length), detail: logs.error_path || "No error log path.", tone: "danger" })}
        ${statCard({ label: "Legacy actions", value: formatNumber(legacyLines.length), detail: logs.legacy_action_path || "No legacy action log path.", tone: "accent" })}
        ${statCard({ label: "Audit file", value: logs.audit_path || "Unknown", detail: "The local JSONL file backing the audit trail.", tone: "ghost" })}
      </section>

      <section class="grid grid--2">
        ${sectionCard("Audit trail", "Recent action audit entries from the local workspace.", renderList(auditEntries, auditCard, "No audit entries have been written yet."))}
        ${sectionCard("Error log", "The tail of the error log file, if any.", errorLines.length ? preBlock(errorLines.join("\n")) : `<div class="empty-state">No error log lines were found.</div>`)}
      </section>

      <section class="grid grid--2">
        ${sectionCard("Legacy action log", "Older action log entries kept for compatibility.", legacyLines.length ? preBlock(legacyLines.join("\n")) : `<div class="empty-state">No legacy action log lines were found.</div>`)}
        ${sectionCard("Log locations", "Where the dashboard reads the local logs from.", `<div class="info-grid">${infoCard("Audit path", escapeHtml(logs.audit_path || "Unknown"))}${infoCard("Error path", escapeHtml(logs.error_path || "Unknown"))}${infoCard("Legacy path", escapeHtml(logs.legacy_action_path || "Unknown"))}${infoCard("Entries", escapeHtml(formatNumber(auditEntries.length)))}</div>`)}
      </section>
    </div>
  `;
}

function renderContext(state, query) {
  const { session, context } = safeState(state);
  const retrieval = objectValue(context.retrieval);
  const memoryHits = arrayValue(retrieval.memory_hits);
  const snippets = arrayValue(retrieval.corpus_snippets);
  const shortTermLines = String(session.short_term_context || "").split("\n").filter((line) => line.trim());

  function memoryHit(hit) {
    return `
      <div class="list-item">
        <div class="list-item__meta">
          <span>${chip(`score ${formatMetric(hit.score, 3)}`, "accent", "spark")}</span>
          <span>${escapeHtml(hit.kind || "memory")}</span>
          <span>${escapeHtml(formatTimestamp(hit.created_at))}</span>
        </div>
        <h3 class="list-item__title">${escapeHtml(hit.summary || "")}</h3>
        ${hit.metadata && Object.keys(hit.metadata).length ? jsonBlock(hit.metadata) : ""}
      </div>
    `;
  }

  function snippetCard(snippet) {
    return `
      <div class="list-item">
        <div class="list-item__meta">
          <span>${chip(`score ${formatMetric(snippet.score, 3)}`, "brand", "spark")}</span>
          <span>Line ${escapeHtml(snippet.line_number ?? "")}</span>
        </div>
        <h3 class="list-item__title">${escapeHtml(snippet.text || "")}</h3>
      </div>
    `;
  }

  return `
    <div class="stack">
      <section class="stat-grid">
        ${statCard({ label: "Memory hits", value: formatNumber(memoryHits.length), detail: "Relevant memories selected for the current query.", tone: "brand" })}
        ${statCard({ label: "Corpus snippets", value: formatNumber(snippets.length), detail: "Relevant lines from the merged corpus file.", tone: "accent" })}
        ${statCard({ label: "Short-term lines", value: formatNumber(shortTermLines.length), detail: "The rolling buffer of the last conversation turns.", tone: "good" })}
        ${statCard({ label: "Query", value: query || context.query || "none", detail: "The query used for the current context pass.", tone: "ghost" })}
      </section>

      <section class="grid grid--2">
        ${sectionCard("Assembled context", "The exact context text passed into the runtime.", preBlock(context.assembled_context || "No assembled context is available yet."))}
        ${sectionCard("Short-term buffer", "The rolling context buffer rebuilt from recent conversation turns.", preBlock(session.short_term_context || "No short-term context is available yet."))}
      </section>

      <section class="grid grid--2">
        ${sectionCard("Memory retrieval", "Relevant memories selected for the current query.", renderList(memoryHits, memoryHit, "No memory hits matched the current query."))}
        ${sectionCard("Corpus retrieval", "Relevant corpus snippets selected for the current query.", renderList(snippets, snippetCard, "No corpus snippets matched the current query."))}
      </section>
    </div>
  `;
}

function renderOps(state) {
  const { ops } = safeState(state);
  const commands = arrayValue(ops.commands);
  const paths = objectValue(ops.paths);

  function commandCard(command) {
    return `
      <div class="command">
        <div class="command__head">
          <h3 class="command__title">${escapeHtml(command.label || "Command")}</h3>
          <button type="button" class="btn btn--small btn--ghost" data-copy-command="${escapeHtml(command.command || "")}">
            ${icon("copy")}
            <span>Copy</span>
          </button>
        </div>
        <p class="command__body">${escapeHtml(command.command || "")}</p>
      </div>
    `;
  }

  return `
    <div class="stack">
      <section class="stat-grid">
        ${statCard({ label: "Commands", value: formatNumber(commands.length), detail: "Local shell commands surfaced by the dashboard.", tone: "brand" })}
        ${statCard({ label: "Paths", value: formatNumber(Object.keys(paths).length), detail: "Project paths used by the current runtime.", tone: "accent" })}
        ${statCard({ label: "Registry", value: ops.registry_path || "Unknown", detail: "The model registry associated with the current config.", tone: "good" })}
        ${statCard({ label: "Active model", value: ops.active_model?.version || "none", detail: ops.active_model?.model_path || "No active model loaded.", tone: ops.active_model ? "good" : "danger" })}
      </section>

      <section class="card">
        <div class="card__header">
          <div>
            <h2 class="card__title">Commands</h2>
            <p class="card__subtitle">Copy one of these local commands into your terminal when you need it.</p>
          </div>
        </div>
        <div class="card__body">
          <div class="command-grid">${commands.map(commandCard).join("")}</div>
        </div>
      </section>

      <section class="grid grid--2">
        ${sectionCard(
          "Local paths",
          "All file paths used by the dashboard and local runtime.",
          `<div class="info-grid">${Object.entries(paths).map(([label, value]) => infoCard(label.replace(/_/g, " "), escapeHtml(String(value || "Unknown")))).join("")}</div>`,
        )}
        ${sectionCard(
          "Local-first note",
          "Everything here points at project files on disk.",
          `<div class="empty-state">No external fonts, icon libraries, or CDNs are required. The dashboard loads its own CSS, JS, and SVG icons from the local <code>/assets</code> folder.</div>`,
        )}
      </section>
    </div>
  `;
}

function renderHealth(state) {
  const { health } = safeState(state);
  const cpu = objectValue(health.cpu);
  const memory = objectValue(health.memory);
  const confidence = objectValue(health.model_confidence);

  const cpuGrid = `<div class="info-grid">${infoCard("Proxy", escapeHtml(cpu.proxy_type || "unknown"))}${infoCard("CPU count", escapeHtml(formatNumber(cpu.cpu_count || 0)))}${infoCard("Thermal band", escapeHtml(cpu.thermal_proxy_band || "unknown"))}${infoCard("Load ratio 1m", escapeHtml(cpu.load_ratio_1m != null ? formatMetric(cpu.load_ratio_1m, 3) : "n/a"))}</div>`;
  const memoryGrid = `<div class="info-grid">${infoCard("Platform", escapeHtml(memory.platform || "unknown"))}${infoCard("Usage %", escapeHtml(memory.usage_percent != null ? formatMetric(memory.usage_percent, 2) : "n/a"))}${infoCard("Used bytes", escapeHtml(formatNumber(memory.used_bytes || 0)))}${infoCard("Available bytes", escapeHtml(formatNumber(memory.available_bytes || 0)))}</div>`;
  const confidenceGrid = `<div class="info-grid">${infoCard("Status", escapeHtml(confidence.status || "unknown"))}${infoCard("Band", escapeHtml(confidence.confidence_band || "unknown"))}${infoCard("Metric", escapeHtml(confidence.confidence_metric || "n/a"))}${infoCard("Score", escapeHtml(confidence.confidence_score != null ? formatMetric(confidence.confidence_score, 4) : "n/a"))}</div>`;

  return `
    <div class="stack">
      <section class="stat-grid">
        ${statCard({ label: "CPU thermal proxy", value: cpu.thermal_proxy_band || "unknown", detail: cpu.proxy_type || "no proxy", tone: "brand" })}
        ${statCard({ label: "RAM usage", value: memory.usage_percent != null ? `${formatMetric(memory.usage_percent, 2)}%` : "n/a", detail: memory.platform || "unknown", tone: "accent" })}
        ${statCard({ label: "Model confidence", value: confidence.confidence_band || "unknown", detail: confidence.confidence_metric || "no metric", tone: confidence.confidence_band === "low" ? "danger" : "good" })}
        ${statCard({ label: "Updated", value: formatTimestamp(health.timestamp || ""), detail: "Local runtime clock", tone: "ghost" })}
      </section>

      <section class="grid grid--2">
        ${sectionCard("CPU pressure / thermal proxy", "Derived from local load where available.", cpuGrid + (cpu.detail ? `<div class="empty-state">${escapeHtml(cpu.detail)}</div>` : ""))}
        ${sectionCard("RAM usage", "Physical memory usage snapshot from the local host runtime.", memoryGrid + (memory.detail ? `<div class="empty-state">${escapeHtml(memory.detail)}</div>` : ""))}
      </section>

      <section class="card">
        <div class="card__header">
          <div>
            <h2 class="card__title">Model confidence summary</h2>
            <p class="card__subtitle">Confidence band derived from active model metrics when available.</p>
          </div>
        </div>
        <div class="card__body">
          ${confidenceGrid}
          ${confidence.detail ? `<div class="empty-state">${escapeHtml(confidence.detail)}</div>` : ""}
        </div>
      </section>
    </div>
  `;
}

function renderNotFound(state, path) {
  return `
    <div class="stack">
      <section class="stat-grid">
        ${statCard({ label: "Requested path", value: path || "Unknown", detail: "This route is not recognized by the dashboard shell.", tone: "danger" })}
        ${statCard({ label: "Available pages", value: "9", detail: "overview, chat, runs, models, memory, context, logs, ops, and health", tone: "brand" })}
      </section>

      <section class="card">
        <div class="card__header">
          <div>
            <h2 class="card__title">Unknown route</h2>
            <p class="card__subtitle">Use one of the supported subpages below.</p>
          </div>
        </div>
        <div class="card__body">
          <div class="command-grid">${QUICK_LINKS.map(cardLink).join("")}</div>
        </div>
      </section>
    </div>
  `;
}

function bindPageActions(route) {
  const chatForm = viewEl.querySelector('[data-role="chat-form"]');
  const chatInput = viewEl.querySelector('[data-role="chat-input"]');
  const memoryForm = viewEl.querySelector('[data-role="memory-form"]');
  const memoryInput = viewEl.querySelector('[data-role="memory-query"]');

  if (chatForm && chatInput) {
    const sendMessage = async (text) => {
      const message = String(text || "").trim();
      if (!message) {
        return;
      }
      setStatus("Sending...");
      const controls = chatForm.querySelectorAll("button, input");
      controls.forEach((control) => {
        control.disabled = true;
      });
      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || `Request failed with ${response.status}`);
        }
        chatInput.value = "";
        await loadDashboard();
        setStatus(payload.reply ? "Updated" : "Ready");
      } catch (error) {
        console.error(error);
        setStatus("Chat error");
        alert(String(error.message || error));
      } finally {
        controls.forEach((control) => {
          control.disabled = false;
        });
        chatInput.focus();
      }
    };

    chatForm.addEventListener("submit", (event) => {
      event.preventDefault();
      sendMessage(chatInput.value);
    });

    chatForm.querySelectorAll("[data-action='confirm']").forEach((button) => {
      button.addEventListener("click", () => sendMessage("/confirm"));
    });
    chatForm.querySelectorAll("[data-action='reject']").forEach((button) => {
      button.addEventListener("click", () => sendMessage("/reject"));
    });
    chatForm.querySelectorAll("[data-action='last']").forEach((button) => {
      button.addEventListener("click", () => sendMessage("/last"));
    });
    chatForm.querySelectorAll("[data-action='context']").forEach((button) => {
      button.addEventListener("click", () => sendMessage("/history"));
    });
    viewEl.querySelectorAll("[data-action='refresh-chat']").forEach((button) => {
      button.addEventListener("click", () => loadDashboard());
    });
  }

  if (memoryForm && memoryInput) {
    memoryForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const query = memoryInput.value.trim();
      const nextUrl = new URL(window.location.href);
      if (query) {
        nextUrl.searchParams.set("q", query);
      } else {
        nextUrl.searchParams.delete("q");
      }
      window.location.href = nextUrl.toString();
    });
  }

  viewEl.querySelectorAll("[data-action='memory-recent']").forEach((button) => {
    button.addEventListener("click", () => {
      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.delete("q");
      window.location.href = nextUrl.toString();
    });
  });

  viewEl.querySelectorAll("[data-copy-command]").forEach((button) => {
    button.addEventListener("click", () => {
      copyToClipboard(button.getAttribute("data-copy-command") || "");
    });
  });

  if (route === "chat") {
    const log = viewEl.querySelector('[data-role="chat-log"]');
    if (log) {
      log.scrollTop = log.scrollHeight;
    }
  }
}

async function copyToClipboard(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      setStatus("Copied to clipboard");
      return true;
    }
  } catch (error) {
    console.warn("Clipboard write failed", error);
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    document.execCommand("copy");
    setStatus("Copied to clipboard");
    return true;
  } catch (error) {
    console.warn("Fallback clipboard copy failed", error);
    setStatus("Copy failed");
    return false;
  } finally {
    document.body.removeChild(textarea);
  }
}

async function loadDashboard() {
  currentRoute = normalizeRoute(window.location.pathname);
  currentQuery = new URLSearchParams(window.location.search).get("q")?.trim() || "";
  setDocumentTitle(currentRoute);
  setNavActive(currentRoute);
  setGlobalQueryInput(currentQuery);
  setStatus("Loading...");

  const loadToken = ++activeLoadToken;
  try {
    const response = await fetch(buildStateUrl(currentRoute, currentQuery));
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || `Dashboard state request failed with ${response.status}`);
    }
    if (loadToken !== activeLoadToken) {
      return;
    }
    renderShell(currentRoute, payload, currentQuery);
    bindPageActions(currentRoute);
  } catch (error) {
    if (loadToken !== activeLoadToken) {
      return;
    }
    console.error(error);
    routeMetaEl.innerHTML = hero("notfound", { query: currentQuery }, currentQuery);
    viewEl.innerHTML = `
      <div class="stack">
        <section class="card">
          <div class="card__header">
            <div>
              <h2 class="card__title">Unable to load dashboard state</h2>
              <p class="card__subtitle">The local server did not return a usable JSON payload.</p>
            </div>
          </div>
          <div class="card__body">
            <div class="empty-state">${escapeHtml(error.message || String(error))}</div>
            <div class="btn-group" style="margin-top: 12px;">
              <button type="button" class="btn btn--ghost" onclick="window.location.reload()">
                ${icon("refresh")}
                <span>Reload</span>
              </button>
              <a class="btn btn--green" href="/overview">
                ${icon("overview")}
                <span>Back to overview</span>
              </a>
            </div>
          </div>
        </section>
      </div>
    `;
    setStatus("Error");
  }
}

bindGlobalSearch();
loadDashboard();
